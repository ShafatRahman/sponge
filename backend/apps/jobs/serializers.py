"""DRF serializers for the Jobs API."""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from apps.core.models import JobMode, JobStatus
from apps.core.ssrf_protection import SSRFGuard
from apps.jobs.models import Job


class CreateJobSerializer(serializers.Serializer):
    """Validates incoming job creation requests."""

    url = serializers.URLField(max_length=2048)
    mode = serializers.ChoiceField(
        choices=[(m.value, m.value) for m in JobMode],
        default=JobMode.DEFAULT.value,
    )
    max_urls = serializers.IntegerField(min_value=1, max_value=100, default=50, required=False)

    def validate_url(self, value: str) -> str:
        """Validate URL is safe (not SSRF)."""
        ssrf_guard = SSRFGuard()
        try:
            result = ssrf_guard.validate_url(value)
            return result.url
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class JobSerializer(serializers.ModelSerializer):
    """Serializes Job model for list and detail views."""

    class Meta:
        model = Job
        fields: ClassVar[list[str]] = [
            "id",
            "url",
            "mode",
            "status",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields: ClassVar[list[str]] = fields


class ProgressSerializer(serializers.Serializer):
    """Serializes progress events from Redis."""

    phase = serializers.CharField()
    message = serializers.CharField()
    urls_found = serializers.IntegerField(allow_null=True, default=None)
    completed = serializers.IntegerField(allow_null=True, default=None)
    total = serializers.IntegerField(allow_null=True, default=None)
    current_url = serializers.CharField(allow_null=True, default=None)


class JobResultSerializer(serializers.Serializer):
    """Serializes the final generation result."""

    llms_txt = serializers.CharField()
    llms_full_txt_url = serializers.CharField(allow_null=True, default=None)
    total_pages = serializers.IntegerField()
    pages_processed = serializers.IntegerField()
    pages_failed = serializers.IntegerField(default=0)
    generation_time_seconds = serializers.FloatField()
    llm_calls_made = serializers.IntegerField(default=0)
    llm_cost_usd = serializers.FloatField(default=0.0)


class JobStatusSerializer(serializers.Serializer):
    """Full job status response including progress and result."""

    id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[(s.value, s.value) for s in JobStatus])
    progress = ProgressSerializer(allow_null=True)
    result = JobResultSerializer(allow_null=True)
    error = serializers.CharField(allow_null=True)
