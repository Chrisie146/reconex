"""
Redis Cache Service for API Response Caching

Provides response caching for frequently accessed endpoints to improve
performance and reduce database load. Uses Redis as the cache backend
with automatic TTL expiration and cache invalidation.
"""

import os
import json
import hashlib
from typing import Optional, Any, Callable
from functools import wraps
from datetime import datetime, timedelta

import redis
from fastapi import Request


class CacheService:
    """
    Redis-based cache service for API responses.
    
    Features:
    - Response caching with TTL
    - Cache key generation with user/client/session isolation
    - Automatic cache invalidation
    - Cache statistics (hit/miss/size)
    - Pattern-based cache deletion
    """
    
    def __init__(self):
        """Initialize Redis connection for caching"""
        self.enabled = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        
        if not self.enabled:
            self.redis_client = None
            return
        
        # Use separate Redis database for cache (db=1, Celery uses db=0)
        cache_redis_url = os.getenv('REDIS_CACHE_URL', 'redis://localhost:6379/1')
        
        try:
            self.redis_client = redis.from_url(
                cache_redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            print(f"✅ Cache service initialized: {cache_redis_url}")
        except Exception as e:
            print(f"⚠️  Cache service unavailable: {e}")
            self.enabled = False
            self.redis_client = None
        
        # Default TTLs (in seconds)
        self.ttl_default = int(os.getenv('CACHE_TTL_DEFAULT', '300'))  # 5 minutes
        self.ttl_transactions = int(os.getenv('CACHE_TTL_TRANSACTIONS', '300'))  # 5 minutes
        self.ttl_summaries = int(os.getenv('CACHE_TTL_SUMMARIES', '1800'))  # 30 minutes
        self.ttl_rules = int(os.getenv('CACHE_TTL_RULES', '3600'))  # 1 hour
        self.ttl_sessions = int(os.getenv('CACHE_TTL_SESSIONS', '600'))  # 10 minutes
        
        # Statistics
        self.stats_key = 'cache:stats'
    
    def _generate_cache_key(self, endpoint: str, **kwargs) -> str:
        """
        Generate unique cache key based on endpoint and parameters.
        
        Args:
            endpoint: API endpoint path (e.g., '/transactions')
            **kwargs: Query parameters and context (user_id, session_id, etc.)
        
        Returns:
            Unique cache key string
        """
        # Sort kwargs for consistent key generation
        params = sorted(kwargs.items())
        params_str = json.dumps(params, sort_keys=True)
        
        # Create hash of parameters
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:16]
        
        return f"cache:{endpoint}:{params_hash}"
    
    def get(self, key: str) -> Optional[dict]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value as dict, or None if not found
        """
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            cached_value = self.redis_client.get(key)
            if cached_value:
                self._increment_stat('hits')
                return json.loads(cached_value)
            else:
                self._increment_stat('misses')
                return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (default: ttl_default)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.ttl_default
            serialized_value = json.dumps(value, default=str)
            self.redis_client.setex(key, ttl, serialized_value)
            self._increment_stat('sets')
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete specific key from cache.
        
        Args:
            key: Cache key to delete
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            self.redis_client.delete(key)
            self._increment_stat('deletes')
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., 'cache:/transactions:*')
        
        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis_client:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                self._increment_stat('deletes', deleted)
                return deleted
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0
    
    def invalidate_session(self, session_id: str) -> int:
        """
        Invalidate all cache entries for a session.
        
        Args:
            session_id: Session ID
        
        Returns:
            Number of keys deleted
        """
        pattern = f"cache:*:*session_id*{session_id}*"
        return self.delete_pattern(pattern)
    
    def invalidate_user(self, user_id: int) -> int:
        """
        Invalidate all cache entries for a user.
        
        Args:
            user_id: User ID
        
        Returns:
            Number of keys deleted
        """
        pattern = f"cache:*:*user_id*{user_id}*"
        return self.delete_pattern(pattern)
    
    def invalidate_client(self, client_id: int) -> int:
        """
        Invalidate all cache entries for a client.
        
        Args:
            client_id: Client ID
        
        Returns:
            Number of keys deleted
        """
        pattern = f"cache:*:*client_id*{client_id}*"
        return self.delete_pattern(pattern)
    
    def flush_all(self) -> bool:
        """
        Flush all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            self.redis_client.flushdb()
            self._reset_stats()
            return True
        except Exception as e:
            print(f"Cache flush error: {e}")
            return False
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics (hits, misses, hit_rate, size, keys)
        """
        if not self.enabled or not self.redis_client:
            return {
                'enabled': False,
                'hits': 0,
                'misses': 0,
                'sets': 0,
                'deletes': 0,
                'hit_rate': 0.0,
                'size_mb': 0.0,
                'keys': 0
            }
        
        try:
            stats = self.redis_client.hgetall(self.stats_key)
            hits = int(stats.get('hits', 0))
            misses = int(stats.get('misses', 0))
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0.0
            
            # Get memory usage
            info = self.redis_client.info('memory')
            size_mb = info.get('used_memory', 0) / (1024 * 1024)
            
            # Get number of cache keys
            cache_keys = len(self.redis_client.keys('cache:*'))
            
            return {
                'enabled': True,
                'hits': hits,
                'misses': misses,
                'sets': int(stats.get('sets', 0)),
                'deletes': int(stats.get('deletes', 0)),
                'hit_rate': round(hit_rate, 2),
                'size_mb': round(size_mb, 2),
                'keys': cache_keys
            }
        except Exception as e:
            print(f"Cache stats error: {e}")
            return {'enabled': False, 'error': str(e)}
    
    def _increment_stat(self, stat_name: str, value: int = 1):
        """Increment cache statistic counter"""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            self.redis_client.hincrby(self.stats_key, stat_name, value)
        except Exception:
            pass
    
    def _reset_stats(self):
        """Reset cache statistics"""
        if not self.enabled or not self.redis_client:
            return
        
        try:
            self.redis_client.delete(self.stats_key)
        except Exception:
            pass
    
    def health_check(self) -> dict:
        """
        Check cache health status.
        
        Returns:
            Dict with health status
        """
        if not self.enabled:
            return {'status': 'disabled'}
        
        if not self.redis_client:
            return {'status': 'unavailable', 'error': 'Redis client not initialized'}
        
        try:
            self.redis_client.ping()
            return {'status': 'healthy', 'redis_db': self.redis_client.connection_pool.connection_kwargs.get('db', 1)}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}


# Singleton instance
_cache_service = None


def get_cache() -> CacheService:
    """Get or create cache service singleton"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def cached(ttl: Optional[int] = None):
    """
    Decorator for caching FastAPI endpoint responses.
    
    Usage:
        @app.get("/transactions")
        @cached(ttl=300)  # Cache for 5 minutes
        async def get_transactions(session_id: str, current_user: User = Depends(get_current_user)):
            ...
    
    Args:
        ttl: Time to live in seconds (optional, uses default if not specified)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Skip cache if disabled
            if not cache.enabled:
                return await func(*args, **kwargs)
            
            # Extract request parameters for cache key
            request = kwargs.get('request')
            current_user = kwargs.get('current_user')
            
            # Build cache key from endpoint and parameters
            endpoint = request.url.path if request else func.__name__
            cache_params = {
                'user_id': current_user.id if current_user else None,
                **{k: v for k, v in kwargs.items() if k not in ['request', 'db', 'current_user']}
            }
            
            # Add query parameters if request exists
            if request:
                cache_params.update(dict(request.query_params))
            
            cache_key = cache._generate_cache_key(endpoint, **cache_params)
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response
            
            # Call original function
            response = await func(*args, **kwargs)
            
            # Cache the response
            cache.set(cache_key, response, ttl)
            
            return response
        
        return wrapper
    return decorator
