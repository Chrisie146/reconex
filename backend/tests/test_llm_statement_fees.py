"""Regression checks for generic inline fees, independent of bank templates."""
from decimal import Decimal
import unittest

from test_llm_statement_validator import statement, transaction
from services.llm_statement.adapter import transactions_for_import
from services.llm_statement.validator import StatementValidator


class FeeTests(unittest.TestCase):
    def make_statement(self, fee="-2.00", direction="debit"):
        balance = "898.00" if direction == "debit" else "1098.00"
        row = transaction("2026-01-02", "Payment", "100.00", direction, 1, balance)
        row["additional_fee"] = fee
        return statement([row], "1000.00", balance)

    def test_inline_fee_reconciles_and_imports_separately_once(self):
        extraction = self.make_statement()
        result = StatementValidator().validate(extraction)
        self.assertTrue(result.passed)
        self.assertEqual(Decimal("102.00"), result.total_debits)
        entries = transactions_for_import(extraction)
        self.assertEqual([Decimal("-100.00"), Decimal("-2.00")], [e["amount"] for e in entries])
        self.assertEqual("Bank fee: Payment", entries[1]["description"])
        self.assertTrue(entries[1]["debit_flag"])

    def test_omitted_or_double_counted_fee_fails(self):
        for fee, amount in [("0.00", "100.00"), ("-2.00", "102.00")]:
            with self.subTest(fee=fee, amount=amount):
                extraction = self.make_statement(fee)
                extraction["transactions"][0]["amount"] = amount
                codes = {i.code for i in StatementValidator().validate(extraction).failures}
                self.assertIn("balance_mismatch", codes)
                self.assertIn("running_balance_mismatch", codes)

    def test_included_fee_is_not_added_again(self):
        extraction = self.make_statement("0.00")
        extraction["transactions"][0]["amount"] = "102.00"
        self.assertTrue(StatementValidator().validate(extraction).passed)
        self.assertEqual(1, len(transactions_for_import(extraction)))

    def test_credit_with_fee_and_fee_refund(self):
        extraction = self.make_statement(direction="credit")
        result = StatementValidator().validate(extraction)
        self.assertTrue(result.passed)
        self.assertEqual(Decimal("100.00"), result.total_credits)
        self.assertEqual(Decimal("2.00"), result.total_debits)
        extraction = self.make_statement("2.00")
        extraction["closing_balance"] = "902.00"
        extraction["transactions"][0]["balance_after"] = "902.00"
        self.assertTrue(StatementValidator().validate(extraction).passed)
        self.assertEqual(Decimal("2.00"), transactions_for_import(extraction)[1]["amount"])

    def test_unknown_missing_and_invalid_fees_fail_closed(self):
        for fee in [None, "unknown", "2", "NaN", 2]:
            with self.subTest(fee=fee):
                extraction = self.make_statement(fee)
                self.assertFalse(StatementValidator().validate(extraction).passed)
        extraction = self.make_statement()
        del extraction["transactions"][0]["additional_fee"]
        self.assertFalse(StatementValidator().validate(extraction).passed)

    def test_descending_dates_and_standalone_fee(self):
        payment = self.make_statement()["transactions"][0]
        later = transaction("2026-01-03", "Monthly fee", "5.00", "debit", 2, "893.00")
        extraction = statement([later, payment], "1000.00", "893.00")
        self.assertTrue(StatementValidator().validate(extraction).passed)
        self.assertEqual(3, len(transactions_for_import(extraction)))


if __name__ == "__main__":
    unittest.main()
