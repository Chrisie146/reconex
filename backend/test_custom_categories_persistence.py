"""
Test that custom categories persist across sessions
"""

from services.categories_service import CategoriesService

# Create service
cs = CategoriesService()

print("=" * 60)
print("Testing Custom Category Persistence Across Sessions")
print("=" * 60)

# Session 1: Create a custom category
print("\n[Session 1] Creating custom category 'Marketing'...")
session1 = "test-session-001"
success, msg = cs.create_category(session1, "Marketing")
print(f"  Result: {msg}")

# Verify it exists in session 1
cats1 = cs.get_all_categories(session1)
print(f"  Categories in session 1: {[c for c in cats1 if c == 'Marketing']}")

# Session 2: NEW session - check if custom category is available
print("\n[Session 2] Checking if 'Marketing' exists in NEW session...")
session2 = "test-session-002"  # Different session ID
cats2 = cs.get_all_categories(session2)
if "Marketing" in cats2:
    print(f"  ✅ SUCCESS: 'Marketing' is available in session 2")
else:
    print(f"  ❌ FAILED: 'Marketing' NOT found in session 2")

# Create another category in session 2
print("\n[Session 2] Creating custom category 'Consulting'...")
success, msg = cs.create_category(session2, "Consulting")
print(f"  Result: {msg}")

# Session 3: Verify both custom categories exist
print("\n[Session 3] Checking both custom categories in NEW session...")
session3 = "test-session-003"
cats3 = cs.get_all_categories(session3)
marketing_exists = "Marketing" in cats3
consulting_exists = "Consulting" in cats3

print(f"  Marketing exists: {marketing_exists}")
print(f"  Consulting exists: {consulting_exists}")

if marketing_exists and consulting_exists:
    print("\n✅ TEST PASSED: Custom categories persist across sessions!")
else:
    print("\n❌ TEST FAILED: Custom categories do not persist")

# Clean up
print("\n[Cleanup] Deleting test categories...")
cs.delete_category(session3, "Marketing")
cs.delete_category(session3, "Consulting")
print("  Cleanup complete")
