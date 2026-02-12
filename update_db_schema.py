"""
Script to update database schema for bank_source column
"""
import sqlite3
import os
from pathlib import Path

# Find the database file
db_path = "backend/statement_analyzer.db"

if not os.path.exists(db_path):
    print(f"[ERROR] Database not found at {db_path}")
    print("The database will be created automatically on first run.")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "bank_source" in columns:
        print("[OK] Column 'bank_source' already exists in transactions table")
    else:
        print("[INFO] Adding 'bank_source' column to transactions table...")
        cursor.execute("""
            ALTER TABLE transactions 
            ADD COLUMN bank_source TEXT DEFAULT 'unknown'
        """)
        conn.commit()
        print("[OK] Column 'bank_source' added successfully")
    
    # Verify the column exists
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\n[OK] Transaction table now has columns: {', '.join(columns)}")
    
    conn.close()
    print("\n[SUCCESS] Database schema updated successfully!")
    
except sqlite3.OperationalError as e:
    print(f"[ERROR] {e}")
    exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    exit(1)
