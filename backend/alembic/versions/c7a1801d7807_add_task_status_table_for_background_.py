"""Add task_status table for background jobs

Revision ID: c7a1801d7807
Revises: 15118861dcfd
Create Date: 2026-02-12 14:43:08.597999

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7a1801d7807'
down_revision: Union[str, None] = '15118861dcfd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS task_status (
            id SERIAL PRIMARY KEY,
            task_id VARCHAR NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id),
            task_name VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            progress_percent INTEGER,
            progress_message VARCHAR,
            result VARCHAR,
            error_message VARCHAR,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_task_status_created_at ON task_status (created_at)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_task_status_id ON task_status (id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_task_status_status ON task_status (status)"))
    conn.execute(sa.text("CREATE UNIQUE INDEX IF NOT EXISTS ix_task_status_task_id ON task_status (task_id)"))
    conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_task_status_user_id ON task_status (user_id)"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP TABLE IF EXISTS task_status"))
