"""Verify income vs expenses are calculated correctly"""
import sys
sys.path.insert(0, '.')

from models import SessionLocal, Transaction

db = SessionLocal()

# Get first session
sessions = db.query(Transaction.session_id).distinct().limit(1).all()
if sessions:
    session_id = sessions[0][0]
    transactions = db.query(Transaction).filter(Transaction.session_id == session_id).all()
    
    print(f"Session: {session_id}")
    print(f"Total transactions: {len(transactions)}\n")
    
    # Income categories
    income_categories = {'Income', 'Salary', 'Wages'}
    exclude_categories = {'Transfers', 'Debt repayment'}
    
    total_income = 0.0
    total_expenses = 0.0
    
    for t in transactions:
        cat = t.category or 'Uncategorized'
        amount_abs = abs(t.amount)
        
        if cat in income_categories:
            total_income += amount_abs
        elif cat not in exclude_categories:
            total_expenses += amount_abs
    
    net_balance = total_income - total_expenses
    
    print(f"Total Income:     R {total_income:,.2f}")
    print(f"Total Expenses:   R {total_expenses:,.2f}")
    print(f"Net Balance:      R {net_balance:,.2f}")
    print()
    
    # Category breakdown
    categories = {}
    for t in transactions:
        cat = t.category or 'Uncategorized'
        if cat not in categories:
            categories[cat] = 0.0
        categories[cat] += abs(t.amount)
    
    print("Breakdown by category:")
    for cat, amount in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        is_income = "✓ INCOME" if cat in income_categories else ""
        print(f"  {cat:30} R {amount:>12,.2f}  {is_income}")

db.close()
