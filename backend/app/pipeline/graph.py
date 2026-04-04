"""
LangGraph StateGraph definition + edges.
Main pipeline controller — implements the three-stage flow.

Flow:
  PENDING -> STAGE1_RUNNING -> [STAGE1_REVIEW] -> STAGE2_RUNNING ->
  STAGE3_RUNNING -> [VALIDATION_FAILED] -> AWAITING_APPROVAL -> APPROVED
"""

import os
import json
import calendar
import tempfile
from datetime import date

from app.services.s3_service import get_storage
from app.core.database import (
    update_pipeline_status,
    update_pipeline_s3_key,
    execute_query,
)
from app.ocr.classifier import classify_pdf, AccountMeta
from app.ocr.base_agent import extract_pdf
from app.services.forex_rate_service import fetch_rates_for_period
from app.excel.statement_builder import build_statement_excel
from app.excel.working_sheet.builder import generate_working_sheet
from app.excel.banking_report.builder import generate_banking_report
from app.services.validation_service import run_all_validations

storage = get_storage()


async def run_pipeline(run_id: str, pdf_s3_keys: list[str], org_id: str, month: str):
    """Main pipeline entry point. month format: '2026-02'"""
    try:
        update_pipeline_status(run_id, "STAGE1_RUNNING", stage=1)

        extracted = {}
        account_registry = []
        low_confidence_fields = []

        with tempfile.TemporaryDirectory() as tmpdir:
            for s3_key in pdf_s3_keys:
                local_path = os.path.join(tmpdir, s3_key.split("/")[-1])
                storage.download_file(s3_key, local_path)

                meta = classify_pdf(local_path, s3_key.split("/")[-1])
                account_registry.append(meta.to_dict())

                result = extract_pdf(local_path, {
                    "account_type": meta.account_type,
                    "account_id": meta.account_id,
                })

                if result.get("overall_confidence", 1.0) < 0.95:
                    low_confidence_fields.append({
                        "file": s3_key,
                        "account": meta.account_label,
                        "account_id": meta.account_id,
                        "confidence": result["overall_confidence"],
                    })

                extracted[meta.account_id] = result

            account_registry = _deduplicate_registry(account_registry)

            if low_confidence_fields:
                update_pipeline_status(
                    run_id, "STAGE1_REVIEW", stage=1,
                    metadata={
                        "review_required": low_confidence_fields,
                        "account_registry": account_registry,
                    },
                )
                _save_extracted_data(run_id, extracted, account_registry, tmpdir)
                return

            year, mo = int(month[:4]), int(month[5:7])
            from_date = date(year, mo, 1)
            last_day = calendar.monthrange(year, mo)[1]
            to_date = date(year, mo, last_day)
            forex_rates = await fetch_rates_for_period(from_date, to_date)

            stmt_path = os.path.join(tmpdir, f"statement_{month}.xlsx")
            build_statement_excel(
                extracted, forex_rates, stmt_path,
                account_registry=account_registry,
            )

            stmt_key = f"outputs/{org_id}/{year}/{mo:02d}/statement_excel.xlsx"
            storage.upload_file(stmt_path, stmt_key)
            update_pipeline_s3_key(run_id, "statementExcelKey", stmt_key)

            # ── STAGE 2
            update_pipeline_status(run_id, "STAGE2_RUNNING", stage=2)

            wcdl_loans = _collect_wcdl_loans(extracted, account_registry)

            ws_path = os.path.join(tmpdir, f"working_sheet_{month}.xlsx")
            generate_working_sheet(
                stmt_path, forex_rates, wcdl_loans, ws_path,
                account_registry=account_registry,
            )

            ws_key = f"outputs/{org_id}/{year}/{mo:02d}/working_sheet.xlsx"
            storage.upload_file(ws_path, ws_key)
            update_pipeline_s3_key(run_id, "workingSheetKey", ws_key)

            # ── STAGE 3
            update_pipeline_status(run_id, "STAGE3_RUNNING", stage=3)

            rpt_path = os.path.join(tmpdir, f"banking_report_{month}.xlsx")
            generate_banking_report(ws_path, forex_rates, {}, rpt_path)

            rpt_key = f"outputs/{org_id}/{year}/{mo:02d}/banking_report.xlsx"
            storage.upload_file(rpt_path, rpt_key)
            update_pipeline_s3_key(run_id, "bankingReportKey", rpt_key)

            # ── VALIDATION
            from app.services.validation_service import (
                extract_computed_values_from_ws,
                extract_bank_stated_from_stmt,
            )
            validation = run_all_validations(
                computed_values=extract_computed_values_from_ws(ws_path),
                bank_stated_values=extract_bank_stated_from_stmt(stmt_path),
            )

            update_pipeline_status(
                run_id,
                "VALIDATION_FAILED" if validation["blocked"] else "AWAITING_APPROVAL",
                stage=3 if validation["blocked"] else 4,
                metadata=validation,
            )

    except Exception as e:
        update_pipeline_status(run_id, "FAILED", error=str(e))
        raise


async def resume_pipeline_from_stage2(run_id: str):
    """Resume pipeline after Stage 1 review confirmation."""
    rows = execute_query(
        'SELECT "orgId", "statementMonth", "statementExcelKey" FROM "PipelineRun" WHERE id = %s',
        (run_id,),
    )
    if not rows:
        raise ValueError(f"Run {run_id} not found")

    run = rows[0]
    org_id = run["orgId"]
    month = run["statementMonth"]

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            account_registry = _load_account_registry(run_id, tmpdir)
            extracted = _load_extracted_data(run_id, tmpdir)

            year, mo = int(month[:4]), int(month[5:7])
            from_date = date(year, mo, 1)
            last_day = calendar.monthrange(year, mo)[1]
            to_date = date(year, mo, last_day)
            forex_rates = await fetch_rates_for_period(from_date, to_date)

            stmt_path = os.path.join(tmpdir, f"statement_{month}.xlsx")
            stmt_key = run.get("statementExcelKey")

            if stmt_key and storage.file_exists(stmt_key):
                storage.download_file(stmt_key, stmt_path)
            else:
                update_pipeline_status(run_id, "STAGE1_RUNNING", stage=1)
                build_statement_excel(extracted, forex_rates, stmt_path,
                                      account_registry=account_registry)
                stmt_key = f"outputs/{org_id}/{year}/{mo:02d}/statement_excel.xlsx"
                storage.upload_file(stmt_path, stmt_key)
                update_pipeline_s3_key(run_id, "statementExcelKey", stmt_key)

            # ── STAGE 2
            update_pipeline_status(run_id, "STAGE2_RUNNING", stage=2)
            wcdl_loans = _collect_wcdl_loans(extracted, account_registry)
            ws_path = os.path.join(tmpdir, f"working_sheet_{month}.xlsx")
            generate_working_sheet(stmt_path, forex_rates, wcdl_loans, ws_path,
                                   account_registry=account_registry)
            ws_key = f"outputs/{org_id}/{year}/{mo:02d}/working_sheet.xlsx"
            storage.upload_file(ws_path, ws_key)
            update_pipeline_s3_key(run_id, "workingSheetKey", ws_key)

            # ── STAGE 3
            update_pipeline_status(run_id, "STAGE3_RUNNING", stage=3)
            rpt_path = os.path.join(tmpdir, f"banking_report_{month}.xlsx")
            generate_banking_report(ws_path, forex_rates, {}, rpt_path)
            rpt_key = f"outputs/{org_id}/{year}/{mo:02d}/banking_report.xlsx"
            storage.upload_file(rpt_path, rpt_key)
            update_pipeline_s3_key(run_id, "bankingReportKey", rpt_key)

            # ── VALIDATION
            from app.services.validation_service import (
                extract_computed_values_from_ws,
                extract_bank_stated_from_stmt,
            )
            validation = run_all_validations(
                computed_values=extract_computed_values_from_ws(ws_path),
                bank_stated_values=extract_bank_stated_from_stmt(stmt_path),
            )
            update_pipeline_status(
                run_id,
                "VALIDATION_FAILED" if validation["blocked"] else "AWAITING_APPROVAL",
                stage=3 if validation["blocked"] else 4,
                metadata=validation,
            )

    except Exception as e:
        update_pipeline_status(run_id, "FAILED", error=str(e))
        raise


# ── Helpers ───────────────────────────────────────────────────────────────────

def _deduplicate_registry(registry: list[dict]) -> list[dict]:
    seen = {}
    for r in registry:
        aid = r["account_id"]
        if aid not in seen or r.get("confidence", 0) > seen[aid].get("confidence", 0):
            seen[aid] = r
    return list(seen.values())


def _collect_wcdl_loans(extracted: dict, registry: list[dict]) -> list:
    loans = []
    for reg in registry:
        if reg.get("account_type") == "WCDL":
            acct_data = extracted.get(reg["account_id"], {})
            loans.extend(acct_data.get("loans", []))
    return loans


def _save_extracted_data(run_id, extracted, account_registry, tmpdir):
    data_path = os.path.join(tmpdir, f"extracted_{run_id}.json")
    with open(data_path, "w") as f:
        json.dump({"extracted": extracted, "account_registry": account_registry}, f, default=str)
    storage.upload_file(data_path, f"temp/{run_id}/extracted.json")


def _load_account_registry(run_id, tmpdir):
    try:
        data_path = os.path.join(tmpdir, f"registry_{run_id}.json")
        storage.download_file(f"temp/{run_id}/extracted.json", data_path)
        with open(data_path, "r") as f:
            return json.load(f).get("account_registry", [])
    except Exception:
        return []


def _load_extracted_data(run_id, tmpdir):
    try:
        data_path = os.path.join(tmpdir, f"extracted_{run_id}.json")
        storage.download_file(f"temp/{run_id}/extracted.json", data_path)
        with open(data_path, "r") as f:
            return json.load(f).get("extracted", {})
    except Exception:
        return {}
