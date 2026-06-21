"""Celery worker configuration for background tasks.

Handles:
  - MCP tool list synchronization (periodic)
  - Provider pricing sync (periodic)
  - Budget alert checks (periodic)
  - Long-running tool call execution
"""

from __future__ import annotations

from celery import Celery
from patchbay_gateway.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "patchbay",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_soft_time_limit=300,
    task_time_limit=600,
)

celery_app.autodiscover_tasks(["patchbay_gateway.tasks"])
