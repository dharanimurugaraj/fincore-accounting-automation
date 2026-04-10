import os
import asyncio
import uuid
import calendar as cal_mod
from io import BytesIO
from app.core.database import execute_insert, execute_query
from datetime import datetime, date
from typing import List, Dict, Any
from .validator import PDFValidator
from .extractor import PDFExtractor
from .statement_transform import apply_transforms_to_account, apply_transforms_to_transactions
from .engine import FinCoreComputationEngine
from .working_sheet import generate_working_sheet
from .banking_report import generate_banking_report
from .fx_sheet import generate_fx_sheet, build_daily_loan_util_dict
from .loan_tracker import loans_from_wcdl_rows, calculate_loan_interest, LoanTracker

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
            
            # Temporary storage for downloaded files (Vercel-friendly /tmp path)
            is_vercel = os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
            temp_root = "/tmp/fincore/temp" if is_vercel else "./storage/temp"
            temp_dir = os.path.join(temp_root, job_id)
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
            accounts_data  = []
            fx_accounts    = []   # FX-type accounts routed separately
            wcdl_data      = []   # raw dicts from DB (WCDLLoan rows)
            loan_trackers: List[LoanTracker] = []  # typed for utilisation engine
            ai_usage       = []
            
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
                
                # Prioritize a non-UNKNOWN account number
                ext_acct = str(extracted.get("account_number", "")).strip()
                val_acct = str(pdf_info.get("account_number", "")).strip()
                
                # If extracted is bad (empty, UNKNOWN, or heavily masked) and validator is better, swap
                is_bad_ext = not ext_acct or ext_acct == "UNKNOWN" or (ext_acct.count('X') > 5 and val_acct != "UNKNOWN")
                if is_bad_ext and val_acct and val_acct != "UNKNOWN":
                    extracted["account_number"] = val_acct
                elif not ext_acct or ext_acct == "UNKNOWN":
                     extracted["account_number"] = val_acct if val_acct else "UNKNOWN"
                
                return {"extracted": extracted, "usage": usage}

            results = await asyncio.gather(*[process_single_pdf(p) for p in validated_pdfs])
            
            self.update_progress(job_id, "extraction", "running", "Persisting extracted data to DB...", 50)
            
            # Dynamic Cleanup: Remove previous records for this job to avoid unique constraint violations on re-runs
            execute_query('DELETE FROM "ParsedAccount" WHERE "runId" = %s', (job_id,))

            for res in results:
                extracted = res["extracted"]
                if res["usage"]: ai_usage.append(res["usage"])
                apply_transforms_to_account(extracted)

                # Use full UUID for ID to ensure zero collisions
                acct_id = f"acct_{uuid.uuid4().hex}"
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
                    wd = float(txn.get("withdrawal_dr", txn.get("withdrawal") or 0))
                    dep = float(txn.get("deposit_cr", txn.get("deposit") or 0))
                    pos_bal = float(txn.get("positive_balance", 0))
                    no_days = txn.get("no_of_days")
                    if no_days is None:
                        no_days = 1 if pos_bal > 0 else 0
                    dr_cr = "CR" if pos_bal > 0 else "DR"
                    cc_val = abs(bal) if bal < 0 else 0

                    execute_insert(
                        'INSERT INTO "Transaction" (id, "accountId", date, narration, "refNumber", withdrawal, deposit, "closingBalance", "drCrFlag", "ccValue", "posBalance", "noOfDays", category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                        (
                            f"txn_{uuid.uuid4().hex}", acct_id, txn.get("date"), txn.get("narration"),
                            txn.get("ref_number"), wd, dep,
                            bal, dr_cr, cc_val, pos_bal, no_days, txn.get("category")
                        )
                    )
                # Route FX accounts separately — they go to fx_sheet, not working_sheet
                if extracted.get("account_type", "CC") == "FX":
                    fx_accounts.append(extracted)
                else:
                    accounts_data.append(extracted)

            # ── Preparation: expand to full calendar period ─────────────────
            from .working_sheet import _expand_to_full_month

            for acc in accounts_data + fx_accounts:
                start_date = acc.get("period_from")
                if start_date and "-" in start_date:
                    try:
                        dt           = datetime.strptime(start_date[:10], "%Y-%m-%d")
                        first_day    = dt.replace(day=1)
                        last_day_num = cal_mod.monthrange(dt.year, dt.month)[1]
                        last_day     = dt.replace(day=last_day_num)
                        acc["period_from"] = first_day.strftime("%Y-%m-%d")
                        acc["period_to"]   = last_day.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                acc["full_month_transactions"] = _expand_to_full_month(
                    acc.get("transactions", []),
                    acc.get("period_from"),
                    acc.get("period_to"),
                    acc.get("opening_balance", 0),
                    balance_style=acc.get("balance_style") or "signed",
                )
                fmx = acc.get("full_month_transactions") or []
                if fmx:
                    apply_transforms_to_transactions(
                        fmx,
                        acc.get("balance_style") or "signed",
                        acc.get("positive_markers"),
                        acc.get("negative_markers"),
                    )

            # ── Infer actual days in period + period slug ──────────────────
            # Must happen BEFORE the loan_rows query (which uses period_slug)
            period_data    = self._get_period_context(accounts_data)
            period_slug    = period_data["slug"]   # e.g. "Feb2026"
            days_in_period = 30
            if accounts_data:
                pf = accounts_data[0].get("period_from")
                pt = accounts_data[0].get("period_to")
                if pf and pt:
                    try:
                        d_start = datetime.strptime(pf[:10], "%Y-%m-%d")
                        d_end   = datetime.strptime(pt[:10], "%Y-%m-%d")
                        days_in_period = (d_end - d_start).days + 1
                    except Exception:
                        pass

            # ── Load WCDL / BC / PQL loans from DB for this org + month ────
            loan_rows = execute_query(
                'SELECT * FROM "WCDLLoan" WHERE "orgId" = %s AND "statementMonth" = %s',
                (user_context.get("org_id") if user_context else None, period_slug),
            ) or []
            # Also merge any wcdl_data passed in (backwards compat)
            loan_rows = loan_rows + list(wcdl_data)
            loan_trackers = loans_from_wcdl_rows(loan_rows)

            # ── Build daily loan utilisation dict (for working sheet I/J/K) ─
            daily_loan_util = None
            if loan_trackers and accounts_data:
                # Build date_range from period of primary account
                pf_str = accounts_data[0].get("period_from", "")
                pt_str = accounts_data[0].get("period_to", "")
                try:
                    d_start = datetime.strptime(pf_str[:10], "%Y-%m-%d").date()
                    d_end   = datetime.strptime(pt_str[:10], "%Y-%m-%d").date()
                    from datetime import timedelta
                    date_range = [
                        d_start + timedelta(days=i)
                        for i in range((d_end - d_start).days + 1)
                    ]
                    daily_loan_util = build_daily_loan_util_dict(loan_trackers, date_range)
                except Exception as e:
                    print(f"WARN: daily_loan_util build failed: {e}")

            # ── Calculate per-loan interest results for Section C ───────────
            loan_results = [calculate_loan_interest(l) for l in loan_trackers]

            # ── Step 3: Computation ─────────────────────────────────────────
            self.update_progress(job_id, "computation", "running", "Computing financial formulas...", 60)
            computed = self.engine.compute_all(
                accounts_data, loan_rows, ai_usage=ai_usage,
                days_in_period=days_in_period,
            )

            # Attach avg WCDL util for Section A of banking report
            if loan_trackers and days_in_period > 0:
                total_wcdl_days = sum(
                    l.principal_inr * l.actual_active_days_in_range(
                        datetime.strptime(
                            (accounts_data[0].get("period_from") or "")[:10], "%Y-%m-%d"
                        ).date() if accounts_data and accounts_data[0].get("period_from") else date.today(),
                        datetime.strptime(
                            (accounts_data[0].get("period_to") or "")[:10], "%Y-%m-%d"
                        ).date() if accounts_data and accounts_data[0].get("period_to") else date.today(),
                    )
                    for l in loan_trackers if l.loan_type == "WCDL"
                )
                computed["avg_wcdl_util"] = total_wcdl_days / days_in_period if days_in_period else 0.0
            else:
                computed["avg_wcdl_util"] = 0.0
            
            # Step 4: Excel Generation & Upload to R2
            self.update_progress(job_id, "working_sheet", "running", "Generating and uploading Excel Reports...", 70)

            # Fetch run metadata (orgFolder, runTimestamp) from DB
            run_rows = execute_query('SELECT "orgFolder", "runTimestamp" FROM "PipelineRun" WHERE id = %s', (job_id,))
            if not run_rows or not run_rows[0].get("orgFolder"):
                email         = user_context.get("email") if user_context else "unknown@fincore.app"
                org_folder    = derive_org_folder(email)
                run_timestamp = generate_run_timestamp()
            else:
                org_folder    = run_rows[0]["orgFolder"]
                run_timestamp = run_rows[0]["runTimestamp"]

            # ── Generate local temp files in parallel ───────────────────────
            ws_path = await asyncio.to_thread(
                generate_working_sheet,
                accounts_data, loan_rows, computed, job_id, period_slug,
                daily_loan_util,          # Gap 4: WCDL/BC/PQL per-day values
            )
            br_path = await asyncio.to_thread(
                generate_banking_report,
                accounts_data, computed, job_id, period_slug,
                loan_results,             # Gap 6: Section C per-loan ROI table
            )

            # FX sheet (Gap 7): only generated when FX accounts exist
            fx_path = None
            if fx_accounts:
                fx_path = await asyncio.to_thread(
                    generate_fx_sheet, fx_accounts, job_id, period_slug
                )

            # ── Upload to R2 ────────────────────────────────────────────────
            ws_key = get_excel_key(org_folder, run_timestamp, "workingsheet")
            br_key = get_excel_key(org_folder, run_timestamp, "bankingreport")

            async def upload_async(local_path, key):
                with open(local_path, "rb") as f:
                    file_obj = BytesIO(f.read())
                    return await asyncio.to_thread(
                        upload_file_object, file_obj, key,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            upload_tasks = [
                upload_async(ws_path, ws_key),
                upload_async(br_path, br_key),
            ]
            if fx_path:
                fx_key = get_excel_key(org_folder, run_timestamp, "fxsheet")
                upload_tasks.append(upload_async(fx_path, fx_key))

            await asyncio.gather(*upload_tasks)

            # ── Update PipelineRun with R2 keys ────────────────────────────
            from app.core.database import update_pipeline_s3_key
            update_pipeline_s3_key(job_id, "workingSheetKey", ws_key)
            update_pipeline_s3_key(job_id, "bankingReportKey", br_key)
            if fx_path:
                update_pipeline_s3_key(job_id, "fxSheetKey", fx_key)

            execute_query(
                'UPDATE "PipelineRun" SET status = %s, "completedAt" = %s WHERE id = %s',
                ("APPROVED", datetime.utcnow(), job_id),
            )

            sub_steps = [
                f"✓ Working Sheet ({len(accounts_data)} accounts)",
                f"✓ Banking Report (Section A/B/C)",
            ]
            if fx_path:
                sub_steps.append(f"✓ FX Sheet ({len(fx_accounts)} FX accounts)")
            if loan_trackers:
                sub_steps.append(f"✓ WCDL/BC/PQL tracker ({len(loan_trackers)} loans)")

            self.update_progress(
                job_id, "complete", "complete",
                "Analysis complete. Reports uploaded to R2.", 100,
                sub_steps=sub_steps,
                downloads={
                    "working_sheet":  ws_key,
                    "banking_report": br_key,
                    **(({"fx_sheet": fx_key}) if fx_path else {}),
                },
            )

            # ── Cleanup temp files ──────────────────────────────────────────
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            for p in filter(None, [ws_path, br_path, fx_path]):
                if os.path.exists(p):
                    os.remove(p)

            return {
                "success":          True,
                "jobId":            job_id,
                "workingSheetKey":  ws_key,
                "bankingReportKey": br_key,
                "fxSheetKey":       fx_key if fx_path else None,
                "count":            len(accounts_data),
                "fxCount":          len(fx_accounts),
                "loansProcessed":   len(loan_trackers),
                "daysInPeriod":     days_in_period,
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
