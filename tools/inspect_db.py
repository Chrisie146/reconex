import sqlite3
from pprint import pprint

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

print('--- Clients ---')
try:
    cur.execute('SELECT id, name, user_id FROM clients')
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('clients table error:', e)

print('\n--- SessionState ---')
try:
    cur.execute('SELECT session_id, friendly_name, created_at FROM session_states')
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('session_states table error:', e)

print('\n--- Transactions summary (by session_id, client_id) ---')
try:
    cur.execute('SELECT session_id, client_id, COUNT(*) as cnt FROM transactions GROUP BY session_id, client_id')
    rows = cur.fetchall()
    for r in rows:
        print(r)
except Exception as e:
    print('transactions table error:', e)

conn.close()
