#!/usr/bin/env python
"""
Fix guide for Transaction 404 errors

This script shows what transactions are in the database and 
helps you understand the session mismatch issue.
"""

import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'statement_analyzer.db')

print("""
╔════════════════════════════════════════════════════════════════════════════════╗
║                    TRANSACTION 404 ERROR - FIX GUIDE                           ║
╚════════════════════════════════════════════════════════════════════════════════╝

The error "Transaction not found. Please refresh the page..." means the frontend 
is showing transactions that don't exist in the database.

This usually happens when:
  1. Database was reset (e.g., after running init_db_schema.py)
  2. Frontend has cached/old transaction data
  3. Session ID mismatches

╔────────────────────────────────────────────────────────────────────────────────╗
║ WHAT'S IN YOUR DATABASE:                                                       ║
╚────────────────────────────────────────────────────────────────────────────────╝
""")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check transaction count
cur.execute("SELECT COUNT(*) as count FROM transactions")
total = cur.fetchone()['count']

print(f"✓ Total transactions: {total}")

if total == 0:
    print("""
    ❌ DATABASE IS EMPTY

    Your database has no transactions. The session you're trying to work with 
    doesn't have any data.
    """)
else:
    # List sessions
    print("\n✓ Sessions with transactions:")
    cur.execute("""
        SELECT session_id, COUNT(*) as txn_count 
        FROM transactions 
        GROUP BY session_id
        ORDER BY COUNT(*) DESC
    """)
    
    for row in cur.fetchall():
        session = row['session_id']
        count = row['txn_count']
        print(f"    - {session[:20]}... ({count} transactions)")

# Show sample transactions
cur.execute("SELECT id, session_id, description FROM transactions LIMIT 5")
samples = cur.fetchall()

if samples:
    print("\n✓ Sample transaction IDs in database:")
    for row in samples:
        print(f"    - ID: {row['id']} | Session: {row['session_id'][:20]}...")

print("""
╔────────────────────────────────────────────────────────────────────────────────╗
║ HOW TO FIX THIS:                                                               ║
╚────────────────────────────────────────────────────────────────────────────────╝

STEP 1: Check backend error messages
   The backend now provides better diagnostics. When you see a 404 error,
   it will say whether:
   - The database is empty
   - The session was reset
   - There's a session mismatch
   - The specific transaction doesn't exist

STEP 2: Restart the backend to apply new error handling
   """)

print("   Option A - Run from terminal:")
print("      $ cd backend")
print("      $ python main.py")
print("""
   Option B - Kill and restart:
      1. Stop the current backend process
      2. python backend/main.py
      3. Wait for "Application startup complete"

STEP 3: Refresh the frontend
   1. Go to browser where app is running
   2. Press F5 or Ctrl+R to refresh
   3. Try uploading a new statement

STEP 4: Try editing a transaction again
   Now when you try to save, you'll get a more helpful error message
   that explains exactly what the problem is.

╔────────────────────────────────────────────────────────────────────────────────╗
║ ADDITIONAL TIPS:                                                               ║
╚────────────────────────────────────────────────────────────────────────────────╝

• If you see "database was reset": Upload a new statement
• If you see "session mismatch": Refresh the page
• If database is empty: Check if init_db_schema.py was recently run
• To preserve data before resetting: Export transactions first

For more detailed diagnostics, run:
   $ python debug_transaction_mismatch.py
""")

conn.close()
