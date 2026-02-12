"""
Database migration: Add user_id column to user_categorization_rules table
This fixes the issue where learned rules disappear on new uploads
"""

import sqlite3
import os
import uuid

def migrate_database(db_path="statement_analyzer.db"):
    """Add user_id column and migrate existing data"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   The table will be created automatically on first app startup")
        return
    
    print(f"📊 Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='user_categorization_rules'
    """)
    
    if not cursor.fetchone():
        print("ℹ️  Table 'user_categorization_rules' doesn't exist yet")
        print("   It will be created automatically on first use")
        conn.close()
        return
    
    # Check if user_id column already exists
    cursor.execute("PRAGMA table_info(user_categorization_rules)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'user_id' in columns:
        print("✓ Column 'user_id' already exists")
        conn.close()
        return
    
    print("Adding 'user_id' column...")
    
    # Add user_id column (nullable first for migration)
    cursor.execute("""
        ALTER TABLE user_categorization_rules 
        ADD COLUMN user_id TEXT
    """)
    
    # Generate a migration user_id for existing rules
    # All existing rules will be assigned to a single "migrated" user
    migration_user_id = str(uuid.uuid4())
    
    cursor.execute("""
        UPDATE user_categorization_rules 
        SET user_id = ? 
        WHERE user_id IS NULL
    """, (migration_user_id,))
    
    rows_updated = cursor.rowcount
    
    # Create index on user_id
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_cat_rules_user_id 
        ON user_categorization_rules(user_id)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Migration complete!")
    print(f"  - Added 'user_id' column")
    print(f"  - Migrated {rows_updated} existing rules to user_id: {migration_user_id[:8]}...")
    print(f"  - Created index on user_id")
    print("\n📌 Important:")
    print("  Existing learned rules have been assigned to a migration user.")
    print("  New uploads will use a persistent user_id from the frontend.")
    print("  Users can view/manage their learned rules normally.")


if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "statement_analyzer.db"
    migrate_database(db_path)
