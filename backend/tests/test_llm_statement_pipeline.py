import unittest
from unittest.mock import patch

from services.llm_statement.ingest import ExtractedPage, PDFAssessment, PageLine
from services.llm_statement.pipeline import LLMStatementPipeline
from services.llm_statement.provider import ModelResponse
from services.llm_statement.redaction import RedactionResult
from services.llm_statement.validator import StatementValidator


def _transaction(description, amount, direction, ordinal, balance_after):
    return {
        "date": f"2026-01-0{ordinal + 1}", "value_date": None,
        "description": description, "amount": amount, "direction": direction,
        "additional_fee": "0.00",
        "balance_after": balance_after, "source_page": 1,
        "source_row_ordinal": ordinal, "source_bbox": None,
    }


def statement():
    return {
        "document_type": "bank_statement", "bank_name": "Example Bank",
        "account_type": "Current", "account_number_last4": "1234",
        "statement_period_start": "2026-01-01", "statement_period_end": "2026-01-31",
        "opening_balance": "1000.00", "closing_balance": "1150.00", "currency": "ZAR",
        "processed_pages": [1], "transaction_pages": [1],
        "transactions": [
            _transaction("Deposit", "200.00", "credit", 1, "1200.00"),
            _transaction("Fee", "50.00", "debit", 2, "1150.00"),
        ],
        "extraction_notes": [],
    }


class _FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.retry_instructions = []

    async def extract(self, _document_id, _page_text, retry_instruction=None):
        self.retry_instructions.append(retry_instruction)
        extraction = self.responses[self.calls]
        self.calls += 1
        return ModelResponse(extraction, f"msg_{self.calls}", 10, 5, "end_turn")


def _pipeline(responses):
    pipeline = object.__new__(LLMStatementPipeline)
    pipeline.provider = _FakeProvider(responses)
    pipeline.validator = StatementValidator()
    pipeline.max_pages = 10
    pipeline.max_characters = 10000
    pipeline.chunk_characters = 5000
    pipeline.chunk_pages = 12
    pipeline.strict_redaction = True
    pipeline.layout_hmac_key = b"test-key"
    pipeline.model_id = "test-model"
    return pipeline


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_validation_once_then_passes(self):
        failed = statement()
        failed["transactions"][1]["amount"] = "60.00"
        passed = statement()
        pipeline = _pipeline([failed, passed])
        page = ExtractedPage(1, 595, 842, "usable_text", [PageLine(10, "statement", ())], 100, 0)
        assessment = PDFAssessment("usable_text", [page], "ok")
        redaction = RedactionResult(True, ["<page number=1>statement</page>"], 0, (), {})

        with patch("services.llm_statement.pipeline.assess_pdf", return_value=assessment), patch(
            "services.llm_statement.pipeline.redact_pages", return_value=redaction
        ):
            result = await pipeline.process(b"pdf")

        self.assertEqual("parsed", result.status)
        self.assertEqual("passed", result.validation.status)
        self.assertEqual(2, pipeline.provider.calls)
        self.assertEqual(20, result.input_tokens)
        self.assertEqual(10, result.output_tokens)
        self.assertIn("balance_mismatch", pipeline.provider.retry_instructions[1])
        self.assertIn("page 1, transaction row 2", pipeline.provider.retry_instructions[1])

    def test_chunks_do_not_repeat_previous_transaction_page(self):
        pipeline = _pipeline([])
        chunks = pipeline._chunks(["page-1", "page-2", "page-3", "page-4"], 3, 1000)
        self.assertEqual(["page-1\npage-2\npage-3", "page-1\npage-4"], chunks)

    async def test_redaction_failure_never_calls_provider(self):
        pipeline = _pipeline([])
        page = ExtractedPage(1, 595, 842, "usable_text", [], 100, 0)
        assessment = PDFAssessment("usable_text", [page], "ok")
        redaction = RedactionResult(False, ["unsafe"], 0, ("possible_identifier",), {})
        with patch("services.llm_statement.pipeline.assess_pdf", return_value=assessment), patch(
            "services.llm_statement.pipeline.redact_pages", return_value=redaction
        ):
            result = await pipeline.process(b"pdf")
        self.assertEqual("redaction_failed", result.status)
        self.assertEqual(0, pipeline.provider.calls)

    async def test_not_a_statement_does_not_spend_a_retry(self):
        not_statement = statement()
        not_statement["document_type"] = "not_a_statement"
        not_statement["transactions"] = []
        pipeline = _pipeline([not_statement])
        page = ExtractedPage(1, 595, 842, "usable_text", [], 100, 0)
        assessment = PDFAssessment("usable_text", [page], "ok")
        redaction = RedactionResult(True, ["<page number=1>document</page>"], 0, (), {})
        with patch("services.llm_statement.pipeline.assess_pdf", return_value=assessment), patch(
            "services.llm_statement.pipeline.redact_pages", return_value=redaction
        ):
            result = await pipeline.process(b"pdf")
        self.assertEqual("not_a_statement", result.status)
        self.assertEqual(1, pipeline.provider.calls)


if __name__ == "__main__":
    unittest.main()
