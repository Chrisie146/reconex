import sqlite3
conn = sqlite3.connect('statement_analyzer.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Tables:', tables)
if 'transactions' in [t[0] for t in tables]:
    cursor.execute('SELECT COUNT(*) FROM transactions')
    count = cursor.fetchone()
    print('Transaction count:', count[0])
    cursor.execute('SELECT id, session_id, client_id FROM transactions WHERE id=322')
    txn = cursor.fetchone()
    if txn:
        print('Transaction 322:', txn)
    else:
        print('Transaction 322 not found')
conn.close()