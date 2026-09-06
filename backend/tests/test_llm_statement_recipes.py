import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from services.llm_statement.ingest import ExtractedPage, PDFAssessment, PageLine
from services.llm_statement.recipe_registry import (
    CodeRecipeRegistry,
    extract_recipe,
    layout_shape,
    learn_recipe,
)
from services.llm_statement.pipeline import LLMStatementPipeline
from services.llm_statement.validator import StatementValidator


def _line(text, *spans):
    return PageLine(10, text, tuple(f"x={x}:{word}" for x, word in spans), 0, 550, 20)


def _assessment(closing="1148.00", debit="50.00"):
    lines = [
        _line("From Date: 01/01/2026 Opening Balance: R1 000.00",
              (10, "From"), (40, "Date:"), (75, "01/01/2026"),
              (180, "Opening"), (230, "Balance:"), (280, "R1"), (300, "000.00")),
        _line(f"To Date: 31/01/2026 Closing Balance: R{closing}",
              (10, "To"), (30, "Date:"), (65, "31/01/2026"),
              (180, "Closing"), (230, "Balance:"), (280, f"R{closing}")),
        _line("Date Description Money In Money Out Fee* Balance",
              (10, "Date"), (80, "Description"), (250, "Money"), (290, "In"),
              (340, "Money"), (385, "Out"), (430, "Fee*"), (480, "Balance")),
        _line("02/01/2026 Deposit 200.00 1200.00",
              (10, "02/01/2026"), (80, "Deposit"), (250, "200.00"), (480, "1200.00")),
        _line(f"03/01/2026 Purchase {debit} -2.00 {closing}",
              (10, "03/01/2026"), (80, "Purchase"), (340, debit),
              (430, "-2.00"), (480, closing)),
    ]
    page = ExtractedPage(1, 595, 842, "usable_text", lines, 200, 2)
    return PDFAssessment("usable_text", [page], "ok")


def _recipe(assessment):
    return {"version": 1, "shape": layout_shape(assessment), "date_format": "%d/%m/%Y"}


class RecipeRegistryTests(unittest.IsolatedAsyncioTestCase):
    def test_recipe_is_global_data_only_source_file(self):
        assessment = _assessment()
        with TemporaryDirectory() as folder:
            first = CodeRecipeRegistry(folder)
            self.assertTrue(first.save(assessment, _recipe(assessment)))
            second = CodeRecipeRegistry(folder)
            loaded = second.load(assessment)
            self.assertEqual(_recipe(assessment), loaded)
            files = list(Path(folder).glob("*.json"))
            self.assertEqual(1, len(files))
            payload = files[0].read_text(encoding="utf-8")
            self.assertNotIn("Deposit", payload)
            self.assertNotIn("1148.00", payload)
            self.assertEqual({"version", "shape", "date_format"}, set(json.loads(payload)))

    def test_recipe_is_learned_only_after_exact_replay(self):
        assessment = _assessment()
        validator = StatementValidator()
        reference = extract_recipe(assessment, _recipe(assessment))
        self.assertEqual(_recipe(assessment), learn_recipe(assessment, reference, validator))
        reference["transactions"][0]["amount"] = "201.00"
        self.assertIsNone(learn_recipe(assessment, reference, validator))

    async def test_pipeline_recipe_hit_makes_no_provider_request(self):
        assessment = _assessment()
        with TemporaryDirectory() as folder:
            registry = CodeRecipeRegistry(folder)
            registry.save(assessment, _recipe(assessment))
            pipeline = object.__new__(LLMStatementPipeline)
            pipeline.provider = None
            pipeline.validator = StatementValidator()
            pipeline.max_pages = 10
            pipeline.max_characters = 10000
            pipeline.strict_redaction = True
            pipeline.layout_hmac_key = b"test-key"
            pipeline.recipe_registry = registry
            pipeline.allow_provider_fallback = False
            pipeline.model_id = "unused"
            with patch("services.llm_statement.pipeline.assess_pdf", return_value=assessment):
                result = await pipeline.process(b"pdf")
            self.assertEqual("parsed", result.status)
            self.assertEqual("code_recipe", result.extraction_path)
            self.assertEqual([], result.provider_request_ids)
            self.assertEqual(0, result.input_tokens)

    async def test_changed_financials_fail_closed_without_paid_fallback(self):
        original = _assessment()
        changed = _assessment(closing="999.00")
        with TemporaryDirectory() as folder:
            registry = CodeRecipeRegistry(folder)
            registry.save(original, _recipe(original))
            pipeline = object.__new__(LLMStatementPipeline)
            pipeline.provider = None
            pipeline.validator = StatementValidator()
            pipeline.max_pages = 10
            pipeline.max_characters = 10000
            pipeline.strict_redaction = True
            pipeline.layout_hmac_key = b"test-key"
            pipeline.recipe_registry = registry
            pipeline.allow_provider_fallback = False
            pipeline.model_id = "unused"
            with patch("services.llm_statement.pipeline.assess_pdf", return_value=changed):
                result = await pipeline.process(b"pdf")
            self.assertEqual("parser_not_available", result.status)
            self.assertEqual("none", result.extraction_path)


if __name__ == "__main__":
    unittest.main()
