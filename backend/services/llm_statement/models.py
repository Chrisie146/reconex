"""Domain types shared by the LLM statement pipeline.

Money remains text at the provider boundary and ``Decimal`` inside validation.
These types intentionally contain no database or FastAPI dependencies.
"""

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    source_page: Optional[int] = None
    source_row_ordinal: Optional[int] = None


@dataclass(frozen=True)
class CheckResult:
    name: str
    applicable: bool
    passed: bool
    observed: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    status: str
    failures: List[ValidationIssue]
    warnings: List[ValidationIssue]
    checks: List[CheckResult]
    opening_balance: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    total_debits: Optional[Decimal] = None
    expected_closing_balance: Optional[Decimal] = None
    closing_balance: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    schema_version: str = "statement-extraction-v2"
    validator_version: str = "statement-validator-v2"

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> Dict[str, Any]:
        def serialise(value: Any) -> Any:
            if isinstance(value, Decimal):
                return format(value, "f")
            if isinstance(value, list):
                return [serialise(item) for item in value]
            if isinstance(value, dict):
                return {key: serialise(item) for key, item in value.items()}
            return value

        return serialise(asdict(self))


@dataclass(frozen=True)
class PipelineResult:
    status: str
    document_id: str
    extraction: Optional[Dict[str, Any]] = None
    validation: Optional[ValidationResult] = None
    bank_source: Optional[str] = None
    provider_request_ids: List[str] = field(default_factory=list)
    message: Optional[str] = None
    layout_id: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    extraction_path: str = "model"
    recipe_created: bool = False
