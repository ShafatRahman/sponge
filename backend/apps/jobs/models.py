"""Django ORM models for the jobs app."""

from __future__ import annotations

import uuid
from typing import ClassVar

from django.db import models

from apps.core.models import JobMode, JobStatus


class Job(models.Model):
    """Represents a single llms.txt generation job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(null=True, blank=True, db_index=True)
    url = models.URLField(max_length=2048)
    mode = models.CharField(
        max_length=10,
        choices=[(m.value, m.value) for m in JobMode],
        default=JobMode.DEFAULT.value,
    )
    status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in JobStatus],
        default=JobStatus.PENDING.value,
    )
    config = models.JSONField(default=dict)
    result_llms_txt = models.TextField(blank=True)
    result_meta = models.JSONField(null=True, blank=True)
    llms_full_txt_key = models.CharField(max_length=512, blank=True)
    error_message = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering: ClassVar[list[str]] = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["user_id", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["url", "mode", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Job({self.id!s:.8}) {self.url} [{self.status}]"
