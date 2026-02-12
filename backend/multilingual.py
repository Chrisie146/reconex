from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple


# Multilingual column header mapping (extendable)
COLUMN_MAP: Dict[str, List[str]] = {
    "date": ["postingdate", "posting date", "posting_date", "date", "datum", "value date", "value_date"],
    "description": [
        "description",
        "beskrywing",
        "besonderhede",
        "verwysing",
        "transaction details",
        "details",
    ],
    "debit": ["debit", "debiet", "onttrekking", "withdrawal", "money out", "money_out"],
    "credit": ["credit", "krediet", "deposito", "deposit", "money in", "money_in"],
    "amount": ["amount", "bedrag", "amptelike bedrag"],
    "balance": ["balance", "balans", "saldo"],
    "fee": ["fee", "fees", "fooi", "heffing"],
}


# Multilingual category keywords. Keep categories deterministic by using an
# ordered dict-like structure (here a plain dict preserves insertion order
# in modern Python). Add both English and Afrikaans variants.
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Fuel": ["engen", "shell", "bp", "brandstof"],
    "Bank Fees": ["fee", "fees", "fooi", "heffing"],
    "Rent": ["rent", "huur"],
    "Salary": ["salary", "salaris", "loon"],
    "Groceries": ["spar", "checkers", "pick n pay", "pick 'n pay", "kruideniersware", "pick n pay"],
}


class ColumnDetectionError(Exception):
    """Raised when column mapping fails or is ambiguous.

    Messages are user-facing and should be calm and actionable.
    """


def _normalize_header(h: str) -> str:
    if h is None:
        return ""
    return h.strip().lower()


def normalize_headers(headers: List[str]) -> Dict[str, int]:
    """Map incoming headers to canonical column keys.

    Returns mapping canonical_name -> column_index.

    Raises ColumnDetectionError with a clear message if required columns
    are missing or if ambiguous matches are found.
    """
    if not headers:
        raise ColumnDetectionError("No headers provided for detection.")

    norm_headers = [_normalize_header(h) for h in headers]

    # Build alias -> canonical map
    alias_map: Dict[str, str] = {}
    for canonical, aliases in COLUMN_MAP.items():
        for a in aliases:
            alias_map[a.lower()] = canonical

    result: Dict[str, int] = {}
    collisions: List[Tuple[str, int]] = []

    for idx, nh in enumerate(norm_headers):
        if not nh:
            continue
        if nh in alias_map:
            canonical = alias_map[nh]
            if canonical in result:
                # Two input headers resolved to same canonical -> ambiguous
                collisions.append((canonical, idx))
            else:
                result[canonical] = idx

    if collisions:
        names = ", ".join(f"{c} (col {i})" for c, i in collisions)
        raise ColumnDetectionError(
            f"Ambiguous column mapping detected for: {names}. Please use Guided Import."
        )

    # Validate we have essential columns: date + description + (amount | debit+credit)
    missing = []
    if "date" not in result:
        missing.append("date")
    if "description" not in result:
        missing.append("description")

    has_amount = "amount" in result
    has_debit_credit = "debit" in result and "credit" in result

    if not (has_amount or has_debit_credit):
        missing.append("amount or debit+credit")

    if missing:
        raise ColumnDetectionError(
            "We couldn\'t identify the transaction columns. Please use Guided Import. Missing: "
            + ", ".join(missing)
        )

    return result


def _word_match(keyword: str, text: str, strict_boundaries: bool = True) -> bool:
    """Match keyword in text with optional strict word boundaries.
    
    Args:
        keyword: The keyword to search for
        text: The text to search in
        strict_boundaries: If True, keyword must be a separate word (default).
                          If False, keyword can be part of a compound word (CamelCase).
    
    Examples:
        - strict_boundaries=True: 'vat' matches 'VAT Payment' but not 'NaVATFeb'
        - strict_boundaries=False: 'vat' matches 'VAT Payment' and 'NaVATFeb'
    """
    kw = keyword.strip()
    if not kw:
        return False
    
    if strict_boundaries:
        # Strict: keyword must be a separate word (original behavior)
        # \w includes alphanumeric and underscore
        pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None
    else:
        # Loose: keyword can be part of a compound word (CamelCase)
        # Match when:
        # 1. Keyword is at word boundary OR preceded by lowercase (compound word start), OR
        # 2. Keyword is followed by capital letter (case transition) OR non-alphanumeric OR end of string
        # This catches patterns like: NaVATFeb, RenteOpDTBal, SARSOnline
        pattern = r"(?:(?<!\w)|(?<=[a-z]))" + re.escape(kw) + r"(?=(?:[A-Z]|\W|$))"
        return re.search(pattern, text, flags=re.IGNORECASE) is not None


def match_keyword_in_text(keyword: str, text: str, strict_boundaries: bool = True) -> bool:
    """Public wrapper for keyword-in-text matching.

    - Deterministic, case-insensitive.
    - Can use strict word boundaries (default) or allow compound word matching.
    - Intended for use by other services (bulk matching, filters).
    
    Args:
        keyword: The keyword to search for
        text: The text to search in
        strict_boundaries: If True (default), keyword must be separate word.
                          If False, keyword can be part of compound word.
    """
    if not text or not keyword:
        return False
    return _word_match(keyword, text, strict_boundaries=strict_boundaries)


def categorize_transaction(description: Optional[str], override: Optional[str] = None) -> str:
    """Categorise a transaction description using keyword dictionaries.

    Rules:
    - Case-insensitive
    - Match against `description` only
    - First strong match wins (order of CATEGORY_KEYWORDS)
    - Manual override allowed
    """
    if override:
        return override
    if not description:
        return "Uncategorized"
    text = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if _word_match(kw, text):
                return category

    return "Uncategorized"


def parse_number(s: Optional[str]) -> Optional[Decimal]:
    """Parse a numeric string to Decimal using locale-safe heuristics.

    Heuristics used (non-exhaustive but deterministic):
    - Remove currency symbols and spaces
    - If both '.' and ',' present, assume the rightmost separator is the decimal
      separator and remove thousand separators accordingly.
    - If only ',' present and the final group length is 1-2, treat ',' as decimal
      separator, otherwise as thousands separator.
    - Ensure only one decimal point before constructing Decimal.
    """
    if s is None:
        return None
    raw = s.strip()
    if raw == "":
        return None

    # Keep minus sign
    raw = raw.replace('\xa0', '')
    raw = raw.replace(' ', '')
    # remove currency signs and letters
    raw = re.sub(r"[^0-9,\.-]", "", raw)
    if raw == "":
        return None

    try:
        if ',' in raw and '.' in raw:
            # use rightmost separator as decimal
            if raw.rfind(',') > raw.rfind('.'):
                raw = raw.replace('.', '')
                raw = raw.replace(',', '.')
            else:
                raw = raw.replace(',', '')
        elif ',' in raw:
            parts = raw.split(',')
            if len(parts[-1]) in (1, 2):
                raw = raw.replace(',', '.')
            else:
                raw = raw.replace(',', '')
        # collapse multiple dots: keep last as decimal
        if raw.count('.') > 1:
            last = raw.rfind('.')
            raw = raw[:last].replace('.', '') + raw[last:]

        return Decimal(raw)
    except InvalidOperation:
        raise ValueError(f"Unable to parse numeric amount: {s}")


def handle_ocr_text(text: Optional[str]) -> str:
    """Normalize OCR-extracted text for categorisation.

    This function does not translate text; it simply normalizes whitespace
    and control characters so keyword matching behaves predictably.
    """
    if text is None:
        return ""
    t = text.strip()
    t = re.sub(r"\s+", " ", t)
    return t


def process_guided_ocr(extracted: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """Process field-extracted values from guided OCR.

    - Trust positional extraction for field mapping
    - Parse numeric values using locale-safe parser
    - Apply keyword categorisation on `description`
    """
    out: Dict[str, Optional[str]] = {}
    # pass through date as-is (parsing left to caller)
    out['date'] = extracted.get('date')
    desc = handle_ocr_text(extracted.get('description') or extracted.get('details') or '')
    out['description'] = desc
    amt_raw = extracted.get('amount') or extracted.get('value') or extracted.get('debit') or extracted.get('credit')
    try:
        amt = parse_number(amt_raw) if amt_raw is not None else None
    except ValueError:
        amt = None
    out['amount'] = str(amt) if amt is not None else None
    out['category'] = categorize_transaction(desc)
    return out


def soft_language_detection(text: str) -> Dict[str, object]:
    """Lightweight language hint by counting language-specific keywords.

    This is only for UI hints and metadata; core logic must not branch on it.
    """
    if not text:
        return {"language": "unknown", "counts": {"en": 0, "af": 0}}

    text = text.lower()
    # lightweight hint keywords
    en = ["date", "description", "fee", "rent", "salary", "deposit", "withdrawal"]
    af = ["datum", "beskrywing", "fooi", "huur", "salaris", "deposito", "onttrekking"]

    en_count = sum(1 for kw in en if _word_match(kw, text))
    af_count = sum(1 for kw in af if _word_match(kw, text))

    detected = "unknown"
    if en_count > af_count:
        detected = "en"
    elif af_count > en_count:
        detected = "af"

    return {"language": detected, "counts": {"en": en_count, "af": af_count}}
