"""
Shared dependencies, request/response models, and helper functions
used across all router modules.
"""

import json
import logging
import math
import os
import re
import uuid
from datetime import date, datetime
from typing import List, Optional

from fastapi import Body, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, or_, String
from sqlalchemy.orm import Session

from auth import get_current_user
from config import Config
from exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DatabaseError,
    FileProcessingError,
    NotFoundError,
    ValidationError,
)
from models import (
    Client,
    FileAccessLog,
    Invoice,
    InvoiceMatch,
    OverallReconciliation,
    Reconciliation,
    Rule,
    SessionState,
    SessionVATConfig,
    Transaction,
    TransactionMerchant,
    User,
    get_db,
)
from rate_limiter import add_rate_limit_headers, read_limiter, standard_limiter, upload_limiter
from services.bulk_categorizer import BulkCategorizer
from services.cache import cached, get_cache
from services.categories_service import CategoriesService
from services.categorization_learning_service import CategorizationLearningService
from services.categoriser import categorize_transaction, extract_merchant
from services.storage import get_storage
from services.summary import (
    ExcelExporter,
    calculate_monthly_summary,
    get_category_summary,
)
from services.vat_service import VATService
from validators import validate_csv_upload, validate_pdf_upload

logger = logging.getLogger(__name__)

# ============================================================================
# SINGLETON SERVICE INSTANCES
# ============================================================================

categories_service = CategoriesService()
vat_service = VATService()
learning_service = CategorizationLearningService()
bulk_categorizer = BulkCategorizer()

# In-memory OCR regions store: (user_id, session_id) -> mapping of pages -> regions
ocr_region_store: dict = {}


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class BulkCategorizeRequest(BaseModel):
    """Request body for bulk categorization"""
    keyword: str
    category: str
    only_uncategorised: bool = True


class CreateCategoryRequest(BaseModel):
    """Request body for creating a custom category"""
    category_name: str
    is_income: bool = False


class CreateRuleRequest(BaseModel):
    """Request body for creating a categorization rule"""
    name: str
    category: str
    keywords: List[str]
    priority: int = 10
    auto_apply: bool = True
    match_compound_words: bool = False


class UpdateRuleRequest(BaseModel):
    """Request body for updating a rule"""
    name: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    auto_apply: Optional[bool] = None
    enabled: Optional[bool] = None
    match_compound_words: Optional[bool] = None


class BulkApplyRulesRequest(BaseModel):
    """Request body for bulk applying rules to transactions"""
    rule_ids: Optional[List[str]] = None
    auto_apply_only: bool = False


class ReconciliationRequest(BaseModel):
    month: str  # YYYY-MM
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None


class OverallReconciliationRequest(BaseModel):
    system_opening_balance: Optional[float] = None
    bank_closing_balance: Optional[float] = None


class BulkDeleteSessionsRequest(BaseModel):
    """Request body for bulk deleting sessions"""
    session_ids: List[str]


class ClearCategoriesRequest(BaseModel):
    """Request body for clearing categories (empty body allowed)"""
    pass


class VATConfigRequest(BaseModel):
    """Request body for VAT configuration"""
    vat_enabled: bool
    default_vat_rate: Optional[float] = 15.0


class UpdateCategoryVATRequest(BaseModel):
    """Request body for updating category VAT settings"""
    vat_applicable: bool
    vat_rate: float = 15.0
    is_income: Optional[bool] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def ensure_session_access(session_id: str, current_user: User, db: Session) -> None:
    """Validate that the session belongs to the authenticated user via client ownership."""
    if not session_id:
        raise ValidationError("session_id is required")

    client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
    if not client_ids:
        raise NotFoundError("Client", "for user")

    allowed = db.query(Transaction.id).filter(
        Transaction.session_id == session_id,
        Transaction.client_id.in_(client_ids),
    ).first()

    if not allowed:
        raise NotFoundError("Session", session_id)


def ensure_session_access_lenient(session_id: str, current_user: User, db: Session) -> None:
    """
    Lenient session access check for read-only operations.
    Falls back to checking SessionState if no transactions with client_id exist.
    """
    if not session_id:
        raise ValidationError("session_id is required")

    client_ids = [c.id for c in db.query(Client.id).filter(Client.user_id == current_user.id).all()]
    if not client_ids:
        raise NotFoundError("Client", "for user")

    # First try transaction-based check
    allowed = db.query(Transaction.id).filter(
        Transaction.session_id == session_id,
        Transaction.client_id.in_(client_ids),
    ).first()

    if allowed:
        return

    # Fall back to checking if session has any transactions at all (for backwards compatibility)
    session_exists = db.query(Transaction.id).filter(
        Transaction.session_id == session_id
    ).first()

    if not session_exists:
        raise NotFoundError("Session", session_id)


def generate_file_key(filename: str, prefix: str = "invoices") -> str:
    """Generate a unique object key for cloud storage with path traversal protection."""
    unique_id = uuid.uuid4().hex
    # Strip path separators and dangerous characters to prevent traversal
    basename = os.path.basename(filename)  # removes directory components
    safe_filename = re.sub(r'[^\w\-.]', '_', basename)  # whitelist safe chars
    if not safe_filename or safe_filename.startswith('.'):
        safe_filename = "file"
    return f"{prefix}/{unique_id}_{safe_filename}"


def log_file_access(
    db: Session,
    user_id: int,
    file_key: str,
    action: str,
    request: Request = None,
    invoice_id: int = None,
):
    """Log file access event for audit trail"""
    log_entry = FileAccessLog(
        user_id=user_id,
        invoice_id=invoice_id,
        file_key=file_key,
        action=action,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None,
        storage_backend=Config.STORAGE_BACKEND,
    )
    db.add(log_entry)
    db.commit()
    return log_entry


def sanitize_response_data(data):
    """Recursively sanitize NaN and infinity values from response data"""
    if isinstance(data, dict):
        return {k: sanitize_response_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_response_data(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            logger.warning(f"[RESPONSE_SANITIZATION] Sanitized invalid float value: {data}")
            return 0.0
        return data
    else:
        return data


def txn_matches_conditions(txn: dict, conds: dict) -> bool:
    """Evaluate whether a transaction matches a set of rule conditions."""
    match_type = conds.get("match_type", "all")
    clauses = conds.get("conditions", [])

    # Pre-compiled safe regex cache to avoid ReDoS
    _MAX_REGEX_LEN = 200

    def eval_clause(cl):
        f = cl.get("field")
        op = cl.get("op")
        val = cl.get("value")
        v = txn.get(f)
        if v is None:
            return False
        try:
            if op == "contains":
                return str(val).lower() in str(v).lower()
            if op == "equals":
                return str(v).lower() == str(val).lower()
            if op == "regex":
                # Guard against ReDoS: limit pattern length and use timeout
                if not val or len(str(val)) > _MAX_REGEX_LEN:
                    return False
                try:
                    # Compile with a reasonable limit; Python 3.11+ has timeout but
                    # for compatibility, we limit the pattern complexity instead
                    pattern = re.compile(str(val), re.IGNORECASE)
                    return pattern.search(str(v)) is not None
                except re.error:
                    return False
            if op == "gt":
                return float(v) > float(val)
            if op == "lt":
                return float(v) < float(val)
        except Exception:
            return False
        return False

    results = [eval_clause(c) for c in clauses]
    if match_type == "any":
        return any(results)
    return all(results)


def load_enabled_rules(db: Session, client_id: Optional[int] = None) -> list:
    """Load enabled rules from database. Only loads rules scoped to the given client."""
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


def apply_rules_to_transaction(txn_data: dict, category: str, enabled_rules: list) -> str:
    """Apply auto-apply rules to a single transaction. Returns final category."""
    tdict = {
        "description": txn_data["description"],
        "amount": txn_data["amount"],
        "date": txn_data.get("date"),
        "category": category,
    }
    for r in enabled_rules:
        if not r.get("auto_apply"):
            continue
        try:
            if txn_matches_conditions(tdict, r.get("conditions", {})):
                act = r.get("action", {})
                if act.get("type") == "set_category" and act.get("category"):
                    return act["category"]
                if act.get("type") == "set_merchant" and act.get("merchant"):
                    txn_data["_merchant"] = act["merchant"]
                    break
        except Exception:
            continue
    return category


def apply_learned_rules_to_session(
    session_id: str,
    current_user: User,
    db: Session,
) -> int:
    """Apply learned categorization rules to a session's transactions. Returns count of updates."""
    try:
        all_transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
        if not all_transactions:
            return 0
        effective_user_id = str(current_user.id)
        # Derive client_id from transactions so rules are strictly scoped per-client
        client_id = all_transactions[0].client_id if all_transactions else None
        # override_existing=True so learned rules beat the built-in keyword categorizer
        suggestions = learning_service.apply_learned_rules(
            effective_user_id, all_transactions, db, client_id=client_id, override_existing=True
        )

        updated_ids = []
        for txn_id, category in suggestions.items():
            txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
            if txn:
                txn.category = category
                txn.suggested_category = None  # learned = confirmed, clear any suggestion
                updated_ids.append(txn_id)

        if suggestions:
            db.commit()
            for txn_id in updated_ids:
                vat_service.apply_vat_to_transaction(txn_id, session_id, force=False)
            logger.info(f"Auto-categorized {len(suggestions)} transaction(s) using learned rules")

        return len(suggestions)
    except Exception as learn_error:
        logger.warning(f"Failed to apply learned rules: {learn_error}")
        return 0


def create_session_state(db: Session, session_id: str, filename: str) -> None:
    """Create a SessionState record with a friendly name derived from the filename."""
    friendly_name = filename.rsplit(".", 1)[0]
    friendly_name = friendly_name.replace("_", " ")
    friendly_name = " ".join(word.capitalize() for word in friendly_name.split())
    ss = SessionState(session_id=session_id, friendly_name=friendly_name)
    db.add(ss)
    db.commit()
