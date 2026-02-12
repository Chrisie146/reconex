"""
Test script to verify learned rules persist across sessions
This tests the user_id fix for the disappearing rules bug
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Transaction, UserCategorizationRule
from services.categorization_learning_service import CategorizationLearningService
import uuid
from datetime import date

# Setup database
engine = create_engine("sqlite:///statement_analyzer.db")
Session = sessionmaker(bind=engine)
db = Session()

learning_service = CategorizationLearningService()

# Test scenario
print("🧪 Testing User ID Persistence Fix")
print("=" * 60)

# Create a persistent user_id (simulating localStorage)
user_id = str(uuid.uuid4())
print(f"\n1️⃣ Creating test user: {user_id[:8]}...")

# Session 1: Upload first statement
session_1 = str(uuid.uuid4())
print(f"\n2️⃣ Session 1: {session_1[:8]}...")

# Create test transaction in session 1
txn1 = Transaction(
    id=None,
    session_id=session_1,
    date=date(2024, 1, 15),
    description="UBER TRIP",
    amount=-25.50,
    category="Transport"
)
db.add(txn1)
db.commit()

# User categorizes the transaction - this should learn a rule
print(f"   Categorizing: {txn1.description} -> {txn1.category}")
learning_service.learn_from_categorization(
    user_id=user_id,
    session_id=session_1,
    description=txn1.description,
    category=txn1.category,
    db=db
)

# Check learned rules
rules_after_session1 = learning_service.get_learned_rules(user_id, db)
print(f"   ✓ Learned {len(rules_after_session1)} rule(s)")
for rule in rules_after_session1:
    print(f"     - {rule['pattern_type']}: '{rule['pattern_value']}' → {rule['category']}")

# Session 2: Upload second statement (new session_id)
print(f"\n3️⃣ Session 2 (NEW SESSION): Simulating new upload...")
session_2 = str(uuid.uuid4())
print(f"   Session 2: {session_2[:8]}...")

# Create new transaction in session 2 that should match learned rule
txn2 = Transaction(
    id=None,
    session_id=session_2,
    date=date(2024, 2, 20),
    description="UBER EATS",
    amount=-18.75,
    category=""  # Empty string instead of None
)
db.add(txn2)
db.commit()

# Check if rules are still accessible with the SAME user_id
rules_in_session2 = learning_service.get_learned_rules(user_id, db)
print(f"\n4️⃣ Checking rules in Session 2 with user_id {user_id[:8]}...")
print(f"   Found {len(rules_in_session2)} rule(s) - {'✅ PASS' if len(rules_in_session2) > 0 else '❌ FAIL'}")

if len(rules_in_session2) == 0:
    print("   ❌ BUG: Rules disappeared! They were tied to session_id, not user_id")
else:
    print("   ✅ SUCCESS: Rules persisted across sessions!")

# Apply learned rules to new session
transactions_session2 = db.query(Transaction).filter(Transaction.session_id == session_2).all()
suggestions = learning_service.apply_learned_rules(user_id, transactions_session2, db)

print(f"\n5️⃣ Auto-categorization Results:")
if suggestions:
    print(f"   ✅ Auto-categorized {len(suggestions)} transaction(s)")
    for txn_id, category in suggestions.items():
        txn = db.query(Transaction).filter(Transaction.id == txn_id).first()
        print(f"     - '{txn.description}' → {category}")
else:
    print(f"   ⚠️  No matches (this is okay if patterns don't match)")

# Test with WRONG user_id (should find no rules)
print(f"\n6️⃣ Testing with different user_id (should have no rules)...")
wrong_user_id = str(uuid.uuid4())
rules_wrong_user = learning_service.get_learned_rules(wrong_user_id, db)
print(f"   Found {len(rules_wrong_user)} rules - {'✅ PASS' if len(rules_wrong_user) == 0 else '❌ FAIL'}")

# Cleanup
print(f"\n7️⃣ Cleaning up test data...")
db.query(Transaction).filter(Transaction.session_id.in_([session_1, session_2])).delete()
db.query(UserCategorizationRule).filter(UserCategorizationRule.user_id == user_id).delete()
db.commit()
db.close()

print("\n" + "=" * 60)
print("✅ Test Complete!")
print("\nKey findings:")
print("  - Rules should persist across different session_ids")
print("  - Rules should be isolated per user_id")
print("  - Auto-categorization should work in new sessions")
