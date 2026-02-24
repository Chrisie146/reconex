"""
Invoice routes: upload, list, match, confirm, download, file uploads.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from auth import get_current_user
from config import Config
from models import Client, Invoice, InvoiceMatch, Transaction, User, get_db
from routers.dependencies import ensure_session_access, generate_file_key, log_file_access, logger
from services import matcher
from services.invoice_parser import extract_invoice_metadata
from services.storage import get_storage

router = APIRouter(tags=["Invoices"])


@router.post("/invoice/upload")
def upload_invoice(
    payload: dict = Body(...),
    session_id: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload invoice metadata for matching."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        ensure_session_access(session_id, current_user, db)

        supplier = payload.get("supplier_name")
        inv_date = payload.get("invoice_date")
        total = payload.get("total_amount")
        if not supplier or not inv_date or total is None:
            raise HTTPException(status_code=400, detail="supplier_name, invoice_date and total_amount are required")

        try:
            if isinstance(inv_date, str):
                inv_date_obj = datetime.fromisoformat(inv_date).date()
            else:
                inv_date_obj = inv_date
        except Exception:
            raise HTTPException(status_code=400, detail="invoice_date must be YYYY-MM-DD")

        inv = Invoice(
            session_id=session_id,
            supplier_name=supplier.strip(),
            invoice_date=inv_date_obj,
            invoice_number=payload.get("invoice_number"),
            total_amount=float(total),
            vat_amount=(float(payload.get("vat_amount")) if payload.get("vat_amount") is not None else None),
            file_reference=payload.get("file_reference"),
        )
        db.add(inv)
        db.commit()
        return {"success": True, "invoice_id": inv.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoices")
def list_invoices(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List invoices for a session or client."""
    try:
        if session_id:
            ensure_session_access(session_id, current_user, db)
            rows = db.query(Invoice).filter(Invoice.session_id == session_id).all()
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            rows = db.query(Invoice).filter(Invoice.client_id == client_id).all()
        else:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "supplier_name": r.supplier_name,
                "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
                "invoice_number": r.invoice_number,
                "total_amount": r.total_amount,
                "vat_amount": r.vat_amount,
                "file_reference": r.file_reference,
            })
        return {"invoices": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoice/match")
def match_invoices(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Attempt matches for all invoices and bank transactions in the session."""
    try:
        ensure_session_access(session_id, current_user, db)

        invoices_db = db.query(Invoice).filter(Invoice.session_id == session_id).all()
        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()

        if not txns_db:
            return {"matches": [], "count": 0, "detail": "No transactions in this session to match against"}

        # Skip invoices that the user has already confirmed or rejected
        locked_statuses = {"confirmed", "rejected"}
        locked_inv_ids = {
            im.invoice_id
            for im in db.query(InvoiceMatch).filter(
                InvoiceMatch.invoice_id.in_([i.id for i in invoices_db]),
                InvoiceMatch.status.in_(locked_statuses),
            ).all()
        }
        # Also skip transactions already confirmed to a different invoice
        locked_txn_ids = {
            im.transaction_id
            for im in db.query(InvoiceMatch).filter(
                InvoiceMatch.status == "confirmed",
                InvoiceMatch.transaction_id.isnot(None),
            ).all()
        }

        invoices_to_match = [
            {
                "id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "vat_amount": inv.vat_amount,
                "file_reference": inv.file_reference,
            }
            for inv in invoices_db
            if inv.id not in locked_inv_ids
        ]
        txns = [
            {"id": t.id, "date": t.date.isoformat() if t.date else None, "description": t.description, "amount": t.amount}
            for t in txns_db
            if t.id not in locked_txn_ids
        ]

        matches = matcher.find_best_matches(invoices_to_match, txns)

        for m in matches:
            inv_id = m.get("invoice_id")
            txn_id = m.get("transaction_id")
            score = int(m.get("score") or 0)
            explanation = m.get("explanation")

            existing = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv_id).first()
            if existing:
                # Never overwrite a confirmed or rejected decision
                if existing.status in locked_statuses:
                    continue
                existing.transaction_id = txn_id
                existing.confidence = score
                existing.explanation = explanation
                existing.status = "suggested"
                existing.suggested_at = datetime.utcnow()
            else:
                im = InvoiceMatch(invoice_id=inv_id, transaction_id=txn_id, confidence=score, explanation=explanation, status="suggested")
                db.add(im)

        db.commit()

        out = []
        for m in matches:
            out.append({
                "invoice_id": m.get("invoice_id"),
                "invoice": m.get("invoice"),
                "suggested_transaction_id": m.get("transaction_id"),
                "transaction": m.get("transaction"),
                "confidence": m.get("score"),
                "classification": m.get("classification"),
                "explanation": m.get("explanation"),
            })

        return {"matches": out, "count": len(out)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoice/match/confirm")
def confirm_match(
    payload: dict = Body(...),
    session_id: str = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """User confirms or rejects a suggested match."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")
        ensure_session_access(session_id, current_user, db)

        inv_id = payload.get("invoice_id")
        txn_id = payload.get("transaction_id")
        confirm = payload.get("confirm")

        if inv_id is None or confirm is None:
            raise HTTPException(status_code=400, detail="invoice_id and confirm are required")

        invoice = db.query(Invoice).filter(Invoice.id == inv_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if invoice.session_id != session_id:
            raise HTTPException(status_code=403, detail="Invoice does not belong to this session")

        im = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv_id).first()
        if not im:
            raise HTTPException(status_code=404, detail="Suggested match not found for this invoice")

        if confirm:
            if txn_id is not None and im.transaction_id != txn_id:
                im.transaction_id = txn_id
            im.status = "confirmed"
            im.confirmed_at = datetime.utcnow()

            txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
            if txn:
                txn.invoice_id = inv_id
        else:
            im.status = "rejected"
            im.confirmed_at = datetime.utcnow()

            txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
            if txn:
                txn.invoice_id = None

        db.commit()
        return {"success": True, "invoice_id": inv_id, "transaction_id": im.transaction_id, "status": im.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/matches")
def list_matches(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List suggested/confirmed/rejected matches for a session."""
    try:
        ensure_session_access(session_id, current_user, db)
        rows = db.query(Invoice, InvoiceMatch).filter(Invoice.session_id == session_id).outerjoin(InvoiceMatch, InvoiceMatch.invoice_id == Invoice.id).all()
        out = []
        for inv, im in rows:
            txn_obj = None
            if im and im.transaction_id:
                txn = db.query(Transaction).filter(Transaction.id == im.transaction_id).first()
                if txn:
                    txn_obj = {"id": txn.id, "date": txn.date.isoformat() if txn.date else None, "description": txn.description, "amount": txn.amount}

            out.append({
                "invoice_id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "total_amount": inv.total_amount,
                "match_status": im.status if im else None,
                "suggested_transaction_id": im.transaction_id if im else None,
                "transaction": txn_obj,
                "confidence": im.confidence if im else None,
                "explanation": im.explanation if im else None,
            })
        return {"matches": out}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/unmatched")
def unmatched_view(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return bank transactions and invoices without confirmed matches."""
    try:
        ensure_session_access(session_id, current_user, db)

        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        invs_db = db.query(Invoice).filter(Invoice.session_id == session_id).all()

        session_inv_ids = [i.id for i in invs_db]
        session_txn_ids = [t.id for t in txns_db]

        # Filter confirmed IDs to this session only
        confirmed_txn_ids = {
            im.transaction_id
            for im in db.query(InvoiceMatch).filter(
                InvoiceMatch.status == "confirmed",
                InvoiceMatch.transaction_id.in_(session_txn_ids),
            ).all()
        }
        confirmed_inv_ids = {
            im.invoice_id
            for im in db.query(InvoiceMatch).filter(
                InvoiceMatch.status == "confirmed",
                InvoiceMatch.invoice_id.in_(session_inv_ids),
            ).all()
        }

        unmatched_txns = [
            {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": t.amount}
            for t in txns_db
            if t.id not in confirmed_txn_ids
        ]
        unmatched_invoices = [
            {"id": i.id, "supplier_name": i.supplier_name, "invoice_date": i.invoice_date.isoformat(), "total_amount": i.total_amount}
            for i in invs_db
            if i.id not in confirmed_inv_ids
        ]

        return {"unmatched_transactions": unmatched_txns, "unmatched_invoices": unmatched_invoices}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/invoice/download")
def download_invoice_file(
    request: Request,
    invoice_id: int,
    session_id: str = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a secure, time-limited download URL for the invoice PDF."""
    try:
        # Look up the invoice by ID first
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Verify ownership: check via session_id (if provided) or the invoice's own session
        effective_session = session_id or inv.session_id
        if effective_session:
            ensure_session_access(effective_session, current_user, db)
        else:
            # No session available – deny access
            raise HTTPException(status_code=403, detail="Cannot verify invoice ownership")

        if not inv.file_reference:
            raise HTTPException(status_code=404, detail="No file attached to this invoice")

        storage = get_storage()
        file_key = inv.file_reference

        if not storage.file_exists(file_key):
            raise HTTPException(status_code=404, detail="Invoice file not found in storage")

        log_file_access(db, current_user.id, file_key, "generate_url", request, inv.id)

        if Config.STORAGE_BACKEND == "local":
            local_path = storage.generate_signed_url(file_key)
            return FileResponse(local_path, media_type="application/pdf", filename=os.path.basename(file_key))
        else:
            signed_url = storage.generate_signed_url(file_key, expiration_seconds=Config.SIGNED_URL_EXPIRATION_SECONDS)
            return {"download_url": signed_url, "expires_in_seconds": Config.SIGNED_URL_EXPIRATION_SECONDS}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoice/upload_file")
async def upload_invoice_file(
    request: Request,
    supplier_name: str = None,
    invoice_date: str = None,
    total_amount: float = None,
    invoice_number: Optional[str] = None,
    vat_amount: Optional[float] = None,
    file: UploadFile = File(None),
    session_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an invoice PDF with metadata."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")
        ensure_session_access(session_id, current_user, db)

        if not supplier_name or not invoice_date or total_amount is None:
            raise HTTPException(status_code=400, detail="supplier_name, invoice_date and total_amount are required")

        try:
            if isinstance(invoice_date, str):
                inv_date_obj = datetime.fromisoformat(invoice_date).date()
            else:
                inv_date_obj = invoice_date
        except Exception:
            raise HTTPException(status_code=400, detail="invoice_date must be YYYY-MM-DD")

        file_key = None
        if file:
            filename = file.filename or "invoice.pdf"
            if not filename.lower().endswith(".pdf"):
                raise HTTPException(status_code=400, detail="Only PDF files are allowed")
            content = await file.read()
            file_key = generate_file_key(filename, prefix="invoices")
            storage = get_storage()
            storage.upload_file(content, file_key, content_type="application/pdf")

        inv = Invoice(
            session_id=session_id,
            supplier_name=supplier_name.strip(),
            invoice_date=inv_date_obj,
            invoice_number=invoice_number,
            total_amount=float(total_amount),
            vat_amount=(float(vat_amount) if vat_amount is not None else None),
            file_reference=file_key,
        )
        db.add(inv)
        db.commit()

        if file_key:
            log_file_access(db, current_user.id, file_key, "upload", request, inv.id)

        return {"success": True, "invoice_id": inv.id, "file_key": file_key}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoice/upload_file_auto")
async def upload_invoice_file_auto(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an invoice PDF and automatically extract metadata, create invoice, and suggest a match."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")
        ensure_session_access(session_id, current_user, db)
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        filename = file.filename or "invoice.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        content = await file.read()
        file_key = generate_file_key(filename, prefix="invoices")
        storage = get_storage()
        storage.upload_file(content, file_key, content_type="application/pdf")

        meta = extract_invoice_metadata(content)
        if not meta.get("supplier_name") and not meta.get("total_amount"):
            raise HTTPException(status_code=400, detail="Failed to extract key fields from invoice.")

        inv = Invoice(
            session_id=session_id,
            supplier_name=(meta.get("supplier_name") or "").strip() or "Unknown Supplier",
            invoice_date=meta.get("invoice_date"),
            invoice_number=meta.get("invoice_number"),
            total_amount=float(meta.get("total_amount") or 0.0),
            vat_amount=(float(meta.get("vat_amount")) if meta.get("vat_amount") is not None else None),
            file_reference=file_key,
        )
        db.add(inv)
        db.commit()

        log_file_access(db, current_user.id, file_key, "upload", request, inv.id)

        txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txns = [{"id": t.id, "date": t.date.isoformat() if t.date else None, "description": t.description, "amount": t.amount} for t in txns_db]
        invoices = [{
            "id": inv.id,
            "supplier_name": inv.supplier_name,
            "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
            "invoice_number": inv.invoice_number,
            "total_amount": inv.total_amount,
            "vat_amount": inv.vat_amount,
            "file_reference": inv.file_reference,
        }]

        matches = matcher.find_best_matches(invoices, txns)
        m = matches[0] if matches else None
        if m:
            existing = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv.id).first()
            if existing:
                existing.transaction_id = m.get("transaction_id")
                existing.confidence = int(m.get("score") or 0)
                existing.explanation = m.get("explanation")
                existing.status = "suggested"
                existing.suggested_at = datetime.utcnow()
            else:
                im = InvoiceMatch(
                    invoice_id=inv.id,
                    transaction_id=m.get("transaction_id"),
                    confidence=int(m.get("score") or 0),
                    explanation=m.get("explanation"),
                    status="suggested",
                )
                db.add(im)
            db.commit()

        return {"success": True, "invoice": invoices[0], "extracted_meta": meta, "suggested_match": m}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invoice/upload_file_direct")
async def upload_invoice_file_direct(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    transaction_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload an invoice PDF and directly link to a specific transaction."""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id query parameter is required")
        ensure_session_access(session_id, current_user, db)
        if not transaction_id:
            raise HTTPException(status_code=400, detail="transaction_id query parameter is required")
        if not file:
            raise HTTPException(status_code=400, detail="file is required")

        filename = file.filename or "invoice.pdf"
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")

        txn = db.query(Transaction).filter(Transaction.id == transaction_id, Transaction.session_id == session_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found in this session")

        content = await file.read()
        file_key = generate_file_key(filename, prefix="invoices")
        storage = get_storage()
        storage.upload_file(content, file_key, content_type="application/pdf")

        # Attempt metadata extraction but do not fail if it returns nothing
        try:
            meta = extract_invoice_metadata(content)
        except Exception:
            meta = {}

        invoice_date = meta.get("invoice_date") or txn.date

        inv = Invoice(
            session_id=session_id,
            supplier_name=(meta.get("supplier_name") or "").strip() or filename,
            invoice_date=invoice_date,
            invoice_number=meta.get("invoice_number"),
            total_amount=float(meta.get("total_amount") or 0.0),
            vat_amount=(float(meta.get("vat_amount")) if meta.get("vat_amount") is not None else None),
            file_reference=file_key,
        )
        db.add(inv)
        db.commit()

        log_file_access(db, current_user.id, file_key, "upload", request, inv.id)

        existing_match = db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == inv.id).first()
        if not existing_match:
            im = InvoiceMatch(
                invoice_id=inv.id,
                transaction_id=transaction_id,
                confidence=100,
                explanation="Directly uploaded for this transaction",
                status="confirmed",
            )
            db.add(im)

        # Explicitly link the invoice to the transaction
        txn.invoice_id = inv.id
        db.commit()

        return {
            "success": True,
            "invoice": {
                "id": inv.id,
                "supplier_name": inv.supplier_name,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "invoice_number": inv.invoice_number,
                "total_amount": inv.total_amount,
                "vat_amount": inv.vat_amount,
                "file_reference": inv.file_reference,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            },
            "transaction_id": transaction_id,
            "message": "Invoice linked successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/invoice/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    session_id: str = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an invoice, its matches, and unlink from any transactions."""
    try:
        inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Verify ownership via provided session_id or the invoice's own session
        effective_session = session_id or inv.session_id
        if effective_session:
            ensure_session_access(effective_session, current_user, db)
        else:
            raise HTTPException(status_code=403, detail="Cannot verify invoice ownership")

        # Unlink any transactions that reference this invoice
        db.query(Transaction).filter(Transaction.invoice_id == invoice_id).update({"invoice_id": None})

        # Delete invoice matches
        db.query(InvoiceMatch).filter(InvoiceMatch.invoice_id == invoice_id).delete()

        # Delete the file from storage if present
        if inv.file_reference:
            try:
                storage = get_storage()
                storage.delete_file(inv.file_reference)
            except Exception:
                pass  # Non-fatal: file may already be gone

        db.delete(inv)
        db.commit()

        return {"success": True, "message": "Invoice deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
