"""
Test custom categories API persistence
"""

import requests

API_BASE = "http://localhost:8000"

print("=" * 70)
print("Testing Custom Category API - Persistence Across Sessions")
print("=" * 70)

# Session 1: Create a category
print("\n[Session 1] Creating custom category 'Office Supplies'...")
session1 = "api-test-001"
response = requests.post(
    f"{API_BASE}/categories",
    params={"session_id": session1},
    json={"category_name": "Office Supplies"}
)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    print(f"  Response: {response.json()['message']}")
else:
    print(f"  Error: {response.text}")

# Session 2: Check if category exists
print("\n[Session 2] Getting categories in NEW session...")
session2 = "api-test-002"
response = requests.get(
    f"{API_BASE}/categories",
    params={"session_id": session2}
)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    categories = response.json()['categories']
    if "Office Supplies" in categories:
        print(f"  ✅ SUCCESS: 'Office Supplies' found in new session!")
        print(f"  Total categories: {len(categories)}")
    else:
        print(f"  ❌ FAILED: 'Office Supplies' not found")
else:
    print(f"  Error: {response.text}")

# Cleanup
print("\n[Cleanup] Deleting test category...")
response = requests.delete(
    f"{API_BASE}/categories/Office Supplies",
    params={"session_id": session2}
)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    print(f"  Cleanup successful")
