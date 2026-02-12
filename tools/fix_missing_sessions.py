import sqlite3
from datetime import datetime

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Fixing Database for Statements Display ===\n')

# 1. Create a default client
print('1. Creating default client...')
cur.execute('''
    INSERT INTO clients (name, user_id, created_at) 
    VALUES ('Default Client', 'default_user', ?)
''', (datetime.now().isoformat(),))
client_id = cur.lastrowid
print(f'   Created client with ID: {client_id}')

# 2. Get all unique session_ids from transactions
print('\n2. Finding orphaned sessions...')
cur.execute('SELECT DISTINCT session_id FROM transactions')
session_ids = [row[0] for row in cur.fetchall()]
print(f'   Found {len(session_ids)} unique session(s): {session_ids}')

# 3. Create session_states for each session
print('\n3. Creating session_states entries...')
for session_id in session_ids:
    # Check if session_state already exists
    cur.execute('SELECT COUNT(*) FROM session_states WHERE session_id = ?', (session_id,))
    if cur.fetchone()[0] == 0:
        # Get transaction count and date range
        cur.execute('''
            SELECT COUNT(*), MIN(date), MAX(date)
            FROM transactions
            WHERE session_id = ?
        ''', (session_id,))
        count, min_date, max_date = cur.fetchone()
        
        # Create friendly name
        friendly_name = f'Statement {min_date} to {max_date}'
        
        # Insert session_state
        cur.execute('''
            INSERT INTO session_states (session_id, friendly_name, created_at)
            VALUES (?, ?, ?)
        ''', (session_id, friendly_name, datetime.now().isoformat()))
        
        print(f'   Created session_state: {session_id} - {friendly_name} ({count} transactions)')

# 4. Update all transactions to have the default client_id
print(f'\n4. Updating transactions with client_id={client_id}...')
cur.execute('UPDATE transactions SET client_id = ? WHERE client_id IS NULL', (client_id,))
updated = cur.rowcount
print(f'   Updated {updated} transactions')

# Commit changes
conn.commit()

# 5. Verify the fix
print('\n=== Verification ===')
cur.execute('SELECT COUNT(*) FROM clients')
print(f'Clients: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM session_states')
print(f'Session states: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM transactions WHERE client_id IS NOT NULL')
print(f'Transactions with client_id: {cur.fetchone()[0]}')

print('\nClients:')
cur.execute('SELECT id, name, user_id FROM clients')
for row in cur.fetchall():
    print(f'  ID {row[0]}: {row[1]} (user: {row[2]})')

print('\nSession States:')
cur.execute('SELECT session_id, friendly_name FROM session_states')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

conn.close()

print('\n✅ Database fixed! Statements should now appear in the left sidebar.')
