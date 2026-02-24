"""Add client_id to custom_categories and user_categorization_rules

Revision ID: e3f2a1b4c5d6
Revises: 5a07ac224708
Create Date: 2026-02-24 12:00:00.000000

Backfills the client_id column that was previously added via the standalone
migrate_client_scoped_categories.py script but never tracked by Alembic.
Uses PostgreSQL's ADD COLUMN IF NOT EXISTS so it is fully idempotent.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e3f2a1b4c5d6'
down_revision: Union[str, None] = '5a07ac224708'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add client_id to custom_categories (idempotent via IF NOT EXISTS)
    conn.execute(sa.text(
        "ALTER TABLE custom_categories "
        "ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_custom_categories_client_id "
        "ON custom_categories (client_id)"
    ))

    # Add client_id to user_categorization_rules (idempotent via IF NOT EXISTS)
    conn.execute(sa.text(
        "ALTER TABLE user_categorization_rules "
        "ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_client_id "
        "ON user_categorization_rules (client_id)"
    ))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_user_categorization_rules_client_id"
    ))
    conn.execute(sa.text(
        "ALTER TABLE user_categorization_rules DROP COLUMN IF EXISTS client_id"
    ))

    conn.execute(sa.text(
        "DROP INDEX IF EXISTS ix_custom_categories_client_id"
    ))
    conn.execute(sa.text(
        "ALTER TABLE custom_categories DROP COLUMN IF EXISTS client_id"
    ))
