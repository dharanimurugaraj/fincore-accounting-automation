import pdfplumber
import fitz  # PyMuPDF
import json
import os
import httpx
import asyncio
import base64
import io
import re
from datetime import datetime
from typing import Dict, Any, List, Callable
from app.core.config import settings
from .classifier import classify_transaction
from app.core.database import execute_insert
import uuid

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

class PDFExtractor:

    async def extract(self, pdf_path: str, bank_name: str = "UNKNOWN", on_progress: Callable[[int, int], None] = None, user_context: dict = None) -> Dict[str, Any]:
        """ Optimized hybrid extraction: Deterministic first, then AI if needed. """
        
        # 1. OPTIMIZATION: Immediate Deterministic Check (Zero AI latency)
        pages_text = await self._get_pages_text(pdf_path)
        total_pages = len(pages_text)
        
        # Check if it looks like HDFC/Union Bank from text immediately
        header_sample = "\n".join(pages_text[:3]).upper()
        
        if "HDFC BANK" in header_sample:
            deterministic = await asyncio.to_thread(self._extract_hdfc_deterministic, pages_text, on_progress=on_progress)
            if deterministic:
                await self._log_usage({"model": "DETERMINISTIC_HDFC", "prompt_tokens": 0, "completion_tokens": 0}, "PARSE", user_context)
                return {"data": deterministic, "usage": {"model": "deterministic_hdfc"}}
        
        if "UNION BANK" in header_sample:
            deterministic = await asyncio.to_thread(self._extract_union_bank_deterministic, pages_text, on_progress=on_progress)
            if deterministic:
                await self._log_usage({"model": "DETERMINISTIC_UBI", "prompt_tokens": 0, "completion_tokens": 0}, "PARSE", user_context)
                return {"data": deterministic, "usage": {"model": "deterministic_ubi"}}

        # 2. If not deterministic, proceed to AI (Validation -> Vision)
        # Using gpt-4o-mini for validation as it's 10x faster and more reliable than Sonnet for simple detection
        validation = await self.validate_statement(pdf_path, user_context=user_context)
        if validation.get("data", {}).get("is_bank_statement") is False:
             return {"data": {"error": f"Rejected: {validation['data'].get('rejection_reason')}"}, "usage": {}}
             
        # AI Logic (Vision) - PARALLELIZE THIS (Fixing 40-minute delay for 57 pages)
        self.update_progress = on_progress
        images_base64 = await self._render_pdf_to_base64(pdf_path)
        total_pages = len(images_base64)
        
        semaphore = asyncio.Semaphore(10) # Process 10 pages concurrently
        tasks = []
        
        async def _process_page(idx, img_b64):
            async with semaphore:
                # Local progress update for this specific page
                res = await self._structure_image(img_b64, user_context=user_context)
                if self.update_progress:
                    self.update_progress(idx + 1, total_pages, detail=f"Extracted Page {idx+1}/{total_pages}")
                return res

        for i, img_b64 in enumerate(images_base64):
            tasks.append(_process_page(i, img_b64))
            
        results = await asyncio.gather(*tasks)
        
        all_transactions = []
        final_meta = {}
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "model": "anthropic/claude-sonnet-4.5"}
        
        for res in results:
            data = res.get("data", {})
            usage = res.get("usage", {})
            
            total_usage["prompt_tokens"] += (usage.get("prompt_tokens") or 0)
            total_usage["completion_tokens"] += (usage.get("completion_tokens") or 0)
            
            if "transactions" in data:
                all_transactions.extend(data["transactions"])
                
            if not final_meta and "account_number" in data:
                final_meta = {
                    "account_number": data.get("account_number"),
                    "account_type": data.get("account_type"),
                    "bank_name": data.get("bank_name"),
                    "period_from": data.get("period_from"),
                    "period_to": data.get("period_to"),
                    "cc_roi_percent": data.get("cc_roi_percent"),
                    "opening_balance": data.get("opening_balance")
                }
            
            if "closing_balance" in data:
                final_meta["closing_balance"] = data.get("closing_balance")

        # Classify final list
        for txn in all_transactions:
            txn["category"] = classify_transaction(txn.get("narration", ""))
            
        final_data = {**final_meta, "transactions": all_transactions}
        return {"data": final_data, "usage": total_usage}

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
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # Slightly lower res for speed
                img_data = pix.tobytes("png")
                b64 = base64.b64encode(img_data).decode("utf-8")
                images.append(f"data:image/png;base64,{b64}")
            doc.close()
            return images
        return await asyncio.to_thread(_render)

    async def _structure_image(self, image_url: str, user_context: dict = None) -> Dict[str, Any]:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.FRONTEND_URL,
            "X-Title": "FinCore AI"
        }
        
        payload = {
            "model": "anthropic/claude-sonnet-4.5",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=120.0)
                
                # Check for stability - fallback to cheap/reliable mini if bad gateway or 404
                if response.status_code != 200:
                    print(f"WARN: Sonnet 4.5 Vision Failed ({response.status_code}), trying 3.5 Sonnet...")
                    payload["model"] = "anthropic/claude-3.5-sonnet"
                    response = await client.post(url, headers=headers, json=payload, timeout=120.0)
                
                if response.status_code != 200:
                    raise Exception(f"AI Service Unavailable ({response.status_code})")
                
                data = response.json()
                content = data['choices'][0]['message'].get('content', '')
                
                if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content: content = content.split("```")[1].split("```")[0].strip()
                
                usage = data.get("usage", {})
                usage["model"] = data.get("model", "unknown") # Extract model from top level
                await self._log_usage(usage, "EXTRACT_VISION", user_context)
                return {"data": json.loads(content), "usage": usage}
        except Exception as e:
            return {"data": {"error": str(e)}, "usage": {}}

    async def validate_statement(self, pdf_path: str, user_context: dict = None) -> Dict[str, Any]:
        """ Uses gpt-4o-mini for ultra-fast validation. """
        pages = await self._get_pages_text(pdf_path)
        header_text = "\n".join(pages[:2])
        
        prompt = f"Analyze this bank statement header. Return JSON with is_bank_statement, bank_name, account_number, account_type. Rules: CC Account = CC_PRIMARY. Text: {header_text}"
        
        payload = {
            "model": "openai/gpt-4o-mini", # FAST and RELIABLE
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        res = await self._call_openrouter(payload)
        if res.get("usage"):
            await self._log_usage(res["usage"], "VALIDATE", user_context)
        return res

    async def _log_usage(self, usage: dict, action: str, user: dict):
        if not user: return
        
        # OpenRouter returns 'model', but sometimes it's nested
        model = usage.get("model", "unknown")
        p_tokens = usage.get("prompt_tokens", 0)
        c_tokens = usage.get("completion_tokens", 0)
        
        # Precise dynamic pricing (USD per 1M tokens)
        rates = {
            "anthropic/claude-sonnet-4.5": (3.00, 15.00),
            "anthropic/claude-3.5-sonnet": (3.00, 15.00),
            "openai/gpt-4o-mini": (0.15, 0.60),
            "unknown": (3.00, 15.00)
        }
        
        # Resolve rate
        in_p, out_p = rates.get(model, (3.00, 15.00))
        cost = (p_tokens * in_p + c_tokens * out_p) / 1_000_000
        
        try:
            execute_insert(
                'INSERT INTO "AIUsageLog" (id, "orgId", "userId", "userEmail", model, "tokensIn", "tokensOut", "costUsd", action, "createdAt") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                (f"ai_{uuid.uuid4().hex[:12]}", user.get("org_id"), user.get("id"), user.get("email", ""), model, p_tokens, c_tokens, cost, action, datetime.utcnow())
            )
        except Exception as e:
            print(f"WARN: Usage logging failed: {e}")

    async def _call_openrouter(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                data = response.json()
                content = data['choices'][0]['message'].get('content', '')
                if "```json" in content: content = content.split("```json")[1].split("```")[0].strip()
                usage = data.get("usage", {})
                usage["model"] = data.get("model", "unknown")
                return {"data": json.loads(content), "usage": usage}
        except Exception as e:
            return {"data": {"error": str(e)}, "usage": {}}

    def _extract_hdfc_deterministic(self, pages: List[str], on_progress: Callable = None) -> Dict[str, Any]:
        transactions = []
        meta = {"bank_name": "HDFC"}
        running_narration = ""
        current_date = None
        prev_balance = None
        total_pages = len(pages)
        for i, page_text in enumerate(pages, 1):
            if on_progress: on_progress(i, total_pages)
            lines = page_text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                if "Account:" in line or "Account No:" in line:
                    meta["account_number"] = re.split(r'Account(?:\s+No)?:', line)[-1].strip().split()[0]
                if "Opening Balance" in line:
                    match = re.search(r'(OD|Cr)\s+Rs\.?\s?([\d,]+\.\d{2})', line)
                    if match:
                        code, val = match.groups()
                        meta["opening_balance"] = float(val.replace(',', '')) * (-1 if code == 'OD' else 1)
                        prev_balance = meta["opening_balance"]
                if "Statement Period:" in line:
                    dates = re.findall(r'(\d{2}-[A-Za-z]{3}-\d{4})', line)
                    if len(dates) >= 2:
                        meta["period_from"] = datetime.strptime(dates[0], "%d-%b-%Y").strftime("%Y-%m-%d")
                        meta["period_to"] = datetime.strptime(dates[1], "%d-%b-%Y").strftime("%Y-%m-%d")
                date_match = re.match(r'^(\d{2}-[A-Za-z]{3}-\d{4})', line)
                if date_match:
                    # If we already have a pending transaction from a previous date, save it? 
                    # No, HDFC usually has one trans per date-line start.
                    current_date = date_match.group(1)
                    remaining = line[len(current_date):].strip()
                    
                    # Check if amounts are already on this line
                    row_match = re.search(r'(?:Rs\.\s?([\d,]+\.\d{2}))\s+(OD|Cr)\s+Rs\.\s?([\d,]+\.\d{2})', remaining)
                    if row_match:
                        txn_amt_str, bal_code, bal_val_str = row_match.groups()
                        bal_val = float(bal_val_str.replace(',', '')) * (-1 if bal_code == 'OD' else 1)
                        txn_amt = float(txn_amt_str.replace(',', ''))
                        is_withdrawal = (bal_val < prev_balance) if prev_balance is not None else True
                        
                        narration = remaining[:row_match.start()].strip()
                        transactions.append({
                            "date": datetime.strptime(current_date, "%d-%b-%Y").strftime("%Y-%m-%d"),
                            "narration": narration,
                            "withdrawal": txn_amt if is_withdrawal else None,
                            "deposit": None if is_withdrawal else txn_amt,
                            "closing_balance": bal_val
                        })
                        prev_balance = bal_val
                        current_date = None # Reset
                        running_narration = ""
                    else:
                        running_narration = remaining
                else:
                    if current_date:
                        # Check if amounts are on this continuation line
                        row_match = re.search(r'(?:Rs\.\s?([\d,]+\.\d{2}))\s+(OD|Cr)\s+Rs\.\s?([\d,]+\.\d{2})', line)
                        if row_match:
                            txn_amt_str, bal_code, bal_val_str = row_match.groups()
                            bal_val = float(bal_val_str.replace(',', '')) * (-1 if bal_code == 'OD' else 1)
                            txn_amt = float(txn_amt_str.replace(',', ''))
                            is_withdrawal = (bal_val < prev_balance) if prev_balance is not None else True
                            
                            narration = (running_narration + " " + line[:row_match.start()]).strip()
                            transactions.append({
                                "date": datetime.strptime(current_date, "%d-%b-%Y").strftime("%Y-%m-%d"),
                                "narration": narration,
                                "withdrawal": txn_amt if is_withdrawal else None,
                                "deposit": None if is_withdrawal else txn_amt,
                                "closing_balance": bal_val
                            })
                            prev_balance = bal_val
                            current_date = None
                            running_narration = ""
                        else:
                            running_narration += " " + line
        if transactions:
            meta["transactions"] = transactions
            meta["closing_balance"] = transactions[-1]["closing_balance"]
            return meta
        return None

    def _extract_union_bank_deterministic(self, pages: List[str], on_progress: Callable = None) -> Dict[str, Any]:
        meta = {"bank_name": "UNION BANK OF INDIA", "opening_balance": 0.0, "transactions": []}
        full_text = "\n".join(pages)
        acct_match = re.search(r'A/c No:\s*(\w+)', full_text)
        if acct_match: meta["account_number"] = acct_match.group(1)
        period_match = re.search(r'Period:\s*(\d{2}-[A-Za-z]{3}-\d{4})\s*to\s*(\d{2}-[A-Za-z]{3}-\d{4})', full_text)
        if period_match:
            try:
                meta["period_from"] = datetime.strptime(period_match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
                meta["period_to"] = datetime.strptime(period_match.group(2), "%d-%b-%Y").strftime("%Y-%m-%d")
            except: pass
        open_bal_match = re.search(r'Opening Balance as on .*?:\s*Rs\.([\d,]+\.\d{2})\s*(Cr|Dr)', full_text)
        if open_bal_match:
            val = float(open_bal_match.group(1).replace(",", ""))
            if open_bal_match.group(2) == "Dr": val = -val
            meta["opening_balance"] = val
        transactions = []
        current_date = None
        running_narration = ""
        prev_balance = meta["opening_balance"]
        total_pages = len(pages)
        for i, p in enumerate(pages, 1):
            if on_progress: on_progress(i, total_pages)
            lines = p.split("\n")
            for line in lines:
                line = line.strip()
                if not line or "Union Bank" in line or "Page" in line: continue
                date_match = re.match(r'^(\d{2}-[A-Za-z]{3}-\d{4})\s?(.*)', line)
                if date_match:
                    current_date = date_match.group(1)
                    running_narration = date_match.group(2).strip()
                else:
                    if current_date:
                        row_match = re.search(r'Rs\.([\d,]+\.\d{2})\s+Rs\.([\d,]+\.\d{2})\s+(Cr|Dr)$', line)
                        if row_match:
                            txn_amt_str, bal_val_str, bal_flag = row_match.groups()
                            bal_val = float(bal_val_str.replace(",", "")) * (-1 if bal_flag == "Dr" else 1)
                            txn_amt = float(txn_amt_str.replace(",", ""))
                            is_withdrawal = bal_val < prev_balance
                            transactions.append({
                                "date": datetime.strptime(current_date, "%d-%b-%Y").strftime("%Y-%m-%d"),
                                "narration": running_narration,
                                "withdrawal": txn_amt if is_withdrawal else None,
                                "deposit": None if is_withdrawal else txn_amt,
                                "closing_balance": bal_val,
                                "category": classify_transaction(running_narration)
                            })
                            prev_balance = bal_val
                            current_date = None
                            running_narration = ""
                        else:
                            running_narration += " " + line
        if transactions:
            meta["transactions"] = transactions
            meta["closing_balance"] = transactions[-1]["closing_balance"]
            return meta
        return None
