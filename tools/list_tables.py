import sqlite3

DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

print('=== Database Tables ===\n')
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

for table in tables:
    print(f'\n{table} count:')
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    print(cur.fetchone()[0])

conn.close()
