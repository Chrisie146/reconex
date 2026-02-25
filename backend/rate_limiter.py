"""
Rate limiting middleware for API endpoints
Prevents abuse by limiting requests per time window.

Uses Redis (shared across all workers) when CACHE_ENABLED=true and Redis is
reachable.  Falls back to process-local in-memory sliding windows when Redis
is not available, so the service still works but per-process limits apply.
"""

from fastapi import Request
from typing import Dict, Optional
import time
import logging
from collections import defaultdict, deque

from config import Config
from exceptions import RateLimitError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def _get_redis():
    """Return a connected Redis client when caching is enabled, else None."""
    if not Config.CACHE_ENABLED:
        return None
    try:
        import redis as redis_lib
        client = redis_lib.from_url(
            Config.REDIS_CACHE_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        logger.info("[RateLimiter] Redis connection established — shared rate limiting active")
        return client
    except Exception as exc:
        logger.warning(f"[RateLimiter] Redis unavailable — falling back to in-memory: {exc}")
        return None


def _redis_sliding_window(redis_client, key: str, limit: int, window_seconds: int) -> int:
    """
    Increment a sliding-window counter in Redis using a sorted set.
    Returns the request count *after* adding the current request.

    Uses ZADD + ZREMRANGEBYSCORE + ZCARD in a pipeline for atomicity.
    """
    now = time.time()
    cutoff = now - window_seconds
    member = f"{now}:{id(redis_client)}"  # unique member per request

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, "-inf", cutoff)          # drop expired entries
    pipe.zadd(key, {member: now})                        # record this request
    pipe.zcard(key)                                      # count in window
    pipe.expire(key, window_seconds + 5)                 # auto-expire the key
    results = pipe.execute()
    return int(results[2])  # zcard result


# ---------------------------------------------------------------------------
# In-memory sliding window (per-process fallback)
# ---------------------------------------------------------------------------

class _InMemoryRateLimiter:
    """Process-local sliding window rate limiter (no shared state)."""

    def __init__(self, requests_per_minute: int, requests_per_hour: int):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_windows: Dict[str, deque] = defaultdict(deque)
        self.hour_windows: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def _cleanup_old_entries(self):
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        for client_id in list(self.minute_windows.keys()):
            w = self.minute_windows[client_id]
            while w and w[0] < cutoff_minute:
                w.popleft()
            if not w:
                del self.minute_windows[client_id]
        for client_id in list(self.hour_windows.keys()):
            w = self.hour_windows[client_id]
            while w and w[0] < cutoff_hour:
                w.popleft()
            if not w:
                del self.hour_windows[client_id]
        self.last_cleanup = current_time

    def check(self, client_id: str) -> Dict:
        """Check limits and record the request. Raises RateLimitError if exceeded."""
        current_time = time.time()
        self._cleanup_old_entries()

        # --- minute window ---
        mw = self.minute_windows[client_id]
        cutoff_min = current_time - 60
        while mw and mw[0] < cutoff_min:
            mw.popleft()
        minute_count = len(mw)

        # --- hour window ---
        hw = self.hour_windows[client_id]
        cutoff_hr = current_time - 3600
        while hw and hw[0] < cutoff_hr:
            hw.popleft()
        hour_count = len(hw)

        if minute_count >= self.requests_per_minute:
            reset_seconds = int(60 - (current_time - mw[0]))
            logger.warning(f"[RateLimiter] Minute limit exceeded for {client_id}: {minute_count}/{self.requests_per_minute}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_minute} requests per minute. Retry in {reset_seconds}s.",
                retry_after=reset_seconds,
            )

        if hour_count >= self.requests_per_hour:
            reset_seconds = int(3600 - (current_time - hw[0]))
            logger.warning(f"[RateLimiter] Hour limit exceeded for {client_id}: {hour_count}/{self.requests_per_hour}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_hour} requests per hour. Retry in {reset_seconds // 60} min.",
                retry_after=reset_seconds,
            )

        mw.append(current_time)
        hw.append(current_time)

        remaining = min(
            self.requests_per_minute - minute_count - 1,
            self.requests_per_hour - hour_count - 1,
        )
        reset = int(60 - (current_time - mw[0]) if mw else 60)
        return {"allowed": True, "limit": self.requests_per_minute, "remaining": remaining, "reset": reset}


# ---------------------------------------------------------------------------
# Public RateLimiter class (Redis when available, in-memory fallback)
# ---------------------------------------------------------------------------

class RateLimiter:
    """
    Sliding window rate limiter with Redis backend and in-memory fallback.

    When CACHE_ENABLED=true and Redis is reachable the limits are enforced
    *across all worker processes* (correct multi-worker behaviour).

    When Redis is unavailable (e.g., local dev, Redis down) the limiter
    transparently falls back to process-local memory.  Rate limits still
    work but are per-worker rather than global — a safe degradation.
    """

    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self._redis = _get_redis()
        self._memory = _InMemoryRateLimiter(requests_per_minute, requests_per_hour)
        backend = "Redis (shared)" if self._redis else "in-memory (per-worker)"
        logger.info(f"[RateLimiter] {requests_per_minute}/min · {requests_per_hour}/hr · backend={backend}")

    def _get_client_id(self, request: Request, user_id: Optional[int] = None) -> str:
        """Use user_id when authenticated; fall back to IP address."""
        if user_id:
            return f"user:{user_id}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[int] = None,
    ) -> Dict:
        """
        Check rate limit and record the request.

        Returns dict: {allowed, limit, remaining, reset}.
        Raises RateLimitError if the limit is exceeded.
        """
        client_id = self._get_client_id(request, user_id)

        if self._redis:
            try:
                return self._check_redis(client_id)
            except RateLimitError:
                raise
            except Exception as exc:
                logger.warning(f"[RateLimiter] Redis error, falling back to in-memory: {exc}")
                self._redis = None  # stop retrying this instance

        return self._memory.check(client_id)

    def _check_redis(self, client_id: str) -> Dict:
        minute_count = _redis_sliding_window(
            self._redis, f"rl:min:{client_id}", self.requests_per_minute, 60
        )
        hour_count = _redis_sliding_window(
            self._redis, f"rl:hr:{client_id}", self.requests_per_hour, 3600
        )

        if minute_count > self.requests_per_minute:
            logger.warning(f"[RateLimiter] Minute limit exceeded (Redis) for {client_id}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_minute} requests per minute.",
                retry_after=60,
            )
        if hour_count > self.requests_per_hour:
            logger.warning(f"[RateLimiter] Hour limit exceeded (Redis) for {client_id}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_hour} requests per hour.",
                retry_after=3600,
            )

        remaining = min(
            self.requests_per_minute - minute_count,
            self.requests_per_hour - hour_count,
        )
        return {"allowed": True, "limit": self.requests_per_minute, "remaining": remaining, "reset": 60}


# ---------------------------------------------------------------------------
# Global limiter instances (created once at module import time)
# ---------------------------------------------------------------------------

standard_limiter = RateLimiter(
    requests_per_minute=Config.RATE_LIMIT_PER_MINUTE,
    requests_per_hour=Config.RATE_LIMIT_PER_HOUR,
)

upload_limiter = RateLimiter(
    requests_per_minute=Config.UPLOAD_RATE_LIMIT_PER_MINUTE,
    requests_per_hour=Config.UPLOAD_RATE_LIMIT_PER_HOUR,
)

read_limiter = RateLimiter(
    requests_per_minute=Config.READ_RATE_LIMIT_PER_MINUTE,
    requests_per_hour=Config.READ_RATE_LIMIT_PER_HOUR,
)


def add_rate_limit_headers(response, rate_info: Dict):
    """Attach X-RateLimit-* headers to an HTTP response."""
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
    return response

