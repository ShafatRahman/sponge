"""Tests for the Redis-based sliding window rate limiter."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from apps.core.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from redis import Redis


@pytest.fixture()
def rate_limiter(fake_redis: Redis) -> RateLimiter:
    return RateLimiter(fake_redis)


class TestRateLimiter:
    """Test sliding-window rate limiting logic."""

    def test_allows_under_limit(self, rate_limiter: RateLimiter) -> None:
        result = rate_limiter.check("test:user1", limit=5, window_seconds=60)
        assert result.allowed is True
        assert result.remaining == 4

    def test_allows_up_to_limit(self, rate_limiter: RateLimiter) -> None:
        for i in range(5):
            result = rate_limiter.check("test:user2", limit=5, window_seconds=60)
            assert result.allowed is True
            assert result.remaining == 4 - i

    def test_rejects_over_limit(self, rate_limiter: RateLimiter) -> None:
        for _ in range(3):
            rate_limiter.check("test:user3", limit=3, window_seconds=60)

        result = rate_limiter.check("test:user3", limit=3, window_seconds=60)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.reset_at is not None

    def test_rejected_request_not_counted(
        self, rate_limiter: RateLimiter, fake_redis: Redis
    ) -> None:
        """Rejected requests should NOT be added to the sorted set."""
        for _ in range(2):
            rate_limiter.check("test:user4", limit=2, window_seconds=60)

        # This request should be rejected and NOT counted
        rate_limiter.check("test:user4", limit=2, window_seconds=60)

        count = fake_redis.zcard("ratelimit:test:user4")
        assert count == 2  # Only the 2 allowed requests

    def test_check_user_delegates(self, rate_limiter: RateLimiter) -> None:
        result = rate_limiter.check_user("abc-123", limit=10)
        assert result.allowed is True

    def test_check_ip_delegates(self, rate_limiter: RateLimiter) -> None:
        result = rate_limiter.check_ip("192.0.2.1", limit=5)
        assert result.allowed is True

    def test_check_domain_uses_one_second_window(self, rate_limiter: RateLimiter) -> None:
        result = rate_limiter.check_domain("example.com", limit=2.0)
        assert result.allowed is True

    def test_separate_identifiers_independent(self, rate_limiter: RateLimiter) -> None:
        for _ in range(3):
            rate_limiter.check("test:a", limit=3, window_seconds=60)

        # user a is at limit
        result_a = rate_limiter.check("test:a", limit=3, window_seconds=60)
        assert result_a.allowed is False

        # user b is independent
        result_b = rate_limiter.check("test:b", limit=3, window_seconds=60)
        assert result_b.allowed is True
