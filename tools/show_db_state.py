import sqlite3

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Current Database State ===\n')

print('Clients:')
cur.execute('SELECT id, user_id, name FROM clients')
for row in cur.fetchall():
    print(f'  ID {row[0]}: user_id={row[1]}, name={row[2]}')

print('\nSession States:')
cur.execute('SELECT session_id, friendly_name FROM session_states')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

print('\nTransactions Summary:')
cur.execute('''
    SELECT 
        session_id, 
        client_id,
        COUNT(*) as count,
        MIN(date) as min_date,
        MAX(date) as max_date
    FROM transactions 
    GROUP BY session_id, client_id
''')
for row in cur.fetchall():
    print(f'  Session {row[0]}: client_id={row[1]}, {row[2]} txns, dates {row[3]} to {row[4]}')

conn.close()
