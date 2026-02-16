"""Supabase service wrapper for database and storage operations."""

from __future__ import annotations

import logging

from django.conf import settings
from supabase import Client, create_client

logger = logging.getLogger(__name__)

STORAGE_BUCKET = "sponge-results"


class SupabaseService:
    """Wraps supabase-py for DB queries and object storage.

    Uses the service role key for full access (server-side only).
    """

    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SECRET_KEY,
            )
        return self._client

    def upload_file(self, path: str, content: bytes, content_type: str = "text/markdown") -> str:
        """Upload a file to Supabase Storage. Returns the storage path."""
        self.client.storage.from_(STORAGE_BUCKET).upload(
            path,
            content,
            {"content-type": content_type},
        )
        logger.info("Uploaded file to storage: %s", path)
        return path

    def get_public_url(self, path: str) -> str:
        """Get a public URL for a storage object."""
        result = self.client.storage.from_(STORAGE_BUCKET).get_public_url(path)
        return result

    def download_file(self, path: str) -> bytes:
        """Download a file from Supabase Storage."""
        return self.client.storage.from_(STORAGE_BUCKET).download(path)
