"""Add transaction mapping metadata.

Revision ID: d4e5f6a7b8c9
Revises: b1c2d3e4f5a6
Create Date: 2026-05-14 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
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
    _add_column_if_missing(conn, "transactions", sa.Column("mapping_confidence", sa.Float(), nullable=True))
    _add_column_if_missing(conn, "transactions", sa.Column("mapping_source", sa.String(), nullable=True))
    _add_column_if_missing(conn, "transactions", sa.Column("mapping_reason", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS mapping_reason"))
    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS mapping_source"))
    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS mapping_confidence"))
