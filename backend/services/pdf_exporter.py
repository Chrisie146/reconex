"""
PDF Export Service
Generates branded, accountant-ready PDF reports using reportlab.
"""

from io import BytesIO
from typing import Dict, List, Any, Optional
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from sqlalchemy.orm import Session
from models import Transaction, TransactionMerchant


# ── Brand colours ───────────────────────────────────────────────────
INDIGO_DARK = colors.HexColor("#3730A3")
INDIGO_MID = colors.HexColor("#4F46E5")
INDIGO_LIGHT = colors.HexColor("#E0E7FF")
INDIGO_PALE = colors.HexColor("#EEF2FF")
GREEN_DARK = colors.HexColor("#065F46")
GREEN_BG = colors.HexColor("#D1FAE5")
RED_DARK = colors.HexColor("#991B1B")
RED_BG = colors.HexColor("#FEE2E2")
NEUTRAL_100 = colors.HexColor("#F5F5F5")
NEUTRAL_200 = colors.HexColor("#E5E5E5")
NEUTRAL_700 = colors.HexColor("#404040")
WHITE = colors.white


def _fmt_currency(val: float) -> str:
    """Format a value as ZAR currency."""
    if val is None:
        return "R 0.00"
    sign = "-" if val < 0 else ""
    return f"{sign}R {abs(val):,.2f}"


def _build_styles():
    """Build reusable paragraph styles."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "BrandTitle", parent=styles["Title"],
        fontSize=18, textColor=INDIGO_DARK, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "SectionHeader", parent=styles["Heading2"],
        fontSize=13, textColor=INDIGO_MID, spaceBefore=14, spaceAfter=6,
        borderWidth=0, borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        "SubHeader", parent=styles["Heading3"],
        fontSize=11, textColor=NEUTRAL_700, spaceBefore=10, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "BodySmall", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=NEUTRAL_700,
    ))
    styles.add(ParagraphStyle(
        "FooterStyle", parent=styles["Normal"],
        fontSize=7, textColor=colors.HexColor("#9CA3AF"), alignment=TA_CENTER,
    ))
    return styles


def _header_footer(canvas, doc):
    """Draw page header and footer on every page."""
    canvas.saveState()
    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#9CA3AF"))
    canvas.drawCentredString(
        doc.pagesize[0] / 2, 12 * mm,
        f"Reconex  |  Generated {date.today().isoformat()}  |  Page {doc.page}"
    )
    # Top accent line
    canvas.setStrokeColor(INDIGO_MID)
    canvas.setLineWidth(2)
    canvas.line(doc.leftMargin, doc.pagesize[1] - 12 * mm,
                doc.pagesize[0] - doc.rightMargin, doc.pagesize[1] - 12 * mm)
    canvas.restoreState()


def _make_table(headers: List[str], rows: List[list], col_widths=None) -> Table:
    """Build a styled Table with branded colours."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, NEUTRAL_200),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    # Alternating row stripes
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), INDIGO_PALE))
    t.setStyle(TableStyle(style))
    return t


# ═════════════════════════════════════════════════════════════════════
#  PDF: EXECUTIVE SUMMARY
# ═════════════════════════════════════════════════════════════════════

def export_executive_summary_pdf(
    session_id: Optional[str],
    db: Session,
    client_id: Optional[int] = None,
    include_vat: bool = False,
    client_name: Optional[str] = None,
) -> BytesIO:
    """Generate branded executive-summary PDF (landscape, with full reconciliation table)."""
    from services.summary import calculate_monthly_summary
    from models import Reconciliation, OverallReconciliation

    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()
    summary = calculate_monthly_summary(session_id=session_id, db=db, client_id=client_id)

    # ── Load reconciliation records ────────────────────────────────
    recon_query = db.query(Reconciliation)
    if session_id:
        recon_query = recon_query.filter(Reconciliation.session_id == session_id)
    elif client_id:
        recon_query = recon_query.filter(Reconciliation.client_id == client_id)
    recon_map: Dict[str, Any] = {r.month: r for r in recon_query.all()}

    overall_recon = None
    try:
        oq = db.query(OverallReconciliation)
        if session_id:
            oq = oq.filter(OverallReconciliation.session_id == session_id)
        elif client_id:
            oq = oq.filter(OverallReconciliation.client_id == client_id)
        overall_recon = oq.first()
    except Exception:
        pass

    buf = BytesIO()
    # Landscape for the wider reconciliation table
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=18 * mm, bottomMargin=18 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    styles = _build_styles()
    story: List[Any] = []

    # ── Title ─────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary Report", styles["BrandTitle"]))
    if transactions:
        period = f"{transactions[0].date.isoformat()}  to  {transactions[-1].date.isoformat()}"
        story.append(Paragraph(f"Period: {period}", styles["BodySmall"]))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", styles["BodySmall"]))
    if client_name:
        story.append(Paragraph(f"Client: {client_name}", styles["BodySmall"]))
    story.append(Spacer(1, 8 * mm))

    # ── KPI Cards ─────────────────────────────────────────────────
    overall = summary.get("overall", {})
    total_income = overall.get("total_income", 0)
    total_expenses = overall.get("total_expenses", 0)
    net_balance = overall.get("net_balance", 0)

    # VAT totals
    total_vat = sum((t.vat_amount or 0.0) for t in transactions) if include_vat else 0.0
    total_excl = sum(t.amount - (t.vat_amount or 0.0) for t in transactions) if include_vat else 0.0

    if include_vat:
        kpi_data = [
            ["Total Income", "Total Expenses", "Net Balance", "Total VAT", "Total Excl. VAT", "Transactions"],
            [_fmt_currency(total_income), _fmt_currency(total_expenses),
             _fmt_currency(net_balance), _fmt_currency(total_vat), _fmt_currency(total_excl), str(len(transactions))],
        ]
        kpi_table = Table(kpi_data, colWidths=[110, 110, 110, 100, 110, 80])
    else:
        kpi_data = [
            ["Total Income", "Total Expenses", "Net Balance", "Transactions"],
            [_fmt_currency(total_income), _fmt_currency(total_expenses),
             _fmt_currency(net_balance), str(len(transactions))],
        ]
        kpi_table = Table(kpi_data, colWidths=[160, 160, 160, 100])
    kpi_style = [
        ("BACKGROUND", (0, 0), (-1, 0), INDIGO_LIGHT),
        ("TEXTCOLOR", (0, 0), (-1, 0), INDIGO_DARK),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, 1), 11),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, NEUTRAL_200),
    ]
    net_color = GREEN_DARK if net_balance >= 0 else RED_DARK
    kpi_style.append(("TEXTCOLOR", (2, 1), (2, 1), net_color))
    kpi_table.setStyle(TableStyle(kpi_style))
    story.append(kpi_table)
    story.append(Spacer(1, 8 * mm))

    # ── Monthly Breakdown + Reconciliation table ───────────────────
    story.append(Paragraph("Monthly Breakdown & Reconciliation", styles["SectionHeader"]))
    months = summary.get("months", [])

    GREEN_CHIP = colors.HexColor("#D1FAE5")
    YELLOW_CHIP = colors.HexColor("#FEF9C3")
    RED_CHIP = colors.HexColor("#FEE2E2")

    if months:
        # Column widths summing to ~237mm (landscape A4 usable ~267mm with 15mm margins)
        col_widths = [22, 33, 30, 30, 28, 35, 35, 24]  # mm
        col_widths_pts = [w * mm for w in col_widths]
        headers = ["Month", "Opening", "Income", "Expenses", "Net",
                   "Exp. Closing", "Act. Closing", "Status"]

        rows = []
        status_row_indices: List[tuple] = []  # (row_idx, status)
        row_i = 0  # 0-based data row index (header is row 0 in _make_table)
        for m in months:
            rec = recon_map.get(m["month"])
            opening = rec.opening_balance if rec else None
            actual_closing = rec.closing_balance if rec else None
            opening_val = opening if opening is not None else 0.0
            expected_closing = opening_val + m["net_balance"]

            # Determine status
            if actual_closing is not None:
                if abs(actual_closing - expected_closing) < 0.01:
                    status_text = "Reconciled"
                    status_flag = "ok"
                else:
                    status_text = "Mismatch"
                    status_flag = "bad"
            else:
                status_text = "Pending"
                status_flag = "pending"

            rows.append([
                m["month"],
                _fmt_currency(opening_val) if opening is not None else "—",
                _fmt_currency(m["total_income"]),
                _fmt_currency(m["total_expenses"]),
                _fmt_currency(m["net_balance"]),
                _fmt_currency(expected_closing),
                _fmt_currency(actual_closing) if actual_closing is not None else "—",
                status_text,
            ])
            status_row_indices.append((row_i + 1, status_flag))  # +1 for header row
            row_i += 1

        # Totals row
        rows.append([
            "TOTAL", "", _fmt_currency(total_income), _fmt_currency(total_expenses),
            _fmt_currency(net_balance), "", "", "",
        ])

        tbl = _make_table(headers, rows, col_widths=col_widths_pts)

        # Extra styling: align numbers right, status chips
        extra_style = [
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), INDIGO_LIGHT),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (-1, 0), (-1, -1), "CENTER"),  # Status col centred
        ]
        for row_idx, flag in status_row_indices:
            if flag == "ok":
                extra_style.append(("BACKGROUND", (-1, row_idx), (-1, row_idx), GREEN_CHIP))
                extra_style.append(("TEXTCOLOR", (-1, row_idx), (-1, row_idx), GREEN_DARK))
            elif flag == "bad":
                extra_style.append(("BACKGROUND", (-1, row_idx), (-1, row_idx), RED_CHIP))
                extra_style.append(("TEXTCOLOR", (-1, row_idx), (-1, row_idx), RED_DARK))
            else:
                extra_style.append(("BACKGROUND", (-1, row_idx), (-1, row_idx), YELLOW_CHIP))
                extra_style.append(("TEXTCOLOR", (-1, row_idx), (-1, row_idx), colors.HexColor("#92400E")))
        tbl.setStyle(TableStyle(extra_style))
        story.append(tbl)

    story.append(Spacer(1, 6 * mm))

    # ── Overall Reconciliation section ────────────────────────────
    if overall_recon and (overall_recon.system_opening_balance is not None
                          or overall_recon.bank_closing_balance is not None):
        story.append(Paragraph("Overall Reconciliation", styles["SectionHeader"]))
        txn_total = sum(t.amount for t in transactions)
        sys_open = overall_recon.system_opening_balance or 0.0
        sys_close = sys_open + txn_total
        bank_close = overall_recon.bank_closing_balance
        diff = (bank_close - sys_close) if bank_close is not None else None

        ov_rows = [
            ["System Opening Balance", _fmt_currency(sys_open)],
            ["Total Transactions", _fmt_currency(txn_total)],
            ["System Closing Balance", _fmt_currency(sys_close)],
            ["Bank Closing Balance", _fmt_currency(bank_close) if bank_close is not None else "—"],
            ["Difference", _fmt_currency(diff) if diff is not None else "—"],
        ]
        ov_tbl = _make_table(["Description", "Amount"], ov_rows, col_widths=[200, 120])
        diff_style = []
        if diff is not None:
            diff_color = GREEN_DARK if abs(diff) < 0.01 else RED_DARK
            diff_style.append(("TEXTCOLOR", (1, -1), (1, -1), diff_color))
            diff_style.append(("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"))
        ov_tbl.setStyle(TableStyle(diff_style))
        story.append(ov_tbl)
        story.append(Spacer(1, 6 * mm))

    # ── Category Breakdown ────────────────────────────────────────
    story.append(Paragraph("Category Breakdown", styles["SectionHeader"]))

    income_cats: Dict[str, float] = {}
    expense_cats: Dict[str, float] = {}
    for t in transactions:
        cat = t.category or "Uncategorized"
        if t.amount >= 0:
            income_cats[cat] = income_cats.get(cat, 0) + t.amount
        else:
            expense_cats[cat] = expense_cats.get(cat, 0) + abs(t.amount)

    if income_cats:
        story.append(Paragraph("Income Categories", styles["SubHeader"]))
        if include_vat:
            inc_rows = []
            for cat, amt in sorted(income_cats.items(), key=lambda x: x[1], reverse=True):
                cat_txns_inc = [t for t in transactions if (t.category or "Uncategorized") == cat and t.amount >= 0]
                vat_sum = sum(t.vat_amount or 0.0 for t in cat_txns_inc)
                inc_rows.append([cat, _fmt_currency(amt), _fmt_currency(vat_sum), _fmt_currency(amt - vat_sum)])
            incl_vat_total = sum(t.vat_amount or 0.0 for t in transactions if t.amount >= 0)
            inc_rows.append(["Total Income", _fmt_currency(total_income),
                              _fmt_currency(incl_vat_total), _fmt_currency(total_income - incl_vat_total)])
            tbl = _make_table(["Category", "Amount (Incl)", "VAT", "Excl. VAT"], inc_rows,
                               col_widths=[200, 110, 90, 110])
        else:
            inc_rows = [[cat, _fmt_currency(amt)] for cat, amt in
                        sorted(income_cats.items(), key=lambda x: x[1], reverse=True)]
            inc_rows.append(["Total Income", _fmt_currency(total_income)])
            tbl = _make_table(["Category", "Amount"], inc_rows, col_widths=[310, 180])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), GREEN_BG),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4 * mm))

    if expense_cats:
        story.append(Paragraph("Expense Categories", styles["SubHeader"]))
        if include_vat:
            exp_rows = []
            for cat, amt in sorted(expense_cats.items(), key=lambda x: x[1], reverse=True):
                cat_txns_exp = [t for t in transactions if (t.category or "Uncategorized") == cat and t.amount < 0]
                vat_sum = sum(t.vat_amount or 0.0 for t in cat_txns_exp)
                exp_rows.append([cat, _fmt_currency(amt), _fmt_currency(vat_sum), _fmt_currency(amt - vat_sum)])
            exp_vat_total = sum(t.vat_amount or 0.0 for t in transactions if t.amount < 0)
            exp_rows.append(["Total Expenses", _fmt_currency(total_expenses),
                              _fmt_currency(exp_vat_total), _fmt_currency(total_expenses - exp_vat_total)])
            tbl = _make_table(["Category", "Amount (Incl)", "VAT", "Excl. VAT"], exp_rows,
                               col_widths=[200, 110, 90, 110])
        else:
            exp_rows = [[cat, _fmt_currency(amt)] for cat, amt in
                        sorted(expense_cats.items(), key=lambda x: x[1], reverse=True)]
            exp_rows.append(["Total Expenses", _fmt_currency(total_expenses)])
            tbl = _make_table(["Category", "Amount"], exp_rows, col_widths=[310, 180])
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), RED_BG),
        ]))
        story.append(tbl)

    # ── Build ─────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════
#  PDF: TRANSACTIONS LISTING
# ═════════════════════════════════════════════════════════════════════

def export_transactions_pdf(
    session_id: Optional[str],
    db: Session,
    client_id: Optional[int] = None,
    include_vat: bool = False,
    client_name: Optional[str] = None,
) -> BytesIO:
    """Generate a branded transactions PDF listing."""
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=12 * mm, rightMargin=12 * mm)
    styles = _build_styles()
    story: List[Any] = []

    story.append(Paragraph("Transaction Listing", styles["BrandTitle"]))
    story.append(Paragraph(f"Total transactions: {len(transactions)}", styles["BodySmall"]))
    if transactions:
        period = f"{transactions[0].date.isoformat()}  to  {transactions[-1].date.isoformat()}"
        story.append(Paragraph(f"Period: {period}", styles["BodySmall"]))
    if client_name:
        story.append(Paragraph(f"Client: {client_name}", styles["BodySmall"]))
    story.append(Spacer(1, 6 * mm))

    if not transactions:
        story.append(Paragraph("No transactions found.", styles["BodySmall"]))
    else:
        # Build rows in chunks to avoid memory issues with very large datasets
        if include_vat:
            headers = ["Date", "Description", "Category", "Amount (Incl)", "VAT", "Excl VAT"]
            col_widths = [60, 280, 100, 90, 70, 90]
        else:
            headers = ["Date", "Description", "Category", "Amount"]
            col_widths = [65, 350, 120, 100]

        rows = []
        running_total = 0.0
        running_vat = 0.0
        running_excl = 0.0
        for t in transactions:
            desc = t.description or ""
            if len(desc) > 70:
                desc = desc[:67] + "..."
            running_total += t.amount
            if include_vat:
                vat_amt = t.vat_amount if t.vat_amount is not None else 0.0
                excl = t.amount - vat_amt
                running_vat += vat_amt
                running_excl += excl
                rows.append([
                    t.date.isoformat(),
                    desc,
                    t.category or "Uncategorized",
                    _fmt_currency(t.amount),
                    _fmt_currency(vat_amt),
                    _fmt_currency(excl),
                ])
            else:
                rows.append([
                    t.date.isoformat(),
                    desc,
                    t.category or "Uncategorized",
                    _fmt_currency(t.amount),
                ])

        # Add totals row
        if include_vat:
            rows.append(["", "", "TOTAL", _fmt_currency(running_total), _fmt_currency(running_vat), _fmt_currency(running_excl)])
        else:
            rows.append(["", "", "TOTAL", _fmt_currency(running_total)])

        tbl = _make_table(headers, rows, col_widths=col_widths)
        # Bold & highlight last row
        tbl.setStyle(TableStyle([
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("BACKGROUND", (0, -1), (-1, -1), INDIGO_LIGHT),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
        ]))
        story.append(tbl)

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════════════════════════════
#  PDF: CATEGORY REPORT
# ═════════════════════════════════════════════════════════════════════

def export_category_pdf(
    session_id: Optional[str],
    db: Session,
    client_id: Optional[int] = None,
    selected_categories: Optional[List[str]] = None,
    include_vat: bool = False,
    client_name: Optional[str] = None,
) -> BytesIO:
    """Generate a per-category PDF with monthly sections."""
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    # Group by category
    cats: Dict[str, list] = {}
    for t in transactions:
        cat = t.category or "Uncategorized"
        cats.setdefault(cat, []).append(t)

    if selected_categories:
        cats = {k: v for k, v in cats.items() if k in selected_categories}

    buf = BytesIO()
    # Use landscape when VAT columns are included to give more horizontal room
    pagesize = landscape(A4) if include_vat else A4
    doc = SimpleDocTemplate(buf, pagesize=pagesize, topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=15 * mm, rightMargin=15 * mm)
    styles = _build_styles()
    story: List[Any] = []

    story.append(Paragraph("Category Report", styles["BrandTitle"]))
    if include_vat:
        story.append(Paragraph("VAT amounts are shown where applicable.", styles["BodySmall"]))
    story.append(Paragraph(f"Generated: {date.today().isoformat()}", styles["BodySmall"]))
    if client_name:
        story.append(Paragraph(f"Client: {client_name}", styles["BodySmall"]))
    story.append(Spacer(1, 6 * mm))

    for cat_name in sorted(cats.keys()):
        cat_txns = cats[cat_name]

        story.append(Paragraph(f"Category: {cat_name}", styles["SectionHeader"]))
        cat_total = sum(t.amount for t in cat_txns)
        cat_vat = sum(t.vat_amount or 0.0 for t in cat_txns) if include_vat else 0.0
        cat_excl = sum(t.amount - (t.vat_amount or 0.0) for t in cat_txns) if include_vat else 0.0

        summary_text = f"Transactions: {len(cat_txns)}  |  Total: {_fmt_currency(cat_total)}"
        if include_vat:
            summary_text += f"  |  VAT: {_fmt_currency(cat_vat)}  |  Excl. VAT: {_fmt_currency(cat_excl)}"
        story.append(Paragraph(summary_text, styles["BodySmall"]))
        story.append(Spacer(1, 3 * mm))

        # Group by month
        months_map: Dict[str, list] = {}
        for t in cat_txns:
            mk = t.date.strftime("%Y-%m")
            months_map.setdefault(mk, []).append(t)

        for mk in sorted(months_map.keys()):
            mtxns = months_map[mk]
            story.append(Paragraph(mk, styles["SubHeader"]))
            rows = []
            for t in mtxns:
                desc = t.description or ""
                if len(desc) > 55:
                    desc = desc[:52] + "..."
                if include_vat:
                    vat_amt = t.vat_amount if t.vat_amount is not None else 0.0
                    excl = t.amount - vat_amt
                    rows.append([t.date.isoformat(), desc, _fmt_currency(t.amount),
                                 _fmt_currency(vat_amt), _fmt_currency(excl)])
                else:
                    rows.append([t.date.isoformat(), desc, _fmt_currency(t.amount)])

            month_total = sum(t.amount for t in mtxns)
            if include_vat:
                month_vat = sum(t.vat_amount or 0.0 for t in mtxns)
                month_excl = sum(t.amount - (t.vat_amount or 0.0) for t in mtxns)
                rows.append(["", "Month Total", _fmt_currency(month_total),
                             _fmt_currency(month_vat), _fmt_currency(month_excl)])
                tbl = _make_table(
                    ["Date", "Description", "Amount (Incl)", "VAT", "Excl. VAT"],
                    rows,
                    col_widths=[65, 270, 90, 70, 90],
                )
            else:
                rows.append(["", "Month Total", _fmt_currency(month_total)])
                tbl = _make_table(["Date", "Description", "Amount"], rows,
                                  col_widths=[65, 300, 100])

            tbl.setStyle(TableStyle([
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), INDIGO_LIGHT),
                ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 3 * mm))

        story.append(Spacer(1, 4 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=NEUTRAL_200))
        story.append(Spacer(1, 2 * mm))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    buf.seek(0)
    return buf
