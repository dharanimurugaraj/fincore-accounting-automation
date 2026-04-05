"""
GET /reports               — list pipeline runs with download links
GET /reports/dashboard     — monthly KPI summary for the dashboard
POST /reports/{id}/approve — approve a run (alias kept for backwards compat)
"""

import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.database import execute_query, execute_insert
from app.api.deps import CurrentUser

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    user: CurrentUser,
    statement_month: Optional[str] = Query(None),
):
    """Return KPI summary for the latest approved run (or specified month)."""
    org_id = user["org_id"]

    query = """
        SELECT id, "statementMonth", status, "validationResult", "reportSummary",
               "statementExcelKey", "workingSheetKey", "bankingReportKey",
               "startedAt", "completedAt"
        FROM "PipelineRun"
        WHERE "orgId" = %s AND status = 'APPROVED'
    """
    params: list = [org_id]
    if statement_month:
        query += ' AND "statementMonth" = %s'
        params.append(statement_month)
    query += ' ORDER BY "completedAt" DESC LIMIT 1'

    try:
        rows = execute_query(query, tuple(params))
        if not rows:
            return _empty_dashboard(statement_month or _current_month())

        run = rows[0]
        month = run["statementMonth"]

        # Try cached reportSummary first
        if run["reportSummary"]:
            try:
                summary = json.loads(run["reportSummary"])
                summary["month"] = month
                summary.setdefault("has_data", True)
                return summary
            except:
                pass

        # Build from validationResult
        validation = {}
        if run["validationResult"]:
            try:
                validation = json.loads(run["validationResult"])
            except:
                pass

        checks = validation.get("checks", [])
        cc_interest = sum(
            (c.get("computed") or 0) for c in checks
            if "CC Interest" in c.get("name", "")
        )
        wcdl_interest = sum(
            (c.get("computed") or 0) for c in checks
            if "WCDL Interest" in c.get("name", "")
        )

        # Loans mapping
        wcdl_rows = execute_query(
            'SELECT * FROM "WCDLLoan" WHERE "orgId" = %s AND "statementMonth" = %s',
            (org_id, month)
        )
        wcdl_loans = []
        today = date.today()
        for w in wcdl_rows:
            try:
                maturity = w["maturityDate"]
                if isinstance(maturity, str):
                    maturity = date.fromisoformat(maturity)
                days_left = (maturity - today).days if maturity else None
                wcdl_loans.append({
                    "loanId": w["id"],
                    "loanNumber": w["loanNumber"],
                    "principal": float(w["principalAmount"] or 0),
                    "roi": float(w["roi"] or 0),
                    "maturityDate": str(maturity) if maturity else None,
                    "daysToMaturity": days_left,
                    "status": w["status"]
                })
            except:
                continue

        # KPI List
        fc_pct = validation.get("summary", {}).get("finance_cost_pct", 0) or 0
        kpis = [
            { "label": "Total CC Interest", "value": f"₹{(cc_interest or 0):,.2f}", "color": "text-emerald-400" },
            { "label": "Total WCDL Interest", "value": f"₹{(wcdl_interest or 0):,.2f}", "color": "text-amber-400" },
            { "label": "Finance Cost %", "value": f"{fc_pct:.2f}% p.a.", "color": "text-cyan-400" },
        ]

        return {
            "month": month,
            "kpis": kpis,
            "ccUtilisation": {"actual": validation.get("summary", {}).get("cc_utilisation_pct", 0) or 0, "sanctioned": 100},
            "wcdlUtilisation": {"actual": validation.get("summary", {}).get("wcdl_utilisation_pct", 0) or 0, "sanctioned": 100},
            "wcdlLoans": wcdl_loans,
            "chargesSummary": {
                "penal": float(sum(c.get("amount", 0) or 0 for c in validation.get("charges", []) if c.get("category") == "Penal")),
                "recurring": float(sum(c.get("amount", 0) or 0 for c in validation.get("charges", []) if c.get("category") == "Recurring")),
                "total": 0
            },
            "trendData": [],
            "idleBalances": validation.get("idle_balances", []),
            "has_data": True
        }
    except Exception as e:
        print(f"ERROR: Dashboard build failed: {e}")
        return _empty_dashboard(statement_month or _current_month())


@router.get("")
async def list_reports(
    user: CurrentUser,
    limit: int = Query(20, le=100),
    offset: int = Query(0),
):
    """List all pipeline runs for the org."""
    org_id = user["org_id"]
    rows = execute_query(
        """
        SELECT pr.id, pr."statementMonth", pr.status, pr.stage,
               pr."statementExcelKey", pr."workingSheetKey", pr."bankingReportKey",
               pr."validationResult", pr."errorMessage",
               pr."startedAt", pr."completedAt", pr."createdAt",
               COUNT(u.id) as upload_count
        FROM "PipelineRun" pr
        LEFT JOIN "Upload" u ON u."runId" = pr.id
        WHERE pr."orgId" = %s
        GROUP BY pr.id
        ORDER BY pr."createdAt" DESC
        LIMIT %s OFFSET %s
        """,
        (org_id, limit, offset),
    )

    result = []
    for row in rows:
        validation = None
        if row["validationResult"]:
            try:
                validation = json.loads(row["validationResult"])
            except Exception:
                pass

        result.append({
            "run_id": row["id"],
            "statement_month": row["statementMonth"],
            "status": row["status"],
            "stage": row["stage"],
            "upload_count": row["upload_count"],
            "statement_excel_key": row["statementExcelKey"],
            "working_sheet_key": row["workingSheetKey"],
            "banking_report_key": row["bankingReportKey"],
            "validation_result": validation,
            "error_message": row["errorMessage"],
            "started_at": row["startedAt"].isoformat() if row["startedAt"] else None,
            "completed_at": row["completedAt"].isoformat() if row["completedAt"] else None,
            "created_at": row["createdAt"].isoformat() if row["createdAt"] else None,
        })

    return {"reports": result, "total": len(result)}


@router.post("/{report_id}/approve")
async def approve_report(report_id: str, user: CurrentUser):
    """Approve a specific report — alias for /pipeline/approve."""
    rows = execute_query(
        'SELECT id, status FROM "PipelineRun" WHERE id = %s',
        (report_id,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Report not found")

    run = rows[0]
    if run["status"] == "APPROVED":
        return {"report_id": report_id, "status": "approved", "message": "Already approved"}

    if run["status"] != "AWAITING_APPROVAL":
        raise HTTPException(
            status_code=400,
            detail=f"Run is in status {run['status']}, cannot approve",
        )

    import uuid
    execute_query(
        'UPDATE "PipelineRun" SET status = %s, "completedAt" = %s WHERE id = %s',
        ("APPROVED", datetime.utcnow(), report_id),
    )

    approval_id = f"appr_{uuid.uuid4().hex[:12]}"
    execute_insert(
        'INSERT INTO "Approval" (id, "runId", "userId", "createdAt") VALUES (%s, %s, %s, %s)',
        (approval_id, report_id, user["id"], datetime.utcnow()),
    )

    audit_id = f"aud_{uuid.uuid4().hex[:12]}"
    execute_insert(
        """
        INSERT INTO "AuditLog" (id, "orgId", "userId", action, "entityType", "entityId", "createdAt")
        VALUES (%s, %s, %s, 'APPROVED', 'PipelineRun', %s, %s)
        """,
        (audit_id, user["org_id"], user["id"], report_id, datetime.utcnow()),
    )

    return {"report_id": report_id, "status": "approved", "message": "Report approved successfully"}


# ── Helpers ───────────────────��──────────────────────────────────��────────────

def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def _empty_dashboard(month: str) -> dict:
    return {
        "month": month,
        "run_id": None,
        "kpis": [],
        "ccUtilisation": {"actual": 0, "sanctioned": 100},
        "wcdlUtilisation": {"actual": 0, "sanctioned": 100},
        "wcdl_loans": [],
        "trend_data": [],
        "chargesSummary": {"penal": 0, "recurring": 0, "total": 0},
        "idleBalances": [],
        "has_data": False,
    }
