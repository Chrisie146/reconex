"""
Capitec Bank plugin – wraps existing CapitecAdapter.
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class CapitecPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="capitec",
        bank_name="Capitec Bank",
        pdf_keywords=["capitec"],
        csv_header_patterns={
            "money": [r"money\s*in", r"money\s*out"],
            "posting_date": [r"posting\s*date", r"transaction\s*date"],
            "core": [r"\bdate\b.*\bdescription\b.*\bamount\b"],
        },
        date_formats=["%Y-%m-%d", "%d/%m/%Y"],
        date_regex=r"^\d{4}-\d{2}-\d{2}",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0
        if "date" in headers_str and "description" in headers_str and "amount" in headers_str:
            score += 0.4
        if len(headers) == 3 and "amount" in headers_str:
            score += 0.2
        if "money" in headers_str and ("money in" in headers_str or "money out" in headers_str):
            score += 0.5
        if "posting date" in headers_str or "transaction date" in headers_str:
            score += 0.2
        if "account" in headers_str and "balance" in headers_str:
            score += 0.1
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{4}-\d{2}-\d{2}", str(cell).strip()):
                        score += 0.2
                        break
                if score > 0.7:
                    break
        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import CapitecAdapter
        return CapitecAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        """Capitec PDF parsing is handled inline in pdf_to_csv_bytes."""
        return None  # handled inline in pdf_parser for now
