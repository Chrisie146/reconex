"""
System rule engine for Categorisation V2.

Runs the product-shipped SystemRule table against each uploaded transaction.
Each match emits a *purpose* (business/personal/capital/financing/tax/mixed/other);
the resolver maps purpose + client context to a concrete account on that client's
seeded Chart of Accounts.

Pipeline order (in routers/upload.py::_apply_rules_and_save):
    apply_system_rules  ← here
    categorize_transaction (legacy heuristics)
    user Rule eval
    apply_learned_rules (UserCategorizationRule)

User-authored rules and learned rules always win — system rules only set
account_id / suggested_account_id when later layers don't override them.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from models import Account, Client, SystemRule
from routers.dependencies import txn_matches_conditions

logger = logging.getLogger(__name__)


# ── purpose × trading_capacity → CoA code ────────────────────────────────────
# Codes reference sa_sme_v1.json. Keep this small and principled — merchant
# specifics belong in rule conditions, not in the resolver.
PURPOSE_MATRIX: Dict[str, Dict[str, str]] = {
    "business": {
        "company": "_use_hint",
        "sole_prop": "_use_hint",
        "individual_trader": "_use_hint",
        "individual_only": "9999",  # No trade → review
    },
    "personal": {
        "company": "2140",          # Director's Loan Account
        "sole_prop": "3300",         # Owner Drawings
        "individual_trader": "9999", # Flag — out-of-trade, exclude from P&L
        "individual_only": "_use_hint",
    },
    "capital": {
        "company": "_use_hint",      # Hint expected to be 1510 / 1530 / 1550 etc.
        "sole_prop": "_use_hint",
        "individual_trader": "_use_hint",
        "individual_only": "9999",
    },
    "financing": {
        "company": "_use_hint",      # 2510 long-term loans, 2520 shareholders' loans
        "sole_prop": "3300",
        "individual_trader": "3300",
        "individual_only": "9999",
    },
    "tax": {
        "company": "_use_hint",      # 9100/9200, or 2150/2160/2170 payable accounts
        "sole_prop": "_use_hint",
        "individual_trader": "_use_hint",
        "individual_only": "9999",
    },
    "mixed": {
        "company": "9999",           # V2.3 introduces per-client split rules
        "sole_prop": "9999",
        "individual_trader": "9999",
        "individual_only": "9999",
    },
    "other": {
        "company": "9999",
        "sole_prop": "9999",
        "individual_trader": "9999",
        "individual_only": "9999",
    },
}


@dataclass
class SuggestedClassification:
    """One system-rule hit against one transaction."""
    rule_code: str
    rule_name: str
    purpose: str
    confidence: str                  # high | medium | low
    account: Optional[Account]       # None when the resolver couldn't find a code
    reason: str                      # human-readable, persisted to Transaction.suggestion_reason


def _client_trading_capacity(client: Optional[Client]) -> str:
    """Default unknown clients to individual_only so the matrix never KeyErrors."""
    if client and client.trading_capacity:
        return client.trading_capacity
    return "individual_only"


def _entity_filter_matches(filter_json: Optional[str], client: Optional[Client]) -> bool:
    """A rule's entity_filter restricts which clients it applies to.

    Shape: {"legal_entity_type": ["pty_ltd", "cc"], "trade_type": ["farming"]}
    Missing keys = match-all on that dimension. Missing client = match only
    rules with no filter at all.
    """
    if not filter_json:
        return True
    if client is None:
        return False
    try:
        flt = json.loads(filter_json)
    except (ValueError, TypeError):
        return True

    for field in ("legal_entity_type", "trading_capacity", "trade_type"):
        allowed = flt.get(field)
        if not allowed:
            continue
        actual = getattr(client, field, None)
        if actual not in allowed:
            return False
    return True


def resolve_purpose_to_account(
    purpose: str,
    coa_hint: Optional[str],
    client: Optional[Client],
    db: Session,
) -> Optional[Account]:
    """Resolve a (purpose, hint, client) tuple to an actual postable Account row.

    Returns None when no client (session-only uploads) or no matching account on
    the client's CoA. Caller is expected to fall back to the suspense behaviour
    (leave account_id NULL, flag for review).
    """
    if client is None or client.id is None:
        return None

    capacity = _client_trading_capacity(client)
    matrix_value = PURPOSE_MATRIX.get(purpose, {}).get(capacity)

    # _use_hint means "trust the rule's coa_hint" — typical for business expense
    # rules (e.g. Eskom hints 6210 Utilities).
    target_code = coa_hint if matrix_value == "_use_hint" else matrix_value
    if target_code is None:
        return None

    account = (
        db.query(Account)
        .filter(
            Account.client_id == client.id,
            Account.code == target_code,
            Account.is_active == True,  # noqa: E712
        )
        .first()
    )
    if account is None or not account.is_postable:
        # Fall back to suspense — better to flag than to fail silently.
        suspense = (
            db.query(Account)
            .filter(Account.client_id == client.id, Account.code == "9999")
            .first()
        )
        return suspense
    return account


def _build_reason(rule: SystemRule, purpose: str, account: Optional[Account]) -> str:
    """One-line accountant-facing explanation persisted on the Transaction."""
    bits = []
    if account is not None:
        bits.append(f"{account.code} {account.name}")
    if rule.description:
        bits.append(rule.description)
    else:
        bits.append(f"{rule.name} — purpose: {purpose}")
    return " · ".join(bits)


def apply_system_rules(
    transactions: List[Dict[str, Any]],
    client: Optional[Client],
    db: Session,
) -> List[Optional[SuggestedClassification]]:
    """Evaluate enabled SystemRules against each transaction (same order in/out).

    Returns one entry per input transaction:
      - SuggestedClassification when a rule matched
      - None when no rule matched (later pipeline stages decide what to do)
    """
    rules = (
        db.query(SystemRule)
        .filter(SystemRule.enabled == True)  # noqa: E712
        .order_by(SystemRule.priority.asc())
        .all()
    )
    if not rules:
        return [None] * len(transactions)

    # Pre-parse JSON once per rule.
    parsed: List[Dict[str, Any]] = []
    for r in rules:
        if not _entity_filter_matches(r.entity_filter, client):
            continue
        try:
            conds = json.loads(r.conditions)
        except (ValueError, TypeError):
            logger.warning("System rule %s has unparseable conditions; skipping.", r.code)
            continue
        parsed.append({"rule": r, "conditions": conds})

    out: List[Optional[SuggestedClassification]] = []
    for txn in transactions:
        tdict = {
            "description": txn.get("description", ""),
            "amount": txn.get("amount", 0.0),
            "date": txn.get("date"),
        }
        hit: Optional[SuggestedClassification] = None
        for entry in parsed:
            r: SystemRule = entry["rule"]
            try:
                if txn_matches_conditions(tdict, entry["conditions"]):
                    account = resolve_purpose_to_account(r.purpose, r.coa_hint, client, db)
                    hit = SuggestedClassification(
                        rule_code=r.code,
                        rule_name=r.name,
                        purpose=r.purpose,
                        confidence=r.confidence,
                        account=account,
                        reason=_build_reason(r, r.purpose, account),
                    )
                    break
            except Exception as exc:
                logger.warning("System rule %s failed on a transaction: %s", r.code, exc)
                continue
        out.append(hit)
    return out
