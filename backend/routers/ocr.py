"""
OCR routes: pdf_debug, ocr/regions, ocr/extract.
"""

import io
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from models import User, get_db
from routers.dependencies import ensure_session_access, logger, ocr_region_store
from rate_limiter import upload_limiter
from validators import validate_pdf_upload

router = APIRouter(tags=["OCR"])


@router.post("/pdf_debug")
async def pdf_debug_extract(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Return raw extracted text and table previews per page to help debug parsing."""
    try:
        content = await file.read()
        try:
            from services.pdf_parser import _HAS_PDFPLUMBER, pdfplumber
        except Exception:
            raise HTTPException(status_code=500, detail="PDF debug helper not available")

        if not _HAS_PDFPLUMBER or pdfplumber is None:
            raise HTTPException(status_code=400, detail="pdfplumber not available; install pdfplumber")

        pages_out = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                text_preview = text[:5000]
                tables = []
                try:
                    t = page.extract_tables()
                    for table in t:
                        rows_preview = [[('' if c is None else str(c)) for c in row] for row in table[:10]]
                        tables.append(rows_preview)
                except Exception:
                    tables = []

                pages_out.append({"page": i, "text_preview": text_preview, "tables": tables})

        return {"pages": pages_out}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ocr/regions")
async def save_ocr_regions(
    payload: dict,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save OCR region definitions for a user's session."""
    try:
        ensure_session_access(session_id, current_user, db)

        if not payload:
            raise HTTPException(status_code=400, detail="Payload is required")

        has_pages = "pages" in payload and isinstance(payload["pages"], dict)
        has_single_page = "page" in payload

        if not has_pages and not has_single_page:
            raise HTTPException(status_code=400, detail="Payload must include either 'pages' or 'page'")

        page = int(payload.get("page", 1))
        if has_single_page:
            for key in ["date_region", "description_region", "amount_region", "debit_region", "credit_region"]:
                if key in payload:
                    r = payload[key]
                    for f in ["x", "y", "w", "h"]:
                        if f not in r:
                            raise HTTPException(status_code=400, detail=f"Region {key} missing {f}")
                        v = float(r[f])
                        if v < 0 or v > 1:
                            raise HTTPException(status_code=400, detail=f"Region coordinates must be relative 0..1 for {key}")

        store_key = (current_user.id, session_id)
        entry = ocr_region_store.get(store_key, {"pages": {}, "amount_type": "single"})

        if "pages" in payload and isinstance(payload["pages"], dict):
            for p_str, regs in payload["pages"].items():
                try:
                    pnum = int(p_str)
                except Exception:
                    continue
                regs_filtered = {k: v for k, v in regs.items() if k.endswith("_region")}
                entry["pages"][pnum] = regs_filtered
        else:
            regs_filtered = {k: payload[k] for k in payload if k.endswith("_region")}
            entry["pages"][page] = regs_filtered

        if "amount_type" in payload:
            entry["amount_type"] = payload.get("amount_type", entry.get("amount_type", "single"))

        ocr_region_store[store_key] = entry

        return {"success": True, "message": "Regions saved", "session_id": session_id, "pages_saved": list(entry["pages"].keys())}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ocr/extract")
async def ocr_extract(
    request: Request,
    file: UploadFile = File(...),
    session_id: str = None,
    page: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run OCR extraction using previously saved regions for this session."""
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    await validate_pdf_upload(file)

    try:
        ensure_session_access(session_id, current_user, db)
        store_key = (current_user.id, session_id)
        if not session_id or store_key not in ocr_region_store:
            raise HTTPException(status_code=400, detail="session_id is required and must have saved regions via /ocr/regions")

        content = await file.read()
        saved = ocr_region_store[store_key]
        pages_map = saved.get("pages", {})
        amount_type = saved.get("amount_type", "single")

        from services.ocr_workflow import run_extraction

        results = {}

        if page is not None:
            if int(page) not in pages_map:
                raise HTTPException(status_code=400, detail=f"No regions saved for page {page}")
            res = run_extraction(content, pages_map[int(page)], page=int(page))
            results[int(page)] = res
        else:
            for pnum, regs in pages_map.items():
                res = run_extraction(content, regs, page=int(pnum))
                results[int(pnum)] = res

        return {"success": True, "preview": True, "results": results, "amount_type": amount_type}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
