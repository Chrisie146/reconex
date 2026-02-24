"""add_financial_years_archive_and_backup_tables

Revision ID: 5a07ac224708
Revises: c7a1801d7807
Create Date: 2026-02-23 20:01:22.312774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a07ac224708'
down_revision: Union[str, None] = 'c7a1801d7807'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS backup_records (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            label VARCHAR NOT NULL,
            status VARCHAR,
            file_size_bytes INTEGER,
            error_message VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_backup_records_created_at ON backup_records (created_at)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_backup_records_id ON backup_records (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_backup_records_user_id ON backup_records (user_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS financial_years (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            label VARCHAR NOT NULL,
            year_start DATE NOT NULL,
            year_end DATE NOT NULL,
            status VARCHAR,
            archived_at TIMESTAMP,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_financial_years_client_id ON financial_years (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_financial_years_id ON financial_years (id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_invoice_matches (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            original_invoice_id INTEGER NOT NULL,
            original_transaction_id INTEGER NOT NULL,
            confidence INTEGER NOT NULL,
            explanation VARCHAR,
            status VARCHAR,
            suggested_at TIMESTAMP,
            confirmed_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoice_matches_financial_year_id ON archived_invoice_matches (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoice_matches_id ON archived_invoice_matches (id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_invoices (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            session_id VARCHAR NOT NULL,
            supplier_name VARCHAR NOT NULL,
            invoice_date DATE NOT NULL,
            invoice_number VARCHAR,
            total_amount DOUBLE PRECISION NOT NULL,
            vat_amount DOUBLE PRECISION,
            file_reference VARCHAR,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoices_client_id ON archived_invoices (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoices_financial_year_id ON archived_invoices (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoices_id ON archived_invoices (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_invoices_session_id ON archived_invoices (session_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_overall_reconciliations (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            session_id VARCHAR,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            system_opening_balance DOUBLE PRECISION,
            bank_closing_balance DOUBLE PRECISION,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_overall_reconciliations_client_id ON archived_overall_reconciliations (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_overall_reconciliations_financial_year_id ON archived_overall_reconciliations (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_overall_reconciliations_id ON archived_overall_reconciliations (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_overall_reconciliations_session_id ON archived_overall_reconciliations (session_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_reconciliations (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            session_id VARCHAR,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            month VARCHAR,
            opening_balance DOUBLE PRECISION,
            closing_balance DOUBLE PRECISION,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_reconciliations_client_id ON archived_reconciliations (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_reconciliations_financial_year_id ON archived_reconciliations (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_reconciliations_id ON archived_reconciliations (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_reconciliations_month ON archived_reconciliations (month)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_reconciliations_session_id ON archived_reconciliations (session_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_sessions (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            session_id VARCHAR NOT NULL,
            locked INTEGER,
            friendly_name VARCHAR,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_sessions_client_id ON archived_sessions (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_sessions_financial_year_id ON archived_sessions (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_sessions_id ON archived_sessions (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_sessions_session_id ON archived_sessions (session_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_transaction_merchants (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            original_transaction_id INTEGER NOT NULL,
            session_id VARCHAR NOT NULL,
            merchant VARCHAR,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transaction_merchants_financial_year_id ON archived_transaction_merchants (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transaction_merchants_id ON archived_transaction_merchants (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transaction_merchants_session_id ON archived_transaction_merchants (session_id)"))
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS archived_transactions (
            id SERIAL PRIMARY KEY,
            financial_year_id INTEGER NOT NULL REFERENCES financial_years(id) ON DELETE CASCADE,
            original_id INTEGER NOT NULL,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            session_id VARCHAR NOT NULL,
            original_invoice_id INTEGER,
            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            category VARCHAR NOT NULL,
            vat_amount DOUBLE PRECISION,
            amount_excl_vat DOUBLE PRECISION,
            amount_incl_vat DOUBLE PRECISION,
            bank_source VARCHAR,
            balance_verified INTEGER,
            balance_difference DOUBLE PRECISION,
            validation_message VARCHAR,
            original_created_at TIMESTAMP,
            archived_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transactions_client_id ON archived_transactions (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transactions_financial_year_id ON archived_transactions (financial_year_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transactions_id ON archived_transactions (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_archived_transactions_session_id ON archived_transactions (session_id)"))


def downgrade() -> None:
    conn = op.get_bind()
    # Drop in reverse dependency order
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_transactions"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_transaction_merchants"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_sessions"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_reconciliations"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_overall_reconciliations"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_invoices"))
    conn.execute(sa.text("DROP TABLE IF EXISTS archived_invoice_matches"))
    conn.execute(sa.text("DROP TABLE IF EXISTS financial_years"))
    conn.execute(sa.text("DROP TABLE IF EXISTS backup_records"))
