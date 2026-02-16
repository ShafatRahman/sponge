"""Custom DRF exception handler that returns clean JSON for all errors.

Ensures no stack traces, internal details, or raw Python exceptions ever
reach the client. Known DRF/Django errors get their natural status codes;
everything else becomes a generic 500 with a safe message.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

# User-facing messages keyed by HTTP status code.
FRIENDLY_MESSAGES: dict[int, str] = {
    400: "The request was invalid. Please check your input and try again.",
    401: "Authentication required. Please sign in and try again.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    405: "This action is not supported.",
    429: "Too many requests. Please wait a moment and try again.",
    500: "Something went wrong on our end. Please try again later.",
    502: "The server is temporarily unavailable. Please try again later.",
    503: "The service is temporarily unavailable. Please try again later.",
}


def custom_exception_handler(exc: Exception, context: dict) -> Response:
    """Handle all exceptions and return clean, consistent JSON.

    Flow:
    1. Let DRF handle known exceptions (validation, auth, 404, throttle, etc.)
       and return their structured response.
    2. For anything DRF doesn't handle (unhandled Python exceptions),
       log the full traceback and return a generic 500.
    3. Normalize every response to ``{"error": "<message>"}`` format.
    """
    # Let DRF handle its own exception types first.
    response = drf_exception_handler(exc, context)

    if response is not None:
        # DRF handled it -- normalize the body to {"error": "<message>"}.
        error_message = _extract_drf_message(response)
        response.data = {"error": error_message}
        return response

    # Unhandled exception -- log it fully, return a safe 500.
    logger.exception(
        "Unhandled exception in %s",
        context.get("view", "unknown view"),
    )

    return Response(
        {"error": FRIENDLY_MESSAGES[500]},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _extract_drf_message(response: Response) -> str:
    """Pull a single human-readable string from a DRF error response."""
    data = response.data

    # DRF validation errors come as {"field": ["error", ...]} or as a list.
    if isinstance(data, dict):
        # Direct error/detail key (our own views, DRF exceptions).
        for key in ("error", "detail", "message"):
            if key in data:
                val = data[key]
                return str(val) if not isinstance(val, list) else str(val[0])

        # Field-level validation errors: pick the first one.
        for _field, errors in data.items():
            if isinstance(errors, list) and errors:
                return str(errors[0])
            return str(errors)

    if isinstance(data, list) and data:
        return str(data[0])

    # Fallback to a friendly message by status code.
    return FRIENDLY_MESSAGES.get(
        response.status_code,
        FRIENDLY_MESSAGES[500],
    )
