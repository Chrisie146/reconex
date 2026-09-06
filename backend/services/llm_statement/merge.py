"""Merge page chunks while preserving legitimate duplicate transactions."""

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping, Tuple


class MergeError(ValueError):
    pass


METADATA_FIELDS = (
    "document_type", "bank_name", "account_type", "account_number_last4",
    "statement_period_start", "statement_period_end", "opening_balance",
    "closing_balance", "currency",
)


def _row_location(row: Mapping[str, Any]) -> Tuple[Any, Any]:
    return row.get("source_page"), row.get("source_row_ordinal")


def merge_extractions(extractions: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    items = list(extractions)
    if not items:
        raise MergeError("No model extractions to merge")

    merged: Dict[str, Any] = {field: None for field in METADATA_FIELDS}
    pages = set()
    transaction_pages = set()
    rows: Dict[Tuple[Any, Any], Dict[str, Any]] = {}
    notes: List[Dict[str, Any]] = []

    for extraction in items:
        for field in METADATA_FIELDS:
            value = extraction.get(field)
            current = merged[field]
            if value is None:
                continue
            if current is None:
                merged[field] = value
            elif current != value:
                raise MergeError(f"Conflicting chunk metadata: {field}")

        processed = extraction.get("processed_pages", [])
        declared_transaction_pages = extraction.get("transaction_pages", [])
        if not isinstance(processed, list) or not isinstance(declared_transaction_pages, list):
            raise MergeError("Chunk page coverage is invalid")
        pages.update(processed)
        transaction_pages.update(declared_transaction_pages)

        chunk_rows = extraction.get("transactions", [])
        if not isinstance(chunk_rows, list):
            raise MergeError("Chunk transactions is not an array")
        for raw_row in chunk_rows:
            if not isinstance(raw_row, Mapping):
                raise MergeError("Chunk contains a non-object transaction")
            location = _row_location(raw_row)
            if location[0] is None or location[1] is None:
                raise MergeError("Transaction lacks a physical source location")
            row = deepcopy(dict(raw_row))
            previous = rows.get(location)
            if previous is None:
                rows[location] = row
            elif previous != row:
                raise MergeError(f"Conflicting copies of source row {location}")
            # An exact duplicate from an intentionally overlapping page is removed.

        raw_notes = extraction.get("extraction_notes", [])
        if isinstance(raw_notes, list):
            for note in raw_notes:
                if isinstance(note, Mapping) and dict(note) not in notes:
                    notes.append(deepcopy(dict(note)))

    merged["processed_pages"] = sorted(pages)
    merged["transaction_pages"] = sorted(transaction_pages)
    merged["transactions"] = sorted(
        rows.values(), key=lambda row: (row.get("source_page", 0), row.get("source_row_ordinal", 0))
    )
    merged["extraction_notes"] = notes
    return merged
