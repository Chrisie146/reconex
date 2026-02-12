import os
import sys
import pytest

# Ensure the backend package/module is importable when running tests from repo root
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import multilingual


def test_normalize_headers_ok():
    headers = ["Date", "Besonderhede", "Bedrag", "Saldo"]
    mapping = multilingual.normalize_headers(headers)
    assert mapping["date"] == 0
    assert mapping["description"] == 1
    assert mapping["amount"] == 2


def test_normalize_headers_missing():
    headers = ["Trans ID", "SomeCol"]
    with pytest.raises(multilingual.ColumnDetectionError):
        multilingual.normalize_headers(headers)


def test_categorize_transaction():
    assert multilingual.categorize_transaction("Payment to SPAR Claremont") == "Groceries"
    assert multilingual.categorize_transaction("FOOI bank charge") == "Bank Fees"
    assert multilingual.categorize_transaction(None) == "Uncategorized"


def test_parse_number_various():
    assert multilingual.parse_number("1,234.56") == pytest.approx(multilingual.Decimal("1234.56"))
    assert multilingual.parse_number("1.234,56") == pytest.approx(multilingual.Decimal("1234.56"))
    assert multilingual.parse_number("1234") == pytest.approx(multilingual.Decimal("1234"))
    assert multilingual.parse_number("R 1 234,56") == pytest.approx(multilingual.Decimal("1234.56"))


def test_process_guided_ocr():
    extracted = {"date": "2026-01-01", "description": "Shell Cape Town", "amount": "R 500,00"}
    out = multilingual.process_guided_ocr(extracted)
    assert out["date"] == "2026-01-01"
    assert out["category"] == "Fuel"
    assert out["amount"] == str(multilingual.Decimal("500.00"))
