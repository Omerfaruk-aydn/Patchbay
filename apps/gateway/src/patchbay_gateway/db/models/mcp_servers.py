from __future__ import annotations

import sqlalchemy as sa

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    transport: Mapped[str] = mapped_column(String(50), nullable=False)
    connection_uri: Mapped[str] = mapped_column(Text, nullable=False)
    auth_credential_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_via: Mapped[str] = mapped_column(String(50), default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now()
    )
