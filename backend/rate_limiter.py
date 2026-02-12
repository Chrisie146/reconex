"""
Rate limiting middleware for API endpoints
Prevents abuse by limiting requests per time window
"""

from fastapi import Request
from typing import Dict, Optional
import time
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

from config import Config
from exceptions import RateLimitError

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window algorithm
    For production, consider Redis-backed solution (slowapi, etc.)
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Store request timestamps per client
        # Format: {client_id: deque([timestamp1, timestamp2, ...])}
        self.minute_windows: Dict[str, deque] = defaultdict(deque)
        self.hour_windows: Dict[str, deque] = defaultdict(deque)
        
        # Cleanup old entries periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory growth"""
        current_time = time.time()
        
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_minute = current_time - 60
        cutoff_hour = current_time - 3600
        
        # Clean up minute windows
        for client_id in list(self.minute_windows.keys()):
            window = self.minute_windows[client_id]
            while window and window[0] < cutoff_minute:
                window.popleft()
            if not window:
                del self.minute_windows[client_id]
        
        # Clean up hour windows
        for client_id in list(self.hour_windows.keys()):
            window = self.hour_windows[client_id]
            while window and window[0] < cutoff_hour:
                window.popleft()
            if not window:
                del self.hour_windows[client_id]
        
        self.last_cleanup = current_time
        logger.debug(f"Rate limiter cleanup completed. Active clients: {len(self.minute_windows)}")
    
    def _get_client_id(self, request: Request, user_id: Optional[int] = None) -> str:
        """
        Get unique identifier for client
        Prefer user_id if authenticated, otherwise use IP
        """
        if user_id:
            return f"user:{user_id}"
        
        # Get client IP from headers (proxy-aware)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    def check_rate_limit(
        self,
        request: Request,
        user_id: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Check if request is within rate limits
        
        Returns:
            Dict with: {
                "allowed": bool,
                "limit": int,
                "remaining": int,
                "reset": int (seconds until reset)
            }
        
        Raises:
            RateLimitError: If rate limit exceeded
        """
        current_time = time.time()
        client_id = self._get_client_id(request, user_id)
        
        # Periodic cleanup
        self._cleanup_old_entries()
        
        # Check minute window
        minute_window = self.minute_windows[client_id]
        cutoff_minute = current_time - 60
        
        # Remove old entries
        while minute_window and minute_window[0] < cutoff_minute:
            minute_window.popleft()
        
        minute_count = len(minute_window)
        minute_remaining = max(0, self.requests_per_minute - minute_count)
        
        # Check hour window
        hour_window = self.hour_windows[client_id]
        cutoff_hour = current_time - 3600
        
        # Remove old entries
        while hour_window and hour_window[0] < cutoff_hour:
            hour_window.popleft()
        
        hour_count = len(hour_window)
        hour_remaining = max(0, self.requests_per_hour - hour_count)
        
        # Determine if allowed
        if minute_count >= self.requests_per_minute:
            reset_seconds = int(60 - (current_time - minute_window[0]))
            logger.warning(f"Rate limit exceeded (minute) for {client_id}: {minute_count}/{self.requests_per_minute}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_minute} requests per minute. Try again in {reset_seconds} seconds.",
                retry_after=reset_seconds
            )
        
        if hour_count >= self.requests_per_hour:
            reset_seconds = int(3600 - (current_time - hour_window[0]))
            logger.warning(f"Rate limit exceeded (hour) for {client_id}: {hour_count}/{self.requests_per_hour}")
            raise RateLimitError(
                message=f"Rate limit exceeded: {self.requests_per_hour} requests per hour. Try again in {reset_seconds // 60} minutes.",
                retry_after=reset_seconds
            )
        
        # Add current request to windows
        minute_window.append(current_time)
        hour_window.append(current_time)
        
        # Return rate limit info
        remaining = min(minute_remaining - 1, hour_remaining - 1)
        reset = int(60 - (current_time - minute_window[0]) if minute_window else 60)
        
        return {
            "allowed": True,
            "limit": self.requests_per_minute,
            "remaining": remaining,
            "reset": reset
        }


# Global rate limiter instances
# Standard rate limit for most endpoints
standard_limiter = RateLimiter(
    requests_per_minute=int(Config.RATE_LIMIT_PER_MINUTE) if hasattr(Config, 'RATE_LIMIT_PER_MINUTE') else 60,
    requests_per_hour=int(Config.RATE_LIMIT_PER_HOUR) if hasattr(Config, 'RATE_LIMIT_PER_HOUR') else 1000
)

# Stricter rate limit for file uploads (more resource-intensive)
upload_limiter = RateLimiter(
    requests_per_minute=int(Config.UPLOAD_RATE_LIMIT_PER_MINUTE) if hasattr(Config, 'UPLOAD_RATE_LIMIT_PER_MINUTE') else 10,
    requests_per_hour=int(Config.UPLOAD_RATE_LIMIT_PER_HOUR) if hasattr(Config, 'UPLOAD_RATE_LIMIT_PER_HOUR') else 100
)

# Lenient rate limit for GET requests
read_limiter = RateLimiter(
    requests_per_minute=int(Config.READ_RATE_LIMIT_PER_MINUTE) if hasattr(Config, 'READ_RATE_LIMIT_PER_MINUTE') else 120,
    requests_per_hour=int(Config.READ_RATE_LIMIT_PER_HOUR) if hasattr(Config, 'READ_RATE_LIMIT_PER_HOUR') else 2000
)


def add_rate_limit_headers(response, rate_info: Dict):
    """Add rate limit headers to response"""
    response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])
    return response
