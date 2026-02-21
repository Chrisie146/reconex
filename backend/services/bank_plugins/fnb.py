"""
FNB (First National Bank) plugin – wraps existing FNBAdapter.
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class FNBPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="fnb",
        bank_name="FNB (First National Bank)",
        pdf_keywords=["fnb", "first national"],
        csv_header_patterns={
            "balance": [r"\bbalance\b"],
            "core": [r"\bamount\b.*\bdescription\b.*\bdate\b"],
        },
        date_formats=["%Y/%m/%d"],
        date_regex=r"^\d{4}/\d{2}/\d{2}$",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0
        if "balance" in headers_str:
            score += 0.3
        if "amount" in headers_str and "description" in headers_str and "date" in headers_str:
            score += 0.3
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{4}/\d{2}/\d{2}$", str(cell).strip()):
                        score += 0.3
                        break
                if score >= 0.8:
                    break
            for row in sample_rows[:3]:
                row_str = " ".join(str(c).lower() for c in row if c is not None)
                if "fnb" in row_str or "first national" in row_str:
                    score += 0.2
                    break
        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import FNBAdapter
        return FNBAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        """FNB PDF parsing delegates to existing table + OCR parsers.

        The heavy lifting for FNB is done inside pdf_to_csv_bytes because it
        needs page-level table iteration.  Return None so the main pipeline
        keeps its existing FNB handling.
        """
        return None  # handled inline in pdf_parser for now
