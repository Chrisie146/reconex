"""
Balance-based validation for OCR-extracted transactions.

This module provides deterministic arithmetic validation to:
- Verify transaction amounts using balance information
- Detect OCR misreads, sign errors, and missing rows
- Correct transaction signs when balance information is available
- Provide transparent and explainable validation results

The validator is safe for accountants - it's deterministic, transparent,
and tolerant of small rounding differences.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP


class BalanceValidator:
    """
    Validates transactions using balance information with deterministic arithmetic.
    """
    
    # Tolerance for rounding differences (1 cent)
    TOLERANCE = Decimal("0.01")
    
    @staticmethod
    def resolve_signed_amount(transaction: Dict) -> Optional[Decimal]:
        """
        Determine signed amount from transaction data.
        
        Priority:
        1. Explicit 'amount' field if present
        2. Derive from 'credit' (positive) or 'debit' (negative)
        
        Args:
            transaction: Dict with keys: amount, debit, credit
            
        Returns:
            Decimal signed amount or None if unable to determine
        """
        # Try explicit amount first
        if transaction.get("amount") is not None:
            try:
                return Decimal(str(transaction["amount"]))
            except:
                pass
        
        # Try credit/debit
        credit = transaction.get("credit")
        debit = transaction.get("debit")
        
        if credit is not None and credit != 0:
            try:
                return Decimal(str(credit))
            except:
                pass
        
        if debit is not None and debit != 0:
            try:
                return -Decimal(str(debit))
            except:
                pass
        
        return None
    
    @staticmethod
    def validate_transaction(
        current: Dict,
        previous_balance: Optional[Decimal],
        index: int
    ) -> Dict:
        """
        Validate a single transaction against expected balance.
        
        Args:
            current: Current transaction with keys: date, description, amount/debit/credit, balance
            previous_balance: Balance from previous transaction (or opening balance)
            index: Transaction index (0-based)
            
        Returns:
            Validation result dict with keys:
            - balance_verified: True/False/None
            - balance_difference: float or None
            - validation_message: str
            - corrected_amount: Decimal or None (if sign needs correction)
        """
        result = {
            "balance_verified": None,
            "balance_difference": None,
            "validation_message": "",
            "corrected_amount": None
        }
        
        # First transaction or opening balance - no previous balance to validate against
        if index == 0:
            current_balance = current.get("balance")
            if current_balance is not None:
                try:
                    result["validation_message"] = f"Opening balance: {Decimal(str(current_balance))}"
                except:
                    result["validation_message"] = "Opening balance (invalid format)"
            else:
                result["validation_message"] = "Opening balance (no balance provided)"
            return result
        
        # Get signed amount
        signed_amount = BalanceValidator.resolve_signed_amount(current)
        if signed_amount is None:
            result["validation_message"] = "Cannot determine transaction amount"
            return result
        
        # Get current balance
        current_balance = current.get("balance")
        if current_balance is None:
            result["validation_message"] = "No balance provided - cannot validate"
            return result
        
        try:
            current_balance = Decimal(str(current_balance))
        except:
            result["validation_message"] = "Invalid balance format"
            return result
        
        # Validate balance
        if previous_balance is None:
            result["validation_message"] = "No previous balance - cannot validate"
            return result
        
        expected_balance = previous_balance + signed_amount
        difference = abs(expected_balance - current_balance)
        
        if difference <= BalanceValidator.TOLERANCE:
            result["balance_verified"] = True
            result["balance_difference"] = float(difference)
            result["validation_message"] = "[OK] Balance verified"
        else:
            # Balance doesn't match - try flipping the sign
            flipped_amount = -signed_amount
            expected_balance_flipped = previous_balance + flipped_amount
            difference_flipped = abs(expected_balance_flipped - current_balance)
            
            if difference_flipped <= BalanceValidator.TOLERANCE:
                # Sign correction needed
                result["balance_verified"] = True
                result["balance_difference"] = float(difference_flipped)
                result["corrected_amount"] = float(flipped_amount)
                result["validation_message"] = f"[OK] Balance verified (sign corrected: {signed_amount} -> {flipped_amount})"
            else:
                # Balance mismatch even after sign correction
                result["balance_verified"] = False
                result["balance_difference"] = float(difference)
                result["validation_message"] = (
                    f"[FAIL] Balance mismatch: expected {expected_balance:.2f}, "
                    f"actual {current_balance:.2f}, diff {difference:.2f}"
                )
        
        return result
    
    @staticmethod
    def validate_transactions(transactions: List[Dict], strict: bool = False) -> Tuple[List[Dict], Dict]:
        """
        Validate all transactions and return annotated results.
        
        Args:
            transactions: List of transaction dicts with keys:
                - date: str
                - description: str
                - debit: float or None
                - credit: float or None
                - amount: float or None (signed)
                - balance: float or None
            strict: If False (default/production), only annotate - don't auto-correct signs.
                   If True (testing), auto-correct signs based on balance validation.
        
        Returns:
            Tuple of (annotated_transactions, summary)
            - annotated_transactions: List of transactions with validation fields added
            - summary: Dict with validation statistics
        """
        annotated = []
        previous_balance = None
        
        # Statistics
        total_transactions = len(transactions)
        verified_count = 0
        failed_count = 0
        corrected_count = 0
        no_balance_count = 0
        
        mode_str = "annotation-only" if not strict else "auto-correct"
        print(f"[BalanceValidator] Mode: {mode_str} | Validating {total_transactions} transactions...")
        
        for i, txn in enumerate(transactions):
            # Make a copy to avoid modifying original
            annotated_txn = txn.copy()
            
            # Validate transaction
            validation = BalanceValidator.validate_transaction(
                txn, previous_balance, i
            )
            
            # Add validation fields
            annotated_txn.update(validation)
            
            # Apply sign correction only if STRICT mode
            if strict and validation.get("corrected_amount") is not None:
                annotated_txn["amount"] = validation["corrected_amount"]
                corrected_count += 1
                if i < 10:  # Show first 10 corrections in strict mode
                    print(f"  [Correction #{corrected_count}] Row {i}: {txn.get('description', '')[:40]}")
                    print(f"    Original: {txn['amount']}, Corrected: {validation['corrected_amount']}")
            
            # Update statistics
            if validation["balance_verified"] is True:
                verified_count += 1
            elif validation["balance_verified"] is False:
                failed_count += 1
                if i < 5:  # Show first 5 failures
                    print(f"  [Failure] Row {i}: {validation['validation_message']}")
            else:
                no_balance_count += 1
            
            # Update previous_balance for next iteration
            if txn.get("balance") is not None:
                try:
                    previous_balance = Decimal(str(txn["balance"]))
                except:
                    pass
            
            annotated.append(annotated_txn)
        
        # Calculate net from corrected amounts (or original if not strict)
        net_amount = Decimal("0")
        for txn in annotated:
            signed_amount = BalanceValidator.resolve_signed_amount(txn)
            if signed_amount is not None:
                net_amount += signed_amount
        
        summary = {
            "total_transactions": total_transactions,
            "verified_count": verified_count,
            "failed_count": failed_count,
            "corrected_count": corrected_count if strict else 0,
            "no_balance_count": no_balance_count,
            "mode": mode_str,
            "verification_rate": f"{verified_count / max(1, total_transactions - no_balance_count) * 100:.1f}%",
            "net_amount": float(net_amount)
        }
        
        print(f"[BalanceValidator] Verified: {verified_count}, Failed: {failed_count}, Corrected: {corrected_count if strict else 0}, No balance: {no_balance_count}")
        print(f"[BalanceValidator] Net amount: R {float(net_amount):,.2f}")
        
        return annotated, summary


def demo():
    """Demo usage of balance validator"""
    transactions = [
        {
            "date": "2024-01-01",
            "description": "OPENING BALANCE",
            "debit": None,
            "credit": None,
            "amount": None,
            "balance": 10000.00
        },
        {
            "date": "2024-01-02",
            "description": "ENGEN MIDRAND",
            "debit": 500.00,
            "credit": None,
            "amount": -500.00,
            "balance": 9500.00
        },
        {
            "date": "2024-01-03",
            "description": "SALARY DEPOSIT",
            "debit": None,
            "credit": 5000.00,
            "amount": 5000.00,
            "balance": 14500.00
        },
        {
            "date": "2024-01-04",
            "description": "WOOLWORTHS",
            "debit": 250.00,
            "credit": None,
            "amount": 250.00,  # WRONG SIGN - should be negative
            "balance": 14250.00
        }
    ]
    
    annotated, summary = BalanceValidator.validate_transactions(transactions)
    
    print("Balance Validation Results")
    print("=" * 80)
    for i, txn in enumerate(annotated):
        print(f"\n[{i}] {txn['date']} - {txn['description']}")
        print(f"    Amount: {txn.get('amount', 'N/A')}")
        print(f"    Balance: {txn.get('balance', 'N/A')}")
        print(f"    {txn['validation_message']}")
    
    print("\n" + "=" * 80)
    print("Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo()
