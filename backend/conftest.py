"""Shared pytest fixtures for the Sponge backend test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import fakeredis
import pytest

from apps.core.cache import CacheService
from apps.core.models import JobMode, JobStatus

if TYPE_CHECKING:
    import uuid

    from redis import Redis

    from apps.jobs.models import Job


@pytest.fixture()
def fake_redis() -> Redis:
    """Return a fakeredis instance that behaves like a real Redis connection."""
    return fakeredis.FakeRedis(decode_responses=False)


@pytest.fixture()
def cache_service(fake_redis: Redis) -> CacheService:
    """Return a CacheService backed by fakeredis."""
    return CacheService(fake_redis)


@pytest.fixture()
def job_factory(db):
    """Factory fixture for creating Job model instances."""

    def _create(
        *,
        url: str = "https://example.com",
        mode: str = JobMode.DEFAULT.value,
        status: str = JobStatus.PENDING.value,
        user_id: uuid.UUID | None = None,
        ip_address: str = "127.0.0.1",
        config: dict | None = None,
        result_llms_txt: str = "",
        error_message: str = "",
    ) -> Job:
        from apps.jobs.models import Job

        return Job.objects.create(
            url=url,
            mode=mode,
            status=status,
            user_id=user_id,
            ip_address=ip_address,
            config=config or {"crawl": {"max_urls": 50}},
            result_llms_txt=result_llms_txt,
            error_message=error_message,
        )

    return _create
