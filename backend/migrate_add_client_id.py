"""
Database migration: Add client_id column to transactions table
This enables multi-client support for the statement analyzer
"""

import sqlite3
import os

def migrate_database(db_path="statement_analyzer.db"):
    """Add client_id column to transactions table"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "client_id" in columns:
        print("✓ Column 'client_id' already exists in transactions table")
        conn.close()
        return
    
    print("Adding 'client_id' column to transactions table...")
    
    try:
        # Add client_id column (nullable initially)
        cursor.execute("""
            ALTER TABLE transactions 
            ADD COLUMN client_id INTEGER
        """)
        
        # Create index for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_transactions_client_id 
            ON transactions(client_id)
        """)
        
        conn.commit()
        print("✓ Column 'client_id' added successfully")
        print("✓ Index created on client_id")
        
        # Count transactions without client_id
        cursor.execute("SELECT COUNT(*) FROM transactions WHERE client_id IS NULL")
        null_count = cursor.fetchone()[0]
        
        if null_count > 0:
            print(f"\n⚠️  Found {null_count} transactions without client_id")
            print("   These are from uploads before multi-client support was added.")
            print("   They can still be accessed via session_id.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    import sys
    
    db_path = sys.argv[1] if len(sys.argv) > 1 else "statement_analyzer.db"
    migrate_database(db_path)
