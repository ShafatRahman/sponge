from __future__ import annotations

from django.apps import AppConfig


class JobsConfig(AppConfig):
    """Django app configuration for the jobs module."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jobs"
