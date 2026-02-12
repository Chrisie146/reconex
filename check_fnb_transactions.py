import sys
sys.path.insert(0, r'c:\Users\christopherm\statementbur_python\backend')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Connect to database
engine = create_engine("sqlite:///statement_analyzer.db")

with engine.connect() as conn:
    # Get recent transactions from fnb
    result = conn.execute(text("""
        SELECT 
            session_id,
            date, 
            description, 
            amount, 
            category,
            bank_source
        FROM transactions 
        WHERE bank_source = 'fnb'
        ORDER BY date DESC
        LIMIT 20
    """))
    
    rows = result.fetchall()
    print(f"Last 20 FNB transactions in database:")
    print(f"{'Session':<8} {'Date':<12} {'Amount':>10} {'Category':<20} {'Description':<40}")
    print("-" * 95)
    
    for row in rows:
        session, date, desc, amount, category, bank = row
        print(f"{str(session)[:8]:<8} {str(date):<12} {amount:>10.2f} {category:<20} {str(desc)[:40]:<40}")
