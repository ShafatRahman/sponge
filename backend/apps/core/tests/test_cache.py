"""Tests for the CacheService wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from apps.core.cache import CacheService


class TestCacheService:
    """Test CacheService get/set/delete/publish operations."""

    def test_set_and_get(self, cache_service: CacheService) -> None:
        cache_service.set("key1", "value1", ttl_seconds=60)
        assert cache_service.get("key1") == "value1"

    def test_get_missing_key_returns_none(self, cache_service: CacheService) -> None:
        assert cache_service.get("nonexistent") is None

    def test_set_json_and_get_json(self, cache_service: CacheService) -> None:
        data = {"status": "ok", "count": 42}
        cache_service.set_json("json1", data, ttl_seconds=60)
        result = cache_service.get_json("json1")
        assert result == data

    def test_get_json_returns_none_for_missing(self, cache_service: CacheService) -> None:
        assert cache_service.get_json("missing") is None

    def test_get_json_returns_none_for_invalid_json(self, cache_service: CacheService) -> None:
        cache_service.set("bad_json", "not-json{", ttl_seconds=60)
        assert cache_service.get_json("bad_json") is None

    def test_delete_removes_key(self, cache_service: CacheService) -> None:
        cache_service.set("del_me", "value", ttl_seconds=60)
        assert cache_service.get("del_me") == "value"
        cache_service.delete("del_me")
        assert cache_service.get("del_me") is None

    def test_delete_nonexistent_key_no_error(self, cache_service: CacheService) -> None:
        cache_service.delete("never_existed")

    @pytest.mark.parametrize("value", ["hello", '{"key": "val"}', ""])
    def test_set_various_values(self, cache_service: CacheService, value: str) -> None:
        cache_service.set("varied", value, ttl_seconds=60)
        assert cache_service.get("varied") == value

    def test_publish_does_not_raise(self, cache_service: CacheService) -> None:
        """Publish should not raise even if no subscribers exist."""
        cache_service.publish("some:channel", '{"event": "test"}')

    def test_get_json_list(self, cache_service: CacheService) -> None:
        data = [1, 2, 3]
        cache_service.set_json("list1", data, ttl_seconds=60)
        result = cache_service.get_json("list1")
        assert result == [1, 2, 3]
