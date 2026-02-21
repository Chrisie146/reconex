"""
Migration script: Scope custom categories and learned rules to client_id.

What this does:
1. Adds client_id column to custom_categories table (if not present)
2. Adds client_id column to user_categorization_rules table (if not present)
3. Removes the old global unique constraint on custom_categories.name
4. Duplicates existing (unscoped) custom categories to ALL existing clients
5. Duplicates existing (unscoped) learned rules to ALL existing clients for that user

Run once after deploying the updated models. Safe to re-run (idempotent).

Usage:
    cd backend
    python migrate_client_scoped_categories.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from models import (
    engine,
    SessionLocal,
    Client,
    CustomCategory,
    UserCategorizationRule,
)


def column_exists(inspector, table_name: str, column_name: str) -> bool:
    columns = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in columns


def migrate():
    db = SessionLocal()
    inspector = inspect(engine)
    is_sqlite = str(engine.url).startswith("sqlite")

    print("=" * 60)
    print("Migration: Client-scoped categories & learned rules")
    print("=" * 60)

    # ── Step 1: Add client_id to custom_categories ─────────────────
    if not column_exists(inspector, "custom_categories", "client_id"):
        print("\n[1/4] Adding client_id column to custom_categories...")
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE custom_categories ADD COLUMN client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE"
            ))
        print("  ✓ Column added")
    else:
        print("\n[1/4] custom_categories.client_id already exists — skipping")

    # ── Step 2: Remove unique constraint on name (SQLite workaround) ──
    if is_sqlite:
        print("\n[2/4] SQLite: Rebuilding custom_categories table without unique constraint on name...")
        try:
            with engine.begin() as conn:
                # Check if unique index exists on name
                indexes = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='custom_categories'"
                )).fetchall()
                index_names = [r[0] for r in indexes]
                print(f"  Existing indexes: {index_names}")

                # SQLite table rebuild approach to remove unique constraint
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS custom_categories_new (
                        id INTEGER PRIMARY KEY,
                        client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE,
                        name VARCHAR(100) NOT NULL,
                        is_income BOOLEAN DEFAULT 0,
                        vat_applicable BOOLEAN DEFAULT 0,
                        vat_rate FLOAT DEFAULT 15.0,
                        created_at DATETIME
                    )
                """))
                conn.execute(text("""
                    INSERT OR IGNORE INTO custom_categories_new (id, client_id, name, is_income, vat_applicable, vat_rate, created_at)
                    SELECT id, client_id, name, is_income, vat_applicable, vat_rate, created_at
                    FROM custom_categories
                """))
                conn.execute(text("DROP TABLE custom_categories"))
                conn.execute(text("ALTER TABLE custom_categories_new RENAME TO custom_categories"))
            print("  ✓ Table rebuilt without unique constraint on name")
        except Exception as e:
            print(f"  ⚠ Table rebuild error: {e}")
    else:
        print("\n[2/4] Removing global unique constraint on custom_categories.name...")
        try:
            with engine.begin() as conn:
                conn.execute(text(
                    "DROP INDEX IF EXISTS ix_custom_categories_name"
                ))
                conn.execute(text(
                    "ALTER TABLE custom_categories DROP CONSTRAINT IF EXISTS custom_categories_name_key"
                ))
            print("  ✓ Unique constraint removed")
        except Exception as e:
            print(f"  ⚠ Could not remove constraint (may not exist): {e}")

    # ── Step 3: Add client_id to user_categorization_rules ─────────
    if not column_exists(inspector, "user_categorization_rules", "client_id"):
        print("\n[3/4] Adding client_id column to user_categorization_rules...")
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE user_categorization_rules ADD COLUMN client_id INTEGER REFERENCES clients(id) ON DELETE CASCADE"
            ))
        print("  ✓ Column added")
    else:
        print("\n[3/4] user_categorization_rules.client_id already exists — skipping")

    # ── Step 4: Duplicate existing unscoped data to all clients ────
    print("\n[4/4] Duplicating existing unscoped data to all clients...")

    # Get all unscoped custom categories
    unscoped_cats = db.query(CustomCategory).filter(
        CustomCategory.client_id.is_(None)
    ).all()
    print(f"  Found {len(unscoped_cats)} unscoped custom categories")

    # Get all clients grouped by user
    all_clients = db.query(Client).all()
    # Group clients by user_id (user_id is a string)
    user_clients: dict[str, list] = {}
    for c in all_clients:
        user_clients.setdefault(c.user_id, []).append(c)

    # Duplicate categories to all clients
    cats_created = 0
    for cat in unscoped_cats:
        for client_list in user_clients.values():
            for client in client_list:
                # Check if already exists for this client
                existing = db.query(CustomCategory).filter(
                    CustomCategory.client_id == client.id,
                    CustomCategory.name == cat.name
                ).first()
                if not existing:
                    new_cat = CustomCategory(
                        client_id=client.id,
                        name=cat.name,
                        is_income=cat.is_income,
                        vat_applicable=cat.vat_applicable,
                        vat_rate=cat.vat_rate,
                    )
                    db.add(new_cat)
                    cats_created += 1
    db.commit()
    print(f"  ✓ Created {cats_created} client-scoped category copies")

    # Clean up unscoped categories (now that copies exist)
    if unscoped_cats and cats_created > 0:
        for cat in unscoped_cats:
            db.delete(cat)
        db.commit()
        print(f"  ✓ Removed {len(unscoped_cats)} old unscoped categories")

    # Get all unscoped learned rules
    unscoped_rules = db.query(UserCategorizationRule).filter(
        UserCategorizationRule.client_id.is_(None)
    ).all()
    print(f"  Found {len(unscoped_rules)} unscoped learned rules")

    rules_created = 0
    for rule in unscoped_rules:
        user_id_str = rule.user_id
        clients_for_user = user_clients.get(user_id_str, [])
        for client in clients_for_user:
            existing = db.query(UserCategorizationRule).filter(
                UserCategorizationRule.user_id == user_id_str,
                UserCategorizationRule.client_id == client.id,
                UserCategorizationRule.pattern_type == rule.pattern_type,
                UserCategorizationRule.pattern_value == rule.pattern_value,
            ).first()
            if not existing:
                new_rule = UserCategorizationRule(
                    user_id=user_id_str,
                    client_id=client.id,
                    session_id=rule.session_id,
                    category=rule.category,
                    pattern_type=rule.pattern_type,
                    pattern_value=rule.pattern_value,
                    confidence_score=rule.confidence_score,
                    use_count=rule.use_count,
                    enabled=rule.enabled,
                )
                db.add(new_rule)
                rules_created += 1
    db.commit()
    print(f"  ✓ Created {rules_created} client-scoped learned rule copies")

    # Clean up unscoped learned rules
    if unscoped_rules and rules_created > 0:
        for rule in unscoped_rules:
            db.delete(rule)
        db.commit()
        print(f"  ✓ Removed {len(unscoped_rules)} old unscoped learned rules")

    # Create index on new columns
    print("\n  Creating indexes...")
    try:
        with engine.begin() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_custom_categories_client_id ON custom_categories(client_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_user_categorization_rules_client_id ON user_categorization_rules(client_id)"
            ))
        print("  ✓ Indexes created")
    except Exception as e:
        print(f"  ⚠ Index creation note: {e}")

    db.close()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print("\nNotes:")
    print("- New clients will start with NO custom categories or rules")
    print("- Use the /rules/clone endpoint to copy between clients")
    print("- Existing data has been duplicated to all current clients")


if __name__ == "__main__":
    migrate()
