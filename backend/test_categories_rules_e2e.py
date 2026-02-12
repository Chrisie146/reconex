#!/usr/bin/env python3
"""
End-to-End Test for Category & Rules Management System
Demonstrates the complete workflow:
1. Create a session
2. Upload a statement
3. Create custom categories
4. Create rules with multilingual keywords
5. Preview rule matches
6. Bulk apply rules
7. Verify statistics
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_system():
    print("=" * 80)
    print("CATEGORY & RULES MANAGEMENT END-TO-END TEST")
    print("=" * 80)

    # Step 1: Create a session (simulate upload)
    print("\n[1] Creating session...")
    session_response = requests.post(f"{BASE_URL}/upload", files={
        'file': ('test.csv', b'date,description,amount\n2024-01-15,Spar Grocery,1500.00')
    })
    
    if session_response.status_code != 200:
        print(f"❌ Failed to create session: {session_response.text}")
        return
    
    session_data = session_response.json()
    session_id = session_data.get('session_id')
    print(f"✅ Session created: {session_id}")

    # Step 2: Test getting built-in categories
    print("\n[2] Retrieving built-in categories...")
    categories_response = requests.get(f"{BASE_URL}/categories?session_id={session_id}")
    if categories_response.status_code == 200:
        categories = categories_response.json().get('categories', [])
        print(f"✅ Categories: {', '.join(categories)}")
    else:
        print(f"❌ Failed to get categories: {categories_response.text}")

    # Step 3: Create a custom category
    print("\n[3] Creating custom category...")
    custom_cat_response = requests.post(
        f"{BASE_URL}/categories?session_id={session_id}",
        json={"name": "Home Improvement"}
    )
    if custom_cat_response.status_code == 200:
        print(f"✅ Custom category created")
    else:
        print(f"❌ Failed: {custom_cat_response.text}")

    # Step 4: Create rules with multilingual keywords
    print("\n[4] Creating rules with keywords...")
    
    rules_data = [
        {
            "name": "Grocery Stores",
            "category": "Groceries",
            "keywords": ["spar", "pick n pay", "checkers", "kruideniersware", "supermark"],
            "priority": 5,
            "auto_apply": True
        },
        {
            "name": "Fuel Stations",
            "category": "Fuel",
            "keywords": ["shell", "bp", "engen", "aral", "petrol", "diesel"],
            "priority": 10,
            "auto_apply": True
        },
        {
            "name": "Restaurants",
            "category": "Dining",
            "keywords": ["restaurant", "cafe", "bistro", "pizza", "burger", "sushi"],
            "priority": 15,
            "auto_apply": False
        }
    ]

    created_rules = []
    for rule_data in rules_data:
        rule_response = requests.post(
            f"{BASE_URL}/rules?session_id={session_id}",
            json=rule_data
        )
        if rule_response.status_code == 200:
            rules_list = rule_response.json().get('rules', [])
            print(f"✅ Created rule: {rule_data['name']}")
            created_rules.extend(rules_list)
        else:
            print(f"❌ Failed to create {rule_data['name']}: {rule_response.text}")

    # Step 5: Get all rules
    print("\n[5] Retrieving all rules...")
    all_rules_response = requests.get(f"{BASE_URL}/rules?session_id={session_id}")
    if all_rules_response.status_code == 200:
        rules = all_rules_response.json().get('rules', [])
        print(f"✅ Total rules: {len(rules)}")
        for rule in rules:
            print(f"   - {rule['name']} ({rule['category']}, Priority: {rule['priority']})")
            print(f"     Keywords: {', '.join(rule['keywords'][:3])}" + 
                  (f" +{len(rule['keywords'])-3} more" if len(rule['keywords']) > 3 else ""))
    else:
        print(f"❌ Failed to get rules: {all_rules_response.text}")
        return

    # Step 6: Preview rule matches
    if rules:
        print("\n[6] Previewing rule matches...")
        first_rule = rules[0]
        preview_response = requests.post(
            f"{BASE_URL}/rules/{first_rule['rule_id']}/preview?session_id={session_id}"
        )
        if preview_response.status_code == 200:
            preview = preview_response.json()
            print(f"✅ Preview for '{first_rule['name']}':")
            print(f"   Matches: {preview.get('count', 0)} transaction(s) " +
                  f"({preview.get('percentage', 0):.1f}%)")
            matched = preview.get('matched', [])
            if matched:
                for txn in matched[:3]:
                    print(f"   - {txn['description']}: R{txn['amount']}")
        else:
            print(f"⚠️ Preview failed: {preview_response.text}")

    # Step 7: Get rule statistics
    print("\n[7] Getting rule statistics...")
    stats_response = requests.get(f"{BASE_URL}/rules/statistics?session_id={session_id}")
    if stats_response.status_code == 200:
        stats = stats_response.json()
        print(f"✅ Rule Statistics:")
        if 'statistics' in stats:
            for stat in stats['statistics']:
                print(f"   - {stat.get('name', 'Unknown')}: " +
                      f"{stat.get('match_count', 0)} matches " +
                      f"({stat.get('percentage', 0):.1f}%)")
        else:
            print(f"   No statistics available yet")
    else:
        print(f"⚠️ Statistics failed: {stats_response.text}")

    # Step 8: Bulk apply rules
    print("\n[8] Bulk applying rules...")
    bulk_response = requests.post(
        f"{BASE_URL}/rules/apply-bulk?session_id={session_id}",
        json={"auto_apply_only": False}
    )
    if bulk_response.status_code == 200:
        result = bulk_response.json()
        print(f"✅ Bulk apply completed:")
        print(f"   Updated: {result.get('updated_count', 0)} transaction(s)")
        print(f"   Rules applied: {result.get('rules_applied', 0)}")
    else:
        print(f"⚠️ Bulk apply failed: {bulk_response.text}")

    # Step 9: Test rule update
    if rules:
        print("\n[9] Updating a rule...")
        rule_to_update = rules[0]
        update_response = requests.put(
            f"{BASE_URL}/rules/{rule_to_update['rule_id']}?session_id={session_id}",
            json={
                "name": f"{rule_to_update['name']} (Updated)",
                "category": rule_to_update['category'],
                "keywords": rule_to_update['keywords'] + ["newkeyword"],
                "priority": rule_to_update['priority'],
                "auto_apply": not rule_to_update['auto_apply']
            }
        )
        if update_response.status_code == 200:
            print(f"✅ Rule updated successfully")
        else:
            print(f"❌ Update failed: {update_response.text}")

    # Step 10: Test rule deletion
    print("\n[10] Testing rule deletion...")
    if len(rules) > 1:
        rule_to_delete = rules[-1]
        delete_response = requests.delete(
            f"{BASE_URL}/rules/{rule_to_delete['rule_id']}?session_id={session_id}"
        )
        if delete_response.status_code == 200:
            print(f"✅ Rule deleted successfully")
        else:
            print(f"❌ Deletion failed: {delete_response.text}")

    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)
    print("\n💡 Next Steps:")
    print("1. Open http://localhost:3000/rules in your browser")
    print(f"2. Use session ID: {session_id}")
    print("3. Create, edit, preview, and manage rules from the UI")
    print("4. Use bulk apply to categorize transactions automatically")

if __name__ == '__main__':
    print("Waiting for backend to be ready...")
    time.sleep(2)
    
    try:
        # Check if backend is running
        requests.get(f"{BASE_URL}/health", timeout=5)
        test_system()
    except requests.exceptions.ConnectionError:
        print("❌ Backend is not running. Start it with:")
        print("   cd backend && python -m uvicorn main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")
