"""
Investec Bank plugin – new bank support.

Investec CSV formats:
  1. Online export: Date, Description, Debit, Credit, Balance
     - Date format: DD/MM/YYYY
  2. Programmable Banking API: Posted Date, Description, Debit, Credit, Running Balance
  3. Excel export: Transaction Date, Value Date, Description, Debit, Credit
     - Date format: YYYY/MM/DD or DD/MM/YYYY

Investec PDF:
  - Keywords: "investec"
  - Layout: Date | Description | Debit | Credit | Balance
  - Often uses DD Mon YYYY dates
"""

import re
from typing import Any, List, Optional

from services.bank_plugins.registry import BankPlugin, BankPluginConfig


class InvestecPlugin(BankPlugin):
    config = BankPluginConfig(
        bank_id="investec",
        bank_name="Investec Bank",
        pdf_keywords=["investec"],
        csv_header_patterns={
            "posted_date": [r"posted\s*date"],
            "running_balance": [r"running\s*balance"],
            "debit_credit": [r"\bdebit\b", r"\bcredit\b"],
        },
        date_formats=["%d/%m/%Y", "%Y/%m/%d", "%d %b %Y", "%Y-%m-%d"],
        date_regex=r"^\d{2}/\d{2}/\d{4}$",
    )

    def score_csv(self, headers_str, headers, sample_rows=None):
        score = 0.0

        # Investec-specific headers
        if "posted date" in headers_str or "posting date" in headers_str:
            score += 0.2
        if "running balance" in headers_str:
            score += 0.25

        # Generic structure signals
        if "debit" in headers_str and "credit" in headers_str:
            score += 0.15
        if "description" in headers_str:
            score += 0.05
        if "value date" in headers_str:
            score += 0.1

        # Content hint
        if sample_rows:
            for row in sample_rows[:3]:
                row_str = " ".join(str(c).lower() for c in row if c)
                if "investec" in row_str:
                    score += 0.3
                    break
            # DD/MM/YYYY date format
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(r"^\d{2}/\d{2}/\d{4}$", str(cell).strip()):
                        score += 0.1
                        break

        return min(score, 1.0)

    def get_adapter(self):
        from services.bank_adapters import InvestecAdapter
        return InvestecAdapter()

    def parse_pdf(self, text, pdf_obj=None, statement_year=None):
        """Parse Investec PDF statement text into rows."""
        rows: List[List[str]] = []

        # Investec PDF: lines starting with DD Mon YYYY or DD/MM/YYYY
        date_pat = re.compile(
            r"^\s*(\d{2}\s+\w{3}\s+\d{4}|\d{2}[/\-]\d{2}[/\-]\d{4})"
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

            amounts = amount_pat.findall(rest)
            if not amounts:
                continue

            first_amt_idx = rest.find(amounts[0])
            desc = rest[:first_amt_idx].strip()
            if not desc:
                desc = "(No description)"

            # Investec typically has Debit | Credit | Balance cols
            debit = 0.0
            credit = 0.0
            for i, amt_str in enumerate(amounts):
                val = float(amt_str.replace(" ", "").replace(",", ""))
                if i == 0 and len(amounts) >= 2:
                    debit = val
                elif i == 1:
                    credit = val
                elif len(amounts) == 1:
                    if val < 0:
                        debit = abs(val)
                    else:
                        credit = val

            amount = -debit if debit else credit
            if amount != 0:
                rows.append([date_str, desc.strip(" -|"), f"{amount:.2f}"])

        return rows if rows else None
