"""
PDFExtractor -- Hybrid extraction pipeline.

Phase 1 (Gate check)         -- pdfplumber; zero AI cost
Phase 2 (LLM pattern scout)  -- page 1 text -> gpt-4o-mini -> BankSchema JSON (one call/PDF)
Phase 3 (Dynamic regex)      -- BankSchema drives regex engine over ALL pages in parallel
Fallback (Legacy AI vision)  -- claude-sonnet per page; original behaviour, triggered only
                                when Phase 2 fails or confidence is critically low

UNIVERSAL APPROACH:
  We no longer have hardcoded rules for specific banks (HDFC/UBI).
  Every statement uses Phase 2 to discover the template and Phase 3 to execute it.
"""

import pdfplumber
import fitz          # PyMuPDF
import json
import os
import httpx
import asyncio
import base64
import re
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings
from app.core.database import execute_insert

from .bank_schema import BankSchema
from .classifier import classify_transaction
from .schema_parser import SchemaParser, infer_dr_cr, classify_transactions


# == Prompts ==================================================================

SCOUT_PROMPT = """
Target: You are a Bank Statement Archaeologist. 
Task: Analyze the provided first page text of a bank PDF and extract the structural "DNA" for a regex parser.
 Your job is to identify the account metadata and describe the \
exact column/format structure so a deterministic regex engine can parse the remaining pages.

Return ONLY a valid JSON object -- no markdown, no explanation, no trailing text.

Required fields:
{
  "bank_name":        "exact bank name from header",
  "account_number":   "account number string",
  "account_type":     "CC" or "CA" or "SA",
  "period_from":      "YYYY-MM-DD or null",
  "period_to":        "YYYY-MM-DD or null",
  "opening_balance":  number or null,
  "cc_roi_percent":   number or null,
  "cc_limit":         number or null,

  "date_format": "DD-Mon-YYYY" | "DD/MM/YYYY" | "DD-MM-YYYY" | "YYYY-MM-DD" | "DD Mon YYYY" | "DD MMM YYYY",
  "amount_style": "rs_prefix" | "plain_number",
  "balance_style": "marker_inline" | "dr_cr_suffix" | "signed" | "plain_positive",
  "column_layout": "amount_then_balance" | "debit_credit_balance" | "amount_flag_balance",

  "positive_markers": ["strings that mean positive balance, e.g. Cr, CR"],
  "negative_markers": ["OD", "DR", "Dr", "Debit"],

  "has_narration_continuation": true | false,
  "header_keywords": ["up to 6 exact column header words from the table header row"],
  "skip_footer_markers": ["optional strings marking start of footer, ignore text below these"],

  "narration_col_name": "exact column header used for narration/remarks (e.g. 'Transaction Remarks')",
  "ref_col_name":       "exact column header used for reference number",
  "withdrawal_col_name": "exact column header used for debit/withdrawals",
  "deposit_col_name":    "exact column header used for credit/deposits",
  "balance_col_name":    "exact column header used for running balance"
}

Definitions:
  account_type:
    CC = Cash Credit / Overdraft account (balance can be negative)
    CA = Current Account
    SA = Savings Account
  amount_style:
    rs_prefix    -> amounts shown as "Rs.1,23,456.78" or "Rs 12,345.67"
    plain_number -> amounts shown as "1,23,456.78" without Rs prefix
  balance_style:
    marker_inline  -> balance has OD/Cr/DR marker on SAME token (HDFC CC: "Rs.50,000 OD")
    dr_cr_suffix   -> balance followed by standalone Dr or Cr word (Axis: "50,000.00 Dr")
    signed         -> balance is a plain signed number (-50000.00)
    plain_positive -> balance always positive; debit/credit cols determine direction
  column_layout:
    amount_then_balance   -> one transaction-amount column then closing balance (HDFC CC, Union Bank)
    debit_credit_balance  -> separate Debit and Credit columns then closing balance (SBI, Axis, ICICI Savings)
    amount_flag_balance   -> one amount column, Dr/Cr flag column, then balance (ICICI CC)
  has_narration_continuation:
    true  -> transaction description may span multiple lines before amount row appears
    false -> every transaction fits on exactly one line

Rules:
1. "column_layout":
   - Use 'debit_credit_balance' if there are separate columns for Dr and Cr.
   - Use 'amount_then_balance' if all amounts are in one column followed by Dr/Cr/OD.
2. "negative_markers": Very important for Axis/CC statements. Include ["OD", "DR"] next to balances.
3. Ignore header dates for 'date_format'; look at transaction rows (e.g. 03-03-2025).
4. If a value has 'DR' or 'OD' or 'Dr' next to it in opening balance line, return it as NEGATIVE.

Page 1 Text:
------------
{page1_text}
"""

# Original vision prompt (Fallback only -- unchanged)
EXTRACTION_PROMPT = """
You are a professional bank statement parser.
Extract all transactions from the provided image(s) into a structured JSON format.

Rules:
- Remove commas and 'Rs.' from numerical strings.
- Standardize dates to YYYY-MM-DD.
- Handle Cash Credit (CC) markers:
  - If a balance has 'OD', it is a negative number (e.g., 'OD 1,000' -> -1000).
  - If a balance has 'Cr', it is a positive number (e.g., 'Cr 1,000' -> 1000).
- Extract period_from and period_to from the header if available.
- Look for Interest Rates (ROI %) in the header or transaction narration (e.g., 'INT RATE 7.25%').
- For each transaction: date, narration, ref_number, withdrawal, deposit, closing_balance.

Output EXACTLY this JSON structure:
{
  "account_number": "string",
  "account_type": "string",
  "bank_name": "string",
  "period_from": "YYYY-MM-DD",
  "period_to": "YYYY-MM-DD",
  "opening_balance": number or null,
  "closing_balance": number or null,
  "cc_roi_percent": number or null,
  "transactions": [
    {
      "date": "YYYY-MM-DD",
      "narration": "string",
      "ref_number": "string",
      "withdrawal": number or null,
      "deposit": number or null,
      "closing_balance": number
    }
  ]
}
"""


# == PDFExtractor =============================================================

class PDFExtractor:
    """
    Main extractor. Call extract() for each PDF.
    Returns: { "data": { account + transactions dict }, "usage": { tokens/cost } }
    """

    # -- Public entry point ---------------------------------------------------

    async def extract(
        self,
        pdf_path: str,
        bank_name: str = "UNKNOWN",
        on_progress: Optional[Callable[[int, int], None]] = None,
        user_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Universal Hybrid extraction entry point.
        Every PDF uses a 1-page AI scout to determine the format.
        """
        pages_text = await self._get_pages_text(pdf_path)

        if not pages_text:
            return {"data": {"error": "Empty PDF"}, "usage": {}}

        # -- Phase 2: LLM pattern scout (page 1 TEXT only, one call per PDF) --
        # This determines: Bank, Account, Date Format, Column positions, etc.
        scout_result = await self._scout_pattern(pages_text[0], user_context)
        schema: Optional[BankSchema] = scout_result.get("schema")
        scout_usage = scout_result.get("usage", {})

        if schema and schema.is_valid():
            # SUCCESS: Explicitly log discovery for flow visibility
            print(f"\n[PHASE 2 - SUCCESS] Identified Format Blueprint:")
            print(f" > Bank:    {schema.bank_name}")
            print(f" > Account: {schema.account_number} ({schema.account_type})")
            print(f" > Period:  {schema.period_from} to {schema.period_to}")
            print(f" > Column Mappings:")
            print(f"   - Narration: '{schema.narration_col_name}'")
            print(f"   - Ref No:    '{schema.ref_col_name}'")
            print(f"   - Withdrawal:'{schema.withdrawal_col_name}'")
            print(f"   - Deposit:   '{schema.deposit_col_name}'")
            print(f"   - Balance:   '{schema.balance_col_name}'")
            print(f" > Sign Markers (Neg): {schema.negative_markers}")
            print(f" > Engine:   Actuating Dynamic Regex over {len(pages_text)} pages...\n")

            # -- Phase 3: Dynamic regex engine (Parallel on ALL pages, including p.1) --
            data, regex_usage = await self._dynamic_regex_engine(
                pages_text, schema, on_progress, user_context
            )
            combined_usage = _merge_usage(scout_usage, regex_usage)
            return {"data": data, "usage": combined_usage}

        # -- Fallback: legacy AI vision (If scout fails or confidence is low) --
        print(
            f"[EXTRACTOR] Phase 2 scout failed or invalid schema "
            f"({scout_result.get('error', 'unknown')}). "
            f"Falling back to AI vision for {os.path.basename(pdf_path)}."
        )
        return await self._legacy_vision_extract(pdf_path, on_progress, user_context)

    # -- Phase 2: Scout -------------------------------------------------------

    async def _scout_pattern(
        self,
        page1_text: str,
        user_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """
        Send page 1 text to gpt-4o-mini to return a BankSchema.
        """
        prompt = SCOUT_PROMPT.replace("{page1_text}", page1_text[:6000])

        payload = {
            "model": "anthropic/claude-4.5-sonnet-20250929",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }

        result = await self._call_openrouter(payload)
        data   = result.get("data", {})
        usage  = result.get("usage", {})

        if "error" in data or not isinstance(data, dict):
            return {"schema": None, "usage": usage, "error": data.get("error", "bad response")}

        if usage:
            await self._log_usage(usage, "SCOUT", user_context)

        try:
            schema = BankSchema.from_dict(data)
            schema.extraction_model = usage.get("model", "openai/gpt-4o-mini")
            missing = [f for f in ("bank_name", "period_from", "period_to") if not data.get(f)]
            schema.confidence = "low" if len(missing) >= 2 else ("medium" if missing else "high")
            return {"schema": schema, "usage": usage}
        except Exception as e:
            return {"schema": None, "usage": usage, "error": str(e)}

    # -- Phase 3: Dynamic regex engine ----------------------------------------

    async def _dynamic_regex_engine(
        self,
        pages_text: List[str],
        schema: BankSchema,
        on_progress: Optional[Callable],
        user_context: Optional[dict] = None,
    ) -> tuple:
        """
        Runs SchemaParser on every page in parallel via asyncio.to_thread.
        """
        parser = SchemaParser(schema)
        total_pages = len(pages_text)
        semaphore = asyncio.Semaphore(10) # Max 10 concurrent parsing threads

        async def _parse(page_idx: int, text: str) -> Dict:
            async with semaphore:
                result = await asyncio.to_thread(parser.parse_page, text)
                if on_progress:
                    on_progress(page_idx + 1, total_pages)
                return result

        # All pages in parallel -- limited by semaphore
        page_results = await asyncio.gather(
            *[_parse(i, page) for i, page in enumerate(pages_text)]
        )

        # Merge results from all pages
        all_transactions: List[Dict] = []
        final_closing: Optional[float] = None

        for pr in page_results:
            all_transactions.extend(pr.get("transactions", []))
            if pr.get("closing_balance") is not None:
                final_closing = pr["closing_balance"]

        # Sort by date
        try:
            all_transactions.sort(key=lambda t: t.get("date", ""))
        except Exception:
            pass

        # Reconstruct withdrawal/deposit direction based on balance flow
        all_transactions = infer_dr_cr(all_transactions, schema.opening_balance or 0.0)

        # Narration classification
        all_transactions = classify_transactions(all_transactions)

        # Persist schema JSON to AIUsageLog for audit/replay
        await self._persist_schema(schema, user_context)

        data = {
            "bank_name":          schema.bank_name,
            "account_number":     schema.account_number,
            "account_type":       schema.account_type,
            "period_from":        schema.period_from,
            "period_to":          schema.period_to,
            "opening_balance":    schema.opening_balance,
            "closing_balance":    final_closing,
            "cc_roi_percent":     schema.cc_roi_percent,
            "cc_limit":           schema.cc_limit,
            "transactions":       all_transactions,

            # Semantic Column Metadata for Working Sheet
            "narration_col_name":  schema.narration_col_name,
            "ref_col_name":        schema.ref_col_name,
            "withdrawal_col_name": schema.withdrawal_col_name,
            "deposit_col_name":    schema.deposit_col_name,
            "balance_col_name":    schema.balance_col_name,

            "_extraction_mode":   "hybrid_schema_regex",
            "_schema_confidence": schema.confidence,
        }

        # Log a "PARSE" row for the UI dashboard
        await self._log_usage(
            {"model": f"HYBRID_REGEX ({schema.bank_name})", "prompt_tokens": 0, "completion_tokens": 0},
            "PARSE", user_context,
        )

        usage = {
            "model":             f"schema_regex (scouted by {schema.extraction_model})",
            "prompt_tokens":     0,
            "completion_tokens": 0,
        }
        return data, usage

    # -- Fallback: Legacy AI vision (original code, unchanged) ----------------

    async def _legacy_vision_extract(
        self,
        pdf_path: str,
        on_progress: Optional[Callable],
        user_context: Optional[dict],
    ) -> Dict[str, Any]:
        """
        Original per-page image vision fallback.
        Sends every page as a base64 PNG to Claude Sonnet.
        """
        validation = await self.validate_statement(pdf_path, user_context=user_context)
        if validation.get("data", {}).get("is_bank_statement") is False:
            reason = validation["data"].get("rejection_reason", "Not a bank statement")
            return {"data": {"error": f"Rejected: {reason}"}, "usage": {}}

        images_b64 = await self._render_pdf_to_base64(pdf_path)
        total_pages = len(images_b64)
        self._on_progress = on_progress

        semaphore = asyncio.Semaphore(10)

        async def _process_page(idx: int, img_b64: str) -> Dict:
            async with semaphore:
                res = await self._structure_image(img_b64, user_context=user_context)
                if self._on_progress:
                    self._on_progress(idx + 1, total_pages)
                return res

        results = await asyncio.gather(
            *[_process_page(i, img) for i, img in enumerate(images_b64)]
        )

        all_transactions: List[Dict] = []
        final_meta: Dict = {}
        total_usage = {
            "prompt_tokens": 0, "completion_tokens": 0,
            "model": "anthropic/claude-sonnet-4-5",
        }

        for res in results:
            d     = res.get("data", {})
            usage = res.get("usage", {})
            total_usage["prompt_tokens"]     += usage.get("prompt_tokens", 0) or 0
            total_usage["completion_tokens"] += usage.get("completion_tokens", 0) or 0
            if "transactions" in d:
                all_transactions.extend(d["transactions"])
            if not final_meta and "account_number" in d:
                final_meta = {k: d.get(k) for k in (
                    "account_number", "account_type", "bank_name",
                    "period_from", "period_to", "cc_roi_percent", "opening_balance",
                )}
            if "closing_balance" in d:
                final_meta["closing_balance"] = d["closing_balance"]

        for txn in all_transactions:
            txn["category"] = classify_transaction(txn.get("narration", ""))

        return {
            "data": {**final_meta, "transactions": all_transactions,
                     "_extraction_mode": "legacy_vision"},
            "usage": total_usage,
        }

    # -- AI helpers -----------------------------------------------------------

    async def _get_pages_text(self, pdf_path: str) -> List[str]:
        def _read():
            pages = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    pages.append(page.extract_text() or "")
            return pages
        return await asyncio.to_thread(_read)

    async def _render_pdf_to_base64(self, pdf_path: str) -> List[str]:
        def _render():
            images = []
            doc = fitz.open(pdf_path)
            for page in doc:
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = pix.tobytes("png")
                b64 = base64.b64encode(img_data).decode("utf-8")
                images.append(f"data:image/png;base64,{b64}")
            doc.close()
            return images
        return await asyncio.to_thread(_render)

    async def _structure_image(
        self, image_url: str, user_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Legacy AI vision call -- unchanged from original."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.FRONTEND_URL,
            "X-Title": "FinCore AI",
        }
        payload = {
            "model": "anthropic/claude-4.5-sonnet-20250929",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text",      "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }],
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=120.0)
                if response.status_code != 200:
                    print(f"WARN: Sonnet 4.5 Vision failed ({response.status_code}), trying 3.5 Sonnet...")
                    payload["model"] = "anthropic/claude-3.5-sonnet"
                    response = await client.post(url, headers=headers, json=payload, timeout=120.0)
                if response.status_code != 200:
                    raise Exception(f"AI Service unavailable ({response.status_code})")
                data = response.json()
                content = data["choices"][0]["message"].get("content", "")
                content = _strip_json_fences(content)
                usage = data.get("usage", {})
                usage["model"] = data.get("model", "unknown")
                await self._log_usage(usage, "EXTRACT_VISION", user_context)
                return {"data": json.loads(content), "usage": usage}
        except Exception as e:
            return {"data": {"error": str(e)}, "usage": {}}

    async def validate_statement(
        self, pdf_path: str, user_context: Optional[dict] = None,
    ) -> Dict[str, Any]:
        pages = await self._get_pages_text(pdf_path)
        header_text = "\n".join(pages[:2])
        prompt = (
            "Analyze this bank statement header. Return JSON with "
            "is_bank_statement, bank_name, account_number, account_type. "
            f"Rules: CC Account = CC_PRIMARY. Text: {header_text}"
        )
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        }
        res = await self._call_openrouter(payload)
        if res.get("usage"):
            await self._log_usage(res["usage"], "VALIDATE", user_context)
        return res

    async def _call_openrouter(self, payload: Dict) -> Dict:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                data = response.json()
                content = data["choices"][0]["message"].get("content", "")
                content = _strip_json_fences(content)
                usage = data.get("usage", {})
                usage["model"] = data.get("model", "unknown")
                return {"data": json.loads(content), "usage": usage}
        except Exception as e:
            return {"data": {"error": str(e)}, "usage": {}}

    async def _log_usage(
        self, usage: dict, action: str, user: Optional[dict],
    ) -> None:
        if not user:
            return
        model    = usage.get("model", "unknown")
        p_tokens = usage.get("prompt_tokens", 0) or 0
        c_tokens = usage.get("completion_tokens", 0) or 0
        rates = {
            "anthropic/claude-sonnet-4-5": (3.00, 15.00),
            "anthropic/claude-3.5-sonnet": (3.00, 15.00),
            "openai/gpt-4o-mini":          (0.15,  0.60),
            "unknown":                     (3.00, 15.00),
        }
        in_p, out_p = rates.get(model, (3.00, 15.00))
        cost = (p_tokens * in_p + c_tokens * out_p) / 1_000_000
        try:
            execute_insert(
                'INSERT INTO "AIUsageLog" '
                '(id, "orgId", "userId", "userEmail", model, "tokensIn", "tokensOut", '
                '"costUsd", action, "createdAt") '
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    f"ai_{uuid.uuid4().hex[:12]}",
                    user.get("org_id"), user.get("id"), user.get("email", ""),
                    model, p_tokens, c_tokens, cost, action, datetime.utcnow(),
                ),
            )
        except Exception as e:
            print(f"WARN: AI usage logging failed: {e}")

    async def _persist_schema(
        self, schema: BankSchema, user_context: Optional[dict],
    ) -> None:
        """
        Store the extracted BankSchema in AIUsageLog (action=SCHEMA_SCOUT).
        """
        if not user_context:
            return
        try:
            schema_json = json.dumps(schema.to_dict())
            execute_insert(
                'INSERT INTO "AIUsageLog" '
                '(id, "orgId", "userId", "userEmail", model, "tokensIn", "tokensOut", '
                '"costUsd", action, "createdAt") '
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    f"schema_{uuid.uuid4().hex[:12]}",
                    user_context.get("org_id"), user_context.get("id"),
                    user_context.get("email", ""),
                    f"schema_regex:{schema.bank_name}",
                    0, 0, 0.0,
                    f"SCHEMA_SCOUT:{schema_json[:500]}",
                    datetime.utcnow(),
                ),
            )
        except Exception as e:
            print(f"WARN: Schema persistence failed: {e}")


# == Utilities ================================================================

def _strip_json_fences(content: str) -> str:
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return content


def _merge_usage(a: dict, b: dict) -> dict:
    return {
        "model":             a.get("model") or b.get("model", "unknown"),
        "prompt_tokens":     (a.get("prompt_tokens") or 0) + (b.get("prompt_tokens") or 0),
        "completion_tokens": (a.get("completion_tokens") or 0) + (b.get("completion_tokens") or 0),
    }
