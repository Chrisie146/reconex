"""
Categories and VAT management routes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from auth import get_current_user
from models import Client, CustomCategory, Transaction, User, get_db
from routers.dependencies import (
    CreateCategoryRequest,
    UpdateCategoryVATRequest,
    VATConfigRequest,
    categories_service,
    ensure_session_access,
    ensure_session_access_lenient,
    logger,
    vat_service,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from config import Config

router = APIRouter(tags=["Categories"])


@router.get("/categories")
def get_categories(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of available transaction categories with transaction counts"""
    try:
        # Verify client ownership if client_id provided
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            categories = categories_service.get_all_categories(session_id, client_id=client_id)

            category_counts = (
                db.query(Transaction.category, func.count(Transaction.id).label("count"))
                .filter(Transaction.session_id == session_id)
                .group_by(Transaction.category)
                .all()
            )
            count_map = {cat: count for cat, count in category_counts}

            categories_with_counts = [
                {"name": cat, "transaction_count": count_map.get(cat, 0)} for cat in categories
            ]
            return {"categories": categories_with_counts}
        else:
            categories = categories_service.get_all_categories(client_id=client_id)
            categories_with_counts = [{"name": cat, "transaction_count": 0} for cat in categories]
            return {"categories": categories_with_counts}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[categories] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.post("/categories")
def create_category(
    request: CreateCategoryRequest,
    session_id: str,
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new custom category scoped to a client"""
    try:
        ensure_session_access(session_id, current_user, db)
        # Verify client ownership if client_id provided
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        success, message = categories_service.create_category(
            session_id, request.category_name, is_income=request.is_income, client_id=client_id
        )
        if not success:
            raise HTTPException(status_code=400, detail=message)

        all_categories = categories_service.get_all_categories(session_id, client_id=client_id)
        return {"success": True, "message": message, "categories": all_categories}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create category: {str(e)}")


@router.delete("/categories/all/custom")
def delete_all_custom_categories(
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all custom (non-built-in) categories for a client"""
    try:
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        query = db.query(CustomCategory).filter(CustomCategory.is_income != None)  # all custom categories
        if client_id is not None:
            query = query.filter(CustomCategory.client_id == client_id)

        count = query.count()
        query.delete(synchronize_session="fetch")
        db.commit()

        return {"success": True, "message": f"Deleted {count} custom category(ies)", "deleted_count": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete categories: {str(e)}")


@router.delete("/categories/{category_name}")
def delete_category(
    category_name: str,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a custom category by name (scoped to client)"""
    try:
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        success, message = categories_service.delete_category(session_id, category_name, client_id=client_id)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete category: {str(e)}")


@router.get("/categories/with-vat")
def get_categories_with_vat(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all categories with their VAT settings"""
    try:
        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        categories = categories_service.get_all_categories_with_vat(session_id, client_id=client_id)
        return {"categories": categories}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get categories: {str(e)}")


@router.patch("/categories/{category_name}/vat")
def update_category_vat(
    category_name: str,
    request: UpdateCategoryVATRequest,
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update VAT settings for a custom category"""
    try:
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        success, message = vat_service.update_category_vat_settings(
            category_name, request.vat_applicable, request.vat_rate, is_income=request.is_income, client_id=client_id
        )
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update VAT settings: {str(e)}")


@router.get("/categories/{category}/transactions")
def get_transactions_for_category(
    category: str,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return transactions for a specific category (by session or client)"""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        if session_id:
            ensure_session_access(session_id, current_user, db)
        
        from services.summary import get_transactions_by_category

        txns = get_transactions_by_category(category, db, session_id=session_id, client_id=client_id)
        return {"transactions": txns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# VAT ENDPOINTS
# =============================================================================


@router.get("/vat/config")
def get_vat_config(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get VAT configuration for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        config = vat_service.get_session_vat_config(session_id)
        if config:
            return {"vat_enabled": config.vat_enabled == 1, "default_vat_rate": config.default_vat_rate}
        return {"vat_enabled": False, "default_vat_rate": 15.0}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get VAT config: {str(e)}")


@router.post("/vat/config")
def update_vat_config(
    session_id: str,
    request: VATConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Enable or disable VAT calculation for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        if request.vat_enabled:
            success, message = vat_service.enable_vat(session_id, request.default_vat_rate)
            if success:
                recalc_success, recalc_msg, stats = vat_service.recalculate_all_transactions(session_id)
                if recalc_success:
                    return {"success": True, "message": message, "recalculation_stats": stats}
                else:
                    return {"success": True, "message": message, "recalculation_error": recalc_msg}
        else:
            success, message = vat_service.disable_vat(session_id)

        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update VAT config: {str(e)}")


@router.post("/vat/recalculate")
def recalculate_vat(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recalculate VAT for all transactions in a session or across all statements for a client"""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")
        
        if session_id:
            ensure_session_access(session_id, current_user, db)
            success, message, stats = vat_service.recalculate_all_transactions(session_id)
        else:
            # Verify client belongs to user
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            success, message, stats = vat_service.recalculate_all_transactions_for_client(client_id)
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to recalculate VAT: {str(e)}")


@router.get("/vat/summary")
def get_vat_summary(
    session_id: str,
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get VAT summary for a session"""
    try:
        ensure_session_access(session_id, current_user, db)
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
        summary = vat_service.get_vat_summary(session_id, start, end)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get VAT summary: {str(e)}")


@router.get("/vat/export")
def export_vat_report(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    export_type: str = "both",
    format: str = "excel",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export VAT report as Excel or CSV"""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access_lenient(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        if export_type not in ["both", "input_only", "output_only"]:
            raise HTTPException(
                status_code=400, detail="export_type must be 'both', 'input_only', or 'output_only'"
            )

        start = date.fromisoformat(date_from) if date_from else None
        end = date.fromisoformat(date_to) if date_to else None

        report_bytes = vat_service.export_vat_report(session_id, start, end, format, client_id, export_type)

        identifier = session_id[:8] if session_id else f"client_{client_id}"
        type_str = export_type.replace("_", "_")
        if format == "csv":
            filename = f"vat_{type_str}_{identifier}.csv"
            media_type = "text/csv"
        else:
            filename = f"vat_{type_str}_{identifier}.xlsx"
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        return StreamingResponse(
            report_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to export VAT report: {str(e)}")
