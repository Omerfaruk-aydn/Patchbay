"""MCP task manager — tracks async tool call lifecycle.

Tool calls go through a state machine:
  pending → running → completed | failed

This enables:
  - Querying active tool calls ("show me all running tools")
  - Timeout detection for hung tool calls
  - Audit trail of tool executions
  - Cost attribution per tool call
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import ToolCall

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages async MCP tool call lifecycle."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_task(
        self,
        request_id: str,
        mcp_tool_id: str,
        input_payload: dict[str, Any],
    ) -> str:
        """Create a new tool call task in pending state."""
        task = ToolCall(
            request_id=request_id,
            mcp_tool_id=mcp_tool_id,
            status="pending",
            input_payload=input_payload,
        )
        self._db.add(task)
        await self._db.flush()
        logger.debug("task_created", extra={"task_id": str(task.id), "tool_id": mcp_tool_id})
        return str(task.id)

    async def mark_running(self, task_id: str) -> None:
        """Transition task from pending to running."""
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "running"
            logger.debug("task_running", extra={"task_id": task_id})

    async def mark_completed(
        self,
        task_id: str,
        output_payload: dict[str, Any],
    ) -> None:
        """Transition task to completed state."""
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "completed"
            task.output_payload = output_payload
            task.completed_at = datetime.now(timezone.utc)
            logger.info("task_completed", extra={"task_id": task_id})

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        """Transition task to failed state."""
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "failed"
            task.error_message = error_message
            task.completed_at = datetime.now(timezone.utc)
            logger.warning("task_failed", extra={"task_id": task_id, "error": error_message})

    async def get_active_tasks(self) -> list[dict[str, Any]]:
        """Get all pending and running tasks."""
        result = await self._db.execute(
            self._db.select(ToolCall).where(
                ToolCall.status.in_(["pending", "running"])
            )
        )
        return [
            {
                "id": str(t.id),
                "request_id": str(t.request_id),
                "status": t.status,
                "started_at": t.started_at.isoformat(),
            }
            for t in result.scalars().all()
        ]
