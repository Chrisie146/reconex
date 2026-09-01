"""Fix PostgreSQL auto-generated IDs for Chart of Accounts.

The original accounts migration used ``INTEGER PRIMARY KEY`` in raw SQL.
That auto-generates IDs in SQLite, but PostgreSQL requires an explicit
sequence/default for inserts that omit ``id``.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Keep this idempotent so it is safe if a deployment is retried.
    op.execute(sa.text("""
        CREATE SEQUENCE IF NOT EXISTS accounts_id_seq;
        ALTER SEQUENCE accounts_id_seq OWNED BY accounts.id;
        ALTER TABLE accounts
            ALTER COLUMN id SET DEFAULT nextval('accounts_id_seq');
        SELECT setval(
            'accounts_id_seq',
            COALESCE((SELECT MAX(id) FROM accounts), 0) + 1,
            false
        );
    """))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text(
        "ALTER TABLE accounts ALTER COLUMN id DROP DEFAULT"
    ))
    op.execute(sa.text("DROP SEQUENCE IF EXISTS accounts_id_seq"))
