"""
Nedbank plugin – new bank support.

Nedbank CSV formats:
  1. Standard: Date, Description, Debit, Credit, Balance
     - Date format: DD/MM/YYYY or YYYY-MM-DD
  2. Online Banking export: Transaction Date, Value Date, Transaction Description,
     Debit Amount, Credit Amount, Balance
  3. Simple: Date, Description, Amount

Nedbank PDF:
  - Keywords: "nedbank", "nedgroup", "ned bank"
  - Tables with Date | Reference | Description | Debit | Credit | Balance
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class NedbankPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="nedbank",
        bank_name="Nedbank",
        pdf_keywords=["nedbank", "nedgroup", "ned bank"],
        csv_header_patterns={
            "nedbank_headers": [r"transaction\s*description", r"value\s*date"],
            "reference": [r"\breference\b"],
            "debit_credit": [r"\bdebit\b", r"\bcredit\b"],
        },
        date_formats=["%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d-%m-%Y"],
        date_regex=r"^\d{2}/\d{2}/\d{4}$",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0

        # Nedbank-specific signals
        if "transaction description" in headers_str:
            score += 0.3
        if "value date" in headers_str and "transaction date" in headers_str:
            score += 0.3
        if "reference" in headers_str:
            score += 0.1

        # Generic debit/credit structure
        if "debit" in headers_str and "credit" in headers_str:
            score += 0.15

        # Balance column (common but not unique)
        if "balance" in headers_str:
            score += 0.05

        # Content hint: "nedbank" anywhere in sample rows
        if sample_rows:
            for row in sample_rows[:3]:
                row_str = " ".join(str(c).lower() for c in row if c)
                if "nedbank" in row_str or "nedgroup" in row_str:
                    score += 0.3
                    break
            # Date format: DD/MM/YYYY
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{2}/\d{2}/\d{4}$", str(cell).strip()):
                        score += 0.1
                        break
                if score >= 0.8:
                    break

        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import NedbankAdapter
        return NedbankAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        """Parse Nedbank PDF statement text into rows."""
        rows: List[List[str]] = []

        # Nedbank PDF table rows typically:
        # DD/MM/YYYY  or  DD Mon YYYY  |  Reference  |  Description  |  Debit  |  Credit  |  Balance
        # We look for lines starting with a date pattern.
        date_pat = re.compile(
            r"^\s*(\d{2}[/\-]\d{2}[/\-]\d{4}|\d{2}\s+\w{3}\s+\d{4})"
        )
        amount_pat = re.compile(r"-?\d[\d\s,]*\.\d{2}")

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue

            m = date_pat.match(line)
            if not m:
                continue

            date_str = m.group(1).strip()
            rest = line[m.end():].strip()

            # Find amounts at the end of the line
            amounts = amount_pat.findall(rest)
            if not amounts:
                continue

            # Description is the text before the first amount
            first_amt_idx = rest.find(amounts[0])
            desc = rest[:first_amt_idx].strip()

            if not desc:
                desc = "(No description)"

            # Determine amount: if 2+ amounts, first is debit, second credit
            debit = 0.0
            credit = 0.0
            for i, amt_str in enumerate(amounts):
                val = float(amt_str.replace(" ", "").replace(",", ""))
                if i == 0 and len(amounts) >= 2:
                    debit = val
                elif i == 1:
                    credit = val
                elif len(amounts) == 1:
                    # Single amount – negative is debit, positive is credit
                    if val < 0:
                        debit = abs(val)
                    else:
                        credit = val

            amount = -debit if debit else credit
            if amount != 0:
                rows.append([date_str, desc.strip(" -|"), f"{amount:.2f}"])

        return rows if rows else None
