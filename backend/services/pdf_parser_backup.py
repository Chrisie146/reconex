import io
import re
from typing import List, Tuple, Optional

import pandas as pd

from .parser import ParserError
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multilingual

# Try to import pdfplumber lazily; if missing, we raise a ParserError at runtime instead
try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except Exception:
    pdfplumber = None
    _HAS_PDFPLUMBER = False

# More flexible date patterns (handles OCR spacing issues)
# Matches: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD MMM, DD MMM YYYY, etc.
DATE_REGEX = r"(\d{1,2}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{2,4}|\d{4}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{1,2}|\d{1,2}\s+[A-Za-z]{3,}(?:\s+\d{4})?)"
# More flexible amount regex to handle:
# - Leading currency symbols: $123.45, R123.45
# - Trailing credit/debit: 123.45Cr, 123.45Dr, 123.45C, 123.45D
# - Parentheses for negatives: (123.45)
# - Various thousand separators: 1,234.45 or 1 234.45 or 1.234,45
# BUT: REQUIRE proper decimal format (X.YY) to avoid matching random numbers
AMOUNT_REGEX = r"\(?[+\-]?\s*[A-Za-z$€£R]?\s*\d{1,3}(?:[.,\s]\d{3})*[.,]\d{2}\s*[CcDdRr]{0,3}\)?"

MAX_REASONABLE_AMOUNT = 200000.0


def _clean_amount_text(s: str) -> str:
    # normalize common thousand separators and parentheses
    t = s.strip()
    return t


def _normalize_amount(amount_text: str) -> Optional[str]:
    """Normalize OCR amount text to plain signed decimal string.

    Examples:
      '13,499.80C' -> '13499.80'
      '(293.92' -> '-293.92'
      '1 234,56' -> '1234.56'
    Returns None if no valid numeric amount found.
    """
    if not amount_text:
        return None
    t = amount_text.strip()
    # Remove trailing credit/debit markers
    t = re.sub(r'[CcRrDd]+\s*$', '', t)
    # Remove stray non-numeric leading characters except sign and decimal/group separators
    t = re.sub(r'^[^0-9\+\-\(]+', '', t)
    # Handle parentheses as negative
    is_negative = False
    if t.startswith('(') and t.endswith(')'):
        is_negative = True
        t = t[1:-1]
    # Normalize thousand separators: replace spaces and non-decimal commas when appropriate
    # If comma is used as decimal (e.g., '1 234,56'), convert to dot
    if re.search(r'\d+[\s\.\,]\d{3}[\s\.\,]\d{3}', t):
        # multiple group separators: remove spaces/dots/commas then fix decimal
        t = re.sub(r'[\s\.]', '', t)
    # If comma appears and the last comma is followed by exactly 2 digits, treat comma as decimal
    if ',' in t and re.search(r',\d{2}$', t):
        t = t.replace('.', '')
        t = t.replace(',', '.')
    else:
        # remove group commas/spaces
        t = t.replace(',', '')
    t = t.replace(' ', '')

    # Remove any trailing non-digit junk
    m = re.search(r'([+\-]?\d+\.?\d*)', t)
    if not m:
        return None
    num = m.group(1)
    if is_negative and not num.startswith('-'):
        num = '-' + num
    return num


def _clean_description(desc: str) -> str:
    """Clean OCR'd description text: remove repeated artifacts and trailing balances."""
    if not desc:
        return desc
    s = desc.strip()
    # Remove common OCR separators and control characters
    s = re.sub(r'[\|_\[\]\*]+', ' ', s)
    s = re.sub(r'\s{2,}', ' ', s)
    # Remove any amount-like tokens (often balances) anywhere in the description
    s = re.sub(AMOUNT_REGEX, '', s).strip(' ,;')
    # Remove date-like tokens inside description (often duplicated)
    s = re.sub(DATE_REGEX, '', s).strip()
    # Collapse stray punctuation and multiple commas/spaces
    s = re.sub(r'[\.,]{2,}', '.', s)
    s = re.sub(r'\s{2,}', ' ', s)
    # Collapse repeated punctuation
    s = re.sub(r'[\.,]{2,}', '.', s)
    return s


def _is_valid_row(desc: str, amount: Optional[str]) -> bool:
    if not desc or not desc.strip():
        return False
    if not amount:
        return False
    # discard rows that are just punctuation or commas
    if re.fullmatch(r'[\,\.-]+', desc.strip()):
        return False
    return True


def _rows_to_csv(rows: List[List[str]]) -> bytes:
    """Convert rows to CSV bytes"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "description", "amount"])
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


# BACKUP of the original file created before clearing Capitec parsing.
# File originally contained many Capitec-specific parsing functions and heuristics.
# This backup is written so we can restore or inspect the prior logic if needed.
