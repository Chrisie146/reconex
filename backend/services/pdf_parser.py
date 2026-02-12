import io
import re
import csv
from typing import List, Tuple, Optional

from .parser import ParserError
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multilingual

# We'll use OCR for Capitec statements. OCR helpers live in `.ocr`.
try:
    from .ocr import ocr_pdf_bytes
except Exception:
    ocr_pdf_bytes = None

# For single-page OCR, we need pdf2image
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None

# Date pattern for matching dates in OCR text
# Matches: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, DD MMM, DD MMM YYYY, etc.
DATE_REGEX = r"(\d{1,2}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{2,4}|\d{4}\s*[\/\-]\s*\d{1,2}\s*[\/\-]\s*\d{1,2}|\d{1,2}\s+[A-Za-z]{3,}(?:\s+\d{4})?)"

# Amount pattern for matching currency amounts
# Matches: $123.45, R123.45, (123.45), 123.45Cr, 1,234.45, etc.
AMOUNT_REGEX = r"\(?[+\-]?\s*[A-Za-z$€£R]?\s*\d{1,3}(?:[.,\s]\d{3})*[.,]\d{2}\s*[CcDdRr]{0,3}\)?"


def _rows_to_csv(rows: List[List[str]]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Determine if rows have balance column (4 columns vs 3)
    has_balance = rows and len(rows[0]) == 4
    
    # Debug: print to verify logic
    if has_balance:
        print(f"[DEBUG] CSV has balance column - writing 4-column header")
        writer.writerow(["date", "description", "amount", "balance"])
    else:
        print(f"[DEBUG] CSV has no balance column - writing 3-column header")
        writer.writerow(["date", "description", "amount"])
    
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _parse_amount_sa_simple(s: str) -> Optional[float]:
    if not s:
        return None
    t = s.strip()
    # handle parentheses as negative
    neg = False
    if t.startswith('(') and t.endswith(')'):
        neg = True
        t = t[1:-1]
    # remove currency symbols and spaces
    t = re.sub(r'[A-Za-z$€£R\s]', '', t)
    # normalize comma decimal
    if t.count(',') == 1 and t.count('.') == 0:
        t = t.replace(',', '.')
    else:
        t = t.replace(',', '')
    try:
        v = float(t)
        return -v if neg else v
    except Exception:
        return None


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
    clean = m.group(1)
    if is_negative:
        if not clean.startswith('-'):
            clean = '-' + clean
    return clean


def _extract_statement_year(text: str) -> Optional[int]:
    """Extract statement year from PDF text (e.g., from 'Statement Period : 13 November 2025 to 13 December 2025')"""
    # Look for year in statement date/period lines
    year_patterns = [
        r'Statement\s+Period[:\s]+.*?(\d{4})',
        r'Statement\s+Date[:\s]+.*?(\d{4})',
        r'(\d{4})[/-]\d{1,2}[/-]\d{1,2}',  # Date in YYYY-MM-DD or YYYY/MM/DD format
    ]
    
    for pattern in year_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                year = int(match.group(1))
                if 2000 <= year <= 2100:  # Sanity check
                    return year
            except (ValueError, IndexError):
                continue
    
    return None


def _parse_amount_sa(s: str) -> float:
    """Parse South African formatted amount (spaces as thousands sep, comma as decimal)"""
    if not s or s.strip() == "":
        return 0.0
    try:
        # Remove leading/trailing whitespace
        s = s.strip()
        # Replace space with nothing (thousands separator), comma with dot (decimal)
        s = s.replace(' ', '').replace(',', '.')
        return float(s)
    except:
        return 0.0


def _parse_capitec_row(row: List, col_indices: dict) -> Optional[List[str]]:
    """Parse a single row from a Capitec transaction table.
    
    Args:
        row: Single row from a table
        col_indices: Dict with column indices for date, desc, money_in, money_out, fee
    
    Returns:
        [date, description, amount] or None if invalid
    """
    if not row or len(row) < 7:
        return None
    
    # Extract date
    date_val = str(row[col_indices['date']]).strip() if col_indices['date'] < len(row) else ""
    if not date_val or not re.search(DATE_REGEX, date_val):
        return None
    
    # Extract description
    desc_val = str(row[col_indices['desc']]).strip() if col_indices['desc'] < len(row) else ""
    
    # Skip balance rows or other non-transaction rows
    # Balance rows typically have names like "Nedabf/mfc -R", "Balance", etc.
    if desc_val and re.search(r'^[A-Z][a-z]*/[a-z]+ -[RC]$|^Balance|^Opening|^Closing', desc_val):
        return None
    
    # Extract category (optional)
    category = str(row[col_indices.get('category', 2)]).strip() if col_indices.get('category', 2) < len(row) else ""
    
    # Append category to description if present
    if category and category not in desc_val:
        desc_val = f"{desc_val} {category}".strip()
    
    # Extract Money In and Money Out (combined as main transaction)
    money_in_str = str(row[col_indices['money_in']]).strip() if col_indices['money_in'] < len(row) and row[col_indices['money_in']] else ""
    money_out_str = str(row[col_indices['money_out']]).strip() if col_indices['money_out'] < len(row) and row[col_indices['money_out']] else ""
    fee_str = str(row[col_indices.get('fee')]).strip() if col_indices.get('fee') and col_indices['fee'] < len(row) and row[col_indices['fee']] else ""
    
    # Parse amounts
    money_in_amt = _parse_amount_sa(money_in_str)  # Positive value
    money_out_amt = _parse_amount_sa(money_out_str)  # Already negative in PDF
    fee_amt = _parse_amount_sa(fee_str)  # Already negative in PDF
    
    # Main transaction is Money In + Money Out (don't include fee yet)
    transaction_amount = money_in_amt + money_out_amt
    
    # Only add if there's a real transaction (Money In or Money Out is non-zero)
    if money_in_amt == 0.0 and money_out_amt == 0.0:
        return None
    
    # Format as amount string
    amount_val = f"{transaction_amount:.2f}"
    
    return [date_val, desc_val, amount_val]


def _parse_capitec_single_row_table(table: List[List], col_indices: dict = None) -> Optional[List[str]]:
    """Parse a single-row (or mostly single-row) Capitec transaction table.
    
    Capitec PDF format stores each transaction as a separate table.
    Usually 1 row, but sometimes has 2+ rows where extra rows are footers.
    
    Args:
        table: Table from pdfplumber (1 or more rows)
        col_indices: Optional dict with keys 'date', 'desc', 'money_in', 'money_out', 'fee', 'balance'
                     mapping to column indices. If None, uses default positions.
    
    Returns:
        List of rows: main transaction + separate fee row if applicable
    """
    if not table or len(table) == 0:
        return []
    
    # Use provided column indices or defaults
    if col_indices is None:
        col_indices = {
            'date': 0,
            'desc': 1,
            'category': 2,
            'money_in': 3,
            'money_out': 5,
            'fee': 7,
            'balance': 8,
        }
    
    # Parse the transaction row
    row_data = table[0]

    # Extract basic info
    date_val = str(row_data[col_indices['date']]).strip() if col_indices['date'] < len(row_data) else ""
    if not date_val or not re.search(DATE_REGEX, date_val):
        return []

    desc_val = str(row_data[col_indices['desc']]).strip() if col_indices['desc'] < len(row_data) else ""

    # Skip balance rows
    if desc_val and re.search(r'^[A-Z][a-z]*/[a-z]+ -[RC]$|^Balance|^Opening|^Closing', desc_val):
        return []

    # Extract category
    category = str(row_data[col_indices.get('category', 2)]).strip() if col_indices.get('category', 2) < len(row_data) else ""
    if category and category not in desc_val:
        desc_val = f"{desc_val} {category}".strip()

    # Extract amounts
    money_in_str = str(row_data[col_indices['money_in']]).strip() if col_indices['money_in'] < len(row_data) and row_data[col_indices['money_in']] else ""
    money_out_str = str(row_data[col_indices['money_out']]).strip() if col_indices['money_out'] < len(row_data) and row_data[col_indices['money_out']] else ""
    fee_str = str(row_data[col_indices.get('fee')]).strip() if col_indices.get('fee') and col_indices['fee'] < len(row_data) and row_data[col_indices['fee']] else ""

    # Parse amounts
    money_in_amt = _parse_amount_sa(money_in_str)
    money_out_amt = _parse_amount_sa(money_out_str)
    fee_amt = _parse_amount_sa(fee_str)

    # Build rows: Money In as income, Money Out as expense, Fee as separate expense
    rows_result = []

    # Money In (income)
    if money_in_amt and abs(money_in_amt) > 0.0001:
        rows_result.append([date_val, desc_val, f"{money_in_amt:.2f}"])

    # Money Out (expense) - keep sign as parsed (likely negative)
    if money_out_amt and abs(money_out_amt) > 0.0001:
        rows_result.append([date_val, desc_val, f"{money_out_amt:.2f}"])

    # Fee (expense) - append as separate row with (Fee) marker
    if fee_amt and abs(fee_amt) > 0.0001:
        rows_result.append([date_val, f"{desc_val} (Fee)", f"{fee_amt:.2f}"])

    return rows_result


def _parse_capitec_text(pdf, col_indices: dict = None) -> List[List[str]]:
    """Parse Capitec transactions from text when table extraction is incomplete.
    
    Only processes lines that match the Capitec transaction pattern:
    DATE DESCRIPTION... CATEGORY MONEY_IN MONEY_OUT FEE BALANCE
    
    Example: 19/12/2025 Banking App Transfer to Credit Card: Transfer Transfer -300.00 3 495.76
    """
    rows = []
    
    if not pdf or not hasattr(pdf, 'pages'):
        return rows
    
    for page in pdf.pages:
        try:
            text = page.extract_text()
        except:
            continue
        
        if not text:
            continue
        
        # Process line by line, looking for Capitec transaction patterns
        for line in text.split('\n'):
            line = line.strip()
            if not line or len(line) < 20:
                continue
            
            # Skip header and footer lines
            if any(skip in line for skip in ['Capitec Bank', 'Statement', 'balance', 'Includes VAT', 'Client Care', 'authorized', 'registered', 'FSP', 'Reg. No', 'Date', 'Description', '24hr', 'E-mail', 'Website', 'Limited', 'Opening', 'Closing', 'Balance']):
                continue
            
            # Match Capitec transaction line pattern:
            # Must start with DD/MM/YYYY date
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.{20,})', line)
            if not date_match:
                continue
            
            date_str = date_match.group(1)
            rest = date_match.group(2)
            
            # Find all amount-like values (must have . or , followed by 2 digits for decimal)
            # Negative amounts should have - or parentheses
            amount_pattern = r'-?\s*\d{1,3}(?:[\s,]\d{3})*[.,]\d{2}'
            amounts = re.findall(amount_pattern, rest)
            
            if len(amounts) < 1:
                continue
            
            # Parse the amounts found
            parsed_amounts = []
            for amt_str in amounts:
                try:
                    clean = amt_str.replace(' ', '').replace(',', '.')
                    parsed_amounts.append(float(clean))
                except:
                    pass
            
            if not parsed_amounts:
                continue
            
            # Remove all amount strings from rest to get description (once, before the loop)
            desc_part = rest
            for amt_str in amounts:
                desc_part = desc_part.replace(amt_str, '', 1)
            
            desc_part = desc_part.strip()
            if not desc_part or len(desc_part) < 5:
                continue
            
            # Skip balance rows or similar non-transaction rows
            if re.search(r'^[A-Z][a-z]*/[a-z]+ -[RC]$|^Balance|^Opening|^Closing', desc_part):
                continue
            
            # For Capitec: Create separate rows for each amount (except Balance which is last)
            # The last amount is Balance (to be ignored)
            num_amounts = len(parsed_amounts)
            
            # Add one row for each amount (except the last which is balance)
            for idx, amount in enumerate(parsed_amounts[:-1]):
                # Don't add (Payment)/(Fee) tags - the table parser handles that
                rows.append([date_str, desc_part, f"{amount:.2f}"])
    
    return rows


def _parse_capitec_table(table: List[List]) -> List[List[str]]:
    """Parse Capitec Bank statement table format.
    
    Capitec uses a table with columns:
    Date | Description | Category | Money In | Money Out | Fee | Balance
    
    The key difference from other banks:
    - Has separate "Money In" and "Money Out" columns instead of a single Amount column
    - Balance is the running balance (NOT the transaction amount)
    - Amount should be: Money In (positive) if populated, else Money Out (negative if populated)
    
    Returns a list of [date, description, amount] rows.
    """
    if len(table) < 2:
        return []
    
    rows = []
    
    # Try to detect Capitec structure from headers
    header = table[0]
    header_strs = [str(h).strip().lower() if h else "" for h in header]
    
    # Check if this looks like a Capitec table
    # Must have Date, Money In/Out columns (or At least description + amounts)
    has_date = any('date' in h for h in header_strs)
    has_money_in = any('money' in h and 'in' in h for h in header_strs)
    has_money_out = any('money' in h and 'out' in h for h in header_strs)
    has_amount = any('amount' in h for h in header_strs)
    
    # Capitec-specific pattern: Date, Description, and separate Money In/Out
    is_capitec_format = has_date and (has_money_in or has_money_out)
    
    if not is_capitec_format:
        return []  # Not a Capitec table
    
    # Find column indices
    date_idx = None
    desc_idx = None
    money_in_idx = None
    money_out_idx = None
    fee_idx = None
    balance_idx = None
    
    for i, h in enumerate(header_strs):
        if 'date' in h:
            date_idx = i
        elif 'description' in h or 'narrative' in h:
            desc_idx = i
        elif 'money' in h and 'in' in h:
            money_in_idx = i
        elif 'money' in h and 'out' in h:
            money_out_idx = i
        elif 'fee' in h:
            fee_idx = i
        elif 'balance' in h:
            balance_idx = i
    
    # If no Money In/Out columns found by header, try column positions
    # Typical Capitec: Date(0), Description(1), Category(2), Money In(3), Money Out(4), Fee(5), Balance(6)
    if money_in_idx is None and len(header) >= 4:
        money_in_idx = 3
    if money_out_idx is None and len(header) >= 5:
        money_out_idx = 4
    
    if date_idx is None:
        date_idx = 0
    if desc_idx is None and len(header) >= 2:
        desc_idx = 1
    
    # Parse data rows (skip header at row 0)
    for row in table[1:]:
        if not row or len(row) < 2:
            continue
        
        # Extract date
        date_val = str(row[date_idx]).strip() if date_idx < len(row) and row[date_idx] else ""
        if not date_val or not re.search(DATE_REGEX, date_val):
            continue
        
        # Extract description
        desc_val = str(row[desc_idx]).strip() if desc_idx < len(row) and row[desc_idx] else ""
        if not desc_val:
            desc_val = ""
        # Normalize whitespace (remove newlines, collapse multiple spaces)
        desc_val = re.sub(r'[\n\r\t]+', ' ', desc_val)
        desc_val = re.sub(r'\s+', ' ', desc_val).strip()
        
        # Extract Money In and Money Out
        money_in = str(row[money_in_idx]).strip() if money_in_idx < len(row) and row[money_in_idx] else ""
        money_out = str(row[money_out_idx]).strip() if money_out_idx < len(row) and row[money_out_idx] else ""
        fee = str(row[fee_idx]).strip() if fee_idx < len(row) and row[fee_idx] else ""
        
        # Determine amount: use Money In if present (positive), else Money Out (negative)
        amount_val = None
        if money_in and money_in.strip() and money_in != "":
            # This is income (positive)
            amount_val = money_in
        elif money_out and money_out.strip() and money_out != "":
            # This is expense (negative) - prepend minus sign if not already there
            mo = money_out.strip()
            if mo.startswith('-'):
                amount_val = mo
            else:
                amount_val = '-' + mo
        
        # Only add if we have an amount
        if amount_val:
            rows.append([date_val, desc_val, amount_val])
        
        # Handle Fee column: if present and not empty, add as separate negative transaction
        if fee and fee.strip() and fee != "" and fee != "0" and fee != "0.00":
            try:
                fee_float = float(fee.replace(',', '').strip())
                if fee_float > 0:  # Fees are positive in the column, but should be negative transactions
                    fee_desc = desc_val + " (Fee)" if desc_val else "Fee"
                    rows.append([date_val, fee_desc, f"-{fee_float:.2f}"])
            except ValueError:
                pass  # Skip if not a valid number
    
    return rows


def _parse_fnb_table(table: List[List], statement_year: Optional[int] = None, statement_end_year: Optional[int] = None) -> List[List[str]]:
    """Parse FNB bank statement table format.
    
    FNB uses a unique format where:
    - Row 0: Header with columns like Date, Description, Amount, Balance (in English or Afrikaans)
    - Row 1: Contains ALL amounts and balances in merged cells (newline-separated)
    - Rows 2+: Individual transaction dates and descriptions
    
    Args:
        table: The table to parse
        statement_year: Starting year of statement (e.g., 2025 for "Dec 2025 to Jan 2026")
        statement_end_year: Optional ending year if statement spans years
    
    Returns a list of [date, description, amount] rows.
    """
    if len(table) < 3:
        return []
    
    header = table[0]
    # Use multilingual module to detect header columns
    try:
        header_strs = [str(h).strip() if h else "" for h in header]
        column_map = multilingual.normalize_headers(header_strs)
        # Successfully mapped headers! Extract columns
        date_idx = column_map.get("date")
        desc_idx = column_map.get("description")
        amount_idx = column_map.get("amount")
    except Exception:
        # Fallback to multilingual keyword detection (English + Afrikaans)
        date_idx = None
        desc_idx = None
        amount_idx = None
        # Try simple multilingual column detection
        for i, h in enumerate(header):
            h_str = str(h).lower() if h else ""
            if 'date' in h_str or 'datum' in h_str:
                date_idx = i
            elif 'description' in h_str or 'beskrywing' in h_str or 'desc' in h_str:
                desc_idx = i
            elif 'amount' in h_str or 'bedrag' in h_str:
                amount_idx = i
        
        # If columns not found, return empty
        if date_idx is None or desc_idx is None or amount_idx is None:
            return []
    
    # Row 1 typically contains merged amounts/balances
    merged_row = table[1] if len(table) > 1 else None
    
    # Find the amounts column
    amounts_list = []
    if merged_row and len(merged_row) > amount_idx and merged_row[amount_idx]:
        amounts_text = str(merged_row[amount_idx])
        if '\n' in amounts_text:
            # Split by newline and clean
            amounts_list = [amt.strip() for amt in amounts_text.split('\n') if amt.strip()]
    
    # Extract date/description rows (starting from row 2)
    # Keep them as-is - blank descriptions indicate non-text elements (images, icons, etc.)
    date_desc_rows = []
    for row in table[2:]:
        if not row or len(row) < 2:
            continue
        date_val = str(row[0]).strip() if row[0] else ""
        desc_val = str(row[1]).strip() if row[1] else ""
        date_desc_rows.append([date_val, desc_val])
    
    # Match dates/descriptions with amounts
    result_rows = []
    months_list = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    last_month_num = 0
    year_has_transitioned = False
    
    for idx, (date_val, desc_val) in enumerate(date_desc_rows):
        if idx < len(amounts_list):
            amount_val = amounts_list[idx]
            
            # Add year to date if statement spans multiple years
            date_with_year = date_val
            if statement_year and statement_end_year and statement_end_year > statement_year:
                # Extract month from date_val
                month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_val, re.IGNORECASE)
                if month_match:
                    month_str = month_match.group(1).lower()
                    month_num = months_list.index(month_str) + 1
                    
                    transaction_year = statement_year
                    if year_has_transitioned:
                        transaction_year = statement_end_year
                    elif last_month_num > 0 and month_num < last_month_num:
                        year_has_transitioned = True
                        transaction_year = statement_end_year
                    elif last_month_num == 0 and month_num == 1:
                        year_has_transitioned = True
                        transaction_year = statement_end_year
                    
                    last_month_num = month_num
                    date_with_year = f"{date_val} {transaction_year}"
            elif statement_year:
                # No year boundary, just add the year
                date_with_year = f"{date_val} {statement_year}"
            
            result_rows.append([date_with_year, desc_val, amount_val])
    
    return result_rows


def _split_transactions_from_block(date: str, text: str) -> List[List[str]]:
    """Split a combined OCR text block into multiple (date, description, amount) rows

    Strategy:
    - Find all amount matches in the block using AMOUNT_REGEX
    - For each amount match, take the text between the previous amount end (or start)
      and the current amount start as the description for that amount.
    - Trim common OCR artifacts from descriptions.
    """
    rows: List[List[str]] = []
    try:
        amount_matches = list(re.finditer(AMOUNT_REGEX, text))
        if not amount_matches:
            return []

        # Precompute normalized numeric values for heuristics
        norm_values = []
        raw_texts = []
        spans = []
        for m in amount_matches:
            raw = m.group(0).strip()
            spans.append(m.span())
            raw_texts.append(raw)
            nv = _normalize_amount(raw)
            try:
                nv_f = float(nv) if nv is not None else None
            except Exception:
                nv_f = None
            norm_values.append(nv_f)

        rows = []
        prev_end = 0
        i = 0
        while i < len(amount_matches):
            start, end = spans[i]
            amount_text = raw_texts[i]
            amount_val = norm_values[i]

            paired = False
            # If a following amount exists, decide whether it's a balance (pair) or a separate txn
            if i + 1 < len(amount_matches):
                start2, end2 = spans[i + 1]
                raw2 = raw_texts[i + 1]
                val2 = norm_values[i + 1]

                # Heuristic: if raw2 ends with credit marker or val2 is noticeably larger than val1,
                # treat (amount, raw2) as (transaction amount, running balance) pair.
                has_credit_marker = bool(re.search(r'[CcRr]$', raw2))
                numeric_jump = False
                if amount_val is not None and val2 is not None:
                    try:
                        if val2 > amount_val * 1.5 or val2 - amount_val > 500:
                            numeric_jump = True
                    except Exception:
                        numeric_jump = False

                # Also consider proximity: if two amounts are close together in text, pairing is likely
                proximity = (start2 - end) < 40

                if has_credit_marker or numeric_jump or proximity:
                    # description is text from prev_end to start (before first amount)
                    desc_seg = text[prev_end:start].strip()
                    desc_seg = re.sub(r'[\|_\[\]\*]+', ' ', desc_seg)
                    desc_seg = re.sub(r'\s{2,}', ' ', desc_seg).strip(' ,;')
                    if not desc_seg:
                        left = text[max(0, start - 80):start].strip()
                        desc_seg = re.sub(r'\s{2,}', ' ', left).strip(' ,;')

                    # Choose transaction amount vs balance: prefer smaller as txn, or first if credit marker on second
                    txn_raw = amount_text
                    if val2 is not None and amount_val is not None:
                        if has_credit_marker or val2 > amount_val:
                            txn_raw = amount_text
                        elif amount_val > val2 * 1.2:
                            txn_raw = raw2  # second looks like txn, first could be balance mis-read

                    rows.append([date, desc_seg, txn_raw])
                    prev_end = end2
                    i += 2
                    paired = True

            if not paired:
                # Single amount -> description between prev_end and start
                desc_seg = text[prev_end:start].strip()
                desc_seg = re.sub(r'[\|_\[\]\*]+', ' ', desc_seg)
                desc_seg = re.sub(r'\s{2,}', ' ', desc_seg).strip(' ,;')
                if not desc_seg:
                    left = text[max(0, start - 80):start].strip()
                    desc_seg = re.sub(r'\s{2,}', ' ', left).strip(' ,;')

                rows.append([date, desc_seg, amount_text])
                prev_end = end
                i += 1

        return rows
    except Exception:
        return []


def _rows_to_csv(rows: List[List[str]]) -> bytes:
    """Convert rows to CSV bytes"""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Determine if rows have balance column (4 columns vs 3)
    has_balance = rows and len(rows[0]) == 4
    
    if has_balance:
        writer.writerow(["date", "description", "amount", "balance"])
    else:
        writer.writerow(["date", "description", "amount"])
    
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')


def _parse_fnb_ocr_text(text: str, statement_year: Optional[int] = None, statement_end_year: Optional[int] = None) -> List[List[str]]:
    """
    Parse FNB bank statement text from OCR with robust handling of artifacts.
    
    FNB OCR Format (each line):
    [Date] |[Description] [Amount] [Balance]Cr[ optional bank charges]
    
    Example:
    02 Jan |POS Purchase S2S*Dandv 412752°6823 31 Dec 90.00 13,645.20Cr|
    03 Jan |Payshap Credit C Mcpherson 230.00Cr| 12,578.94Cr|
    05 Jan |Payment To Investment Transfer 6,000.00 3,158.69Cr
    
    Handles OCR artifacts from lower-quality scans:
    - Date corruption: '120 Oct' -> '20 Oct', '1 Nov' -> correct
    - Month typos: '0ct' (zero) -> 'Oct' (letter O)
    - Currency corruption: 'Gr' -> 'Cr', 'Gr;' -> 'Cr'
    - Garbage symbols: trailing '[', ']', '}', ')' removed
    - Special char corruption in descriptions
    
    Strategy:
    1. Pre-process OCR text to fix common artifacts
    2. Match lines starting with date pattern (DD Mon or |DD Mon)
    3. Extract description after the pipe |
    4. Extract amounts with robustness to corruption
    5. Extract balance information for validation
    6. Use balance-based validation to determine correct sign
    
    Args:
        text: OCR text to parse
        statement_year: Starting year of statement (e.g., 2025 for "Dec 2025 to Jan 2026")
        statement_end_year: Optional ending year if statement spans years (e.g., 2026 for "Dec 2025 to Jan 2026")
    
    Returns:
    List of rows: [date, description, amount, balance]
    """
    rows = []
    
    # Try to extract statement year from text if not provided
    if statement_year is None:
        year_match = re.search(r'\b(20[0-2][0-9])\b', text)
        if year_match:
            statement_year = int(year_match.group(1))
        else:
            # Default to current year
            from datetime import datetime
            statement_year = datetime.now().year
    
    # Pre-process OCR text to fix common artifacts
    # 1. Fix currency corruption: 'Gr' or 'Gr;' or 'Gr}' etc. -> 'Cr'
    text = re.sub(r'\bGr(?=[\];|}]|\s|$)', 'Cr', text)
    
    # 2. Fix month typos: '0ct' (zero O), '0ct' -> 'Oct'
    text = re.sub(r'\b0ct\b', 'Oct', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ec\b', 'Dec', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ov\b', 'Nov', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0an\b', 'Jan', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ar\b', 'Mar', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0pr\b', 'Apr', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ay\b', 'May', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0un\b', 'Jun', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ul\b', 'Jul', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ug\b', 'Aug', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ep\b', 'Sep', text, flags=re.IGNORECASE)
    
    # Pattern to match date at start of line: optional chars, then DD Mon, optionally followed by |
    # Allow common OCR misreads (O, l, I) in the day digits and normalize later
    date_pattern = re.compile(r'^[\(\[\]\|]*([0-9OlI]{1,2}\s+[A-Za-z]{3})\s+\|?(.+)$')
    
    # Pattern to extract amounts from the line
    # FNB format: amounts with commas/spaces as thousands separators
    # Must have decimal point with 2 digits
    # Pattern: 1-3 digits, optionally followed by comma/space + 3 digits (repeated), then .XX
    # Make sure we don't match long account numbers by being strict about format
    # Use word boundary at start but not at end to allow "1,000.00Cr|"
    amount_pattern = re.compile(r'\b(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})')
    
    # Track the previous month to detect year boundary crossings
    months_list = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
    last_month_num = 0
    year_has_transitioned = False  # Track if we've already crossed from Dec to Jan
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Skip header lines and metadata
        skip_keywords = [
            'description', 'balance', 'amount', 'page ', 'branch number', 'account number',
            'vat registration', 'turnover', 'transactions in'
        ]
        if any(keyword in line.lower() for keyword in skip_keywords):
            continue
        
        # Strip trailing garbage symbols that OCR adds
        line = re.sub(r'[\[\]\}\)\|]+$', '', line).rstrip()
        
        # Try to match transaction line
        match = date_pattern.match(line)
        if match:
            # Normalize common OCR misreads in the day portion (O -> 0, l/I -> 1)
            # Only normalize the day part, not the month part
            date_str_raw = match.group(1).strip()
            
            # Split into day and month, normalize ONLY the day part
            date_parts = date_str_raw.split()
            if len(date_parts) >= 2:
                day_part = date_parts[0]
                month_part = ' '.join(date_parts[1:])
                # Normalize day: O -> 0, l/I -> 1
                day_normalized = re.sub(r'[OlIi]', lambda m: '0' if m.group(0).upper() == 'O' else '1', day_part)
                date_str = f"{day_normalized} {month_part}"
            else:
                date_str = date_str_raw
            
            rest = match.group(2).strip()
        else:
            # Fallback: sometimes OCR places the date irregularly (e.g., 'lO7 Jan')
            # Try to find a day+month anywhere in the line and use remainder as description
            alt = re.search(r'([0-9OlI]{1,2})\s+([A-Za-z]{3})', line)
            if not alt:
                continue
            date_str_raw = f"{alt.group(1)} {alt.group(2)}"
            
            # Normalize only the day part (not the month part)
            day_part = alt.group(1)
            month_part = alt.group(2)
            day_normalized = re.sub(r'[OlIi]', lambda m: '0' if m.group(0).upper() == 'O' else '1', day_part)
            date_str = f"{day_normalized} {month_part}"
            
            # Try to use text after the matched date as the rest, or fallback to whole line
            rest = line[alt.end():].lstrip(' |') or line
        
        # Fix potential leading digits in day: '120 Oct' -> '20 Oct', '44 Oct' -> '4 Oct', etc.
        # Try removing leading digits one at a time until we get a valid day (1-31)
        day_match = re.match(r'^([0-9]+)\s+([A-Za-z]{3})', date_str)
        if day_match:
            day_str = day_match.group(1)
            month_str = day_match.group(2)
            try:
                day_int = int(day_str)
                # If day is > 31, try removing leading digit(s) iteratively
                while day_int > 31 and len(day_str) > 1:
                    day_str = day_str[1:]  # Remove leading digit
                    day_int = int(day_str)
                
                # Validate the final day is in range 1-31
                if 1 <= day_int <= 31:
                    date_str = f"{day_str} {month_str}"
            except:
                pass
        
        # Sometimes OCR splits the balance decimal (e.g. '12,548 94' instead of '12,548.94').
        # Normalize a pattern of 'thousands [space] 2digits' into 'thousands.2digits'
        rest = re.sub(r"(\d{1,3}(?:[,\s]\d{3})+)\s+(\d{2})(?=\b)", r"\1.\2", rest)

        # Remove amounts that are embedded in descriptions (e.g., "Fee-209.00" where 209.00 is not the transaction amount)
        # These are amounts preceded by a hyphen with no space
        rest_cleaned = re.sub(r'-(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})', '-XXXXX', rest)

        # Find all amounts in the cleaned line
        amounts = amount_pattern.findall(rest_cleaned)
        if not amounts:
            continue
        
        # Parse the amounts
        parsed_amounts = []
        for amt_str in amounts:
            clean = amt_str.replace(' ', '').replace(',', '')
            try:
                parsed_amounts.append(float(clean))
            except:
                pass
        
        if not parsed_amounts:
            continue
        
        # The FIRST amount is the transaction amount
        # The SECOND amount (if present) is the balance
        transaction_amount = parsed_amounts[0]
        balance_amount = parsed_amounts[1] if len(parsed_amounts) > 1 else None
        
        # Determine if this is income (credit) or expense (debit)
        # In FNB OCR format, credits have 'Cr' marker after amounts, debits have no marker
        # Check the ORIGINAL line for 'Cr' pattern after the transaction amount
        is_credit = False
        
        # Look for 'Cr' marker after the first amount in the original line
        # Pattern: amount followed by 'Cr' with optional punctuation
        amount_str_in_line = amounts[0] if amounts else None
        if amount_str_in_line:
            # Find position of amount in rest string
            amount_pos = rest.find(amount_str_in_line)
            if amount_pos >= 0:
                # Check text after amount for 'Cr' marker (within next 5 characters)
                text_after_amount = rest[amount_pos + len(amount_str_in_line):amount_pos + len(amount_str_in_line) + 5]
                if 'Cr' in text_after_amount or 'C' in text_after_amount:
                    is_credit = True
        
        # Also check for explicit credit keywords in description
        credit_keywords = ['transfer from', 'payshap credit', 'credit c ', 'debit order krediet', 'winnings']
        if any(keyword in rest.lower() for keyword in credit_keywords):
            is_credit = True
        
        # Extract description by removing ALL amounts and balance markers
        # We need to remove all found amounts since we don't know which is which
        desc = rest
        for amt_str in amounts:
            desc = desc.replace(amt_str, '', 1)
        
        # Clean up description
        desc = desc.replace('Cr|', '').replace('Cr', '').replace('|', '').strip()
        # Remove trailing garbage symbols
        desc = re.sub(r'[\[\]\}\)\|]+$', '', desc).rstrip()
        # Normalize whitespace
        desc = re.sub(r'\s{2,}', ' ', desc)
        desc = desc.strip(' ,-')
        
        if not desc or len(desc) < 3:
            continue
        
        # Format amount with FNB suffix: 'C' for credits (income), no suffix for debits (expenses)
        # This allows the downstream parser to correctly interpret the sign
        if is_credit:
            amount_str = f"{transaction_amount:.2f}C"  # Credit suffix for income
        else:
            amount_str = f"{transaction_amount:.2f}"  # No suffix for expenses (will be made negative by parser)
        
        # Format balance (always positive, append 'Cr' marker to distinguish from transaction amounts)
        balance_str = f"{balance_amount:.2f}Cr" if balance_amount else ""
        
        # Determine correct year for this transaction
        # If statement spans multiple years (e.g., Dec 2025 to Jan 2026), use year boundary logic
        transaction_year = statement_year
        
        if statement_end_year and statement_end_year > statement_year:
            # Extract month from date_str to determine if we should use end year
            month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_str, re.IGNORECASE)
            if month_match:
                month_str = month_match.group(1).lower()
                month_num = months_list.index(month_str) + 1
                
                # Track year transitions: if we go from Dec (12) to Jan (1), we've crossed a year boundary
                # Once we've transitioned to the next year, stay there for all early months
                if year_has_transitioned:
                    # Already transitioned, use end year for months before the start of the period
                    transaction_year = statement_end_year
                elif last_month_num > 0 and month_num < last_month_num:
                    # Month went backwards (e.g., from Dec 12 to Jan 1), mark as transitioned
                    year_has_transitioned = True
                    transaction_year = statement_end_year
                elif last_month_num == 0 and month_num == 1:
                    # First month is January and statement starts in Dec, mark as transitioned
                    year_has_transitioned = True
                    transaction_year = statement_end_year
                
                last_month_num = month_num
        
        # Append year to date_str for proper parsing
        date_with_year = f"{date_str} {transaction_year}"
        
        # Add transaction row with balance information
        rows.append([date_with_year, desc, amount_str, balance_str])
    
    return rows
    # Pre-process OCR text to fix common artifacts
    # 1. Fix currency corruption: 'Gr' or 'Gr;' or 'Gr}' etc. -> 'Cr'
    text = re.sub(r'\bGr(?=[\];|}]|\s|$)', 'Cr', text)
    
    # 2. Fix month typos: '0ct' (zero O), '0ct' -> 'Oct'
    text = re.sub(r'\b0ct\b', 'Oct', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ec\b', 'Dec', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ov\b', 'Nov', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0an\b', 'Jan', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ar\b', 'Mar', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0pr\b', 'Apr', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ay\b', 'May', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0un\b', 'Jun', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ul\b', 'Jul', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ug\b', 'Aug', text, flags=re.IGNORECASE)
    text = re.sub(r'\b0ep\b', 'Sep', text, flags=re.IGNORECASE)
    
    # Pattern to match date at start of line: optional chars, then DD Mon, optionally followed by |
    # Allow common OCR misreads (O, l, I) in the day digits and normalize later
    date_pattern = re.compile(r'^[\(\[\]\|]*([0-9OlI]{1,2}\s+[A-Za-z]{3})\s+\|?(.+)$')
    
    # Pattern to extract amounts from the line
    # FNB format: amounts with commas/spaces as thousands separators
    # Must have decimal point with 2 digits
    # Pattern: 1-3 digits, optionally followed by comma/space + 3 digits (repeated), then .XX
    # Make sure we don't match long account numbers by being strict about format
    # Use word boundary at start but not at end to allow "1,000.00Cr|"
    amount_pattern = re.compile(r'\b(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})')
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Skip header lines and metadata
        skip_keywords = [
            'description', 'balance', 'amount', 'page ', 'branch number', 'account number',
            'vat registration', 'turnover', 'transactions in'
        ]
        if any(keyword in line.lower() for keyword in skip_keywords):
            continue
        
        # Strip trailing garbage symbols that OCR adds
        line = re.sub(r'[\[\]\}\)\|]+$', '', line).rstrip()
        
        # Try to match transaction line
        match = date_pattern.match(line)
        if match:
            # Normalize common OCR misreads in the day portion (O -> 0, l/I -> 1)
            # Only normalize the day part, not the month part
            date_str_raw = match.group(1).strip()
            
            # Split into day and month, normalize ONLY the day part
            date_parts = date_str_raw.split()
            if len(date_parts) >= 2:
                day_part = date_parts[0]
                month_part = ' '.join(date_parts[1:])
                # Normalize day: O -> 0, l/I -> 1
                day_normalized = re.sub(r'[OlIi]', lambda m: '0' if m.group(0).upper() == 'O' else '1', day_part)
                date_str = f"{day_normalized} {month_part}"
            else:
                date_str = date_str_raw
            
            rest = match.group(2).strip()
        else:
            # Fallback: sometimes OCR places the date irregularly (e.g., 'lO7 Jan')
            # Try to find a day+month anywhere in the line and use remainder as description
            alt = re.search(r'([0-9OlI]{1,2})\s+([A-Za-z]{3})', line)
            if not alt:
                continue
            date_str_raw = f"{alt.group(1)} {alt.group(2)}"
            
            # Normalize only the day part (not the month part)
            day_part = alt.group(1)
            month_part = alt.group(2)
            day_normalized = re.sub(r'[OlIi]', lambda m: '0' if m.group(0).upper() == 'O' else '1', day_part)
            date_str = f"{day_normalized} {month_part}"
            
            # Try to use text after the matched date as the rest, or fallback to whole line
            rest = line[alt.end():].lstrip(' |') or line
        
        # Fix potential leading digits in day: '120 Oct' -> '20 Oct', '44 Oct' -> '4 Oct', etc.
        # Try removing leading digits one at a time until we get a valid day (1-31)
        day_match = re.match(r'^([0-9]+)\s+([A-Za-z]{3})', date_str)
        if day_match:
            day_str = day_match.group(1)
            month_str = day_match.group(2)
            try:
                day_int = int(day_str)
                # If day is > 31, try removing leading digit(s) iteratively
                while day_int > 31 and len(day_str) > 1:
                    day_str = day_str[1:]  # Remove leading digit
                    day_int = int(day_str)
                
                # Validate the final day is in range 1-31
                if 1 <= day_int <= 31:
                    date_str = f"{day_str} {month_str}"
            except:
                pass
        
        # Sometimes OCR splits the balance decimal (e.g. '12,548 94' instead of '12,548.94').
        # Normalize a pattern of 'thousands [space] 2digits' into 'thousands.2digits'
        rest = re.sub(r"(\d{1,3}(?:[,\s]\d{3})+)\s+(\d{2})(?=\b)", r"\1.\2", rest)

        # Remove amounts that are embedded in descriptions (e.g., "Fee-209.00" where 209.00 is not the transaction amount)
        # These are amounts preceded by a hyphen with no space
        rest_cleaned = re.sub(r'-(\d{1,3}(?:[,\s]\d{3})+\.\d{2}|\d{1,3}\.\d{2})', '-XXXXX', rest)

        # Find all amounts in the cleaned line
        amounts = amount_pattern.findall(rest_cleaned)
        if not amounts:
            continue
        
        # Parse the amounts
        parsed_amounts = []
        for amt_str in amounts:
            clean = amt_str.replace(' ', '').replace(',', '')
            try:
                parsed_amounts.append(float(clean))
            except:
                pass
        
        if not parsed_amounts:
            continue
        
        # The FIRST amount is the transaction amount
        # The SECOND amount (if present) is the balance
        transaction_amount = parsed_amounts[0]
        balance_amount = parsed_amounts[1] if len(parsed_amounts) > 1 else None
        
        # Determine if this is income (credit) or expense (debit)
        # In FNB OCR format, credits have 'Cr' marker after amounts, debits have no marker
        # Check the ORIGINAL line for 'Cr' pattern after the transaction amount
        is_credit = False
        
        # Look for 'Cr' marker after the first amount in the original line
        # Pattern: amount followed by 'Cr' with optional punctuation
        amount_str_in_line = amounts[0] if amounts else None
        if amount_str_in_line:
            # Find position of amount in rest string
            amount_pos = rest.find(amount_str_in_line)
            if amount_pos >= 0:
                # Check text after amount for 'Cr' marker (within next 5 characters)
                text_after_amount = rest[amount_pos + len(amount_str_in_line):amount_pos + len(amount_str_in_line) + 5]
                if 'Cr' in text_after_amount or 'C' in text_after_amount:
                    is_credit = True
        
        # Also check for explicit credit keywords in description
        credit_keywords = ['transfer from', 'payshap credit', 'credit c ', 'debit order krediet', 'winnings']
        if any(keyword in rest.lower() for keyword in credit_keywords):
            is_credit = True
        
        # Extract description by removing ALL amounts and balance markers
        # We need to remove all found amounts since we don't know which is which
        desc = rest
        for amt_str in amounts:
            desc = desc.replace(amt_str, '', 1)
        
        # Clean up description
        desc = desc.replace('Cr|', '').replace('Cr', '').replace('|', '').strip()
        # Remove trailing garbage symbols
        desc = re.sub(r'[\[\]\}\)\|]+$', '', desc).rstrip()
        # Normalize whitespace
        desc = re.sub(r'\s{2,}', ' ', desc)
        desc = desc.strip(' ,-')
        
        if not desc or len(desc) < 3:
            continue
        
        # Format amount with FNB suffix: 'C' for credits (income), no suffix for debits (expenses)
        # This allows the downstream parser to correctly interpret the sign
        if is_credit:
            amount_str = f"{transaction_amount:.2f}C"  # Credit suffix for income
        else:
            amount_str = f"{transaction_amount:.2f}"  # No suffix for expenses (will be made negative by parser)
        
        # Format balance (always positive, append 'Cr' marker to distinguish from transaction amounts)
        balance_str = f"{balance_amount:.2f}Cr" if balance_amount else ""
        
        # Determine correct year for this transaction
        # If statement spans multiple years (e.g., Dec 2025 to Jan 2026), 
        # dates in later months should use the later year
        transaction_year = statement_year
        if statement_end_year and statement_end_year > statement_year:
            # Statement spans years
            # Extract month from date_str to determine if we should use end year
            month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', date_str, re.IGNORECASE)
            if month_match:
                month_str = month_match.group(1).lower()
                # Map month string to month number
                months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                month_num = months.index(month_str) + 1
                
                # If statement starts in a late month (like Dec) and ends in early month (like Jan),
                # then early months (Jan-Nov) should use the end year
                statement_start_month_match = re.search(r'^(\d{1,2})\s+([A-Za-z]{3})', date_str)
                if statement_start_month_match:
                    start_month_str = statement_start_month_match.group(2).lower()
                    start_month_num = months.index(start_month_str) + 1
                    
                    # If start month is later than end month (Dec to Jan case), 
                    # months <= start month use statement_year, others use end_year
                    # Actually simpler: if it's Jan-Nov and statement_start is Dec,
                    # and we're seeing Jan-Nov, use end_year
                    # But this requires getting the actual start month from Statement Period
                    
                    # Even simpler: just check if current month < start month
                    # If current month is earlier in year than start month, use end_year
                    if month_num > start_month_num:
                        # Month increased, still in same year
                        transaction_year = statement_year
                    else:
                        # Month decreased or same, but went backwards - use end year
                        transaction_year = statement_end_year
        
        # Append year to date_str for proper parsing
        date_with_year = f"{date_str} {transaction_year}"
        
        # Add transaction row with balance information
        rows.append([date_with_year, desc, amount_str, balance_str])
    
    return rows



def _parse_absa_text(text: str, pdf=None) -> List[List[str]]:
    """
    Parse ABSA bank statement text extracted from OCR from all pages.
    
    ABSA Format: OCR produces a table with columns:
    - Entry No (XXXXX format)
    - Date (YYMMDD format)
    - Description (variable length)
    - Amount (in separate "Amount" column)
    - Balance (in separate "Balance" column)
    
    Strategy:
    1. Extract all transaction lines (entry number + date + description)
    2. Extract all amounts in order from Amount column
    3. Match them by SEQUENTIAL ORDER, handling missing entry numbers
    4. Skip zero amounts only in output, not during matching
    """
    rows = []
    
    # Extract text from all pages
    all_text = text
    if pdf and hasattr(pdf, 'pages') and len(pdf.pages) > 1:
        # We have additional pages beyond the first
        for page in pdf.pages[1:]:
            try:
                page_text = page.extract_text()
                if page_text:
                    all_text += "\n" + page_text
            except Exception:
                pass
    
    # Step 1: Extract transaction lines with entry number and date
    lines = all_text.split('\n')
    entry_data = []  # List of (entry_num, date, description) tuples
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip clear header/footer lines
        skip_keywords = [
            "Entry", "No", "Date", "Description",
            "Start Date", "End Date",
            "Statement Enquiry", "Account", "Branch",
            "Balance", "Amount", "Site",
            "Page", "Reg no",
            "Regional", "Service Centre",
            "Wed,", "BIO CASE"
        ]
        
        # More specific patterns
        if any(kw in line for kw in skip_keywords):
            continue
        
        # Skip timestamp lines (e.g., "2025-07-02 at 08:42:33 AM")
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+at\s+\d{2}:\d{2}', line):
            continue
        
        # Must start with entry number (digits)
        if not line or not line[0].isdigit():
            continue
        
        # Extract entry number
        entry_match = re.match(r'^(\d{2,5})\s', line)
        if not entry_match:
            continue
        
        entry_num = int(entry_match.group(1))
        
        # Look for YYMMDD date pattern (6 digits)
        date_match = re.search(r'\b(\d{6})\b', line)
        if not date_match:
            continue
        
        date_str = date_match.group(1)
        
        # Extract description (from after date to end of line)
        date_end = date_match.end()
        desc = line[date_end:].strip()
        
        # Remove trailing reference codes and site indicators
        desc = re.sub(r'\s+(SETTLEMENT|CASHFOCUS|CF|RIVER|RIVERSDAL|BIO CASE)\s*$', '', desc).strip()
        desc = re.sub(r'\s+\d{4,}(?:\s|$)', ' ', desc).strip()
        
        if not desc:
            desc = "Transaction"
        
        # Convert YYMMDD to YYYYMMDD
        yy = int(date_str[:2])
        yyyy = 2000 + yy if yy < 50 else 1900 + yy
        yyyymmdd = f"{yyyy}{date_str[2:]}"
        
        entry_data.append((entry_num, yyyymmdd, desc))
    
    # Step 2: Extract all amounts from Amount column (in order)
    # Important: Handle multiple Amount sections (one per page/table)
    amounts = []
    
    search_pos = 0
    while True:
        amount_idx = all_text.find('Amount', search_pos)
        if amount_idx < 0:
            break
        
        balance_idx = all_text.find('Balance', amount_idx)
        if balance_idx < 0:
            balance_idx = len(all_text)
        
        amount_section = all_text[amount_idx:balance_idx]
        
        # Find all numeric amounts in this section (with optional space before decimal for OCR artifacts)
        amount_pattern = re.compile(r'-?\d+\s*\.\d{2}')
        for match in amount_pattern.finditer(amount_section):
            try:
                amount_text = match.group(0).replace(' ', '')
                amounts.append(float(amount_text))
            except ValueError:
                pass
        
        search_pos = balance_idx
    
    # Step 3: Match entries to amounts by SEQUENTIAL ORDER
    # Important: each entry gets matched with the corresponding amount in order
    # Even if entry numbers are missing/non-sequential, we match by position in the list
    for i, (entry_num, date_str, desc) in enumerate(entry_data):
        if i >= len(amounts):
            # No matching amount for this entry
            break
        
        amount = amounts[i]
        
        # Skip zero amounts (balance forward, etc.) - but don't skip the matching!
        if amount == 0:
            # Still matched (not skipped), just don't add to output
            continue
        
        # Fix sign based on description
        desc_upper = desc.upper()
        has_credit = 'CREDIT' in desc_upper
        has_debit = 'DEBIT' in desc_upper or 'PAYMENT' in desc_upper
        
        # If description says CREDIT but amount is negative, flip it
        if has_credit and amount < 0:
            amount = -amount
        # If description says DEBIT/PAYMENT but amount is positive, flip it
        elif has_debit and amount > 0:
            amount = -amount
        
        rows.append([date_str, desc, str(amount)])
    
    return rows


def _parse_standard_bank_business_text(text: str, pdf, statement_year: int = None) -> List[List[str]]:
    """
    Parse Standard Bank Business Account PDF text format
    
    Format: Details Service_Fee Credits Debits Date(MMDD) Balance
    Example: MAGTAPE CREDIT 9090  2,504.00  1201 1,605,084.91
    
    Date format is MMDD (4 digits like 1201 for Dec 1)
    Credits are positive (income), Debits are negative (expenses)
    """
    rows = []
    
    # If no year provided, try to extract from statement header
    if statement_year is None:
        # Look for "Statement from DD MMMM YYYY to DD MMMM YYYY"
        year_match = re.search(r'Statement from.*?(\d{4})', text, re.IGNORECASE)
        if year_match:
            statement_year = int(year_match.group(1))
        else:
            statement_year = 2025  # Default to current year
    
    lines = text.split('\n')
    current_date = None
    
    for i, line in enumerate(lines):
        line = line.strip()

        # Handle multi-line descriptions: if this line contains only text (no digits)
        # and the next line contains the MMDD date/amounts, merge them so they
        # parse as a single transaction row.
        if line and not re.search(r'\d', line):
            next_line = lines[i+1].strip() if i+1 < len(lines) else ''
            mmdd_regex = r'\b(0[1-9]|1[0-2])\d{2}\b'
            if next_line and re.search(mmdd_regex, next_line):
                # Merge current and next line and blank out next to avoid double parse
                merged = f"{line} {next_line}"
                line = merged
                lines[i+1] = ''
        
        # Skip headers, empty lines, and common non-transaction/summary lines
        line_upper = line.upper()
        skip_keywords = [
            "CURRENT ACCOUNT",
            "DETAILS SERVICE",
            "STANDARD BANK",
            "STATEMENT",
            "BALANCE BROUGHT FORWARD",
            "BALANCE CARRIED",
            "BALANCE BROUGHT",
            "THE HEADMASTER",
            "GET AHEAD",
            "PAGE ",
            "STNDRDBANK",
            "BASC"
        ]
        if not line or any(k in line_upper for k in skip_keywords):
            continue
        
        # Look for transaction lines: must have 4-digit MMDD date (allow optional space)
        # Pattern: description ... numbers ... MM DD or MMDD ... balance
        date_match = re.search(r'\s(0[1-9]|1[0-2])[ \t]?(\d{2})\s', line)
        if not date_match:
            # Fallback: OCR sometimes drops the date column. If line contains
            # amounts and a textual description, parse it and use last known date.
            if not re.search(r'[A-Za-z]', line):
                continue
            if not re.search(r'\d', line):
                continue
            if re.search(r'(Balance available|Net Payment Received|Total charge amount|VAT\b|Statement / Invoice|MONTHLY EMAIL|VAT Reg)', line, re.IGNORECASE):
                continue
            if not re.search(r'(PAYMENT|TRANSFER|CREDIT|DEBIT|FEE|PURCHASE|CASH|CHEQUE|STOP ORDER|REAL TIME|AUTOBANK|IB PAYMENT|PAYSHAP)', line, re.IGNORECASE):
                continue

            parts = line.split()


            # Description is from start to before the first numeric value
            desc_end_idx = 0
            for idx, part in enumerate(parts):
                # Consider this a numeric token only if it has a decimal/comma
                # followed by digits (e.g. '5,500.00' or '2500.00').
                # Ignore tokens like '9484.' (trailing punctuation) as amounts.
                if re.match(r'^[\d,]+\.?\d*-?$', part):
                    if re.search(r'[.,]\d', part):
                        break
                desc_end_idx = idx + 1

            description = ' '.join(parts[0:desc_end_idx])
            # Clean trailing punctuation from description (OCR may add a trailing dot)
            description = description.rstrip('.,').strip()

            # Extract amounts from the remainder (typically Service_Fee Debit Credit Date Balance)
            amounts = []
            for idx in range(desc_end_idx, len(parts)):
                raw = parts[idx]
                # Normalize token: remove thousands commas, strip trailing punctuation
                clean_token = raw.replace(',', '').rstrip('.,').rstrip('-')
                # Skip reference numbers (4 digits)
                if len(clean_token) == 4 and clean_token.isdigit():
                    continue
                # Skip YYYYMMDD dates (8 digits)
                if len(clean_token) == 8 and clean_token.isdigit():
                    continue
                # Handle negatives indicated by trailing dash
                is_negative = raw.endswith('-')
                val_str = raw.replace(',', '').rstrip('.,').rstrip('-')
                try:
                    val = float(val_str)
                    if is_negative:
                        val = -val
                    # Skip very large values (likely balance, not transaction)
                    if abs(val) > 10000000:  # 10 million threshold
                        continue
                    amounts.append(val)
                except ValueError:
                    pass

            if not amounts or not description:
                continue

            # Standard Bank format: Service_Fee, Debit (negative), Credit (positive)
            # Determine amount: use non-zero debit or credit
            negatives = [amt for amt in amounts if amt < 0]
            positives = [amt for amt in amounts if amt > 0]
            
            if negatives:
                # Has debit (expense) - use the negative amount
                amount = max(negatives)  # Closest to zero = actual transaction
            elif positives:
                # Has credit (income) - use smallest positive (not the balance)
                amount = min(positives)
            else:
                amount = 0.0

            if amount == 0.0:
                continue

            fallback_date = current_date or f"{statement_year}0101"
            rows.append([fallback_date, description, str(amount)])
            continue
        
        mmdd_str_raw = date_match.group(0).strip()
        month = date_match.group(1)
        day = date_match.group(2)
        mmdd_token = f"{month}{day}"
        
        # Convert MMDD to full date (YYYYMMDD)
        full_date = f"{statement_year}{month}{day}"
        current_date = full_date
        
        # Split line to extract parts
        parts = line.split()

        # Clean any trailing punctuation from description after extraction
        
        # Find date position. Handle both contiguous MMDD token and separated 'MM DD'
        date_idx = None
        for idx, part in enumerate(parts):
            if part == mmdd_token or part == mmdd_str_raw:
                date_idx = idx
                break
            # Handle split month/day tokens
            if idx + 1 < len(parts) and part == month and parts[idx + 1] == day:
                date_idx = idx + 1
                break
        
        if date_idx is None or date_idx < 2:
            continue
        
        # Description is from start to before the first numeric value
        # Find where numbers start
        desc_end_idx = 0
        for idx, part in enumerate(parts):
            # Check if this looks like a number (amount with comma/decimal)
            if re.match(r'^[\d,]+\.?\d*-?$', part):
                # Consider it an amount only if it has a comma/dot followed by digits
                if re.search(r'[.,]\d', part):
                    # This is likely an amount, description ends here
                    break
            desc_end_idx = idx + 1
        
        description = ' '.join(parts[0:desc_end_idx])
        description = description.rstrip('.,').strip()
        
        # Extract amounts between description and date
        # Format: Service_Fee, Debit (negative), Credit (positive)
        # Standard Bank: Debit/Credit will have commas or decimals
        amounts = []
        for idx in range(desc_end_idx, date_idx):
            raw = parts[idx]
            clean_token = raw.replace(',', '').rstrip('.,').rstrip('-')
            # Skip reference numbers like '9484' (4 digits)
            if len(clean_token) == 4 and clean_token.isdigit():
                continue
            # Skip YYYYMMDD dates (8 digits)
            if len(clean_token) == 8 and clean_token.isdigit():
                continue
            is_negative = raw.endswith('-')
            val_str = raw.replace(',', '').rstrip('.,').rstrip('-')
            try:
                val = float(val_str)
                if is_negative:
                    val = -val
                amounts.append(val)
            except ValueError:
                pass
        
        # Determine transaction amount
        # Standard Bank format: Service_Fee, Debit (negative), Credit (positive)
        # Debit is expense (negative), Credit is income (positive)
        amount = 0.0

        if amounts:
            negatives = [amt for amt in amounts if amt < 0]
            positives = [amt for amt in amounts if amt > 0]
            
            if negatives:
                # Has debit (expense) - use the last/largest magnitude negative
                amount = negatives[-1] if len(negatives) > 1 else negatives[0]
            elif positives:
                # Has credit (income) - use the last/largest positive (skip service fee)
                amount = positives[-1] if len(positives) > 1 else positives[0]
            else:
                # All zeros - skip this transaction
                amount = 0.0
        
        if amount == 0.0 or not description:
            continue
        
        rows.append([full_date, description, str(amount)])
        
        # After appending this row, check if the next line is a short text continuation
        # (merchant/reference name). Only append short lines to avoid including footer text.
        # Stop appending if we hit footer/disclaimer keywords.
        footer_keywords = [
            "These fees",
            "VAT Reg",
            "Authorised financial",
            "Standard Bank of South",
            "Reg. No.",
            "registered credit",
            "Code of Banking",
            "Ombudsman",
            "Business Banking",
            "QUEENSTOWN",
            "PICKERING STREET",
            "NEWTON PARK",
            "EASTERN CAPE",
            "CATHCART RD",
            "GETAHEAD",
            "COLLEGE PO BOX",
            "KOMANI",
        ]
        
        next_idx = i + 1
        max_continuations = 1  # Only append up to 1 continuation line
        appended = 0
        while next_idx < len(lines) and appended < max_continuations:
            next_line = lines[next_idx].strip()
            if not next_line:
                next_idx += 1
                continue
            # Stop if next line looks like a transaction line (has date or amount pattern)
            if re.search(r'\b(0[1-9]|1[0-2])[ \t]?(\d{2})\b', next_line):
                break
            if re.search(r'[.,]\d', next_line):
                break
            # Stop if line contains footer keywords
            if any(kw.upper() in next_line.upper() for kw in footer_keywords):
                break
            # Only append if line is reasonably short (likely merchant name, not long text)
            if len(next_line) > 80:
                break
            # Append the short continuation line
            if next_line:
                rows[-1][1] = f"{rows[-1][1]} {next_line}".strip()
                lines[next_idx] = ''
                appended += 1
            next_idx += 1
    
    return rows


def _parse_standard_bank_text(text: str, pdf) -> List[List[str]]:
    """
    Parse Standard Bank PDF text format from all pages
    
    Format per line: PAGE# DESCRIPTION... SERVICE_FEE DEBIT CREDIT DATE(YYYYMMDD) BALANCE
    Example: 10 ELECTRONIC BANKING TRANSFER TO 0.00 -92.71 0.00 20240222 6,536,806.66
    
    Description: From page# to before first numeric amount
    Debit/Credit: Usually second-to-last and last numeric amounts before balance
    Date: Always YYYYMMDD format  
    """
    rows = []
    
    # text parameter already contains all pages from the caller,
    # so we don't need to extract additional pages from pdf
    all_text = text
    lines = all_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip headers and empty lines
        if (not line or "CURRENT ACCOUNT" in line or "Page Details" in line or 
            "Standard Bank" in line or "Reg. No." in line or "DATE " in line or "Computer Generated" in line):
            i += 1
            continue
        
        # Look for transaction lines: must have YYYYMMDD date
        date_match = re.search(r'\s(\d{8})\s', line)  # Date surrounded by spaces
        if not date_match:
            i += 1
            continue
        
        date_str = date_match.group(1)
        
        # Split by spaces to extract amounts more reliably
        parts = line.split()
        
        if len(parts) < 5:  # At minimum: PAGE DESC AMOUNT AMOUNT DATE
            i += 1
            continue
        
        # Find the date position in parts
        date_idx = None
        for idx, part in enumerate(parts):
            if part == date_str:
                date_idx = idx
                break
        
        if date_idx is None or date_idx < 2:
            i += 1
            continue
        
        # The amounts before date are typically: Service_Fee Debit Credit (or Debit Credit if Service_Fee is missing)
        # We want the last three numeric values before the date
        numeric_before_date = []
        for j in range(date_idx):
            # Try to parse as float
            try:
                val = float(parts[j].replace(',', ''))
                numeric_before_date.append((j, val, parts[j]))
            except ValueError:
                pass
        
        if len(numeric_before_date) < 2:
            i += 1
            continue
        
        # Standard Bank format has Service_Fee, Debit, Credit in order
        # Get the last three numeric values if available
        if len(numeric_before_date) >= 3:
            service_fee_idx, service_fee_val, service_fee_str = numeric_before_date[-3]
            debit_idx, debit_val, debit_str = numeric_before_date[-2]
            credit_idx, credit_val, credit_str = numeric_before_date[-1]
            desc_end_idx = service_fee_idx  # Description ends before Service_Fee
        else:
            # Fallback if we don't have 3 numeric values (shouldn't happen with proper format)
            debit_idx, debit_val, debit_str = numeric_before_date[-2]
            credit_idx, credit_val, credit_str = numeric_before_date[-1]
            desc_end_idx = debit_idx
        
        # Determine the transaction amount
        # Standard Bank: negative debit means expense, positive credit means income
        if debit_val < 0:
            amount = debit_val  # Already negative for expense
        elif credit_val > 0:
            amount = credit_val  # Positive for income
        else:
            i += 1
            continue
        
        # Extract description: everything from after page number to before Service_Fee
        # The description is from parts[1] to parts[desc_end_idx-1]
        description = ' '.join(parts[1:desc_end_idx])
        
        if not description:
            i += 1
            continue
        
        # Check if next line is a continuation (non-transaction line with no date)
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not re.search(r'\s\d{8}\s', next_line) and not re.match(r'^\d+\s+', next_line):
                # Continuation line
                description = f"{description} {next_line}"
                i += 1
        
        rows.append([date_str, description, str(amount)])
        i += 1
    
    return rows


def pdf_to_csv_bytes(file_content: bytes, explain_amounts: Optional[List[float]] = None, explain_transactions: bool = False) -> Tuple[bytes, Optional[int], Optional[str]]:
    """OCR-first parser for Capitec statements (minimal implementation).

    If the first page text indicates a Capitec statement (or pdfplumber is
    unavailable), we run OCR and apply a simple line-based extractor.

    Returns (csv_bytes, statement_year, bank_type)
    """
    rows: List[List[str]] = []
    detected_bank: Optional[str] = None

    # Prepare explain set
    explain_set = set()
    if explain_amounts:
        try:
            explain_set = set(round(float(x), 2) for x in explain_amounts)
        except Exception:
            explain_set = set()

    # Try quick detection using pdfplumber text when available
    use_ocr = True
    pdf_obj = None
    try:
        import pdfplumber
        pdf_obj = pdfplumber.open(io.BytesIO(file_content))
        first_page_text = None
        if pdf_obj.pages:
            try:
                first_page_text = pdf_obj.pages[0].extract_text() or ''
            except Exception:
                first_page_text = ''

        if first_page_text and 'capitec' not in first_page_text.lower():
            # Not Capitec - try FNB/ABSA/Standard Bank with pdfplumber first
            use_ocr = False
    except Exception as e:
        # pdfplumber not available or failed; fall back to OCR
        use_ocr = True

    if use_ocr:
        if convert_from_bytes is None or pytesseract is None:
            raise ParserError('OCR dependencies missing; cannot parse image-based PDF.')

        # First, OCR all pages to detect bank
        ocr_texts = []
        try:
            # Convert all pages at 200 DPI
            images = convert_from_bytes(file_content, dpi=200)
            for idx, img in enumerate(images, start=1):
                img = img.convert('L')
                try:
                    text = pytesseract.image_to_string(img, lang='eng')
                    if text:
                        ocr_texts.append(text)
                except Exception as e:
                    print(f"[OCR] Failed to OCR page {idx}: {e}")
        except Exception as e:
            raise ParserError(f'OCR conversion failed: {e}')
        
        if not ocr_texts:
            raise ParserError('No OCR text extracted from PDF')
        
        # Detect bank from OCR text
        full_ocr_text = '\n'.join(ocr_texts).lower()
        if 'standard bank' in full_ocr_text or 'sbsa' in full_ocr_text:
            detected_bank = 'standard_bank'
        elif 'absa' in full_ocr_text or 'absacapital' in full_ocr_text:
            detected_bank = 'absa'
        elif 'fnb' in full_ocr_text or 'first national' in full_ocr_text:
            detected_bank = 'fnb'
        elif 'capitec' in full_ocr_text:
            detected_bank = 'capitec'
        else:
            # Default to capitec processing for unknown image PDFs
            detected_bank = 'capitec'
        
        ocr_text = '\n'.join(ocr_texts)
        
        # Track statement year for FNB
        detected_year = None

        # Handle bank-specific OCR parsing
        if detected_bank == 'standard_bank':
            # Standard Bank parsing: use _parse_standard_bank_business_text for OCR
            try:
                # Try to extract statement year
                statement_year = None
                year_match = re.search(r'Statement from.*?(\d{4})', ocr_text, re.IGNORECASE)
                if year_match:
                    statement_year = int(year_match.group(1))
                
                print(f"[DEBUG-SB] Calling _parse_standard_bank_business_text with year={statement_year}")
                parsed = _parse_standard_bank_business_text(ocr_text, pdf_obj, statement_year)
                print(f"[DEBUG-SB] Got {len(parsed) if parsed else 0} rows from business format")
                if parsed:
                    # DEBUG: Check for 9484
                    for row in parsed:
                        if '9484' in row[1]:
                            print(f"[DEBUG-SB] Found 9484 in parsed: {row}")
                    rows.extend(parsed)
                else:
                    # Try regular format if business format doesn't work
                    print(f"[DEBUG-SB] Calling _parse_standard_bank_text")
                    parsed = _parse_standard_bank_text(ocr_text, pdf_obj)
                    if parsed:
                        rows.extend(parsed)
            except Exception as e:
                print(f"[OCR] Failed to parse Standard Bank text: {e}")
                import traceback
                traceback.print_exc()
        elif detected_bank == 'absa':
            # ABSA parsing: use _parse_absa_text which handles OCR text
            try:
                parsed = _parse_absa_text(ocr_text, pdf_obj)
                if parsed:
                    rows.extend(parsed)
            except Exception as e:
                print(f"[OCR] Failed to parse ABSA text: {e}")
        elif detected_bank == 'fnb':
            # FNB parsing: try table extraction first, then fallback to OCR text parsing
            if pdf_obj is None:
                try:
                    import pdfplumber
                    pdf_obj = pdfplumber.open(io.BytesIO(file_content))
                except Exception:
                    pass
            
            # Try to extract statement year from OCR text
            # First, try to parse Statement Period to get the start and end years
            statement_year = None
            statement_end_year = None
            statement_start_year = None
            try:
                # Look for Statement Period: DD Month YYYY to DD Month YYYY
                period_match = re.search(
                    r'Statement\s+Period\s*:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+to\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
                    ocr_text,
                    re.IGNORECASE
                )
                if period_match:
                    start_year = int(period_match.group(3))
                    end_year = int(period_match.group(6))
                    statement_start_year = start_year
                    statement_year = start_year
                    statement_end_year = end_year
                    print(f"[OCR-FNB] Extracted statement period: {period_match.group(1)} {period_match.group(2)} {start_year} to {period_match.group(4)} {period_match.group(5)} {end_year}")
            except Exception:
                pass
            
            # Fallback: if Statement Period not found, count years and use the most common one
            if statement_year is None:
                try:
                    year_matches = re.findall(r'\b(20[0-2][0-9])\b', ocr_text)
                    if year_matches:
                        from collections import Counter
                        cnt = Counter(year_matches)
                        most_common_year = int(cnt.most_common(1)[0][0])
                        if 2010 <= most_common_year <= 2030:
                            statement_year = most_common_year
                except Exception:
                    pass
            
            # Try table extraction (works for text-extractable FNB PDFs)
            if pdf_obj:
                for page_num, page in enumerate(pdf_obj.pages):
                    try:
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                if table:
                                    parsed = _parse_fnb_table(table, statement_year, statement_end_year)
                                    if parsed:
                                        rows.extend(parsed)
                    except Exception as e:
                        print(f"[OCR-FNB] Failed to extract FNB table from page {page_num}: {e}")
                        pass
            
            # If no rows extracted from tables, try OCR text parsing
            if not rows:
                try:
                    parsed = _parse_fnb_ocr_text(ocr_text, statement_year, statement_end_year)
                    if parsed:
                        rows.extend(parsed)
                        print(f"[OCR-FNB] Extracted {len(parsed)} transactions from OCR text")
                except Exception as e:
                    print(f"[OCR-FNB] Failed to parse FNB OCR text: {e}")
            
            # Store the detected year for this path
            detected_year = statement_year
        elif detected_bank == 'capitec':
            # Capitec parsing: custom OCR logic
            date_line_re = re.compile(r'^(\s*)(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+(.+)$')
            # Amount pattern for transaction history: matches both formatted (2 721.12) and unformatted (2721.12) amounts
            # Pattern: optional minus sign, then digits (possibly with space/comma separators every 3 digits), decimal point, 2 digits
            amount_re = re.compile(r'-?\d+(?:[\s,]?\d{3})*[.,]\d{2}')
            # Amount pattern for pending: includes -R currency format  
            amount_re_pending = re.compile(r'-?R?\s*\d+(?:[\s,]?\d{3})*[.,]\d{2}')

            # Find where "Transaction History" section starts to skip summaries (Debit Orders, Spending Summary, etc.)
            ocr_text_lower = ocr_text.lower()
            transaction_history_idx = ocr_text_lower.find('transaction history')
            # Look for pending section (may be garbled by OCR as "nding cai" or similar)
            pending_idx = -1
            for pending_pattern in ['pending card', 'nding cai', 'pending transactions']:
                idx = ocr_text_lower.find(pending_pattern)
                if idx >= 0:
                    pending_idx = idx
                    break
            
            # Extract only transaction history section, stop at pending section
            if transaction_history_idx >= 0:
                if pending_idx > transaction_history_idx:
                    # Both sections exist; process transaction history up to pending
                    ocr_text = ocr_text[transaction_history_idx:pending_idx]
                else:
                    # Only transaction history
                    ocr_text = ocr_text[transaction_history_idx:]
            else:
                # No transaction history marker, use all text
                ocr_text = ocr_text

            # Process transaction history section
            for raw_line in ocr_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                
                # Skip known header/footer lines
                if any(k in line for k in ['Capitec Bank', 'Statement', 'Opening', 'Closing', 'Balance', 'Date Description', 'Money In', 'Money Out', 'Transaction History']):
                    continue

                m = date_line_re.match(line)
                if not m:
                    continue
                date_str = m.group(2)
                rest = m.group(3)

                # find all amounts; Capitec format is: Description | Money In | Money Out | Fee* | Balance
                amounts = amount_re.findall(rest)
                if not amounts:
                    continue

                # Parse all amounts to separate transaction (Money Out/In) and fee amounts
                parsed_amounts = []
                for amt_str in amounts:
                    clean = amt_str.replace(' ', '').replace(',', '.')
                    try:
                        parsed_amounts.append((float(clean), amt_str))
                    except:
                        pass
                
                if not parsed_amounts:
                    continue

                # Identify transaction amount and fee amount
                negative_amounts = [(v, s) for v, s in parsed_amounts if v < 0]
                positive_amounts = [(v, s) for v, s in parsed_amounts if v >= 0]
                
                txn_amt = None
                fee_amt = None
                
                # If multiple negatives: smaller one (|value| <= 5) is likely a fee
                if len(negative_amounts) >= 2:
                    # Sort by absolute value
                    negative_amounts_by_abs = sorted(negative_amounts, key=lambda x: abs(x[0]))
                    if abs(negative_amounts_by_abs[0][0]) <= 5.0:
                        # First (smallest absolute) is likely the fee
                        fee_amt = negative_amounts_by_abs[0][0]
                        txn_amt = negative_amounts_by_abs[1][0]  # Second largest is transaction
                    else:
                        # Pick first negative as transaction, second as fee (if exists)
                        txn_amt = negative_amounts[0][0]
                        if len(negative_amounts) > 1:
                            fee_amt = negative_amounts[1][0]
                elif len(negative_amounts) == 1:
                    txn_amt = negative_amounts[0][0]
                elif positive_amounts:
                    # No negatives, use first positive (Money In)
                    txn_amt = positive_amounts[0][0]
                else:
                    continue
                
                if txn_amt is None:
                    continue

                # Build description by removing all amount strings
                desc = rest
                for _, amt_str in parsed_amounts:
                    desc = desc.replace(amt_str, '', 1)
                
                desc = desc.strip()
                desc = re.sub(r'\s{2,}', ' ', desc).strip(' ,-')
                
                if not desc or len(desc) < 3:
                    continue

                # Add transaction row
                rows.append([date_str, desc, f"{txn_amt:.2f}"])
                
                # Add separate fee row if present
                if fee_amt is not None and fee_amt != 0:
                    rows.append([date_str, f"{desc} (Fee)", f"{fee_amt:.2f}"])

        # If no rows found, return header-only CSV
        if not rows:
            if pdf_obj:
                pdf_obj.close()
            return _rows_to_csv([]), detected_year, detected_bank

        if pdf_obj:
            pdf_obj.close()
        return _rows_to_csv(rows), detected_year, detected_bank
    
    else:
        # pdfplumber path: try FNB/ABSA table extraction
        try:
            if pdf_obj is None:
                import pdfplumber
                pdf_obj = pdfplumber.open(io.BytesIO(file_content))
            
            # Try to detect and parse FNB or ABSA
            full_text = ''
            try:
                for page in pdf_obj.pages:
                    page_text = page.extract_text() or ''
                    if page_text:
                        full_text += page_text + '\n'
            except Exception:
                pass
            
            text_lower = full_text.lower()

            # Try to infer the statement year from visible text (e.g., header 'Statement 2024')
            statement_year = None
            statement_end_year = None
            try:
                years = re.findall(r"\b(20[0-2][0-9])\b", full_text)  # 2000-2029 only
                if years:
                    # Pick the most frequent year mention
                    from collections import Counter
                    cnt = Counter(years)
                    most_common_year = int(cnt.most_common(1)[0][0])
                    # Sanity check: year should be reasonable (2010-2030)
                    if 2010 <= most_common_year <= 2030:
                        statement_year = most_common_year
            except Exception:
                statement_year = None
            
            # Check for FNB
            if 'fnb' in text_lower or 'first national' in text_lower:
                detected_bank = 'fnb'
                # Extract year from statement period if available
                try:
                    period_match = re.search(
                        r'Statement\s+Period\s*:\s*(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+to\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',
                        full_text,
                        re.IGNORECASE
                    )
                    if period_match:
                        statement_year = int(period_match.group(3))
                        statement_end_year = int(period_match.group(6))
                except Exception:
                    pass
                
                for page_num, page in enumerate(pdf_obj.pages):
                    try:
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                if table:  # Make sure table is not empty
                                    parsed = _parse_fnb_table(table, statement_year, statement_end_year)
                                    if parsed:
                                        rows.extend(parsed)
                    except Exception as e:
                        print(f"[PDF] Failed to extract FNB table from page {page_num}: {e}")
                        pass
            
            # Check for Standard Bank
            elif 'standard bank' in text_lower or 'sbsa' in text_lower:
                detected_bank = 'standard_bank'
                try:
                    # First try regular format (YYYYMMDD dates) - most common
                    parsed = _parse_standard_bank_text(full_text, pdf_obj)
                    if parsed and len(parsed) > 0:
                        rows.extend(parsed)
                    else:
                        # Fallback to Business Account format (MMDD dates)
                        parsed = _parse_standard_bank_business_text(full_text, pdf_obj, statement_year)
                        if parsed:
                            rows.extend(parsed)
                except Exception as e:
                    print(f"[PDF] Failed to parse Standard Bank text: {e}")
                    import traceback
                    traceback.print_exc()
                    pass
            
            # Check for ABSA
            elif 'absa' in text_lower or 'absacapital' in text_lower:
                detected_bank = 'absa'
                try:
                    parsed = _parse_absa_text(full_text, pdf_obj)
                    if parsed:
                        rows.extend(parsed)
                except Exception as e:
                    print(f"[PDF] Failed to parse ABSA text: {e}")
                    pass
            
            # Fallback: try generic table extraction if no rows yet
            if not rows:
                for page_num, page in enumerate(pdf_obj.pages):
                    try:
                        tables = page.extract_tables()
                        if tables:
                            for table in tables:
                                if table:
                                    # Try FNB parsing first, then fallback to simple extraction
                                    parsed = _parse_fnb_table(table, statement_year, statement_end_year)
                                    if parsed:
                                        rows.extend(parsed)
                                    else:
                                        # Fallback: try to extract first 3 columns as date/desc/amount
                                        for row in table[1:]:  # Skip header
                                            if len(row) >= 3 and row[0] and row[1] and row[2]:
                                                rows.append([str(row[0]), str(row[1]), str(row[2])])
                    except Exception as e:
                        print(f"[PDF] Failed to extract table from page {page_num}: {e}")
                        pass
            
            if not rows:
                raise ParserError('Could not extract transactions from PDF - no tables found')
            
            if pdf_obj:
                pdf_obj.close()
            return _rows_to_csv(rows), statement_year, detected_bank
        
        except Exception as e:
            if pdf_obj:
                try:
                    pdf_obj.close()
                except:
                    pass
            raise ParserError(f'PDF parsing failed: {str(e)}')

    # If not using OCR and not Capitec, return empty header for now
    return _rows_to_csv([]), None, detected_bank
