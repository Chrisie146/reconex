"""
Categorization rules routes (session-based and client-based).
Includes learned rules endpoints.
"""

import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from auth import get_current_user
from exceptions import AppException
from models import Client, Rule, SessionState, Transaction, TransactionMerchant, User, UserCategorizationRule, get_db
from routers.dependencies import (
    BulkApplyRulesRequest,
    CreateRuleRequest,
    UpdateRuleRequest,
    categories_service,
    ensure_session_access,
    learning_service,
    logger,
    txn_matches_conditions,
    vat_service,
)

router = APIRouter(tags=["Rules"])


# =============================================================================
# SESSION-BASED RULES (via CategoriesService in-memory)
# =============================================================================


@router.get("/session-rules", tags=["Rules"])
def get_session_rules(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all categorization rules for this session (in-memory rules)"""
    try:
        ensure_session_access(session_id, current_user, db)
        rules = categories_service.get_rules(session_id)
        return {"rules": rules}
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch rules: {str(e)}")


@router.post("/session-rules", tags=["Rules"])
def create_session_rule(
    request: CreateRuleRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new categorization rule (in-memory, session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        rule_id = str(uuid.uuid4())
        success, message = categories_service.create_rule(
            session_id=session_id,
            rule_id=rule_id,
            name=request.name,
            category=request.category,
            keywords=request.keywords,
            priority=request.priority,
            auto_apply=request.auto_apply,
            match_compound_words=request.match_compound_words,
        )
        if not success:
            raise HTTPException(status_code=400, detail=message)

        return {
            "success": True,
            "message": message,
            "rule_id": rule_id,
            "rules": categories_service.get_rules(session_id),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create rule: {str(e)}")


@router.put("/session-rules/{rule_id}", tags=["Rules"])
def update_session_rule(
    rule_id: str,
    request: UpdateRuleRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a categorization rule (in-memory, session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        updates = {k: v for k, v in request.dict().items() if v is not None}
        success, message = categories_service.update_rule(session_id, rule_id, **updates)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "rules": categories_service.get_rules(session_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update rule: {str(e)}")


@router.delete("/session-rules/{rule_id}", tags=["Rules"])
def delete_session_rule(
    rule_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a categorization rule (in-memory, session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        success, message = categories_service.delete_rule(session_id, rule_id)
        if not success:
            raise HTTPException(status_code=400, detail=message)
        return {"success": True, "message": message, "rules": categories_service.get_rules(session_id)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete rule: {str(e)}")


@router.post("/session-rules/{rule_id}/preview", tags=["Rules"])
def preview_session_rule(
    rule_id: str,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview which transactions would match a specific rule (session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {"id": t.id, "date": t.date, "description": t.description, "amount": t.amount, "category": t.category}
            for t in transactions
        ]
        preview = categories_service.preview_rule_matches(session_id, rule_id, txn_dicts)
        return preview
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to preview rule: {str(e)}")


@router.post("/session-rules/apply-bulk", tags=["Rules"])
def apply_rules_bulk(
    request: BulkApplyRulesRequest,
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply rules to all transactions in a session (session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {"id": t.id, "date": t.date, "description": t.description, "amount": t.amount, "category": t.category}
            for t in transactions
        ]

        result = categories_service.apply_rules_to_transactions(
            session_id, txn_dicts, rule_ids=request.rule_ids, auto_apply_only=request.auto_apply_only
        )

        updated_ids = []
        for txn_dict in result["transactions"]:
            txn = db.query(Transaction).filter(Transaction.id == txn_dict["id"]).first()
            if txn and txn.category != txn_dict.get("category"):
                txn.category = txn_dict.get("category")
                updated_ids.append(txn.id)

        db.commit()

        for txn_id in updated_ids:
            vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)

        return {
            "success": True,
            "message": f"Applied {result['rules_applied']} rule(s) to {result['updated']} transaction(s)",
            "updated_count": result["updated"],
            "rules_applied": result["rules_applied"],
        }
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to apply rules: {str(e)}")


@router.get("/session-rules/statistics", tags=["Rules"])
def get_rule_statistics(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get statistics for all rules (session scope)"""
    try:
        ensure_session_access(session_id, current_user, db)
        transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        txn_dicts = [
            {"id": t.id, "date": t.date, "description": t.description, "amount": t.amount, "category": t.category}
            for t in transactions
        ]
        stats = categories_service.get_rule_statistics(session_id, txn_dicts)
        return {"statistics": stats}
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch statistics: {str(e)}")


# =============================================================================
# DATABASE-BACKED RULES (client-scoped)
# =============================================================================


@router.get("/rules")
def list_rules(
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all categorization rules (database-backed, client scope)"""
    try:
        if client_id:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            rows = db.query(Rule).filter(Rule.client_id == client_id).order_by(Rule.priority.asc()).all()
        else:
            client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
            rows = db.query(Rule).filter(Rule.client_id.in_(client_ids)).order_by(Rule.priority.asc()).all()

        out = []
        for r in rows:
            out.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "enabled": bool(r.enabled),
                    "priority": r.priority,
                    "conditions": json.loads(r.conditions),
                    "action": json.loads(r.action),
                    "auto_apply": bool(r.auto_apply),
                }
            )
        return {"rules": out}
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rules")
def create_rule(
    request: dict,
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new rule (database-backed). Body: { name, enabled, priority, conditions, action, auto_apply }"""
    try:
        name = request.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        conditions = request.get("conditions")
        action = request.get("action")
        if conditions is None or action is None:
            raise HTTPException(status_code=400, detail="conditions and action are required")

        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        r = Rule(
            client_id=client_id,
            name=name,
            enabled=1 if request.get("enabled", True) else 0,
            priority=int(request.get("priority", 100)),
            conditions=json.dumps(conditions),
            action=json.dumps(action),
            auto_apply=1 if request.get("auto_apply", False) else 0,
        )
        db.add(r)
        db.commit()
        return {"success": True, "id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a database-backed rule"""
    try:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

        # Verify ownership: rule must have a client_id and that client must belong to the current user
        if not r.client_id:
            raise HTTPException(status_code=403, detail="Access denied: unscoped rule")
        client = db.query(Client).filter(Client.id == r.client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=403, detail="Access denied")

        if "name" in request:
            r.name = request.get("name")
        if "enabled" in request:
            r.enabled = 1 if request.get("enabled") else 0
        if "priority" in request:
            r.priority = int(request.get("priority"))
        if "conditions" in request:
            r.conditions = json.dumps(request.get("conditions"))
        if "action" in request:
            r.action = json.dumps(request.get("action"))
        if "auto_apply" in request:
            r.auto_apply = 1 if request.get("auto_apply") else 0
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a database-backed rule"""
    try:
        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

        # Verify ownership: rule must have a client_id and that client must belong to the current user
        if not r.client_id:
            raise HTTPException(status_code=403, detail="Access denied: unscoped rule")
        client = db.query(Client).filter(Client.id == r.client_id, Client.user_id == current_user.id).first()
        if not client:
            raise HTTPException(status_code=403, detail="Access denied")

        db.delete(r)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rules/{rule_id}/preview")
def preview_rule(
    rule_id: int,
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview a rule against a session: body { session_id: '...' }"""
    try:
        sid = payload.get("session_id")
        if not sid:
            raise HTTPException(status_code=400, detail="session_id is required")

        ensure_session_access(sid, current_user, db)

        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

        if r.client_id:
            client = db.query(Client).filter(Client.id == r.client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=403, detail="Access denied")

        conds = json.loads(r.conditions)
        txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        matches = []
        for t in txns_db:
            td = {"id": t.id, "description": t.description, "amount": t.amount, "date": t.date, "category": t.category}
            if txn_matches_conditions(td, conds):
                matches.append({"id": t.id, "description": t.description, "amount": t.amount, "category": t.category})
        return {"matches": matches, "count": len(matches)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rules/{rule_id}/apply")
def apply_rule(
    rule_id: int,
    payload: dict,
    session_id: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a rule to a session."""
    from routers.dependencies import bulk_categorizer
    from services.bulk_categorizer import BulkAction

    try:
        sid = session_id or payload.get("session_id")
        if not sid:
            raise HTTPException(status_code=400, detail="session_id is required")

        ensure_session_access(sid, current_user, db)

        ss = db.query(SessionState).filter(SessionState.session_id == sid).first()
        if ss and ss.locked:
            raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        r = db.query(Rule).filter(Rule.id == rule_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Rule not found")

        if r.client_id:
            client = db.query(Client).filter(Client.id == r.client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=403, detail="Access denied")

        conds = json.loads(r.conditions)
        action = json.loads(r.action)

        txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        matched = []
        original_state = []
        for t in txns_db:
            td = {"id": t.id, "description": t.description, "amount": t.amount, "date": t.date, "category": t.category}
            if txn_matches_conditions(td, conds):
                matched.append(t.id)
                original_state.append({"id": t.id, "category": t.category, "description": t.description})

        if not matched:
            return {"updated_count": 0, "message": "No matching transactions"}

        updated_count = 0
        if action.get("type") == "set_category" and action.get("category"):
            newcat = action["category"]
            for tid in matched:
                db.query(Transaction).filter(Transaction.id == tid).update({"category": newcat})
                updated_count += 1
            db.commit()

            try:
                action_id = str(uuid.uuid4())
                bulk_categorizer.last_action = BulkAction(
                    action_id=action_id,
                    keyword=f"rule:{r.id}",
                    category=newcat,
                    timestamp=datetime.utcnow().isoformat(),
                    matched_transactions=original_state,
                    transaction_ids=[t["id"] for t in original_state],
                )
            except Exception:
                pass

        elif action.get("type") == "set_merchant" and action.get("merchant"):
            newm = action["merchant"]
            for tid in matched:
                tm = db.query(TransactionMerchant).filter(TransactionMerchant.transaction_id == tid).first()
                if not tm:
                    tm = TransactionMerchant(transaction_id=tid, session_id=sid, merchant=newm)
                    db.add(tm)
                    updated_count += 1
                else:
                    if tm.merchant != newm:
                        tm.merchant = newm
                        updated_count += 1
            db.commit()

        updated_txns_db = db.query(Transaction).filter(Transaction.session_id == sid).all()
        updated_transactions = [
            {"id": t.id, "date": t.date.isoformat(), "description": t.description, "amount": t.amount, "category": t.category}
            for t in updated_txns_db
        ]

        return {
            "updated_count": updated_count,
            "transactions": updated_transactions,
            "undo_available": bulk_categorizer.get_last_action_info() is not None,
            "message": f"Updated {updated_count} transaction(s)",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# LEARNED RULES
# =============================================================================


@router.get("/learned-rules")
def get_learned_rules(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all auto-learned categorization rules for this user, optionally scoped to a client"""
    try:
        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
        effective_user_id = str(current_user.id)
        rules = learning_service.get_learned_rules(effective_user_id, db, client_id=client_id)
        return {"rules": rules, "total": len(rules)}
    except (HTTPException, AppException):
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch learned rules: {str(e)}")


@router.put("/learned-rules/{rule_id}")
def update_learned_rule(
    rule_id: int,
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a learned rule (enable/disable, change category, edit pattern)"""
    try:
        effective_user_id = str(current_user.id)
        success, message = learning_service.update_rule(rule_id, effective_user_id, request, db)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {str(e)}")


@router.delete("/learned-rules/all")
def delete_all_learned_rules(
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all learned rules for the current user, optionally scoped to a client"""
    try:
        effective_user_id = str(current_user.id)
        query = db.query(UserCategorizationRule).filter(UserCategorizationRule.user_id == effective_user_id)

        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            query = query.filter(UserCategorizationRule.client_id == client_id)

        count = query.count()
        query.delete(synchronize_session="fetch")
        db.commit()

        return {"success": True, "message": f"Deleted {count} learned rule(s)", "deleted_count": count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete learned rules: {str(e)}")


@router.delete("/learned-rules/{rule_id}")
def delete_learned_rule(
    rule_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a learned categorization rule"""
    try:
        effective_user_id = str(current_user.id)
        success, message = learning_service.delete_rule(rule_id, effective_user_id, db)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {str(e)}")


@router.post("/learned-rules/apply")
def apply_learned_rules(
    session_id: Optional[str] = Query(default=None),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply all learned rules to uncategorized transactions — for a session or all client transactions"""
    try:
        if not session_id and not client_id:
            raise HTTPException(status_code=400, detail="Either session_id or client_id must be provided")

        effective_user_id = str(current_user.id)

        if client_id is not None:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        if session_id:
            ensure_session_access(session_id, current_user, db)
            ss = db.query(SessionState).filter(SessionState.session_id == session_id).first()
            if ss and ss.locked:
                raise HTTPException(status_code=403, detail="Session is locked and cannot be modified")

        # Get transactions: all client transactions if client_id given, else just the session
        if client_id is not None:
            transactions = db.query(Transaction).filter(Transaction.client_id == client_id).all()
        elif session_id:
            transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        else:
            transactions = []

        # override_existing=True: user explicitly wants their learned rules applied,
        # so they should win over any auto-assigned categories
        suggestions = learning_service.apply_learned_rules(
            effective_user_id, transactions, db, client_id=client_id, override_existing=True
        )

        updated_count = 0
        updated_ids = []
        for txn_id, category in suggestions.items():
            txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
            if txn:
                txn.category = category
                updated_count += 1
                updated_ids.append((txn_id, txn.session_id))

        db.commit()

        for txn_id, txn_session_id in updated_ids:
            if txn_session_id:
                vat_service.apply_vat_to_transaction(txn_id, txn_session_id, force=False)

        return {
            "success": True,
            "message": f"Auto-categorized {updated_count} transaction(s)",
            "updated_count": updated_count,
            "suggestions": suggestions,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply learned rules: {str(e)}")


# =============================================================================
# MERCHANT RULES
# =============================================================================


@router.post("/merchant-rules/learn")
def upsert_merchant_rule(
    request: dict = Body(...),
    client_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create or update a merchant auto-apply rule based on a keyword in description."""
    try:
        keyword = (request.get("keyword") or "").strip()
        merchant = request.get("merchant")
        auto_apply = bool(request.get("auto_apply", True))
        enabled = bool(request.get("enabled", True))

        if not keyword or len(keyword) < 3:
            raise HTTPException(status_code=400, detail="keyword must be at least 3 characters")
        if merchant is None or not str(merchant).strip():
            raise HTTPException(status_code=400, detail="merchant is required")

        # Require client_id for tenant isolation
        if client_id is None:
            # Fall back to user's first client
            first_client = db.query(Client).filter(Client.user_id == current_user.id).first()
            if not first_client:
                raise HTTPException(status_code=400, detail="No client found for user. Create a client first.")
            client_id = first_client.id
        else:
            client = db.query(Client).filter(Client.id == client_id, Client.user_id == current_user.id).first()
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")

        keyword_norm = keyword.lower()
        existing_rule = None

        # Only search rules belonging to this client
        rules = db.query(Rule).filter(Rule.client_id == client_id).all()
        for r in rules:
            try:
                conds = json.loads(r.conditions)
                action_data = json.loads(r.action)
            except Exception:
                continue

            if action_data.get("type") != "set_merchant":
                continue

            clauses = conds.get("conditions", []) if isinstance(conds, dict) else []
            for clause in clauses:
                if (
                    clause.get("field") == "description"
                    and clause.get("op") == "contains"
                    and str(clause.get("value", "")).strip().lower() == keyword_norm
                ):
                    existing_rule = r
                    break
            if existing_rule:
                break

        if existing_rule:
            action_data = json.loads(existing_rule.action)
            action_data["type"] = "set_merchant"
            action_data["merchant"] = merchant
            existing_rule.action = json.dumps(action_data)
            existing_rule.auto_apply = 1 if auto_apply else 0
            existing_rule.enabled = 1 if enabled else 0
            existing_rule.name = f"Merchant: {merchant} ({keyword})"
            db.commit()
            return {"success": True, "updated": True, "id": existing_rule.id}

        conditions = {"match_type": "all", "conditions": [{"field": "description", "op": "contains", "value": keyword}]}
        action_data = {"type": "set_merchant", "merchant": merchant}

        r = Rule(
            client_id=client_id,
            name=f"Merchant: {merchant} ({keyword})",
            enabled=1 if enabled else 0,
            priority=int(request.get("priority", 100)),
            conditions=json.dumps(conditions),
            action=json.dumps(action_data),
            auto_apply=1 if auto_apply else 0,
        )
        db.add(r)
        db.commit()
        return {"success": True, "created": True, "id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# CLONE / COPY RULES & CATEGORIES BETWEEN CLIENTS
# =============================================================================


@router.post("/rules/clone")
def clone_rules_to_client(
    request: dict = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clone (copy) rules and/or categories from one client to another.
    Body: {
        source_client_id: int,
        target_client_id: int,
        include_rules: bool (default True),
        include_categories: bool (default True),
        include_learned_rules: bool (default True)
    }
    """
    from models import CustomCategory, UserCategorizationRule

    try:
        source_id = request.get("source_client_id")
        target_id = request.get("target_client_id")

        if not source_id or not target_id:
            raise HTTPException(status_code=400, detail="source_client_id and target_client_id are required")

        if source_id == target_id:
            raise HTTPException(status_code=400, detail="Source and target clients must be different")

        # Verify both clients belong to user
        source = db.query(Client).filter(Client.id == source_id, Client.user_id == current_user.id).first()
        target = db.query(Client).filter(Client.id == target_id, Client.user_id == current_user.id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source client not found")
        if not target:
            raise HTTPException(status_code=404, detail="Target client not found")

        include_rules = request.get("include_rules", True)
        include_categories = request.get("include_categories", True)
        include_learned = request.get("include_learned_rules", True)

        cloned_rules = 0
        cloned_categories = 0
        cloned_learned = 0

        # Clone DB-backed rules
        if include_rules:
            source_rules = db.query(Rule).filter(Rule.client_id == source_id).all()
            for r in source_rules:
                existing = db.query(Rule).filter(
                    Rule.client_id == target_id, Rule.name == r.name
                ).first()
                if not existing:
                    new_rule = Rule(
                        client_id=target_id,
                        name=r.name,
                        enabled=r.enabled,
                        priority=r.priority,
                        conditions=r.conditions,
                        action=r.action,
                        auto_apply=r.auto_apply,
                    )
                    db.add(new_rule)
                    cloned_rules += 1

        # Clone custom categories
        if include_categories:
            source_cats = db.query(CustomCategory).filter(CustomCategory.client_id == source_id).all()
            for cat in source_cats:
                existing = db.query(CustomCategory).filter(
                    CustomCategory.client_id == target_id,
                    CustomCategory.name == cat.name,
                ).first()
                if not existing:
                    new_cat = CustomCategory(
                        client_id=target_id,
                        name=cat.name,
                        is_income=cat.is_income,
                        vat_applicable=cat.vat_applicable,
                        vat_rate=cat.vat_rate,
                    )
                    db.add(new_cat)
                    cloned_categories += 1

        # Clone learned rules
        if include_learned:
            source_learned = db.query(UserCategorizationRule).filter(
                UserCategorizationRule.user_id == str(current_user.id),
                UserCategorizationRule.client_id == source_id,
            ).all()
            for lr in source_learned:
                existing = db.query(UserCategorizationRule).filter(
                    UserCategorizationRule.user_id == str(current_user.id),
                    UserCategorizationRule.client_id == target_id,
                    UserCategorizationRule.pattern_type == lr.pattern_type,
                    UserCategorizationRule.pattern_value == lr.pattern_value,
                ).first()
                if not existing:
                    new_lr = UserCategorizationRule(
                        user_id=str(current_user.id),
                        client_id=target_id,
                        category=lr.category,
                        pattern_type=lr.pattern_type,
                        pattern_value=lr.pattern_value,
                        confidence_score=lr.confidence_score,
                        use_count=0,
                        enabled=lr.enabled,
                    )
                    db.add(new_lr)
                    cloned_learned += 1

        db.commit()

        return {
            "success": True,
            "message": f"Cloned {cloned_rules} rule(s), {cloned_categories} category/ies, {cloned_learned} learned rule(s) from '{source.name}' to '{target.name}'",
            "cloned_rules": cloned_rules,
            "cloned_categories": cloned_categories,
            "cloned_learned_rules": cloned_learned,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
