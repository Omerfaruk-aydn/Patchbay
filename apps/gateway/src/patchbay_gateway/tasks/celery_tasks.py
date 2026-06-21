"""Celery background tasks for Patchbay Gateway."""

from __future__ import annotations

from patchbay_gateway.tasks import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_mcp_tools(self, project_id: str) -> dict:
    """Periodic task to sync MCP server tool lists."""
    return {"status": "completed", "project_id": project_id}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_pricing(self) -> dict:
    """Periodic task to sync provider pricing from official pages."""
    return {"status": "completed"}
