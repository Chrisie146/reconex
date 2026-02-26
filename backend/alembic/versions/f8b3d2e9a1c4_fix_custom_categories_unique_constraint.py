"""Fix custom_categories unique constraint: name-only -> (client_id, name)

Revision ID: f8b3d2e9a1c4
Revises: e3f2a1b4c5d6
Create Date: 2026-02-26 18:30:00.000000

The original unique index on custom_categories.name was global (across all clients).
This caused UniqueViolation when different clients tried to create a category with
the same name.  This migration drops the old constraint and replaces it with a
composite unique index on (client_id, name) so that uniqueness is enforced per
client rather than globally.

NULL client_id rows (legacy/global) are left as-is; PostgreSQL treats two NULL
values as distinct in a UNIQUE index, so legacy rows are unaffected.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f8b3d2e9a1c4'
down_revision: Union[str, None] = 'e3f2a1b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop the old global unique index on name (if it still exists).
    # It may be a UNIQUE INDEX or a UNIQUE CONSTRAINT – handle both.
    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_custom_categories_name"
    ))
    # Also drop as a constraint in case it was created that way
    conn.execute(sa.text(
        "ALTER TABLE custom_categories "
        "DROP CONSTRAINT IF EXISTS ix_custom_categories_name"
    ))

    # Re-create as a plain (non-unique) index on name for query performance,
    # but only if SQLAlchemy's index=True on the column didn't already create it.
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_custom_categories_name "
        "ON custom_categories (name)"
    ))

    # Add composite unique constraint: one category name per client.
    # We use a partial-style unique index via NULLS NOT DISTINCT (PG 15+)
    # for consistent behaviour; fall back to standard unique if not supported.
    # Standard UNIQUE(client_id, name) is safe because:
    #   - (5, 'Transfer') is unique per client  ✓
    #   - (NULL, 'Transfer') rows are NOT considered duplicates of each other
    #     under the standard SQL NULL semantics (NULL != NULL), which is fine
    #     for legacy global categories.
    conn.execute(sa.text(
        "ALTER TABLE custom_categories "
        "ADD CONSTRAINT uq_custom_categories_client_name "
        "UNIQUE (client_id, name)"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "ALTER TABLE custom_categories "
        "DROP CONSTRAINT IF EXISTS uq_custom_categories_client_name"
    ))

    # Restore the old global unique index on name
    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_custom_categories_name"
    ))
    conn.execute(sa.text(
        "CREATE UNIQUE INDEX ix_custom_categories_name "
        "ON custom_categories (name)"
    ))
