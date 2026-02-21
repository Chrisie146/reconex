import sys
sys.path.append('.')
from backend.models import SessionLocal, Transaction

db = SessionLocal()
try:
    # Get sample transactions and their categories
    txns = db.query(Transaction).limit(20).all()
    print('Sample transactions:')
    for t in txns:
        print(f'ID: {t.id}, Category: \"{t.category}\", Description: {t.description[:50]}...')

    # Count transactions by category
    from sqlalchemy import func
    category_counts = db.query(Transaction.category, func.count(Transaction.id)).group_by(Transaction.category).all()
    print('\nCategory counts:')
    for cat, count in category_counts:
        print(f'\"{cat}\": {count}')

    # Check for transactions with empty/null category
    empty_count = db.query(Transaction).filter((Transaction.category == None) | (Transaction.category == '')).count()
    print(f'\nTransactions with empty/null category: {empty_count}')

    # Check for 'Other' category
    other_count = db.query(Transaction).filter(Transaction.category == 'Other').count()
    print(f'Transactions with \"Other\" category: {other_count}')

finally:
    db.close()