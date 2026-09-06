"""Pure deterministic validation for LLM-extracted statements."""

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .models import CheckResult, ValidationIssue, ValidationResult


MONEY_PATTERN = re.compile(r"^-?(?:0|[1-9]\d*)\.\d{2}$")
UNSIGNED_MONEY_PATTERN = re.compile(r"^(?:0|[1-9]\d*)\.\d{2}$")
LAST4_PATTERN = re.compile(r"^\d{4}$")
ISO_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")

TOP_LEVEL_KEYS: Set[str] = {
    "document_type", "bank_name", "account_type", "account_number_last4",
    "statement_period_start", "statement_period_end", "opening_balance",
    "closing_balance", "currency", "processed_pages", "transaction_pages",
    "transactions", "extraction_notes",
}
TRANSACTION_KEYS: Set[str] = {
    "date", "value_date", "description", "amount", "direction",
    "balance_after", "source_page", "source_row_ordinal", "source_bbox", "additional_fee",
}


def _issue(code: str, message: str, txn: Optional[Mapping[str, Any]] = None) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        message=message,
        source_page=txn.get("source_page") if txn else None,
        source_row_ordinal=txn.get("source_row_ordinal") if txn else None,
    )


def _parse_date(value: Any) -> Optional[date]:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _parse_money(value: Any, unsigned: bool = False) -> Optional[Decimal]:
    if not isinstance(value, str):
        return None
    pattern = UNSIGNED_MONEY_PATTERN if unsigned else MONEY_PATTERN
    if not pattern.fullmatch(value):
        return None
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return None
    if not parsed.is_finite() or (unsigned and parsed < 0):
        return None
    return parsed


def _valid_positive_int_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(type(item) is int and item > 0 for item in value)
        and len(set(value)) == len(value)
    )


class StatementValidator:
    """Validate an extraction without modifying or repairing it."""

    VERSION = "statement-validator-v2"

    def __init__(self, tolerance: Decimal = Decimal("0.01")) -> None:
        self.tolerance = tolerance

    def validate(
        self,
        extraction: Mapping[str, Any],
        expected_pages: Optional[Iterable[int]] = None,
        coverage_evidence_complete: bool = True,
    ) -> ValidationResult:
        failures: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        checks: List[CheckResult] = []

        if not isinstance(extraction, Mapping):
            failure = _issue("invalid_root", "Extraction must be an object")
            return ValidationResult("failed", [failure], [], [CheckResult("schema", True, False)])

        missing = TOP_LEVEL_KEYS - set(extraction)
        unknown = set(extraction) - TOP_LEVEL_KEYS
        if missing:
            failures.append(_issue("missing_fields", "Missing fields: " + ", ".join(sorted(missing))))
        if unknown:
            failures.append(_issue("unknown_fields", "Unknown fields: " + ", ".join(sorted(unknown))))

        document_type = extraction.get("document_type")
        if document_type not in {"bank_statement", "not_a_statement", "ambiguous"}:
            failures.append(_issue("invalid_document_type", "Invalid document_type"))
        elif document_type == "not_a_statement":
            failures.append(_issue("not_a_statement", "Document is not a bank statement"))
        elif document_type == "ambiguous":
            failures.append(_issue("ambiguous_document", "Document type is ambiguous"))

        last4 = extraction.get("account_number_last4")
        if last4 is not None and (not isinstance(last4, str) or not LAST4_PATTERN.fullmatch(last4)):
            failures.append(_issue("invalid_account_last4", "Account last four digits must contain exactly four digits"))
        currency = extraction.get("currency")
        if currency is None:
            failures.append(_issue("missing_currency", "Statement currency is required"))
        elif not isinstance(currency, str) or not ISO_CURRENCY_PATTERN.fullmatch(currency):
            failures.append(_issue("invalid_currency", "Currency must be an uppercase ISO 4217 code"))
        for field in ("bank_name", "account_type"):
            value = extraction.get(field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                failures.append(_issue(f"invalid_{field}", f"{field} must be a non-empty string or null"))

        period_start = _parse_date(extraction.get("statement_period_start"))
        period_end = _parse_date(extraction.get("statement_period_end"))
        if period_start is None or period_end is None:
            failures.append(_issue("missing_statement_period", "A valid statement period is required"))
        elif period_start > period_end:
            failures.append(_issue("invalid_statement_period", "Statement period start is after its end"))

        opening_raw = extraction.get("opening_balance")
        closing_raw = extraction.get("closing_balance")
        opening = _parse_money(opening_raw)
        closing = _parse_money(closing_raw)
        if opening_raw is not None and opening is None:
            failures.append(_issue("invalid_opening_balance", "Opening balance has an invalid monetary format"))
        if closing_raw is not None and closing is None:
            failures.append(_issue("invalid_closing_balance", "Closing balance has an invalid monetary format"))
        if opening is None or closing is None:
            warnings.append(_issue("missing_reconciliation_anchor", "Opening and closing balances are required to verify reconciliation"))

        processed_pages = extraction.get("processed_pages")
        transaction_pages = extraction.get("transaction_pages")
        pages_valid = _valid_positive_int_list(processed_pages) and _valid_positive_int_list(transaction_pages)
        if not pages_valid:
            failures.append(_issue("invalid_page_coverage", "Page lists must contain unique positive integers"))
        elif not set(transaction_pages).issubset(set(processed_pages)):
            failures.append(_issue("transaction_page_not_processed", "Every transaction page must be processed"))
            pages_valid = False

        if expected_pages is not None and pages_valid:
            expected = set(expected_pages)
            observed = set(processed_pages)
            if expected != observed:
                failures.append(_issue("incomplete_page_coverage", f"Expected pages {sorted(expected)}, observed {sorted(observed)}"))
                pages_valid = False

        raw_transactions = extraction.get("transactions")
        if not isinstance(raw_transactions, list):
            failures.append(_issue("invalid_transactions", "transactions must be an array"))
            raw_transactions = []

        valid_rows: List[Tuple[Mapping[str, Any], date, Decimal, str, Optional[Decimal]]] = []
        locations: List[Tuple[int, int]] = []
        for index, raw in enumerate(raw_transactions):
            if not isinstance(raw, Mapping):
                failures.append(_issue("invalid_transaction", f"Transaction {index + 1} must be an object"))
                continue
            missing_txn = TRANSACTION_KEYS - set(raw)
            unknown_txn = set(raw) - TRANSACTION_KEYS
            if missing_txn:
                failures.append(_issue("missing_transaction_fields", "Missing transaction fields: " + ", ".join(sorted(missing_txn)), raw))
            if unknown_txn:
                failures.append(_issue("unknown_transaction_fields", "Unknown transaction fields: " + ", ".join(sorted(unknown_txn)), raw))

            txn_date = _parse_date(raw.get("date"))
            if txn_date is None:
                failures.append(_issue("invalid_transaction_date", "Transaction date is required and must be ISO formatted", raw))
            value_date = raw.get("value_date")
            if value_date is not None and _parse_date(value_date) is None:
                failures.append(_issue("invalid_value_date", "Value date must be ISO formatted or null", raw))
            description = raw.get("description")
            if not isinstance(description, str) or not description.strip():
                failures.append(_issue("empty_description", "Transaction description is required", raw))
            amount = _parse_money(raw.get("amount"), unsigned=True)
            fee = _parse_money(raw.get("additional_fee"))
            if fee is None:
                failures.append(_issue("invalid_additional_fee", "Additional fee must be known and a signed decimal string", raw))
            if amount is None:
                failures.append(_issue("invalid_amount", "Transaction amount must be an unsigned decimal string with two fractional digits", raw))
            direction = raw.get("direction")
            if direction not in {"debit", "credit"}:
                failures.append(_issue("invalid_direction", "Transaction direction must be debit or credit", raw))
            balance_after_raw = raw.get("balance_after")
            balance_after = _parse_money(balance_after_raw) if balance_after_raw is not None else None
            if balance_after_raw is not None and balance_after is None:
                failures.append(_issue("invalid_running_balance", "Running balance must be a signed decimal string with two fractional digits", raw))
            page = raw.get("source_page")
            ordinal = raw.get("source_row_ordinal")
            if type(page) is not int or page <= 0 or type(ordinal) is not int or ordinal <= 0:
                failures.append(_issue("invalid_source_location", "Source page and row ordinal must be positive integers", raw))
            else:
                locations.append((page, ordinal))
                if pages_valid and page not in transaction_pages:
                    failures.append(_issue("source_page_not_declared", "Transaction source page is not in transaction_pages", raw))
            bbox = raw.get("source_bbox")
            if bbox is not None:
                bbox_keys = {"x0", "top", "x1", "bottom"}
                if (
                    not isinstance(bbox, Mapping)
                    or set(bbox) != bbox_keys
                    or any(type(bbox[key]) not in {int, float} for key in bbox_keys)
                ):
                    failures.append(_issue("invalid_source_bbox", "Source bbox must contain four numeric coordinates", raw))

            if txn_date and period_start and period_end and not period_start <= txn_date <= period_end:
                failures.append(_issue("date_out_of_period", f"Transaction date {txn_date.isoformat()} is outside the statement period", raw))
            if txn_date and amount is not None and fee is not None and direction in {"debit", "credit"}:
                valid_rows.append((raw, txn_date, amount, direction, balance_after))

        duplicate_locations = [location for location, count in Counter(locations).items() if count > 1]
        if duplicate_locations:
            failures.append(_issue("duplicate_source_location", f"Duplicate physical source rows: {duplicate_locations}"))

        schema_passed = not any(issue.code in {
            "invalid_root", "missing_fields", "unknown_fields", "invalid_document_type",
            "invalid_account_last4", "missing_currency", "invalid_currency", "invalid_bank_name",
            "invalid_account_type", "invalid_statement_period", "invalid_opening_balance",
            "invalid_closing_balance",
            "missing_statement_period", "invalid_transactions", "invalid_transaction",
            "missing_transaction_fields", "unknown_transaction_fields", "invalid_transaction_date",
            "invalid_value_date", "empty_description", "invalid_amount", "invalid_direction",
            "invalid_running_balance", "invalid_source_location", "invalid_source_bbox", "invalid_additional_fee",
        } for issue in failures)
        checks.append(CheckResult("schema", True, schema_passed, {"transaction_count": len(raw_transactions)}))

        totals_applicable = opening is not None and closing is not None and len(valid_rows) == len(raw_transactions)
        credits = sum((row[2] for row in valid_rows if row[3] == "credit"), Decimal("0.00"))
        debits = sum((row[2] for row in valid_rows if row[3] == "debit"), Decimal("0.00"))
        credits += sum((max(Decimal(row[0]["additional_fee"]), Decimal(0)) for row in valid_rows), Decimal(0))
        debits += sum((max(-Decimal(row[0]["additional_fee"]), Decimal(0)) for row in valid_rows), Decimal(0))
        expected_closing = opening + credits - debits if opening is not None else None
        difference = abs(expected_closing - closing) if expected_closing is not None and closing is not None else None
        reconciliation_passed = bool(totals_applicable and difference is not None and difference <= self.tolerance)
        if totals_applicable and not reconciliation_passed:
            failures.append(_issue("balance_mismatch", f"Opening plus credits less debits differs from closing by {difference}"))
        checks.append(CheckResult("document_reconciliation", totals_applicable, reconciliation_passed, {
            "opening_balance": opening, "total_credits": credits, "total_debits": debits,
            "expected_closing_balance": expected_closing, "closing_balance": closing,
            "difference": difference, "tolerance": self.tolerance,
        }))

        dates = [row[1] for row in valid_rows]
        asc = all(left <= right for left, right in zip(dates, dates[1:]))
        desc = all(left >= right for left, right in zip(dates, dates[1:]))

        chain_applicable = opening is not None and bool(valid_rows) and any(row[4] is not None for row in valid_rows)
        chain_passed = True
        checked_steps = 0
        if desc and not asc:
            for index, (raw, _txn_date, amount, direction, balance_after) in enumerate(valid_rows):
                older_balance = valid_rows[index + 1][4] if index + 1 < len(valid_rows) else opening
                if older_balance is None or balance_after is None:
                    continue
                expected_balance = older_balance + amount if direction == "credit" else older_balance - amount
                expected_balance += Decimal(raw["additional_fee"])
                step_difference = abs(expected_balance - balance_after)
                checked_steps += 1
                if step_difference > self.tolerance:
                    chain_passed = False
                    failures.append(_issue("running_balance_mismatch", f"Running balance differs by {step_difference}", raw))
        else:
            previous = opening
            for raw, _txn_date, amount, direction, balance_after in valid_rows:
                if previous is None or balance_after is None:
                    previous = balance_after
                    continue
                expected_balance = previous + amount if direction == "credit" else previous - amount
                expected_balance += Decimal(raw["additional_fee"])
                step_difference = abs(expected_balance - balance_after)
                checked_steps += 1
                if step_difference > self.tolerance:
                    chain_passed = False
                    failures.append(_issue("running_balance_mismatch", f"Running balance differs by {step_difference}", raw))
                previous = balance_after
        if chain_applicable and checked_steps == 0:
            chain_passed = False
            warnings.append(_issue("running_balance_gaps", "Printed running balances were too sparse to validate an adjacent step"))
        checks.append(CheckResult("running_balance_chain", chain_applicable, chain_passed, {"checked_steps": checked_steps}))

        if len(dates) > 1 and not asc and not desc:
            warnings.append(_issue("non_monotonic_dates", "Transaction dates change ordering direction"))
        checks.append(CheckResult("date_order", bool(dates), asc or desc, {"order": "ascending" if asc else "descending" if desc else "mixed"}))

        if pages_valid and transaction_pages and len(raw_transactions) < len(transaction_pages):
            warnings.append(_issue("low_transaction_density", "There are fewer transactions than declared transaction pages"))

        coverage_passed = pages_valid and coverage_evidence_complete
        if not coverage_evidence_complete:
            warnings.append(_issue("incomplete_coverage_evidence", "Independent extraction coverage evidence is incomplete"))
        checks.append(CheckResult("coverage", True, coverage_passed, {"processed_pages": processed_pages, "transaction_pages": transaction_pages}))

        notes = extraction.get("extraction_notes")
        if not isinstance(notes, list):
            failures.append(_issue("invalid_extraction_notes", "extraction_notes must be an array"))
        else:
            expected_note_keys = {"source_page", "source_row_ordinal", "code", "message"}
            for note in notes:
                if (
                    not isinstance(note, Mapping)
                    or set(note) != expected_note_keys
                    or type(note.get("source_page")) is not int
                    or note.get("source_page", 0) <= 0
                    or (note.get("source_row_ordinal") is not None and type(note.get("source_row_ordinal")) is not int)
                    or not isinstance(note.get("code"), str)
                    or not note.get("code")
                    or not isinstance(note.get("message"), str)
                    or not note.get("message")
                ):
                    failures.append(_issue("invalid_extraction_note", "Extraction note has an invalid shape"))
                    break
        notes_valid = not any(issue.code in {"invalid_extraction_notes", "invalid_extraction_note"} for issue in failures)
        checks.append(CheckResult("extraction_notes", True, notes_valid, {"count": len(notes) if isinstance(notes, list) else None}))

        if failures:
            status = "failed"
        elif not totals_applicable or not coverage_passed:
            status = "unverifiable"
        else:
            status = "passed"

        return ValidationResult(
            status=status,
            failures=failures,
            warnings=warnings,
            checks=checks,
            opening_balance=opening,
            total_credits=credits,
            total_debits=debits,
            expected_closing_balance=expected_closing,
            closing_balance=closing,
            difference=difference,
            validator_version=self.VERSION,
        )
