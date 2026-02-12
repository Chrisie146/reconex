import sqlite3
DB = 'c:\\Users\\christopherm\\statementbur_python\\statement_analyzer.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
for name, sql in cur.fetchall():
    print('\nTABLE:', name)
    print(sql)
conn.close()
