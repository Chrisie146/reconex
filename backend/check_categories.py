import sqlite3

conn = sqlite3.connect('statement_analyzer.db')
c = conn.cursor()

# Get all unique categories
c.execute("SELECT DISTINCT category FROM transactions ORDER BY category")
categories = [row[0] for row in c.fetchall()]
print("All categories:")
for cat in categories:
    print(f"  '{cat}'")
    if ':' in cat:
        print(f"    ^ CONTAINS COLON!")

conn.close()
