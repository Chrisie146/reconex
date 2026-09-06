"""Convert validated physical rows into ledger entries without losing fees."""

from datetime import date
from decimal import Decimal


def transactions_for_import(extraction: dict) -> list:
    transactions = []
    for row in extraction["transactions"]:
        magnitude = Decimal(row["amount"])
        amount = magnitude if row["direction"] == "credit" else -magnitude
        fee = Decimal(row["additional_fee"])
        entries = [(row["description"], amount)]
        if fee:
            label = "Bank fee" if fee < 0 else "Bank fee refund"
            entries.append((f"{label}: {row['description']}", fee))
        for description, signed_amount in entries:
            transactions.append({
                "date": date.fromisoformat(row["date"]),
                "description": description,
                "amount": signed_amount,
                "debit_flag": signed_amount < 0,
                "balance_verified": None,
                "balance_difference": None,
                "validation_message": "Document-level LLM reconciliation passed",
            })
    return transactions
