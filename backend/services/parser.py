"""
CSV Parser Service
Validates, normalizes, and prepares bank statement data for processing
"""

import csv
import io
import sys
import os
import re
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import pandas as pd

# Import multilingual column mapping
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import multilingual

# Import bank detection and adapters
from .bank_detector import BankDetector, BankType
from .bank_adapters import get_adapter

REQUIRED_COLUMNS = ["Date", "Description", "Amount"]

# Helper function to check if value is "NaN" or empty
def is_na(val) -> bool:
    """Check if value is None or NaN-like"""
    if val is None:
        return True
    if isinstance(val, float) and val != val:  # NaN check
        return True
    if isinstance(val, str):
        val_lower = val.lower().strip()
        if val_lower in ["nan", "none", "n/a", "na", "-", ""]:
            return True
    return False

# Helper function to clean NaN-like strings
def clean_value(val) -> str:
    """Convert value to string and remove NaN/None/empty markers"""
    if is_na(val):
        return ""
    result = str(val).strip()
    return result if result else ""

FLEXIBLE_AMOUNT_COLUMNS = ["Amount", "Debit", "Credit", "Debit/Credit"]


class ParserError(Exception):
    """Custom exception for parsing errors"""
    pass


def _map_csv_headers_multilingual(csv_headers: List[str]) -> Dict[str, int]:
    """
    Map CSV column headers to canonical column names using multilingual module.
    
    Args:
        csv_headers: List of header strings from CSV
    
    Returns:
        Dict mapping canonical names (date, description, amount, debit, credit, balance) to column indices
        
    Raises:
        ValueError: If required columns are not found or ambiguous
    """
    try:
        return multilingual.normalize_headers(csv_headers)
    except multilingual.ColumnDetectionError as e:
        # Re-raise with ParserError so calling code can handle it
        raise ParserError(str(e))


def validate_csv(file_content: bytes) -> Tuple[bool, str]:
    """
    Validate that CSV has required columns and proper structure
    Uses multilingual column mapping for deterministic detection
    
    Args:
        file_content: Raw bytes of uploaded CSV file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # First, try to read the CSV to find where the actual headers are
        rows_and_headers = _find_data_start(file_content)
        
        if rows_and_headers is None or len(rows_and_headers[1]) == 0:
            return False, "CSV file is empty or no data found"
        
        # Try multilingual header mapping first
        try:
            headers_list = rows_and_headers[0]
            _map_csv_headers_multilingual(headers_list)
            # If we get here, mapping succeeded
            return True, ""
        except ParserError as pe:
            # Fallback: provide helpful message
            return False, str(pe)
        
    except Exception as e:
        return False, f"Error reading CSV: {str(e)}"


def _find_data_start(file_content: bytes):
    """
    Find where the actual data starts in a CSV file
    Some bank statements have header rows/metadata before the actual column names
    
    Returns:
        Tuple of (headers_list, data_rows) or None if not found
    """
    try:
        text = file_content.decode('utf-8', errors='replace')
        reader = csv.reader(io.StringIO(text))
        all_rows = list(reader)
        
        if not all_rows:
            return None
        
        # Look for a row that contains typical column header names
        header_keywords = {
            "date": ["date", "transaction date", "posted date", "value date"],
            "amount": ["amount", "transaction amount", "debit/credit"],
            "description": ["description", "particulars", "narration", "details"]
        }
        
        # Find header row
        for idx, row in enumerate(all_rows):
            if not row:
                continue
            row_values = [str(val).lower().strip() for val in row if val and not is_na(val)]
            row_str = " ".join(row_values)
            
            # Check if this row looks like a header row
            has_date = any(kw in row_str for kw in header_keywords["date"])
            has_desc_or_amount = (
                any(kw in row_str for kw in header_keywords["description"]) or
                any(kw in row_str for kw in header_keywords["amount"])
            )
            
            if has_date and has_desc_or_amount:
                # Found likely header row
                headers = [str(col).strip() for col in row]
                data_rows = all_rows[idx + 1:]
                if len(data_rows) > 0:
                    return (headers, data_rows)
        
        # Fallback: use first row as headers
        if all_rows:
            headers = [str(col).strip() for col in all_rows[0]]
            data_rows = all_rows[1:]
            return (headers, data_rows)
        
        return None
    except Exception as e:
        print(f"Error parsing CSV: {e}")
        return None


def _clean_rows(headers: List[str], rows: List[List[str]]) -> Tuple[List[str], List[Dict[str, str]]]:
    """Clean columns and rows for noisy CSV exports."""
    if not headers or not rows:
        return headers, rows

    # Normalize header names
    clean_headers = [str(col).strip() for col in headers]
    
    # Remove empty column indices
    valid_indices = [i for i, h in enumerate(clean_headers) if h and not h.lower().startswith("unnamed")]
    if not valid_indices:
        return clean_headers, rows
    
    # Filter headers and reconstruct rows
    clean_headers = [clean_headers[i] for i in valid_indices]
    cleaned_rows = []
    for row in rows:
        # Skip totally empty rows
        if not row or all(not val or is_na(val) for val in row):
            continue
        # Build dict with valid columns only
        row_dict = {}
        for idx in valid_indices:
            col_name = clean_headers[len(row_dict)] if len(row_dict) < len(clean_headers) else f"col_{len(row_dict)}"
            val = row[idx] if idx < len(row) else ""
            row_dict[col_name] = clean_value(val)
        cleaned_rows.append(row_dict)
    
    return clean_headers, cleaned_rows


def normalize_csv(file_content: bytes, statement_year: int = None, forced_bank: Optional[str] = None) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]], str]:
    """
    Normalize CSV data to standard format
    Auto-detects bank and applies appropriate adapter
    
    Args:
        file_content: Raw bytes of uploaded CSV file
        statement_year: Optional year for short date formats (e.g., "14 Nov")
        
    Returns:
        Tuple of (normalized_transactions, error_message, detailed_errors, bank_source)
        - normalized_transactions: List of dicts with keys: date, description, amount, debit_flag
        - error_message: Short summary string (empty if successful)
        - detailed_errors: List of dicts with keys `row`, `reason`, and `raw` for skipped rows
        - bank_source: Detected bank source (e.g., 'standard_bank', 'absa', 'capitec', 'unknown')
    """
    try:
        # Use smart header detection
        df = _find_data_start(file_content)
        if df is None or df.empty:
            return [], "Could not find data in CSV file", [], "unknown"
        
        # Normalize column names (strip whitespace) and clean noise
        df = _clean_dataframe(df)
        
        # Detect bank from headers and sample rows
        headers_list = list(df.columns)
        sample_rows = df.head(3).values.tolist() if len(df) > 0 else []
        
        # Allow caller to force bank type (pdf parser) to avoid mis-detection
        if forced_bank:
            bank_source = forced_bank
            print(f"[PARSER] Forced bank source from PDF parser: {bank_source}")
        else:
            bank_type, confidence = BankDetector.detect(headers_list, sample_rows)
            bank_source = bank_type.value
            print(f"[PARSER] Detected bank: {BankDetector.get_bank_name(bank_type)} (confidence: {confidence:.1%})")

        # Apply bank adapter
        adapter = get_adapter(bank_source)
        
        try:
            # Normalize using bank-specific adapter
            df_normalized = adapter.normalize(df)
            
            if df_normalized.empty:
                return [], "Bank adapter produced no valid transactions", [], bank_source
            
            # Convert normalized dataframe to transaction list
            transactions = []
            errors = []
            detailed_errors: List[Dict[str, Any]] = []
            
            for idx, row in df_normalized.iterrows():
                try:
                    date_str = row.get("Date", "")
                    description = row.get("Description", "")
                    amount = row.get("Amount", 0.0)
                    
                    # Parse the date (should already be normalized, but verify)
                    date_obj = parse_date(date_str, statement_year)
                    if not date_obj:
                        msg = f"Invalid date format '{date_str}'"
                        errors.append(f"Row {idx + 2}: {msg}")
                        detailed_errors.append({"row": idx + 2, "reason": msg, "raw": dict(row)})
                        continue
                    
                    # Allow blank descriptions (e.g., Apple payment fees)
                    # Just warn but don't skip the transaction
                    if not description:
                        description = "(No description)"
                        msg = "Empty description - using placeholder"
                        errors.append(f"Row {idx + 2}: {msg}")
                    
                    if amount is None:
                        msg = f"Invalid amount"
                        errors.append(f"Row {idx + 2}: {msg}")
                        detailed_errors.append({"row": idx + 2, "reason": msg, "raw": dict(row)})
                        continue
                    
                    transactions.append({
                        "date": date_obj,
                        "description": description,
                        "amount": float(amount),
                        "debit_flag": float(amount) < 0  # Expenses are negative
                    })
                
                except Exception as e:
                    errors.append(f"Row {idx + 2}: {str(e)}")
            
            # Report errors if any
            error_msg = ""
            if errors:
                error_msg = "Warnings during parsing:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f"\n... and {len(errors) - 5} more issues"
            
            return transactions, error_msg, detailed_errors, bank_source
        
        except Exception as e:
            print(f"[PARSER] Bank adapter failed: {e}. Falling back to generic parser.")
            # Fallback: use old parsing logic (unchanged from original)
            return _parse_generic(df, statement_year)
        
    except Exception as e:
        print(f"[PARSER] Error: {e}")
        return [], f"Error processing CSV: {str(e)}", [], "unknown"


def _parse_generic(df: pd.DataFrame, statement_year: int = None) -> Tuple[List[Dict[str, Any]], str, List[Dict[str, Any]], str]:
    """Fallback generic parser (original logic)"""
    try:
        headers_list = list(df.columns)
        
        # Try multilingual mapping
        try:
            column_map = _map_csv_headers_multilingual(headers_list)
            date_col = df.columns[column_map["date"]] if "date" in column_map else None
            desc_col = df.columns[column_map["description"]] if "description" in column_map else None
            amount_col = df.columns[column_map["amount"]] if "amount" in column_map else None
            debit_col = df.columns[column_map["debit"]] if "debit" in column_map else None
            credit_col = df.columns[column_map["credit"]] if "credit" in column_map else None
        except ParserError as pe:
            return [], str(pe), [{"row": 1, "reason": str(pe), "raw": {}}], "unknown"
        
        if not date_col or not desc_col:
            return [], "Could not identify required columns (Date and Description)", [], "unknown"

        # Fallback detection
        def _is_date_column(col_name):
            sample = df[col_name].dropna().astype(str).head(10)
            if sample.empty:
                return False
            parsed = sum(1 for v in sample if parse_date(v.strip()) is not None)
            return parsed >= max(1, len(sample) // 2)

        def _is_amount_column(col_name):
            sample = df[col_name].dropna().astype(str).head(10)
            if sample.empty:
                return False
            parsed = sum(1 for v in sample if parse_amount(str(v).strip()) is not None)
            return parsed >= max(1, len(sample) // 2)

        def _is_text_column(col_name):
            sample = df[col_name].dropna().astype(str).head(10)
            if sample.empty:
                return False
            non_numeric = sum(1 for v in sample if parse_amount(str(v).strip()) is None)
            long_enough = sum(1 for v in sample if len(str(v).strip()) > 3)
            return non_numeric >= max(1, len(sample) // 2) and long_enough >= max(1, len(sample) // 2)

        if date_col is None:
            for col in df.columns:
                if _is_date_column(col):
                    date_col = col
                    break

        if desc_col is None:
            for col in df.columns:
                if col == date_col:
                    continue
                if _is_text_column(col):
                    desc_col = col
                    break

        if amount_col is None and not (debit_col and credit_col):
            for col in df.columns:
                if col in (date_col, desc_col):
                    continue
                if _is_amount_column(col):
                    amount_col = col
                    break
        
        transactions = []
        errors = []
        detailed_errors: List[Dict[str, Any]] = []
        
        for idx, row in df.iterrows():
            try:
                date_str = str(row[date_col]).strip()
                date_obj = parse_date(date_str, statement_year)
                if not date_obj:
                    msg = f"Invalid date format '{date_str}'"
                    errors.append(f"Row {idx + 2}: {msg}")
                    detailed_errors.append({"row": idx + 2, "reason": msg, "raw": _row_to_simple_dict(row)})
                    continue

                description = clean_value(row[desc_col])
                try:
                    desc_idx = df.columns.get_loc(desc_col)
                    extra_parts = []
                    for extra_col in df.columns[desc_idx + 1:]:
                        val = clean_value(row.get(extra_col))
                        if val:
                            extra_parts.append(val)
                    if extra_parts:
                        description = description + ' ' + ' '.join(extra_parts) if description else ' '.join(extra_parts)
                except Exception:
                    pass
                
                if not description:
                    msg = "Empty description"
                    errors.append(f"Row {idx + 2}: {msg}")
                    detailed_errors.append({"row": idx + 2, "reason": msg, "raw": _row_to_simple_dict(row)})
                    continue

                if amount_col:
                    amount = parse_amount(str(row[amount_col]))
                elif debit_col and credit_col:
                    debit = parse_amount(str(row[debit_col])) if pd.notna(row[debit_col]) else 0
                    credit = parse_amount(str(row[credit_col])) if pd.notna(row[credit_col]) else 0
                    amount = credit - debit
                else:
                    msg = "Unable to determine amount"
                    errors.append(f"Row {idx + 2}: {msg}")
                    detailed_errors.append({"row": idx + 2, "reason": msg, "raw": _row_to_simple_dict(row)})
                    continue

                if amount is None:
                    raw_val = str(row[amount_col]) if amount_col else "N/A"
                    msg = f"Invalid amount '{raw_val}'"
                    errors.append(f"Row {idx + 2}: {msg}")
                    detailed_errors.append({"row": idx + 2, "reason": msg, "raw": _row_to_simple_dict(row)})
                    continue

                transactions.append({
                    "date": date_obj,
                    "description": description,
                    "amount": amount,
                    "debit_flag": amount < 0
                })

            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
        
        error_msg = ""
        if errors:
            error_msg = "Warnings during parsing:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                error_msg += f"\n... and {len(errors) - 5} more issues"

        return transactions, error_msg, detailed_errors, "unknown"
        
    except Exception as e:
        return [], f"Error in generic parsing: {str(e)}", [], "unknown"

        
    except Exception as e:
        return [], f"Error processing CSV: {str(e)}"


def parse_date(date_str: str, statement_year: int = None) -> datetime.date:
    """
    Parse date string in multiple common formats
    Returns None if unable to parse
    
    Args:
        date_str: Date string to parse
        statement_year: Optional year to use for short date formats (e.g., "14 Nov")
    """
    # Fix OCR artifacts: replace common misreadings before parsing
    # '0ct' (zero) -> 'Oct', etc.
    normalized_date_str = date_str
    normalized_date_str = re.sub(r'\b0ct\b', 'Oct', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ec\b', 'Dec', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ov\b', 'Nov', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0an\b', 'Jan', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ar\b', 'Mar', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0pr\b', 'Apr', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ay\b', 'May', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0un\b', 'Jun', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ul\b', 'Jul', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ug\b', 'Aug', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\b0ep\b', 'Sep', normalized_date_str, flags=re.IGNORECASE)
    
    # Additional OCR typos
    normalized_date_str = re.sub(r'\bQet\b', 'Oct', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\bNoy\b', 'Nov', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\bvar\b', 'Jan', normalized_date_str, flags=re.IGNORECASE)
    normalized_date_str = re.sub(r'\bvat\b', '', normalized_date_str, flags=re.IGNORECASE)  # Remove VAT header
    
    # Afrikaans to English month mapping (abbreviated)
    afr_to_eng = {
        'jan': 'Jan', 'feb': 'Feb', 'maa': 'Mar', 'mrt': 'Mar',
        'apr': 'Apr', 'mei': 'May', 'jun': 'Jun', 'jul': 'Jul',
        'aug': 'Aug', 'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'des': 'Dec'
    }
    
    # Normalize Afrikaans months to English
    for afr, eng in afr_to_eng.items():
        # Case-insensitive replace
        normalized_date_str = re.sub(rf'\b{afr}\b', eng, normalized_date_str, flags=re.IGNORECASE)
    
    formats = [
        "%Y-%m-%d",      # 2024-01-15
        "%d/%m/%Y",      # 15/01/2024
        "%m/%d/%Y",      # 01/15/2024
        "%d-%m-%Y",      # 15-01-2024
        "%Y/%m/%d",      # 2024/01/15
        "%d.%m.%Y",      # 15.01.2024
        "%B %d, %Y",     # January 15, 2024
        "%b %d, %Y",     # Jan 15, 2024
        "%d %b %Y",      # 15 Jan 2024 (common bank format)
        "%d %B %Y",      # 15 January 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(normalized_date_str, fmt).date()
        except ValueError:
            continue
    
    # Try short formats with inferred year (e.g., "14 Nov", "15 Dec", "14Nov", "17Aug")
    if statement_year:
        short_formats = [
            "%d %b",     # 14 Nov
            "%d %B",     # 14 November
            "%b %d",     # Nov 14
            "%B %d",     # November 14
            "%d%b",      # 14Nov (no space)
            "%b%d",      # Nov14 (no space)
        ]
        for fmt in short_formats:
            try:
                # Append year to date_str before parsing to handle leap year dates like "29 Feb"
                date_with_year = f"{normalized_date_str} {statement_year}"
                fmt_with_year = f"{fmt} %Y"
                parsed = datetime.strptime(date_with_year, fmt_with_year)
                return parsed.date()
            except ValueError:
                continue
    
    return None


def parse_amount(amount_str: str) -> float:
    """
    Parse amount string to float, handling various formats
    Returns None if unable to parse
    """
    if not amount_str or amount_str.lower() in ["nan", "none", ""]:
        return None

    try:
        cleaned = amount_str.strip()

        # Detect negative amounts represented with parentheses e.g. (2.75)
        negative = False
        if cleaned.startswith('(') and cleaned.endswith(')'):
            negative = True
            cleaned = cleaned[1:-1]
        
        # Handle FNB format: amounts ending with 'C'/'K'/'Kt' (Credit/Krediet) or 'D'/'Dt' (Debit)
        # English: 'C' = Credit (positive), 'D' = Debit (negative)
        # Afrikaans: 'K'/'Kt'/'Krediet' = Krediet (positive), 'Dt' = Debiet (negative)
        # e.g., "300.00C" = credit (positive), "300.00K" = krediet (positive)
        # e.g., "8.00" or "8.00D" or "8.00Dt" = debit (negative)
        credit_suffix = False
        if cleaned.upper().endswith(('C', 'CR', 'K', 'KT', 'KREDIET')):
            credit_suffix = True
            # Remove credit markers (C, K, Kt, Krediet, etc.)
            for marker in ['krediet', 'kt', 'k', 'cr', 'c']:
                if cleaned.upper().endswith(marker.upper()):
                    cleaned = cleaned[:-len(marker)].strip()
                    break
        elif cleaned.upper().endswith(('D', 'DR', 'DT', 'DEBIET')):
            # Remove debit markers (D, Dt, Debiet, etc.)
            for marker in ['debiet', 'dt', 'd', 'dr']:
                if cleaned.upper().endswith(marker.upper()):
                    cleaned = cleaned[:-len(marker)].strip()
                    break
            negative = True

        # Remove common currency symbols and whitespace
        for symbol in ["$", "€", "£", "R", "R$"]:
            cleaned = cleaned.replace(symbol, "")
        
        # Remove thousand separators (commas)
        cleaned = cleaned.replace(',', '')

        # Remove any spaces
        cleaned = cleaned.replace(' ', '')

        # Handle comma as decimal separator (European format) - only if no period exists
        # (already removed thousand separator commas above)
        
        # Handle leading plus/minus
        if cleaned.startswith('+'):
            cleaned = cleaned[1:]
        if cleaned.startswith('-'):
            negative = True
            cleaned = cleaned[1:]

        value = float(cleaned)
        
        # FNB logic: amounts with 'C' suffix are credits (positive/income)
        # amounts without suffix or with 'D' are debits (negative/expenses)
        if credit_suffix:
            return value  # Credits are positive income
        else:
            return -value if not negative else value  # Debits are negative expenses
            
    except (ValueError, AttributeError):
        return None


def _row_to_simple_dict(row) -> Dict[str, Any]:
    """Convert a pandas Series row to a simple dict with stringified values."""
    try:
        return {str(k): ("" if pd.isna(v) else str(v)) for k, v in row.items()}
    except Exception:
        # fallback for non-standard row types
        try:
            return {str(i): str(v) for i, v in enumerate(list(row))}
        except Exception:
            return {"row": str(row)}
