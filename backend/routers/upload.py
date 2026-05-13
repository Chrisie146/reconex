"""
Upload routes: CSV, PDF, save_parsed, detect-bank.
"""

import json
import math
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from auth import get_current_user
from models import Account, Client, Rule, SessionState, Transaction, User, get_db
from routers.dependencies import (
    learning_service,
    logger,
    sanitize_response_data,
    txn_matches_conditions,
    vat_service,
)
from services.bank_detector import BankDetector
from services.categoriser import MERCHANT_MAPPINGS, categorize_transaction
from services.parser import _find_data_start, normalize_csv, parse_date, validate_csv
from services.pdf_parser import ParserError as PDFParserError
from services.pdf_parser import pdf_to_csv_bytes
from rate_limiter import upload_limiter
from validators import validate_csv_upload, validate_pdf_upload
from services import posthog_tracker

router = APIRouter(tags=["Uploads"])


@router.post("/detect-bank")
async def detect_bank_format(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """Detect the bank format from an uploaded statement file."""
    try:
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")

        try:
            df = _find_data_start(file_content)
            if df is None or df.empty:
                raise HTTPException(status_code=400, detail="Could not parse file")

            headers_list = list(df.columns)
            sample_rows = df.head(3).values.tolist() if len(df) > 0 else []

            bank_type, confidence = BankDetector.detect(headers_list, sample_rows)
            bank_name = BankDetector.get_bank_name(bank_type)

            return {
                "bank_type": bank_type.value,
                "bank_name": bank_name,
                "confidence": round(confidence, 3),
                "message": f"Detected {bank_name} with {confidence:.1%} confidence",
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Detection failed: {str(e)}")


def _load_enabled_rules(db: Session, client_id: Optional[int]) -> list:
    """Load enabled auto-apply rules from DB. Only loads rules scoped to the given client."""
    if client_id is None:
        return []  # Never load rules without tenant scope
    try:
        rules_query = db.query(Rule).filter(Rule.enabled == 1)
        rules_query = rules_query.filter(Rule.client_id == client_id)
        enabled_rules_db = rules_query.order_by(Rule.priority.asc()).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "priority": r.priority,
                "conditions": json.loads(r.conditions),
                "action": json.loads(r.action),
                "auto_apply": bool(r.auto_apply),
            }
            for r in enabled_rules_db
        ]
    except Exception:
        return []


def _sanitize_amounts(transactions: list) -> None:
    """Sanitise NaN / infinity amounts in-place."""
    for t in transactions:
        amount = t.get("amount")
        if isinstance(amount, float) and (math.isnan(amount) or math.isinf(amount)):
            logger.warning(f"[UPLOAD] Invalid amount ({amount}) in transaction: {t.get('description', '?')}, setting to 0.0")
            t["amount"] = 0.0


def _resolve_action_account(db: Session, client_id: Optional[int], action: dict) -> Optional[Account]:
    if client_id is None:
        return None
    account_id = action.get("account_id")
    query = db.query(Account).filter(
        Account.client_id == client_id,
        Account.is_active == True,  # noqa: E712
        Account.is_postable == True,  # noqa: E712
    )
    if account_id is not None:
        return query.filter(Account.id == account_id).first()
    if action.get("account_code"):
        return query.filter(Account.code == action["account_code"]).first()
    return None


def _apply_rules_and_save(
    normalized_transactions: list,
    enabled_rules: list,
    session_id: str,
    client_id: Optional[int],
    bank_source: str,
    db: Session,
    current_user: User,
) -> set:
    """Apply auto-apply rules, persist transactions, return categories found."""
    from models import TransactionMerchant as TM

    categories_found: set = set()

    for txn_data in normalized_transactions:
        raw_category, is_expense = categorize_transaction(txn_data["description"], txn_data["amount"])

        # Built-in rules always confirm directly — no suggestions needed.
        # "Other" means no built-in rule matched → Uncategorized.
        category = raw_category if raw_category != "Other" else "Uncategorized"

        tdict = {
            "description": txn_data["description"],
            "amount": txn_data["amount"],
            "date": txn_data.get("date"),
            "category": category,
        }

        # User-created auto-apply rules override and confirm directly
        account_id = None
        for r in enabled_rules:
            if not r.get("auto_apply"):
                continue
            try:
                if txn_matches_conditions(tdict, r.get("conditions", {})):
                    act = r.get("action", {})
                    if act.get("type") == "set_category" and (act.get("category") or act.get("account_id") is not None):
                        account = _resolve_action_account(db, client_id, act)
                        if act.get("category"):
                            category = act["category"]
                        elif account:
                            category = account.name
                        if account:
                            account_id = account.id
                        break
                    if act.get("type") == "set_account":
                        account = _resolve_action_account(db, client_id, act)
                        if account:
                            account_id = account.id
                            category = account.name
                            break
                    if act.get("type") == "set_merchant" and act.get("merchant"):
                        txn_data["_merchant"] = act["merchant"]
                        break
            except Exception:
                continue

        # Auto-assign merchant from built-in MERCHANT_MAPPINGS if not already set by a user rule
        if not txn_data.get("_merchant"):
            desc_lower = txn_data["description"].lower()
            for mapping in MERCHANT_MAPPINGS:
                for pattern in mapping.get("patterns", []):
                    if pattern.lower() in desc_lower:
                        txn_data["_merchant"] = mapping["merchant"]
                        break
                if txn_data.get("_merchant"):
                    break

        categories_found.add(category)
        transaction = Transaction(
            client_id=client_id,
            session_id=session_id,
            date=txn_data["date"],
            description=txn_data["description"],
            amount=txn_data["amount"],
            category=category,
            account_id=account_id,
            suggested_category=None,
            bank_source=bank_source,
            balance_verified=txn_data.get("balance_verified"),
            balance_difference=txn_data.get("balance_difference"),
            validation_message=txn_data.get("validation_message"),
        )
        db.add(transaction)
        db.flush()

        if txn_data.get("_merchant"):
            tm = TM(transaction_id=transaction.id, session_id=session_id, merchant=txn_data["_merchant"])
            db.add(tm)

    db.commit()

    # Apply keyword-based learned rules — confirmed directly (no suggestions).
    # These rules only exist because the user explicitly created them by typing a
    # keyword, so auto-confirming them is safe and expected behaviour.
    try:
        all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        effective_user_id = str(current_user.id)
        confirmed = learning_service.apply_learned_rules(
            effective_user_id, all_transactions, db, client_id=client_id, override_existing=True
        )

        updated_count = 0
        for txn_id, suggestion in confirmed.items():
            if isinstance(suggestion, (tuple, list)):
                cat, account_id = suggestion[0], suggestion[1] if len(suggestion) > 1 else None
            else:
                cat, account_id = suggestion, None
            txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
            if txn:
                txn.category = cat
                if account_id is not None:
                    txn.account_id = account_id
                txn.suggested_category = None
                categories_found.add(cat)
                updated_count += 1

        if confirmed:
            db.commit()
            print(f"✓ Auto-categorized {updated_count} transaction(s) from keyword rules")
        else:
            print("ℹ️  No keyword rules matched transactions in this upload")
    except Exception as learn_error:
        import traceback
        print(f"Warning: Failed to apply keyword rules: {learn_error}")
        traceback.print_exc()

    return categories_found


def _create_friendly_session(filename: str, session_id: str, db: Session):
    """Create SessionState with a human-friendly name derived from filename."""
    friendly_name = filename.rsplit(".", 1)[0]
    friendly_name = friendly_name.replace("_", " ")
    friendly_name = " ".join(word.capitalize() for word in friendly_name.split())

    ss = SessionState(session_id=session_id, friendly_name=friendly_name)
    db.add(ss)
    db.commit()


@router.post("/upload")
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    preview: bool = False,
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None,
):
    """Upload and process a bank statement CSV file."""
    rate_info = upload_limiter.check_rate_limit(request, current_user.id)
    await validate_csv_upload(file)

    try:
        file_content = await file.read()

        is_valid, error_msg = validate_csv(file_content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {error_msg}")

        normalized_transactions, parse_warnings, skipped_rows, bank_source = normalize_csv(file_content)
        if not normalized_transactions:
            raise HTTPException(status_code=400, detail="No valid transactions found in file")

        print(f"[UPLOAD] Detected bank source: {bank_source}")

        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        enabled_rules = _load_enabled_rules(db, client_id)

        if preview:
            serialized = []
            for t in normalized_transactions:
                amount = t.get("amount")
                if isinstance(amount, float) and (math.isnan(amount) or math.isinf(amount)):
                    amount = 0.0
                serialized.append({"date": t["date"].isoformat(), "description": t["description"], "amount": amount})
            return sanitize_response_data({
                "preview": True,
                "transactions": serialized,
                "warnings": parse_warnings or None,
                "skipped_rows": skipped_rows or None,
            })

        session_id = str(uuid.uuid4())
        _sanitize_amounts(normalized_transactions)
        categories_found = _apply_rules_and_save(
            normalized_transactions, enabled_rules, session_id, client_id, bank_source, db, current_user
        )

        filename = file.filename or "Statement"
        _create_friendly_session(filename, session_id, db)

        posthog_tracker.capture(
            str(current_user.id),
            "statement_parsed_success",
            {
                "file_type": "csv",
                "bank_source": bank_source,
                "transaction_count": len(normalized_transactions),
            },
        )

        return sanitize_response_data({
            "session_id": session_id,
            "transaction_count": len(normalized_transactions),
            "categories": sorted(list(categories_found)),
            "warnings": parse_warnings or None,
            "skipped_rows": skipped_rows or None,
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Upload error: {str(e)}")
        traceback.print_exc()
        posthog_tracker.capture(
            str(current_user.id),
            "statement_parsed_failed",
            {"file_type": "csv", "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@router.post("/upload_pdf")
async def upload_pdf_statement(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    preview: bool = False,
    current_user: User = Depends(get_current_user),
    client_id: Optional[int] = None,
):
    """Upload a PDF bank statement and extract transactions."""
    logger.info(f"[PDF_UPLOAD] Starting upload for user {current_user.id}, file: {file.filename}, client_id: {client_id}, preview: {preview}")

    rate_info = upload_limiter.check_rate_limit(request, current_user.id)

    try:
        await validate_pdf_upload(file)
    except Exception as e:
        logger.error(f"[PDF_UPLOAD] File validation failed for {file.filename}: {str(e)}")
        raise

    try:
        content = await file.read()
        logger.info(f"[PDF_UPLOAD] File read successfully, size: {len(content)} bytes")

        try:
            csv_bytes, statement_year, detected_bank = pdf_to_csv_bytes(content)
            logger.info(f"[PDF_UPLOAD] PDF parsed successfully, detected year: {statement_year}, bank: {detected_bank}")
        except PDFParserError as pe:
            raise HTTPException(status_code=400, detail=str(pe))

        is_valid, error_msg = validate_csv(csv_bytes)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Extracted CSV invalid: {error_msg}")

        normalized_transactions, parse_warnings, skipped_rows, bank_source = normalize_csv(
            csv_bytes, statement_year, detected_bank if "detected_bank" in locals() else None
        )
        if not normalized_transactions:
            raise HTTPException(status_code=400, detail="No transactions could be read from this statement. The file may use an unsupported format — try exporting as CSV from your bank's online portal instead.")

        logger.info(f"[PDF_UPLOAD] Detected bank source: {bank_source}")

        if client_id is not None:
            logger.info(f"[PDF_UPLOAD] Validating client {client_id} belongs to user {current_user.id}")
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                logger.error(f"[PDF_UPLOAD] Client {client_id} not found for user {current_user.id}")
                raise HTTPException(status_code=404, detail=f"Client {client_id} not found or doesn't belong to your account")

        enabled_rules = _load_enabled_rules(db, client_id)

        if preview:
            serialized = []
            for t in normalized_transactions:
                amount = t.get("amount")
                if isinstance(amount, float) and (math.isnan(amount) or math.isinf(amount)):
                    amount = 0.0
                serialized.append({"date": t["date"].isoformat(), "description": t["description"], "amount": amount})
            return sanitize_response_data({
                "preview": True,
                "transactions": serialized,
                "warnings": parse_warnings or None,
                "skipped_rows": skipped_rows or None,
            })

        session_id = str(uuid.uuid4())
        _sanitize_amounts(normalized_transactions)
        categories_found = _apply_rules_and_save(
            normalized_transactions, enabled_rules, session_id, client_id, bank_source, db, current_user
        )

        filename = file.filename or "Statement"
        _create_friendly_session(filename, session_id, db)

        posthog_tracker.capture(
            str(current_user.id),
            "statement_parsed_success",
            {
                "file_type": "pdf",
                "bank_source": bank_source,
                "transaction_count": len(normalized_transactions),
            },
        )

        return sanitize_response_data({
            "session_id": session_id,
            "transaction_count": len(normalized_transactions),
            "categories": sorted(list(categories_found)),
            "bank_source": bank_source,
            "warnings": parse_warnings or None,
            "skipped_rows": skipped_rows or None,
        })
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"[PDF_UPLOAD] Unexpected error: {str(e)}")
        logger.error(f"[PDF_UPLOAD] Traceback: {traceback.format_exc()}")
        posthog_tracker.capture(
            str(current_user.id),
            "statement_parsed_failed",
            {"file_type": "pdf", "error": str(e)},
        )
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@router.post("/save_parsed")
def save_parsed_transactions(
    payload: dict,
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save parsed transactions provided as JSON array of {date, description, amount}."""
    try:
        txns = payload.get("transactions") or []
        if not isinstance(txns, list) or not txns:
            raise HTTPException(status_code=400, detail="transactions must be a non-empty list")

        session_id = str(uuid.uuid4())
        categories_found: set = set()

        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        enabled_rules = _load_enabled_rules(db, client_id)

        for item in txns:
            d = item.get("date")
            desc = item.get("description") or ""
            amount = item.get("amount")
            if not d or amount is None:
                continue

            if isinstance(d, str):
                date_obj = parse_date(d)
                if not date_obj:
                    raise HTTPException(status_code=400, detail=f"Invalid date format: {d}")
            else:
                date_obj = d

            category, _is_expense = categorize_transaction(desc, amount)

            # Built-in rules always confirm directly — "Other" maps to Uncategorized
            category = category if category != "Other" else "Uncategorized"

            tdict = {"description": desc, "amount": amount, "date": date_obj, "category": category}

            account_id = None
            for r in enabled_rules:
                if not r.get("auto_apply"):
                    continue
                try:
                    if txn_matches_conditions(tdict, r.get("conditions", {})):
                        act = r.get("action", {})
                        if act.get("type") == "set_category" and (act.get("category") or act.get("account_id") is not None):
                            account = _resolve_action_account(db, client_id, act)
                            if act.get("category"):
                                category = act["category"]
                            elif account:
                                category = account.name
                            if account:
                                account_id = account.id
                            break
                        if act.get("type") == "set_account":
                            account = _resolve_action_account(db, client_id, act)
                            if account:
                                account_id = account.id
                                category = account.name
                                break
                        if act.get("type") == "set_merchant" and act.get("merchant"):
                            item["_merchant"] = act["merchant"]
                            break
                except Exception:
                    continue

            # Auto-assign merchant from built-in MERCHANT_MAPPINGS if not already set by a user rule
            if not item.get("_merchant"):
                desc_lower = desc.lower()
                for mapping in MERCHANT_MAPPINGS:
                    for pattern in mapping.get("patterns", []):
                        if pattern.lower() in desc_lower:
                            item["_merchant"] = mapping["merchant"]
                            break
                    if item.get("_merchant"):
                        break

            categories_found.add(category)
            transaction = Transaction(
                client_id=client_id,
                session_id=session_id,
                date=date_obj,
                description=desc,
                amount=amount,
                category=category,
                account_id=account_id,
                suggested_category=None,
                balance_verified=item.get("balance_verified"),
                balance_difference=item.get("balance_difference"),
                validation_message=item.get("validation_message"),
            )
            db.add(transaction)
            db.flush()
            if item.get("_merchant"):
                from models import TransactionMerchant as TM
                tm = TM(transaction_id=transaction.id, session_id=session_id, merchant=item["_merchant"])
                db.add(tm)

        db.commit()

        # Apply keyword-based learned rules — confirmed directly
        try:
            all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
            effective_user_id = str(current_user.id)
            confirmed = learning_service.apply_learned_rules(
                effective_user_id, all_transactions, db, client_id=client_id, override_existing=True
            )
            for txn_id, suggestion in confirmed.items():
                if isinstance(suggestion, (tuple, list)):
                    cat, account_id = suggestion[0], suggestion[1] if len(suggestion) > 1 else None
                else:
                    cat, account_id = suggestion, None
                txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
                if txn:
                    txn.category = cat
                    if account_id is not None:
                        txn.account_id = account_id
                    txn.suggested_category = None
                    categories_found.add(cat)
            if confirmed:
                db.commit()
                print(f"✓ Auto-categorized {len(confirmed)} transaction(s) from keyword rules")
            else:
                print("ℹ️  No keyword rules matched transactions in this upload")
        except Exception as learn_error:
            import traceback
            print(f"Warning: Failed to apply keyword rules: {learn_error}")
            traceback.print_exc()

        return sanitize_response_data({
            "session_id": session_id,
            "transaction_count": len(txns),
            "categories": sorted(list(categories_found)),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
