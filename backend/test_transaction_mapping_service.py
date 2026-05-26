from types import SimpleNamespace

from services.transaction_mapping_service import TransactionMappingService


class QueryStub:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows


class DBStub:
    def __init__(self, accounts=None, learned_rules=None):
        self.accounts = accounts or []
        self.learned_rules = learned_rules or []

    def query(self, model):
        name = getattr(model, "__name__", "")
        if name == "Account":
            return QueryStub(self.accounts)
        if name == "UserCategorizationRule":
            return QueryStub(self.learned_rules)
        return QueryStub([])


def account(code, name, account_type="expense", account_id=None):
    return SimpleNamespace(
        id=account_id or int(code),
        client_id=1,
        code=code,
        name=name,
        account_type=account_type,
        is_active=True,
        is_postable=True,
    )


def test_high_confidence_bank_fee_auto_maps_to_bank_charges():
    svc = TransactionMappingService()
    result = svc.resolve(
        db=DBStub(accounts=[account("6700", "Bank Charges")]),
        client_id=1,
        user_id="1",
        description="MONTHLY BANK CHARGE",
        amount=-120.0,
        bank_source="fnb",
    )

    assert result.account_id == 6700
    assert result.suggested_account_id is None
    assert result.category == "Bank Charges"
    assert result.source == "heuristic"
    assert result.confidence >= 0.9


def test_ambiguous_loan_repayment_is_suggested_not_auto_mapped():
    svc = TransactionMappingService()
    result = svc.resolve(
        db=DBStub(accounts=[account("2510", "Long-term Loans", "liability")]),
        client_id=1,
        user_id="1",
        description="WESBANK VEHICLE FINANCE INSTALMENT",
        amount=-4500.0,
        bank_source="fnb",
    )

    assert result.account_id is None
    assert result.suggested_account_id == 2510
    assert result.confidence < 0.9


def test_clear_sales_receipt_auto_maps_positive_amount_to_sales():
    svc = TransactionMappingService()
    result = svc.resolve(
        db=DBStub(accounts=[account("4100", "Sales (Standard-rated 15%)", "revenue")]),
        client_id=1,
        user_id="1",
        description="CUSTOMER INVOICE PAYMENT ACME",
        amount=2500.0,
        bank_source="absa",
    )

    assert result.account_id == 4100
    assert result.category == "Sales (Standard-rated 15%)"
    assert result.confidence >= 0.9
