"""
Reports routes: summary, category-summary, category-monthly, all exports.
Includes PDF exports, CSV exports, cash flow, merchant analytics, and recurring detection.
"""

import re
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from models import Client, Transaction, TransactionMerchant, User, get_db
from routers.dependencies import ensure_session_access, ensure_session_access_lenient
from services.cache import cached
from services.summary import ExcelExporter, calculate_monthly_summary, get_category_summary
from services.analytics import (
    get_cashflow_series,
    get_merchant_analytics,
    detect_recurring_transactions,
    export_transactions_csv,
    export_summary_csv,
)
from services.pdf_exporter import (
    export_executive_summary_pdf,
    export_transactions_pdf,
    export_category_pdf,
)
from services.vat_service import VATService

router = APIRouter(tags=["Reports"])


def _resolve_include_vat(
    include_vat_requested: bool,
    session_id: Optional[str],
    client_id: Optional[int],
    db: Session,
) -> bool:
    """Return True only when both the caller requested VAT AND it is actually enabled.

    • session-scoped: checks SessionVATConfig for that session.
    • client-scoped:  checks whether any session for the client has VAT enabled.
    """
    if not include_vat_requested:
        return False
    vat_svc = VATService()
    if session_id:
        return vat_svc.is_vat_enabled(session_id)
    if client_id is not None:
        from models import SessionVATConfig
        session_ids = [
            r[0]
            for r in db.query(Transaction.session_id)
            .filter(
                Transaction.client_id == client_id,
                Transaction.session_id.isnot(None),
            )
            .distinct()
            .all()
        ]
        for sid in session_ids:
            if vat_svc.is_vat_enabled(sid):
                return True
    return False


@router.get("/summary")
@cached(ttl=1800)
async def get_summary(
    request: Request,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get monthly summary for a session or client."""
    if not session_id and not client_id:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

    if session_id:
        ensure_session_access_lenient(session_id, current_user, db)
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    summary = calculate_monthly_summary(session_id, db, client_id)
    return summary


@router.get("/category-summary")
@cached(ttl=1800)
async def get_category_totals(
    request: Request,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get total amounts by category for a session or client."""
    if not session_id and not client_id:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

    if session_id:
        ensure_session_access_lenient(session_id, current_user, db)
    if client_id is not None:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

    categories = get_category_summary(session_id, db, client_id)
    return {"categories": categories}


@router.get("/category-monthly")
def get_category_monthly(
    category: str,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return month-to-month totals for a specific category (by session or client)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        
        summary = calculate_monthly_summary(session_id=session_id, db=db, client_id=client_id)
        months = summary.get("months", [])
        series = []
        for m in months:
            series.append({"month": m["month"], "amount": m.get("categories", {}).get(category, 0.0)})
        return {"category": category, "series": series}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================


@router.get("/export/transactions")
def export_transactions(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all transactions to Excel."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        include_vat_bool = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        output = ExcelExporter.export_transactions(session_id, db, client_id, include_vat=include_vat_bool, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="transactions{vat_suffix}_{filename_part}.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/summary")
def export_summary(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export monthly summary to Excel (multi-sheet)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        include_vat_bool = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        summary = calculate_monthly_summary(session_id, db, client_id)

        # Query transactions so exports can compute per-category signed totals and VAT breakdowns
        query = db.query(Transaction)
        if session_id:
            query = query.filter(Transaction.session_id == session_id)
        elif client_id:
            query = query.filter(Transaction.client_id == client_id)
        transactions_list = query.order_by(Transaction.date).all()

        output = ExcelExporter.export_monthly_summary(summary, include_vat=include_vat_bool, transactions=transactions_list, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="summary{vat_suffix}_{filename_part}.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/category")
def export_category(
    category: str,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a single category workbook with month sections."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        output = ExcelExporter.export_category_monthly(session_id, category, db, client_id, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        headers = {"Content-Disposition": f'attachment; filename="category_{category[:16]}_{filename_part}.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/categories")
def export_all_categories(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    include_vat: bool = False,
    categories: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all categories into a single workbook (one sheet per category)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None

        if isinstance(include_vat, str):
            include_vat_bool = include_vat.lower() in ("true", "1", "yes")
        else:
            include_vat_bool = bool(include_vat)

        selected_categories = None
        if categories:
            selected_categories = [c.strip() for c in categories.split(",") if c.strip()]

        output = ExcelExporter.export_all_categories_monthly(
            session_id=session_id,
            db=db,
            client_id=client_id,
            date_from=date_from,
            date_to=date_to,
            include_vat=include_vat_bool,
            selected_categories=selected_categories,
            client_name=client_name,
        )

        client_slug = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else None
        date_suffix = f"{date_from}_to_{date_to}" if date_from and date_to else (f"{client_slug}" if client_slug else (session_id[:8] if session_id else f"client_{client_id}"))
        vat_suffix = "_with_vat" if include_vat_bool else ""
        filename = f"categories{vat_suffix}_{date_suffix}.xlsx"

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/accountant")
def export_for_accountant(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export comprehensive report for accountants."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        include_vat_bool = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        output = ExcelExporter.export_for_accountant(session_id, db, client_id, include_vat=include_vat_bool, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="statement_report{vat_suffix}_{filename_part}.xlsx"'}
        return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


# =============================================================================
# PDF EXPORT ENDPOINTS
# =============================================================================


@router.get("/export/pdf/summary")
def export_pdf_summary(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export executive summary as a branded PDF."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        include_vat_raw = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        include_vat_bool = _resolve_include_vat(include_vat_raw, session_id, client_id, db)
        output = export_executive_summary_pdf(session_id, db, client_id, include_vat=include_vat_bool, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="summary{vat_suffix}_{filename_part}.pdf"'}
        return StreamingResponse(output, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@router.get("/export/pdf/transactions")
def export_pdf_transactions(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export transactions listing as a branded PDF."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        include_vat_raw = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        include_vat_bool = _resolve_include_vat(include_vat_raw, session_id, client_id, db)
        output = export_transactions_pdf(session_id, db, client_id, include_vat=include_vat_bool, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="transactions{vat_suffix}_{filename_part}.pdf"'}
        return StreamingResponse(output, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


@router.get("/export/pdf/categories")
def export_pdf_categories(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    categories: Optional[str] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export per-category report as a branded PDF."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        client_name = client.name if client else None
        selected = [c.strip() for c in categories.split(",") if c.strip()] if categories else None
        include_vat_raw = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        include_vat_bool = _resolve_include_vat(include_vat_raw, session_id, client_id, db)
        output = export_category_pdf(session_id, db, client_id, selected, include_vat=include_vat_bool, client_name=client_name)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="categories{vat_suffix}_{filename_part}.pdf"'}
        return StreamingResponse(output, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF export failed: {str(e)}")


# =============================================================================
# CSV EXPORT ENDPOINTS
# =============================================================================


@router.get("/export/csv/transactions")
def export_csv_transactions(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export all transactions as CSV."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        include_vat_bool = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        output = export_transactions_csv(db, session_id, client_id, include_vat=include_vat_bool)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="transactions{vat_suffix}_{filename_part}.csv"'}
        return StreamingResponse(output, media_type="text/csv", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")


@router.get("/export/csv/summary")
def export_csv_summary(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    include_vat: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export monthly summary as CSV."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        client = None
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        include_vat_bool = include_vat if isinstance(include_vat, bool) else str(include_vat).lower() in ("true", "1", "yes")
        output = export_summary_csv(db, session_id, client_id, include_vat=include_vat_bool)
        filename_part = re.sub(r'[^\w-]', '_', client.name.strip())[:24] if client else (session_id[:8] if session_id else f"client_{client_id}")
        vat_suffix = "_with_vat" if include_vat_bool else ""
        headers = {"Content-Disposition": f'attachment; filename="summary{vat_suffix}_{filename_part}.csv"'}
        return StreamingResponse(output, media_type="text/csv", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================


@router.get("/analytics/cashflow")
def get_cashflow(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get daily cash flow / running balance series for charting."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        return get_cashflow_series(db, session_id, client_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cash flow analysis failed: {str(e)}")


@router.get("/analytics/merchants")
def get_merchants_analytics(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    top_n: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get merchant-level analytics for dashboard visualisation."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        return get_merchant_analytics(db, session_id, client_id, top_n)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merchant analytics failed: {str(e)}")


@router.get("/analytics/recurring")
def get_recurring(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    min_occurrences: int = Query(default=2, ge=2),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detect recurring transactions (subscriptions, rent, insurance, etc.)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        return detect_recurring_transactions(db, session_id, client_id, min_occurrences)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recurring detection failed: {str(e)}")


# =============================================================================
# UNUSUAL / IRREGULAR TRANSACTIONS REPORT
# =============================================================================

@router.get("/unusual")
def get_unusual_transactions(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    above_amount: Optional[float] = Query(default=None),
    below_amount: Optional[float] = Query(default=None),
    round_amount: bool = Query(default=False),
    round_multiple: int = Query(default=100, ge=1),
    recurring: bool = Query(default=False),
    recurring_min_count: int = Query(default=3, ge=2),
    duplicates: bool = Query(default=False),
    duplicate_window_days: int = Query(default=3, ge=1),
    weekend: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return transactions flagged as unusual/irregular based on the selected criteria."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        if not any([above_amount is not None, below_amount is not None, round_amount, recurring, duplicates, weekend]):
            raise HTTPException(status_code=400, detail="At least one filter criterion must be enabled")

        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # ── Fetch transactions ─────────────────────────────────────
        q = db.query(Transaction)
        if session_id:
            q = q.filter(Transaction.session_id == session_id)
        elif client_id is not None:
            q = q.filter(Transaction.client_id == client_id)
        txns = q.order_by(Transaction.date).all()

        # ── Merchant lookup map ────────────────────────────────────
        txn_ids = [t.id for t in txns]
        merchant_map: dict = {}
        if txn_ids:
            merchants = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id.in_(txn_ids)).all()
            for m in merchants:
                merchant_map[m.transaction_id] = m.merchant or ""

        # ── Pre-compute for recurring check ────────────────────────
        # Key: (normalised description, rounded amount) → list of transaction ids
        from collections import defaultdict
        recur_groups: dict = defaultdict(list)
        if recurring:
            for t in txns:
                key = (t.description.strip().lower(), round(abs(t.amount), 2))
                recur_groups[key].append(t.id)
            recurring_ids = {
                tid
                for ids in recur_groups.values()
                if len(ids) >= recurring_min_count
                for tid in ids
            }
        else:
            recurring_ids = set()

        # ── Pre-compute for duplicates check ───────────────────────
        duplicate_ids: set = set()
        if duplicates:
            for i, t in enumerate(txns):
                for j, other in enumerate(txns):
                    if i == j:
                        continue
                    same_desc = t.description.strip().lower() == other.description.strip().lower()
                    same_amt = round(abs(t.amount), 2) == round(abs(other.amount), 2)
                    within_window = abs((t.date - other.date).days) <= duplicate_window_days
                    if same_desc and same_amt and within_window:
                        duplicate_ids.add(t.id)

        # ── Evaluate each transaction ──────────────────────────────
        results = []
        for t in txns:
            flags: List[str] = []
            abs_amt = abs(t.amount)

            if above_amount is not None and abs_amt > above_amount:
                flags.append("above_threshold")

            if below_amount is not None and abs_amt < below_amount and abs_amt > 0:
                flags.append("below_threshold")

            if round_amount and abs_amt > 0 and abs_amt % round_multiple == 0:
                flags.append("round_amount")

            if t.id in recurring_ids:
                flags.append("recurring")

            if t.id in duplicate_ids:
                flags.append("duplicate")

            if weekend and t.date.weekday() >= 5:
                flags.append("weekend")

            if flags:
                results.append({
                    "id": t.id,
                    "date": t.date.isoformat(),
                    "description": t.description,
                    "amount": t.amount,
                    "category": t.category,
                    "merchant": merchant_map.get(t.id, ""),
                    "flags": flags,
                })

        return {
            "total": len(results),
            "transactions": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unusual transactions report failed: {str(e)}")
