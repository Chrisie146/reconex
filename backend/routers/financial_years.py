"""
Financial Year management routes.

Provides endpoints to define financial years per client, archive completed years
(moves all related data to archive tables), and read archived data in a read-only
manner. Users can also unarchive (restore) a year back to live tables.
"""

from datetime import datetime, date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from auth import get_current_user
from models import (
    Client,
    FinancialYear,
    ArchivedSession,
    ArchivedTransaction,
    ArchivedTransactionMerchant,
    ArchivedReconciliation,
    ArchivedOverallReconciliation,
    ArchivedInvoice,
    ArchivedInvoiceMatch,
    SessionState,
    Transaction,
    TransactionMerchant,
    Reconciliation,
    OverallReconciliation,
    Invoice,
    InvoiceMatch,
    User,
    get_db,
)

router = APIRouter(tags=["Financial Years"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class FinancialYearCreate(BaseModel):
    client_id: int
    label: str
    year_start: date
    year_end: date


class FinancialYearUpdate(BaseModel):
    label: Optional[str] = None
    year_start: Optional[date] = None
    year_end: Optional[date] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_or_404(client_id: int, user: User, db: Session) -> Client:
    client = db.query(Client).filter(
        Client.id == client_id,
        Client.user_id == user.id,
    ).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _get_fy_or_404(fy_id: int, user: User, db: Session) -> FinancialYear:
    fy = db.query(FinancialYear).filter(FinancialYear.id == fy_id).first()
    if not fy:
        raise HTTPException(status_code=404, detail="Financial year not found")
    # Verify ownership via client
    _get_client_or_404(fy.client_id, user, db)
    return fy


def _serialize_fy(fy: FinancialYear) -> dict:
    return {
        "id": fy.id,
        "client_id": fy.client_id,
        "label": fy.label,
        "year_start": fy.year_start.isoformat(),
        "year_end": fy.year_end.isoformat(),
        "status": fy.status,
        "archived_at": fy.archived_at.isoformat() if fy.archived_at else None,
        "created_at": fy.created_at.isoformat() if fy.created_at else None,
    }


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.get("/financial-years")
def list_financial_years(
    client_id: int = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all financial years for a client."""
    _get_client_or_404(client_id, current_user, db)
    years = (
        db.query(FinancialYear)
        .filter(FinancialYear.client_id == client_id)
        .order_by(FinancialYear.year_start.desc())
        .all()
    )
    return {"financial_years": [_serialize_fy(y) for y in years]}


@router.post("/financial-years", status_code=201)
def create_financial_year(
    body: FinancialYearCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new financial year definition for a client."""
    _get_client_or_404(body.client_id, current_user, db)
    if body.year_end <= body.year_start:
        raise HTTPException(status_code=400, detail="year_end must be after year_start")
    fy = FinancialYear(
        client_id=body.client_id,
        label=body.label,
        year_start=body.year_start,
        year_end=body.year_end,
        status="open",
    )
    db.add(fy)
    db.commit()
    db.refresh(fy)
    return _serialize_fy(fy)


@router.put("/financial-years/{fy_id}")
def update_financial_year(
    fy_id: int,
    body: FinancialYearUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update label or dates of an open financial year."""
    fy = _get_fy_or_404(fy_id, current_user, db)
    if fy.status == "archived":
        raise HTTPException(status_code=400, detail="Cannot edit an archived financial year")
    if body.label is not None:
        fy.label = body.label
    if body.year_start is not None:
        fy.year_start = body.year_start
    if body.year_end is not None:
        fy.year_end = body.year_end
    if fy.year_end <= fy.year_start:
        raise HTTPException(status_code=400, detail="year_end must be after year_start")
    db.commit()
    db.refresh(fy)
    return _serialize_fy(fy)


@router.delete("/financial-years/{fy_id}", status_code=204)
def delete_financial_year(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an open financial year definition (no data is changed)."""
    fy = _get_fy_or_404(fy_id, current_user, db)
    if fy.status == "archived":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an archived year. Unarchive it first.",
        )
    db.delete(fy)
    db.commit()


# ---------------------------------------------------------------------------
# Archive / Unarchive
# ---------------------------------------------------------------------------


@router.post("/financial-years/{fy_id}/archive")
def archive_financial_year(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Archive a financial year.

    Finds all sessions whose transactions fall within year_start..year_end for
    this client, copies all related data to archive tables in a single transaction,
    then removes the rows from the live tables.
    """
    fy = _get_fy_or_404(fy_id, current_user, db)
    if fy.status == "archived":
        raise HTTPException(status_code=400, detail="Financial year is already archived")

    now = datetime.utcnow()

    # Step 1: Select only transactions that fall within the date range.
    # Do NOT scope by session — a session may span year boundaries.
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.client_id == fy.client_id,
            Transaction.date >= fy.year_start,
            Transaction.date <= fy.year_end,
        )
        .all()
    )

    if not transactions:
        raise HTTPException(
            status_code=400,
            detail="No transactions found in this date range. Nothing to archive.",
        )

    txn_ids = [t.id for t in transactions]
    # All session_ids that contributed at least one transaction to this archive
    session_ids_in_range = list({t.session_id for t in transactions})

    # Step 2: Determine which sessions become fully empty after removing these
    # transactions. Only those sessions (and their related records) get archived
    # at the session level — a session that still has transactions outside the
    # date range stays in the live tables.
    fully_archived_session_ids = []
    for sid in session_ids_in_range:
        remaining = (
            db.query(func.count(Transaction.id))
            .filter(
                Transaction.session_id == sid,
                Transaction.client_id == fy.client_id,
                ~Transaction.id.in_(txn_ids),
            )
            .scalar()
        )
        if remaining == 0:
            fully_archived_session_ids.append(sid)

    try:
        # -- Sessions (only fully emptied ones) --
        for ss in db.query(SessionState).filter(
            SessionState.session_id.in_(fully_archived_session_ids)
        ).all():
            db.add(ArchivedSession(
                financial_year_id=fy.id,
                original_id=ss.id,
                client_id=fy.client_id,
                session_id=ss.session_id,
                locked=ss.locked,
                friendly_name=ss.friendly_name,
                original_created_at=ss.created_at,
                archived_at=now,
            ))

        # -- Transactions (only those within the date range) --
        for t in transactions:
            db.add(ArchivedTransaction(
                financial_year_id=fy.id,
                original_id=t.id,
                client_id=t.client_id,
                session_id=t.session_id,
                original_invoice_id=t.invoice_id,
                date=t.date,
                description=t.description,
                amount=t.amount,
                category=t.category,
                vat_amount=t.vat_amount,
                amount_excl_vat=t.amount_excl_vat,
                amount_incl_vat=t.amount_incl_vat,
                bank_source=t.bank_source,
                balance_verified=t.balance_verified,
                balance_difference=t.balance_difference,
                validation_message=t.validation_message,
                original_created_at=t.created_at,
                archived_at=now,
            ))

        # -- Merchants (scoped to the archived transaction IDs, not session) --
        for m in db.query(TransactionMerchant).filter(
            TransactionMerchant.transaction_id.in_(txn_ids)
        ).all():
            db.add(ArchivedTransactionMerchant(
                financial_year_id=fy.id,
                original_id=m.id,
                original_transaction_id=m.transaction_id,
                session_id=m.session_id,
                merchant=m.merchant,
                original_created_at=m.created_at,
                archived_at=now,
            ))

        # -- Reconciliations (only for fully archived sessions) --
        for r in db.query(Reconciliation).filter(
            Reconciliation.session_id.in_(fully_archived_session_ids)
        ).all():
            db.add(ArchivedReconciliation(
                financial_year_id=fy.id,
                original_id=r.id,
                session_id=r.session_id,
                client_id=r.client_id,
                month=r.month,
                opening_balance=r.opening_balance,
                closing_balance=r.closing_balance,
                original_created_at=r.created_at,
                archived_at=now,
            ))

        for o in db.query(OverallReconciliation).filter(
            OverallReconciliation.session_id.in_(fully_archived_session_ids)
        ).all():
            db.add(ArchivedOverallReconciliation(
                financial_year_id=fy.id,
                original_id=o.id,
                session_id=o.session_id,
                client_id=o.client_id,
                system_opening_balance=o.system_opening_balance,
                bank_closing_balance=o.bank_closing_balance,
                original_created_at=o.created_at,
                archived_at=now,
            ))

        # -- Invoices & Matches (only for fully archived sessions) --
        invoices = db.query(Invoice).filter(
            Invoice.session_id.in_(fully_archived_session_ids)
        ).all()
        invoice_ids = [i.id for i in invoices]

        for inv in invoices:
            db.add(ArchivedInvoice(
                financial_year_id=fy.id,
                original_id=inv.id,
                client_id=inv.client_id if inv.client_id is not None else fy.client_id,
                session_id=inv.session_id,
                supplier_name=inv.supplier_name,
                invoice_date=inv.invoice_date,
                invoice_number=inv.invoice_number,
                total_amount=inv.total_amount,
                vat_amount=inv.vat_amount,
                file_reference=inv.file_reference,
                original_created_at=inv.created_at,
                archived_at=now,
            ))

        if invoice_ids:
            for m in db.query(InvoiceMatch).filter(
                InvoiceMatch.invoice_id.in_(invoice_ids)
            ).all():
                db.add(ArchivedInvoiceMatch(
                    financial_year_id=fy.id,
                    original_id=m.id,
                    original_invoice_id=m.invoice_id,
                    original_transaction_id=m.transaction_id,
                    confidence=m.confidence,
                    explanation=m.explanation,
                    status=m.status,
                    suggested_at=m.suggested_at,
                    confirmed_at=m.confirmed_at,
                    archived_at=now,
                ))

        # -- Flush archive inserts before deleting from live tables --
        db.flush()

        # -- Delete from live tables --
        # Transactions: only the date-filtered rows
        db.query(Transaction).filter(Transaction.id.in_(txn_ids)).delete(synchronize_session=False)
        # Merchants: only for archived transaction IDs
        db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id.in_(txn_ids)).delete(synchronize_session=False)
        # Session-level records: only fully emptied sessions
        if invoice_ids:
            db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        if fully_archived_session_ids:
            db.query(Invoice).filter(Invoice.session_id.in_(fully_archived_session_ids)).delete(synchronize_session=False)
            db.query(OverallReconciliation).filter(OverallReconciliation.session_id.in_(fully_archived_session_ids)).delete(synchronize_session=False)
            db.query(Reconciliation).filter(Reconciliation.session_id.in_(fully_archived_session_ids)).delete(synchronize_session=False)
            db.query(SessionState).filter(SessionState.session_id.in_(fully_archived_session_ids)).delete(synchronize_session=False)

        # -- Mark year as archived --
        fy.status = "archived"
        fy.archived_at = now
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Archive failed: {str(e)}")

    return {
        "success": True,
        "message": f"Financial year '{fy.label}' archived successfully",
        "sessions_archived": len(fully_archived_session_ids),
        "transactions_archived": len(txn_ids),
    }


@router.post("/financial-years/{fy_id}/unarchive")
def unarchive_financial_year(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Restore an archived financial year back to the live tables.
    All archive records for this year are moved back and the year status
    is set back to 'open'.
    """
    fy = _get_fy_or_404(fy_id, current_user, db)
    if fy.status != "archived":
        raise HTTPException(status_code=400, detail="Financial year is not archived")

    try:
        # -- Restore Sessions --
        for s in db.query(ArchivedSession).filter(ArchivedSession.financial_year_id == fy.id).all():
            existing = db.query(SessionState).filter(SessionState.session_id == s.session_id).first()
            if not existing:
                db.add(SessionState(
                    id=s.original_id,
                    session_id=s.session_id,
                    locked=s.locked,
                    friendly_name=s.friendly_name,
                    created_at=s.original_created_at,
                ))

        # -- Restore Transactions --
        for t in db.query(ArchivedTransaction).filter(ArchivedTransaction.financial_year_id == fy.id).all():
            db.add(Transaction(
                id=t.original_id,
                client_id=t.client_id,
                session_id=t.session_id,
                invoice_id=t.original_invoice_id,
                date=t.date,
                description=t.description,
                amount=t.amount,
                category=t.category,
                vat_amount=t.vat_amount,
                amount_excl_vat=t.amount_excl_vat,
                amount_incl_vat=t.amount_incl_vat,
                bank_source=t.bank_source,
                balance_verified=t.balance_verified,
                balance_difference=t.balance_difference,
                validation_message=t.validation_message,
                created_at=t.original_created_at,
            ))

        # -- Restore Merchants --
        for m in db.query(ArchivedTransactionMerchant).filter(ArchivedTransactionMerchant.financial_year_id == fy.id).all():
            db.add(TransactionMerchant(
                id=m.original_id,
                transaction_id=m.original_transaction_id,
                session_id=m.session_id,
                merchant=m.merchant,
                created_at=m.original_created_at,
            ))

        # -- Restore Reconciliations --
        for r in db.query(ArchivedReconciliation).filter(ArchivedReconciliation.financial_year_id == fy.id).all():
            db.add(Reconciliation(
                id=r.original_id,
                session_id=r.session_id,
                client_id=r.client_id,
                month=r.month,
                opening_balance=r.opening_balance,
                closing_balance=r.closing_balance,
                created_at=r.original_created_at,
            ))

        for o in db.query(ArchivedOverallReconciliation).filter(ArchivedOverallReconciliation.financial_year_id == fy.id).all():
            db.add(OverallReconciliation(
                id=o.original_id,
                session_id=o.session_id,
                client_id=o.client_id,
                system_opening_balance=o.system_opening_balance,
                bank_closing_balance=o.bank_closing_balance,
                created_at=o.original_created_at,
            ))

        # -- Restore Invoices --
        for inv in db.query(ArchivedInvoice).filter(ArchivedInvoice.financial_year_id == fy.id).all():
            db.add(Invoice(
                id=inv.original_id,
                client_id=inv.client_id,
                session_id=inv.session_id,
                supplier_name=inv.supplier_name,
                invoice_date=inv.invoice_date,
                invoice_number=inv.invoice_number,
                total_amount=inv.total_amount,
                vat_amount=inv.vat_amount,
                file_reference=inv.file_reference,
                created_at=inv.original_created_at,
            ))

        for m in db.query(ArchivedInvoiceMatch).filter(ArchivedInvoiceMatch.financial_year_id == fy.id).all():
            db.add(InvoiceMatch(
                id=m.original_id,
                invoice_id=m.original_invoice_id,
                transaction_id=m.original_transaction_id,
                confidence=m.confidence,
                explanation=m.explanation,
                status=m.status,
                suggested_at=m.suggested_at,
                confirmed_at=m.confirmed_at,
            ))

        db.flush()

        # -- Delete archive records --
        db.query(ArchivedInvoiceMatch).filter(ArchivedInvoiceMatch.financial_year_id == fy.id).delete()
        db.query(ArchivedInvoice).filter(ArchivedInvoice.financial_year_id == fy.id).delete()
        db.query(ArchivedOverallReconciliation).filter(ArchivedOverallReconciliation.financial_year_id == fy.id).delete()
        db.query(ArchivedReconciliation).filter(ArchivedReconciliation.financial_year_id == fy.id).delete()
        db.query(ArchivedTransactionMerchant).filter(ArchivedTransactionMerchant.financial_year_id == fy.id).delete()
        db.query(ArchivedTransaction).filter(ArchivedTransaction.financial_year_id == fy.id).delete()
        db.query(ArchivedSession).filter(ArchivedSession.financial_year_id == fy.id).delete()

        fy.status = "open"
        fy.archived_at = None
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unarchive failed: {str(e)}")

    return {"success": True, "message": f"Financial year '{fy.label}' restored to live tables"}


# ---------------------------------------------------------------------------
# Read-only archived data endpoints
# ---------------------------------------------------------------------------


@router.get("/financial-years/{fy_id}/transactions")
def get_archived_transactions(
    fy_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List archived transactions for a financial year (read-only, paginated)."""
    fy = _get_fy_or_404(fy_id, current_user, db)

    q = db.query(ArchivedTransaction).filter(ArchivedTransaction.financial_year_id == fy.id)
    if search:
        q = q.filter(ArchivedTransaction.description.ilike(f"%{search}%"))
    if category:
        q = q.filter(ArchivedTransaction.category == category)

    total = q.count()
    items = q.order_by(ArchivedTransaction.date.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "financial_year": _serialize_fy(fy),
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": [
            {
                "id": t.id,
                "original_id": t.original_id,
                "session_id": t.session_id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat,
                "bank_source": t.bank_source,
            }
            for t in items
        ],
    }


@router.get("/financial-years/{fy_id}/sessions")
def get_archived_sessions(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List archived sessions for a financial year (read-only)."""
    fy = _get_fy_or_404(fy_id, current_user, db)
    sessions = db.query(ArchivedSession).filter(ArchivedSession.financial_year_id == fy.id).all()

    result = []
    for s in sessions:
        txn_count = db.query(func.count(ArchivedTransaction.id)).filter(
            ArchivedTransaction.financial_year_id == fy.id,
            ArchivedTransaction.session_id == s.session_id,
        ).scalar()
        date_stats = db.query(
            func.min(ArchivedTransaction.date),
            func.max(ArchivedTransaction.date),
        ).filter(
            ArchivedTransaction.financial_year_id == fy.id,
            ArchivedTransaction.session_id == s.session_id,
        ).first()
        result.append({
            "session_id": s.session_id,
            "friendly_name": s.friendly_name or s.session_id,
            "locked": bool(s.locked),
            "transaction_count": txn_count,
            "date_from": date_stats[0].isoformat() if date_stats[0] else None,
            "date_to": date_stats[1].isoformat() if date_stats[1] else None,
        })

    return {"financial_year": _serialize_fy(fy), "sessions": result}


@router.get("/financial-years/{fy_id}/reconciliation")
def get_archived_reconciliation(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get archived reconciliation records for a financial year (read-only)."""
    fy = _get_fy_or_404(fy_id, current_user, db)

    monthly = (
        db.query(ArchivedReconciliation)
        .filter(ArchivedReconciliation.financial_year_id == fy.id)
        .order_by(ArchivedReconciliation.month)
        .all()
    )
    overall = (
        db.query(ArchivedOverallReconciliation)
        .filter(ArchivedOverallReconciliation.financial_year_id == fy.id)
        .all()
    )

    return {
        "financial_year": _serialize_fy(fy),
        "monthly": [
            {
                "month": r.month,
                "session_id": r.session_id,
                "opening_balance": r.opening_balance,
                "closing_balance": r.closing_balance,
            }
            for r in monthly
        ],
        "overall": [
            {
                "session_id": o.session_id,
                "system_opening_balance": o.system_opening_balance,
                "bank_closing_balance": o.bank_closing_balance,
            }
            for o in overall
        ],
    }


@router.get("/financial-years/{fy_id}/invoices")
def get_archived_invoices(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List archived invoices for a financial year (read-only)."""
    fy = _get_fy_or_404(fy_id, current_user, db)
    invoices = db.query(ArchivedInvoice).filter(ArchivedInvoice.financial_year_id == fy.id).all()

    return {
        "financial_year": _serialize_fy(fy),
        "invoices": [
            {
                "id": inv.id,
                "original_id": inv.original_id,
                "session_id": inv.session_id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "vat_amount": inv.vat_amount,
                "file_reference": inv.file_reference,
            }
            for inv in invoices
        ],
    }


@router.get("/financial-years/{fy_id}/summary")
def get_archived_summary(
    fy_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return an income/expense summary for an archived financial year,
    grouped by category — used for report exports.
    """
    fy = _get_fy_or_404(fy_id, current_user, db)
    client = db.query(Client).filter(Client.id == fy.client_id).first()
    client_name = client.name if client else None

    rows = (
        db.query(
            ArchivedTransaction.category,
            func.sum(ArchivedTransaction.amount).label("total"),
            func.count(ArchivedTransaction.id).label("count"),
        )
        .filter(ArchivedTransaction.financial_year_id == fy.id)
        .group_by(ArchivedTransaction.category)
        .all()
    )

    total_income = sum(r.total for r in rows if r.total and r.total > 0)
    total_expenses = sum(r.total for r in rows if r.total and r.total < 0)

    return {
        "financial_year": _serialize_fy(fy),
        "client_name": client_name,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net": total_income + total_expenses,
        "by_category": [
            {"category": r.category, "total": r.total, "count": r.count}
            for r in rows
        ],
    }
