"""Introduce Chart of Accounts (Phase 1 - additive).

Revision ID: b1c2d3e4f5a6
Revises: f8b3d2e9a1c4
Create Date: 2026-05-13 00:00:00.000000

Creates the accounts table and adds nullable FK / snapshot columns on:
  - transactions (account_id, suggested_account_id)
  - user_categorization_rules (account_id)
  - archived_transactions (account_id, account_code, account_name)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "f8b3d2e9a1c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _add_column_if_missing(conn, table_name: str, column: sa.Column) -> None:
    if not _has_column(conn, table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
            code VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            parent_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
            path VARCHAR NOT NULL DEFAULT '',
            level INTEGER NOT NULL DEFAULT 0,
            account_type VARCHAR NOT NULL,
            account_subtype VARCHAR,
            normal_balance VARCHAR NOT NULL,
            cash_flow_section VARCHAR NOT NULL DEFAULT 'none',
            is_vat_control BOOLEAN NOT NULL DEFAULT FALSE,
            vat_treatment VARCHAR,
            vat_rate DOUBLE PRECISION,
            is_postable BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            description VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_id ON accounts (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_client_id ON accounts (client_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_code ON accounts (code)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_parent_id ON accounts (parent_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_account_type ON accounts (account_type)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_account_subtype ON accounts (account_subtype)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_accounts_is_active ON accounts (is_active)"))
    conn.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS uq_accounts_client_code ON accounts (client_id, code)"))

    _add_column_if_missing(
        conn,
        "transactions",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
    )
    _add_column_if_missing(
        conn,
        "transactions",
        sa.Column("suggested_account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
    )
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_transactions_account_id ON transactions (account_id)"))

    _add_column_if_missing(
        conn,
        "user_categorization_rules",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id"), nullable=True),
    )
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_account_id "
        "ON user_categorization_rules (account_id)"
    ))

    _add_column_if_missing(conn, "archived_transactions", sa.Column("account_id", sa.Integer(), nullable=True))
    _add_column_if_missing(conn, "archived_transactions", sa.Column("account_code", sa.String(), nullable=True))
    _add_column_if_missing(conn, "archived_transactions", sa.Column("account_name", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("ALTER TABLE archived_transactions DROP COLUMN IF EXISTS account_name"))
    conn.execute(sa.text("ALTER TABLE archived_transactions DROP COLUMN IF EXISTS account_code"))
    conn.execute(sa.text("ALTER TABLE archived_transactions DROP COLUMN IF EXISTS account_id"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_user_categorization_rules_account_id"))
    conn.execute(sa.text("ALTER TABLE user_categorization_rules DROP COLUMN IF EXISTS account_id"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_transactions_account_id"))
    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS suggested_account_id"))
    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS account_id"))

    conn.execute(sa.text("DROP TABLE IF EXISTS accounts"))
