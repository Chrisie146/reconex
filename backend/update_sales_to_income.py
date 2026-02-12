#!/usr/bin/env python
"""
Update Sales category to be Income (VAT Output)
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "statement_analyzer.db")

def update_sales_category():
    """Update Sales category to is_income = 1"""
    print("Updating Sales category to Income (VAT Output)...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Update Sales to be income
        cursor.execute("""
            UPDATE custom_categories 
            SET is_income = 1 
            WHERE name = 'Sales'
        """)
        
        rows_updated = cursor.rowcount
        conn.commit()
        
        if rows_updated > 0:
            print(f"✅ Updated {rows_updated} row(s)")
            print("   Sales is now classified as Income (VAT Output)")
        else:
            print("⚠️  Sales category not found in database")
        
        # Show current status
        cursor.execute("""
            SELECT name, is_income, vat_applicable 
            FROM custom_categories 
            WHERE name IN ('Sales', 'Salary', 'Income')
            ORDER BY name
        """)
        
        results = cursor.fetchall()
        if results:
            print("\nIncome/Sales categories:")
            print("=" * 50)
            for name, is_income, vat_app in results:
                cat_type = "Income (VAT Output)" if is_income == 1 else "Expense (VAT Input)"
                print(f"  {name}: {cat_type}, VAT: {'Yes' if vat_app else 'No'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_sales_category()
    print("\n✅ Done! Sales category is now Income (VAT Output)")
