"""Celery application configuration for Sponge."""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("sponge")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["apps.jobs"])

# Single queue for all tasks -- both Default and Detailed modes share the same
# pipeline and worker type.
app.conf.task_default_queue = "celery"

app.conf.task_time_limit = 300
app.conf.task_soft_time_limit = 240
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1
