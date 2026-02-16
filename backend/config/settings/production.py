"""Production-specific Django settings."""

from __future__ import annotations

import os

from .base import *  # noqa: F403

DEBUG = False

# SSL termination is handled by the ALB -- do NOT redirect at the Django level
# or ALB health checks will fail with 301.
SECURE_SSL_REDIRECT = False
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": (
                '{"time":"%(asctime)s","name":"%(name)s",'
                '"level":"%(levelname)s","message":"%(message)s"}'
            ),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {"level": "WARNING"},
        "apps": {"level": "INFO"},
    },
}
