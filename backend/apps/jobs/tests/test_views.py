"""Integration tests for the Jobs API views."""

from __future__ import annotations

import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.models import JobMode, JobStatus


@override_settings(
    SUPABASE_URL="",
    REDIS_URL="redis://localhost:6379/0",
)
class TestJobCreateView(TestCase):
    """Test POST /api/jobs/ endpoint."""

    def setUp(self) -> None:
        self.client = APIClient()

    @patch("apps.jobs.views._get_redis")
    @patch("apps.jobs.tasks.generate.delay")
    @patch("socket.gethostbyname", return_value="93.184.216.34")
    def test_create_default_job(self, _dns: object, mock_delay: object, mock_redis: object) -> None:
        import fakeredis

        mock_redis.return_value = fakeredis.FakeRedis()

        response = self.client.post(
            "/api/jobs/",
            {"url": "https://example.com", "mode": "default"},
            format="json",
        )
        assert response.status_code == 201
        data = response.json()
        assert data["url"] == "https://example.com"
        assert data["mode"] == "default"
        assert data["status"] == "pending"
        assert "id" in data
        mock_delay.assert_called_once()

    @patch("apps.jobs.views._get_redis")
    @patch("apps.jobs.tasks.generate.delay")
    @patch("socket.gethostbyname", return_value="93.184.216.34")
    def test_create_detailed_job(
        self, _dns: object, mock_delay: object, mock_redis: object
    ) -> None:
        import fakeredis

        mock_redis.return_value = fakeredis.FakeRedis()

        response = self.client.post(
            "/api/jobs/",
            {"url": "https://example.com", "mode": "detailed"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["mode"] == "detailed"
        mock_delay.assert_called_once()

    def test_create_job_invalid_url(self) -> None:
        response = self.client.post(
            "/api/jobs/",
            {"url": "not-a-url", "mode": "default"},
            format="json",
        )
        assert response.status_code == 400

    def test_create_job_missing_url(self) -> None:
        response = self.client.post(
            "/api/jobs/",
            {"mode": "default"},
            format="json",
        )
        assert response.status_code == 400

    @patch("apps.jobs.views._get_redis")
    @patch("socket.gethostbyname", return_value="93.184.216.34")
    def test_rate_limit_blocks_excess_requests(self, _dns: object, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        # Anonymous daily limit is 3 by default
        for _ in range(3):
            with patch("apps.jobs.tasks.generate.delay"):
                response = self.client.post(
                    "/api/jobs/",
                    {"url": "https://example.com", "mode": "default"},
                    format="json",
                )
                assert response.status_code == 201

        # 4th request should be rate-limited
        with patch("apps.jobs.tasks.generate.delay"):
            response = self.client.post(
                "/api/jobs/",
                {"url": "https://example.com", "mode": "default"},
                format="json",
            )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]


@override_settings(
    SUPABASE_URL="",
    REDIS_URL="redis://localhost:6379/0",
)
class TestJobDetailView(TestCase):
    """Test GET /api/jobs/<id>/ endpoint."""

    def setUp(self) -> None:
        self.client = APIClient()

    @patch("apps.jobs.views._get_redis")
    def test_get_pending_job(self, mock_redis: object) -> None:
        import fakeredis

        mock_redis.return_value = fakeredis.FakeRedis()

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.PENDING.value,
        )

        response = self.client.get(f"/api/jobs/{job.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(job.id)
        assert data["status"] == "pending"
        assert data["progress"] is None
        assert data["result"] is None

    @patch("apps.jobs.views._get_redis")
    def test_get_job_with_progress(self, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.EXTRACTING.value,
        )

        progress = {
            "job_id": str(job.id),
            "phase": "extracting",
            "message": "Extracting 5/10",
            "completed": 5,
            "total": 10,
        }
        fake.set(f"job:{job.id}:progress", json.dumps(progress).encode())

        response = self.client.get(f"/api/jobs/{job.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["progress"]["phase"] == "extracting"
        assert data["progress"]["completed"] == 5

    @patch("apps.jobs.views._get_redis")
    def test_get_completed_job_with_result(self, mock_redis: object) -> None:
        import fakeredis

        mock_redis.return_value = fakeredis.FakeRedis()

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.COMPLETED.value,
            result_llms_txt="# Example\n> A website\n",
            result_meta={
                "total_pages": 10,
                "pages_processed": 9,
                "pages_failed": 1,
                "generation_time_seconds": 5.2,
            },
        )

        response = self.client.get(f"/api/jobs/{job.id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["llms_txt"] == "# Example\n> A website\n"
        assert data["result"]["total_pages"] == 10

    def test_get_nonexistent_job(self) -> None:
        response = self.client.get("/api/jobs/00000000-0000-0000-0000-000000000000/")
        assert response.status_code == 404


@override_settings(
    SUPABASE_URL="",
    REDIS_URL="redis://localhost:6379/0",
)
class TestJobStreamView(TestCase):
    """Test GET /api/jobs/<id>/stream/ SSE endpoint."""

    def setUp(self) -> None:
        self.client = APIClient()

    @patch("apps.jobs.views._get_redis")
    def test_stream_returns_sse_content_type(self, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.COMPLETED.value,
            result_llms_txt="# Test\n",
            result_meta={"total_pages": 1, "pages_processed": 1},
        )

        response = self.client.get(f"/api/jobs/{job.id}/stream/")
        assert response["Content-Type"] == "text/event-stream"

    @patch("apps.jobs.views._get_redis")
    def test_stream_sends_initial_cached_progress(self, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.COMPLETED.value,
            result_llms_txt="# Test\n",
            result_meta={"total_pages": 1, "pages_processed": 1},
        )

        progress = {"phase": "extracting", "message": "Working..."}
        fake.set(f"job:{job.id}:progress", json.dumps(progress).encode())

        response = self.client.get(f"/api/jobs/{job.id}/stream/")
        content = b"".join(response.streaming_content).decode()
        assert "event: progress" in content
        assert "Working..." in content

    @patch("apps.jobs.views._get_redis")
    def test_stream_completed_job_sends_complete_event(self, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.COMPLETED.value,
            result_llms_txt="# Test\n",
            result_meta={
                "total_pages": 1,
                "pages_processed": 1,
                "pages_failed": 0,
                "generation_time_seconds": 1.0,
            },
        )

        response = self.client.get(f"/api/jobs/{job.id}/stream/")
        content = b"".join(response.streaming_content).decode()
        assert "event: complete" in content
        assert "# Test" in content

    def test_stream_nonexistent_job_returns_error(self) -> None:
        response = self.client.get("/api/jobs/00000000-0000-0000-0000-000000000000/stream/")
        assert response.status_code == 404
        content = b"".join(response.streaming_content).decode()
        assert "Job not found" in content

    @patch("apps.jobs.views._get_redis")
    def test_stream_has_no_cache_header(self, mock_redis: object) -> None:
        import fakeredis

        fake = fakeredis.FakeRedis()
        mock_redis.return_value = fake

        from apps.jobs.models import Job

        job = Job.objects.create(
            url="https://example.com",
            mode=JobMode.DEFAULT.value,
            status=JobStatus.COMPLETED.value,
            result_llms_txt="# Test\n",
            result_meta={"total_pages": 1, "pages_processed": 1},
        )

        response = self.client.get(f"/api/jobs/{job.id}/stream/")
        assert response.get("Cache-Control") == "no-cache"
