"""
Database models for Bank Statement Analyzer
Handles storage of transactions and session data
"""

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, create_engine, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
    created_at = Column(DateTime, default=datetime.utcnow)


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
    category = Column(String, nullable=False)  # Rent, Utilities, Fuel, Groceries, Fees, Income, Other
    
    # VAT calculation fields (when VAT is enabled)
    vat_amount = Column(Float, nullable=True)  # Calculated VAT amount
    amount_excl_vat = Column(Float, nullable=True)  # Amount excluding VAT
    amount_incl_vat = Column(Float, nullable=True)  # Amount including VAT (same as amount when VAT applies)
    
    # Bank source tracking
    bank_source = Column(String, nullable=True, default="unknown")  # standard_bank, absa, capitec, unknown
    
    # Balance validation metadata (for production transparency)
    balance_verified = Column(Integer, nullable=True)  # 1=True, 0=False, NULL=None/no balance
    balance_difference = Column(Float, nullable=True)  # Absolute difference from expected balance
    validation_message = Column(String, nullable=True)  # Human-readable validation result
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


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
    category = Column(String, nullable=False)
    
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
        # Unique category name per client (replaces old global unique on name)
        # client_id=NULL entries are legacy/global and still allowed
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
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
