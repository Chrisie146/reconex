#!/usr/bin/env python3
"""
Migration script: Add invoice_id column to transactions table
Run this once to add support for linking confirmed invoices to transactions.
"""

import sqlite3
import sys
from pathlib import Path

# Find the database file (prefer backend-local DB used by the app)
backend_db = Path(__file__).parent / "statement_analyzer.db"
root_db = Path(__file__).parent.parent / "statement_analyzer.db"
db_path = backend_db if backend_db.exists() else root_db

if not db_path.exists():
    print(f"ERROR: Database not found at {db_path}")
    sys.exit(1)

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "invoice_id" in columns:
        print("✓ Column 'invoice_id' already exists in transactions table")
        conn.close()
        sys.exit(0)
    
    print("Adding 'invoice_id' column to transactions table...")
    cursor.execute("ALTER TABLE transactions ADD COLUMN invoice_id INTEGER NULL")
    conn.commit()
    
    # Verify the column was added
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "invoice_id" in columns:
        print("✓ Successfully added 'invoice_id' column to transactions table")
        print("\nMigration complete! You can now restart the backend.")
        conn.close()
        sys.exit(0)
    else:
        print("ERROR: Column was not added successfully")
        conn.close()
        sys.exit(1)
        
except sqlite3.OperationalError as e:
    print(f"Database error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
