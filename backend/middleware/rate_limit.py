"""
In-memory rate limiting middleware for the Creator Sticker Platform.

Security fix H2: Prevents abuse of sensitive endpoints.

Uses a simple sliding-window counter per IP address.
For production, replace with Redis-backed limiter.
"""
import time
import logging
from collections import defaultdict
from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory sliding-window rate limiter.

    Tracks request timestamps per (IP, route) key.
    Not suitable for multi-worker deployments (use Redis instead).
    """

    def __init__(self):
        # {key: [timestamp1, timestamp2, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str, window_seconds: int):
        """Remove expired timestamps from the window."""
        now = time.time()
        cutoff = now - window_seconds
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier (e.g., "IP:route")
            max_requests: Maximum allowed requests in the window
            window_seconds: Time window in seconds

        Returns:
            True if allowed, False if rate-limited
        """
        self._cleanup(key, window_seconds)

        if len(self._requests[key]) >= max_requests:
            return False

        self._requests[key].append(time.time())
        return True

    def remaining(self, key: str, max_requests: int, window_seconds: int) -> int:
        """Get the number of remaining requests in the current window."""
        self._cleanup(key, window_seconds)
        return max(0, max_requests - len(self._requests[key]))


# Global rate limiter instance
_limiter = RateLimiter()


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """
    FastAPI dependency factory for rate limiting.

    Usage:
        @router.post("/register")
        async def register(request: Request, _=Depends(rate_limit(5, 3600))):
            ...

    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    """
    async def _check_rate_limit(request: Request):
        # Use client IP + route path as the rate limit key
        client_ip = request.client.host if request.client else "unknown"
        route_path = request.url.path
        key = f"{client_ip}:{route_path}"

        if not _limiter.check(key, max_requests, window_seconds):
            remaining = _limiter.remaining(key, max_requests, window_seconds)
            logger.warning(
                f"Rate limit exceeded: {client_ip} on {route_path} "
                f"({max_requests}/{window_seconds}s)"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests "
                       f"per {window_seconds} seconds. Try again later.",
                headers={
                    "Retry-After": str(window_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                },
            )

    return _check_rate_limit
