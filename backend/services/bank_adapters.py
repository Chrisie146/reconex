"""
Bank Adapters - Normalize different bank statement formats to standard format
Each adapter converts bank-specific CSV format to canonical format:
  {Date, Description, Amount}
  where Amount: negative=expense, positive=income
"""

import re
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

# Try to import pandas, create a stub if not available
try:
    import pandas as pd
except ImportError:
    # Stub pandas to prevent import errors
    class PandasStub:
        DataFrame = dict
        Index = list
        def notna(self, val):
            return val is not None and val == val
        def isna(self, val):
            return val is None or val != val
        class NA:
            pass
        NA = None
    pd = PandasStub()

from .balance_validator import BalanceValidator


class BankAdapter(ABC):
    """Base class for bank adapters"""

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize bank-specific DataFrame to standard format

        Args:
            df: DataFrame with bank-specific columns

        Returns:
            DataFrame with columns: Date, Description, Amount
              - Date: YYYY-MM-DD format
              - Description: Transaction description
              - Amount: Negative for expenses, positive for income
        """
        pass

    @staticmethod
    def parse_amount(amount_str: str) -> float:
        """Parse amount string to float, handling various formats"""
        if not amount_str or not isinstance(amount_str, str):
            return 0.0

        s = amount_str.strip()
        if not s:
            return 0.0

        # Remove currency symbols
        s = re.sub(r"[R$€£]", "", s)

        # Handle parentheses as negative
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            s = s[1:-1]

        # Remove thousand separators and normalize decimal
        s = s.replace(",", ".")
        s = re.sub(r"[\s_]", "", s)

        try:
            value = float(s)
            return -value if is_negative else value
        except ValueError:
            return 0.0

    @staticmethod
    def parse_date(date_str: str, formats: List[str]) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if not date_str:
            return ""

        date_str = str(date_str).strip()

        # Try each format
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                continue

        # Fallback: return as-is
        return date_str


class StandardBankAdapter(BankAdapter):
    """
    Adapter for Standard Bank statement format
    
    Supports multiple Standard Bank formats:
    1. Table format: Page, Details, Service Fee, Debit, Credit, Date, Balance
    2. OCR format: date, description, amount (already normalized)
    3. Raw text format: Space-separated columns

    - Date format: YYYYMMDD
    - Debit: Negative amounts (expenses)
    - Credit: Positive amounts (income)
    - Multi-line descriptions (merchant spans 2 lines sometimes)
    """

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main entry point - detects format and routes to appropriate handler"""
        col_map = self._map_columns(df.columns)
        format_type = self._detect_format(col_map, df)
        
        print(f"[StandardBankAdapter] Detected format: {format_type}")
        
        if format_type == "ocr":
            return self._normalize_ocr_format(df)
        elif format_type == "raw_text":
            return self._parse_raw_text(df)
        else:
            return self._normalize_table_format(df, col_map)
    
    def _detect_format(self, col_map: dict, df: pd.DataFrame) -> str:
        """
        Detect which Standard Bank format we're dealing with
        
        Returns:
            "ocr" - Already normalized from PDF extraction (date, description, amount)
            "table" - Traditional table with debit/credit columns
            "raw_text" - Raw text that needs line-by-line parsing
        """
        columns_lower = [str(c).lower() for c in df.columns]
        
        # Check for OCR format (already normalized)
        if "date" in columns_lower and "amount" in columns_lower and "description" in columns_lower:
            return "ocr"
        
        # Check for raw text format
        if not col_map.get("date") or not col_map.get("details"):
            return "raw_text"
        
        # Default to table format
        return "table"
    
    def _normalize_ocr_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle OCR-extracted format (already normalized)"""
        df_out = df.copy()
        df_out.columns = [str(c).lower() for c in df_out.columns]
        
        # Parse dates
        df_out["date"] = df_out["date"].apply(
            lambda x: self.parse_date(str(x), ["%Y%m%d", "%Y-%m-%d"]) if pd.notna(x) else ""
        )
        
        # Ensure amounts are numeric
        df_out["amount"] = df_out["amount"].apply(
            lambda x: self.parse_amount(str(x)) if pd.notna(x) else 0.0
        )
        
        # Allow blank descriptions
        df_out["description"] = df_out["description"].fillna("(No description)")
        
        return df_out[["date", "description", "amount"]].rename(
            columns={"date": "Date", "description": "Description", "amount": "Amount"}
        )
    
    def _normalize_table_format(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """Handle traditional table format with debit/credit columns"""
        normalized_rows = []
        i = 0
        while i < len(df):
            row = df.iloc[i]

            # Check if this is a transaction row (has Date column)
            date_val = row.get(col_map["date"])
            if pd.isna(date_val) or str(date_val).strip() == "":
                i += 1
                continue

            # Parse transaction row
            description = self._combine_description(df, i, col_map)
            date_normalized = self.parse_date(str(date_val).strip(), ["%Y%m%d"])

            # Get debit or credit
            debit = self.parse_amount(str(row.get(col_map["debit"], 0)))
            credit = self.parse_amount(str(row.get(col_map["credit"], 0)))

            # Amount: debit is negative (expense), credit is positive (income)
            amount = -debit if debit != 0 else credit

            # Allow blank descriptions
            if not description:
                description = "(No description)"

            if date_normalized:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

            i += 1

        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
        return result_df[["Date", "Description", "Amount"]]

    def _parse_raw_text(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Parse Standard Bank raw text format
        
        Standard format is space-separated columns:
        Page Details Service_Fee Debit Credit Date Balance
        With optional merchant continuation line following
        """
        import re
        
        normalized_rows = []
        
        # If we have a single text column, split on whitespace
        if len(df.columns) == 1:
            # This is raw text, split into rows
            col_name = df.columns[0]
            lines = []
            for idx, row in df.iterrows():
                text = str(row[col_name]).strip()
                if text:
                    lines.append(text)
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Try to match transaction line pattern
                # Pattern: PAGE NUMBER, DESCRIPTION, AMOUNTS, DATE (YYYYMMDD), BALANCE
                # e.g.: "10 ELECTRONIC BANKING TRANSFER TO 0.00 -92.71 0.00 20240222 6,536,806.66"
                
                # Check if line contains a date in YYYYMMDD format
                date_match = re.search(r'\b(\d{8})\b', line)
                if not date_match:
                    i += 1
                    continue
                
                date_str = date_match.group(1)
                
                # Find amounts (negative for debit, positive for credit)
                # Look for amounts before the date
                amount_pattern = r'-[\d,]+\.\d{2}|[\d,]+\.\d{2}'
                amounts = re.findall(amount_pattern, line[:date_match.start()])
                
                if len(amounts) >= 2:
                    # Typically: Service Fee, Debit, Credit
                    # Use the last two (Debit, Credit)
                    debit_str = amounts[-2]
                    credit_str = amounts[-1]
                    
                    debit = self.parse_amount(debit_str)
                    credit = self.parse_amount(credit_str)
                    
                    # Extract description: everything after PAGE number and before amounts
                    # Find page number (first number in line)
                    page_match = re.match(r'^(\d+)\s+(.+?)(?:\s+[\d,]+\.\d{2})', line)
                    if page_match:
                        description = page_match.group(2).strip()
                        
                        # Check if next line is a continuation (no date and no amounts)
                        if i + 1 < len(lines):
                            next_line = lines[i + 1]
                            if not re.search(r'\b\d{8}\b', next_line) and not re.search(amount_pattern, next_line):
                                # This is a continuation line
                                description = f"{description} {next_line.strip()}"
                                i += 1
                        
                        # Amount logic: debit is negative, credit is positive
                        amount = -debit if debit != 0 else credit
                        
                        date_normalized = self.parse_date(date_str, ["%Y%m%d"])
                        
                        if description and date_normalized:
                            normalized_rows.append({
                                "Date": date_normalized,
                                "Description": description,
                                "Amount": amount,
                            })
                
                i += 1
        
        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            result_df = pd.DataFrame(columns=["Date", "Description", "Amount"])
        else:
            result_df = result_df[["Date", "Description", "Amount"]]
        return result_df

    def _map_columns(self, columns: pd.Index) -> Dict[str, str]:
        """Map bank columns to canonical names"""
        col_map = {}
        columns_lower = [str(c).lower() for c in columns]

        for canonical, patterns in {
            "page": [r"page"],
            "details": [r"details", r"description"],
            "service_fee": [r"service\s*fee"],
            "debit": [r"debit"],
            "credit": [r"credit"],
            "date": [r"date"],
            "balance": [r"balance"],
        }.items():
            for i, col in enumerate(columns_lower):
                for pattern in patterns:
                    if re.search(pattern, col):
                        col_map[canonical] = columns[i]
                        break
                if canonical in col_map:
                    break

        return col_map

    def _combine_description(self, df: pd.DataFrame, row_idx: int, col_map: Dict[str, str]) -> str:
        """
        Combine description from transaction row and potential next row (continuation)
        Standard Bank: merchant name can span 2 rows
        """
        current_row = df.iloc[row_idx]
        details = str(current_row.get(col_map["details"], "")).strip()

        # Check if next row is a continuation (no date)
        if row_idx + 1 < len(df):
            next_row = df.iloc[row_idx + 1]
            next_date = next_row.get(col_map["date"])

            if pd.isna(next_date) or str(next_date).strip() == "":
                # This is a continuation row
                continuation = str(next_row.get(col_map["details"], "")).strip()
                if continuation:
                    details = f"{details} {continuation}"

        return details


class ABSAAdapter(BankAdapter):
    """
    Adapter for ABSA Bank statement format
    
    Supports multiple ABSA formats:
    1. OCR format: date, description, amount (from scanned PDFs)
    2. Table format: Trans Date, Description, Debit, Credit
    
    - Date format: DD/MM/YYYY or YYYYMMDD (OCR)
    - Debit: Expenses (shown as negative in output)
    - Credit: Income (shown as positive in output)
    """

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main entry point - detects format and routes to appropriate handler"""
        col_map = self._map_columns(df.columns)
        format_type = self._detect_format(col_map, df)
        
        print(f"[ABSAAdapter] Detected format: {format_type}")
        
        if format_type == "ocr":
            return self._normalize_ocr_format(df)
        else:
            return self._normalize_table_format(df, col_map)
    
    def _detect_format(self, col_map: dict, df: pd.DataFrame) -> str:
        """
        Detect which ABSA format we're dealing with
        
        Returns:
            "ocr" - Already normalized from OCR extraction (date, description, amount)
            "table" - Traditional format with debit/credit columns
        """
        columns_lower = [str(c).lower() for c in df.columns]
        
        # Check for OCR format (already normalized)
        if "date" in columns_lower and "amount" in columns_lower:
            return "ocr"
        
        # Default to table format
        return "table"
    
    def _normalize_ocr_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle OCR-extracted format"""
        df_out = df.copy()
        df_out.columns = [str(c).lower() for c in df_out.columns]
        
        # Filter out rows with no date or amount = 0
        df_out = df_out[df_out["date"].notna()]
        df_out = df_out[df_out["date"].astype(str).str.strip() != ""]
        
        # Parse dates (can be YYYYMMDD from OCR or other formats)
        df_out["date"] = df_out["date"].apply(
            lambda x: self.parse_date(str(x), ["%Y%m%d", "%d/%m/%Y", "%Y-%m-%d"]) if pd.notna(x) else ""
        )
        
        # Parse amounts
        df_out["amount"] = df_out["amount"].apply(
            lambda x: self.parse_amount(str(x)) if pd.notna(x) else 0.0
        )
        
        # Filter out zero amounts
        df_out = df_out[df_out["amount"] != 0]
        
        # Allow blank descriptions
        df_out["description"] = df_out["description"].fillna("(No description)")
        
        # Return in standard format
        if len(df_out) > 0:
            return df_out[["date", "description", "amount"]].rename(
                columns={"date": "Date", "description": "Description", "amount": "Amount"}
            )
        else:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
    
    def _normalize_table_format(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """Handle traditional table format with debit/credit columns"""
        normalized_rows = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            desc_val = row.get(col_map.get("description"))

            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            # ABSA dates can be: DD/MM/YYYY, YYYY-MM-DD, or YYYYMMDD (from OCR parser)
            date_normalized = self.parse_date(str(date_val).strip(), ["%d/%m/%Y", "%Y-%m-%d", "%Y%m%d"])
            description = str(desc_val).strip() if desc_val else "(No description)"

            # Try to get amount from various possible column names
            amount = 0.0
            
            # First try: direct amount column
            if "amount" in col_map:
                amount_val = row.get(col_map["amount"])
                if amount_val is not None and not pd.isna(amount_val):
                    amount = self.parse_amount(str(amount_val))
            
            # Second try: debit/credit columns
            if amount == 0.0:
                debit_col = col_map.get("debit")
                credit_col = col_map.get("credit")
                
                debit = 0.0
                credit = 0.0
                
                if debit_col:
                    debit_val = row.get(debit_col)
                    if debit_val is not None and not pd.isna(debit_val):
                        debit = self.parse_amount(str(debit_val))
                
                if credit_col:
                    credit_val = row.get(credit_col)
                    if credit_val is not None and not pd.isna(credit_val):
                        credit = self.parse_amount(str(credit_val))
                
                if debit != 0 or credit != 0:
                    amount = -debit if debit != 0 else credit

            if date_normalized and amount != 0:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

        result_df = pd.DataFrame(normalized_rows)
        if len(result_df) > 0:
            result_df = result_df[["Date", "Description", "Amount"]]
        else:
            result_df = pd.DataFrame(columns=["Date", "Description", "Amount"])
        return result_df

    def _map_columns(self, columns: pd.Index) -> Dict[str, str]:
        """Map ABSA columns to canonical names"""
        col_map = {}
        columns_lower = [str(c).lower() for c in columns]

        for canonical, patterns in {
            "date": [r"trans(action)?\s*date", r"date"],
            "description": [r"description", r"narration"],
            "debit": [r"debit"],
            "credit": [r"credit"],
        }.items():
            for i, col in enumerate(columns_lower):
                for pattern in patterns:
                    if re.search(pattern, col):
                        col_map[canonical] = columns[i]
                        break
                if canonical in col_map:
                    break

        return col_map


class CapitecAdapter(BankAdapter):
    """
    Adapter for Capitec Bank statement format
    
    Supports multiple Capitec formats:
    1. Money In/Out format: Date, Description, Money In, Money Out, Fee (new CSV format)
    2. Simple format: Date, Description, Amount (single column with +/- signs)
    3. Table format: Date, Description, Debit, Credit
    
    - Date format: YYYY-MM-DD or DD/MM/YYYY
    - Amount: Single column (negative=expense, positive=income)
    
    The Money In/Money Out format is typically from native Capitec CSV exports
    """

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Main entry point - detects format and routes to appropriate handler"""
        col_map = self._map_columns(df.columns)
        format_type = self._detect_format(col_map, df)
        
        print(f"[CapitecAdapter] Detected format: {format_type}")
        
        if format_type == "money_in_out":
            return self._normalize_money_in_out_format(df, col_map)
        elif format_type == "table":
            return self._normalize_table_format(df, col_map)
        else:
            return self._normalize_simple_format(df, col_map)
    
    def _detect_format(self, col_map: dict, df: pd.DataFrame) -> str:
        """
        Detect which Capitec format we're dealing with
        
        Returns:
            "money_in_out" - Separate Money In/Money Out columns (native CSV export)
            "table" - Separate debit/credit columns
            "simple" - Single amount column with +/- signs
        """
        # Check if we have Money In/Money Out columns (new format)
        has_money_in_out = col_map.get("money_in") or col_map.get("money_out")
        
        if has_money_in_out:
            return "money_in_out"
        
        # Check if we have debit/credit columns
        has_debit_credit = col_map.get("debit") or col_map.get("credit")
        
        if has_debit_credit:
            return "table"
        
        return "simple"
    
    def _normalize_money_in_out_format(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """Handle Money In/Money Out format (native Capitec CSV export)"""
        normalized_rows = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            desc_val = row.get(col_map.get("description"))

            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(str(date_val).strip(), ["%Y-%m-%d", "%d/%m/%Y"])
            description = str(desc_val).strip() if desc_val else "(No description)"

            # Parse Money In, Money Out, and Fee (all already have correct signs in the CSV)
            money_in_val = row.get(col_map.get("money_in", ""))
            money_out_val = row.get(col_map.get("money_out", ""))
            fee_val = row.get(col_map.get("fee", ""))
            
            money_in = self.parse_amount(str(money_in_val)) if money_in_val and pd.notna(money_in_val) else 0.0
            money_out = self.parse_amount(str(money_out_val)) if money_out_val and pd.notna(money_out_val) else 0.0
            fee = self.parse_amount(str(fee_val)) if fee_val and pd.notna(fee_val) else 0.0
            
            # Calculate net amount: money_in is positive income, money_out and fee are already negative
            amount = money_in + money_out + fee

            if date_normalized:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
        return result_df[["Date", "Description", "Amount"]]

    def _normalize_simple_format(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """Handle simple format with single amount column"""
        normalized_rows = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            desc_val = row.get(col_map.get("description"))
            amount_val = row.get(col_map.get("amount"))

            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(str(date_val).strip(), ["%Y-%m-%d", "%d/%m/%Y"])
            description = str(desc_val).strip() if desc_val else "(No description)"
            amount = self.parse_amount(str(amount_val)) if amount_val else 0.0

            if date_normalized:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
        return result_df[["Date", "Description", "Amount"]]
    
    def _normalize_table_format(self, df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
        """Handle table format with debit/credit columns"""
        normalized_rows = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            desc_val = row.get(col_map.get("description"))

            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(str(date_val).strip(), ["%Y-%m-%d", "%d/%m/%Y"])
            description = str(desc_val).strip() if desc_val else "(No description)"

            # Parse debit/credit
            debit_val = row.get(col_map.get("debit", ""))
            credit_val = row.get(col_map.get("credit", ""))
            
            debit = self.parse_amount(str(debit_val)) if debit_val and pd.notna(debit_val) else 0.0
            credit = self.parse_amount(str(credit_val)) if credit_val and pd.notna(credit_val) else 0.0
            
            # Amount: debit is negative (expense), credit is positive (income)
            amount = -debit if debit != 0 else credit

            if date_normalized:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
        return result_df[["Date", "Description", "Amount"]]

    def _map_columns(self, columns: pd.Index) -> Dict[str, str]:
        """Map Capitec columns to canonical names"""
        col_map = {}
        columns_lower = [str(c).lower() for c in columns]

        for canonical, patterns in {
            "date": [r"posting\s*date", r"transaction\s*date", r"date"],
            "description": [r"description", r"narrative"],
            "amount": [r"amount", r"transaction\s*amount"],
            "money_in": [r"money\s*in"],
            "money_out": [r"money\s*out"],
            "debit": [r"debit"],
            "credit": [r"credit"],
            "fee": [r"fee"],
        }.items():
            for i, col in enumerate(columns_lower):
                for pattern in patterns:
                    if re.search(pattern, col):
                        col_map[canonical] = columns[i]
                        break
                if canonical in col_map:
                    break

        return col_map


class GenericAdapter(BankAdapter):
    """
    Fallback adapter for unknown/generic bank formats

    Expects minimal structure: Date, Description, Amount (or Debit/Credit)
    """

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize generic format (pass-through with minimal cleanup)"""

        col_map = self._map_columns(df.columns)

        normalized_rows = []
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            desc_val = row.get(col_map.get("description"))

            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            # Try multiple date formats
            date_normalized = self.parse_date(
                str(date_val).strip(),
                ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"],
            )

            description = str(desc_val).strip() if desc_val else ""

            # Try to get amount from various columns
            amount = 0.0
            if "amount" in col_map:
                amount_str = str(row.get(col_map["amount"], 0))
                # Use FNB-aware parse_amount_fnb for better handling
                amount = self.parse_amount_fnb(amount_str)
            else:
                # Try debit/credit
                debit = self.parse_amount_fnb(str(row.get(col_map.get("debit", ""), 0)))
                credit = self.parse_amount_fnb(str(row.get(col_map.get("credit", ""), 0)))
                amount = -debit if debit != 0 else credit

            if description and date_normalized:
                normalized_rows.append(
                    {
                        "Date": date_normalized,
                        "Description": description,
                        "Amount": amount,
                    }
                )

        result_df = pd.DataFrame(normalized_rows)
        result_df = result_df[["Date", "Description", "Amount"]]
        return result_df
    
    @staticmethod
    def parse_amount_fnb(amount_str: str) -> float:
        """Parse amount with FNB-specific formats (K/C suffixes, commas)"""
        if not amount_str or not isinstance(amount_str, str):
            return 0.0

        s = amount_str.strip()
        if not s or s.lower() in ['nan', 'none', '']:
            return 0.0

        # FNB format: amounts ending with 'K' (Krediet/Credit) are income (positive)
        # Amounts without suffix or with 'D' are expenses (negative)
        # Example: "109,250.00K" = +109250.00, "649.90" = -649.90
        is_credit = False
        s_upper = s.upper()
        if s_upper.endswith(('K', 'KT', 'KREDIET', 'C', 'CR', 'CREDIT')):
            is_credit = True
            # Remove suffix
            for suffix in ['KREDIET', 'CREDIT', 'KT', 'CR', 'K', 'C']:
                if s_upper.endswith(suffix):
                    s = s[:-len(suffix)].strip()
                    break

        # Remove currency symbols
        s = re.sub(r"[R$€£]", "", s)

        # Handle parentheses as negative (overrides credit suffix)
        is_negative = False
        if s.startswith("(") and s.endswith(")"):
            is_negative = True
            is_credit = False
            s = s[1:-1]

        # Remove thousand separators (commas) and spaces
        s = s.replace(",", "")
        s = s.replace(" ", "")

        try:
            value = float(s)
            # FNB convention: credits are positive (income), debits are negative (expenses)
            if is_negative:
                return -abs(value)
            elif is_credit:
                return abs(value)  # Income
            else:
                return -abs(value)  # Expense (default for amounts without suffix)
        except ValueError:
            return 0.0

    def _map_columns(self, columns: pd.Index) -> Dict[str, str]:
        """Map generic columns to canonical names"""
        col_map = {}
        columns_lower = [str(c).lower() for c in columns]

        for canonical, patterns in {
            "date": [r"date"],
            "description": [r"description", r"narrative", r"detail"],
            "amount": [r"amount"],
            "debit": [r"debit"],
            "credit": [r"credit"],
        }.items():
            for i, col in enumerate(columns_lower):
                for pattern in patterns:
                    if re.search(pattern, col):
                        col_map[canonical] = columns[i]
                        break
                if canonical in col_map:
                    break

        return col_map


class FNBAdapter(BankAdapter):
    """
    Adapter for FNB CSV exports (Account Transaction History)
    
    Supports multiple FNB formats:
    1. Scanned PDFs (OCR): date, description, amount (with 'K' suffix for credits)
    2. Table-based PDFs: date, description, debit, credit columns
    
    Common columns: Date, Amount, Balance, Description
    - Dates: YYYY/MM/DD
    - Amounts: signed numbers (negative debits, positive credits)
    - Balance: running balance (used to infer missing amount or sign)
    """

    def normalize(self, df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
        """
        Main entry point - detects format and routes to appropriate handler
        """
        col_map = self._map_columns(df.columns)
        format_type = self._detect_format(col_map, df)
        
        print(f"[FNBAdapter] Detected format: {format_type}")
        
        if format_type == "table":
            return self._normalize_table_format(df, col_map, strict)
        elif format_type == "csv":
            return self._normalize_csv_format(df, col_map, strict)
        else:  # "ocr"
            return self._normalize_scanned_format(df, col_map, strict)
    
    def _detect_format(self, col_map: dict, df: pd.DataFrame) -> str:
        """
        Detect which FNB format we're dealing with
        
        Returns:
            "table" - has separate debit/credit columns
            "csv" - direct CSV export with signed amounts
            "ocr" - OCR-parsed format with unsigned amounts and C/K suffixes
        """
        # Check if we have debit/credit columns
        has_debit_credit = col_map.get("debit") or col_map.get("credit")
        
        if has_debit_credit:
            return "table"
        
        # Detect CSV vs OCR by examining amount column
        if col_map.get("amount"):
            sample_amounts = df[col_map["amount"]].head(20).astype(str)
            
            # Count signed amounts (CSV format) vs amounts with C/K suffix (OCR format)
            has_minus = False
            has_plus = False
            has_credit_suffix = False
            
            for val in sample_amounts:
                if pd.isna(val) or not val.strip():
                    continue
                val_str = str(val).strip().upper()
                
                # Check for minus sign
                if val_str.startswith('-'):
                    has_minus = True
                # Check for plus sign
                if val_str.startswith('+'):
                    has_plus = True
                # Check for credit suffixes (C, K, Cr, Credit, Krediet, Kt)
                if any(suffix in val_str for suffix in ['C', 'K', 'CR', 'CREDIT', 'KREDIET', 'KT']):
                    has_credit_suffix = True
            
            # If we see minus or plus signs, it's CSV format with signed amounts
            if has_minus or has_plus:
                return "csv"
            
            # If we see credit suffixes, it's OCR format
            if has_credit_suffix:
                return "ocr"
        
        # Default to CSV format (most common for direct exports)
        return "csv"
    
    def _normalize_table_format(self, df: pd.DataFrame, col_map: dict, strict: bool) -> pd.DataFrame:
        """
        Handle table-based PDFs with separate debit/credit columns
        """
        transactions_for_validation = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(
                str(date_val).strip(),
                ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"],
            )

            desc_val = row.get(col_map.get("description"))
            description = str(desc_val).strip() if pd.notna(desc_val) else ""
            if not description:
                description = self._infer_description(row, col_map)

            # Parse debit/credit columns
            debit_val = row.get(col_map.get("debit", ""))
            credit_val = row.get(col_map.get("credit", ""))
            
            debit = self.parse_amount(str(debit_val)) if debit_val and pd.notna(debit_val) else 0.0
            credit = self.parse_amount(str(credit_val)) if credit_val and pd.notna(credit_val) else 0.0
            
            # Amount: debit is negative (expense), credit is positive (income)
            amount = -debit if debit != 0 else credit

            balance_val = row.get(col_map.get("balance"))
            balance = self.parse_balance(balance_val)

            transactions_for_validation.append({
                "date": date_normalized,
                "description": description,
                "amount": amount,
                "debit": debit,
                "credit": credit,
                "balance": balance
            })

        return self._finalize_transactions(transactions_for_validation, strict)
    
    def _normalize_csv_format(self, df: pd.DataFrame, col_map: dict, strict: bool) -> pd.DataFrame:
        """
        Handle direct CSV exports with signed amounts (positive = income, negative = expense)
        """
        transactions_for_validation = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(
                str(date_val).strip(),
                ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"],
            )

            desc_val = row.get(col_map.get("description"))
            description = str(desc_val).strip() if pd.notna(desc_val) else ""
            if not description:
                description = self._infer_description(row, col_map)

            # Parse signed amount (CSV format: positive = income, negative = expense)
            amount_str = str(row.get(col_map.get("amount", ""), "")).strip()
            amount = self.parse_amount_csv(amount_str)

            balance_val = row.get(col_map.get("balance"))
            balance = self.parse_balance(balance_val)

            transactions_for_validation.append({
                "date": date_normalized,
                "description": description,
                "amount": amount,
                "debit": None,
                "credit": None,
                "balance": balance
            })

        return self._finalize_transactions(transactions_for_validation, strict)
    
    def _normalize_scanned_format(self, df: pd.DataFrame, col_map: dict, strict: bool) -> pd.DataFrame:
        """
        Handle scanned PDFs with amount column (K or C suffix for credits)
        OCR Format: unsigned amounts with C/K suffix for credits, no suffix for debits
        """
        transactions_for_validation = []
        
        for idx, row in df.iterrows():
            date_val = row.get(col_map.get("date"))
            if pd.isna(date_val) or str(date_val).strip() == "":
                continue

            date_normalized = self.parse_date(
                str(date_val).strip(),
                ["%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y", "%Y%m%d"],
            )

            desc_val = row.get(col_map.get("description"))
            description = str(desc_val).strip() if pd.notna(desc_val) else ""
            if not description:
                description = self._infer_description(row, col_map)

            # OCR Format: use parse_amount_ocr for unsigned amounts with C/K suffix handling
            amount_str = str(row.get(col_map.get("amount", ""), "")).strip()
            amount = self.parse_amount_ocr(amount_str)

            balance_val = row.get(col_map.get("balance"))
            balance = self.parse_balance(balance_val)

            transactions_for_validation.append({
                "date": date_normalized,
                "description": description,
                "amount": amount,
                "debit": None,
                "credit": None,
                "balance": balance
            })

        return self._finalize_transactions(transactions_for_validation, strict)
    
    def _finalize_transactions(self, transactions_for_validation: list, strict: bool) -> pd.DataFrame:
        """
        Common finalization logic - balance validation and result formatting
        """
        # Apply balance validation (non-strict by default for production)
        validated, summary = BalanceValidator.validate_transactions(transactions_for_validation, strict=strict)
        
        # Build normalized rows with corrected amounts (if strict) or validation metadata (if not strict)
        normalized_rows = []
        for txn in validated:
            # Include transactions with blank descriptions (e.g., Apple payment fees)
            if txn["date"]:
                # Use corrected amount only if strict mode
                final_amount = txn["amount"]  # Default to original amount
                if strict and txn.get("corrected_amount") is not None:
                    final_amount = txn.get("corrected_amount")
                
                row_data = {
                    "Date": txn["date"],
                    "Description": txn["description"] or "",  # Allow blank descriptions
                    "Amount": final_amount,
                }
                
                # Always include validation metadata
                row_data["balance_verified"] = txn.get("balance_verified")
                row_data["balance_difference"] = txn.get("balance_difference")
                row_data["validation_message"] = txn.get("validation_message", "")
                
                normalized_rows.append(row_data)

        result_df = pd.DataFrame(normalized_rows)
        if result_df.empty:
            return pd.DataFrame(columns=["Date", "Description", "Amount"])
        
        # Return standard columns, keep validation columns for internal use
        return result_df[["Date", "Description", "Amount", "balance_verified", "balance_difference", "validation_message"]]

    @staticmethod
    def parse_amount_signed(amount_str: str) -> float:
        """Parse signed amount with optional FNB credit suffixes."""
        if not amount_str or not isinstance(amount_str, str):
            return 0.0

        s = amount_str.strip()
        if not s or s.lower() in ["nan", "none", ""]:
            return 0.0

        # Track if the original string had a minus sign (before removing anything)
        has_minus_sign = s.startswith("-")

        s_upper = s.upper()
        credit_suffix = False
        if s_upper.endswith(("K", "KT", "KREDIET", "C", "CR", "CREDIT")):
            credit_suffix = True
            for suffix in ["KREDIET", "CREDIT", "KT", "CR", "K", "C"]:
                if s_upper.endswith(suffix):
                    s = s[: -len(suffix)].strip()
                    break

        # Remove currency symbols and spaces
        s = re.sub(r"[R$€£]", "", s)
        s = s.replace(",", "").replace(" ", "")

        # Parentheses indicate negative
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
            try:
                return -abs(float(s))
            except ValueError:
                return 0.0

        # If explicit sign exists, honor it
        if s.startswith("+") or s.startswith("-"):
            try:
                return float(s)
            except ValueError:
                return 0.0

        try:
            value = float(s)
        except ValueError:
            return 0.0

        if credit_suffix:
            return abs(value)

        # For FNB CSV: preserve the original sign from the CSV
        # For FNB OCR: if no suffix and no sign, it's a debit (negative)
        # Check if original string had minus sign (CSV format has explicit signs)
        if has_minus_sign:
            return -abs(value)
        else:
            # No suffix and no minus sign - for OCR this means debit (negative)
            # But for CSV it means positive (income)
            # Since this is ambiguous, return positive and let the format-specific handlers call parse_amount_csv instead
            return abs(value)

    @staticmethod
    def parse_amount_csv(amount_str: str) -> float:
        """
        Parse signed amount from direct CSV export.
        Format: positive numbers = income, negative = expense (e.g., "22" or "-2.75")
        """
        if not amount_str or not isinstance(amount_str, str):
            return 0.0

        s = amount_str.strip()
        if not s or s.lower() in ["nan", "none", ""]:
            return 0.0

        # Remove currency symbols
        s = re.sub(r"[R$€£]", "", s)
        s = s.replace(",", "").replace(" ", "")

        # Parentheses indicate negative
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
            try:
                return -abs(float(s))
            except ValueError:
                return 0.0

        try:
            # Preserve the sign from the CSV (positive or negative)
            return float(s)
        except ValueError:
            return 0.0

    @staticmethod
    def parse_amount_ocr(amount_str: str) -> float:
        """
        Parse OCR-format amounts: unsigned with C/K suffix for credits.
        Format: "22.00C" (credit/income), "22.00" (debit/expense, will be made negative)
        """
        if not amount_str or not isinstance(amount_str, str):
            return 0.0

        s = amount_str.strip()
        if not s or s.lower() in ["nan", "none", ""]:
            return 0.0

        s_upper = s.upper()
        credit_suffix = False
        
        # Check for credit suffixes (C, K, Cr, Credit, Krediet, Kt)
        if s_upper.endswith(("K", "KT", "KREDIET", "C", "CR", "CREDIT")):
            credit_suffix = True
            for suffix in ["KREDIET", "CREDIT", "KT", "CR", "K", "C"]:
                if s_upper.endswith(suffix):
                    s = s[: -len(suffix)].strip()
                    break

        # Remove currency symbols and spaces
        s = re.sub(r"[R$€£]", "", s)
        s = s.replace(",", "").replace(" ", "")

        # Parentheses indicate negative (debit)
        if s.startswith("(") and s.endswith(")"):
            s = s[1:-1].strip()
            try:
                return -abs(float(s))
            except ValueError:
                return 0.0

        try:
            value = float(s)
        except ValueError:
            return 0.0

        if credit_suffix:
            # 'C' or 'K' suffix = income (credit)
            return abs(value)
        else:
            # No suffix = expense (debit) in OCR format
            return -abs(value)

    @staticmethod
    def parse_balance(balance_val) -> Optional[float]:
        if balance_val is None or (isinstance(balance_val, float) and pd.isna(balance_val)):
            return None
        s = str(balance_val).strip()
        if not s or s.lower() in ["nan", "none", ""]:
            return None

        # Remove 'Cr' suffix (credit marker in FNB statements)
        s_upper = s.upper()
        if s_upper.endswith(("CR", "C")):
            for suffix in ["CR", "C"]:
                if s_upper.endswith(suffix):
                    s = s[:-len(suffix)].strip()
                    break

        # Remove currency symbols and spaces
        s = re.sub(r"[R$€£]", "", s)
        s = s.replace(",", "").replace(" ", "")

        # Parentheses indicate negative
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]

        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def _is_unsigned_amount(amount_str: str) -> bool:
        if not amount_str or not isinstance(amount_str, str):
            return False
        s = amount_str.strip().upper()
        if not s:
            return False
        if s.startswith(("+", "-")):
            return False
        if s.endswith(("K", "KT", "KREDIET", "C", "CR", "CREDIT", "D", "DR", "DT", "DEBIET")):
            return False
        return True

    def _map_columns(self, columns: pd.Index) -> Dict[str, str]:
        col_map = {}
        columns_lower = [str(c).lower() for c in columns]

        for canonical, patterns in {
            "date": [r"date"],
            "description": [r"description", r"narrative", r"detail"],
            "amount": [r"amount"],
            "balance": [r"balance"],
        }.items():
            for i, col in enumerate(columns_lower):
                for pattern in patterns:
                    if re.search(pattern, col):
                        col_map[canonical] = columns[i]
                        break
                if canonical in col_map:
                    break

        return col_map

    @staticmethod
    def _infer_description(row: pd.Series, col_map: Dict[str, str]) -> str:
        parts = []
        used_cols = {v for v in col_map.values()}
        for col in row.index:
            if col in used_cols:
                continue
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                parts.append(str(val).strip())
        return " ".join(parts).strip()


def get_adapter(bank_type_str: str):
    """Factory function to get appropriate adapter"""
    from .bank_detector import BankType

    adapter_map = {
        BankType.STANDARD_BANK.value: StandardBankAdapter(),
        BankType.ABSA.value: ABSAAdapter(),
        BankType.CAPITEC.value: CapitecAdapter(),
        BankType.FNB.value: FNBAdapter(),
        "fnb": FNBAdapter(),
        "unknown": GenericAdapter(),
        "generic": GenericAdapter(),
    }

    return adapter_map.get(bank_type_str, GenericAdapter())
