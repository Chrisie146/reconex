"""
Column Mapping routes – manual fallback when bank detection fails.

Flow:
1. Frontend uploads file → gets back "unknown" bank detection
2. Frontend calls POST /column-mapping/preview with the file → gets headers + sample rows
3. User maps columns (date, description, amount/debit/credit) in a modal
4. Frontend calls POST /column-mapping/upload with file + mapping → processes the statement
"""

import io
import json
import math
import uuid
from pathlib import Path
from typing import Any, Optional

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
from services.parser import _clean_rows, _find_data_start, parse_date
from rate_limiter import upload_limiter

router = APIRouter(prefix="/column-mapping", tags=["Column Mapping"])


def _is_pdf(filename: Optional[str], content: bytes) -> bool:
    return bool(filename and Path(filename).suffix.lower() == ".pdf") or content[:5] == b"%PDF-"


def _cell(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _header_score(row: list[str]) -> int:
    text = " ".join(value.lower() for value in row if value)
    score = 0
    if any(token in text for token in ("date", "datum", "posting")):
        score += 2
    if any(token in text for token in ("description", "details", "narration", "particulars", "reference")):
        score += 2
    if any(token in text for token in ("amount", "debit", "credit", "balance", "money in", "money out")):
        score += 2
    return score


def _extract_pdf_table(content: bytes) -> tuple[list[str], list[list[str]]]:
    """Extract a consistent, headered table from a digital PDF."""
    try:
        import pdfplumber
    except ImportError as exc:
        raise HTTPException(status_code=400, detail="PDF table extraction is unavailable. Please export the statement as CSV.") from exc

    candidates: list[tuple[int, list[str], list[list[str]]]] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                for raw_table in page.extract_tables() or []:
                    rows = [[_cell(value) for value in row] for row in raw_table if row and any(_cell(value) for value in row)]
                    if not rows:
                        continue
                    header_index = next((idx for idx, row in enumerate(rows[:5]) if _header_score(row) >= 4), None)
                    if header_index is None or len(rows[header_index]) < 3:
                        continue
                    headers = rows[header_index]
                    candidates.append((_header_score(headers), headers, rows[header_index + 1:]))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not extract a table from this PDF. Please export the statement as CSV.") from exc

    if not candidates:
        raise HTTPException(
            status_code=400,
            detail="This PDF has no extractable transaction table. For scanned PDFs, use the OCR region workflow, or export the statement as CSV.",
        )

    _, headers, first_rows = max(candidates, key=lambda item: item[0])
    signature = tuple(value.lower() for value in headers)
    data_rows = list(first_rows)
    for _, candidate_headers, rows in candidates:
        if tuple(value.lower() for value in candidate_headers) == signature and rows is not first_rows:
            data_rows.extend(rows)
    return headers, data_rows


def _read_mappable_table(content: bytes, filename: Optional[str]) -> tuple[list[str], list[list[str]], str]:
    if _is_pdf(filename, content):
        headers, rows = _extract_pdf_table(content)
        return headers, rows, "pdf_table"
    result = _find_data_start(content)
    if result is None:
        raise HTTPException(status_code=400, detail="CSV file is empty or no data found")
    headers, rows = result
    return [str(header).strip() for header in headers], rows, "csv"


def _validate_mapping(mapping: dict, headers: list[str]) -> None:
    for field in ("date", "description"):
        if not isinstance(mapping.get(field), str) or not mapping[field].strip():
            raise HTTPException(status_code=400, detail=f"column_mapping must include '{field}'")

    has_amount = bool(mapping.get("amount"))
    has_split = bool(mapping.get("debit")) or bool(mapping.get("credit"))
    if has_amount == has_split:
        raise HTTPException(status_code=400, detail="Choose either one amount column or at least one debit/credit column")

    selected = {key: value for key, value in mapping.items() if key in {"date", "description", "amount", "debit", "credit", "balance"} and value}
    missing = [f"{field} column '{column}' was not found" for field, column in selected.items() if column not in set(headers)]
    if missing:
        raise HTTPException(status_code=400, detail="; ".join(missing))
    if len(set(selected.values())) != len(selected):
        raise HTTPException(status_code=400, detail="Each mapped field must use a different source column")


def _mapped_transactions(content: bytes, filename: Optional[str], mapping: dict) -> tuple[list[dict], int, str]:
    headers, data_rows, source_format = _read_mappable_table(content, filename)
    _validate_mapping(mapping, headers)

    from services.bank_adapters import ColumnMappingAdapter
    import pandas as pd

    clean_headers, cleaned_rows = _clean_rows(headers, data_rows)
    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No data rows found")
    df = pd.DataFrame(cleaned_rows)
    df.columns = clean_headers
    normalized = ColumnMappingAdapter(mapping).normalize(df)
    skipped_count = max(0, len(cleaned_rows) - len(normalized))

    transactions = []
    for _, row in normalized.iterrows():
        date_obj = parse_date(row.get("Date", ""))
        amount = row.get("Amount")
        if not date_obj or amount is None:
            skipped_count += 1
            continue
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            skipped_count += 1
            continue
        if math.isnan(amount) or math.isinf(amount):
            skipped_count += 1
            continue
        transactions.append({
            "date": date_obj,
            "description": row.get("Description") or "(No description)",
            "amount": amount,
            "debit_flag": amount < 0,
        })
        if "Balance" in row and row.get("Balance") is not None:
            try:
                transactions[-1]["balance"] = float(row["Balance"])
            except (TypeError, ValueError):
                transactions[-1]["balance"] = None

    if any("balance" in transaction for transaction in transactions):
        from services.balance_validator import BalanceValidator
        transactions, _ = BalanceValidator.validate_transactions(transactions)
    return transactions, skipped_count, source_format


@router.post("/preview")
async def column_mapping_preview(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Return CSV or digital-PDF table headers and sample rows so the user can map columns.

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

        headers, data_rows, source_format = _read_mappable_table(file_content, file.filename)

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
            "format": source_format,
            "extraction_status": "table_extracted" if source_format == "pdf_table" else "csv",
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
    if not isinstance(mapping, dict):
        raise HTTPException(status_code=400, detail="column_mapping must be a JSON object")

    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")

        transactions, skipped_count, source_format = _mapped_transactions(file_content, file.filename, mapping)

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
            "skipped_count": skipped_count,
            "categories": sorted(list(categories_found)),
            "bank_source": bank_source,
            "format": source_format,
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
