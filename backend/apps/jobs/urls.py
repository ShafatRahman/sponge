"""URL routing for the Jobs API."""

from __future__ import annotations

from django.urls import path

from apps.jobs.views import JobCreateView, JobDetailView, JobListView, JobStreamView

urlpatterns = [
    path("jobs/", JobCreateView.as_view(), name="job-create"),
    path("jobs/history/", JobListView.as_view(), name="job-list"),
    path("jobs/<str:job_id>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<str:job_id>/stream/", JobStreamView.as_view(), name="job-stream"),
    path("jobs/<str:job_id>/stream", JobStreamView.as_view(), name="job-stream-no-slash"),
]
