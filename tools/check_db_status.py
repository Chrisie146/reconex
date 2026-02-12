import sqlite3

DB = 'c:\\Users\\christopherm\\statementbur_python\\statements.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Database Status Check ===\n')

print('SessionStates count:')
cur.execute('SELECT COUNT(*) FROM session_states')
print(cur.fetchone()[0])

print('\nTransactions count:')
cur.execute('SELECT COUNT(*) FROM transactions')
print(cur.fetchone()[0])

print('\nClients count:')
cur.execute('SELECT COUNT(*) FROM clients')
print(cur.fetchone()[0])

print('\nSample sessions:')
cur.execute('SELECT session_id, friendly_name, created_at FROM session_states ORDER BY created_at DESC LIMIT 5')
for row in cur.fetchall():
    print(row)

print('\nSample transactions with client_id:')
cur.execute('SELECT id, session_id, client_id, description FROM transactions LIMIT 5')
for row in cur.fetchall():
    print(row)

print('\nTransactions per session:')
cur.execute('SELECT session_id, client_id, COUNT(*) FROM transactions GROUP BY session_id, client_id')
for row in cur.fetchall():
    print(row)

conn.close()
