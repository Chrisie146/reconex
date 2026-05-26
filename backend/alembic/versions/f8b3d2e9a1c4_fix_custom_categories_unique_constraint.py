"""Fix custom_categories unique constraint: name-only -> (client_id, name).

Revision ID: f8b3d2e9a1c4
Revises: e3f2a1b4c5d6
Create Date: 2026-02-26 18:30:00.000000

The original unique index on custom_categories.name was global across all
clients. This migration replaces it with per-client uniqueness.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8b3d2e9a1c4"
down_revision: Union[str, None] = "e3f2a1b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_custom_categories_name"))
    if is_postgres:
        conn.execute(sa.text(
            "ALTER TABLE custom_categories "
            "DROP CONSTRAINT IF EXISTS ix_custom_categories_name"
        ))

    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_custom_categories_name "
        "ON custom_categories (name)"
    ))

    if is_postgres:
        conn.execute(sa.text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE table_name = 'custom_categories'
                      AND constraint_name = 'uq_custom_categories_client_name'
                ) THEN
                    ALTER TABLE custom_categories
                        ADD CONSTRAINT uq_custom_categories_client_name
                        UNIQUE (client_id, name);
                END IF;
            END $$
        """))
    else:
        conn.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_custom_categories_client_name "
            "ON custom_categories (client_id, name)"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        conn.execute(sa.text(
            "ALTER TABLE custom_categories "
            "DROP CONSTRAINT IF EXISTS uq_custom_categories_client_name"
        ))
    else:
        conn.execute(sa.text("DROP INDEX IF EXISTS uq_custom_categories_client_name"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_custom_categories_name"))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX ix_custom_categories_name "
        "ON custom_categories (name)"
    ))
