#!/usr/bin/env python
import requests

# Use one of the sessions that has Herotel transactions
# From the database check, we saw sessions like "0038e00b...", "9f34729c...", etc.
# Let's use the first one with Herotel

session_id = "0038e00b-0000-0000-0000-000000000001"  # This won't work - we need real session IDs

# Get from database instead
import sqlite3

db_path = "statement_analyzer.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get a session that has both transactions and invoices
cursor.execute("""
    SELECT DISTINCT session_id FROM transactions 
    WHERE description LIKE '%HEROTEL%'
    LIMIT 1
""")
result = cursor.fetchone()
if result:
    session_with_herotel_txn = result[0]
    print(f"Found session with Herotel transactions: {session_with_herotel_txn}")
    
    # Check if this session has invoices
    cursor.execute("""
        SELECT COUNT(*) FROM invoices WHERE session_id = ?
    """, (session_with_herotel_txn,))
    inv_count = cursor.fetchone()[0]
    print(f"Invoices in this session: {inv_count}")
    
    # Get the latest invoice
    cursor.execute("""
        SELECT id, supplier_name, invoice_date, total_amount FROM invoices 
        WHERE session_id = ? 
        ORDER BY id DESC LIMIT 1
    """, (session_with_herotel_txn,))
    inv = cursor.fetchone()
    if inv:
        print(f"\nLatest invoice in this session:")
        print(f"  Supplier: {inv[1]}")
        print(f"  Date: {inv[2]}")
        print(f"  Amount: {inv[3]}")
    
    # Now test the matching API
    print(f"\n=== Testing Matcher with Session: {session_with_herotel_txn[:8]}... ===")
    resp = requests.post(
        f"http://127.0.0.1:8000/invoice/match?session_id={session_with_herotel_txn}"
    )
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Matches found: {data['count']}\n")
    
    for m in data['matches']:
        print(f"Invoice: {m['invoice']['supplier_name']}")
        print(f"  Amount: £{m['invoice']['total_amount']}, Date: {m['invoice']['invoice_date']}")
        print(f"  Match Score: {m['confidence']} ({m['classification']})")
        print(f"  Explanation: {m['explanation']}")
        if m['transaction']:
            print(f"  ✓ Matched Txn: {m['transaction']['date']} - {m['transaction']['description']} - £{abs(m['transaction']['amount'])}")
        else:
            print(f"  ✗ No Match")
else:
    print("No session with Herotel transactions found")

conn.close()
