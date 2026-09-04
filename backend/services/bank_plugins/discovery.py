"""Discovery Bank statement plugin.

Discovery Bank's digital PDF statements use a transaction timeline with the
columns ``Date | Card no. | Type | Details | Amount``.  This plugin keeps the
format-specific extraction isolated so other Discovery statement layouts can
be added later without changing the shared PDF parser.
"""

import re
from datetime import datetime
from typing import List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class DiscoveryPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="discovery",
        bank_name="Discovery Bank",
        pdf_keywords=[
            "discovery bank limited",
            "discovery gold transaction account",
            "discovery gold card",
            "discovery bank",
        ],
        csv_header_patterns={
            "timeline": [r"\bcard\s*no\.?\b", r"\btype\b", r"\bdetails\b"],
            "amount": [r"\bamount\b"],
        },
        date_formats=["%d %b %Y", "%d/%m/%Y", "%Y-%m-%d"],
        date_regex=r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$",
    )

    def matches_pdf_text(self, text_lower: str) -> bool:
        """Require Discovery branding, avoiding transaction-description false positives."""
        return (
            "discovery bank limited" in text_lower
            or "discovery gold transaction account" in text_lower
            or "discovery gold card" in text_lower
            or "discovery bank" in text_lower and "transaction timeline" in text_lower
        )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0
        if "card no" in headers_str or "card no." in headers_str:
            score += 0.35
        if "type" in headers_str and "details" in headers_str:
            score += 0.25
        if "amount" in headers_str:
            score += 0.15
        if sample_rows:
            for row in sample_rows[:3]:
                row_str = " ".join(str(cell).lower() for cell in row if cell is not None)
                if "discovery" in row_str:
                    score += 0.25
                    break
        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import DiscoveryAdapter
        return DiscoveryAdapter()

    def parse_pdf(self, text: str, pdf_obj=None, statement_year: Optional[int] = None):
        """Extract dated transaction rows from a Discovery transaction timeline."""
        rows: List[List[str]] = []
        date_re = re.compile(r"^\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})\b")
        amount_re = re.compile(r"(?:[-+]\s*)?R\s*[\d\s,]+\.\d{2}")

        for raw_line in text.splitlines():
            line = " ".join(raw_line.split())
            match = date_re.match(line)
            if not match:
                continue

            rest = line[match.end():].strip()
            amount_matches = list(amount_re.finditer(rest))
            if not amount_matches:
                continue

            # The final currency value is the timeline amount.  Any preceding
            # values are part of the description in other layouts.
            amount_text = amount_matches[-1].group(0)
            amount_clean = re.sub(r"[^0-9.+-]", "", amount_text)
            try:
                amount = float(amount_clean)
            except ValueError:
                continue
            if amount == 0:
                continue

            description = rest[:amount_matches[-1].start()].strip(" -|")
            if not description or description.lower() in {"opening balance", "closing balance"}:
                continue

            day, month, year = match.groups()
            date_str = f"{year}-{datetime.strptime(month, '%b').month:02d}-{int(day):02d}"
            rows.append([date_str, description, f"{amount:.2f}"])

        return rows or None
