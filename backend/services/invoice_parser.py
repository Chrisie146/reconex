from typing import Dict, Any, Optional, List
from io import BytesIO
import re
from datetime import date

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except Exception:
    pdfplumber = None
    _HAS_PDFPLUMBER = False

from services.parser import parse_date


def _extract_text(content: bytes) -> (List[str], str):
    """Return tuple (lines, method) where method is 'pdfplumber' or 'ocr' or 'none'."""
    lines: List[str] = []
    method = 'none'

    # Try text-based extraction first (pdfplumber)
    if _HAS_PDFPLUMBER and pdfplumber is not None:
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    page_lines = [ln.strip() for ln in t.splitlines() if ln and ln.strip()]
                    lines.extend(page_lines)
            if lines:
                method = 'pdfplumber'
        except Exception:
            lines = []

    # If pdfplumber produced no text, fall back to OCR using pytesseract/pdf2image
    if not lines:
        try:
            try:
                from pdf2image import convert_from_bytes
                import pytesseract
            except Exception:
                return ([], 'none')

            images = convert_from_bytes(content, dpi=300)
            for img in images:
                try:
                    t = pytesseract.image_to_string(img)
                    page_lines = [ln.strip() for ln in t.splitlines() if ln and ln.strip()]
                    lines.extend(page_lines)
                except Exception:
                    continue
            if lines:
                method = 'ocr'
        except Exception:
            return ([], 'none')

    return (lines, method)


def _find_total_amount(lines: List[str]) -> Optional[float]:
    # Accept dot or comma as decimal separator, and commas/spaces as thousand separators
    amount_regex = re.compile(r"(?:R|£|\$)?\s*([0-9]{1,3}(?:[ ,][0-9]{3})*(?:[\.,][0-9]{2})|[0-9]+[\.,][0-9]{2}|[0-9]+)")
    candidates: List[float] = []
    # Prefer lines containing total terms
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in ["total", "amount due", "total due", "balance due"]):
            m = amount_regex.findall(ln)
            if m:
                try:
                    tok = m[-1].replace(" ", "")
                    tok = tok.replace(',', '.')
                    val = float(tok)
                    candidates.append(val)
                except Exception:
                    pass
    # If none found, take the largest amount in whole doc as a fallback
    if not candidates:
        for ln in lines:
            for m in amount_regex.findall(ln):
                try:
                    tok = m.replace(" ", "").replace(',', '.')
                    val = float(tok)
                    candidates.append(val)
                except Exception:
                    pass
    if not candidates:
        return None
    # Use max as heuristic for total
    return max(candidates) if candidates else None


def _find_vat_amount(lines: List[str]) -> Optional[float]:
    amount_regex = re.compile(r"(?:R|£|\$)?\s*([0-9]{1,3}(?:[ ,][0-9]{3})*(?:[\.,][0-9]{2})|[0-9]+[\.,][0-9]{2}|[0-9]+)")
    for ln in lines:
        low = ln.lower()
        if any(k in low for k in ["vat", "tax"]):
            # skip lines that are VAT identifiers rather than amounts
            if re.search(r"vat\s*(number|no\.|no)\b", low):
                continue
            m = amount_regex.findall(ln)
            if m:
                try:
                    tok = m[-1].replace(" ", "").replace(',', '.')
                    val = float(tok)
                    # if it's implausibly large (e.g., VAT number), skip
                    if val > 1_000_000:
                        continue
                    return val
                except Exception:
                    continue
    return None


def _find_invoice_number(lines: List[str]) -> Optional[str]:
    # Prefer lines that explicitly contain 'invoice' and then extract a numeric token
    for ln in lines:
        if re.search(r"invoice\s*(no\.|number|#)?", ln, re.I) or re.search(r"inv\b", ln, re.I):
            # find sequences of digits (likely invoice id)
            nums = re.findall(r"(\d{4,})", ln)
            if nums:
                return nums[-1]
            # fallback: capture alphanumeric after colon
            m = re.search(r"[:\-]\s*([A-Za-z0-9\-/]+)$", ln.strip())
            if m:
                return m.group(1)

    # generic fallback: any standalone long alphanumeric token in doc
    for ln in lines:
        m = re.search(r"\b([A-Za-z0-9\-_/]{6,})\b", ln)
        if m:
            return m.group(1)
    return None


def _find_invoice_date(lines: List[str]) -> Optional[date]:
    # Search for explicit date labels first
    for ln in lines:
        if "date" in ln.lower():
            # extract any date token from line
            d = _extract_first_date_from_line(ln)
            if d:
                return d
    # fallback: scan all lines for any date-like token
    for ln in lines:
        d = _extract_first_date_from_line(ln)
        if d:
            return d
    return None


def _extract_first_date_from_line(ln: str) -> Optional[date]:
    # common date formats
    candidates = []
    # dd/mm/yyyy or dd-mm-yyyy
    for m in re.findall(r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4})\b", ln):
        candidates.append(m)
    # yyyy-mm-dd
    for m in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", ln):
        candidates.append(m)
    # dd Month yyyy
    for m in re.findall(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", ln):
        candidates.append(m)
    for tok in candidates:
        d = parse_date(tok)
        if d:
            return d
    return None


def _find_supplier_name(lines: List[str]) -> Optional[str]:
    # Improved heuristics:
    # 1. Prefer lines containing common company suffixes
    company_suffixes = [r"\b(Ltd|Pty|LLC|Inc|Co|Corporation|Limited)\b", r"\bPTY\b", r"\bLTD\b"]
    for ln in lines[:20]:
        for suf in company_suffixes:
            if re.search(suf, ln, re.I):
                return re.sub(r"\s+", " ", ln).strip()

    # 2. Look for 'From:' label and take following tokens or same-line company name
    for i, ln in enumerate(lines):
        if re.search(r"^from[:\s]", ln, re.I) or re.search(r"\bfrom:\b", ln, re.I):
            # try same line after 'From:'
            m = re.split(r"from[:\s]+", ln, flags=re.I)
            if len(m) > 1 and m[1].strip():
                cand = m[1].strip()
                if len(cand) >= 3:
                    return cand
            # else next non-empty line
            for j in range(i + 1, min(i + 6, len(lines))):
                if lines[j].strip():
                    return re.sub(r"\s+", " ", lines[j]).strip()

    # 3. Fallback: first non-generic non-empty line that isn't 'tax invoice' or similar
    for ln in lines:
        if not ln or not ln.strip():
            continue
        if re.search(r"^\s*(tax\s+invoice|invoice|invoice:)\b", ln, re.I):
            continue
        clean = re.sub(r"\s+", " ", ln).strip()
        if len(clean) >= 3:
            return clean

    return lines[0].strip() if lines else None


def extract_invoice_metadata(content: bytes) -> Dict[str, Any]:
    """Extract invoice metadata from a PDF. Returns dict fields where detected.
    Fields: supplier_name, invoice_date, invoice_number, total_amount, vat_amount
    """
    _res = _extract_text(content)
    if isinstance(_res, tuple):
        lines, method = _res
    else:
        lines = _res
        method = 'unknown'
    out: Dict[str, Any] = {}
    out['_extraction_method'] = method
    if not lines:
        return out
    sup = _find_supplier_name(lines)
    if sup:
        out["supplier_name"] = sup
    dt = _find_invoice_date(lines)
    if dt:
        out["invoice_date"] = dt
    invno = _find_invoice_number(lines)
    if invno:
        out["invoice_number"] = invno
    tot = _find_total_amount(lines)
    if tot is not None:
        out["total_amount"] = tot
    vat = _find_vat_amount(lines)
    if vat is not None:
        out["vat_amount"] = vat
    return out
