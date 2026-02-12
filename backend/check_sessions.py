import sqlite3

conn = sqlite3.connect('statement_analyzer.db')
cursor = conn.cursor()

print("=== Checking session_states table ===")
cursor.execute('SELECT session_id, friendly_name FROM session_states LIMIT 5')
rows = cursor.fetchall()
for session_id, friendly_name in rows:
    print(f"Session: {session_id}")
    print(f"  Friendly Name: {friendly_name}")
    print()

conn.close()
