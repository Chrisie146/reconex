#!/usr/bin/env python
import sqlite3

db_path = "statement_analyzer.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables in database:")
for (table_name,) in tables:
    print(f"  - {table_name}")

# Get Transaction count
cursor.execute("SELECT COUNT(*) FROM transactions")
count = cursor.fetchone()[0]
print(f"\nTotal transactions: {count}")

# Get all transactions with Herotel
cursor.execute("""
    SELECT id, session_id, date, description, amount 
    FROM transactions 
    WHERE description LIKE '%herotel%' OR description LIKE '%Herotel%'
    ORDER BY date
""")
herotel_txns = cursor.fetchall()

if herotel_txns:
    print(f"\nFound {len(herotel_txns)} Herotel transactions:")
    for tid, sid, date, desc, amount in herotel_txns:
        print(f"  ID: {tid}, Date: {date}, Desc: {desc}, Amount: {amount}, Session: {sid[:8]}...")
else:
    print("\nNo Herotel transactions found. Getting latest 20 transactions:")
    cursor.execute("""
        SELECT id, session_id, date, description, amount 
        FROM transactions 
        ORDER BY date DESC
        LIMIT 20
    """)
    all_txns = cursor.fetchall()
    for tid, sid, date, desc, amount in all_txns:
        print(f"  ID: {tid}, Date: {date}, Desc: {desc}, Amount: {amount}")

# Get invoices
cursor.execute("SELECT COUNT(*) FROM invoices")
inv_count = cursor.fetchone()[0]
print(f"\nTotal invoices: {inv_count}")

cursor.execute("""
    SELECT id, session_id, supplier_name, invoice_date, total_amount 
    FROM invoices 
    ORDER BY id DESC
    LIMIT 5
""")
invoices = cursor.fetchall()
if invoices:
    print(f"Latest invoices:")
    for iid, sid, supplier, inv_date, total in invoices:
        print(f"  ID: {iid}, Supplier: {supplier}, Date: {inv_date}, Amount: {total}")

conn.close()
