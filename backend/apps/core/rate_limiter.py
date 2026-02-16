"""Redis-based sliding window rate limiter."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apps.core.models import RateLimitResult

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)

DAY_SECONDS = 86400


class RateLimiter:
    """Sliding-window rate limiter backed by Redis sorted sets.

    Supports per-IP, per-user, and per-domain rate limiting.
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def check(
        self,
        identifier: str,
        limit: int,
        window_seconds: int = DAY_SECONDS,
    ) -> RateLimitResult:
        """Check if the identifier is within the rate limit.

        Uses a Redis sorted set with timestamps as scores.
        Only adds the current request if the limit has not been exceeded.
        """
        now = time.time()
        window_start = now - window_seconds
        key = f"ratelimit:{identifier}"

        # First: clean expired entries and count current usage
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        results = pipe.execute()

        current_count = results[1]

        if current_count >= limit:
            # Already at limit -- do NOT add this request
            oldest = self._redis.zrange(key, 0, 0, withscores=True)
            reset_timestamp = oldest[0][1] + window_seconds if oldest else now + window_seconds
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=datetime.fromtimestamp(reset_timestamp, tz=UTC),
            )

        # Under limit -- record this request
        pipe2 = self._redis.pipeline()
        pipe2.zadd(key, {str(now): now})
        pipe2.expire(key, window_seconds)
        pipe2.execute()

        remaining = max(0, limit - current_count - 1)
        return RateLimitResult(allowed=True, remaining=remaining)

    def check_user(self, user_id: str, limit: int) -> RateLimitResult:
        """Check rate limit for an authenticated user."""
        return self.check(f"user:{user_id}", limit)

    def check_ip(self, ip_address: str, limit: int) -> RateLimitResult:
        """Check rate limit for an anonymous user by IP."""
        return self.check(f"ip:{ip_address}", limit)

    def check_domain(self, domain: str, limit: float) -> RateLimitResult:
        """Check per-domain rate limit (requests per second)."""
        return self.check(f"domain:{domain}", int(limit), window_seconds=1)
