"""
Analytics Service
Provides cash flow analysis, merchant analytics, recurring transaction detection,
and other advanced reporting features.
"""

from typing import Dict, List, Any, Optional
from datetime import date, timedelta
from collections import defaultdict
from io import BytesIO
import re

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Transaction, TransactionMerchant


# ═════════════════════════════════════════════════════════════════════
#  CASH FLOW / RUNNING BALANCE
# ═════════════════════════════════════════════════════════════════════

def get_cashflow_series(
    db: Session,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    opening_balance: float = 0.0,
) -> Dict[str, Any]:
    """
    Return a daily running-balance series for charting.

    Returns:
        {
            "opening_balance": 0.0,
            "series": [
                {"date": "2024-01-02", "balance": 1500.00, "daily_income": 2000, "daily_expenses": 500},
                ...
            ],
            "min_balance": -200.00,
            "max_balance": 15000.00,
        }
    """
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    if not transactions:
        return {"opening_balance": opening_balance, "series": [], "min_balance": 0, "max_balance": 0}

    # Try to get reconciliation opening balance if not supplied
    if opening_balance == 0.0:
        from models import OverallReconciliation
        recon_query = db.query(OverallReconciliation)
        if session_id:
            recon_query = recon_query.filter(OverallReconciliation.session_id == session_id)
        elif client_id:
            recon_query = recon_query.filter(OverallReconciliation.client_id == client_id)
        recon = recon_query.first()
        if recon and recon.system_opening_balance is not None:
            opening_balance = recon.system_opening_balance

    # Group transactions by date
    daily: Dict[str, Dict[str, float]] = {}
    for txn in transactions:
        d = txn.date.isoformat()
        if d not in daily:
            daily[d] = {"income": 0.0, "expenses": 0.0}
        if txn.amount >= 0:
            daily[d]["income"] += txn.amount
        else:
            daily[d]["expenses"] += abs(txn.amount)

    # Build cumulative series
    sorted_dates = sorted(daily.keys())
    series = []
    balance = opening_balance
    min_bal = balance
    max_bal = balance

    for d in sorted_dates:
        day = daily[d]
        balance += day["income"] - day["expenses"]
        min_bal = min(min_bal, balance)
        max_bal = max(max_bal, balance)
        series.append({
            "date": d,
            "balance": round(balance, 2),
            "daily_income": round(day["income"], 2),
            "daily_expenses": round(day["expenses"], 2),
        })

    return {
        "opening_balance": opening_balance,
        "series": series,
        "min_balance": round(min_bal, 2),
        "max_balance": round(max_bal, 2),
    }


# ═════════════════════════════════════════════════════════════════════
#  MERCHANT ANALYTICS
# ═════════════════════════════════════════════════════════════════════

def get_merchant_analytics(
    db: Session,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    top_n: int = 20,
) -> Dict[str, Any]:
    """
    Return merchant-level analytics for the UI.

    Returns:
        {
            "merchants": [
                {
                    "merchant": "Woolworths",
                    "count": 12,
                    "total": 3456.78,
                    "average": 288.07,
                    "category": "Groceries",
                    "last_seen": "2024-03-15",
                    "trend": [{"month": "2024-01", "amount": 1200}, ...]
                },
                ...
            ],
            "total_merchants": 45,
        }
    """
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    if not transactions:
        return {"merchants": [], "total_merchants": 0}

    # Build merchant lookup from TransactionMerchant table
    txn_ids = [t.id for t in transactions]
    merchant_records = db.query(TransactionMerchant).filter(
        TransactionMerchant.transaction_id.in_(txn_ids)
    ).all() if txn_ids else []

    merchant_map = {m.transaction_id: m.merchant for m in merchant_records if m.merchant}

    # Aggregate by merchant
    merchants: Dict[str, Dict[str, Any]] = {}
    for txn in transactions:
        merchant_name = merchant_map.get(txn.id, "Unattributed")
        if not merchant_name:
            merchant_name = "Unattributed"

        if merchant_name not in merchants:
            merchants[merchant_name] = {
                "merchant": merchant_name,
                "count": 0,
                "total": 0.0,
                "categories": defaultdict(int),
                "last_seen": txn.date,
                "monthly": defaultdict(float),
            }

        m = merchants[merchant_name]
        m["count"] += 1
        m["total"] += abs(txn.amount)
        m["categories"][txn.category or "Uncategorized"] += 1
        if txn.date > m["last_seen"]:
            m["last_seen"] = txn.date
        month_key = txn.date.strftime("%Y-%m")
        m["monthly"][month_key] += abs(txn.amount)

    # Sort by total descending, take top_n
    sorted_merchants = sorted(merchants.values(), key=lambda x: x["total"], reverse=True)

    result = []
    for m in sorted_merchants[:top_n]:
        # Most common category
        primary_cat = max(m["categories"].items(), key=lambda x: x[1])[0] if m["categories"] else "Unknown"
        # Monthly trend
        trend = [{"month": mk, "amount": round(amt, 2)}
                 for mk, amt in sorted(m["monthly"].items())]
        result.append({
            "merchant": m["merchant"],
            "count": m["count"],
            "total": round(m["total"], 2),
            "average": round(m["total"] / m["count"], 2) if m["count"] else 0,
            "category": primary_cat,
            "last_seen": m["last_seen"].isoformat(),
            "trend": trend,
        })

    return {
        "merchants": result,
        "total_merchants": len(merchants),
    }


# ═════════════════════════════════════════════════════════════════════
#  RECURRING TRANSACTION DETECTION
# ═════════════════════════════════════════════════════════════════════

def detect_recurring_transactions(
    db: Session,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    min_occurrences: int = 2,
    amount_tolerance: float = 0.10,  # 10% tolerance for amount matching
) -> Dict[str, Any]:
    """
    Detect recurring transactions by matching descriptions and amounts across months.

    Returns:
        {
            "recurring": [
                {
                    "description_pattern": "INSURANCE PREMIUM",
                    "category": "Insurance",
                    "average_amount": -450.00,
                    "occurrences": 6,
                    "months_active": ["2024-01", "2024-02", ...],
                    "frequency": "monthly",
                    "total": -2700.00,
                    "amount_variance": 0.0,
                    "last_seen": "2024-06-01",
                    "is_debit": true,
                    "transactions": [{"date": "...", "amount": -450, "description": "..."}]
                },
                ...
            ],
            "total_recurring": 12,
            "total_recurring_amount": -15000.00,
        }
    """
    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    if not transactions:
        return {"recurring": [], "total_recurring": 0, "total_recurring_amount": 0}

    # Normalize descriptions for grouping
    def normalize_desc(desc: str) -> str:
        """Normalize description for matching: remove dates, refs, extra whitespace."""
        s = desc.upper().strip()
        # Remove common variable parts: dates, reference numbers, card numbers
        s = re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', '', s)  # dates
        s = re.sub(r'\b\d{6,}\b', '', s)  # long numbers (references)
        s = re.sub(r'\*+\d+', '', s)  # masked card numbers
        s = re.sub(r'\bREF\s*:?\s*\w+', '', s)  # REF: xxx
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # Group by normalized description
    groups: Dict[str, List[Transaction]] = defaultdict(list)
    for txn in transactions:
        key = normalize_desc(txn.description)
        if key:  # skip empty after normalization
            groups[key].append(txn)

    # Identify recurring: same direction, similar amounts, multiple months
    recurring = []
    for pattern, txns in groups.items():
        if len(txns) < min_occurrences:
            continue

        # Check if all same sign (consistent direction)
        signs = set(1 if t.amount >= 0 else -1 for t in txns)
        if len(signs) > 1:
            continue  # mixed directions, skip

        amounts = [abs(t.amount) for t in txns]
        avg_amount = sum(amounts) / len(amounts)

        if avg_amount < 1:  # skip trivial amounts
            continue

        # Check amount consistency (within tolerance)
        if avg_amount > 0:
            max_deviation = max(abs(a - avg_amount) / avg_amount for a in amounts)
            if max_deviation > amount_tolerance:
                continue

        # Check across multiple months
        months_seen = set(t.date.strftime("%Y-%m") for t in txns)
        if len(months_seen) < min_occurrences:
            continue

        # Determine frequency
        sorted_months = sorted(months_seen)
        all_months_set = set()
        if len(sorted_months) >= 2:
            # Generate all months in range
            from datetime import datetime
            first = datetime.strptime(sorted_months[0], "%Y-%m")
            last = datetime.strptime(sorted_months[-1], "%Y-%m")
            cur = first
            while cur <= last:
                all_months_set.add(cur.strftime("%Y-%m"))
                if cur.month == 12:
                    cur = cur.replace(year=cur.year + 1, month=1)
                else:
                    cur = cur.replace(month=cur.month + 1)

        total_possible = len(all_months_set) if all_months_set else len(sorted_months)
        coverage = len(months_seen) / total_possible if total_possible > 0 else 0

        if coverage >= 0.6:
            frequency = "monthly"
        elif len(months_seen) >= 2:
            frequency = "irregular"
        else:
            continue

        is_debit = list(signs)[0] == -1
        signed_avg = -avg_amount if is_debit else avg_amount

        # Amount variance
        variance = max_deviation if avg_amount > 0 else 0

        # Use original description from the most recent transaction
        sorted_txns = sorted(txns, key=lambda t: t.date, reverse=True)
        primary_desc = sorted_txns[0].description
        primary_cat = sorted_txns[0].category or "Uncategorized"

        txn_details = [
            {"id": t.id, "date": t.date.isoformat(), "amount": t.amount, "description": t.description}
            for t in sorted_txns[:12]  # limit to last 12 occurrences
        ]

        recurring.append({
            "description_pattern": primary_desc,
            "category": primary_cat,
            "average_amount": round(signed_avg, 2),
            "occurrences": len(txns),
            "months_active": sorted_months,
            "frequency": frequency,
            "total": round(sum(t.amount for t in txns), 2),
            "amount_variance": round(variance * 100, 1),  # as percentage
            "last_seen": sorted_txns[0].date.isoformat(),
            "is_debit": is_debit,
            "transactions": txn_details,
            # All IDs in this recurring group (used internally by the unusual report)
            "transaction_ids": [t.id for t in txns],
        })

    # Sort by absolute total descending
    recurring.sort(key=lambda r: abs(r["total"]), reverse=True)

    total_recurring_amount = sum(r["total"] for r in recurring)

    return {
        "recurring": recurring,
        "total_recurring": len(recurring),
        "total_recurring_amount": round(total_recurring_amount, 2),
    }


# ═════════════════════════════════════════════════════════════════════
#  CSV EXPORT HELPERS
# ═════════════════════════════════════════════════════════════════════

def export_transactions_csv(
    db: Session,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    include_vat: bool = False,
) -> BytesIO:
    """Export all transactions as CSV."""
    import csv
    from io import StringIO

    query = db.query(Transaction)
    if session_id:
        query = query.filter(Transaction.session_id == session_id)
    elif client_id:
        query = query.filter(Transaction.client_id == client_id)
    else:
        raise ValueError("Either session_id or client_id must be provided")

    transactions = query.order_by(Transaction.date).all()

    string_buf = StringIO()
    writer = csv.writer(string_buf)
    if include_vat:
        writer.writerow(["Date", "Description", "Amount (Incl VAT)", "VAT Amount", "Amount (Excl VAT)", "Category", "Bank Source"])
        for txn in transactions:
            vat_amt = txn.vat_amount if txn.vat_amount is not None else 0.0
            excl = txn.amount - vat_amt
            writer.writerow([
                txn.date.isoformat(),
                txn.description,
                f"{txn.amount:.2f}",
                f"{vat_amt:.2f}",
                f"{excl:.2f}",
                txn.category or "Uncategorized",
                txn.bank_source or "unknown",
            ])
    else:
        writer.writerow(["Date", "Description", "Amount", "Category", "Bank Source"])
        for txn in transactions:
            writer.writerow([
                txn.date.isoformat(),
                txn.description,
                f"{txn.amount:.2f}",
                txn.category or "Uncategorized",
                txn.bank_source or "unknown",
            ])

    buf = BytesIO(string_buf.getvalue().encode("utf-8-sig"))  # BOM for Excel compat
    buf.seek(0)
    return buf


def export_summary_csv(
    db: Session,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    include_vat: bool = False,
) -> BytesIO:
    """Export monthly summary as CSV."""
    import csv
    from io import StringIO
    from services.summary import calculate_monthly_summary

    summary = calculate_monthly_summary(session_id=session_id, db=db, client_id=client_id)

    # Pre-compute per-month VAT totals if needed
    month_vat = {}
    month_excl = {}
    if include_vat:
        query = db.query(Transaction)
        if session_id:
            query = query.filter(Transaction.session_id == session_id)
        elif client_id:
            query = query.filter(Transaction.client_id == client_id)
        transactions = query.all()
        for t in transactions:
            mk = t.date.strftime("%Y-%m")
            vat = t.vat_amount if t.vat_amount is not None else 0.0
            month_vat[mk] = month_vat.get(mk, 0.0) + vat
            month_excl[mk] = month_excl.get(mk, 0.0) + (t.amount - vat)

    string_buf = StringIO()
    writer = csv.writer(string_buf)
    if include_vat:
        writer.writerow(["Month", "Total Income", "Total Expenses", "Net Balance", "Total VAT", "Total Excl. VAT"])
    else:
        writer.writerow(["Month", "Total Income", "Total Expenses", "Net Balance"])
    for m in summary.get("months", []):
        row_data = [
            m["month"],
            f"{m['total_income']:.2f}",
            f"{m['total_expenses']:.2f}",
            f"{m['net_balance']:.2f}",
        ]
        if include_vat:
            mk = m["month"]
            row_data.append(f"{month_vat.get(mk, 0.0):.2f}")
            row_data.append(f"{month_excl.get(mk, 0.0):.2f}")
        writer.writerow(row_data)

    overall = summary.get("overall", {})
    total_row = [
        "TOTAL",
        f"{overall.get('total_income', 0):.2f}",
        f"{overall.get('total_expenses', 0):.2f}",
        f"{overall.get('net_balance', 0):.2f}",
    ]
    if include_vat:
        total_row.append(f"{sum(month_vat.values()):.2f}")
        total_row.append(f"{sum(month_excl.values()):.2f}")
    writer.writerow(total_row)

    buf = BytesIO(string_buf.getvalue().encode("utf-8-sig"))
    buf.seek(0)
    return buf
