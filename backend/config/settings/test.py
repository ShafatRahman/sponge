"""Test-specific Django settings.

Uses an in-memory SQLite database so tests can run without PostgreSQL.
"""

from __future__ import annotations

from .development import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
