import pytest

from services import pdf_parser


def test_normalize_amount_various_formats():
    cases = {
        '13,499.80C': '13499.80',
        '(293.92)': '-293.92',
        '1 234,56': '1234.56',
        'R 1,250.00': '1250.00',
        '12,345.67Cr': '12345.67',
    }
    for inp, expected in cases.items():
        got = pdf_parser._normalize_amount(inp)
        assert got == expected, f"{inp} -> {got} (expected {expected})"


def test_clean_description_removes_trailing_balance_and_artifacts():
    raw = "POS Purchase |Test__  123.00 13,000.00C"
    cleaned = pdf_parser._clean_description(raw)
    assert '|' not in cleaned
    assert '_' not in cleaned
    assert '13,000.00' not in cleaned
    assert 'POS Purchase' in cleaned


def test_split_transactions_from_block_simple():
    date = '02 Jan'
    block = 'POS A 100.00 POS B 50.00'
    rows = pdf_parser._split_transactions_from_block(date, block)
    # Expect two rows with amounts 100.00 and 50.00
    assert len(rows) == 2
    assert rows[0][0] == date
    assert rows[1][0] == date
    amounts = [r[2] for r in rows]
    assert any('100.00' in a for a in amounts)
    assert any('50.00' in a for a in amounts)
    assert rows[0][1].strip() != '' and rows[1][1].strip() != ''
