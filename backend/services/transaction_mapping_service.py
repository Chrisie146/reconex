"""
Deterministic accountant-style transaction mapping.

This service resolves upload-time categorization and Chart-of-Accounts mapping
without external AI. It keeps legacy free-text categories compatible while
preferring account_id when confidence is strong enough.
"""

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from models import Account, UserCategorizationRule
from services.categorization_learning_service import CategorizationLearningService
from services.categoriser import MERCHANT_MAPPINGS, categorize_transaction


AUTO_APPLY_THRESHOLD = 0.90
SUGGEST_THRESHOLD = 0.65


@dataclass
class MappingResult:
    category: str
    account_id: Optional[int] = None
    suggested_account_id: Optional[int] = None
    confidence: Optional[float] = None
    source: str = "unmapped"
    reason: str = "No reliable account mapping found."
    merchant: Optional[str] = None


class TransactionMappingService:
    """Resolve category/account assignments with explicit precedence."""

    CATEGORY_ACCOUNT_CODES: Dict[str, str] = {
        "Rent": "6200",
        "Utilities": "6210",
        "Fuel": "6300",
        "Insurance": "6600",
        "Professional Services": "6500",
        "Fees & Charges": "6700",
        "Income": "4100",
    }

    HIGH_CONFIDENCE_HEURISTICS = [
        ("6700", "Fees & Charges", 0.96, ["bank charge", "bank fee", "account fee", "service fee", "transaction fee", "monthly fee", "atm fee"], "Bank fee language maps to Bank Charges."),
        ("6300", "Fuel", 0.95, ["fuel", "petrol", "diesel", "caltex", "engen", "sasol", "shell garage", "shell service"], "Fuel merchant or fuel wording maps to Motor Vehicle Fuel."),
        ("6200", "Rent", 0.94, [" rent", "rental", "lease", "landlord", "property management"], "Rent or lease wording maps to Rent."),
        ("6210", "Utilities", 0.93, ["electricity", "eskom", "water", "municipal", "municipality"], "Utility wording maps to Utilities."),
        ("6220", "Utilities", 0.93, ["telephone", "internet", "fibre", "broadband", "airtime", "data bundle", "vodacom", "mtn ", "cell c", "telkom"], "Telecom or internet wording maps to Telephone & Internet."),
        ("6600", "Insurance", 0.93, ["insurance", "insure", "premium", "life cover", "medical aid"], "Insurance wording maps to Insurance."),
        ("6500", "Professional Services", 0.93, ["accounting", "bookkeeper", "audit fee", "auditor"], "Accounting/audit wording maps to Accounting & Audit Fees."),
        ("6510", "Professional Services", 0.93, ["legal fee", "attorney", "lawyer", "law firm"], "Legal wording maps to Legal Fees."),
        ("6100", "Salaries & Wages", 0.95, ["salary", "salaries", "wages", "payroll", "staff pay"], "Payroll wording maps to Salaries & Wages."),
    ]

    AMBIGUOUS_SUGGESTIONS = [
        ("2120", "Transfers", 0.74, ["credit card payment", "credit card debit", "visa payment", "mastercard payment"], "Credit card payments are often liability transfers and need review."),
        ("2510", "Loan Repayment", 0.72, ["home loan", "bond repayment", "loan repayment", "loan instalment", "vehicle finance", "wesbank"], "Loan payments can include principal and interest, so review is required."),
        ("3300", "Owner Drawings", 0.72, ["owner drawing", "drawings", "shareholder"], "Owner/shareholder movements need accountant review."),
        ("1120", "Cash Withdrawal", 0.70, ["cash withdrawal", "atm withdrawal"], "Cash withdrawals may be petty cash or drawings, so review is required."),
    ]

    def resolve(
        self,
        db: Session,
        client_id: Optional[int],
        user_id: str,
        description: str,
        amount: float,
        bank_source: str,
        enabled_rules: Optional[List[dict]] = None,
        condition_matcher: Optional[Callable[[dict, dict], bool]] = None,
    ) -> MappingResult:
        accounts = self._accounts_by_code(db, client_id)
        raw_category, _is_expense = categorize_transaction(description, amount)
        category = raw_category if raw_category != "Other" else "Uncategorized"

        merchant, merchant_category = self._match_merchant(description)
        if merchant_category and category == "Uncategorized":
            category = merchant_category

        learned = self._match_learned_rule(db, client_id, user_id, description)
        if learned:
            rule_category, rule_account = learned
            return self._result_from_account(
                rule_account,
                fallback_category=rule_category,
                confidence=0.98,
                source="learned_rule",
                reason="Matched a user-learned keyword/account rule.",
                merchant=merchant,
                auto=True,
            )

        db_rule = self._match_db_rule(
            db=db,
            client_id=client_id,
            accounts=accounts,
            enabled_rules=enabled_rules or [],
            condition_matcher=condition_matcher,
            description=description,
            amount=amount,
            category=category,
        )
        if db_rule:
            db_rule.merchant = db_rule.merchant or merchant
            return db_rule

        merchant_account = self._account_for_category(accounts, category)
        if merchant and merchant_account and category not in ("Transfers", "Loan Repayment"):
            return self._result_from_account(
                merchant_account,
                fallback_category=category,
                confidence=0.93,
                source="merchant",
                reason=f"Known merchant '{merchant}' maps to {category}.",
                merchant=merchant,
                auto=True,
            )

        heuristic = self._match_heuristic(accounts, description, amount, category, bank_source, merchant)
        if heuristic:
            return heuristic

        category_account = self._account_for_category(accounts, category)
        if category_account and category not in ("Transfers", "Loan Repayment"):
            return self._result_from_account(
                category_account,
                fallback_category=category,
                confidence=0.88,
                source="category",
                reason=f"Built-in category '{category}' suggests this account; review before relying on it.",
                merchant=merchant,
                auto=False,
            )

        if amount > 0 and self._contains_any(description, ["sales", "customer", "invoice payment", "card sales", "settlement"]):
            account = accounts.get("4100")
            if account:
                return self._result_from_account(
                    account,
                    fallback_category="Income",
                    confidence=0.92,
                    source="heuristic",
                    reason="Clear customer/sales receipt wording maps to Sales.",
                    merchant=merchant,
                    auto=True,
                )

        return MappingResult(
            category=category,
            confidence=0.0,
            source="unmapped",
            reason="No learned rule, client rule, merchant rule, or high-confidence accountant heuristic matched.",
            merchant=merchant,
        )

    def _accounts_by_code(self, db: Session, client_id: Optional[int]) -> Dict[str, Account]:
        if client_id is None:
            return {}
        rows = db.query(Account).filter(
            Account.client_id == client_id,
            Account.is_active == True,  # noqa: E712
            Account.is_postable == True,  # noqa: E712
        ).all()
        return {a.code: a for a in rows}

    def _match_learned_rule(
        self,
        db: Session,
        client_id: Optional[int],
        user_id: str,
        description: str,
    ) -> Optional[tuple[str, Optional[Account]]]:
        query = db.query(UserCategorizationRule).filter(
            UserCategorizationRule.user_id == user_id,
            UserCategorizationRule.enabled == 1,
        )
        if client_id is not None:
            query = query.filter(UserCategorizationRule.client_id == client_id)
        else:
            query = query.filter(UserCategorizationRule.client_id.is_(None))

        rules = query.order_by(UserCategorizationRule.confidence_score.desc(), UserCategorizationRule.use_count.desc()).all()
        normalized = CategorizationLearningService.normalize_description(description)
        merchant = CategorizationLearningService.extract_merchant_from_description(description)
        merchant_upper = merchant.upper() if merchant else None

        for rule in rules:
            value = rule.pattern_value
            matched = False
            if rule.pattern_type == "exact":
                matched = normalized == value
            elif rule.pattern_type == "starts_with":
                matched = normalized.startswith(value)
            elif rule.pattern_type == "contains":
                matched = value in normalized
            elif rule.pattern_type == "merchant":
                matched = merchant_upper == value
            if matched:
                account = None
                if rule.account_id is not None and rule.account is not None:
                    if rule.account.client_id == client_id and rule.account.is_active and rule.account.is_postable:
                        account = rule.account
                rule.use_count += 1
                return rule.category, account
        return None

    def _match_db_rule(
        self,
        db: Session,
        client_id: Optional[int],
        accounts: Dict[str, Account],
        enabled_rules: List[dict],
        condition_matcher: Optional[Callable[[dict, dict], bool]],
        description: str,
        amount: float,
        category: str,
    ) -> Optional[MappingResult]:
        if not condition_matcher:
            return None
        tdict = {"description": description, "amount": amount, "category": category}
        for rule in enabled_rules:
            if not rule.get("auto_apply"):
                continue
            try:
                if not condition_matcher(tdict, rule.get("conditions", {})):
                    continue
                action = rule.get("action", {})
                action_type = action.get("type")
                if action_type in ("set_category", "set_account"):
                    account = self._resolve_action_account(db, client_id, accounts, action)
                    next_category = action.get("category") or (account.name if account else category)
                    return self._result_from_account(
                        account,
                        fallback_category=next_category,
                        confidence=0.97,
                        source="client_rule",
                        reason=f"Matched client rule '{rule.get('name', 'Manual Rule')}'.",
                        auto=True,
                    )
                if action_type == "set_merchant" and action.get("merchant"):
                    return MappingResult(
                        category=category,
                        confidence=0.9,
                        source="client_rule",
                        reason=f"Matched client merchant rule '{rule.get('name', 'Manual Rule')}'.",
                        merchant=action["merchant"],
                    )
            except Exception:
                continue
        return None

    def _resolve_action_account(
        self,
        db: Session,
        client_id: Optional[int],
        accounts: Dict[str, Account],
        action: dict,
    ) -> Optional[Account]:
        if client_id is None:
            return None
        if action.get("account_code"):
            return accounts.get(action["account_code"])
        account_id = action.get("account_id")
        if account_id is None:
            return None
        return db.query(Account).filter(
            Account.id == account_id,
            Account.client_id == client_id,
            Account.is_active == True,  # noqa: E712
            Account.is_postable == True,  # noqa: E712
        ).first()

    def _match_heuristic(
        self,
        accounts: Dict[str, Account],
        description: str,
        amount: float,
        category: str,
        bank_source: str,
        merchant: Optional[str],
    ) -> Optional[MappingResult]:
        text = self._norm(description)
        if amount > 0 and self._contains_any(text, ["interest received", "credit interest", "int received"]):
            account = accounts.get("4400")
            if account:
                return self._result_from_account(account, "Interest Income", 0.94, "heuristic", "Interest received maps to Interest Income.", merchant, True)

        if amount > 0 and self._contains_any(text, ["sales", "customer", "invoice payment", "card sales", "settlement"]):
            account = accounts.get("4100")
            if account:
                return self._result_from_account(account, "Income", 0.92, "heuristic", "Clear customer/sales receipt wording maps to Sales.", merchant, True)

        for code, fallback_category, confidence, keywords, reason in self.HIGH_CONFIDENCE_HEURISTICS:
            if self._contains_any(text, keywords):
                account = accounts.get(code)
                if account:
                    return self._result_from_account(account, fallback_category, confidence, "heuristic", reason, merchant, confidence >= AUTO_APPLY_THRESHOLD)

        for code, fallback_category, confidence, keywords, reason in self.AMBIGUOUS_SUGGESTIONS:
            if self._contains_any(text, keywords):
                account = accounts.get(code)
                if account:
                    return self._result_from_account(account, fallback_category, confidence, "heuristic", reason, merchant, False)

        if category == "Loan Repayment":
            account = accounts.get("2510")
            if account:
                return self._result_from_account(account, category, 0.72, "category", "Loan repayments often need principal/interest review.", merchant, False)
        if category == "Transfers":
            account = accounts.get("1110")
            if account:
                return self._result_from_account(account, category, 0.68, "category", "Transfers may be between bank, card, loan, or owner accounts; review required.", merchant, False)
        return None

    def _match_merchant(self, description: str) -> tuple[Optional[str], Optional[str]]:
        desc_lower = description.lower()
        for mapping in MERCHANT_MAPPINGS:
            for pattern in mapping.get("patterns", []):
                if re.search(r"\b" + re.escape(pattern.lower()) + r"\b", desc_lower):
                    return mapping.get("merchant"), mapping.get("category")
        return None, None

    def _account_for_category(self, accounts: Dict[str, Account], category: str) -> Optional[Account]:
        code = self.CATEGORY_ACCOUNT_CODES.get(category)
        return accounts.get(code) if code else None

    def _result_from_account(
        self,
        account: Optional[Account],
        fallback_category: str,
        confidence: float,
        source: str,
        reason: str,
        merchant: Optional[str] = None,
        auto: bool = False,
    ) -> MappingResult:
        if account is None:
            return MappingResult(
                category=fallback_category,
                confidence=confidence,
                source=source,
                reason=reason,
                merchant=merchant,
            )
        if auto and confidence >= AUTO_APPLY_THRESHOLD:
            return MappingResult(
                category=account.name,
                account_id=account.id,
                confidence=confidence,
                source=source,
                reason=reason,
                merchant=merchant,
            )
        if confidence >= SUGGEST_THRESHOLD:
            return MappingResult(
                category=fallback_category,
                suggested_account_id=account.id,
                confidence=confidence,
                source=source,
                reason=reason,
                merchant=merchant,
            )
        return MappingResult(category=fallback_category, confidence=confidence, source=source, reason=reason, merchant=merchant)

    def _contains_any(self, description: str, needles: List[str]) -> bool:
        text = self._norm(description)
        return any(self._norm(needle) in text for needle in needles)

    def _norm(self, text: str) -> str:
        return f" {re.sub(r'[^a-z0-9]+', ' ', (text or '').lower()).strip()} "


transaction_mapping_service = TransactionMappingService()
