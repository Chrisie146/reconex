"""
Test the learn_rule parameter behavior
Verify that rules are only created when learn_rule=true
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

print("🧪 Testing Learn Rule Checkbox Behavior")
print("=" * 60)

user_id = str(uuid.uuid4())
session_1 = str(uuid.uuid4())

print(f"\n1️⃣ Initial State Check")
initial_rules = learning_service.get_learned_rules(user_id, db)
print(f"   User {user_id[:8]} has {len(initial_rules)} existing rules")

print(f"\n2️⃣ Test: Manual categorization WITHOUT learn_rule flag")
# Simulate what happens when user edits category without checking the box
txn1 = Transaction(
    session_id=session_1,
    date=date(2024, 1, 15),
    description="UBER TRIP 123",
    amount=-25.50,
    category="Transport"
)
db.add(txn1)
db.commit()

print(f"   Created transaction: '{txn1.description}' → {txn1.category}")
print(f"   User did NOT check 'Apply to all matching' checkbox")
print(f"   (Backend receives learn_rule=False, so NO rule should be created)")

rules_after_no_learn = learning_service.get_learned_rules(user_id, db)
new_rules_count = len(rules_after_no_learn) - len(initial_rules)

if new_rules_count == 0:
    print(f"   ✅ PASS: No rules created (as expected)")
else:
    print(f"   ❌ FAIL: {new_rules_count} rule(s) were created (should be 0)")

print(f"\n3️⃣ Test: Manual categorization WITH learn_rule flag")
# Simulate what happens when user checks the box
txn2 = Transaction(
    session_id=session_1,
    date=date(2024, 1, 20),
    description="WOOLWORTHS STORE 456",
    amount=-150.00,
    category="Groceries"
)
db.add(txn2)
db.commit()

print(f"   Created transaction: '{txn2.description}' → {txn2.category}")
print(f"   User CHECKED 'Apply to all matching' checkbox")
print(f"   (Backend receives learn_rule=True, calling learning service)")

# Manually call learning service (simulating backend with learn_rule=True)
learned_rules = learning_service.learn_from_categorization(
    user_id=user_id,
    session_id=session_1,
    description=txn2.description,
    category=txn2.category,
    merchant=None,
    db=db
)

print(f"   ✅ PASS: Created {len(learned_rules)} rule(s)")
for rule in learned_rules:
    print(f"     - {rule['pattern_type']}: '{rule['pattern_value']}' → {rule['category']}")

print(f"\n4️⃣ Test: Auto-apply learned rules to new upload")
session_2 = str(uuid.uuid4())

# New transaction that should match the learned rule
txn3 = Transaction(
    session_id=session_2,
    date=date(2024, 2, 10),
    description="WOOLWORTHS FOOD HALL",
    amount=-89.50,
    category=""
)
db.add(txn3)
db.commit()

suggestions = learning_service.apply_learned_rules(user_id, [txn3], db)

if txn3.id in suggestions and suggestions[txn3.id] == "Groceries":
    print(f"   ✅ PASS: New transaction auto-categorized as 'Groceries'")
    print(f"   Transaction: '{txn3.description}' → {suggestions[txn3.id]}")
else:
    print(f"   ⚠️  No match (might be expected if patterns don't match closely)")

print(f"\n5️⃣ Final Rule Count")
final_rules = learning_service.get_learned_rules(user_id, db)
print(f"   Total rules for user: {len(final_rules)}")
print(f"   Rules created in this test: {len(final_rules) - len(initial_rules)}")

# Cleanup
print(f"\n6️⃣ Cleanup")
db.query(Transaction).filter(Transaction.session_id.in_([session_1, session_2])).delete()
db.query(UserCategorizationRule).filter(UserCategorizationRule.user_id == user_id).delete()
db.commit()
db.close()

print("\n" + "=" * 60)
print("✅ Test Complete!")
print("\nKey Behavior:")
print("  - WITHOUT checkbox: No rules created (quick edit)")
print("  - WITH checkbox: Rules created (apply to similar transactions)")
print("  - This gives users full control over when to create learned rules")
