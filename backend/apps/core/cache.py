"""Redis cache service wrapper."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)


class CacheService:
    """Thin wrapper around Redis for caching pipeline results."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    def get(self, key: str) -> str | None:
        """Get a cached value by key. Returns None if not found or on error."""
        try:
            value = self._redis.get(key)
            if value is None:
                return None
            return value.decode("utf-8") if isinstance(value, bytes) else value
        except Exception:
            logger.exception("Cache get failed for key=%s", key)
            return None

    def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None:
        """Set a cached value with TTL."""
        try:
            self._redis.setex(key, ttl_seconds, value)
        except Exception:
            logger.exception("Cache set failed for key=%s", key)

    def get_json(self, key: str) -> dict | list | None:
        """Get and deserialize a JSON-cached value."""
        raw = self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Cache value for key=%s is not valid JSON", key)
            return None

    def set_json(self, key: str, value: dict | list, ttl_seconds: int = 3600) -> None:
        """Serialize and cache a JSON value."""
        self.set(key, json.dumps(value), ttl_seconds)

    def delete(self, key: str) -> None:
        """Delete a cached key."""
        try:
            self._redis.delete(key)
        except Exception:
            logger.exception("Cache delete failed for key=%s", key)

    def publish(self, channel: str, message: str) -> None:
        """Publish a message to a Redis pub/sub channel."""
        try:
            self._redis.publish(channel, message)
        except Exception:
            logger.exception("Cache publish failed for channel=%s", channel)
