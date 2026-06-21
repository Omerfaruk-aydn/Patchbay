from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import ToolCall

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages async MCP tool call lifecycle.

    States: pending → running → completed | failed
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_task(
        self, request_id: str, mcp_tool_id: str, input_payload: dict
    ) -> str:
        """Create a new tool call task in pending state."""
        task_id = str(uuid.uuid4())
        task = ToolCall(
            request_id=request_id,
            mcp_tool_id=mcp_tool_id,
            status="pending",
            input_payload=input_payload,
        )
        self._db.add(task)
        await self._db.flush()
        return str(task.id)

    async def mark_running(self, task_id: str) -> None:
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "running"

    async def mark_completed(self, task_id: str, output_payload: dict) -> None:
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "completed"
            task.output_payload = output_payload
            task.completed_at = datetime.now(timezone.utc)

    async def mark_failed(self, task_id: str, error_message: str) -> None:
        result = await self._db.execute(
            self._db.select(ToolCall).where(ToolCall.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "failed"
            task.error_message = error_message
            task.completed_at = datetime.now(timezone.utc)
