import sqlite3
from datetime import datetime

conn = sqlite3.connect('statement_analyzer.db')
cursor = conn.cursor()

# Get all sessions without friendly names
cursor.execute('SELECT session_id FROM session_states WHERE friendly_name IS NULL')
sessions = cursor.fetchall()

for (session_id,) in sessions:
    # Get date range for this session
    cursor.execute('''
        SELECT MIN(date), MAX(date) FROM transactions WHERE session_id = ?
    ''', (session_id,))
    result = cursor.fetchone()
    
    if result and result[0]:
        date_from = result[0]
        date_to = result[1]
        # Format as 'Statement Jan 27 - Feb 14, 2026'
        from_date = datetime.strptime(date_from, '%Y-%m-%d')
        to_date = datetime.strptime(date_to, '%Y-%m-%d')
        friendly_name = f"Statement {from_date.strftime('%b %d')} - {to_date.strftime('%b %d, %Y')}"
        
        cursor.execute(
            'UPDATE session_states SET friendly_name = ? WHERE session_id = ?',
            (friendly_name, session_id)
        )
        print(f'✅ Updated: {friendly_name}')

conn.commit()
print('\n✅ All sessions updated!')
conn.close()
