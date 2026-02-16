from __future__ import annotations

from django.http import JsonResponse
from django.urls import include, path


def health_check(_request):
    """Health check endpoint for ALB target group."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/health/", health_check, name="health-check"),
    path("api/", include("apps.jobs.urls")),
]
