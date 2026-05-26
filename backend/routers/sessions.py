"""
Session routes: lock, unlock, status, list, delete, bulk-delete, statements, validation-report.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from models import (
    Client,
    Invoice,
    InvoiceMatch,
    OverallReconciliation,
    Reconciliation,
    SessionState,
    Transaction,
    TransactionMerchant,
    User,
    get_db,
)
from routers.dependencies import BulkDeleteSessionsRequest, ensure_session_access

router = APIRouter(tags=["Sessions"])


@router.get("/sessions/{session_id}/validation-report")
def get_validation_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get balance validation report for a statement session."""
    ensure_session_access(session_id, current_user, db)
    transactions = db.query(Transaction).filter(Transaction.session_id == session_id).order_by(Transaction.date.asc()).all()

    if not transactions:
        raise HTTPException(status_code=404, detail=f"No transactions found for session {session_id}")

    verified = sum(1 for t in transactions if t.balance_verified is True)
    failed = sum(1 for t in transactions if t.balance_verified is False)
    no_balance = sum(1 for t in transactions if t.balance_verified is None)

    verified_income = sum(t.amount for t in transactions if t.balance_verified is True and t.amount > 0)
    verified_expenses = sum(t.amount for t in transactions if t.balance_verified is True and t.amount < 0)
    unverified_income = sum(t.amount for t in transactions if t.balance_verified is not True and t.amount > 0)
    unverified_expenses = sum(t.amount for t in transactions if t.balance_verified is not True and t.amount < 0)

    total_income = verified_income + unverified_income
    total_expenses = verified_expenses + unverified_expenses
    total_net = total_income + total_expenses

    failures_by_diff = {}
    for t in transactions:
        if t.balance_verified is False:
            diff_bucket = f">{t.balance_difference:.0f}" if t.balance_difference else "unknown"
            if diff_bucket not in failures_by_diff:
                failures_by_diff[diff_bucket] = 0
            failures_by_diff[diff_bucket] += 1

    return {
        "session_id": session_id,
        "summary": {
            "total_transactions": len(transactions),
            "verified_count": verified,
            "failed_count": failed,
            "no_balance_count": no_balance,
            "verification_rate": f"{verified / max(1, len(transactions) - no_balance) * 100:.1f}%"
            if (len(transactions) - no_balance) > 0
            else "N/A",
        },
        "financials": {
            "verified": {"income": verified_income, "expenses": verified_expenses, "net": verified_income + verified_expenses},
            "unverified": {"income": unverified_income, "expenses": unverified_expenses, "net": unverified_income + unverified_expenses},
            "total": {"income": total_income, "expenses": total_expenses, "net": total_net},
        },
        "failures_by_difference": failures_by_diff,
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "balance_verified": t.balance_verified,
                "balance_difference": t.balance_difference,
                "validation_message": t.validation_message or "",
            }
            for t in transactions
        ],
    }


@router.get("/statements")
def get_statements(
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all uploaded statements (sessions) for a client."""
    try:
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            session_ids = db.query(Transaction.session_id).filter(Transaction.client_id == client_id).distinct().all()
            session_ids = [s[0] for s in session_ids]
        else:
            client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
            if not client_ids:
                return {"statements": []}
            session_ids = db.query(Transaction.session_id).filter(Transaction.client_id.in_(client_ids)).distinct().all()
            session_ids = [s[0] for s in session_ids]

        if not session_ids:
            return {"statements": []}

        sessions = db.query(SessionState).filter(SessionState.session_id.in_(session_ids)).all()

        result = []
        for session in sessions:
            txn_query = db.query(Transaction).filter(Transaction.session_id == session.session_id)
            if client_id:
                txn_query = txn_query.filter(Transaction.client_id == client_id)

            txn_count = txn_query.count()
            if txn_count == 0:
                continue

            date_stats = db.query(
                func.min(Transaction.date).label("min_date"),
                func.max(Transaction.date).label("max_date"),
            ).filter(Transaction.session_id == session.session_id)

            if client_id:
                date_stats = date_stats.filter(Transaction.client_id == client_id)

            stats = date_stats.first()

            result.append({
                "session_id": session.session_id,
                "friendly_name": session.friendly_name or "Unknown Statement",
                "transaction_count": txn_count,
                "date_from": stats.min_date.isoformat() if stats.min_date else None,
                "date_to": stats.max_date.isoformat() if stats.max_date else None,
                "created_at": session.created_at.isoformat() if session.created_at else None,
            })

        result.sort(key=lambda x: x["created_at"] or "", reverse=True)
        return {"statements": result}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/lock")
def lock_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a session as locked/finalized."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not ss:
            ss = SessionState(session_id=session_id, locked=1)
            db.add(ss)
        else:
            ss.locked = 1
        db.commit()
        return {"session_id": session_id, "locked": True, "message": "Session locked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/session/unlock")
def unlock_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unlock a previously locked session."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if not ss:
            return {"session_id": session_id, "locked": False, "message": "Session not found; treated as unlocked"}
        ss.locked = 0
        db.commit()
        return {"session_id": session_id, "locked": False, "message": "Session unlocked"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/session/status")
def session_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return lock status for a session."""
    try:
        ensure_session_access(session_id, current_user, db)
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        locked = bool(ss.locked) if ss else False
        return {"session_id": session_id, "locked": locked}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions")
async def list_sessions(
    request: Request,
    client_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a list of previous upload sessions with basic metadata."""
    try:
        query = db.query(
            Transaction.session_id,
            func.count(Transaction.id).label("txn_count"),
            func.min(Transaction.date).label("date_from"),
            func.max(Transaction.date).label("date_to"),
        )

        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            query = query.filter(Transaction.client_id == client_id)
        else:
            client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
            if not client_ids:
                return {"sessions": []}
            query = query.filter(Transaction.client_id.in_(client_ids))

        rows = query.group_by(Transaction.session_id).all()
        session_ids = [r[0] for r in rows]
        session_state_map = {}
        if session_ids:
            session_states = db.query(SessionState).filter(SessionState.session_id.in_(session_ids)).all()
            session_state_map = {state.session_id: state for state in session_states}

        sessions = []
        for r in rows:
            sid = r[0]
            txn_count = int(r[1] or 0)
            date_from = r[2].isoformat() if r[2] else None
            date_to = r[3].isoformat() if r[3] else None

            ss = session_state_map.get(sid)
            locked = bool(ss.locked) if ss else False

            if ss and ss.friendly_name:
                friendly_name = ss.friendly_name
            elif date_from and date_to:
                from_date = datetime.fromisoformat(date_from)
                to_date = datetime.fromisoformat(date_to)
                friendly_name = f"Statement {from_date.strftime('%b %d')} - {to_date.strftime('%b %d, %Y')}"
            else:
                friendly_name = sid

            sessions.append({
                "session_id": sid,
                "friendly_name": friendly_name,
                "transaction_count": txn_count,
                "date_from": date_from,
                "date_to": date_to,
                "locked": locked,
            })

        sessions.sort(key=lambda s: s.get("date_to") or "", reverse=True)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a session and all associated data."""
    try:
        ensure_session_access(session_id, current_user, db)

        txn_count = db.query(Transaction).filter(Transaction.session_id == session_id).count()
        inv_count = db.query(Invoice).filter(Invoice.session_id == session_id).count()
        merchant_count = db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).count()

        invoice_ids = db.query(Invoice.id).filter(Invoice.session_id == session_id).all()
        invoice_ids = [inv_id[0] for inv_id in invoice_ids]

        db.query(Transaction).filter(Transaction.session_id == session_id).delete()
        db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).delete()

        if invoice_ids:
            db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id.in_(invoice_ids)).delete()

        db.query(Invoice).filter(Invoice.session_id == session_id).delete()
        db.query(Reconciliation).filter(Reconciliation.session_id == session_id).delete()
        db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).delete()
        db.query(SessionState).filter(SessionState.session_id == session_id).delete()

        db.commit()

        return {
            "success": True,
            "message": "Session deleted successfully",
            "deleted_counts": {"transactions": txn_count, "invoices": inv_count, "merchants": merchant_count},
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/bulk-delete")
def bulk_delete_sessions(
    request: BulkDeleteSessionsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple sessions and all their associated data."""
    if not request.session_ids:
        raise HTTPException(status_code=400, detail="No sessions specified")

    try:
        total_txns = 0
        total_invs = 0
        deleted_count = 0

        for session_id in request.session_ids:
            ensure_session_access(session_id, current_user, db)

            txn_count = db.query(Transaction).filter(Transaction.session_id == session_id).count()
            inv_count = db.query(Invoice).filter(Invoice.session_id == session_id).count()

            if txn_count == 0 and inv_count == 0:
                continue

            invoice_ids = db.query(Invoice.id).filter(Invoice.session_id == session_id).all()
            invoice_ids = [inv_id[0] for inv_id in invoice_ids]

            db.query(Transaction).filter(Transaction.session_id == session_id).delete()
            db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).delete()

            if invoice_ids:
                db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id.in_(invoice_ids)).delete()

            db.query(Invoice).filter(Invoice.session_id == session_id).delete()
            db.query(Reconciliation).filter(Reconciliation.session_id == session_id).delete()
            db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).delete()
            db.query(SessionState).filter(SessionState.session_id == session_id).delete()

            total_txns += txn_count
            total_invs += inv_count
            deleted_count += 1

        db.commit()

        return {
            "success": True,
            "message": f"{deleted_count} session(s) deleted successfully",
            "deleted_sessions": deleted_count,
            "total_transactions": total_txns,
            "total_invoices": total_invs,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
