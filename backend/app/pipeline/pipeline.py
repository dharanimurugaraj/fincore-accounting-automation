import os
import asyncio
import uuid
from app.core.database import execute_insert
from datetime import datetime
from typing import List, Dict, Any
from .validator import PDFValidator
from .extractor import PDFExtractor
from .engine import FinCoreComputationEngine
from .working_sheet import generate_working_sheet
from .banking_report import generate_banking_report

class FinCorePipeline:
    
    def __init__(self):
        self.validator = PDFValidator()
        self.extractor = PDFExtractor()
        self.engine = FinCoreComputationEngine()

    def update_progress(self, job_id, step, status, message, percent, sub_steps=None, downloads=None):
        """ Persistent Progress Helper (Writes to DB Layer) """
        from app.core.database import execute_query
        import json
        
        # Format substeps for JSON column
        substeps_json = json.dumps(sub_steps) if sub_steps else None
        
        # Map step to RunStatus enum if needed, but progressPercent is the primary UI driver
        # For now, we update the metadata and Percent
        execute_query(
            'UPDATE "PipelineRun" SET "progressPercent" = %s, "progressMessage" = %s, "progressSubsteps" = %s WHERE id = %s',
            (percent, f"[{step.upper()}] {message}", substeps_json, job_id)
        )
        
        # Log to server console
        print(f"[PROGRESS] Job {job_id[-6:]}: {percent}% - {message}")

    async def run(self, job_id: str, pdf_paths: List[str], user_context: dict = None) -> Dict[str, Any]:
        """
        Input:  List of PDF file paths
        Output: { ... }
        """
        try:
            # 1. Validation
            self.update_progress(job_id, "validation", "running", "Validating bank statements...", 10)
            validated_pdfs = []
            errors = []
            
            # Parallelize validation using to_thread for CPU-bound PDF reading
            async def validate_async(path):
                return await asyncio.to_thread(self.validator.validate, path)

            validation_results = await asyncio.gather(*[validate_async(p) for p in pdf_paths])
            
            for result in validation_results:
                if result["valid"]:
                    validated_pdfs.append(result)
                else:
                    errors.append({"file": os.path.basename(result.get("path", "Unknown")), "reason": result["reason"]})
            
            if not validated_pdfs:
                return {"error": "No valid bank PDFs found", "path_errors": errors}
            
            self.update_progress(job_id, "validation", "done", f"Validated {len(validated_pdfs)} PDF(s)", 20, 
                                 sub_steps=[f"✓ {p['bank']} (..{p['account_number'][-4:]})" for p in validated_pdfs])

            # 2. Extraction
            accounts_data = []
            wcdl_data = []
            ai_usage = []
            
            # Local callback to track progress across parallel jobs
            file_progress = {os.path.basename(p["path"]): "Waiting..." for p in validated_pdfs}
            
            def make_on_progress(filename):
                last_reported_page = 0
                def callback(current: int, total: int):
                    nonlocal last_reported_page
                    
                    # Update status map
                    if current >= total:
                        file_progress[filename] = "Finalized"
                    else:
                        file_progress[filename] = f"Analyzing Page {current}/{total}"
                    
                    # THROTTLE: Only write to DB every 5 pages or on finalization
                    # This prevents "connection pool exhausted" errors on large PDFs (50+ pages)
                    should_update = (current == 1 or current == total or (current - last_reported_page) >= 5)
                    
                    if should_update:
                        last_reported_page = current
                        sub_steps = [f"{'✓' if 'Finalized' in prog else '⏳'} {f}: {prog}" for f, prog in file_progress.items()]
                        self.update_progress(job_id, "extraction", "running", f"Parsing {len(validated_pdfs)} PDFs in parallel...", 40, sub_steps=sub_steps)
                return callback

            async def process_single_pdf(pdf_info):
                print(f"\n[PIPELINE] Starting Extraction for: {os.path.basename(pdf_info['path'])}")
                filename = os.path.basename(pdf_info["path"])
                # FIX: Extraction can be CPU bound or blocking, ensure it reports back to UI loop
                extraction_result = await self.extractor.extract(
                    pdf_info["path"], 
                    bank_name=pdf_info.get("bank", "UNKNOWN"),
                    on_progress=make_on_progress(filename),
                    user_context=user_context
                )
                
                extracted = extraction_result.get("data", {})
                usage = extraction_result.get("usage", {})
                
                # Tag with metadata (Prioritize Scouted Name/Number over Validator guess)
                if not extracted.get("bank_name") or extracted.get("bank_name") == "UNKNOWN":
                    extracted["bank_name"] = pdf_info.get("bank")
                
                if not extracted.get("account_number") or extracted.get("account_number") == "UNKNOWN" or "XXX" in str(extracted.get("account_number")):
                     extracted["account_number"] = pdf_info.get("account_number")
                
                return {"extracted": extracted, "usage": usage}

            # Parallelize extraction
            results = await asyncio.gather(*[process_single_pdf(p) for p in validated_pdfs])
            
            # Persist to DB (Layer 3 Source of Truth)
            self.update_progress(job_id, "extraction", "running", "Persisting extracted data to DB...", 50)
            for res in results:
                extracted = res["extracted"]
                if res["usage"]: ai_usage.append(res["usage"])
                
                # Insert Parsed Account
                acct_id = f"acct_{uuid.uuid4().hex[:8]}"
                execute_insert(
                    'INSERT INTO "ParsedAccount" (id, "runId", "bankName", "accountNo", "accountType", "periodFrom", "periodTo", "openingBal", "closingBal") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (
                        acct_id, job_id, extracted.get("bank_name"), extracted.get("account_number"),
                        extracted.get("account_type", "CC"), extracted.get("period_from"), extracted.get("period_to"),
                        extracted.get("opening_balance"), extracted.get("closing_balance")
                    )
                )
                
                # Insert Transactions
                for txn in extracted.get("transactions", []):
                    bal = float(txn.get("closing_balance", 0))
                    dr_cr = "CR" if bal >= 0 else "DR"
                    cc_val = abs(bal) if bal < 0 else 0
                    pos_bal = bal if bal >= 0 else 0
                    no_days = 1 if bal >= 0 else None
                    
                    execute_insert(
                        'INSERT INTO "Transaction" (id, "accountId", date, narration, "refNumber", withdrawal, deposit, "closingBalance", "drCrFlag", "ccValue", "posBalance", "noOfDays", category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                        (
                            f"txn_{uuid.uuid4().hex[:8]}", acct_id, txn.get("date"), txn.get("narration"),
                            txn.get("ref_number"), txn.get("withdrawal"), txn.get("deposit"),
                            bal, dr_cr, cc_val, pos_bal, no_days, txn.get("category")
                        )
                    )
                
                accounts_data.append(extracted)

            # Preparation: Expand transactions for full month BEFORE parallel generation
            from .working_sheet import _expand_to_full_month
            import calendar
            for acc in accounts_data:
                start_date = acc.get("period_from")
                
                # Auto-Snap to Full Calendar Month
                if start_date and "-" in start_date:
                    try:
                        dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
                        first_day = dt.replace(day=1)
                        last_day_num = calendar.monthrange(dt.year, dt.month)[1]
                        last_day = dt.replace(day=last_day_num)
                        acc["period_from"] = first_day.strftime("%Y-%m-%d")
                        acc["period_to"] = last_day.strftime("%Y-%m-%d")
                    except Exception:
                        pass

                start_date = acc.get("period_from")
                end_date = acc.get("period_to")
                open_bal = acc.get("opening_balance", 0)
                txns = acc.get("transactions", [])
                acc["full_month_transactions"] = _expand_to_full_month(txns, start_date, end_date, open_bal)

            # Step 3: Computation
            self.update_progress(job_id, "computation", "running", "Computing financial formulas...", 60)
            computed = self.engine.compute_all(accounts_data, wcdl_data, ai_usage=ai_usage)
            
            # Step 4: Excel Generation
            period_data = self._get_period_context(accounts_data)
            period_slug = period_data["slug"] 
            
            self.update_progress(job_id, "working_sheet", "running", "Generating Excel Reports in parallel...", 70)
            
            # Start BOTH in parallel (Layer 4 & 5)
            # data is already expanded, so both will see the full month rows
            ws_task = asyncio.to_thread(generate_working_sheet, accounts_data, wcdl_data, computed, job_id, period_slug)
            br_task = asyncio.to_thread(generate_banking_report, accounts_data, computed, job_id, period_slug)

            ws_path, report_path = await asyncio.gather(ws_task, br_task)
            
            # Update PipelineRun with file paths and final status (Layer 6)
            from app.core.database import update_pipeline_s3_key, update_pipeline_status
            update_pipeline_s3_key(job_id, "workingSheetKey", ws_path)
            update_pipeline_s3_key(job_id, "bankingReportKey", report_path)
            
            # Use execute_query to update status and completedAt concisely
            from app.core.database import execute_query
            execute_query(
                'UPDATE "PipelineRun" SET status = %s, "completedAt" = %s WHERE id = %s',
                ("APPROVED", datetime.utcnow(), job_id)
            )
            
            self.update_progress(
                job_id, "complete", "complete", "Analysis complete. Download links ready.", 100, 
                sub_steps=[f"✓ {os.path.basename(ws_path)}", f"✓ {os.path.basename(report_path)}"],
                downloads={"working_sheet": ws_path, "banking_report": report_path}
            )
            
            return {
                "success": True,
                "jobId": job_id,
                "workingSheet": ws_path,
                "bankingReport": report_path,
                "count": len(accounts_data)
            }

        except Exception as e:
            self.update_progress(job_id, "error", "error", f"Pipeline failed: {str(e)}", 0)
            return {"error": str(e)}

    def _get_period_context(self, accounts_data: List[Dict]) -> Dict[str, str]:
        """ Infers period context for naming and display. """
        now = datetime.now()
        default = {"slug": now.strftime("%b%Y"), "display": now.strftime("%b-%Y")}
        
        if not accounts_data or not accounts_data[0].get("transactions"):
            return default
        
        first_date = accounts_data[0]["transactions"][0].get("date", "")
        try:
            if "-" in first_date:
                dt = datetime.strptime(first_date[:10], "%Y-%m-%d")
            else:
                dt = datetime.strptime(first_date[:10], "%d/%m/%Y")
            return {
                "slug": dt.strftime("%b%Y"),    # Feb2026
                "display": dt.strftime("%b-%Y") # Feb-2026
            }
        except:
            return default
