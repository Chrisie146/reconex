"""
Transaction routes: list, update, merchant, bulk categorise/undo, clear, bulk-merchant.
"""

import json
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import String, case, func, or_
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from models import Account, Client, Rule, SessionState, SessionVATConfig, TaskStatus, Transaction, TransactionMerchant, User, get_db
from routers.dependencies import (
    BulkCategorizeRequest,
    ClearCategoriesRequest,
    bulk_categorizer,
    ensure_session_access,
    learning_service,
    logger,
    vat_service,
)
from services.cache import get_cache, cached
from services.categoriser import extract_merchant
from services import posthog_tracker

router = APIRouter(tags=["Transactions"])


def _serialize_transaction_row(t: Transaction, merchant: Optional[str] = None) -> dict:
    return {
        "id": t.id,
        "session_id": t.session_id,
        "date": t.date.isoformat(),
        "description": t.description,
        "amount": t.amount,
        "category": t.category,
        "suggested_category": t.suggested_category,
        "account_id": t.account_id,
        "account_code": t.account.code if t.account else None,
        "account_name": t.account.name if t.account else None,
        "account_type": t.account.account_type if t.account else None,
        "suggested_account_id": t.suggested_account_id,
        "suggested_account_code": t.suggested_account.code if t.suggested_account else None,
        "suggested_account_name": t.suggested_account.name if t.suggested_account else None,
        "suggested_account_type": t.suggested_account.account_type if t.suggested_account else None,
        "mapping_confidence": t.mapping_confidence,
        "mapping_source": t.mapping_source,
        "mapping_reason": t.mapping_reason,
        "invoice_id": t.invoice_id,
        "merchant": merchant,
        "vat_amount": t.vat_amount,
        "amount_excl_vat": t.amount_excl_vat,
        "amount_incl_vat": t.amount_incl_vat,
    }


def _create_task_status(db: Session, task_id: str, user_id: int, task_name: str, message: str) -> None:
    task_status = TaskStatus(
        task_id=task_id,
        user_id=user_id,
        task_name=task_name,
        status="PENDING",
        progress_percent=0,
        progress_message=message,
    )
    db.add(task_status)
    db.commit()


@router.get("/transactions")
async def get_transactions(
    request: Request,
    session_id: Optional[str] = None,
    client_id: Optional[int] = None,
    category: Optional[str] = None,
    q: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "date",
    sort_dir: str = "desc",
    amount_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get transactions for a session or client with server-side filtering, sorting and pagination."""
    # Build base filter conditions (shared between summary and data queries)
    base_conds = []
    if session_id:
        ensure_session_access(session_id, current_user, db)
        base_conds.append(Transaction.session_id == session_id)
    elif client_id:
        client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        base_conds.append(Transaction.client_id == client_id)
    else:
        raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

    if category and category.strip():
        base_conds.append(Transaction.category == category)

    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            base_conds.append(Transaction.date >= df)
        except Exception:
            raise HTTPException(status_code=400, detail="date_from must be YYYY-MM-DD")

    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            base_conds.append(Transaction.date <= dt)
        except Exception:
            raise HTTPException(status_code=400, detail="date_to must be YYYY-MM-DD")

    if q and q.strip():
        like_pattern = f"%{q.strip()}%"
        base_conds.append(
            or_(
                Transaction.description.ilike(like_pattern),
                func.cast(Transaction.amount, String).ilike(like_pattern),
            )
        )

    # Reusable uncategorized condition
    _uncategorized_cond = or_(
        Transaction.category == None,
        Transaction.category == "",
        Transaction.category == "Other",
        Transaction.category == "Uncategorized",
    )

    # Summary stats across ALL base-filtered rows (before amount_filter) — powers the quick-filter chips
    agg = db.query(
        func.count(Transaction.id).label("total"),
        func.coalesce(func.sum(case([(Transaction.amount > 0, 1)], else_=0)), 0).label("income_count"),
        func.coalesce(func.sum(case([(Transaction.amount < 0, 1)], else_=0)), 0).label("expenses_count"),
        func.coalesce(func.sum(case([(_uncategorized_cond, 1)], else_=0)), 0).label("uncategorized_count"),
        func.coalesce(func.sum(case([(Transaction.amount > 0, Transaction.amount)], else_=0)), 0).label("income_total"),
        func.coalesce(func.sum(case([(Transaction.amount < 0, Transaction.amount)], else_=0)), 0).label("expenses_total"),
    ).filter(*base_conds).first()

    summary = {
        "total": int(agg.total or 0),
        "income_count": int(agg.income_count or 0),
        "expenses_count": int(agg.expenses_count or 0),
        "uncategorized_count": int(agg.uncategorized_count or 0),
        "income": float(agg.income_total or 0),
        "expenses": float(abs(agg.expenses_total or 0)),
        "net": float((agg.income_total or 0) + (agg.expenses_total or 0)),
    }

    # Apply amount_filter on top of base conditions
    data_conds = list(base_conds)
    if amount_filter == "income":
        data_conds.append(Transaction.amount > 0)
    elif amount_filter == "expenses":
        data_conds.append(Transaction.amount < 0)
    elif amount_filter == "uncategorized":
        data_conds.append(_uncategorized_cond)

    # Sort column mapping
    _sort_map = {
        "date": Transaction.date,
        "amount": Transaction.amount,
        "description": Transaction.description,
        "category": Transaction.category,
    }
    sort_col = _sort_map.get(sort_by, Transaction.date)
    sort_fn = sort_col.asc() if sort_dir == "asc" else sort_col.desc()

    if limit and limit > 0:
        # Legacy: return a fixed number of rows without pagination
        txn_list = (
            db.query(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.suggested_account))
            .filter(*data_conds)
            .order_by(sort_fn)
            .limit(limit)
            .all()
        )
        total_filtered = len(txn_list)
        page_actual = 1
        page_size_actual = limit
    else:
        page_actual = max(1, page)
        page_size_actual = min(max(1, page_size), 500)
        total_filtered = db.query(func.count(Transaction.id)).filter(*data_conds).scalar() or 0
        offset = (page_actual - 1) * page_size_actual
        txn_list = (
            db.query(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.suggested_account))
            .filter(*data_conds)
            .order_by(sort_fn)
            .offset(offset)
            .limit(page_size_actual)
            .all()
        )

    transaction_ids = [t.id for t in txn_list]
    merchant_map = {}
    if transaction_ids:
        merchant_rows = (
            db.query(TransactionMerchant)
            .filter(TransactionMerchant.transaction_id.in_(transaction_ids))
            .all()
        )
        merchant_map = {row.transaction_id: row.merchant for row in merchant_rows}

    session_names: dict = {}
    if client_id:
        sessions = (
            db.query(SessionState)
            .join(Transaction, Transaction.session_id == SessionState.session_id)
            .filter(Transaction.client_id == client_id)
            .distinct()
            .all()
        )
        session_names = {s.session_id: s.friendly_name for s in sessions}
    elif session_id:
        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss:
            session_names[session_id] = ss.friendly_name

    return {
        "session_id": session_id,
        "count": len(txn_list),
        "total": total_filtered,
        "page": page_actual,
        "page_size": page_size_actual,
        "summary": summary,
        "transactions": [
            {
                "id": t.id,
                "session_id": t.session_id,
                "statement_name": session_names.get(t.session_id, "Unknown Statement"),
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "suggested_category": t.suggested_category,
                "account_id": t.account_id,
                "account_code": t.account.code if t.account else None,
                "account_name": t.account.name if t.account else None,
                "account_type": t.account.account_type if t.account else None,
                "suggested_account_id": t.suggested_account_id,
                "suggested_account_code": t.suggested_account.code if t.suggested_account else None,
                "suggested_account_name": t.suggested_account.name if t.suggested_account else None,
                "suggested_account_type": t.suggested_account.account_type if t.suggested_account else None,
                "mapping_confidence": t.mapping_confidence,
                "mapping_source": t.mapping_source,
                "mapping_reason": t.mapping_reason,
                "invoice_id": t.invoice_id,
                "merchant": merchant_map.get(t.id),
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat,
            }
            for t in txn_list
        ],
    }


@router.put("/transactions/{transaction_id}")
def update_transaction_category(
    transaction_id: int,
    request: dict,
    session_id: str,
    current_user: User = Depends(get_current_user),
    learn_rule: bool = True,
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """Update a single transaction mapping/details in one request."""
    try:
        ensure_session_access(session_id, current_user, db)

        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        category = request.get("category")
        new_description = request.get("description")
        account_supplied = "account_id" in request
        account_id = request.get("account_id")  # Phase 2
        merchant_supplied = "merchant" in request
        merchant = request.get("merchant")
        remember_mapping_rule = bool(request.get("remember_mapping_rule"))
        apply_similar = bool(request.get("apply_similar"))
        rule_keyword = (request.get("keyword") or keyword or "").strip()

        if (
            not category
            and new_description is None
            and not account_supplied
            and not merchant_supplied
            and not remember_mapping_rule
            and not apply_similar
        ):
            raise HTTPException(status_code=400, detail="At least one transaction field is required")

        transaction = db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.session_id == session_id,
        ).first()

        if not transaction:
            txn_any_session = db.query(Transaction).filter(Transaction.id == transaction_id).first()
            session_has_txns = db.query(Transaction).filter(Transaction.session_id == session_id).count()

            if txn_any_session and txn_any_session.session_id != session_id:
                detail = f"Transaction {transaction_id} exists in a different session. Session mismatch."
            elif session_has_txns == 0 and txn_any_session:
                detail = "This session has no transactions. The database may have been reset."
            elif session_has_txns == 0:
                detail = "No transactions found. Please upload a bank statement first."
            else:
                detail = f"Transaction {transaction_id} not found in current session."
            raise HTTPException(status_code=404, detail=detail)

        if category:
            transaction.category = category
            transaction.suggested_category = None  # User confirmed a category — clear any pending suggestion
        if new_description is not None and new_description != transaction.description:
            transaction.description = new_description
            print(f"⚠️  Description updated for transaction {transaction_id}")
        if account_supplied:
            # Validate the account belongs to the same client
            if account_id is None or account_id == 0 or account_id == "":
                transaction.account_id = None
                transaction.suggested_account_id = None
                transaction.mapping_confidence = None
                transaction.mapping_source = None
                transaction.mapping_reason = None
            else:
                account = db.query(Account).filter(
                    Account.id == account_id,
                    Account.client_id == transaction.client_id,
                ).first()
                if not account:
                    raise HTTPException(status_code=404, detail="Account not found for this client")
                transaction.account_id = account.id
                transaction.suggested_account_id = None
                transaction.mapping_confidence = 1.0
                transaction.mapping_source = "user_confirmed"
                transaction.mapping_reason = "User confirmed this account mapping."

        if merchant_supplied:
            merchant_value = (merchant or "").strip() or None
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction.id).first()
            if merchant_value:
                if tm:
                    tm.merchant = merchant_value
                else:
                    db.add(TransactionMerchant(transaction_id=transaction.id, session_id=session_id, merchant=merchant_value))
            elif tm:
                db.delete(tm)
        db.commit()

        cache = get_cache()
        cache.invalidate_session(session_id)

        if category or account_supplied:
            # Check if we should force VAT based on client having any VAT-enabled sessions
            force_vat = False
            if transaction.client_id:
                client_vat_check = db.query(SessionVATConfig).join(
                    Transaction, Transaction.session_id == SessionVATConfig.session_id
                ).filter(
                    Transaction.client_id == transaction.client_id,
                    SessionVATConfig.vat_enabled == 1
                ).first()
                force_vat = client_vat_check is not None
            
            vat_service.apply_vat_to_transaction(transaction_id, session_id, force=force_vat)
            # Refresh to get VAT updates from the service's separate session
            db.refresh(transaction)

        if category:
            try:
                # rule_keyword reads from request body first, then query param — the frontend
                # always sends keyword in the body (never as a query param), so using
                # rule_keyword here (instead of the bare query-param `keyword`) is the only
                # way this block actually executes when called from the UI.
                if rule_keyword and len(rule_keyword) >= 3:
                    # Save keyword as a persistent 'contains' rule for future uploads
                    learned_rules = learning_service.learn_from_categorization(
                        user_id=str(current_user.id),
                        session_id=session_id,
                        description=transaction.description,
                        category=category,
                        merchant=None,
                        keyword=rule_keyword,
                        db=db,
                        client_id=transaction.client_id,
                        account_id=transaction.account_id,  # Phase 2
                    )
                    if learned_rules:
                        print(f"✓ Saved keyword rule: '{rule_keyword.upper()}' \u2192 {category}")

                    # Apply keyword to all similar transactions in the current statement
                    keyword_upper = rule_keyword.upper()
                    matching_transactions = db.query(Transaction).filter(
                        Transaction.session_id == session_id,
                        Transaction.id != transaction_id,
                        Transaction.description.ilike(f"%{keyword_upper}%"),
                    ).all()

                    updated_count = 0
                    for txn in matching_transactions:
                        txn.category = category
                        if transaction.account_id is not None:
                            txn.account_id = transaction.account_id
                        updated_count += 1

                    if updated_count > 0:
                        db.commit()
                        for txn in matching_transactions:
                            vat_service.apply_vat_to_transaction(txn.id, session_id, force=False)
                        print(f"  ✓ Also updated {updated_count} matching transaction(s)")
            except Exception as learn_error:
                print(f"Warning: Failed to save keyword rule: {learn_error}")

        created_rule_id = None
        task_id = None
        if (remember_mapping_rule or learn_rule) and rule_keyword and len(rule_keyword) >= 3 and (transaction.category or transaction.account_id is not None):
            try:
                learned_rules = learning_service.learn_from_categorization(
                    user_id=str(current_user.id),
                    session_id=session_id,
                    description=transaction.description,
                    category=transaction.category,
                    merchant=None,
                    keyword=rule_keyword,
                    db=db,
                    client_id=transaction.client_id,
                    account_id=transaction.account_id,
                )
                if learned_rules and isinstance(learned_rules[0], dict):
                    created_rule_id = learned_rules[0].get("id")
            except Exception as learn_error:
                print(f"Warning: Failed to save keyword rule: {learn_error}")

        if apply_similar and rule_keyword and len(rule_keyword) >= 3:
            try:
                from tasks import transaction_mapping_postprocess_async

                task = transaction_mapping_postprocess_async.delay(
                    transaction_ids=[transaction.id],
                    session_id=session_id,
                    client_id=transaction.client_id,
                    user_id=current_user.id,
                    category=transaction.category,
                    account_id=transaction.account_id,
                    keyword=rule_keyword,
                    source_transaction_id=transaction.id,
                )
                task_id = task.id
                _create_task_status(
                    db,
                    task.id,
                    current_user.id,
                    "transaction_mapping_postprocess_async",
                    "Applying mapping to similar transactions...",
                )
            except Exception as task_error:
                print(f"Warning: Failed to submit mapping post-process task: {task_error}")

        tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction.id).first()
        transaction = db.query(Transaction).options(joinedload(Transaction.account), joinedload(Transaction.suggested_account)).filter(
            Transaction.id == transaction_id,
            Transaction.session_id == session_id,
        ).first()

        response = _serialize_transaction_row(transaction, merchant=tm.merchant if tm else None)
        response["created_rule_id"] = created_rule_id
        response["task_id"] = task_id
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.put("/transactions/{transaction_id}/account")
def update_transaction_account(
    transaction_id: int,
    request: dict,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign (or clear) the Chart-of-Accounts account for a single transaction.

    Body: { account_id: int | null }
    """
    try:
        ensure_session_access(session_id, current_user, db)

        ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id, Transaction.session_id == session_id)
            .first()
        )
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        new_account_id = request.get("account_id")
        if new_account_id is None:
            transaction.account_id = None
        else:
            account = db.query(Account).filter(
                Account.id == new_account_id,
                Account.client_id == transaction.client_id,
            ).first()
            if not account:
                raise HTTPException(status_code=404, detail="Account not found for this client")
            transaction.account_id = account.id
            transaction.suggested_account_id = None
            transaction.mapping_confidence = 1.0
            transaction.mapping_source = "user_confirmed"
            transaction.mapping_reason = "User confirmed this account mapping."

        db.commit()

        # Recalculate VAT with the new account
        force_vat = False
        if transaction.client_id:
            client_vat_check = (
                db.query(SessionVATConfig)
                .join(Transaction, Transaction.session_id == SessionVATConfig.session_id)
                .filter(
                    Transaction.client_id == transaction.client_id,
                    SessionVATConfig.vat_enabled == 1,
                )
                .first()
            )
            force_vat = client_vat_check is not None
        vat_service.apply_vat_to_transaction(transaction_id, session_id, force=force_vat)

        db.refresh(transaction)
        return {
            "id": transaction.id,
            "category": transaction.category,
            "account_id": transaction.account_id,
            "suggested_account_id": transaction.suggested_account_id,
            "mapping_confidence": transaction.mapping_confidence,
            "mapping_source": transaction.mapping_source,
            "mapping_reason": transaction.mapping_reason,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.put("/transactions/{transaction_id}/merchant")
def update_transaction_merchant(
    transaction_id: int,
    request: dict,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update or set merchant for a single transaction."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        merchant = request.get("merchant")
        if merchant is None:
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if session_id and txn.session_id != session_id:
            raise HTTPException(status_code=404, detail="Transaction not found in this session")
        if client_id and txn.client_id != client_id:
            raise HTTPException(status_code=404, detail="Transaction not found for this client")

        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        if str(merchant).strip() == "":
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction_id).first()
            if tm:
                db.delete(tm)
                db.commit()
            return {"id": transaction_id, "merchant": None}

        tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == transaction_id).first()
        if not tm:
            tm = TransactionMerchant(transaction_id=transaction_id, session_id=txn.session_id, merchant=merchant)
            db.add(tm)
        else:
            tm.merchant = merchant

        db.commit()
        return {"id": transaction_id, "merchant": merchant}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transactions/{transaction_id}/merchant/similar")
def apply_merchant_to_similar(
    transaction_id: int,
    request: dict,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply merchant to transactions with the same description."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        merchant = request.get("merchant")
        if merchant is None:
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        # Scope the source transaction lookup
        source_query = db.query(Transaction).filter(Transaction.id == transaction_id)
        if session_id:
            source_query = source_query.filter(Transaction.session_id == session_id)
        if client_id:
            source_query = source_query.filter(Transaction.client_id == client_id)
        source_txn = source_query.first()
        if not source_txn:
            raise HTTPException(status_code=404, detail="Transaction not found")

        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        similar_query = db.query(Transaction).filter(
            Transaction.description == source_txn.description,
            Transaction.id != transaction_id,
        )
        if session_id:
            similar_query = similar_query.filter(Transaction.session_id == session_id)
        if client_id:
            similar_query = similar_query.filter(Transaction.client_id == client_id)
        similar_txns = similar_query.all()

        if not similar_txns:
            return {"updated_count": 0, "message": "No similar transactions found"}

        updated = 0
        for t in similar_txns:
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=t.id, session_id=t.session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if tm.merchant != merchant:
                    tm.merchant = merchant
                    updated += 1

        db.commit()
        return {"updated_count": updated, "message": f"Applied merchant '{merchant}' to {updated} similar transactions"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transactions/clear-categories")
def clear_all_categories(
    request: Optional[ClearCategoriesRequest] = Body(None),
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clear categories from all transactions in a session or client."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        if session_id:
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        if session_id:
            transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            transactions = db.query(Transaction).filter(Transaction.client_id == client_id).all()

        if not transactions:
            return {"success": True, "cleared_count": 0, "message": "No transactions to clear"}

        count = 0
        for txn in transactions:
            if txn.category:
                txn.category = ""
                count += 1

        db.commit()
        return {"success": True, "cleared_count": count, "message": f"Cleared categories from {count} transaction(s)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-categorise/ids")
def bulk_categorize_by_ids(
    payload: dict,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a category to an explicit list of transaction IDs for a session or client."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        ids = payload.get("ids") or []
        category = payload.get("category")
        account_id = payload.get("account_id")  # Phase 2

        if not ids or not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="ids must be a non-empty list")
        if not category and account_id is None:
            raise HTTPException(status_code=400, detail="Either category or account_id is required")

        if session_id:
            txns_db = db.query(Transaction).filter(
                Transaction.session_id == session_id,
                Transaction.id.in_(ids),
            ).all()
        else:
            txns_db = db.query(Transaction).filter(
                Transaction.client_id == client_id,
                Transaction.id.in_(ids),
            ).all()

        if not txns_db:
            raise HTTPException(status_code=404, detail="No matching transactions found for these IDs")

        original_state = [{"id": t.id, "category": t.category, "description": t.description} for t in txns_db]

        # Resolve account if account_id supplied
        resolved_account = None
        if account_id is not None:
            first_txn = txns_db[0]
            resolved_account = db.query(Account).filter(
                Account.id == account_id,
                Account.client_id == first_txn.client_id,
            ).first()
            if not resolved_account:
                raise HTTPException(status_code=404, detail="Account not found for this client")

        for t in txns_db:
            if category:
                t.category = category
            if resolved_account:
                t.account_id = resolved_account.id
                t.suggested_account_id = None
                t.mapping_confidence = 1.0
                t.mapping_source = "user_confirmed"
                t.mapping_reason = "User confirmed this account mapping."
        db.commit()

        cache = get_cache()
        if session_id:
            cache.invalidate_session(session_id)

        try:
            from services.bulk_categorizer import BulkAction

            action_id = str(uuid.uuid4())
            bulk_categorizer.last_action = BulkAction(
                action_id=action_id,
                keyword="by_ids",
                category=category,
                timestamp=datetime.utcnow().isoformat(),
                matched_transactions=original_state,
                transaction_ids=[t["id"] for t in original_state],
            )
        except Exception:
            pass

        task_id = None
        try:
            from tasks import transaction_mapping_postprocess_async

            task = transaction_mapping_postprocess_async.delay(
                transaction_ids=[t.id for t in txns_db],
                session_id=session_id,
                client_id=client_id,
                user_id=current_user.id,
                category=category,
                account_id=resolved_account.id if resolved_account else None,
                keyword=None,
                source_transaction_id=None,
            )
            task_id = task.id
            _create_task_status(
                db,
                task.id,
                current_user.id,
                "transaction_mapping_postprocess_async",
                "Refreshing VAT for mapped transactions...",
            )
        except Exception as task_error:
            print(f"Warning: Failed to submit mapping post-process task: {task_error}")

        updated_transactions_db = (
            db.query(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.suggested_account))
            .filter(Transaction.id.in_([t.id for t in txns_db]))
            .all()
        )
        updated_transactions = [
            _serialize_transaction_row(t)
            for t in updated_transactions_db
        ]

        return {
            "updated_count": len(txns_db),
            "task_id": task_id,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
            "message": f"Updated {len(txns_db)} transaction(s)",
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Bulk by IDs failed: {str(e)}")


@router.post("/bulk-categorise")
def bulk_categorize(
    request: BulkCategorizeRequest,
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a category to all transactions matching a keyword. Supports session_id or client_id (cross-statement)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")
            transactions_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            transactions_db = db.query(Transaction).filter(Transaction.client_id == client_id).all()

        if not transactions_db:
            raise HTTPException(status_code=404, detail="No transactions found")

        transactions = [
            {"id": t.id, "description": t.description, "category": t.category, "date": t.date, "amount": t.amount}
            for t in transactions_db
        ]

        updated_count, updated_txns, error_msg = bulk_categorizer.apply_bulk_categorization(
            transactions, request.keyword, request.category, request.only_uncategorised
        )

        if error_msg:
            raise HTTPException(status_code=400, detail=error_msg)

        if updated_count > 0:
            updated_txn_ids = []
            for txn_dict in updated_txns:
                db.query(Transaction).filter(Transaction.id == txn_dict["id"]).update({"category": txn_dict["category"]})
                updated_txn_ids.append(txn_dict["id"])
            db.commit()

            # When working in client mode, check if VAT is enabled for any session
            force_vat = False
            if client_id:
                # Check if any session for this client has VAT enabled
                client_vat_check = db.query(SessionVATConfig).join(
                    Transaction, Transaction.session_id == SessionVATConfig.session_id
                ).filter(
                    Transaction.client_id == client_id,
                    SessionVATConfig.vat_enabled == 1
                ).first()
                force_vat = client_vat_check is not None

            for txn_id in updated_txn_ids:
                # Look up the transaction's own session_id for VAT calculation
                txn_obj = db.query(Transaction).filter(Transaction.id == txn_id).first()
                if txn_obj:
                    vat_service.apply_vat_to_transaction(txn_id, txn_obj.session_id, force=force_vat)

            # Expire all objects to reload with VAT updates from the service's session
            db.expire_all()

            try:
                if updated_txns:
                    representative_txn = updated_txns[0]
                    txn_db = db.query(Transaction).filter(Transaction.id == representative_txn["id"]).first()
                    if txn_db:
                        merchant = None
                        tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == txn_db.id).first()
                        if tm:
                            merchant = tm.merchant
                        learning_service.learn_from_categorization(
                            user_id=str(current_user.id),
                            session_id=txn_db.session_id,
                            description=txn_db.description,
                            category=request.category,
                            merchant=merchant,
                            keyword=request.keyword,
                            db=db,
                            client_id=txn_db.client_id,
                        )
            except Exception as e:
                print(f"Warning: Failed to learn from bulk categorization: {e}")

        if session_id:
            updated_transactions_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            updated_transactions_db = db.query(Transaction).filter(Transaction.client_id == client_id).all()
        updated_transactions = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
                "vat_amount": t.vat_amount,
                "amount_excl_vat": t.amount_excl_vat,
                "amount_incl_vat": t.amount_incl_vat,
            }
            for t in updated_transactions_db
        ]

        if updated_count > 0:
            cache = get_cache()
            if session_id:
                cache.invalidate_session(session_id)
            elif client_id:
                # Invalidate all sessions for this client
                client_sessions = db.query(Transaction.session_id).filter(
                    Transaction.client_id == client_id
                ).distinct().all()
                for (sid,) in client_sessions:
                    cache.invalidate_session(sid)

        if updated_count > 0:
            posthog_tracker.capture(
                str(current_user.id),
                "transactions_categorised",
                {
                    "count": updated_count,
                    "category": request.category,
                    "method": "bulk",
                    "scope": "session" if session_id else "client",
                },
            )

        return {
            "updated_count": updated_count,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
            "message": f"Updated {updated_count} transaction(s)" if updated_count > 0 else "No matching transactions",
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Bulk categorization failed: {str(e)}")


@router.post("/bulk-categorise/undo")
def undo_bulk_categorize(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Undo the last bulk categorization action."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            transactions_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            transactions_db = db.query(Transaction).filter(Transaction.client_id == client_id).all()
        transactions = [
            {"id": t.id, "description": t.description, "category": t.category, "date": t.date, "amount": t.amount}
            for t in transactions_db
        ]

        success, message, reverted_txns = bulk_categorizer.undo_last_action(transactions)

        if not success:
            raise HTTPException(status_code=400, detail=message)

        if success:
            for txn_dict in reverted_txns:
                db.query(Transaction).filter(Transaction.id == txn_dict["id"]).update({"category": txn_dict["category"]})
            db.commit()

        if session_id:
            updated_transactions_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            updated_transactions_db = db.query(Transaction).filter(Transaction.client_id == client_id).all()
        updated_transactions = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
            }
            for t in updated_transactions_db
        ]

        return {
            "success": success,
            "message": message,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Undo failed: {str(e)}")


@router.post("/bulk-merchant/ids")
def bulk_set_merchant_by_ids(
    payload: dict = Body(...),
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a merchant name to an explicit list of transaction IDs."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        ids = payload.get("ids") or []
        merchant = payload.get("merchant")

        if not ids or not isinstance(ids, list):
            raise HTTPException(status_code=400, detail="ids must be a non-empty list")
        if merchant is None or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            txns_db = db.query(Transaction).filter(Transaction.session_id == session_id, Transaction.id.in_(ids)).all()
        else:
            txns_db = db.query(Transaction).filter(Transaction.client_id == client_id, Transaction.id.in_(ids)).all()
        if not txns_db:
            raise HTTPException(status_code=404, detail="No matching transactions found for these IDs")

        updated = 0
        for t in txns_db:
            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == t.id).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=t.id, session_id=t.session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if tm.merchant != merchant:
                    tm.merchant = merchant
                    updated += 1

        db.commit()
        return {"updated_count": updated, "message": f"Updated {updated} transaction(s) with merchant '{merchant}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk-merchant")
def bulk_set_merchant_by_keyword(
    request: dict = Body(...),
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a merchant to transactions matching a keyword. Supports session_id or client_id (cross-statement)."""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        keyword = request.get("keyword")
        merchant = request.get("merchant")
        only_unassigned = request.get("only_unassigned", True)

        if not merchant or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        if session_id:
            txns_db = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            txns_db = db.query(Transaction).filter(Transaction.client_id == client_id).all()

        transactions = [
            {"id": t.id, "description": t.description, "category": t.category, "date": t.date, "amount": t.amount}
            for t in txns_db
        ]

        from services.bulk_categorizer import BulkCategorizer

        bc = BulkCategorizer()
        matching_ids = bc.find_matching_transactions(transactions, keyword or "", only_uncategorised=only_unassigned)

        if not matching_ids:
            return {"updated_count": 0, "message": "No matching transactions"}

        updated = 0
        for tid in matching_ids:
            # Look up the transaction's own session_id for the merchant record
            txn_obj = db.query(Transaction).filter(Transaction.id == tid).first()
            txn_session_id = txn_obj.session_id if txn_obj else session_id

            tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == tid).first()
            if not tm:
                tm = TransactionMerchant(transaction_id=tid, session_id=txn_session_id, merchant=merchant)
                db.add(tm)
                updated += 1
            else:
                if not only_unassigned or not tm.merchant:
                    if tm.merchant != merchant:
                        tm.merchant = merchant
                        updated += 1

        db.commit()
        return {"updated_count": updated, "message": f"Updated {updated} transaction(s) with merchant '{merchant}'"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/merchants")
def list_merchants(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return list of merchants known for this session."""
    try:
        ensure_session_access(session_id, current_user, db)
        rows = db.query(TransactionMerchant).filter(TransactionMerchant.session_id == session_id).all()
        merchants = {r.merchant for r in rows if r.merchant}

        txns = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        for t in txns:
            m = extract_merchant(t.description)
            if m:
                merchants.add(m)

        return {"merchants": sorted(list(merchants))}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
