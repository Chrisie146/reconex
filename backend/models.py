"""
Database models for Bank Statement Analyzer
Handles storage of transactions and session data
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, create_engine, ForeignKey, Boolean, UniqueConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """
    Represents an authenticated user (accountant) in the system.
    Each user can have multiple clients.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Client(Base):
    """
    Represents a client for an accountant.
    Each accountant can have multiple clients, with isolated transactions and rules per client.
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)  # References authenticated User
    name = Column(String, nullable=False)  # Client name

    # Categorisation V2: drives the (entity × purpose → account) resolver.
    # Values: pty_ltd | cc | sole_prop | trust | partnership | individual | npo
    legal_entity_type = Column(String, nullable=True, index=True)
    # Values: company | sole_prop | individual_trader | individual_only
    # individual_trader = natural person conducting a trade on a personal bank account
    # (farmers, freelancers, Airbnb hosts). Distinct from sole_prop (separate books).
    trading_capacity = Column(String, nullable=True)
    # Values: farming | retail | consulting | professional | construction | rental |
    #         restaurant | other | none
    trade_type = Column(String, nullable=True)
    # When true, retail/grocery spend on a company card defaults to Director's Loan.
    director_uses_company_card = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class Account(Base):
    """
    Chart-of-Accounts node for a single client.

    Hierarchical (adjacency list + materialized `path`). Each client has its own
    independent CoA seeded from a template on client creation. Phase 1 is
    strictly additive: the legacy free-text Transaction.category column and
    CustomCategory table remain in place until Phase 2 sweeps them.
    """
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("client_id", "code", name="uq_accounts_client_code"),
    )

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)

    code = Column(String, nullable=False, index=True)  # e.g. "4100"
    name = Column(String, nullable=False)              # e.g. "Sales (Standard-rated)"

    parent_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    path = Column(String, nullable=False, default="")  # Materialized: "4000/4100" — keeps tree queries cheap
    level = Column(Integer, nullable=False, default=0) # 0 = root, 1 = first child, ...

    # Accounting type. Values: asset | liability | equity | revenue | expense
    account_type = Column(String, nullable=False, index=True)
    # Finer grouping used by P&L / Balance Sheet (e.g. current_asset, fixed_asset,
    # current_liability, long_term_liability, cost_of_sales, operating_expense,
    # finance_cost, other_income, tax_expense). NULL on header rows allowed.
    account_subtype = Column(String, nullable=True, index=True)
    # 'DR' (asset/expense) or 'CR' (liability/equity/revenue) — the side that increases the balance
    normal_balance = Column(String, nullable=False)

    # Forward-compat for the Statement of Cash Flows (deferred phase).
    # Values: operating | investing | financing | none
    cash_flow_section = Column(String, nullable=False, default="none")

    # VAT control accounts (2200 Output, 2210 Input) get is_vat_control=True so
    # VAT aggregation knows where to look. Other accounts carry vat_treatment to
    # describe how postings to them should be treated for VAT calculation.
    is_vat_control = Column(Boolean, nullable=False, default=False)
    # Values: standard_15 | zero_rated | exempt | out_of_scope | NULL (for balance-sheet accounts)
    vat_treatment = Column(String, nullable=True)
    vat_rate = Column(Float, nullable=True)  # e.g. 15.0 for standard-rated; NULL otherwise

    # Only leaf accounts are postable; header nodes (e.g. "4000 Revenue") are not.
    is_postable = Column(Boolean, nullable=False, default=True)
    # Soft delete — preserves historical reporting integrity for accounts that have postings.
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    # System (template-seeded) accounts can only have name/description/cash_flow_section/vat_rate edited.
    is_system = Column(Boolean, nullable=False, default=False)

    description = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    parent = relationship("Account", remote_side=[id], backref="children")


class Transaction(Base):
    """
    Represents a parsed transaction from a bank statement
    Each transaction is categorized and normalized
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    session_id = Column(String, index=True)  # Track session for stateless operation
    invoice_id = Column(Integer, nullable=True)  # Link to confirmed invoice (set when invoice is confirmed)

    # Normalized transaction data
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # Legacy free-text category — kept until Phase 2 sweep migrates everything to account_id
    # New CoA link (Phase 1: nullable, populated alongside category as services are swept in Phase 2)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    suggested_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)

    # VAT calculation fields (when VAT is enabled)
    vat_amount = Column(Float, nullable=True)  # Calculated VAT amount
    amount_excl_vat = Column(Float, nullable=True)  # Amount excluding VAT
    amount_incl_vat = Column(Float, nullable=True)  # Amount including VAT (same as amount when VAT applies)

    # Bank source tracking
    bank_source = Column(String, nullable=True, default="unknown")  # standard_bank, absa, capitec, unknown

    # Suggestion system: predefined rules propose a category, user confirms or changes
    # Populated on upload from keyword/merchant rules; cleared when user accepts/overrides
    suggested_category = Column(String, nullable=True)

    # Categorisation V2: human-readable reason shown next to the suggestion
    # (e.g. "Director's Loan — personal use of company card").
    suggestion_reason = Column(String, nullable=True)

    # Balance validation metadata (for production transparency)
    balance_verified = Column(Integer, nullable=True)  # 1=True, 0=False, NULL=None/no balance
    balance_difference = Column(Float, nullable=True)  # Absolute difference from expected balance
    validation_message = Column(String, nullable=True)  # Human-readable validation result

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", foreign_keys=[account_id])
    suggested_account = relationship("Account", foreign_keys=[suggested_account_id])


class Reconciliation(Base):
    """
    Stores opening and closing balances for a session or client for a given month (YYYY-MM)
    """
    __tablename__ = "reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True, nullable=True)
    month = Column(String, index=True)  # format YYYY-MM
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class OverallReconciliation(Base):
    """
    Stores an overall reconciliation record per session or client: user-provided opening and bank closing balances.
    The system closing balance is computed as opening + sum(all transactions).
    """
    __tablename__ = "overall_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=True)
    system_opening_balance = Column(Float, nullable=True)
    bank_closing_balance = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TransactionMerchant(Base):
    """
    Stores merchant attribution for transactions. We keep it separate from the transactions table
    to avoid altering the original schema in-place on existing deployments.
    """
    __tablename__ = "transaction_merchants"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, index=True)
    session_id = Column(String, index=True)
    merchant = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionState(Base):
    """
    Tracks session-level metadata such as whether a session has been locked/finalized
    """
    __tablename__ = "session_states"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, unique=True)
    locked = Column(Integer, default=0)  # 0 = unlocked, 1 = locked
    friendly_name = Column(String, nullable=True)  # E.g., "FNB Aspire Account 132"
    created_at = Column(DateTime, default=datetime.utcnow)


class Rule(Base):
    """
    Rule for auto-categorization/merchant assignment per client.
    conditions and action are stored as JSON strings.
    """
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    name = Column(String, nullable=False)
    enabled = Column(Integer, default=1)  # 1 = enabled, 0 = disabled
    priority = Column(Integer, default=100)
    conditions = Column(String, nullable=False)  # JSON string
    action = Column(String, nullable=False)      # JSON string
    auto_apply = Column(Integer, default=0)      # 1 = auto-apply on upload
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemRule(Base):
    """
    System-shipped categorisation rules (read-only, ship with the product).

    Distinct from Rule (user-authored, per-client). System rules emit a
    `purpose` (business/personal/capital/financing/tax/mixed/other) plus an
    optional CoA code hint; the resolver maps the purpose to an actual
    account_id on the client's seeded CoA using the entity × trading_capacity
    matrix.

    Conditions JSON shape matches Rule.conditions (reuses txn_matches_conditions
    in routers/dependencies.py). entity_filter optionally restricts which clients
    a rule applies to.
    """
    __tablename__ = "system_rules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)  # stable id for upserts (e.g. "sa.bank.fnb_monthly_fee")
    name = Column(String, nullable=False)
    priority = Column(Integer, nullable=False, default=100, index=True)
    conditions = Column(String, nullable=False)  # JSON string, same shape as Rule.conditions
    # Values: business | personal | capital | financing | tax | mixed | other
    purpose = Column(String, nullable=False)
    coa_hint = Column(String, nullable=True)  # CoA code (e.g. "6700"); resolver may override
    # Values: high (auto-apply) | medium (suggest) | low (flag for review)
    confidence = Column(String, nullable=False, default="medium")
    # Optional JSON restriction by legal_entity_type / trading_capacity / trade_type
    entity_filter = Column(String, nullable=True)
    description = Column(String, nullable=True)  # accountant-facing reason text
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Invoice(Base):
    """
    Represents an uploaded invoice document or metadata attached by the user.
    This table stores invoice header information used for matching against bank transactions.
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), index=True)
    session_id = Column(String, index=True)
    supplier_name = Column(String, nullable=False)
    invoice_date = Column(Date, nullable=False)
    invoice_number = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    vat_amount = Column(Float, nullable=True)
    file_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InvoiceMatch(Base):
    """
    Stores suggested matches between invoices and transactions along with confidence and status.
    Status values: 'suggested', 'confirmed', 'rejected'
    """
    __tablename__ = "invoice_matches"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, index=True)
    transaction_id = Column(Integer, index=True)
    confidence = Column(Integer, nullable=False)
    explanation = Column(String, nullable=True)
    status = Column(String, default='suggested')
    suggested_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)


class UserCategorizationRule(Base):
    """
    Stores learned categorization rules per user, scoped to a specific client.
    When a user assigns a category to a transaction, we learn patterns to auto-categorize future transactions.
    """
    __tablename__ = "user_categorization_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)  # Persistent user identifier across sessions
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=True)
    session_id = Column(String, index=True, nullable=True)  # Optional: track which session created the rule
    category = Column(String, nullable=False)  # Legacy free-text — Phase 2 replaces this with account_id
    # New CoA link — nullable until Phase 2 sweep populates it.
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True, index=True)
    account = relationship("Account", foreign_keys=[account_id])

    # Pattern matching fields
    pattern_type = Column(String, nullable=False)  # 'exact', 'contains', 'starts_with', 'merchant'
    pattern_value = Column(String, nullable=False)  # The actual pattern to match
    
    # Confidence and usage tracking
    confidence_score = Column(Float, default=1.0)  # How reliable this rule is (0.0-1.0)
    use_count = Column(Integer, default=0)  # Number of times this rule was applied
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    enabled = Column(Integer, default=1)  # 1 = enabled, 0 = disabled


class CustomCategory(Base):
    """
    Stores custom categories created by users.
    These persist across sessions so users can reuse categories across different bank statements.
    Scoped per client so each client can have its own set of categories.
    """
    __tablename__ = "custom_categories"
    __table_args__ = (
        # Unique category name per client (replaces old global unique on name).
        # NULL client_id values (legacy/global rows) are each treated as distinct
        # by PostgreSQL's standard NULL semantics, so they do not conflict.
        UniqueConstraint("client_id", "name", name="uq_custom_categories_client_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=True)
    name = Column(String, nullable=False, index=True)  # Category name (unique per client, not globally)
    is_income = Column(Integer, default=0)  # 1 = Income/Sales (VAT Output), 0 = Expense (VAT Input)
    vat_applicable = Column(Integer, default=0)  # 1 = VAT applies, 0 = no VAT
    vat_rate = Column(Float, default=15.0)  # Default South African VAT rate (15%)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionVATConfig(Base):
    """
    Stores VAT configuration per session.
    Allows each session/client to enable/disable VAT calculation independently.
    """
    __tablename__ = "session_vat_config"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, unique=True, nullable=False)
    vat_enabled = Column(Integer, default=0)  # 1 = VAT enabled, 0 = disabled
    default_vat_rate = Column(Float, default=15.0)  # Default VAT rate for this session
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FileAccessLog(Base):
    """
    Audit log for file access events (uploads, downloads, deletions).
    Tracks who accessed which files, when, and from where for security/compliance.
    """
    __tablename__ = "file_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), index=True, nullable=True)
    file_key = Column(String, nullable=False)  # Cloud storage object key
    action = Column(String, nullable=False)  # upload, download, delete, generate_url
    ip_address = Column(String, nullable=True)  # Client IP address
    user_agent = Column(String, nullable=True)  # Client user agent
    storage_backend = Column(String, nullable=True)  # s3, azure, gcs, local
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class TaskStatus(Base):
    """
    Tracks status and progress of background Celery tasks.
    Allows users to poll task status and retrieve results.
    """
    __tablename__ = "task_status"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True, nullable=False)  # Celery task ID
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    task_name = Column(String, nullable=False)  # parse_pdf_async, bulk_categorize_async, etc.
    status = Column(String, nullable=False, index=True)  # PENDING, PROCESSING, SUCCESS, FAILED
    progress_percent = Column(Integer, default=0)  # 0-100
    progress_message = Column(String, nullable=True)  # Current operation message
    result = Column(String, nullable=True)  # JSON-encoded result on success
    error_message = Column(String, nullable=True)  # Error details on failure
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# =============================================================================
# FINANCIAL YEAR & ARCHIVE MODELS
# =============================================================================


class FinancialYear(Base):
    """
    Defines a financial year for a client. Users configure the start/end dates
    and label. Once all work for the year is complete, the year can be archived
    to keep the live tables lean while preserving all historical data.
    """
    __tablename__ = "financial_years"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    label = Column(String, nullable=False)       # e.g. "2024/2025" or "FY2025"
    year_start = Column(Date, nullable=False)    # Inclusive start date
    year_end = Column(Date, nullable=False)      # Inclusive end date
    status = Column(String, default="open")      # "open" | "archived"
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ArchivedSession(Base):
    """
    Archive copy of a SessionState record. Includes client_id (not on the live
    SessionState) so the archived record is self-contained.
    """
    __tablename__ = "archived_sessions"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    locked = Column(Integer, default=0)
    friendly_name = Column(String, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedTransaction(Base):
    """
    Archive copy of a Transaction record.
    """
    __tablename__ = "archived_transactions"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    original_invoice_id = Column(Integer, nullable=True)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    # Denormalized snapshots of the linked Account at archive time so historical
    # reports survive even after a live account is renamed or deleted. No FK —
    # the live account row may be gone by the time anyone reads this.
    account_id = Column(Integer, nullable=True)
    account_code = Column(String, nullable=True)
    account_name = Column(String, nullable=True)
    vat_amount = Column(Float, nullable=True)
    amount_excl_vat = Column(Float, nullable=True)
    amount_incl_vat = Column(Float, nullable=True)
    bank_source = Column(String, nullable=True)
    balance_verified = Column(Integer, nullable=True)
    balance_difference = Column(Float, nullable=True)
    validation_message = Column(String, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedTransactionMerchant(Base):
    """
    Archive copy of a TransactionMerchant record.
    """
    __tablename__ = "archived_transaction_merchants"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    original_transaction_id = Column(Integer, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    merchant = Column(String, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedReconciliation(Base):
    """
    Archive copy of a Reconciliation record.
    """
    __tablename__ = "archived_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    session_id = Column(String, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=True)
    month = Column(String, index=True)
    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedOverallReconciliation(Base):
    """
    Archive copy of an OverallReconciliation record.
    """
    __tablename__ = "archived_overall_reconciliations"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    session_id = Column(String, index=True, nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=True)
    system_opening_balance = Column(Float, nullable=True)
    bank_closing_balance = Column(Float, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedInvoice(Base):
    """
    Archive copy of an Invoice record.
    """
    __tablename__ = "archived_invoices"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False)
    session_id = Column(String, index=True, nullable=False)
    supplier_name = Column(String, nullable=False)
    invoice_date = Column(Date, nullable=False)
    invoice_number = Column(String, nullable=True)
    total_amount = Column(Float, nullable=False)
    vat_amount = Column(Float, nullable=True)
    file_reference = Column(String, nullable=True)
    original_created_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class ArchivedInvoiceMatch(Base):
    """
    Archive copy of an InvoiceMatch record. Stores original IDs for reference
    since the live transaction/invoice rows are removed after archiving.
    """
    __tablename__ = "archived_invoice_matches"

    id = Column(Integer, primary_key=True, index=True)
    financial_year_id = Column(Integer, ForeignKey("financial_years.id", ondelete="CASCADE"), index=True, nullable=False)
    original_id = Column(Integer, nullable=False)
    original_invoice_id = Column(Integer, nullable=False)
    original_transaction_id = Column(Integer, nullable=False)
    confidence = Column(Integer, nullable=False)
    explanation = Column(String, nullable=True)
    status = Column(String, default="suggested")
    suggested_at = Column(DateTime, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, default=datetime.utcnow)


class BackupRecord(Base):
    """
    Audit log of user-triggered backup downloads. The actual backup is streamed
    directly to the browser (pg_dump piped as HTTP response), so no file is stored
    server-side. This table simply records who downloaded a backup and when.
    """
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    label = Column(String, nullable=False)        # e.g. "Full backup - 2025-03-15"
    status = Column(String, default="completed")  # "completed" | "failed"
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Database setup using configuration
from config import DATABASE_URL, ENVIRONMENT

# Fix Render postgres:// URL to postgresql:// for SQLAlchemy 1.4+ compatibility
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure engine based on database type
is_sqlite = DATABASE_URL.startswith("sqlite")
is_postgresql = DATABASE_URL.startswith("postgresql")

# Engine configuration
engine_config = {
    "echo": False  # Set to True for SQL query logging
}

if is_sqlite:
    # SQLite-specific configuration
    engine_config["connect_args"] = {"check_same_thread": False}
elif is_postgresql:
    # PostgreSQL connection pooling configuration
    # Pool size: number of connections to maintain
    # Max overflow: additional connections beyond pool_size
    # Pool timeout: seconds to wait for connection from pool
    # Pool recycle: recycle connections after this many seconds (prevents stale connections)
    engine_config["pool_size"] = 10  # Base pool size
    engine_config["max_overflow"] = 20  # Additional connections beyond pool_size
    engine_config["pool_timeout"] = 30  # Seconds to wait for connection
    engine_config["pool_pre_ping"] = True  # Verify connections before using
    engine_config["pool_recycle"] = 3600  # Recycle connections after 1 hour
    
    # Connection arguments for PostgreSQL
    connect_args = {
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    }
    
    # Enable SSL for production environments
    if ENVIRONMENT == "production":
        connect_args["sslmode"] = "require"
    
    engine_config["connect_args"] = connect_args

engine = create_engine(DATABASE_URL, **engine_config)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency injection for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and run lightweight column migrations."""
    Base.metadata.create_all(bind=engine)

    # Lightweight schema migrations for SQLite (ALTER TABLE ADD COLUMN is idempotent via try/except)
    with engine.connect() as conn:
        for ddl in [
            "ALTER TABLE transactions ADD COLUMN suggested_category VARCHAR",
            "ALTER TABLE transactions ADD COLUMN account_id INTEGER",
            "ALTER TABLE transactions ADD COLUMN suggested_account_id INTEGER",
            "ALTER TABLE transactions ADD COLUMN suggestion_reason VARCHAR",
            "ALTER TABLE user_categorization_rules ADD COLUMN account_id INTEGER",
            "ALTER TABLE archived_transactions ADD COLUMN account_id INTEGER",
            "ALTER TABLE archived_transactions ADD COLUMN account_code VARCHAR",
            "ALTER TABLE archived_transactions ADD COLUMN account_name VARCHAR",
            "ALTER TABLE clients ADD COLUMN legal_entity_type VARCHAR",
            "ALTER TABLE clients ADD COLUMN trading_capacity VARCHAR",
            "ALTER TABLE clients ADD COLUMN trade_type VARCHAR",
            "ALTER TABLE clients ADD COLUMN director_uses_company_card BOOLEAN DEFAULT 0",
        ]:
            try:
                conn.execute(text(ddl))
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore
