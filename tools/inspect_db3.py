import sqlite3
DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('Distinct session_ids in transactions:')
cur.execute("SELECT session_id, COUNT(*) FROM transactions GROUP BY session_id")
for s,c in cur.fetchall():
    print(s, c)

print('\nSession states:')
cur.execute('SELECT session_id, friendly_name, created_at FROM session_states')
for r in cur.fetchall():
    print(r)

print('\nTransactions with NULL client_id (showing session_id samples):')
cur.execute("SELECT session_id, id, description FROM transactions WHERE client_id IS NULL LIMIT 10")
for r in cur.fetchall():
    print(r)

conn.close()
