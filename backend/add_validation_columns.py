#!/usr/bin/env python
"""
Migration: Add balance validation metadata columns to transactions table
Columns: balance_verified (int), balance_difference (float), validation_message (string)
"""
import sqlite3
import os

db_path = "backend/statement_analyzer.db"

if not os.path.exists(db_path):
    print(f"[ERROR] Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    columns_to_add = [
        ("balance_verified", "INTEGER"),
        ("balance_difference", "REAL"),
        ("validation_message", "TEXT")
    ]
    
    added_count = 0
    for col_name, col_type in columns_to_add:
        if col_name in columns:
            print(f"[OK] Column '{col_name}' already exists")
        else:
            print(f"[INFO] Adding column '{col_name}' ({col_type})...")
            cursor.execute(f"""
                ALTER TABLE transactions 
                ADD COLUMN {col_name} {col_type} DEFAULT NULL
            """)
            added_count += 1
    
    if added_count > 0:
        conn.commit()
        print(f"[OK] Added {added_count} columns successfully")
    else:
        print("[OK] All columns already exist - no changes needed")
    
    # Verify the columns exist
    cursor.execute("PRAGMA table_info(transactions)")
    final_columns = [row[1] for row in cursor.fetchall()]
    print(f"\n[OK] Transaction table now has columns: {', '.join(final_columns)}")
    
    conn.close()
    print("\n[SUCCESS] Database schema updated successfully!")
    
except sqlite3.OperationalError as e:
    print(f"[ERROR] {e}")
    exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    exit(1)
