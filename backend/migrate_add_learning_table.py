"""
Database migration: Add user_categorization_rules table
Run this to add the auto-learning feature to existing databases
"""

import sqlite3
import os

def migrate_database(db_path="statement_analyzer.db"):
    """Add user_categorization_rules table to existing database"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        print("   The table will be created automatically on first app startup")
        return
    
    print(f"📊 Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if table already exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='user_categorization_rules'
    """)
    
    if cursor.fetchone():
        print("✓ Table 'user_categorization_rules' already exists")
        conn.close()
        return
    
    # Create the table
    print("Creating table 'user_categorization_rules'...")
    
    cursor.execute("""
        CREATE TABLE user_categorization_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            category TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_value TEXT NOT NULL,
            confidence_score REAL DEFAULT 1.0,
            use_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used TIMESTAMP,
            enabled INTEGER DEFAULT 1
        )
    """)
    
    # Create indexes for performance
    print("Creating indexes...")
    
    cursor.execute("""
        CREATE INDEX idx_user_cat_rules_session 
        ON user_categorization_rules(session_id)
    """)
    
    cursor.execute("""
        CREATE INDEX idx_user_cat_rules_pattern 
        ON user_categorization_rules(pattern_type, pattern_value)
    """)
    
    cursor.execute("""
        CREATE INDEX idx_user_cat_rules_enabled 
        ON user_categorization_rules(enabled)
    """)
    
    conn.commit()
    conn.close()
    
    print("✓ Migration complete!")
    print("\nNew table structure:")
    print("  - id: Primary key")
    print("  - session_id: User/session identifier")
    print("  - category: Target category")
    print("  - pattern_type: 'exact', 'merchant', 'starts_with', 'contains'")
    print("  - pattern_value: The pattern to match")
    print("  - confidence_score: Rule reliability (0.0-1.0)")
    print("  - use_count: Number of times rule was applied")
    print("  - created_at: When rule was created")
    print("  - last_used: Last time rule was applied")
    print("  - enabled: 1=active, 0=disabled")


if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "statement_analyzer.db"
    migrate_database(db_path)
