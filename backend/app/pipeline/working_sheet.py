import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border
from datetime import datetime, timedelta
import calendar
import os
from .engine import FinCoreComputationEngine

def generate_working_sheet(
    accounts_data: list,
    wcdl_data: list,
    computed: dict,
    job_id: str,
    period: str
) -> str:
    wb = openpyxl.Workbook()
    wb.remove(wb.active) # Remove default sheet
    
    for account in accounts_data:
        acct_no = str(account.get("account_number", "UNKNOWN"))
        bank = account.get("bank_name", "UNKNOWN").upper()
        acct_type = account.get("account_type", "CC").upper()
        
        # Exact naming from plan: HDFC-521 CC AC
        tab_name = f"{bank.split()[0]}-{acct_no[-3:]} {acct_type} AC"
        ws = wb.create_sheet(tab_name)
        
        # Row 1: Header - HDFC - 521 CC Account + From 01-02-2026 to 28-02-2026
        period_from = account.get("period_from", "N/A")
        period_to = account.get("period_to", "N/A")
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=13)
        header_cell = ws.cell(row=1, column=1)
        header_cell.value = f"{bank} - {acct_no[-3:]} {acct_type} Account | From {period_from} to {period_to}"
        header_cell.font = Font(bold=True, size=12)
        header_cell.alignment = Alignment(horizontal="center")

        # Row 3: Columns
        headers = [
            "Date", "Narration", "Ref No", "Withdrawal", "Deposit", 
            "Positive Bal", "No. of Days", "CC", "WCDL", 
            "Buyers Credit", "Pre-Qualified Loan", "Total Utilisation",
            "Daily Interest"
        ]
        
        header_fill = PatternFill(fill_type="solid", fgColor="0A0A0F")
        header_font = Font(bold=True, color="FFFFFF")
        
        for col, title in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col)
            cell.value = title
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Transactions expansion
        txns = account.get("transactions", [])
        start_date = account.get("period_from")
        end_date = account.get("period_to")
        open_bal = account.get("opening_balance", 0)
        
        full_month_txns = _expand_to_full_month(txns, start_date, end_date, open_bal)
        account["full_month_transactions"] = full_month_txns 

        roi = account.get("cc_roi_percent") or 7.60
        
        for i, txn in enumerate(full_month_txns):
            row_idx = i + 4
            bal = float(txn.get("closing_balance", 0))
            
            # Date, Narration, Ref, W/D
            ws.cell(row=row_idx, column=1).value = txn.get("date")
            ws.cell(row=row_idx, column=2).value = txn.get("narration")
            ws.cell(row=row_idx, column=3).value = txn.get("ref_number")
            
            # Numeric columns
            wd_cell = ws.cell(row=row_idx, column=4)
            wd_cell.value = txn.get("withdrawal")
            wd_cell.number_format = '#,##0.00'
            
            dep_cell = ws.cell(row=row_idx, column=5)
            dep_cell.value = txn.get("deposit")
            dep_cell.number_format = '#,##0.00'
            
            # Logic: If balance is CR (positive) -> Positive Bal = value, No. of Days = 1, CC = 0
            pos_bal_cell = ws.cell(row=row_idx, column=6)
            cc_cell = ws.cell(row=row_idx, column=8)
            num_days_cell = ws.cell(row=row_idx, column=7)
            
            if bal >= 0:
                pos_bal_cell.value = bal
                num_days_cell.value = 1
                cc_cell.value = 0
            else:
                pos_bal_cell.value = ""
                num_days_cell.value = ""
                cc_cell.value = abs(bal)
            
            pos_bal_cell.number_format = '#,##0.00'
            cc_cell.number_format = '#,##0.00'
                
            # WCDL: Hardcoded formula from plan
            wcdl_cell = ws.cell(row=row_idx, column=9)
            wcdl_cell.value = 550000000 
            wcdl_cell.number_format = '#,##0.00'
            
            # Buyers Credit / Pre-Qualified (Placeholders)
            bc_cell = ws.cell(row=row_idx, column=10)
            bc_cell.value = 0
            bc_cell.number_format = '#,##0.00'
            
            pq_cell = ws.cell(row=row_idx, column=11)
            pq_cell.value = 0
            pq_cell.number_format = '#,##0.00'
            
            # Total Utilisation: =CC+WCDL+Buyers Credit+Pre-Qualified Loan
            total_util_cell = ws.cell(row=row_idx, column=12)
            total_util_cell.value = f"=H{row_idx}+I{row_idx}+J{row_idx}+K{row_idx}"
            total_util_cell.number_format = '#,##0.00'
            
            # Daily Interest: =(Total Utilisation * ROI / 100) / 365
            daily_int_cell = ws.cell(row=row_idx, column=13)
            daily_int_cell.value = f"=(L{row_idx}*{roi}/100)/365"
            daily_int_cell.number_format = '#,##0.00'
            
        # Summary row
        last_row = len(full_month_txns) + 4
        ws.cell(row=last_row, column=1).value = "TOTAL"
        ws.cell(row=last_row, column=1).font = Font(bold=True)
        
        # Sum of CC, WCDL, Total Util, Daily Int
        for col_letter in ['H', 'I', 'L', 'M']:
            col_idx = ord(col_letter) - ord('A') + 1
            sum_cell = ws.cell(row=last_row, column=col_idx)
            sum_cell.value = f"=SUM({col_letter}4:{col_letter}{last_row-1})"
            sum_cell.font = Font(bold=True)
            sum_cell.number_format = '#,##0.00'
            
        # Avg Utilisation Row
        avg_row = last_row + 1
        ws.cell(row=avg_row, column=1).value = "AVG. UTILISATION"
        ws.cell(row=avg_row, column=1).font = Font(bold=True)
        avg_cell = ws.cell(row=avg_row, column=12)
        avg_cell.value = f"=AVERAGE(L4:L{last_row-1})"
        avg_cell.font = Font(bold=True)
        avg_cell.number_format = '#,##0.00'

    # Set Column Widths (Aesthetics)
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 40
    for col in range(4, 14):
        col_letter = openpyxl.utils.get_column_letter(col)
        ws.column_dimensions[col_letter].width = 18

    # Save file
    storage_dir = "./storage/working_sheets"
    os.makedirs(storage_dir, exist_ok=True)
    date_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{date_prefix}_workingsheet.xlsx"
    filepath = os.path.join(storage_dir, filename)
    wb.save(filepath)
    
    return filepath

def _expand_to_full_month(transactions, start_str, end_str, open_bal):
    """ Ensures every day of the calendar period is present. """
    if not start_str or not end_str:
        return transactions # Fallback

    try:
        start_date = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
        end_date = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
    except:
        return transactions

    # Group existing txns by date
    from collections import defaultdict
    txns_by_date = defaultdict(list)
    for t in transactions:
        try:
            d_str = t.get("date", "")[:10]
            if "-" in d_str:
                dt = datetime.strptime(d_str, "%Y-%m-%d").date()
            else:
                dt = datetime.strptime(d_str, "%d/%m/%Y").date()
            txns_by_date[dt].append(t)
        except: continue

    expanded = []
    current_bal = open_bal
    
    curr = start_date
    while curr <= end_date:
        day_txns = txns_by_date.get(curr, [])
        if day_txns:
            for t in day_txns:
                t["real"] = True
                expanded.append(t)
                current_bal = t.get("closing_balance", current_bal)
        else:
            # Carry forward
            expanded.append({
                "date": curr.strftime("%Y-%m-%d"),
                "narration": "CARRY FORWARD BALANCE",
                "ref_number": "-",
                "withdrawal": 0,
                "deposit": 0,
                "closing_balance": current_bal,
                "category": "INTERNAL",
                "real": False
            })
        curr += timedelta(days=1)
        
    return expanded

def _populate_shared_tab(ws, data, title):
    """ Simple aggregation for Charges, Interest, etc. """
    ws.cell(1, 1).value = title
    ws.cell(1, 1).font = Font(bold=True, size=12)
    
    headers = ["Date", "Account", "Particulars", "Amount", "Dr/Cr"]
    for col, h in enumerate(headers, 1):
        ws.cell(3, col).value = h
        ws.cell(3, col).font = Font(bold=True)
        
    for row_idx, item in enumerate(data, 4):
        amt = item.get("withdrawal") or item.get("deposit") or 0
        flag = "Dr" if item.get("withdrawal") else "Cr"
        
        ws.cell(row_idx, 1).value = item.get("date")
        ws.cell(row_idx, 2).value = item.get("acct")
        ws.cell(row_idx, 3).value = item.get("narration")
        ws.cell(row_idx, 4).value = amt
        ws.cell(row_idx, 5).value = flag

def _populate_wcdl_tracker(ws, wcdl_data, engine):
    headers = [
        "Loan Number", "Drawdown Date",
        "Maturity Date", "ROI %",
        "Principal", "Tenure Days",
        "Prepayment Date", "Actual Tenure",
        "Computed Interest", "Bank Charged",
        "Difference", "Status"
    ]
    
    header_fill = PatternFill(fill_type="solid", fgColor="BCF0F0")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.fill = header_fill
    
    for row_idx, loan in enumerate(wcdl_data, 2):
        computed = engine.compute_wcdl_interest(
            loan.get("principal", 0),
            loan.get("roi_percent", 0),
            loan.get("tenure_days", 0)
        )
        
        bank_charged = loan.get("bank_charged_interest", computed)
        difference = computed - bank_charged
        status = "✓ MATCH" if abs(difference) <= 1 else "⚠ FLAG"
        
        row_data = [
            loan.get("loan_number", "WCDL-TXN"),
            loan.get("date", ""),
            loan.get("maturity_date", ""),
            loan.get("roi_percent", 0),
            loan.get("principal", 0),
            loan.get("tenure_days", 0),
            loan.get("prepayment_date", ""),
            loan.get("actual_tenure", loan.get("tenure_days", 0)),
            computed,
            bank_charged,
            round(difference, 2),
            status
        ]
        
        for col, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col).value = value

def _populate_summary_dashboard(ws, computed, period, account_count):
    # Snapshot of the analytics
    ws.cell(1, 1).value = f"Financial Summary — {period}"
    ws.cell(1, 1).font = Font(size=14, bold=True)
    
    kpis = [
        ("Accounts Processed", account_count),
        ("Average Utilization", computed.get("average_utilisation", 0)),
        ("Total Interest (CC + WCDL)", computed.get("total_interest", 0)),
        ("Finance Cost (%)", f"{computed.get('finance_cost_pct', 0):.2f}%"),
        ("ROI Status", computed.get("roi_status", "Checking...")),
    ]
    
    for idx, (label, value) in enumerate(kpis, 3):
        ws.cell(idx, 1).value = label
        ws.cell(idx, 2).value = value
        ws.cell(idx, 1).font = Font(bold=True)
        
    # Styling
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 20
