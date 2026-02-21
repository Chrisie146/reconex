"""
Standard Bank plugin – wraps existing StandardBankAdapter.
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class StandardBankPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="standard_bank",
        bank_name="Standard Bank",
        pdf_keywords=["standard bank", "sbsa"],
        csv_header_patterns={
            "page": [r"\bpage\b"],
            "service_fee": [r"service\s*fee"],
            "core": [r"\bdebit\b.*\bcredit\b.*\bdate\b.*\bbalance\b"],
        },
        date_formats=["%Y%m%d"],
        date_regex=r"^\d{8}$",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0
        if "page" in headers_str:
            score += 0.3
        if "service fee" in headers_str:
            score += 0.2
        if re.search(r"\bdebit\b.*\bcredit\b.*\bdate\b.*\bbalance\b", headers_str):
            score += 0.3
        if sample_rows:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{8}$", str(cell).strip()):
                        score += 0.2
                        break
                if score > 0.9:
                    break
        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import StandardBankAdapter
        return StandardBankAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        from services.pdf_parser import (
            _parse_standard_bank_text,
            _parse_standard_bank_business_text,
        )
        import re as _re

        if statement_year is None:
            m = _re.search(r"Statement from.*?(\d{4})", text, _re.IGNORECASE)
            if m:
                statement_year = int(m.group(1))

        parsed = _parse_standard_bank_business_text(text, pdf_obj, statement_year)
        if parsed:
            return parsed
        parsed = _parse_standard_bank_text(text, pdf_obj)
        return parsed or None
