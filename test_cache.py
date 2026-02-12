"""
Test Redis Cache Service

Tests cache functionality including:
- Connection and health check
- Get/set operations
- TTL expiration
- Cache invalidation
- Statistics tracking
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import time
from services.cache import get_cache

def test_cache_health():
    """Test 1: Cache Health Check"""
    print("\n=== TEST 1: Cache Health Check ===")
    cache = get_cache()
    health = cache.health_check()
    print(f"Health status: {health}")
    
    if health['status'] == 'healthy':
        print("✅ Cache is healthy")
        return True
    elif health['status'] == 'disabled':
        print("⚠️  Cache is disabled")
        return False
    else:
        print(f"❌ Cache is unhealthy: {health.get('error')}")
        return False


def test_basic_operations():
    """Test 2: Basic Get/Set Operations"""
    print("\n=== TEST 2: Basic Get/Set Operations ===")
    cache = get_cache()
    
    if not cache.enabled:
        print("⚠️  Cache disabled, skipping test")
        return False
    
    # Test set
    test_key = "cache:test:key1"
    test_value = {"data": "test_value", "number": 123}
    
    print(f"Setting key: {test_key}")
    success = cache.set(test_key, test_value, ttl=60)
    
    if not success:
        print("❌ Failed to set cache value")
        return False
    
    # Test get
    print(f"Getting key: {test_key}")
    retrieved = cache.get(test_key)
    
    if retrieved == test_value:
        print(f"✅ Retrieved value matches: {retrieved}")
    else:
        print(f"❌ Retrieved value doesn't match. Expected: {test_value}, Got: {retrieved}")
        return False
    
    # Test non-existent key
    non_existent = cache.get("cache:test:doesntexist")
    if non_existent is None:
        print("✅ Non-existent key returns None")
    else:
        print(f"❌ Non-existent key should return None, got: {non_existent}")
        return False
    
    # Clean up
    cache.delete(test_key)
    
    return True


def test_ttl_expiration():
    """Test 3: TTL Expiration"""
    print("\n=== TEST 3: TTL Expiration ===")
    cache = get_cache()
    
    if not cache.enabled:
        print("⚠️  Cache disabled, skipping test")
        return False
    
    test_key = "cache:test:ttl_test"
    test_value = {"expires": True}
    
    # Set with 2 second TTL
    print("Setting key with 2 second TTL...")
    cache.set(test_key, test_value, ttl=2)
    
    # Should exist immediately
    retrieved = cache.get(test_key)
    if retrieved == test_value:
        print("✅ Value exists immediately after set")
    else:
        print("❌ Value not found immediately after set")
        return False
    
    # Wait 3 seconds
    print("Waiting 3 seconds for expiration...")
    time.sleep(3)
    
    # Should be expired
    retrieved = cache.get(test_key)
    if retrieved is None:
        print("✅ Value expired after TTL")
    else:
        print(f"❌ Value should have expired, but still exists: {retrieved}")
        return False
    
    return True


def test_cache_invalidation():
    """Test 4: Cache Invalidation"""
    print("\n=== TEST 4: Cache Invalidation ===")
    cache = get_cache()
    
    if not cache.enabled:
        print("⚠️  Cache disabled, skipping test")
        return False
    
    # Create test session with multiple keys
    session_id = "test_session_123"
    
    # Generate keys using the internal method
    keys = [
        cache._generate_cache_key("/transactions", user_id=1, session_id=session_id),
        cache._generate_cache_key("/summary", user_id=1, session_id=session_id),
        cache._generate_cache_key("/category-summary", user_id=1, session_id=session_id)
    ]
    
    print(f"Creating {len(keys)} cache entries for session {session_id}...")
    for key in keys:
        cache.set(key, {"test": "data"}, ttl=300)
    
    # Verify all exist
    all_exist = all(cache.get(key) is not None for key in keys)
    if all_exist:
        print("✅ All keys created successfully")
    else:
        print("❌ Not all keys were created")
        return False
    
    # Invalidate session
    print(f"Invalidating session: {session_id}...")
    deleted_count = cache.invalidate_session(session_id)
    print(f"Deleted {deleted_count} keys")
    
    # Verify all are gone
    all_gone = all(cache.get(key) is None for key in keys)
    if all_gone:
        print("✅ All keys invalidated successfully")
    else:
        print("❌ Some keys still exist after invalidation")
        return False
    
    return True


def test_statistics():
    """Test 5: Cache Statistics"""
    print("\n=== TEST 5: Cache Statistics ===")
    cache = get_cache()
    
    if not cache.enabled:
        print("⚠️  Cache disabled, skipping test")
        return False
    
    # Reset stats by flushing
    cache.flush_all()
    
    # Generate some cache activity
    test_keys = [f"cache:test:stats_{i}" for i in range(5)]
    
    print("Generating cache activity...")
    # Sets
    for key in test_keys:
        cache.set(key, {"data": key}, ttl=60)
    
    # Hits
    for key in test_keys[:3]:
        cache.get(key)  # Hit
    
    # Misses
    for i in range(2):
        cache.get(f"cache:test:nonexistent_{i}")  # Miss
    
    # Get statistics
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  Enabled: {stats['enabled']}")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Sets: {stats['sets']}")
    print(f"  Hit Rate: {stats['hit_rate']}%")
    print(f"  Size: {stats['size_mb']} MB")
    print(f"  Keys: {stats['keys']}")
    
    # Verify expected values
    if stats['hits'] >= 3 and stats['misses'] >= 2 and stats['sets'] >= 5:
        print("✅ Statistics tracking working correctly")
    else:
        print("❌ Statistics don't match expected values")
        return False
    
    # Clean up
    cache.flush_all()
    
    return True


def test_pattern_deletion():
    """Test 6: Pattern-Based Deletion"""
    print("\n=== TEST 6: Pattern-Based Deletion ===")
    cache = get_cache()
    
    if not cache.enabled:
        print("⚠️  Cache disabled, skipping test")
        return False
    
    # Create keys with different patterns
    keys = {
        "cache:/transactions:abc123": {"type": "transactions"},
        "cache:/transactions:def456": {"type": "transactions"},
        "cache:/summary:abc123": {"type": "summary"},
        "cache:/other:xyz789": {"type": "other"}
    }
    
    print(f"Creating {len(keys)} keys with different patterns...")
    for key, value in keys.items():
        cache.set(key, value, ttl=60)
    
    # Delete only transaction keys
    pattern = "cache:/transactions:*"
    print(f"Deleting keys matching pattern: {pattern}")
    deleted = cache.delete_pattern(pattern)
    print(f"Deleted {deleted} keys")
    
    # Verify transaction keys are gone
    txn_keys_gone = (
        cache.get("cache:/transactions:abc123") is None and
        cache.get("cache:/transactions:def456") is None
    )
    
    # Verify other keys still exist
    other_keys_exist = (
        cache.get("cache:/summary:abc123") is not None and
        cache.get("cache:/other:xyz789") is not None
    )
    
    if txn_keys_gone and other_keys_exist:
        print("✅ Pattern deletion working correctly")
    else:
        print("❌ Pattern deletion didn't work as expected")
        return False
    
    # Clean up
    cache.flush_all()
    
    return True


def main():
    print("=" * 60)
    print("REDIS CACHE SERVICE TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    results['Health Check'] = test_cache_health()
    
    # Only run other tests if cache is healthy
    if results['Health Check']:
        results['Basic Operations'] = test_basic_operations()
        results['TTL Expiration'] = test_ttl_expiration()
        results['Cache Invalidation'] = test_cache_invalidation()
        results['Statistics'] = test_statistics()
        results['Pattern Deletion'] = test_pattern_deletion()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:30} {status}")
    
    print("=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Cache system is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check Redis configuration.")
        return 1


if __name__ == "__main__":
    exit(main())
