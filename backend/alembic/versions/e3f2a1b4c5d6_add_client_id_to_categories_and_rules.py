"""Add client_id to custom_categories and user_categorization_rules

Revision ID: e3f2a1b4c5d6
Revises: 5a07ac224708
Create Date: 2026-02-24 12:00:00.000000

Backfills the client_id column that was previously added via the standalone
migrate_client_scoped_categories.py script but never tracked by Alembic.
Safe to run on databases that already have the column (uses CHECK IF NOT EXISTS logic).
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = 'e3f2a1b4c5d6'
down_revision: Union[str, None] = '5a07ac224708'
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    # Add client_id to custom_categories (nullable, FK to clients.id)
    if not _column_exists("custom_categories", "client_id"):
        op.add_column(
            "custom_categories",
            sa.Column(
                "client_id",
                sa.Integer(),
                sa.ForeignKey("clients.id", ondelete="CASCADE"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index(
            "ix_custom_categories_client_id",
            "custom_categories",
            ["client_id"],
            unique=False,
        )

    # Add client_id to user_categorization_rules (nullable, FK to clients.id)
    if not _column_exists("user_categorization_rules", "client_id"):
        op.add_column(
            "user_categorization_rules",
            sa.Column(
                "client_id",
                sa.Integer(),
                sa.ForeignKey("clients.id", ondelete="CASCADE"),
                nullable=True,
                index=True,
            ),
        )
        op.create_index(
            "ix_user_categorization_rules_client_id",
            "user_categorization_rules",
            ["client_id"],
            unique=False,
        )


def downgrade() -> None:
    # Drop index + column from user_categorization_rules
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    ucr_indexes = [idx["name"] for idx in inspector.get_indexes("user_categorization_rules")]
    if "ix_user_categorization_rules_client_id" in ucr_indexes:
        op.drop_index("ix_user_categorization_rules_client_id", table_name="user_categorization_rules")
    if _column_exists("user_categorization_rules", "client_id"):
        op.drop_column("user_categorization_rules", "client_id")

    # Drop index + column from custom_categories
    cc_indexes = [idx["name"] for idx in inspector.get_indexes("custom_categories")]
    if "ix_custom_categories_client_id" in cc_indexes:
        op.drop_index("ix_custom_categories_client_id", table_name="custom_categories")
    if _column_exists("custom_categories", "client_id"):
        op.drop_column("custom_categories", "client_id")
