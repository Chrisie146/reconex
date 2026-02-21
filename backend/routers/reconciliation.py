"""
Reconciliation routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from models import Client, OverallReconciliation, Reconciliation, Transaction, User, get_db
from routers.dependencies import (
    OverallReconciliationRequest,
    ReconciliationRequest,
    ensure_session_access,
    logger,
)

router = APIRouter(tags=["Reconciliation"])


@router.get("/reconciliation")
def get_reconciliations(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return list of reconciliations for session or client."""
    try:
        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            recs = db.query(Reconciliation).filter(Reconciliation.client_id == client_id).all()
        elif session_id:
            ensure_session_access(session_id, current_user, db)
            recs = db.query(Reconciliation).filter(Reconciliation.session_id == session_id).all()
        else:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        return {
            "reconciliations": [
                {"month": r.month, "opening_balance": r.opening_balance, "closing_balance": r.closing_balance}
                for r in recs
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reconciliation")
def set_reconciliation(
    request: ReconciliationRequest,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a reconciliation record."""
    try:
        month = request.month
        if not month or len(month) != 7:
            raise HTTPException(status_code=400, detail="Month must be in YYYY-MM format")

        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            rec = db.query(Reconciliation).filter(Reconciliation.client_id == client_id, Reconciliation.month == month).first()
            if not rec:
                rec = Reconciliation(client_id=client_id, month=month)
                db.add(rec)
        else:
            ensure_session_access(session_id, current_user, db)
            rec = db.query(Reconciliation).filter(Reconciliation.session_id == session_id, Reconciliation.month == month).first()
            if not rec:
                rec = Reconciliation(session_id=session_id, month=month)
                db.add(rec)

        rec.opening_balance = request.opening_balance
        rec.closing_balance = request.closing_balance
        db.commit()

        return {"success": True, "month": month, "opening_balance": rec.opening_balance, "closing_balance": rec.closing_balance}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reconciliation/overview")
def get_reconciliation_overview(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute overall system balances and return difference vs bank closing balance."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if client_id:
            try:
                client_id = int(client_id)
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid client_id: {client_id}")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            logger.info(f"[reconciliation/overview] Fetching overview for session_id={session_id}")
            total_txn = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.session_id == session_id).scalar()
            overall = db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).first()
            identifier = session_id
        else:
            logger.info(f"[reconciliation/overview] Fetching overview for client_id={client_id}")
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found")
            total_txn = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.client_id == client_id).scalar()
            overall = db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).first()
            identifier = f"client_{client_id}"

        system_opening = overall.system_opening_balance if overall and overall.system_opening_balance is not None else 0.0
        bank_closing = overall.bank_closing_balance if overall and overall.bank_closing_balance is not None else None

        system_closing = system_opening + (total_txn or 0.0)
        difference = None if bank_closing is None else (bank_closing - system_closing)

        return {
            "identifier": identifier,
            "system_opening_balance": system_opening,
            "transactions_total": total_txn,
            "system_closing_balance": system_closing,
            "bank_closing_balance": bank_closing,
            "difference": difference,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[reconciliation/overview] Error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch reconciliation overview: {str(e)}")


@router.post("/reconciliation/overview")
def set_reconciliation_overview(
    request: OverallReconciliationRequest,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update overall opening and bank closing balances."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            logger.info(f"[reconciliation/overview POST] Updating for session_id={session_id}")
            rec = db.query(OverallReconciliation).filter(OverallReconciliation.session_id == session_id).first()
            if not rec:
                rec = OverallReconciliation(session_id=session_id)
                db.add(rec)
            identifier = session_id
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            logger.info(f"[reconciliation/overview POST] Updating for client_id={client_id}")
            rec = db.query(OverallReconciliation).filter(OverallReconciliation.client_id == client_id).first()
            if not rec:
                rec = OverallReconciliation(client_id=client_id)
                db.add(rec)
            identifier = f"client_{client_id}"

        if request.system_opening_balance is not None:
            rec.system_opening_balance = request.system_opening_balance
        if request.bank_closing_balance is not None:
            rec.bank_closing_balance = request.bank_closing_balance

        db.commit()
        logger.info(f"[reconciliation/overview POST] Success: {identifier} updated")

        return {"success": True, "message": "Overall reconciliation updated", "identifier": identifier}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[reconciliation/overview POST] Error: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to update reconciliation: {str(e)}")
