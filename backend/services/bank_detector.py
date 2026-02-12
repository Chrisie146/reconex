"""
Bank Detector - Identifies bank statement format
Analyzes CSV headers, date formats, and transaction patterns to detect bank source
"""

from typing import Tuple, Dict, List, Optional
import re
from enum import Enum


class BankType(Enum):
    """Supported bank types"""
    STANDARD_BANK = "standard_bank"
    ABSA = "absa"
    CAPITEC = "capitec"
    FNB = "fnb"
    UNKNOWN = "unknown"


class BankDetector:
    """Detects bank statement format from CSV headers and sample rows"""

    # Standard Bank patterns
    STANDARD_BANK_PATTERNS = {
        "headers": [r"(?i)page", r"(?i)debit", r"(?i)credit", r"(?i)balance"],
        "date_format": r"\d{8}",  # YYYYMMDD
        "has_service_fee": True,
    }

    # ABSA patterns
    ABSA_PATTERNS = {
        "headers": [r"(?i)transaction\s*date|trans\s*date", r"(?i)debit", r"(?i)credit"],
        "date_format": r"\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY
        "transaction_type": True,
    }

    # Capitec patterns
    CAPITEC_PATTERNS = {
        "headers": [r"(?i)date", r"(?i)description", r"(?i)amount"],
        "date_format": r"\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD
        "single_amount_col": True,
    }

    # FNB patterns
    FNB_PATTERNS = {
        "headers": [r"(?i)date", r"(?i)amount", r"(?i)description", r"(?i)balance"],
        "date_format": r"\d{4}/\d{2}/\d{2}",  # YYYY/MM/DD
    }

    @staticmethod
    def detect(csv_headers: List[str], sample_rows: List[List[str]] = None) -> Tuple[BankType, float]:
        """
        Detect bank type from CSV headers and optional sample rows

        Args:
            csv_headers: List of column headers
            sample_rows: Optional list of 2-3 sample data rows for pattern analysis

        Returns:
            Tuple of (BankType, confidence_score 0-1.0)
        """
        headers_lower = [h.lower() for h in csv_headers]
        headers_str = " ".join(headers_lower)

        scores = {
            BankType.STANDARD_BANK: BankDetector._score_standard_bank(headers_str, csv_headers, sample_rows),
            BankType.ABSA: BankDetector._score_absa(headers_str, csv_headers, sample_rows),
            BankType.CAPITEC: BankDetector._score_capitec(headers_str, csv_headers, sample_rows),
            BankType.FNB: BankDetector._score_fnb(headers_str, csv_headers, sample_rows),
        }

        best_bank = max(scores, key=scores.get)
        confidence = scores[best_bank]

        # If confidence is very low, return UNKNOWN
        if confidence < 0.3:
            return BankType.UNKNOWN, confidence

        return best_bank, confidence

    @staticmethod
    def _score_standard_bank(headers_str: str, headers: List[str], sample_rows: List[List[str]]) -> float:
        """Score likelihood of Standard Bank format"""
        score = 0.0
        max_score = 0.0

        # Check for distinctive headers
        if "page" in headers_str:
            score += 0.3
        if "service fee" in headers_str:
            score += 0.2
        if re.search(r"\bdebit\b.*\bcredit\b.*\bdate\b.*\bbalance\b", headers_str):
            score += 0.3

        max_score += 0.8

        # Check for date format YYYYMMDD in samples
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{8}$", str(cell).strip()):
                        score += 0.2
                        break
                if score > 0.9:
                    break

        max_score += 0.2

        return min(score, 1.0) / max(max_score, 1.0)

    @staticmethod
    def _score_absa(headers_str: str, headers: List[str], sample_rows: List[List[str]]) -> float:
        """Score likelihood of ABSA format"""
        score = 0.0
        max_score = 0.0

        # Check for ABSA-specific headers
        if re.search(r"trans(action)?\s*date|transaction\s*date", headers_str):
            score += 0.3
        if "debit" in headers_str and "credit" in headers_str:
            score += 0.2
        if re.search(r"description", headers_str):
            score += 0.1

        max_score += 0.6

        # Check for DD/MM/YYYY date format (ABSA's OCR extraction produces YYYYMMDD format)
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    cell_str = str(cell).strip()
                    # ABSA: Look for dates that DON'T match Standard Bank patterns
                    # Standard Bank dates are 8-digit YYYYMMDD
                    # ABSA OCR gives YYYYMMDD but with only month/day pattern 20250601
                    if re.match(r"^202[0-9]{5}$", cell_str):  # 2025xxxx format
                        score += 0.4
                        break
                if score >= 0.7:
                    break

        max_score += 0.4

        return min(score, 1.0) / max(max_score, 1.0)

    @staticmethod
    def _score_capitec(headers_str: str, headers: List[str], sample_rows: List[List[str]]) -> float:
        """Score likelihood of Capitec format"""
        score = 0.0

        # Check for Capitec-specific headers (original format)
        if "date" in headers_str and "description" in headers_str and "amount" in headers_str:
            score += 0.4
        if len(headers) == 3 and "amount" in headers_str:
            score += 0.2

        # Check for new Capitec CSV export format (Money In/Money Out)
        if "money" in headers_str and ("money in" in headers_str or "money out" in headers_str):
            score += 0.5
        if "posting date" in headers_str or "transaction date" in headers_str:
            score += 0.2
        if "account" in headers_str and "balance" in headers_str:
            score += 0.1

        # Check for YYYY-MM-DD date format
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{4}-\d{2}-\d{2}", str(cell).strip()):
                        score += 0.2
                        break
                if score > 0.7:
                    break

        return min(score, 1.0)

    @staticmethod
    def _score_fnb(headers_str: str, headers: List[str], sample_rows: List[List[str]]) -> float:
        """Score likelihood of FNB format"""
        score = 0.0
        max_score = 0.0

        # Header signals: includes balance and amount
        if "balance" in headers_str:
            score += 0.3
        if "amount" in headers_str and "description" in headers_str and "date" in headers_str:
            score += 0.3

        max_score += 0.6

        # Date format: YYYY/MM/DD
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{4}/\d{2}/\d{2}$", str(cell).strip()):
                        score += 0.3
                        break
                if score >= 0.8:
                    break

        max_score += 0.3

        # Content hints
        if sample_rows:
            for row in sample_rows[:3]:
                row_str = " ".join([str(c).lower() for c in row if c is not None])
                if "fnb" in row_str or "first national" in row_str:
                    score += 0.2
                    break

        max_score += 0.2

        return min(score, 1.0) / max(max_score, 1.0)

    @staticmethod
    def get_bank_name(bank_type: BankType) -> str:
        """Get human-readable bank name"""
        mapping = {
            BankType.STANDARD_BANK: "Standard Bank",
            BankType.ABSA: "ABSA Bank",
            BankType.CAPITEC: "Capitec Bank",
            BankType.FNB: "FNB (First National Bank)",
            BankType.UNKNOWN: "Unknown/Generic",
        }
        return mapping.get(bank_type, "Unknown")
