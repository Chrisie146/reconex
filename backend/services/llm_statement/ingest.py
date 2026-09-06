"""PDF text-layer assessment and geometry-preserving page representation."""

from dataclasses import dataclass, field
from io import BytesIO
import re
from typing import Dict, List, Sequence

import pdfplumber


DATE_ROW_PATTERN = re.compile(
    r"^\s*(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{2,4})?|\d{1,2}\s+[A-Za-z]{3,9})\b"
)


class PDFIngestError(ValueError):
    def __init__(self, status: str, message: str) -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class PageLine:
    top: float
    text: str
    word_spans: Sequence[str]
    x0: float = 0.0
    x1: float = 0.0
    bottom: float = 0.0


@dataclass(frozen=True)
class ExtractedPage:
    number: int
    width: float
    height: float
    quality: str
    lines: Sequence[PageLine]
    character_count: int
    candidate_transaction_rows: int

    def render(self) -> str:
        header = f"<page number={self.number} width={self.width:.1f} height={self.height:.1f}>"
        body = [f"y={line.top:.1f} | {' '.join(line.word_spans)}" for line in self.lines]
        return "\n".join([header] + body + ["</page>"])


@dataclass(frozen=True)
class PDFAssessment:
    status: str
    pages: Sequence[ExtractedPage] = field(default_factory=list)
    message: str = ""

    @property
    def expected_pages(self) -> List[int]:
        return [page.number for page in self.pages]

    @property
    def candidate_rows_by_page(self) -> Dict[int, int]:
        return {page.number: page.candidate_transaction_rows for page in self.pages}


def _group_words(words: Sequence[dict], tolerance: float = 3.0) -> List[PageLine]:
    groups: List[List[dict]] = []
    for word in sorted(words, key=lambda item: (float(item.get("top", 0)), float(item.get("x0", 0)))):
        top = float(word.get("top", 0))
        if not groups or abs(top - float(groups[-1][0].get("top", 0))) > tolerance:
            groups.append([word])
        else:
            groups[-1].append(word)

    lines: List[PageLine] = []
    for group in groups:
        ordered = sorted(group, key=lambda item: float(item.get("x0", 0)))
        text = " ".join(str(item.get("text", "")).strip() for item in ordered).strip()
        if not text:
            continue
        spans = tuple(f"x={float(item.get('x0', 0)):.1f}:{str(item.get('text', '')).strip()}" for item in ordered)
        lines.append(PageLine(
            top=float(ordered[0].get("top", 0)),
            text=text,
            word_spans=spans,
            x0=min(float(item.get("x0", 0)) for item in ordered),
            x1=max(float(item.get("x1", item.get("x0", 0))) for item in ordered),
            bottom=max(float(item.get("bottom", item.get("top", 0))) for item in ordered),
        ))
    return lines


def _quality(text: str, minimum_characters: int) -> str:
    if not text.strip():
        return "no_text"
    if len(text) < minimum_characters:
        return "low_quality_text"
    printable = sum(character.isprintable() or character in "\n\t" for character in text) / max(1, len(text))
    useful = sum(character.isalnum() or character.isspace() for character in text) / max(1, len(text))
    if printable < 0.90 or useful < 0.55 or text.count("�") > 0:
        return "low_quality_text"
    return "usable_text"


def assess_pdf(
    content: bytes,
    max_pages: int = 100,
    max_characters: int = 2_000_000,
    minimum_characters_per_page: int = 20,
) -> PDFAssessment:
    """Extract every page or fail closed when any text layer is unusable."""
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if len(pdf.pages) == 0:
                raise PDFIngestError("invalid_document", "PDF has no pages")
            if len(pdf.pages) > max_pages:
                raise PDFIngestError("invalid_document", f"PDF exceeds the {max_pages}-page limit")
            pages: List[ExtractedPage] = []
            total_characters = 0
            for number, raw_page in enumerate(pdf.pages, start=1):
                words = raw_page.extract_words(keep_blank_chars=False, use_text_flow=True) or []
                lines = _group_words(words)
                text = "\n".join(line.text for line in lines)
                total_characters += len(text)
                if total_characters > max_characters:
                    raise PDFIngestError("invalid_document", "Extracted text exceeds the configured limit")
                quality = _quality(text, minimum_characters_per_page)
                # A standalone date (for example a branch stamp) is not a
                # transaction candidate. Keep dated rows with any other content
                # so the coverage check remains conservative.
                candidates = sum(
                    1 for line in lines
                    if (match := DATE_ROW_PATTERN.search(line.text))
                    and line.text[match.end():].strip()
                )
                pages.append(ExtractedPage(
                    number=number,
                    width=float(raw_page.width),
                    height=float(raw_page.height),
                    quality=quality,
                    lines=lines,
                    character_count=len(text),
                    candidate_transaction_rows=candidates,
                ))
    except PDFIngestError:
        raise
    except Exception as exc:
        raise PDFIngestError("invalid_document", "PDF is encrypted, corrupt, or unreadable") from exc

    unusable = [page.number for page in pages if page.quality != "usable_text"]
    if unusable:
        return PDFAssessment("requires_ocr", pages, f"Pages without a usable text layer: {unusable}")
    return PDFAssessment("usable_text", pages, "All pages have a usable text layer")
