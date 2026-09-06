"""Add privacy-safe LLM statement failure metadata.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-06 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_statement_failures",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=True),
        sa.Column("layout_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("validation_codes", sa.String(), nullable=False, server_default="[]"),
        sa.Column("model_id", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_llm_statement_failures_document_id", "llm_statement_failures", ["document_id"])
    op.create_index("ix_llm_statement_failures_user_id", "llm_statement_failures", ["user_id"])
    op.create_index("ix_llm_statement_failures_client_id", "llm_statement_failures", ["client_id"])
    op.create_index("ix_llm_statement_failures_layout_id", "llm_statement_failures", ["layout_id"])
    op.create_index("ix_llm_statement_failures_status", "llm_statement_failures", ["status"])
    op.create_index("ix_llm_statement_failures_created_at", "llm_statement_failures", ["created_at"])


def downgrade() -> None:
    op.drop_table("llm_statement_failures")
