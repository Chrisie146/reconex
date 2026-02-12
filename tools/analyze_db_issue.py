import sqlite3

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Transactions Analysis ===\n')

print('Total transactions:', end=' ')
cur.execute('SELECT COUNT(*) FROM transactions')
print(cur.fetchone()[0])

print('\nTransactions by session_id:')
cur.execute('SELECT session_id, COUNT(*) FROM transactions GROUP BY session_id')
for row in cur.fetchall():
    print(f'  Session {row[0]}: {row[1]} transactions')

print('\nTransactions by client_id:')
cur.execute('SELECT client_id, COUNT(*) FROM transactions GROUP BY client_id')
for row in cur.fetchall():
    print(f'  Client {row[0]}: {row[1]} transactions')

print('\nSample transactions:')
cur.execute('SELECT id, session_id, client_id, date, description FROM transactions LIMIT 5')
for row in cur.fetchall():
    print(f'  ID {row[0]}: session={row[1]}, client={row[2]}, date={row[3]}, desc={row[4][:50]}')

print('\n=== Session States ===')
cur.execute('SELECT COUNT(*) FROM session_states')
print(f'Session states count: {cur.fetchone()[0]}')

print('\n=== Clients ===')
cur.execute('SELECT COUNT(*) FROM clients')
print(f'Clients count: {cur.fetchone()[0]}')

conn.close()
