"""
Column Mapping routes – manual fallback when bank detection fails.

Flow:
1. Frontend uploads file → gets back "unknown" bank detection
2. Frontend calls POST /column-mapping/preview with the file → gets headers + sample rows
3. User maps columns (date, description, amount/debit/credit) in a modal
4. Frontend calls POST /column-mapping/upload with file + mapping → processes the statement
"""

import csv
import io
import json
import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from models import Client, User, get_db
from routers.dependencies import logger, sanitize_response_data
from routers.upload import (
    _apply_rules_and_save,
    _create_friendly_session,
    _load_enabled_rules,
    _sanitize_amounts,
)
from services.parser import _find_data_start, normalize_csv, parse_date
from rate_limiter import upload_limiter
from validators import validate_csv_upload

router = APIRouter(prefix="/column-mapping", tags=["Column Mapping"])


@router.post("/preview")
async def column_mapping_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Return CSV headers and sample rows so the user can map columns.

    Response:
    {
        "headers": ["Col A", "Col B", ...],
        "sample_rows": [["val1", "val2", ...], ...],
        "row_count": 150
    }
    """
    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")

        # Decode and read CSV
        text = file_content.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)

        if not all_rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")

        # Try smart header detection first
        result = _find_data_start(file_content)
        if result:
            headers, data_rows = result
        else:
            headers = [str(c).strip() for c in all_rows[0]]
            data_rows = all_rows[1:]

        # Return first 5 rows as sample
        sample_rows = []
        for row in data_rows[:5]:
            if isinstance(row, dict):
                sample_rows.append(list(row.values()))
            else:
                sample_rows.append([str(c) for c in row])

        return {
            "headers": headers,
            "sample_rows": sample_rows,
            "row_count": len(data_rows),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")


@router.post("/upload")
async def column_mapping_upload(
    request: Request,
    file: UploadFile = File(...),
    column_mapping: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None,
    preview: bool = False,
):
    """Upload a CSV with user-provided column mapping.

    ``column_mapping`` is a JSON string:
    {
        "date": "Transaction Date",
        "description": "Details",
        "amount": "Amount",           // OR
        "debit": "Debit Column",
        "credit": "Credit Column",
        "date_format": "%d/%m/%Y"     // optional
    }

    Values are the *original* column header names from the CSV.
    """
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)

    try:
        mapping = json.loads(column_mapping)
    except (json.JSONDecodeError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid column_mapping JSON: {e}")

    # Validate mapping has required fields
    if "date" not in mapping:
        raise HTTPException(status_code=400, detail="column_mapping must include 'date'")
    if "amount" not in mapping and ("debit" not in mapping and "credit" not in mapping):
        raise HTTPException(
            status_code=400,
            detail="column_mapping must include 'amount' or 'debit'/'credit'",
        )

    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")

        # Use the ColumnMappingAdapter via normalize_csv
        from services.bank_adapters import ColumnMappingAdapter
        import pandas as pd

        result = _find_data_start(file_content)
        if result is None:
            raise HTTPException(status_code=400, detail="Could not find data in CSV file")

        headers, data_rows = result

        # Build DataFrame
        from services.parser import _clean_rows, is_na

        clean_headers, cleaned_rows = _clean_rows(headers, data_rows)
        if not cleaned_rows:
            raise HTTPException(status_code=400, detail="No data rows found")

        df = pd.DataFrame(cleaned_rows)
        df.columns = clean_headers

        # Apply column mapping adapter
        adapter = ColumnMappingAdapter(mapping)
        df_normalized = adapter.normalize(df)

        if df_normalized.empty:
            raise HTTPException(status_code=400, detail="No valid transactions found with the provided mapping")

        # Convert to transaction list
        transactions = []
        for _, row in df_normalized.iterrows():
            date_str = row.get("Date", "")
            description = row.get("Description", "")
            amount = row.get("Amount", 0.0)

            date_obj = parse_date(date_str)
            if not date_obj:
                continue

            if isinstance(amount, float) and (math.isnan(amount) or math.isinf(amount)):
                amount = 0.0

            transactions.append({
                "date": date_obj,
                "description": description,
                "amount": float(amount),
                "debit_flag": float(amount) < 0,
            })

        if not transactions:
            raise HTTPException(status_code=400, detail="No valid transactions produced")

        bank_source = "manual_mapping"

        if preview:
            serialized = []
            for t in transactions:
                amt = t["amount"]
                if isinstance(amt, float) and (math.isnan(amt) or math.isinf(amt)):
                    amt = 0.0
                serialized.append({
                    "date": t["date"].isoformat(),
                    "description": t["description"],
                    "amount": amt,
                })
            return sanitize_response_data({
                "preview": True,
                "transactions": serialized,
            })

        # Save
        if client_id is not None:
            client = db.query(Client).filter(
                Client.id == client_id, Client.user_id == current_user.id
            ).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        enabled_rules = _load_enabled_rules(db, client_id)
        session_id = str(uuid.uuid4())
        _sanitize_amounts(transactions)
        categories_found = _apply_rules_and_save(
            transactions, enabled_rules, session_id, client_id, bank_source, db, current_user
        )

        filename = file.filename or "Statement"
        _create_friendly_session(filename, session_id, db)

        return sanitize_response_data({
            "session_id": session_id,
            "transaction_count": len(transactions),
            "categories": sorted(list(categories_found)),
            "bank_source": bank_source,
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[COLUMN_MAPPING] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@router.get("/supported-banks")
async def list_supported_banks(current_user: User = Depends(get_current_user)):
    """Return list of all supported banks (from plugin registry)."""
    try:
        from services.bank_plugins.registry import BankRegistry
        import services.bank_plugins  # noqa: F401
        return {"banks": BankRegistry.list_banks()}
    except Exception:
        return {
            "banks": [
                {"bank_id": "standard_bank", "bank_name": "Standard Bank"},
                {"bank_id": "absa", "bank_name": "ABSA Bank"},
                {"bank_id": "capitec", "bank_name": "Capitec Bank"},
                {"bank_id": "fnb", "bank_name": "FNB (First National Bank)"},
                {"bank_id": "nedbank", "bank_name": "Nedbank"},
                {"bank_id": "investec", "bank_name": "Investec Bank"},
            ]
        }
