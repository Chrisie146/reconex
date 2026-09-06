import copy
from decimal import Decimal
import unittest

from services.llm_statement.validator import StatementValidator


def transaction(day, description, amount, direction, ordinal, balance_after=None, page=1):
    return {
        "date": day,
        "value_date": None,
        "description": description,
        "amount": amount,
        "direction": direction,
        "additional_fee": "0.00",
        "balance_after": balance_after,
        "source_page": page,
        "source_row_ordinal": ordinal,
        "source_bbox": None,
    }


def statement(transactions=None, opening="1000.00", closing="1150.00"):
    return {
        "document_type": "bank_statement",
        "bank_name": "Example Bank",
        "account_type": "Current Account",
        "account_number_last4": "1234",
        "statement_period_start": "2026-01-01",
        "statement_period_end": "2026-01-31",
        "opening_balance": opening,
        "closing_balance": closing,
        "currency": "ZAR",
        "processed_pages": [1],
        "transaction_pages": [1],
        "transactions": transactions or [
            transaction("2026-01-02", "Deposit", "200.00", "credit", 1, "1200.00"),
            transaction("2026-01-03", "Fee", "50.00", "debit", 2, "1150.00"),
        ],
        "extraction_notes": [],
    }


class StatementValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = StatementValidator()

    def assert_has_failure(self, result, code):
        self.assertIn(code, {failure.code for failure in result.failures})

    def test_clean_statement_passes(self):
        result = self.validator.validate(statement(), expected_pages=[1])
        self.assertEqual("passed", result.status)
        self.assertEqual(Decimal("0.00"), result.difference)

    def test_descending_dates_pass(self):
        data = statement([
            transaction("2026-01-03", "Fee", "50.00", "debit", 1, "1150.00"),
            transaction("2026-01-02", "Deposit", "200.00", "credit", 2, "1200.00"),
        ])
        result = self.validator.validate(data)
        self.assertEqual("passed", result.status)

    def test_negative_balances_pass(self):
        data = statement([
            transaction("2026-01-02", "Payment", "100.00", "debit", 1, "-300.00"),
            transaction("2026-01-03", "Deposit", "50.00", "credit", 2, "-250.00"),
        ], opening="-200.00", closing="-250.00")
        self.assertEqual("passed", self.validator.validate(data).status)

    def test_dropped_row_fails_reconciliation(self):
        data = statement()
        data["transactions"].pop()
        result = self.validator.validate(data)
        self.assert_has_failure(result, "balance_mismatch")

    def test_transposed_digit_fails_reconciliation(self):
        data = statement()
        data["transactions"][1]["amount"] = "05.00"
        result = self.validator.validate(data)
        self.assert_has_failure(result, "invalid_amount")

    def test_out_of_period_date_fails(self):
        data = statement()
        data["transactions"][0]["date"] = "2026-02-02"
        result = self.validator.validate(data)
        self.assert_has_failure(result, "date_out_of_period")

    def test_empty_description_fails(self):
        data = statement()
        data["transactions"][0]["description"] = " "
        self.assert_has_failure(self.validator.validate(data), "empty_description")

    def test_null_amount_fails(self):
        data = statement()
        data["transactions"][0]["amount"] = None
        self.assert_has_failure(self.validator.validate(data), "invalid_amount")

    def test_legitimate_duplicate_financial_rows_are_preserved(self):
        data = statement([
            transaction("2026-01-02", "Same payment", "25.00", "debit", 1),
            transaction("2026-01-02", "Same payment", "25.00", "debit", 2),
        ], closing="950.00")
        result = self.validator.validate(data)
        self.assertEqual("passed", result.status)

    def test_overlap_duplicate_source_location_fails(self):
        data = statement()
        data["transactions"].append(copy.deepcopy(data["transactions"][0]))
        result = self.validator.validate(data)
        self.assert_has_failure(result, "duplicate_source_location")

    def test_running_balance_contradiction_fails(self):
        data = statement()
        data["transactions"][0]["balance_after"] = "1201.00"
        result = self.validator.validate(data)
        self.assert_has_failure(result, "running_balance_mismatch")

    def test_missing_statement_balances_is_unverifiable(self):
        data = statement(opening=None, closing=None)
        result = self.validator.validate(data)
        self.assertEqual("unverifiable", result.status)

    def test_incomplete_coverage_is_unverifiable(self):
        result = self.validator.validate(statement(), coverage_evidence_complete=False)
        self.assertEqual("unverifiable", result.status)

    def test_dropped_offsetting_pair_exposes_arithmetic_limit(self):
        # Dropping a net-zero pair cannot be discovered from balances alone. The
        # caller must withhold its independent coverage attestation.
        result = self.validator.validate(statement(), coverage_evidence_complete=False)
        self.assertEqual("unverifiable", result.status)


if __name__ == "__main__":
    unittest.main()
