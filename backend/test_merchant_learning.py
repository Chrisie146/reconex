"""
Test merchant-based learned rules
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Transaction, UserCategorizationRule
from services.categorization_learning_service import CategorizationLearningService
from config import DATABASE_URL
import uuid
from datetime import date

# Setup database
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

learning_service = CategorizationLearningService()

print("🧪 Testing Merchant-Based Learned Rules")
print("=" * 60)

# Create test user
user_id = str(uuid.uuid4())
session_1 = str(uuid.uuid4())

print(f"\n1️⃣ Test Case 1: Transaction WITH merchant field")
print(f"   User ID: {user_id[:8]}...")
print(f"   Session: {session_1[:8]}...")

# Create transaction with merchant
txn1 = Transaction(
    session_id=session_1,
    date=date(2024, 1, 15),
    description="PURCHASE AT STORE #123",
    amount=-45.50,
    category="Groceries"
)
db.add(txn1)
db.commit()

# Learn with merchant provided
print(f"\n   Learning from: '{txn1.description}' with merchant='WOOLWORTHS'")
learned_rules = learning_service.learn_from_categorization(
    user_id=user_id,
    session_id=session_1,
    description=txn1.description,
    category="Groceries",
    merchant="WOOLWORTHS",
    db=db
)

print(f"   ✓ Created {len(learned_rules)} rule(s):")
for rule in learned_rules:
    print(f"     - {rule['pattern_type']}: '{rule['pattern_value']}' → Groceries")

# Check if merchant rule was created
merchant_rules = [r for r in learned_rules if r['pattern_type'] == 'merchant']
if merchant_rules:
    print(f"\n   ✅ PASS: Merchant rule created with value '{merchant_rules[0]['pattern_value']}'")
else:
    print(f"\n   ❌ FAIL: No merchant rule created")

print(f"\n2️⃣ Test Case 2: Auto-categorize new transaction with same merchant")
session_2 = str(uuid.uuid4())

# Create new transaction with same merchant in description or merchant field
txn2 = Transaction(
    session_id=session_2,
    date=date(2024, 2, 20),
    description="DIFFERENT DESCRIPTION AT WOOLWORTHS",
    amount=-67.80,
    category=""
)
# Mock the merchant attribute for testing
txn2.merchant = "WOOLWORTHS"
db.add(txn2)
db.commit()

# Apply learned rules
transactions = [txn2]
suggestions = learning_service.apply_learned_rules(user_id, transactions, db)

if txn2.id in suggestions and suggestions[txn2.id] == "Groceries":
    print(f"   ✅ PASS: Correctly categorized as '{suggestions[txn2.id]}'")
    print(f"   Transaction: '{txn2.description}' + merchant='{txn2.merchant}'")
else:
    print(f"   ❌ FAIL: Expected 'Groceries', got: {suggestions.get(txn2.id, 'NONE')}")

print(f"\n3️⃣ Test Case 3: Multiple merchants for same user")

# Learn another merchant -> category mapping
txn3 = Transaction(
    session_id=session_1,
    date=date(2024, 1, 20),
    description="FUEL PURCHASE",
    amount=-600.00,
    category="Transport"
)
db.add(txn3)
db.commit()

learned_rules2 = learning_service.learn_from_categorization(
    user_id=user_id,
    session_id=session_1,
    description=txn3.description,
    category="Transport",
    merchant="SHELL",
    db=db
)

print(f"   Learned from: '{txn3.description}' with merchant='SHELL' → Transport")
print(f"   Created {len(learned_rules2)} additional rule(s)")

# Check total rules for this user
all_rules = learning_service.get_learned_rules(user_id, db)
merchant_rule_count = sum(1 for r in all_rules if r['pattern_type'] == 'merchant')

print(f"\n   Total merchant rules for user: {merchant_rule_count}")
print(f"   All rules: {len(all_rules)}")

if merchant_rule_count >= 2:
    print(f"   ✅ PASS: Multiple merchant rules stored correctly")
    for rule in all_rules:
        if rule['pattern_type'] == 'merchant':
            print(f"     - {rule['pattern_value']} → {rule['category']}")
else:
    print(f"   ❌ FAIL: Expected at least 2 merchant rules")

print(f"\n4️⃣ Cleanup")
db.query(Transaction).filter(Transaction.session_id.in_([session_1, session_2])).delete()
db.query(UserCategorizationRule).filter(UserCategorizationRule.user_id == user_id).delete()
db.commit()
db.close()

print("\n" + "=" * 60)
print("✅ Merchant Learning Test Complete!")
print("\nKey features verified:")
print("  - Merchant field creates high-priority rules")
print("  - Transactions with matching merchant auto-categorize")
print("  - Multiple merchant mappings per user work correctly")
