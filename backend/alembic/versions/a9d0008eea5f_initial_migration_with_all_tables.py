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
    # This migration is idempotent — the production DB was originally created via
    # SQLAlchemy create_all() so most objects already exist. All DDL uses IF NOT EXISTS
    # / IF EXISTS to avoid duplicate-object errors on re-run.
    conn = op.get_bind()

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
