"""Run a live, non-persisting LLM extraction against a synthetic statement.

This intentionally sends no customer data and never prints the API key.
Run from the backend directory so ``.env`` is loaded by ``config.py``.
"""

import asyncio
from io import BytesIO
from pathlib import Path
import sys

# Allow the script to be launched directly from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from config import Config
from services.llm_statement.pipeline import LLMStatementPipeline
from services.llm_statement.provider import ProviderConfig


def build_synthetic_statement() -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    lines = [
        "Example Bank",
        "Bank Statement",
        "Account holder: Test Customer",
        "Account number: 1234567890",
        "Account type: Current Account",
        "Statement period: 01 January 2026 to 31 January 2026",
        "Currency: ZAR",
        "Opening balance: 1000.00",
        "Date             Description              Debit      Credit      Balance",
        "02 January       Salary payment                         500.00      1500.00",
        "03 January       Grocery store             200.00                  1300.00",
        "04 January       Monthly fee                50.00                  1250.00",
        "Closing balance: 1250.00",
    ]
    y = 800
    for line in lines:
        pdf.drawString(45, y, line)
        y -= 24
    pdf.save()
    return output.getvalue()


async def main() -> int:
    if not Config.ANTHROPIC_API_KEY:
        print("ERROR: ANTHROPIC_API_KEY is not configured")
        return 2

    pipeline = LLMStatementPipeline(
        ProviderConfig(
            api_key=Config.ANTHROPIC_API_KEY,
            model=Config.ANTHROPIC_MODEL,
            max_output_tokens=Config.LLM_STATEMENT_MAX_OUTPUT_TOKENS,
            timeout_seconds=Config.LLM_STATEMENT_TIMEOUT_SECONDS,
            transport_retries=Config.LLM_STATEMENT_TRANSPORT_RETRIES,
        ),
        max_pages=Config.LLM_STATEMENT_MAX_PAGES,
        max_characters=Config.LLM_STATEMENT_MAX_CHARACTERS,
        chunk_characters=Config.LLM_STATEMENT_CHUNK_CHARACTERS,
        chunk_pages=Config.LLM_STATEMENT_CHUNK_PAGES,
        strict_redaction=Config.LLM_STATEMENT_STRICT_REDACTION,
        layout_hmac_key=Config.SECRET_KEY.encode("utf-8"),
    )

    # Keep the normal pipeline response deliberately generic, but retain a safe
    # provider error message for this local diagnostic command. Anthropic error
    # bodies do not contain the submitted statement or API key.
    provider_diagnostic = {}
    original_extract = pipeline.provider.extract

    async def capture_provider_error(*args, **kwargs):
        try:
            return await original_extract(*args, **kwargs)
        except Exception as exc:
            cause = exc.__cause__
            provider_diagnostic["http_status"] = getattr(cause, "status_code", None)
            body = getattr(cause, "body", None)
            if isinstance(body, dict):
                error = body.get("error", {})
                if isinstance(error, dict) and isinstance(error.get("message"), str):
                    provider_diagnostic["message"] = error["message"][:500].replace("\n", " ")
            raise

    pipeline.provider.extract = capture_provider_error
    result = await pipeline.process(build_synthetic_statement())
    extraction = result.extraction or {}

    print(f"model={Config.ANTHROPIC_MODEL}")
    print(f"status={result.status}")
    print(f"validation={result.validation.status if result.validation else 'not_run'}")
    print(f"transactions={len(extraction.get('transactions', []))}")
    print(f"opening_balance={extraction.get('opening_balance')}")
    print(f"closing_balance={extraction.get('closing_balance')}")
    print(f"input_tokens={result.input_tokens}")
    print(f"output_tokens={result.output_tokens}")
    if result.message:
        print(f"message={result.message}")
    if provider_diagnostic:
        print(f"provider_http_status={provider_diagnostic.get('http_status')}")
        print(f"provider_error={provider_diagnostic.get('message', 'No safe detail returned')}")
    return 0 if result.status == "parsed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
