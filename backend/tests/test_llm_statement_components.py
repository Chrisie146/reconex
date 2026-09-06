import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from services.llm_statement.ingest import ExtractedPage, PageLine, assess_pdf
from services.llm_statement.merge import MergeError, merge_extractions
from services.llm_statement.redaction import redact_pages


def extraction(rows, pages):
    return {
        "document_type": "bank_statement",
        "bank_name": "Example Bank",
        "account_type": "Current",
        "account_number_last4": "1234",
        "statement_period_start": "2026-01-01",
        "statement_period_end": "2026-01-31",
        "opening_balance": "100.00",
        "closing_balance": "100.00",
        "currency": "ZAR",
        "processed_pages": pages,
        "transaction_pages": pages,
        "transactions": rows,
        "extraction_notes": [],
    }


def row(page, ordinal, description="Payment"):
    return {
        "date": "2026-01-02", "value_date": None, "description": description,
        "amount": "10.00", "direction": "debit", "balance_after": None,
        "additional_fee": "0.00",
        "source_page": page, "source_row_ordinal": ordinal, "source_bbox": None,
    }


class ComponentTests(unittest.TestCase):
    def test_prompt_explains_common_debit_credit_layouts(self):
        prompt_path = Path(__file__).resolve().parents[1] / "prompts" / "extract_statement.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        self.assertIn("separate debit/withdrawal/paid-out", prompt)
        self.assertIn("one signed amount column", prompt)
        self.assertIn("unambiguous evidence for `ZAR`", prompt)

    def test_schema_is_valid_json(self):
        schema_path = Path(__file__).resolve().parents[1] / "prompts" / "extract_statement.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual("object", schema["type"])
        self.assertFalse(schema["additionalProperties"])
        direction = schema["properties"]["transactions"]["items"]["properties"]["direction"]
        self.assertEqual(
            [
                {"type": "string", "enum": ["debit", "credit"]},
                {"type": "null"},
            ],
            direction["anyOf"],
        )

    def test_redacts_identity_fields_and_preserves_account_last4(self):
        page = ExtractedPage(
            1, 595, 842, "usable_text",
            [
                PageLine(10, "Account holder: Jane Example", ()),
                PageLine(20, "Account number: 1234567890", ()),
                PageLine(30, "Email: jane@example.com Phone: 082 123 4567", ()),
                PageLine(40, "2026-01-02 Grocery 10.00", ()),
            ],
            120,
            1,
        )
        result = redact_pages([page])
        rendered = result.pages[0]
        self.assertIn("line=1 bbox=", rendered)
        self.assertTrue(result.safe)
        self.assertIn("<ACCOUNT_LAST4:7890>", rendered)
        self.assertNotIn("Jane Example", rendered)
        self.assertNotIn("jane@example.com", rendered)
        self.assertNotIn("082 123 4567", rendered)
        self.assertIn("Grocery 10.00", rendered)

    def test_redaction_preserves_horizontal_column_spacing(self):
        page = ExtractedPage(
            1, 600, 800, "usable_text",
            [
                PageLine(
                    100,
                    "02 Jan Grocery 125.50 874.50",
                    ("x=20.0:02", "x=40.0:Jan", "x=120.0:Grocery", "x=400.0:125.50", "x=510.0:874.50"),
                ),
            ],
            40,
            1,
        )
        rendered = redact_pages([page]).pages[0]
        self.assertRegex(rendered, re.compile(r"Grocery\s{10,}125\.50\s{5,}874\.50"))

    def test_redaction_does_not_consume_large_money_or_adjacent_columns(self):
        page = ExtractedPage(
            1, 600, 800, "usable_text",
            [
                PageLine(
                    100,
                    "02 Jan Reference 1234567890 12345678.90",
                    (
                        "x=20.0:02", "x=40.0:Jan", "x=100.0:Reference",
                        "x=260.0:1234567890", "x=450.0:12345678.90",
                    ),
                ),
            ],
            50,
            1,
        )
        rendered = redact_pages([page]).pages[0]
        self.assertNotIn("1234567890", rendered)
        self.assertIn("12345678.90", rendered)

    def test_merge_removes_only_same_source_overlap(self):
        shared = row(2, 1)
        first = extraction([row(1, 1), shared], [1, 2])
        second = extraction([shared, row(3, 1)], [2, 3])
        merged = merge_extractions([first, second])
        self.assertEqual(3, len(merged["transactions"]))
        self.assertEqual([1, 2, 3], merged["processed_pages"])

    def test_merge_preserves_same_financial_values_at_distinct_locations(self):
        merged = merge_extractions([extraction([row(1, 1), row(1, 2)], [1])])
        self.assertEqual(2, len(merged["transactions"]))

    def test_merge_rejects_conflicting_overlap(self):
        first = extraction([row(1, 1, "One")], [1])
        second = extraction([row(1, 1, "Two")], [1])
        with self.assertRaises(MergeError):
            merge_extractions([first, second])

    def test_text_pdf_is_usable(self):
        page = _FakePage([
            _word("Example", 50, 10), _word("Bank", 100, 10), _word("Statement", 140, 10),
            _word("18/08/2026", 280, 20),
            _word("02/01/2026", 50, 30), _word("Grocery", 130, 30),
            _word("purchase", 190, 30), _word("10.00", 260, 30), _word("990.00", 310, 30),
        ])
        with patch("services.llm_statement.ingest.pdfplumber.open", return_value=_FakePDF([page])):
            assessment = assess_pdf(b"fake-pdf")
        self.assertEqual("usable_text", assessment.status)
        self.assertEqual(1, assessment.pages[0].candidate_transaction_rows)

    def test_blank_pdf_requires_ocr(self):
        with patch("services.llm_statement.ingest.pdfplumber.open", return_value=_FakePDF([_FakePage([])])):
            assessment = assess_pdf(b"fake-pdf")
        self.assertEqual("requires_ocr", assessment.status)


def _word(text, x0, top):
    return {"text": text, "x0": x0, "top": top}


class _FakePage:
    width = 595
    height = 842

    def __init__(self, words):
        self.words = words

    def extract_words(self, **_kwargs):
        return self.words


class _FakePDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


if __name__ == "__main__":
    unittest.main()
