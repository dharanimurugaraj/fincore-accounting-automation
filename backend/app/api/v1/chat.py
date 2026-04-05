"""
POST /chat         — send a message, get AI response with document context
GET  /chat/history — fetch message history for a session
"""

import uuid
import json
from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.database import execute_query, execute_insert
from app.core.config import settings
from app.api.deps import CurrentUser
from app.schemas.chat import ChatRequest

router = APIRouter()

# Cost per 1M tokens (approximate)
COST_PER_1M = {
    "gemini-2.5-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-2.0-flash": {"in": 0.10, "out": 0.40},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
}


@router.post("")
async def send_message(req: ChatRequest, user: CurrentUser):
    """Send a message to the AI chat and return the response."""
    org_id = user["org_id"]
    month = req.statement_month or date.today().strftime("%Y-%m")

    # Build document context from latest approved run
    context = _build_context(org_id, month)

    # Build prompt
    system_prompt = (
        "You are FinCore AI, a banking intelligence assistant for an Indian company "
        "managing Working Capital facilities. You have access to the company's banking data "
        "for the selected month. Answer questions about CC utilisation, WCDL loans, forex "
        "transactions, interest charges, and finance costs. Be precise and cite figures. "
        "Format currency as Indian Rupees (₹). If data is not available, say so clearly."
    )

    user_message = req.message
    if context:
        user_message = f"[Banking Data Context for {month}]\n{context}\n\n[User Question]\n{req.message}"

    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    execute_insert(
        """
        INSERT INTO "ChatMessage" (id, "orgId", "userId", "sessionId", role, content, "createdAt")
        VALUES (%s, %s, %s, %s, 'user', %s, %s)
        """,
        (user_msg_id, org_id, user["id"], req.session_id, req.message, datetime.utcnow()),
    )

    # Call AI
    model_used = "gemini-2.5-flash-lite"
    response_text = ""
    tokens_in = 0
    tokens_out = 0

    try:
        if settings.gemini_available:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gemini_model = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite",
                system_instruction=system_prompt,
            )
            response = gemini_model.generate_content(user_message)
            response_text = response.text
            if hasattr(response, "usage_metadata"):
                tokens_in = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                tokens_out = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
            model_used = "gemini-2.5-flash-lite"
        else:
            response_text = (
                "AI service is not configured. Please set GEMINI_API_KEY in the backend .env file."
            )
    except Exception as e:
        response_text = f"I encountered an error processing your request: {str(e)}"

    # Calculate cost
    cost_rates = COST_PER_1M.get(model_used, {"in": 0.10, "out": 0.40})
    cost_usd = (tokens_in * cost_rates["in"] + tokens_out * cost_rates["out"]) / 1_000_000

    # Save assistant message
    asst_msg_id = f"msg_{uuid.uuid4().hex[:16]}"
    execute_insert(
        """
        INSERT INTO "ChatMessage"
            (id, "orgId", "userId", "sessionId", role, content, model,
             "tokensIn", "tokensOut", "costUsd", "createdAt")
        VALUES (%s, %s, %s, %s, 'assistant', %s, %s, %s, %s, %s, %s)
        """,
        (
            asst_msg_id, org_id, user["id"], req.session_id,
            response_text, model_used, tokens_in, tokens_out, cost_usd,
            datetime.utcnow(),
        ),
    )

    # Log AI usage
    log_id = f"ai_{uuid.uuid4().hex[:12]}"
    execute_insert(
        """
        INSERT INTO "AIUsageLog"
            (id, "orgId", "userId", "userEmail", model,
             "tokensIn", "tokensOut", "costUsd", action, "sessionId", "createdAt")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'CHAT', %s, %s)
        """,
        (
            log_id, org_id, user["id"], user.get("email", ""),
            model_used, tokens_in, tokens_out, cost_usd,
            req.session_id, datetime.utcnow(),
        ),
    )

    # Session cost
    session_cost_rows = execute_query(
        'SELECT COALESCE(SUM("costUsd"), 0) as total FROM "ChatMessage" WHERE "sessionId" = %s',
        (req.session_id,),
    )
    session_cost = float(session_cost_rows[0]["total"]) if session_cost_rows else 0.0

    return {
        "message": {
            "id": asst_msg_id,
            "session_id": req.session_id,
            "role": "assistant",
            "content": response_text,
            "model": model_used,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_usd": round(cost_usd, 6),
            "created_at": datetime.utcnow().isoformat(),
        },
        "session_id": req.session_id,
        "total_session_cost_usd": round(session_cost, 6),
    }


@router.get("/history")
async def get_chat_history(
    user: CurrentUser,
    session_id: str = Query(...),
    limit: int = Query(50, le=200),
):
    """Fetch conversation history for a session."""
    rows = execute_query(
        """
        SELECT id, "sessionId", role, content, model,
               "tokensIn", "tokensOut", "costUsd", "createdAt"
        FROM "ChatMessage"
        WHERE "orgId" = %s AND "sessionId" = %s
        ORDER BY "createdAt" ASC
        LIMIT %s
        """,
        (user["org_id"], session_id, limit),
    )

    messages = [
        {
            "id": r["id"],
            "session_id": r["sessionId"],
            "role": r["role"],
            "content": r["content"],
            "model": r["model"],
            "tokens_in": r["tokensIn"] or 0,
            "tokens_out": r["tokensOut"] or 0,
            "cost_usd": float(r["costUsd"]) if r["costUsd"] else 0.0,
            "created_at": r["createdAt"].isoformat() if r["createdAt"] else None,
        }
        for r in rows
    ]

    total_cost = sum(m["cost_usd"] for m in messages if m["role"] == "assistant")
    return {
        "session_id": session_id,
        "messages": messages,
        "total_cost_usd": round(total_cost, 6),
    }


# ── Context Builder ───────────────────────────────────────────────────────────

def _build_context(org_id: str, month: str) -> str:
    """Build a text context block from the latest approved run's data."""
    rows = execute_query(
        """
        SELECT "validationResult", "reportSummary"
        FROM "PipelineRun"
        WHERE "orgId" = %s AND "statementMonth" = %s AND status = 'APPROVED'
        ORDER BY "completedAt" DESC LIMIT 1
        """,
        (org_id, month),
    )
    if not rows:
        return ""

    run = rows[0]
    parts = [f"Statement Month: {month}"]

    if run["validationResult"]:
        try:
            val = json.loads(run["validationResult"])
            checks = val.get("checks", [])
            if checks:
                parts.append("\nValidation Results:")
                for c in checks[:10]:
                    parts.append(
                        f"  - {c['name']}: Computed ₹{c['computed']:,.2f} | "
                        f"Bank Stated ₹{c['bank_stated']:,.2f} | Status: {c['status']}"
                    )
        except Exception:
            pass

    if run["reportSummary"]:
        try:
            rs = json.loads(run["reportSummary"])
            parts.append(f"\nKPIs:")
            parts.append(f"  - CC Utilisation: {rs.get('cc_utilisation_pct', 'N/A')}%")
            parts.append(f"  - Finance Cost: {rs.get('finance_cost_pct', 'N/A')}% p.a.")
            parts.append(f"  - Total CC Interest: ₹{rs.get('total_cc_interest', 0):,.2f}")
            parts.append(f"  - Total WCDL Interest: ₹{rs.get('total_wcdl_interest', 0):,.2f}")
        except Exception:
            pass

    # WCDL summary
    wcdl_rows = execute_query(
        'SELECT "loanNumber", principal, roi, status FROM "WCDLLoan" WHERE "orgId" = %s AND "statementMonth" = %s',
        (org_id, month),
    )
    if wcdl_rows:
        parts.append("\nWCDL Loans:")
        for w in wcdl_rows:
            parts.append(
                f"  - Loan {w['loanNumber']}: ₹{float(w['principal']):,.0f} Cr at {float(w['roi'])*100:.2f}% ({w['status']})"
            )

    # Forex summary
    forex_rows = execute_query(
        """
        SELECT currency, COUNT(*) as cnt, SUM("excessVsAvg") as excess
        FROM "ForexTransaction"
        WHERE "orgId" = %s AND "statementMonth" = %s
        GROUP BY currency
        """,
        (org_id, month),
    )
    if forex_rows:
        parts.append("\nForex Transactions:")
        for f in forex_rows:
            parts.append(
                f"  - {f['currency']}: {f['cnt']} transactions, "
                f"Excess Charges ₹{float(f['excess'] or 0):,.2f}"
            )

    return "\n".join(parts)
