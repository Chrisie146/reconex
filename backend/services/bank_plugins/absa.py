"""
ABSA Bank plugin – wraps existing ABSAAdapter.
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class ABSAPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="absa",
        bank_name="ABSA Bank",
        pdf_keywords=["absa", "absacapital"],
        csv_header_patterns={
            "trans_date": [r"trans(action)?\s*date"],
            "debit_credit": [r"\bdebit\b", r"\bcredit\b"],
            "description": [r"description"],
        },
        date_formats=["%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"],
        date_regex=r"^\d{2}/\d{2}/\d{4}$",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0
        if re.search(r"trans(action)?\s*date|transaction\s*date", headers_str):
            score += 0.3
        if "debit" in headers_str and "credit" in headers_str:
            score += 0.2
        if re.search(r"description", headers_str):
            score += 0.1
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    cell_str = str(cell).strip()
                    if re.match(r"^202[0-9]{5}$", cell_str):
                        score += 0.4
                        break
                if score >= 0.7:
                    break
        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import ABSAAdapter
        return ABSAAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        from services.pdf_parser import _parse_absa_text
        parsed = _parse_absa_text(text, pdf_obj)
        return parsed or None
