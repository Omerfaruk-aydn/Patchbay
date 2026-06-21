from __future__ import annotations

import sqlalchemy as sa

from typing import Any

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class MCPTool(Base):
    __tablename__ = "mcp_tools"
    __table_args__ = (UniqueConstraint("mcp_server_id", "tool_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    mcp_server_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now()
    )
