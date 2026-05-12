"""Initial migration with all tables

Revision ID: a9d0008eea5f
Revises: 
Create Date: 2026-02-12 14:07:03.735016

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9d0008eea5f'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is fully idempotent.
    # For a fresh database: CREATE TABLE IF NOT EXISTS creates all core tables.
    # For an existing database: the CREATE statements are no-ops, ALTER ops patch schema.
    conn = op.get_bind()

    # ── Create core tables if they do not exist ────────────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR NOT NULL UNIQUE,
            hashed_password VARCHAR NOT NULL,
            full_name VARCHAR,
            is_active BOOLEAN DEFAULT TRUE,
            is_superuser BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_clients_id ON clients (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_clients_user_id ON clients (user_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id),
            session_id VARCHAR,
            invoice_id INTEGER,
            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            amount DOUBLE PRECISION NOT NULL,
            category VARCHAR NOT NULL,
            vat_amount DOUBLE PRECISION,
            amount_excl_vat DOUBLE PRECISION,
            amount_incl_vat DOUBLE PRECISION,
            bank_source VARCHAR DEFAULT 'unknown',
            suggested_category VARCHAR,
            balance_verified INTEGER,
            balance_difference DOUBLE PRECISION,
            validation_message VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transactions_id ON transactions (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transactions_session_id ON transactions (session_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transactions_client_id ON transactions (client_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS reconciliations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR,
            client_id INTEGER REFERENCES clients(id),
            month VARCHAR,
            opening_balance DOUBLE PRECISION,
            closing_balance DOUBLE PRECISION,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reconciliations_id ON reconciliations (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reconciliations_session_id ON reconciliations (session_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reconciliations_client_id ON reconciliations (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reconciliations_month ON reconciliations (month)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS overall_reconciliations (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            system_opening_balance DOUBLE PRECISION,
            bank_closing_balance DOUBLE PRECISION,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_id ON overall_reconciliations (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_session_id ON overall_reconciliations (session_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_client_id ON overall_reconciliations (client_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS transaction_merchants (
            id SERIAL PRIMARY KEY,
            transaction_id INTEGER,
            session_id VARCHAR,
            merchant VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transaction_merchants_id ON transaction_merchants (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transaction_merchants_transaction_id ON transaction_merchants (transaction_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transaction_merchants_session_id ON transaction_merchants (session_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS session_states (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR UNIQUE,
            locked INTEGER DEFAULT 0,
            friendly_name VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_session_states_id ON session_states (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_session_states_session_id ON session_states (session_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS rules (
            id SERIAL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id),
            name VARCHAR NOT NULL,
            enabled INTEGER DEFAULT 1,
            priority INTEGER DEFAULT 100,
            conditions VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            auto_apply INTEGER DEFAULT 0,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_rules_id ON rules (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_rules_client_id ON rules (client_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id),
            session_id VARCHAR,
            supplier_name VARCHAR NOT NULL,
            invoice_date DATE NOT NULL,
            invoice_number VARCHAR,
            total_amount DOUBLE PRECISION NOT NULL,
            vat_amount DOUBLE PRECISION,
            file_reference VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_id ON invoices (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_client_id ON invoices (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoices_session_id ON invoices (session_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS invoice_matches (
            id SERIAL PRIMARY KEY,
            invoice_id INTEGER,
            transaction_id INTEGER,
            confidence INTEGER NOT NULL,
            explanation VARCHAR,
            status VARCHAR DEFAULT 'suggested',
            suggested_at TIMESTAMP,
            confirmed_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoice_matches_id ON invoice_matches (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoice_matches_invoice_id ON invoice_matches (invoice_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_invoice_matches_transaction_id ON invoice_matches (transaction_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS user_categorization_rules (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            session_id VARCHAR,
            category VARCHAR NOT NULL,
            pattern_type VARCHAR NOT NULL,
            pattern_value VARCHAR NOT NULL,
            confidence_score DOUBLE PRECISION DEFAULT 1.0,
            use_count INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            last_used TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_id ON user_categorization_rules (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_user_id ON user_categorization_rules (user_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_client_id ON user_categorization_rules (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_session_id ON user_categorization_rules (session_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS custom_categories (
            id SERIAL PRIMARY KEY,
            client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
            name VARCHAR NOT NULL,
            is_income INTEGER DEFAULT 0,
            vat_applicable INTEGER DEFAULT 0,
            vat_rate DOUBLE PRECISION DEFAULT 15.0,
            created_at TIMESTAMP,
            CONSTRAINT uq_custom_categories_client_name UNIQUE (client_id, name)
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_custom_categories_id ON custom_categories (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_custom_categories_name ON custom_categories (name)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_custom_categories_client_id ON custom_categories (client_id)"))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS session_vat_config (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR NOT NULL UNIQUE,
            vat_enabled INTEGER DEFAULT 0,
            default_vat_rate DOUBLE PRECISION DEFAULT 15.0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_session_vat_config_id ON session_vat_config (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_session_vat_config_session_id ON session_vat_config (session_id)"))

    # ── clients.user_id: ensure it is INTEGER ─────────────────────────────────
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='clients' AND column_name='user_id') = 'character varying' THEN
                ALTER TABLE clients ALTER COLUMN user_id TYPE INTEGER USING user_id::integer;
                ALTER TABLE clients ALTER COLUMN user_id SET NOT NULL;
            END IF;
        END $$
    """))

    # ── FK: clients.user_id -> users.id ───────────────────────────────────────
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'clients'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'user_id'
            ) THEN
                ALTER TABLE clients ADD CONSTRAINT clients_user_id_fkey
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
            END IF;
        END $$
    """))

    # ── overall_reconciliations: swap old index names for new ones ─────────────
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_overall_reconciliations_client_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_overall_reconciliations_session_id"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_session_id ON overall_reconciliations (session_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_client_id ON overall_reconciliations (client_id)"))

    # ── FK: overall_reconciliations.client_id -> clients.id ───────────────────
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'overall_reconciliations'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'client_id'
            ) THEN
                ALTER TABLE overall_reconciliations ADD CONSTRAINT overall_reconciliations_client_id_fkey
                    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE;
            END IF;
        END $$
    """))

    # ── reconciliations: swap old index name for new one ──────────────────────
    conn.execute(sa.text("DROP INDEX IF EXISTS idx_reconciliations_client_id"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_reconciliations_client_id ON reconciliations (client_id)"))

    # ── FK: reconciliations.client_id -> clients.id ───────────────────────────
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'reconciliations'
                  AND tc.constraint_type = 'FOREIGN KEY'
                  AND kcu.column_name = 'client_id'
            ) THEN
                ALTER TABLE reconciliations ADD CONSTRAINT reconciliations_client_id_fkey
                    FOREIGN KEY (client_id) REFERENCES clients(id);
            END IF;
        END $$
    """))

    # ── transactions: ALTER COLUMN type changes (REAL -> DOUBLE PRECISION / VARCHAR) ─
    # REAL and FLOAT/DOUBLE PRECISION are already compatible in PostgreSQL —
    # these are no-ops if the column is already the right type.
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='vat_amount') = 'real' THEN
                ALTER TABLE transactions ALTER COLUMN vat_amount TYPE DOUBLE PRECISION;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='amount_excl_vat') = 'real' THEN
                ALTER TABLE transactions ALTER COLUMN amount_excl_vat TYPE DOUBLE PRECISION;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='amount_incl_vat') = 'real' THEN
                ALTER TABLE transactions ALTER COLUMN amount_incl_vat TYPE DOUBLE PRECISION;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='balance_difference') = 'real' THEN
                ALTER TABLE transactions ALTER COLUMN balance_difference TYPE DOUBLE PRECISION;
            END IF;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF (SELECT data_type FROM information_schema.columns
                WHERE table_name='transactions' AND column_name='validation_message') = 'text' THEN
                ALTER TABLE transactions ALTER COLUMN validation_message TYPE VARCHAR;
            END IF;
        END $$
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_reconciliations_client_id"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_reconciliations_client_id ON reconciliations (client_id)"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_overall_reconciliations_client_id"))
    conn.execute(sa.text("DROP INDEX IF EXISTS ix_overall_reconciliations_session_id"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_overall_reconciliations_session_id ON overall_reconciliations (session_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS idx_overall_reconciliations_client_id ON overall_reconciliations (client_id)"))
