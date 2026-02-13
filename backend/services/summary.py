"""
Summary Service
Calculates monthly summaries and aggregations for reporting
"""

from typing import Dict, List, Any, Optional
from datetime import date
from sqlalchemy.orm import Session
from models import Transaction


def calculate_monthly_summary(session_id: str = None, db: Session = None, client_id: int = None) -> Dict[str, Any]:
    """
    Calculate monthly summary for all transactions in a session or by client
    
    Returns:
    {
        "months": [
            {
                "month": "2024-01",
                "total_income": 5000.00,
                "total_expenses": 3500.00,
                "net_balance": 1500.00,
                "categories": {
                    "Rent": 1500.00,
                    "Utilities": 250.00,
                    ...
                }
            },
            ...
        ],
        "overall": {
            "total_income": 15000.00,
            "total_expenses": 10500.00,
            "net_balance": 4500.00
        }
    }
    """
    
    # Fetch transactions - filter by session_id or client_id
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")
    
    transactions = query.order_by(Transaction.date).all()
    
    if not transactions:
        return {
            "months": [],
            "overall": {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_balance": 0.0
            }
        }
    
    # Group by month
    monthly_data: Dict[str, Dict[str, Any]] = {}
    
    for txn in transactions:
        # Create month key (YYYY-MM)
        month_key = txn.date.strftime("%Y-%m")
        
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                "month": month_key,
                "total_income": 0.0,
                "total_expenses": 0.0,
                "net_balance": 0.0,
                "categories": {}
            }
        
        month = monthly_data[month_key]
        
        # Categorize income vs expense
        if txn.amount >= 0:
            month["total_income"] += txn.amount
        else:
            month["total_expenses"] += abs(txn.amount)
        
        # Track by category
        if txn.category not in month["categories"]:
            month["categories"][txn.category] = 0.0
        
        # Store absolute value for categories (makes sense for reporting)
        month["categories"][txn.category] += abs(txn.amount)
        
        # Calculate net
        month["net_balance"] = month["total_income"] - month["total_expenses"]
    
    # Sort months chronologically
    sorted_months = sorted(monthly_data.items())
    months_list = [data for _, data in sorted_months]
    
    # Calculate overall totals
    overall_income = sum(m["total_income"] for m in months_list)
    overall_expenses = sum(m["total_expenses"] for m in months_list)
    overall_balance = overall_income - overall_expenses
    
    return {
        "months": months_list,
        "overall": {
            "total_income": overall_income,
            "total_expenses": overall_expenses,
            "net_balance": overall_balance
        }
    }


def get_category_summary(session_id: str = None, db: Session = None, client_id: int = None) -> Dict[str, float]:
    """
    Get total amounts by category across all transactions in a session or by client
    
    Returns:
        Dict of {category: total_amount}
    """
    
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")
    
    transactions = query.all()
    
    categories: Dict[str, float] = {}
    
    for txn in transactions:
        if txn.category not in categories:
            categories[txn.category] = 0.0
        
        categories[txn.category] += abs(txn.amount)
    
    # Sort by amount descending
    return dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))


def get_transactions_by_category(
    session_id: str,
    category: str,
    db: Session
) -> List[Dict[str, Any]]:
    """
    Get all transactions for a specific category
    """
    
    transactions = db.query(Transaction).filter(
        Transaction.session_id == session_id,
        Transaction.category == category
    ).order_by(Transaction.date.desc()).all()
    
    return [
        {
            "id": txn.id,
            "date": txn.date.isoformat(),
            "description": txn.description,
            "amount": txn.amount,
            "category": txn.category,
            "invoice_id": txn.invoice_id
        }
        for txn in transactions
    ]


# Excel Export Implementation
import os
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from models import TransactionMerchant


class ExcelExporter:
    """Generate accountant-ready Excel exports"""
    
    # Style definitions
    HEADER_FILL = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
    TOTAL_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    TOTAL_FONT = Font(bold=True, size=11)
    SUBTITLE_FILL = PatternFill(start_color="E7E6E6", end_color="E7E6E6", fill_type="solid")
    SUBTITLE_FONT = Font(bold=True, size=10)
    BORDER = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    @staticmethod
    def _get_merchant_for_transaction(transaction_id: int, db: Session) -> str:
        """Get merchant name for a transaction, or empty string if none"""
        merchant_record = db.query(TransactionMerchant).filter(
            TransactionMerchant.transaction_id == transaction_id
        ).first()
        return merchant_record.merchant if merchant_record and merchant_record.merchant else ""
    
    @staticmethod
    def _get_all_merchants(session_id: str, db: Session) -> Dict[str, Dict[str, Any]]:
        """
        Get all merchants with their transaction counts and total amounts
        Returns: {merchant_name: {total_amount, count, categories}}
        """
        transactions = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).all()
        
        merchants: Dict[str, Dict[str, Any]] = {}
        
        for txn in transactions:
            merchant = ExcelExporter._get_merchant_for_transaction(txn.id, db)
            if not merchant:
                merchant = "Unattributed"
            
            if merchant not in merchants:
                merchants[merchant] = {
                    "total_amount": 0.0,
                    "count": 0,
                    "categories": {}
                }
            
            merchants[merchant]["total_amount"] += abs(txn.amount)
            merchants[merchant]["count"] += 1
            
            cat = txn.category or "Uncategorized"
            if cat not in merchants[merchant]["categories"]:
                merchants[merchant]["categories"][cat] = 0
            merchants[merchant]["categories"][cat] += 1
        
        return merchants
    
    @staticmethod
    def export_transactions(session_id: Optional[str], db: Session, client_id: Optional[int] = None) -> BytesIO:
        """
        Export all transactions to Excel
        Clean, professional format suitable for accountants
        """
        
        # Fetch transactions based on session_id or client_id
        query = db.query(Transaction)
        if session_id:
            query = query.filter(Transaction.session_id == session_id)
        elif client_id:
            query = query.filter(Transaction.client_id == client_id)
        else:
            raise ValueError("Either session_id or client_id must be provided")
        
        transactions = query.order_by(Transaction.date).all()
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Transactions"
        
        # Set column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        
        # Headers
        headers = ["Date", "Description", "Amount", "Category"]
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = ExcelExporter.HEADER_FILL
            cell.font = ExcelExporter.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = ExcelExporter.BORDER
        
        # Data rows
        for row_num, txn in enumerate(transactions, 2):
            ws.cell(row=row_num, column=1).value = txn.date.isoformat()
            ws.cell(row=row_num, column=2).value = txn.description
            ws.cell(row=row_num, column=3).value = txn.amount
            ws.cell(row=row_num, column=4).value = txn.category
            
            # Format amount column as currency
            ws.cell(row=row_num, column=3).number_format = '#,##0.00'
            
            # Apply borders
            for col in range(1, 5):
                ws.cell(row=row_num, column=col).border = ExcelExporter.BORDER
                ws.cell(row=row_num, column=col).alignment = Alignment(horizontal="left")
        
        # Total row
        if transactions:
            total_row = len(transactions) + 2
            ws.cell(row=total_row, column=1).value = "TOTAL"
            ws.cell(row=total_row, column=1).font = ExcelExporter.TOTAL_FONT
            ws.cell(row=total_row, column=1).fill = ExcelExporter.TOTAL_FILL
            
            # Sum formula
            total_formula = f"=SUM(C2:C{total_row-1})"
            ws.cell(row=total_row, column=3).value = total_formula
            ws.cell(row=total_row, column=3).font = ExcelExporter.TOTAL_FONT
            ws.cell(row=total_row, column=3).fill = ExcelExporter.TOTAL_FILL
            ws.cell(row=total_row, column=3).number_format = '#,##0.00'
            
            for col in range(1, 5):
                ws.cell(row=total_row, column=col).border = ExcelExporter.BORDER
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def export_for_accountant(session_id: str, db: Session) -> BytesIO:
        """
        Create a comprehensive Excel export optimized for accountants.
        Includes:
        1. Executive Summary - Key metrics and KPIs
        2. Merchant Analysis - Top merchants, transaction counts
        3. Detailed Transactions - Full list with merchant data
        4. Category Summaries - Per-category breakdown with merchant details
        """
        
        # Fetch all data
        transactions = db.query(Transaction).filter(
            Transaction.session_id == session_id
        ).order_by(Transaction.date).all()
        
        if not transactions:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "No Data"
            ws['A1'] = "No transactions found for this session"
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            return output
        
        merchants = ExcelExporter._get_all_merchants(session_id, db)
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Executive Summary"
        
        # ===== SHEET 1: EXECUTIVE SUMMARY =====
        ws_summary.column_dimensions['A'].width = 25
        ws_summary.column_dimensions['B'].width = 18
        
        # Title
        ws_summary.merge_cells('A1:B1')
        title_cell = ws_summary['A1']
        title_cell.value = "EXECUTIVE SUMMARY"
        title_cell.font = Font(bold=True, size=14, color="FFFFFF")
        title_cell.fill = ExcelExporter.HEADER_FILL
        title_cell.alignment = Alignment(horizontal='center', vertical='center')
        ws_summary.row_dimensions[1].height = 25
        
        # Date range
        date_range = f"{transactions[0].date.isoformat()} to {transactions[-1].date.isoformat()}"
        ws_summary['A2'] = "Period:"
        ws_summary['B2'] = date_range
        ws_summary['A2'].font = Font(bold=True)
        
        row = 4
        
        # Key Metrics
        total_income = 0.0
        total_expenses = 0.0
        
        for t in transactions:
            if t.amount >= 0:
                total_income += t.amount
            else:
                total_expenses += abs(t.amount)
        
        net_balance = total_income - total_expenses
        
        ws_summary[f'A{row}'] = "KEY METRICS"
        ws_summary[f'A{row}'].font = ExcelExporter.SUBTITLE_FONT
        ws_summary[f'A{row}'].fill = ExcelExporter.SUBTITLE_FILL
        row += 1
        
        metrics = [
            ("Total Income", total_income),
            ("Total Expenses", total_expenses),
            ("Net Balance", net_balance),
            ("Transaction Count", len(transactions)),
            ("Unique Merchants", len(merchants)),
        ]
        
        for metric_name, metric_value in metrics:
            ws_summary[f'A{row}'] = metric_name
            ws_summary[f'B{row}'] = metric_value
            ws_summary[f'A{row}'].font = Font(bold=True)
            if isinstance(metric_value, float):
                ws_summary[f'B{row}'].number_format = '#,##0.00'
            row += 1
        
        row += 1
        
        # Category Breakdown - Split by Income and Expenses
        ws_summary[f'A{row}'] = "INCOME BY CATEGORY"
        ws_summary[f'A{row}'].font = ExcelExporter.SUBTITLE_FONT
        ws_summary[f'A{row}'].fill = ExcelExporter.SUBTITLE_FILL
        row += 1
        
        # Headers
        ws_summary[f'A{row}'] = "Category"
        ws_summary[f'B{row}'] = "Amount"
        for col in ['A', 'B']:
            ws_summary[f'{col}{row}'].fill = ExcelExporter.HEADER_FILL
            ws_summary[f'{col}{row}'].font = ExcelExporter.HEADER_FONT
        row += 1
        
        # Income categories (amount >= 0)
        income_cats: Dict[str, float] = {}
        for t in transactions:
            if t.amount >= 0:
                cat = t.category or "Uncategorized"
                income_cats[cat] = income_cats.get(cat, 0) + t.amount
        
        sorted_income = sorted(income_cats.items(), key=lambda x: x[1], reverse=True)
        income_row_start = row
        for cat, amount in sorted_income:
            ws_summary[f'A{row}'] = cat
            ws_summary[f'B{row}'] = amount
            ws_summary[f'B{row}'].number_format = '#,##0.00'
            row += 1
        
        # Income subtotal
        income_row_end = row - 1
        if sorted_income:
            ws_summary[f'A{row}'] = "Income Subtotal"
            ws_summary[f'A{row}'].font = ExcelExporter.TOTAL_FONT
            ws_summary[f'A{row}'].fill = ExcelExporter.TOTAL_FILL
            ws_summary[f'B{row}'] = f"=SUM(B{income_row_start}:B{income_row_end})"
            ws_summary[f'B{row}'].font = ExcelExporter.TOTAL_FONT
            ws_summary[f'B{row}'].fill = ExcelExporter.TOTAL_FILL
            ws_summary[f'B{row}'].number_format = '#,##0.00'
            row += 2
        
        # Expenses heading
        ws_summary[f'A{row}'] = "EXPENSES BY CATEGORY"
        ws_summary[f'A{row}'].font = ExcelExporter.SUBTITLE_FONT
        ws_summary[f'A{row}'].fill = ExcelExporter.SUBTITLE_FILL
        row += 1
        
        # Headers
        ws_summary[f'A{row}'] = "Category"
        ws_summary[f'B{row}'] = "Amount"
        for col in ['A', 'B']:
            ws_summary[f'{col}{row}'].fill = ExcelExporter.HEADER_FILL
            ws_summary[f'{col}{row}'].font = ExcelExporter.HEADER_FONT
        row += 1
        
        # Expense categories (amount < 0)
        expense_cats: Dict[str, float] = {}
        for t in transactions:
            if t.amount < 0:
                cat = t.category or "Uncategorized"
                expense_cats[cat] = expense_cats.get(cat, 0) + abs(t.amount)
        
        sorted_expenses = sorted(expense_cats.items(), key=lambda x: x[1], reverse=True)
        expense_row_start = row
        for cat, amount in sorted_expenses:
            ws_summary[f'A{row}'] = cat
            ws_summary[f'B{row}'] = amount
            ws_summary[f'B{row}'].number_format = '#,##0.00'
            row += 1
        
        # Expense subtotal
        expense_row_end = row - 1
        if sorted_expenses:
            ws_summary[f'A{row}'] = "Expense Subtotal"
            ws_summary[f'A{row}'].font = ExcelExporter.TOTAL_FONT
            ws_summary[f'A{row}'].fill = ExcelExporter.TOTAL_FILL
            ws_summary[f'B{row}'] = f"=SUM(B{expense_row_start}:B{expense_row_end})"
            ws_summary[f'B{row}'].font = ExcelExporter.TOTAL_FONT
            ws_summary[f'B{row}'].fill = ExcelExporter.TOTAL_FILL
            ws_summary[f'B{row}'].number_format = '#,##0.00'
            row += 2
        
        # NET BALANCE (the important one)
        ws_summary[f'A{row}'] = "NET BALANCE"
        ws_summary[f'A{row}'].font = Font(bold=True, size=12, color="FFFFFF")
        ws_summary[f'A{row}'].fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        ws_summary[f'B{row}'] = net_balance
        ws_summary[f'B{row}'].font = Font(bold=True, size=12, color="FFFFFF")
        ws_summary[f'B{row}'].fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
        ws_summary[f'B{row}'].number_format = '#,##0.00'
        
        # ===== SHEET 2: MERCHANT ANALYSIS =====
        ws_merchants = wb.create_sheet("Merchant Analysis")
        ws_merchants.column_dimensions['A'].width = 30
        ws_merchants.column_dimensions['B'].width = 15
        ws_merchants.column_dimensions['C'].width = 15
        ws_merchants.column_dimensions['D'].width = 20
        
        # Headers
        headers = ["Merchant", "Transaction Count", "Total Amount", "Avg Per Transaction"]
        for col_num, header in enumerate(headers, 1):
            cell = ws_merchants.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = ExcelExporter.HEADER_FILL
            cell.font = ExcelExporter.HEADER_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = ExcelExporter.BORDER
        
        # Sort merchants by total amount descending
        sorted_merchants = sorted(
            merchants.items(),
            key=lambda x: x[1]["total_amount"],
            reverse=True
        )
        
        for row_num, (merchant_name, data) in enumerate(sorted_merchants, 2):
            ws_merchants.cell(row=row_num, column=1).value = merchant_name
            ws_merchants.cell(row=row_num, column=2).value = data["count"]
            ws_merchants.cell(row=row_num, column=3).value = data["total_amount"]
            ws_merchants.cell(row=row_num, column=3).number_format = '#,##0.00'
            
            avg = data["total_amount"] / data["count"] if data["count"] > 0 else 0
            ws_merchants.cell(row=row_num, column=4).value = avg
            ws_merchants.cell(row=row_num, column=4).number_format = '#,##0.00'
            
            for col in range(1, 5):
                ws_merchants.cell(row=row_num, column=col).border = ExcelExporter.BORDER
        
        # ===== SHEET 3: DETAILED TRANSACTIONS =====
        ws_detail = wb.create_sheet("Transactions")
        ws_detail.column_dimensions['A'].width = 12
        ws_detail.column_dimensions['B'].width = 35
        ws_detail.column_dimensions['C'].width = 25
        ws_detail.column_dimensions['D'].width = 15
        ws_detail.column_dimensions['E'].width = 15
        
        # Headers
        headers = ["Date", "Description", "Merchant", "Amount", "Category"]
        for col_num, header in enumerate(headers, 1):
            cell = ws_detail.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = ExcelExporter.HEADER_FILL
            cell.font = ExcelExporter.HEADER_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = ExcelExporter.BORDER
        
        # Transaction rows
        for row_num, txn in enumerate(transactions, 2):
            merchant = ExcelExporter._get_merchant_for_transaction(txn.id, db) or ""
            
            ws_detail.cell(row=row_num, column=1).value = txn.date.isoformat()
            ws_detail.cell(row=row_num, column=2).value = txn.description
            ws_detail.cell(row=row_num, column=3).value = merchant
            ws_detail.cell(row=row_num, column=4).value = txn.amount
            ws_detail.cell(row=row_num, column=4).number_format = '#,##0.00'
            ws_detail.cell(row=row_num, column=5).value = txn.category or "Uncategorized"
            
            for col in range(1, 6):
                ws_detail.cell(row=row_num, column=col).border = ExcelExporter.BORDER
        
        # Total row for transactions
        if transactions:
            total_row = len(transactions) + 2
            ws_detail.cell(row=total_row, column=4).value = f"=SUM(D2:D{total_row-1})"
            ws_detail.cell(row=total_row, column=4).font = ExcelExporter.TOTAL_FONT
            ws_detail.cell(row=total_row, column=4).fill = ExcelExporter.TOTAL_FILL
            ws_detail.cell(row=total_row, column=4).number_format = '#,##0.00'
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def export_category_monthly(session_id: str, category: str, db: Session) -> BytesIO:
        """
        Export transactions for a single category across months.

        Structure: single workbook with one sheet named for the category.
        For each month include an opening balance (cumulative amount prior to month)
        then the transactions for that month with a running balance.
        """

        # Fetch transactions for this category
        txns = db.query(Transaction).filter(
            Transaction.session_id == session_id,
            Transaction.category == category
        ).order_by(Transaction.date).all()

        wb = openpyxl.Workbook()
        # sanitize sheet name (max 31 chars and remove Excel-invalid characters)
        sheet_name = ExcelExporter._sanitize_sheet_name(category)
        ws = wb.active
        ws.title = sheet_name

        # Header
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 40
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 18

        # Title
        ws.merge_cells('A1:D1')
        title_cell = ws.cell(row=1, column=1)
        title_cell.value = f"Category: {category}"
        title_cell.font = ExcelExporter.HEADER_FONT
        title_cell.fill = ExcelExporter.HEADER_FILL
        title_cell.alignment = Alignment(horizontal='left')

        # Start writing after title
        row = 3

        if not txns:
            ws.cell(row=row, column=1).value = "No transactions for this category"
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            return output

        # Group by month (YYYY-MM)
        months: Dict[str, List[Any]] = {}
        for t in txns:
            m = t.date.strftime("%Y-%m")
            months.setdefault(m, []).append(t)

        # Get sorted month keys
        month_keys = sorted(months.keys())

        # Precompute cumulative amounts prior to each month
        cumulative_before: Dict[str, float] = {}
        all_txns_by_month = []
        # Build list of (month, txns) in order
        for mk in month_keys:
            all_txns_by_month.append((mk, months[mk]))

        # compute cumulative sums
        for idx, (mk, mtxns) in enumerate(all_txns_by_month):
            # sum of amounts for all previous months
            prev_sum = 0.0
            for j in range(0, idx):
                for pt in all_txns_by_month[j][1]:
                    prev_sum += pt.amount
            cumulative_before[mk] = prev_sum

        # For each month write opening balance and rows
        for mk, mtxns in all_txns_by_month:
            # Month header
            ws.cell(row=row, column=1).value = mk
            ws.cell(row=row, column=1).font = ExcelExporter.HEADER_FONT
            ws.cell(row=row, column=1).fill = ExcelExporter.HEADER_FILL
            row += 1

            # Opening balance row
            ws.cell(row=row, column=1).value = "Opening balance"
            ws.cell(row=row, column=3).value = cumulative_before.get(mk, 0.0)
            ws.cell(row=row, column=3).number_format = '#,##0.00'
            row += 1

            # Table header for transactions
            headers = ["Date", "Description", "Amount", "Running Balance"]
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=row, column=col_num)
                cell.value = header
                cell.fill = ExcelExporter.HEADER_FILL
                cell.font = ExcelExporter.HEADER_FONT
                cell.alignment = Alignment(horizontal="center")
                cell.border = ExcelExporter.BORDER
            row += 1

            # Running balance starts at opening
            running = cumulative_before.get(mk, 0.0)
            for t in mtxns:
                ws.cell(row=row, column=1).value = t.date.isoformat()
                ws.cell(row=row, column=2).value = t.description
                ws.cell(row=row, column=3).value = t.amount
                ws.cell(row=row, column=3).number_format = '#,##0.00'
                running += t.amount
                ws.cell(row=row, column=4).value = running
                ws.cell(row=row, column=4).number_format = '#,##0.00'

                # apply borders
                for c in range(1, 5):
                    ws.cell(row=row, column=c).border = ExcelExporter.BORDER
                row += 1

            # blank row between months
            row += 1

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output

    @staticmethod
    def _sanitize_sheet_name(name: str) -> str:
        r"""
        Sanitize a category name for use as an Excel sheet name.
        Excel sheet names can't contain: : \ / ? * [ ]
        Max 31 characters.
        """
        # Remove invalid Excel sheet name characters
        invalid_chars = r'[\:\/\?\*\[\]]'
        import re
        sanitized = re.sub(invalid_chars, '', name)
        # Truncate to 31 chars
        return sanitized[:31]

    @staticmethod
    def export_all_categories_monthly(
        session_id: str,
        db: Session,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        include_vat: bool = False,
        selected_categories: Optional[List[str]] = None
    ) -> BytesIO:
        """
        Export all categories: one sheet per category with month sections.
        
        Parameters:
        - session_id: The session ID
        - db: Database session
        - date_from: Optional start date in YYYY-MM-DD format
        - date_to: Optional end date in YYYY-MM-DD format
        - include_vat: Whether to include VAT columns (Amount Incl VAT, VAT Amount, Amount Excl VAT)
        - selected_categories: Optional list of category names to export (None = all)
        """
        from datetime import datetime
        
        # Debug logging
        print(f"[EXPORT DEBUG] include_vat={include_vat}, type={type(include_vat).__name__}")
        
        # Build query with date filtering
        query = db.query(Transaction).filter(Transaction.session_id == session_id)
        
        if date_from:
            query = query.filter(Transaction.date >= datetime.strptime(date_from, "%Y-%m-%d").date())
        if date_to:
            query = query.filter(Transaction.date <= datetime.strptime(date_to, "%Y-%m-%d").date())
        
        transactions = query.order_by(Transaction.date).all()
        
        if not transactions:
            # Return empty workbook if no transactions
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "No Data"
            ws['A1'] = "No transactions found for this session"
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            return output
        
        # Group transactions by category
        categories_map: Dict[str, List[Any]] = {}
        for t in transactions:
            cat_name = t.category if t.category else 'Uncategorized'
            categories_map.setdefault(cat_name, []).append(t)
        
        print(f"[EXPORT DEBUG] Found {len(categories_map)} unique categories: {list(categories_map.keys())}")
        print(f"[EXPORT DEBUG] selected_categories filter: {selected_categories}")
        
        # Filter by selected categories if provided
        if selected_categories:
            categories_map = {k: v for k, v in categories_map.items() if k in selected_categories}
            print(f"[EXPORT DEBUG] After filtering: {len(categories_map)} categories: {list(categories_map.keys())}")
        else:
            print(f"[EXPORT DEBUG] No filter applied, exporting all {len(categories_map)} categories")

        wb = openpyxl.Workbook()
        first = True
        
        for category, txns in categories_map.items():
            # Sanitize category name for Excel sheet title
            sheet_name = ExcelExporter._sanitize_sheet_name(category)
            if first:
                ws = wb.active
                ws.title = sheet_name
                first = False
            else:
                ws = wb.create_sheet(title=sheet_name)

            # Set column widths based on whether VAT columns are included
            print(f"[EXPORT DEBUG] Sheet '{sheet_name}': include_vat={include_vat}, type={type(include_vat).__name__}")
            
            if include_vat:
                print(f"[EXPORT DEBUG] Adding VAT columns for sheet '{sheet_name}'")
                ws.column_dimensions['A'].width = 12  # Date
                ws.column_dimensions['B'].width = 40  # Description
                ws.column_dimensions['C'].width = 15  # Amount Incl VAT
                ws.column_dimensions['D'].width = 15  # VAT Amount
                ws.column_dimensions['E'].width = 15  # Amount Excl VAT
                ws.column_dimensions['F'].width = 18  # Running Balance
                merge_range = 'A1:F1'
                num_cols = 6
            else:
                print(f"[EXPORT DEBUG] Using standard columns (no VAT) for sheet '{sheet_name}'")
                ws.column_dimensions['A'].width = 12  # Date
                ws.column_dimensions['B'].width = 40  # Description
                ws.column_dimensions['C'].width = 15  # Amount
                ws.column_dimensions['D'].width = 18  # Running Balance
                merge_range = 'A1:D1'
                num_cols = 4

            # Category header
            ws.merge_cells(merge_range)
            ws.cell(row=1, column=1).value = f"Category: {category}"
            ws.cell(row=1, column=1).font = ExcelExporter.HEADER_FONT
            ws.cell(row=1, column=1).fill = ExcelExporter.HEADER_FILL

            row = 3

            # Group transactions by month
            months: Dict[str, List[Any]] = {}
            for t in txns:
                m = t.date.strftime("%Y-%m")
                months.setdefault(m, []).append(t)

            month_keys = sorted(months.keys())
            all_txns_by_month = [(mk, months[mk]) for mk in month_keys]

            # Process each month
            for idx, (mk, mtxns) in enumerate(all_txns_by_month):
                # Calculate opening balance
                prev_sum = 0.0
                for j in range(0, idx):
                    for pt in all_txns_by_month[j][1]:
                        prev_sum += pt.amount

                # Month header
                ws.cell(row=row, column=1).value = mk
                ws.cell(row=row, column=1).font = ExcelExporter.HEADER_FONT
                ws.cell(row=row, column=1).fill = ExcelExporter.HEADER_FILL
                row += 1

                # Opening balance row
                ws.cell(row=row, column=1).value = "Opening balance"
                balance_col = num_cols  # Last column
                ws.cell(row=row, column=balance_col).value = prev_sum
                ws.cell(row=row, column=balance_col).number_format = '#,##0.00'
                row += 1

                # Column headers
                if include_vat:
                    headers = ["Date", "Description", "Amount (Incl VAT)", "VAT Amount", "Amount (Excl VAT)", "Running Balance"]
                    print(f"[EXPORT DEBUG] Adding VAT headers: {headers}")
                else:
                    headers = ["Date", "Description", "Amount", "Running Balance"]
                    print(f"[EXPORT DEBUG] Adding standard headers: {headers}")
                
                for col_num, header in enumerate(headers, 1):
                    cell = ws.cell(row=row, column=col_num)
                    cell.value = header
                    cell.fill = ExcelExporter.HEADER_FILL
                    cell.font = ExcelExporter.HEADER_FONT
                    cell.alignment = Alignment(horizontal="center")
                    cell.border = ExcelExporter.BORDER
                row += 1

                # Transaction rows
                running = prev_sum
                row_count = 0
                for t in mtxns:
                    ws.cell(row=row, column=1).value = t.date.isoformat()
                    ws.cell(row=row, column=2).value = t.description
                    
                    if row_count == 0:
                        print(f"[EXPORT DEBUG] Processing first transaction in month {mk}: include_vat={include_vat}")
                    
                    if include_vat:
                        # Calculate VAT components
                        vat_rate = 0.15  # 15% South African VAT
                        vat_amount = t.vat_amount if t.vat_amount is not None else 0.0
                        amount_incl_vat = t.amount
                        amount_excl_vat = amount_incl_vat - vat_amount
                        
                        if row_count == 0:
                            print(f"[EXPORT DEBUG] Writing VAT columns: incl={amount_incl_vat}, vat={vat_amount}, excl={amount_excl_vat}")
                        
                        ws.cell(row=row, column=3).value = amount_incl_vat
                        ws.cell(row=row, column=3).number_format = '#,##0.00'
                        
                        ws.cell(row=row, column=4).value = vat_amount
                        ws.cell(row=row, column=4).number_format = '#,##0.00'
                        
                        ws.cell(row=row, column=5).value = amount_excl_vat
                        ws.cell(row=row, column=5).number_format = '#,##0.00'
                        
                        running += t.amount
                        ws.cell(row=row, column=6).value = running
                        ws.cell(row=row, column=6).number_format = '#,##0.00'
                    else:
                        if row_count == 0:
                            print(f"[EXPORT DEBUG] Writing standard columns (no VAT)")
                        
                        ws.cell(row=row, column=3).value = t.amount
                        ws.cell(row=row, column=3).number_format = '#,##0.00'
                        
                        running += t.amount
                        ws.cell(row=row, column=4).value = running
                        ws.cell(row=row, column=4).number_format = '#,##0.00'
                    
                    # Apply borders to all cells in the row
                    for c in range(1, num_cols + 1):
                        ws.cell(row=row, column=c).border = ExcelExporter.BORDER
                    row += 1
                    row_count += 1

                row += 1  # Space between months

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
    
    @staticmethod
    def export_monthly_summary(summary_data: Dict[str, Any]) -> BytesIO:
        """
        Export monthly summary to Excel
        Multi-sheet: Overview + Category Details
        """
        
        wb = openpyxl.Workbook()
        
        # ===== SHEET 1: Monthly Overview =====
        ws_overview = wb.active
        ws_overview.title = "Monthly Summary"
        
        # Column widths
        ws_overview.column_dimensions['A'].width = 12
        ws_overview.column_dimensions['B'].width = 15
        ws_overview.column_dimensions['C'].width = 15
        ws_overview.column_dimensions['D'].width = 15
        
        # Headers
        headers = ["Month", "Total Income", "Total Expenses", "Net Balance"]
        for col_num, header in enumerate(headers, 1):
            cell = ws_overview.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = ExcelExporter.HEADER_FILL
            cell.font = ExcelExporter.HEADER_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = ExcelExporter.BORDER
        
        # Data rows
        months = summary_data.get("months", [])
        for row_num, month in enumerate(months, 2):
            ws_overview.cell(row=row_num, column=1).value = month["month"]
            ws_overview.cell(row=row_num, column=2).value = month["total_income"]
            ws_overview.cell(row=row_num, column=3).value = month["total_expenses"]
            ws_overview.cell(row=row_num, column=4).value = month["net_balance"]
            
            for col in range(1, 5):
                cell = ws_overview.cell(row=row_num, column=col)
                cell.border = ExcelExporter.BORDER
                if col > 1:
                    cell.number_format = '#,##0.00'
        
        # Overall totals
        if months:
            total_row = len(months) + 2
            overall = summary_data.get("overall", {})
            
            ws_overview.cell(row=total_row, column=1).value = "OVERALL"
            ws_overview.cell(row=total_row, column=2).value = overall.get("total_income", 0)
            ws_overview.cell(row=total_row, column=3).value = overall.get("total_expenses", 0)
            ws_overview.cell(row=total_row, column=4).value = overall.get("net_balance", 0)
            
            for col in range(1, 5):
                cell = ws_overview.cell(row=total_row, column=col)
                cell.fill = ExcelExporter.TOTAL_FILL
                cell.font = ExcelExporter.TOTAL_FONT
                cell.border = ExcelExporter.BORDER
                if col > 1:
                    cell.number_format = '#,##0.00'
        
        # ===== SHEET 2: Category Breakdown =====
        ws_categories = wb.create_sheet("Category Breakdown")
        ws_categories.column_dimensions['A'].width = 20
        ws_categories.column_dimensions['B'].width = 15
        
        # Headers
        for col_num, header in enumerate(["Category", "Total Amount"], 1):
            cell = ws_categories.cell(row=1, column=col_num)
            cell.value = header
            cell.fill = ExcelExporter.HEADER_FILL
            cell.font = ExcelExporter.HEADER_FONT
            cell.alignment = Alignment(horizontal="center")
            cell.border = ExcelExporter.BORDER
        
        # Aggregate categories across all months
        all_categories: Dict[str, float] = {}
        for month in months:
            for category, amount in month.get("categories", {}).items():
                if category not in all_categories:
                    all_categories[category] = 0
                all_categories[category] += amount
        
        # Sort by amount descending
        sorted_cats = sorted(all_categories.items(), key=lambda x: x[1], reverse=True)
        
        # Data rows
        for row_num, (category, amount) in enumerate(sorted_cats, 2):
            ws_categories.cell(row=row_num, column=1).value = category
            ws_categories.cell(row=row_num, column=2).value = amount
            ws_categories.cell(row=row_num, column=2).number_format = '#,##0.00'
            
            for col in range(1, 3):
                ws_categories.cell(row=row_num, column=col).border = ExcelExporter.BORDER
        
        # Total row
        if all_categories:
            total_row = len(all_categories) + 2
            ws_categories.cell(row=total_row, column=1).value = "TOTAL"
            ws_categories.cell(row=total_row, column=1).font = ExcelExporter.TOTAL_FONT
            ws_categories.cell(row=total_row, column=1).fill = ExcelExporter.TOTAL_FILL
            
            total_formula = f"=SUM(B2:B{total_row-1})"
            ws_categories.cell(row=total_row, column=2).value = total_formula
            ws_categories.cell(row=total_row, column=2).font = ExcelExporter.TOTAL_FONT
            ws_categories.cell(row=total_row, column=2).fill = ExcelExporter.TOTAL_FILL
            ws_categories.cell(row=total_row, column=2).number_format = '#,##0.00'
            
            for col in range(1, 3):
                ws_categories.cell(row=total_row, column=col).border = ExcelExporter.BORDER
        
        # Save to bytes
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return output
