"""
Migration script to add VAT fields to existing database tables.
Run this once to update your database schema with VAT support.
"""
import sqlite3
import os

# Get the database path
DB_PATH = os.path.join(os.path.dirname(__file__), "statement_analyzer.db")

def migrate_database():
    """Add VAT columns to existing tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"Migrating database at: {DB_PATH}")
    
    try:
        # Add VAT columns to transactions table
        print("Adding VAT columns to transactions table...")
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN vat_amount REAL")
            print("  ✓ Added vat_amount column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - vat_amount column already exists")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN amount_excl_vat REAL")
            print("  ✓ Added amount_excl_vat column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - amount_excl_vat column already exists")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE transactions ADD COLUMN amount_incl_vat REAL")
            print("  ✓ Added amount_incl_vat column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - amount_incl_vat column already exists")
            else:
                raise
        
        # Add VAT columns to custom_categories table
        print("\nAdding VAT columns to custom_categories table...")
        try:
            cursor.execute("ALTER TABLE custom_categories ADD COLUMN vat_applicable INTEGER DEFAULT 1")
            print("  ✓ Added vat_applicable column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - vat_applicable column already exists")
            else:
                raise
        
        try:
            cursor.execute("ALTER TABLE custom_categories ADD COLUMN vat_rate REAL DEFAULT 15.0")
            print("  ✓ Added vat_rate column")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("  - vat_rate column already exists")
            else:
                raise
        
        # Create session_vat_config table if it doesn't exist
        print("\nCreating session_vat_config table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_vat_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                vat_enabled INTEGER NOT NULL DEFAULT 0,
                default_vat_rate REAL NOT NULL DEFAULT 15.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✓ session_vat_config table created/verified")
        
        # Commit all changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show table schemas for verification
        print("\n--- Verification ---")
        cursor.execute("PRAGMA table_info(transactions)")
        trans_cols = cursor.fetchall()
        print("\nTransactions table columns:")
        for col in trans_cols:
            print(f"  - {col[1]} ({col[2]})")
        
        cursor.execute("PRAGMA table_info(custom_categories)")
        cat_cols = cursor.fetchall()
        print("\nCustom_categories table columns:")
        for col in cat_cols:
            print(f"  - {col[1]} ({col[2]})")
        
        cursor.execute("PRAGMA table_info(session_vat_config)")
        vat_cols = cursor.fetchall()
        print("\nSession_vat_config table columns:")
        for col in vat_cols:
            print(f"  - {col[1]} ({col[2]})")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
