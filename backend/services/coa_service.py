"""
Chart-of-Accounts service.

Responsible for:
  - Seeding a per-client Chart of Accounts from a JSON template
  - Building the account tree for display
  - Validating that an account is allowed to receive a posting
  - Resolving accounts by id or code (codes are the portable identifier)

The CoA is small (~60 nodes, 3–4 levels deep) and rarely mutated, so we use an
adjacency-list (`parent_id`) plus a materialized `path` string instead of a
recursive CTE — the tree fits easily in memory and the API needs nesting anyway.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import Account

logger = logging.getLogger(__name__)

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "coa_templates")


def _load_template(template_name: str) -> Dict[str, Any]:
    path = os.path.join(TEMPLATE_DIR, f"{template_name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"CoA template '{template_name}' not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_templates() -> List[Dict[str, Any]]:
    """Return metadata for every available template JSON in the templates dir."""
    if not os.path.isdir(TEMPLATE_DIR):
        return []
    out: List[Dict[str, Any]] = []
    for fn in sorted(os.listdir(TEMPLATE_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            data = _load_template(fn[:-5])
            out.append({
                "name": data.get("name", fn[:-5]),
                "version": data.get("version", 1),
                "description": data.get("description", ""),
                "currency": data.get("currency"),
                "account_count": len(data.get("accounts", [])),
            })
        except Exception as exc:
            logger.warning("Failed to load CoA template %s: %s", fn, exc)
    return out


def seed_template_for_client(client_id: int, template_name: str, db: Session) -> Tuple[int, int]:
    """Seed a client's Chart of Accounts from a JSON template.

    Idempotent: any account whose `(client_id, code)` already exists is skipped,
    so this can safely be re-run to top up a client with new template rows after
    a template version bump. Returns ``(created, skipped)``.
    """
    template = _load_template(template_name)
    entries: List[Dict[str, Any]] = template.get("accounts", [])
    if not entries:
        return (0, 0)

    # Pull existing codes once so we can skip without flushing per row.
    existing_codes = {
        code for (code,) in db.query(Account.code).filter(Account.client_id == client_id).all()
    }

    # Two-pass insert: first add every entry as a flat row keyed by code, then
    # resolve parent_code -> parent_id once all rows have ids. This avoids any
    # ordering dependency on the JSON file.
    code_to_account: Dict[str, Account] = {}
    code_to_parent_code: Dict[str, Optional[str]] = {}
    created = 0
    skipped = 0

    for entry in entries:
        code = entry["code"]
        if code in existing_codes:
            skipped += 1
            continue
        account = Account(
            client_id=client_id,
            code=code,
            name=entry["name"],
            account_type=entry["account_type"],
            account_subtype=entry.get("account_subtype"),
            normal_balance=entry["normal_balance"],
            cash_flow_section=entry.get("cash_flow_section", "none"),
            is_vat_control=bool(entry.get("is_vat_control", False)),
            vat_treatment=entry.get("vat_treatment"),
            vat_rate=entry.get("vat_rate"),
            is_postable=bool(entry.get("is_postable", True)),
            is_active=True,
            is_system=True,
            description=entry.get("description"),
            level=0,                 # filled in after parent ids resolved
            path="",                 # filled in after parent ids resolved
        )
        db.add(account)
        code_to_account[code] = account
        code_to_parent_code[code] = entry.get("parent_code")
        created += 1

    if created == 0:
        return (0, skipped)

    # Flush so SERIAL ids are populated; we still need parents to wire children.
    db.flush()

    # Also pull rows we skipped (already existed) so children of the new rows
    # can still hang under an old parent — important when re-seeding.
    if skipped:
        for acc in db.query(Account).filter(Account.client_id == client_id).all():
            code_to_account.setdefault(acc.code, acc)

    # Second pass: resolve parent ids, levels, and materialized paths.
    for code, parent_code in code_to_parent_code.items():
        account = code_to_account[code]
        if parent_code:
            parent = code_to_account.get(parent_code)
            if parent is None:
                logger.warning(
                    "CoA seed: account %s references missing parent %s — leaving as root",
                    code, parent_code,
                )
                continue
            account.parent_id = parent.id
            account.level = (parent.level or 0) + 1
            account.path = f"{parent.path}/{parent.id}" if parent.path else f"{parent.id}"
        else:
            account.level = 0
            account.path = ""

    db.commit()
    logger.info(
        "Seeded CoA template '%s' for client %s — created=%s skipped=%s",
        template_name, client_id, created, skipped,
    )
    return (created, skipped)


def build_tree(client_id: int, db: Session, postable_only: bool = False) -> List[Dict[str, Any]]:
    """Return the full CoA for a client as nested dicts (roots → children)."""
    q = db.query(Account).filter(Account.client_id == client_id, Account.is_active == True)  # noqa: E712
    if postable_only:
        q = q.filter(Account.is_postable == True)  # noqa: E712
    rows: List[Account] = q.order_by(Account.code).all()

    nodes: Dict[int, Dict[str, Any]] = {a.id: serialize_account(a, with_children=True) for a in rows}
    roots: List[Dict[str, Any]] = []
    for a in rows:
        node = nodes[a.id]
        if a.parent_id and a.parent_id in nodes:
            nodes[a.parent_id]["children"].append(node)
        else:
            roots.append(node)
    return roots


def list_accounts(
    client_id: int,
    db: Session,
    postable_only: bool = False,
    include_inactive: bool = False,
) -> List[Dict[str, Any]]:
    """Flat list — useful for selectors and exports."""
    q = db.query(Account).filter(Account.client_id == client_id)
    if not include_inactive:
        q = q.filter(Account.is_active == True)  # noqa: E712
    if postable_only:
        q = q.filter(Account.is_postable == True)  # noqa: E712
    return [serialize_account(a) for a in q.order_by(Account.code).all()]


def serialize_account(account: Account, with_children: bool = False) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": account.id,
        "client_id": account.client_id,
        "code": account.code,
        "name": account.name,
        "parent_id": account.parent_id,
        "path": account.path,
        "level": account.level,
        "account_type": account.account_type,
        "account_subtype": account.account_subtype,
        "normal_balance": account.normal_balance,
        "cash_flow_section": account.cash_flow_section,
        "is_vat_control": bool(account.is_vat_control),
        "vat_treatment": account.vat_treatment,
        "vat_rate": account.vat_rate,
        "is_postable": bool(account.is_postable),
        "is_active": bool(account.is_active),
        "is_system": bool(account.is_system),
        "description": account.description,
    }
    if with_children:
        out["children"] = []
    return out


def validate_account_for_posting(account_id: int, client_id: int, db: Session) -> Account:
    """Raise on accounts that aren't allowed to receive a posting, else return the row.

    Caller is expected to translate ValueError into an HTTP error.
    """
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.client_id == client_id,
    ).first()
    if not account:
        raise ValueError(f"Account {account_id} not found for client {client_id}")
    if not account.is_active:
        raise ValueError(f"Account {account.code} ({account.name}) is inactive")
    if not account.is_postable:
        raise ValueError(
            f"Account {account.code} ({account.name}) is a header — postings must go to a leaf"
        )
    return account


def resolve_by_code(client_id: int, code: str, db: Session) -> Optional[Account]:
    return db.query(Account).filter(
        Account.client_id == client_id,
        Account.code == code,
    ).first()


def has_transactions(account_id: int, db: Session) -> bool:
    """Check whether any Transaction or UserCategorizationRule still references this account."""
    from models import Transaction, UserCategorizationRule

    txn_exists = db.query(Transaction.id).filter(Transaction.account_id == account_id).first() is not None
    if txn_exists:
        return True
    rule_exists = (
        db.query(UserCategorizationRule.id).filter(UserCategorizationRule.account_id == account_id).first()
        is not None
    )
    return rule_exists


def reassign_transactions(from_account_id: int, to_account_id: int, db: Session) -> int:
    """Move all transactions and learned rules from one account to another. Returns rows touched."""
    from models import Transaction, UserCategorizationRule

    n_txn = (
        db.query(Transaction)
        .filter(Transaction.account_id == from_account_id)
        .update({Transaction.account_id: to_account_id}, synchronize_session=False)
    )
    n_sug = (
        db.query(Transaction)
        .filter(Transaction.suggested_account_id == from_account_id)
        .update({Transaction.suggested_account_id: to_account_id}, synchronize_session=False)
    )
    n_rule = (
        db.query(UserCategorizationRule)
        .filter(UserCategorizationRule.account_id == from_account_id)
        .update({UserCategorizationRule.account_id: to_account_id}, synchronize_session=False)
    )
    db.commit()
    return int(n_txn) + int(n_sug) + int(n_rule)
