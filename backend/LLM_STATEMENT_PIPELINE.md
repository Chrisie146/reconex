# LLM-first PDF statement extraction

The optional LLM path is integrated with `POST /upload_pdf` and is disabled by default. When disabled, the existing deterministic PDF parser behaves as before.

## Enable locally

Install `backend/requirements.txt`, apply the latest Alembic migration, then set:

```text
LLM_STATEMENT_ENABLED=true
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

Haiku 4.5 is the default because it is the least expensive current Anthropic model that supports this pipeline's structured JSON output and 200K-token context requirements. Keep the dated ID for reproducibility. Measure its validation pass rate on the evaluation set before considering a more expensive model.

The remaining limits and retry settings are documented in `backend/.env.example`. Do not enable the path with client data until the vendor/operator, retention, cross-border processing, security, deletion, and POPIA disclosures have been reviewed. Redaction is a data-minimisation control, not a legal claim of anonymisation.

## Request behaviour

The endpoint contract remains compatible with the existing UI. Successful responses add:

- `extraction_path`: `model`, `code_recipe`, or `legacy`;
- `document_id`: an opaque per-attempt ID on the LLM path;
- `validation_status`: `passed` on an accepted LLM result.
- `recipe_created`: whether this verified model result added or refreshed a
  customer-free recipe file for its layout.

Non-success LLM responses use a structured `detail` object with a safe status, opaque document ID, and validation codes. Typical statuses are `requires_ocr`, `redaction_failed`, `not_a_statement`, `unparseable`, `invalid_document`, and `provider_unavailable`. Partial transactions are never returned as success.

## Trust boundary

Schema v2 represents a separately posted inline fee as `additional_fee`: a
signed decimal string (negative charge, positive refund). `0.00` means no
additional effect, including fees already included in the amount or posted as
standalone rows. `unknown` is rejected by validation. Reconciliation includes
both components. After validation, an additional fee becomes its own ledger
entry, while physical row identity and coverage remain unchanged. Summary fees
and VAT already included in a fee must not be added again. Ambiguous statements
still require review; arithmetic cannot prove every component was transcribed.

All provider money values are strings and all reconciliation uses `Decimal`. Only after validation passes are signed `Decimal` amounts adapted to the application's existing transaction persistence layer. That existing database column is currently a SQLAlchemy `Float`, so eliminating binary floating point from storage requires a separate database-wide monetary migration.

Validation checks the schema, dates, statement period, document-level balances, available running balances, physical source locations, page coverage, and a conservative independent candidate-row count. It preserves legitimate duplicate-looking transactions and removes only exact overlap copies from the same physical page and row.

Arithmetic reconciliation cannot prove that a net-zero pair of transactions was not omitted. The candidate-row coverage check reduces this risk, and incomplete coverage produces `unverifiable`, but the UI and product language must not describe a passing result as guaranteed complete.

## Privacy and audit data

The model receives redacted text plus line bounding boxes, not the original PDF. The implementation does not use the Files API, prompt caching, batch processing, web search, or tools. The normal logs contain opaque IDs, versions, durations, token counts, and validation codes—not statement contents.

Failed attempts persist only sanitised metadata in `llm_statement_failures`. This requires migration `a2b3c4d5e6f7`. The table contains no filenames, extracted rows, descriptions, balances, account digits, prompts, or provider outputs.

## Shared code recipe registry

Before calling the provider, the pipeline looks for a matching JSON parser
recipe under `services/llm_statement/layout_recipes`. A recipe contains only a
version, recognised column labels and positions, page geometry, and a date
format. It contains no transaction descriptions, account details, customer
identity, dates, balances, or amounts.

After Claude returns a result that passes accounting validation, the pipeline
tries the deterministic extractor against the same PDF. It writes a recipe only
when the local result exactly matches the verified model result. Subsequent
matching statements use the recipe, are independently checked for row coverage
and reconciliation, and make zero provider requests. If the format changes or
does not validate, the recipe is rejected and the normal provider path is used.

Recipe files are application-wide rather than tenant-scoped. They should be
reviewed, tested, and committed so all deployed instances and users receive
them. A production image with a read-only source tree can still consume
committed recipes but cannot learn a new file until the resulting recipe is
promoted in a development/release workflow.

Set `LLM_STATEMENT_ALLOW_PROVIDER_FALLBACK=false` to guarantee that an unknown
layout returns `parser_not_available` without spending money. The default is
`true`, so unknown layouts may call Claude and teach the registry.

The current recipe learner deliberately supports only explicit, stable text
tables with recognised headers, full dates, printed balances, and unambiguous
amount columns. Unsupported or wrapped layouts continue through Claude and do
not produce an unsafe general-purpose parser.

## Deliberately deferred

OCR is also not added. Any page without a usable text layer fails closed with `requires_ocr`.

## Tests

Focused tests live in:

- `backend/tests/test_llm_statement_validator.py`
- `backend/tests/test_llm_statement_components.py`
- `backend/tests/test_llm_statement_provider.py`
- `backend/tests/test_llm_statement_pipeline.py`

They do not call Anthropic and do not require an API key.

For an explicit live check after configuring the key, run this from `backend`:

```powershell
python tools/live_llm_smoke_test.py
```

The command creates a synthetic statement in memory, sends no customer data,
persists no transactions, and never prints the API key. It exits successfully
only when provider extraction and local accounting validation both pass.
