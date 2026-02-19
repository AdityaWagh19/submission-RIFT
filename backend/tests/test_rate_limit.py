"""
Tests for in-memory rate limiter middleware.

Tests: RateLimiter class — sliding window, cleanup, rate_limit dependency.
"""
# TODO FOR JULES:
# 1. Add tests for concurrent access (asyncio.gather with multiple requests)
# 2. Add tests for rate limit headers in response (Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining)
# 3. Add tests for different IP addresses (should have independent limits)
# 4. Add integration test with actual FastAPI endpoint
# 5. Add tests for edge case: exactly at the limit boundary
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import pytest
from middleware.rate_limit import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.unit
    def test_allows_requests_under_limit(self):
        """Requests under the limit should be allowed."""
        limiter = RateLimiter()
        for i in range(5):
            assert limiter.check("testkey", max_requests=5, window_seconds=60) is True

    @pytest.mark.unit
    def test_blocks_requests_over_limit(self):
        """Request exceeding the limit should be blocked."""
        limiter = RateLimiter()
        for _ in range(3):
            limiter.check("testkey", max_requests=3, window_seconds=60)
        # 4th request should be blocked
        assert limiter.check("testkey", max_requests=3, window_seconds=60) is False

    @pytest.mark.unit
    def test_different_keys_independent(self):
        """Different keys should have independent limits."""
        limiter = RateLimiter()
        # Fill up key1
        for _ in range(3):
            limiter.check("key1", max_requests=3, window_seconds=60)
        # key1 should be blocked
        assert limiter.check("key1", max_requests=3, window_seconds=60) is False
        # key2 should still be allowed
        assert limiter.check("key2", max_requests=3, window_seconds=60) is True

    @pytest.mark.unit
    def test_window_expiry(self):
        """Requests should be allowed again after the window expires."""
        limiter = RateLimiter()
        # Fill up with max requests in a very short window
        for _ in range(2):
            limiter.check("testkey", max_requests=2, window_seconds=1)
        # Should be blocked
        assert limiter.check("testkey", max_requests=2, window_seconds=1) is False
        # Wait for window to expire
        time.sleep(1.1)
        # Should be allowed again
        assert limiter.check("testkey", max_requests=2, window_seconds=1) is True

    @pytest.mark.unit
    def test_remaining_count(self):
        """remaining() should return correct count."""
        limiter = RateLimiter()
        assert limiter.remaining("testkey", max_requests=5, window_seconds=60) == 5
        limiter.check("testkey", max_requests=5, window_seconds=60)
        assert limiter.remaining("testkey", max_requests=5, window_seconds=60) == 4
        limiter.check("testkey", max_requests=5, window_seconds=60)
        assert limiter.remaining("testkey", max_requests=5, window_seconds=60) == 3

    @pytest.mark.unit
    def test_remaining_at_zero(self):
        """remaining() should return 0 when limit is reached, not negative."""
        limiter = RateLimiter()
        for _ in range(5):
            limiter.check("testkey", max_requests=5, window_seconds=60)
        assert limiter.remaining("testkey", max_requests=5, window_seconds=60) == 0

    @pytest.mark.unit
    def test_single_request_limit(self):
        """Edge case: max_requests=1 should allow exactly 1."""
        limiter = RateLimiter()
        assert limiter.check("once", max_requests=1, window_seconds=60) is True
        assert limiter.check("once", max_requests=1, window_seconds=60) is False

    @pytest.mark.unit
    def test_cleanup_removes_old_entries(self):
        """_cleanup should remove timestamps older than the window."""
        limiter = RateLimiter()
        # Manually inject old timestamps
        old_time = time.time() - 120  # 2 minutes ago
        limiter._requests["testkey"] = [old_time, old_time + 1, old_time + 2]
        # After cleanup with 60s window, all should be removed
        limiter._cleanup("testkey", 60)
        assert len(limiter._requests["testkey"]) == 0
