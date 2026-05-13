"""Categorisation V2 — Phase A: system rules + entity-aware client fields

Revision ID: d4e5f6a7b8c9
Revises: b1c2d3e4f5a6
Create Date: 2026-05-13 12:00:00.000000

Phase A of the Categorisation Engine V2 rollout. Strictly additive.

Adds:
  - clients.legal_entity_type, trading_capacity, trade_type, director_uses_company_card
  - transactions.suggestion_reason
  - system_rules table (read-only, product-shipped categorisation rules)

Postgres only — SQLite uses init_db() lightweight ALTERs.
"""
from typing import Union, Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS legal_entity_type VARCHAR"
    ))
    conn.execute(sa.text(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS trading_capacity VARCHAR"
    ))
    conn.execute(sa.text(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS trade_type VARCHAR"
    ))
    conn.execute(sa.text(
        "ALTER TABLE clients ADD COLUMN IF NOT EXISTS director_uses_company_card BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    conn.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_clients_legal_entity_type ON clients (legal_entity_type)"
    ))

    conn.execute(sa.text(
        "ALTER TABLE transactions ADD COLUMN IF NOT EXISTS suggestion_reason VARCHAR"
    ))

    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS system_rules (
            id SERIAL PRIMARY KEY,
            code VARCHAR NOT NULL UNIQUE,
            name VARCHAR NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            conditions VARCHAR NOT NULL,
            purpose VARCHAR NOT NULL,
            coa_hint VARCHAR,
            confidence VARCHAR NOT NULL DEFAULT 'medium',
            entity_filter VARCHAR,
            description VARCHAR,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_system_rules_code ON system_rules (code)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_system_rules_priority ON system_rules (priority)"))


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("DROP TABLE IF EXISTS system_rules CASCADE"))

    conn.execute(sa.text("ALTER TABLE transactions DROP COLUMN IF EXISTS suggestion_reason"))

    conn.execute(sa.text("DROP INDEX IF EXISTS ix_clients_legal_entity_type"))
    conn.execute(sa.text("ALTER TABLE clients DROP COLUMN IF EXISTS director_uses_company_card"))
    conn.execute(sa.text("ALTER TABLE clients DROP COLUMN IF EXISTS trade_type"))
    conn.execute(sa.text("ALTER TABLE clients DROP COLUMN IF EXISTS trading_capacity"))
    conn.execute(sa.text("ALTER TABLE clients DROP COLUMN IF EXISTS legal_entity_type"))
