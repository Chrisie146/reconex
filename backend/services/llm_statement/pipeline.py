"""Orchestration for LLM-first bank-statement extraction."""

import hashlib
import hmac
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence
import uuid

from .ingest import ExtractedPage, PDFIngestError, assess_pdf
from .recipe_registry import CodeRecipeRegistry, RecipeMiss, extract_recipe, learn_recipe
from .merge import MergeError, merge_extractions
from .models import PipelineResult
from .provider import AnthropicStatementProvider, ProviderConfig, ProviderError
from .redaction import redact_pages
from .validator import StatementValidator


logger = logging.getLogger(__name__)


class LLMStatementPipeline:
    PROMPT_VERSION = "extract-statement-v6"
    SCHEMA_VERSION = "statement-extraction-v2"

    def __init__(
        self,
        provider_config: ProviderConfig,
        max_pages: int = 100,
        max_characters: int = 2_000_000,
        chunk_characters: int = 80_000,
        chunk_pages: int = 12,
        strict_redaction: bool = True,
        layout_hmac_key: bytes = b"development-only-layout-key",
        recipe_registry_path: Optional[Path] = None,
        learn_recipes: bool = True,
        allow_provider_fallback: bool = True,
    ) -> None:
        base = Path(__file__).resolve().parents[2]
        self.provider = AnthropicStatementProvider(
            provider_config,
            base / "prompts" / "extract_statement.md",
            base / "prompts" / "extract_statement.schema.json",
        )
        self.validator = StatementValidator()
        self.max_pages = max_pages
        self.max_characters = max_characters
        self.chunk_characters = chunk_characters
        self.chunk_pages = chunk_pages
        self.strict_redaction = strict_redaction
        self.layout_hmac_key = layout_hmac_key
        self.model_id = provider_config.model
        self.recipe_registry = CodeRecipeRegistry(
            recipe_registry_path or base / "services" / "llm_statement" / "layout_recipes"
        )
        self.learn_recipes = learn_recipes
        self.allow_provider_fallback = allow_provider_fallback

    @staticmethod
    def _log_event(event: Dict[str, Any]) -> None:
        logger.info("llm_statement_event %s", json.dumps(event, sort_keys=True, separators=(",", ":")))

    @staticmethod
    def _opaque_document_id(content: bytes) -> str:
        # A random ID avoids making a customer document hash visible to the provider.
        return str(uuid.uuid4())

    def _safe_layout_id(self, pages: Sequence[ExtractedPage]) -> str:
        structure = "|".join(f"{page.width:.0f}x{page.height:.0f}:{len(page.lines)}" for page in pages)
        return hmac.new(self.layout_hmac_key, structure.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    def _chunks(self, pages: Sequence[str], maximum_pages: int, maximum_characters: int) -> List[str]:
        if not pages:
            return []
        if len(pages) == 1:
            return [pages[0]]
        header = pages[0]
        remaining = list(pages[1:])
        chunks: List[List[str]] = []
        current: List[str] = []
        current_chars = len(header)
        for page in remaining:
            would_exceed = current and (
                len(current) >= maximum_pages - 1 or current_chars + len(page) > maximum_characters
            )
            if would_exceed:
                chunks.append(current)
                # Each chunk already receives the first-page statement header.
                # Repeating the previous physical page causes two independent
                # transcriptions of the same rows and creates merge conflicts.
                current = [page]
                current_chars = len(header) + sum(len(item) for item in current)
            else:
                current.append(page)
                current_chars += len(page)
        if current:
            chunks.append(current)
        if not chunks:
            return [header]
        return ["\n".join([header] + chunk) for chunk in chunks]

    @staticmethod
    def _coverage_complete(extraction: Dict[str, Any], candidate_rows_by_page: Dict[int, int]) -> bool:
        observed: Dict[int, int] = {}
        for transaction in extraction.get("transactions", []):
            if isinstance(transaction, dict) and isinstance(transaction.get("source_page"), int):
                page = transaction["source_page"]
                observed[page] = observed.get(page, 0) + 1
        return all(observed.get(page, 0) >= candidates for page, candidates in candidate_rows_by_page.items() if candidates > 0)

    async def _extract_attempt(
        self,
        document_id: str,
        redacted_pages: Sequence[str],
        retry: bool,
        validation_instruction: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], List[str], int, int]:
        page_limit = 2 if retry else self.chunk_pages
        character_limit = max(10_000, self.chunk_characters // 2) if retry else self.chunk_characters
        chunks = self._chunks(redacted_pages, page_limit, character_limit)
        extractions = []
        request_ids: List[str] = []
        input_tokens = 0
        output_tokens = 0
        instruction = (
            "This is the only retry. Transcribe each supplied physical row carefully and preserve source locations. "
            "Recheck every printed debit, credit, withdrawal, deposit, paid-in, paid-out, or signed amount column. "
            "Copy each visibly printed transaction magnitude into amount and derive direction only from its column, "
            "sign, Dr/Cr marker, or printed legend. Recheck printed currency labels and symbols. "
            "Do not calculate or change values to make balances agree, and retain null when a value is truly absent."
            if retry else None
        )
        if instruction and validation_instruction:
            instruction += " Validator findings from the previous transcription: " + validation_instruction
        for chunk in chunks:
            response = await self.provider.extract(document_id, chunk, instruction)
            extractions.append(response.extraction)
            request_ids.append(response.request_id)
            input_tokens += response.input_tokens
            output_tokens += response.output_tokens
        return extractions, request_ids, input_tokens, output_tokens

    async def process(self, content: bytes) -> PipelineResult:
        document_id = self._opaque_document_id(content)
        started = time.monotonic()
        try:
            assessment = assess_pdf(content, self.max_pages, self.max_characters)
        except PDFIngestError as exc:
            self._log_event({"document_id": document_id, "stage": "ingest", "status": exc.status})
            return PipelineResult(exc.status, document_id, message=str(exc))
        if assessment.status != "usable_text":
            return PipelineResult(assessment.status, document_id, message=assessment.message)

        layout_id = self._safe_layout_id(assessment.pages)
        registry = getattr(self, "recipe_registry", None)
        if registry is not None:
            recipe = registry.load(assessment)
            if recipe is not None:
                try:
                    extraction = extract_recipe(assessment, recipe)
                    coverage = self._coverage_complete(extraction, assessment.candidate_rows_by_page)
                    validation = self.validator.validate(
                        extraction,
                        expected_pages=assessment.expected_pages,
                        coverage_evidence_complete=coverage,
                    )
                    self._log_event({
                        "document_id": document_id,
                        "layout_id": layout_id,
                        "path": "code_recipe",
                        "status": validation.status,
                        "validation_codes": [issue.code for issue in validation.failures],
                        "transaction_count": len(extraction.get("transactions", [])),
                        "duration_ms": int((time.monotonic() - started) * 1000),
                    })
                    if validation.passed:
                        return PipelineResult(
                            "parsed", document_id, extraction, validation, "code_recipe", [],
                            layout_id=layout_id, extraction_path="code_recipe",
                        )
                except (RecipeMiss, ValueError, TypeError):
                    # A changed or unsupported statement must never be forced
                    # through an old recipe; the verified model path may retry it.
                    pass

        if not getattr(self, "allow_provider_fallback", True):
            return PipelineResult(
                "parser_not_available", document_id,
                message="No verified parser recipe exists for this statement format",
                layout_id=layout_id, extraction_path="none",
            )

        redaction = redact_pages(assessment.pages)
        if self.strict_redaction and not redaction.safe:
            return PipelineResult("redaction_failed", document_id, message="Potential identifiers remain after redaction")

        all_request_ids: List[str] = []
        total_input_tokens = 0
        total_output_tokens = 0
        last_extraction: Optional[Dict[str, Any]] = None
        last_validation = None
        retry_validation_instruction: Optional[str] = None
        try:
            for attempt in (1, 2):
                chunk_extractions, request_ids, input_tokens, output_tokens = await self._extract_attempt(
                    document_id,
                    redaction.pages,
                    retry=attempt == 2,
                    validation_instruction=retry_validation_instruction,
                )
                all_request_ids.extend(request_ids)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                try:
                    extraction = merge_extractions(chunk_extractions)
                except MergeError as exc:
                    self._log_event({
                        "document_id": document_id,
                        "layout_id": layout_id,
                        "stage": "merge",
                        "attempt": attempt,
                        "status": "failed",
                        "model_id": self.model_id,
                        "prompt_version": self.PROMPT_VERSION,
                        "schema_version": self.SCHEMA_VERSION,
                        "provider_request_ids": request_ids,
                        "error_type": type(exc).__name__,
                    })
                    if attempt == 1:
                        continue
                    return PipelineResult(
                        "unparseable", document_id, last_extraction, last_validation,
                        provider_request_ids=all_request_ids, message=str(exc), layout_id=layout_id,
                        input_tokens=total_input_tokens, output_tokens=total_output_tokens,
                    )
                coverage = self._coverage_complete(extraction, assessment.candidate_rows_by_page)
                validation = self.validator.validate(
                    extraction,
                    expected_pages=assessment.expected_pages,
                    coverage_evidence_complete=coverage,
                )
                last_extraction = extraction
                last_validation = validation
                retry_findings = []
                for issue in validation.failures:
                    location = ""
                    if issue.source_page is not None:
                        location = f" on page {issue.source_page}"
                        if issue.source_row_ordinal is not None:
                            location += f", transaction row {issue.source_row_ordinal}"
                    retry_findings.append(f"{issue.code}{location}")
                retry_validation_instruction = "; ".join(dict.fromkeys(retry_findings))
                transactions = extraction.get("transactions", [])
                safe_transaction_count = len(transactions) if isinstance(transactions, list) else 0
                safe_null_amount_count = (
                    sum(
                        1
                        for transaction in transactions
                        if isinstance(transaction, dict) and transaction.get("amount") is None
                    )
                    if isinstance(transactions, list)
                    else 0
                )
                self._log_event({
                    "document_id": document_id,
                    "layout_id": layout_id,
                    "path": "model",
                    "attempt": attempt,
                    "status": validation.status,
                    "model_id": self.model_id,
                    "prompt_version": self.PROMPT_VERSION,
                    "schema_version": self.SCHEMA_VERSION,
                    "provider_request_ids": request_ids,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "validation_codes": [issue.code for issue in validation.failures],
                    "transaction_count": safe_transaction_count,
                    "null_amount_count": safe_null_amount_count,
                    "currency_present": bool(extraction.get("currency")),
                })
                if extraction.get("document_type") == "not_a_statement":
                    return PipelineResult(
                        "not_a_statement", document_id, extraction, validation,
                        provider_request_ids=all_request_ids, message="Document is not a bank statement",
                        layout_id=layout_id, input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                if validation.passed:
                    bank_source = str(extraction.get("bank_name") or "llm").strip().lower().replace(" ", "_")
                    recipe_created = False
                    if registry is not None and getattr(self, "learn_recipes", True):
                        recipe = learn_recipe(assessment, extraction, self.validator)
                        recipe_created = bool(recipe and registry.save(assessment, recipe))
                    return PipelineResult(
                        "parsed", document_id, extraction, validation, bank_source, all_request_ids,
                        layout_id=layout_id, input_tokens=total_input_tokens, output_tokens=total_output_tokens,
                        extraction_path="model", recipe_created=recipe_created,
                    )
        except ProviderError as exc:
            return PipelineResult(
                exc.status, document_id, last_extraction, last_validation,
                provider_request_ids=all_request_ids, message=str(exc), layout_id=layout_id,
                input_tokens=total_input_tokens, output_tokens=total_output_tokens,
            )

        if last_extraction and last_extraction.get("document_type") == "not_a_statement":
            status = "not_a_statement"
        else:
            status = "unparseable"
        return PipelineResult(
            status, document_id, last_extraction, last_validation,
            provider_request_ids=all_request_ids, message="Statement could not be verified",
            layout_id=layout_id, input_tokens=total_input_tokens, output_tokens=total_output_tokens,
        )
