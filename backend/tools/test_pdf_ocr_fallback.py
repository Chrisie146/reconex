import io

import pytest

from services.pdf_parser import pdf_to_csv_bytes, ParserError


class FakePage:
    def extract_tables(self):
        return []

    def extract_text(self):
        return None


class FakePDF:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def fake_open(_bytes_io):
    # return a context manager-like object with pages attribute
    return FakePDF([FakePage()])


def test_pdf_parser_uses_ocr_fallback(monkeypatch):
    # Monkeypatch pdfplumber.open to return a PDF with no text/tables
    import services.pdf_parser as pdf_parser
    monkeypatch.setattr(pdf_parser, 'pdfplumber', pdf_parser.pdfplumber)
    monkeypatch.setattr(pdf_parser.pdfplumber, 'open', fake_open)

    # Monkeypatch OCR to return predictable text containing two transactions
    sample_ocr_text = (
        "14/01/2025 Grocery Store 123.45\n"
        "15/01/2025 ATM Withdrawal (200.00)\n"
    )

    import services.ocr as ocr_module
    monkeypatch.setattr(ocr_module, 'ocr_pdf_bytes', lambda b: sample_ocr_text)

    # Call parser with arbitrary bytes (we fake pdfplumber.open)
    csv_bytes, year = pdf_to_csv_bytes(b"%PDF-FAKE-BYTES")
    csv_text = csv_bytes.decode('utf-8')

    assert "Date,Description,Amount" in csv_text
    assert "14/01/2025" in csv_text
    # OCR/CSV formatting can introduce small differences (commas/newlines),
    # assert presence of a stable substring instead of exact full phrase
    assert "Grocery" in csv_text
    assert "123.45" in csv_text
    assert "15/01/2025" in csv_text
    assert "ATM Withdrawal" in csv_text
    assert "(200.00)" in csv_text
