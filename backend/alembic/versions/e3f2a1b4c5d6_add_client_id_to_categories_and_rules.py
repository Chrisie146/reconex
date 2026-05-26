"""Add client_id to custom_categories and user_categorization_rules.

Revision ID: e3f2a1b4c5d6
Revises: 5a07ac224708
Create Date: 2026-02-24 12:00:00.000000

Backfills the client_id column that was previously added via the standalone
migrate_client_scoped_categories.py script but never tracked by Alembic.
Checks column existence through SQLAlchemy so the migration is idempotent on
both SQLite and PostgreSQL.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f2a1b4c5d6"
down_revision: Union[str, None] = "5a07ac224708"
branch_labels = None
depends_on = None


def _has_column(conn, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(conn)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _add_column_if_missing(conn, table_name: str, column: sa.Column) -> None:
    if not _has_column(conn, table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    conn = op.get_bind()

    _add_column_if_missing(
        conn,
        "custom_categories",
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_custom_categories_client_id "
        "ON custom_categories (client_id)"
    ))

    _add_column_if_missing(
        conn,
        "user_categorization_rules",
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_client_id "
        "ON user_categorization_rules (client_id)"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_user_categorization_rules_client_id"))
    conn.execute(sa.text("ALTER TABLE user_categorization_rules DROP COLUMN IF EXISTS client_id"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_custom_categories_client_id"))
    conn.execute(sa.text("ALTER TABLE custom_categories DROP COLUMN IF EXISTS client_id"))
