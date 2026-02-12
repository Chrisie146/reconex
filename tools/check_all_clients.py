import sqlite3

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== All Clients ===')
cur.execute('SELECT id, user_id, name, created_at FROM clients ORDER BY id')
for row in cur.fetchall():
    print(f'ID {row[0]}: user_id={row[1]}, name={row[2]}, created_at={row[3]}')

print('\n=== All Session States ===')
cur.execute('SELECT session_id, friendly_name, created_at FROM session_states ORDER BY created_at DESC')
for row in cur.fetchall():
    print(f'{row[0]}: {row[1]} (created {row[2]})')

print('\n=== Transaction Distribution ===')
cur.execute('''
    SELECT 
        client_id,
        session_id,
        COUNT(*) as count
    FROM transactions 
    GROUP BY client_id, session_id
    ORDER BY client_id, session_id
''')
for row in cur.fetchall():
    print(f'client_id={row[0]}, session={row[1]}: {row[2]} txns')

conn.close()
