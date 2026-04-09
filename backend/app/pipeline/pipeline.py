import os
import asyncio
import uuid
from io import BytesIO
from app.core.database import execute_insert, execute_query
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
            # 1. Validation & Download from R2
            from app.services.storage_service import download_file_to_memory, derive_org_folder, get_excel_key, upload_file_object
            
            self.update_progress(job_id, "validation", "running", "Downloading and validating bank statements...", 10)
            validated_pdfs = []
            errors = []
            
            # Temporary storage for downloaded files
            temp_dir = f"./storage/temp/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)

            async def download_and_validate(s3_key):
                try:
                    filename = s3_key.split("/")[-1]
                    local_path = os.path.join(temp_dir, filename)
                    
                    # Download from R2
                    file_mem = await asyncio.to_thread(download_file_to_memory, s3_key)
                    with open(local_path, "wb") as f:
                        f.write(file_mem.getbuffer())
                    
                    # Validate local file
                    result = await asyncio.to_thread(self.validator.validate, local_path)
                    return result
                except Exception as e:
                    return {"valid": False, "reason": str(e), "path": s3_key}

            # Gather results
            validation_results = await asyncio.gather(*[download_and_validate(k) for k in pdf_paths])
            
            for result in validation_results:
                if result["valid"]:
                    validated_pdfs.append(result)
                else:
                    errors.append({"file": os.path.basename(result.get("path", "Unknown")), "reason": result["reason"]})
            
            if not validated_pdfs:
                return {"error": "No valid bank PDFs found", "path_errors": errors}
            
            self.update_progress(job_id, "validation", "done", f"Validated {len(validated_pdfs)} PDF(s)", 20, 
                                 sub_steps=[f"✓ {p['bank']} (..{p['account_number'][-4:]})" for p in validated_pdfs])

            # 2. Extraction (Existing logic applies to local temp files)
            accounts_data = []
            wcdl_data = []
            ai_usage = []
            
            # Local callback to track progress across parallel jobs
            file_progress = {os.path.basename(p["path"]): "Waiting..." for p in validated_pdfs}
            
            def make_on_progress(filename):
                last_reported_page = 0
                def callback(current: int, total: int):
                    nonlocal last_reported_page
                    if current >= total:
                        file_progress[filename] = "Finalized"
                    else:
                        file_progress[filename] = f"Analyzing Page {current}/{total}"
                    
                    should_update = (current == 1 or current == total or (current - last_reported_page) >= 5)
                    if should_update:
                        last_reported_page = current
                        sub_steps = [f"{'✓' if 'Finalized' in prog else '⏳'} {f}: {prog}" for f, prog in file_progress.items()]
                        self.update_progress(job_id, "extraction", "running", f"Parsing {len(validated_pdfs)} PDFs in parallel...", 40, sub_steps=sub_steps)
                return callback

            async def process_single_pdf(pdf_info):
                filename = os.path.basename(pdf_info["path"])
                extraction_result = await self.extractor.extract(
                    pdf_info["path"], 
                    bank_name=pdf_info.get("bank", "UNKNOWN"),
                    on_progress=make_on_progress(filename),
                    user_context=user_context
                )
                
                extracted = extraction_result.get("data", {})
                usage = extraction_result.get("usage", {})
                
                if not extracted.get("bank_name") or extracted.get("bank_name") == "UNKNOWN":
                    extracted["bank_name"] = pdf_info.get("bank")
                
                if not extracted.get("account_number") or extracted.get("account_number") == "UNKNOWN" or "XXX" in str(extracted.get("account_number")):
                     extracted["account_number"] = pdf_info.get("account_number")
                
                return {"extracted": extracted, "usage": usage}

            results = await asyncio.gather(*[process_single_pdf(p) for p in validated_pdfs])
            
            self.update_progress(job_id, "extraction", "running", "Persisting extracted data to DB...", 50)
            for res in results:
                extracted = res["extracted"]
                if res["usage"]: ai_usage.append(res["usage"])
                
                acct_id = f"acct_{uuid.uuid4().hex[:8]}"
                execute_insert(
                    'INSERT INTO "ParsedAccount" (id, "runId", "bankName", "accountNo", "accountType", "periodFrom", "periodTo", "openingBal", "closingBal") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
                    (
                        acct_id, job_id, extracted.get("bank_name"), extracted.get("account_number"),
                        extracted.get("account_type", "CC"), extracted.get("period_from"), extracted.get("period_to"),
                        extracted.get("opening_balance"), extracted.get("closing_balance")
                    )
                )
                
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

            # Preparation
            from .working_sheet import _expand_to_full_month
            import calendar
            for acc in accounts_data:
                start_date = acc.get("period_from")
                if start_date and "-" in start_date:
                    try:
                        dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
                        first_day = dt.replace(day=1)
                        last_day_num = calendar.monthrange(dt.year, dt.month)[1]
                        last_day = dt.replace(day=last_day_num)
                        acc["period_from"] = first_day.strftime("%Y-%m-%d")
                        acc["period_to"] = last_day.strftime("%Y-%m-%d")
                    except Exception: pass

                acc["full_month_transactions"] = _expand_to_full_month(acc.get("transactions", []), acc.get("period_from"), acc.get("period_to"), acc.get("opening_balance", 0))

            # Step 3: Computation
            self.update_progress(job_id, "computation", "running", "Computing financial formulas...", 60)
            computed = self.engine.compute_all(accounts_data, wcdl_data, ai_usage=ai_usage)
            
            # Step 4: Excel Generation & Upload to R2
            period_data = self._get_period_context(accounts_data)
            period_slug = period_data["slug"] 
            
            self.update_progress(job_id, "working_sheet", "running", "Generating and uploading Excel Reports...", 70)
            
            # Fetch run metadata (org_folder, timestamp)
            run_rows = execute_query('SELECT "org_folder", "run_timestamp" FROM "PipelineRun" WHERE id = %s', (job_id,))
            if not run_rows or not run_rows[0].get("org_folder"):
                # Fallback if not set (backwards compat during migration)
                email = user_context.get("email") if user_context else "unknown@fincore.app"
                org_folder = derive_org_folder(email)
                run_timestamp = generate_run_timestamp()
            else:
                org_folder = run_rows[0]["org_folder"]
                run_timestamp = run_rows[0]["run_timestamp"]

            # Generate local temp files
            ws_path = await asyncio.to_thread(generate_working_sheet, accounts_data, wcdl_data, computed, job_id, period_slug)
            br_path = await asyncio.to_thread(generate_banking_report, accounts_data, computed, job_id, period_slug)

            # Upload to R2
            ws_key = get_excel_key(org_folder, run_timestamp, "workingsheet")
            br_key = get_excel_key(org_folder, run_timestamp, "bankingreport")

            async def upload_async(local_path, key):
                with open(local_path, "rb") as f:
                    file_obj = BytesIO(f.read())
                    return await asyncio.to_thread(upload_file_object, file_obj, key, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            await asyncio.gather(
                upload_async(ws_path, ws_key),
                upload_async(br_path, br_key)
            )

            # Update PipelineRun with R2 keys
            from app.core.database import update_pipeline_s3_key
            update_pipeline_s3_key(job_id, "workingSheetKey", ws_key)
            update_pipeline_s3_key(job_id, "bankingReportKey", br_key)
            
            execute_query(
                'UPDATE "PipelineRun" SET status = %s, "completedAt" = %s WHERE id = %s',
                ("APPROVED", datetime.utcnow(), job_id)
            )
            
            self.update_progress(
                job_id, "complete", "complete", "Analysis complete. Reports uploaded to R2.", 100, 
                sub_steps=[f"✓ {os.path.basename(ws_key)}", f"✓ {os.path.basename(br_key)}"],
                downloads={"working_sheet": ws_key, "banking_report": br_key}
            )
            
            # Cleanup temp files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            if os.path.exists(ws_path): os.remove(ws_path)
            if os.path.exists(br_path): os.remove(br_path)

            return {
                "success": True,
                "jobId": job_id,
                "workingSheetKey": ws_key,
                "bankingReportKey": br_key,
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
