"""Supabase JWT authentication middleware for Django.

Uses the JWKS endpoint to verify asymmetric JWTs issued by Supabase Auth.
Supports ES256, RS256, EdDSA, and HS256 algorithms.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import jwt
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from jwt import PyJWKClient

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Algorithms accepted from the Supabase JWKS endpoint.
_SUPPORTED_ALGORITHMS = ["ES256", "RS256", "EdDSA", "HS256"]

# PyJWKClient caches keys in memory for this many seconds.
_JWKS_CACHE_LIFESPAN = 600  # 10 minutes


class SupabaseJWTAuthMiddleware:
    """Validates Supabase JWT tokens and attaches user_id to the request.

    Token verification uses the JWKS discovery endpoint at
    ``{SUPABASE_URL}/auth/v1/.well-known/jwks.json``, which publishes the
    public keys used by Supabase Auth to sign access tokens.

    Anonymous requests (no token) pass through with request.user_id = None.
    Invalid or expired tokens return 401.
    """

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

        supabase_url = (settings.SUPABASE_URL or "").rstrip("/")
        if supabase_url:
            jwks_url = f"{supabase_url}/auth/v1/.well-known/jwks.json"
            self._jwks_client: PyJWKClient | None = PyJWKClient(
                jwks_url,
                cache_keys=True,
                lifespan=_JWKS_CACHE_LIFESPAN,
            )
        else:
            self._jwks_client = None

    def __call__(self, request: HttpRequest):
        request.user_id = None  # type: ignore[attr-defined]
        request.is_authenticated_user = False  # type: ignore[attr-defined]

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return self.get_response(request)

        token = auth_header[7:]
        if self._jwks_client is None:
            logger.warning("SUPABASE_URL is not configured; skipping JWT auth")
            return self.get_response(request)

        try:
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=_SUPPORTED_ALGORITHMS,
                audience="authenticated",
            )
            request.user_id = payload.get("sub")  # type: ignore[attr-defined]
            request.is_authenticated_user = True  # type: ignore[attr-defined]
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError as exc:
            logger.debug("Invalid JWT: %s", exc)
            return JsonResponse({"error": "Invalid token"}, status=401)

        return self.get_response(request)
