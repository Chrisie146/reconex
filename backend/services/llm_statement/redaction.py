"""Conservative redaction of identity fields before model egress."""

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Sequence, Tuple

from .ingest import DATE_ROW_PATTERN, ExtractedPage, PageLine


EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
# Separators are deliberately limited to one character. An unrestricted
# whitespace match can bridge visually separate PDF columns and consume an
# amount or balance together with an identifier.
LONG_NUMBER = re.compile(r"(?<![\d.])(\d(?:[\s-]?\d){7,})(?![\d.]|\.\d{2})")
PHONE = re.compile(r"(?<!\d)(?:\+27|0)[\s-]?\d{2}(?:[\s-]?\d){7}(?!\d)")
IDENTITY_LABEL = re.compile(r"\b(?:account\s*holder|customer\s*name|client\s*name|name)\s*[:\-]", re.I)
ADDRESS_LABEL = re.compile(r"\b(?:physical|postal|residential|business)?\s*address\s*[:\-]", re.I)
ADDRESS_LINE = re.compile(r"\b(?:p\.?\s*o\.?\s*box|street|st\.?|road|rd\.?|avenue|ave\.?|boulevard|drive|lane)\b", re.I)
HEADER_METADATA = re.compile(
    r"\b(?:bank|statement|account|branch|period|date|page|balance|currency|vat|swift|code|number)\b",
    re.I,
)


@dataclass(frozen=True)
class RedactionResult:
    safe: bool
    pages: Sequence[str]
    redaction_count: int
    findings: Sequence[str]
    redaction_map: Dict[str, str]


def _redact_number(match: re.Match, mapping: Dict[str, str], counter: List[int], context: str) -> str:
    original = match.group(0)
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", original.strip()):
        return original
    digits = re.sub(r"\D", "", original)
    if len(digits) < 8:
        return original
    if "account" in context.lower() and len(digits) >= 8:
        replacement = f"<ACCOUNT_LAST4:{digits[-4:]}>"
    else:
        counter[0] += 1
        replacement = f"<NUMBER_REDACTED_{counter[0]}>"
    mapping[replacement] = original
    return replacement


def _redact_line(text: str, mapping: Dict[str, str], counter: List[int]) -> Tuple[str, int]:
    count_before = len(mapping)

    def replace_email(match: re.Match) -> str:
        counter[0] += 1
        token = f"<EMAIL_REDACTED_{counter[0]}>"
        mapping[token] = match.group(0)
        return token

    def replace_phone(match: re.Match) -> str:
        counter[0] += 1
        token = f"<PHONE_REDACTED_{counter[0]}>"
        mapping[token] = match.group(0)
        return token

    result = EMAIL.sub(replace_email, text)
    result = PHONE.sub(replace_phone, result)
    result = LONG_NUMBER.sub(lambda match: _redact_number(match, mapping, counter, text), result)

    label = IDENTITY_LABEL.search(result)
    if label and result[label.end():].strip():
        counter[0] += 1
        token = f"<NAME_REDACTED_{counter[0]}>"
        original = result[label.end():].strip()
        mapping[token] = original
        result = result[:label.end()] + " " + token

    address = ADDRESS_LABEL.search(result)
    if address and result[address.end():].strip():
        counter[0] += 1
        token = f"<ADDRESS_REDACTED_{counter[0]}>"
        original = result[address.end():].strip()
        mapping[token] = original
        result = result[:address.end()] + " " + token
    elif ADDRESS_LINE.search(result) and not DATE_ROW_PATTERN.search(result):
        counter[0] += 1
        token = f"<ADDRESS_REDACTED_{counter[0]}>"
        mapping[token] = result
        result = token

    return result, len(mapping) - count_before


def _positioned_line(line: PageLine, page_width: float, output_columns: int = 140) -> str:
    """Render words at approximate x positions so table columns survive egress."""
    positioned = []
    for span in line.word_spans:
        match = re.fullmatch(r"x=(-?\d+(?:\.\d+)?):(.*)", span)
        if match and match.group(2):
            positioned.append((float(match.group(1)), match.group(2)))
    if not positioned:
        return line.text

    rendered = ""
    width = max(page_width, 1.0)
    for x, word in sorted(positioned):
        column = max(0, round((x / width) * output_columns))
        rendered += " " * max(1, column - len(rendered)) + word
    return rendered.rstrip()


def _likely_unlabelled_identity(line: PageLine, page: ExtractedPage) -> bool:
    """Conservatively identify a name/company line in the page-one header."""
    if page.number != 1 or line.top > page.height * 0.35:
        return False
    text = line.text.strip()
    if DATE_ROW_PATTERN.search(text) or HEADER_METADATA.search(text) or any(character.isdigit() for character in text):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'&.-]*", text)
    if not 2 <= len(words) <= 8:
        return False
    title_or_upper = sum(word.isupper() or word[:1].isupper() for word in words)
    return title_or_upper == len(words)


def redact_pages(pages: Iterable[ExtractedPage]) -> RedactionResult:
    mapping: Dict[str, str] = {}
    counter = [0]
    rendered: List[str] = []
    findings: List[str] = []

    for page in pages:
        output = [f"<page number={page.number} width={page.width:.1f} height={page.height:.1f}>"]
        for line_number, line in enumerate(page.lines, start=1):
            if _likely_unlabelled_identity(line, page):
                counter[0] += 1
                token = f"<HEADER_IDENTITY_REDACTED_{counter[0]}>"
                mapping[token] = line.text
                redacted = token
            else:
                redacted, _count = _redact_line(_positioned_line(line, page.width), mapping, counter)
            output.append(
                f"line={line_number} bbox={line.x0:.1f},{line.top:.1f},{line.x1:.1f},{line.bottom:.1f} | {redacted}"
            )
        output.append("</page>")
        page_text = "\n".join(output)
        possible_long_number = any(
            len(re.sub(r"\D", "", match.group(0))) >= 8
            and not re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", match.group(0).strip())
            for match in LONG_NUMBER.finditer(page_text)
        )
        if EMAIL.search(page_text) or PHONE.search(page_text) or possible_long_number:
            findings.append(f"page_{page.number}_contains_possible_identifier")
        rendered.append(page_text)

    return RedactionResult(
        safe=not findings,
        pages=rendered,
        redaction_count=len(mapping),
        findings=tuple(findings),
        redaction_map=mapping,
    )
