#!/usr/bin/env python
"""
Migration: Add is_income field to custom_categories table

This migration adds support for classifying custom categories as either:
- Income/Sales (VAT Output) - is_income = 1
- Expenses (VAT Input) - is_income = 0

Run this script to update existing databases.
"""

import sqlite3
import sys
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "statement_analyzer.db")

def migrate():
    """Add is_income column to custom_categories table"""
    print(f"Migrating database: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        print("   Creating new database with updated schema...")
        from models import init_db
        init_db()
        print("✅ Database created with new schema")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(custom_categories)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'is_income' in columns:
            print("✅ Migration already applied - is_income column exists")
            return
        
        print("Adding is_income column to custom_categories...")
        
        # Add the new column with default value 0 (expense)
        cursor.execute("""
            ALTER TABLE custom_categories 
            ADD COLUMN is_income INTEGER DEFAULT 0
        """)
        
        conn.commit()
        print("✅ Successfully added is_income column")
        
        # Show current categories
        cursor.execute("SELECT name, vat_applicable, is_income FROM custom_categories")
        categories = cursor.fetchall()
        
        if categories:
            print(f"\nFound {len(categories)} custom categories:")
            print("=" * 60)
            for name, vat_app, is_income in categories:
                cat_type = "Income (VAT Output)" if is_income == 1 else "Expense (VAT Input)"
                print(f"  {name}: {cat_type}, VAT: {'Yes' if vat_app else 'No'}")
            print("\n💡 All custom categories defaulted to 'Expense'")
            print("   Update via API or manually if any should be 'Income'")
        else:
            print("\nNo custom categories found in database")
        
    except sqlite3.OperationalError as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("VAT Category Type Migration")
    print("=" * 60)
    migrate()
    print("\n✅ Migration complete!")
    print("\nNext steps:")
    print("  1. Restart backend server")
    print("  2. Custom categories can now be marked as Income/Expense")
    print("  3. VAT reports will automatically split correctly")
