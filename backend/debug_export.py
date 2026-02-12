import sqlite3

conn = sqlite3.connect('statement_analyzer.db')
c = conn.cursor()

# Check tables
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in c.fetchall()]
print('Tables:', tables)

# Check transaction data if transactions table exists
if 'transactions' in tables:
    c.execute("SELECT COUNT(*) FROM transactions")
    count = c.fetchone()[0]
    print(f'Transaction count: {count}')
    
    # Check for NULL dates
    c.execute("SELECT COUNT(*) FROM transactions WHERE date IS NULL")
    null_dates = c.fetchone()[0]
    print(f'Transactions with NULL date: {null_dates}')
    
    # Check for NULL categories
    c.execute("SELECT COUNT(*) FROM transactions WHERE category IS NULL")
    null_cats = c.fetchone()[0]
    print(f'Transactions with NULL category: {null_cats}')
    
    # Show session IDs
    c.execute("SELECT DISTINCT session_id FROM transactions LIMIT 3")
    sessions = [row[0] for row in c.fetchall()]
    print(f'Sample session IDs: {sessions}')
    
    # Show a few rows
    print('\nSample transactions:')
    c.execute("SELECT id, date, description, category FROM transactions LIMIT 3")
    for row in c.fetchall():
        print(f'  {row}')

conn.close()
