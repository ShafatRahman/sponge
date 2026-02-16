"""Sponge Django project configuration.

Import Celery app so it's loaded when Django starts,
enabling autodiscovery of task modules.
"""

from .celery import app as celery_app

__all__ = ["celery_app"]
