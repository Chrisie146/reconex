"""Add file_access_logs table for audit trail

Revision ID: 15118861dcfd
Revises: a9d0008eea5f
Create Date: 2026-02-12 14:29:36.798133

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15118861dcfd'
down_revision: Union[str, None] = 'a9d0008eea5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS file_access_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            invoice_id INTEGER REFERENCES invoices(id),
            file_key VARCHAR NOT NULL,
            action VARCHAR NOT NULL,
            ip_address VARCHAR,
            user_agent VARCHAR,
            storage_backend VARCHAR,
            created_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_file_access_logs_created_at ON file_access_logs (created_at)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_file_access_logs_id ON file_access_logs (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_file_access_logs_invoice_id ON file_access_logs (invoice_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_file_access_logs_user_id ON file_access_logs (user_id)"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS file_access_logs"))
