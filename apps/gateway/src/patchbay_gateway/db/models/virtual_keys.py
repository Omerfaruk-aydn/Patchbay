"""Virtual key model — API authentication and budget tracking.

Keys follow the GitHub PAT pattern:
  - Raw key shown to user ONCE (pk_live_...)
  - Only bcrypt hash stored in database
  - Keys carry scopes, rate limits, and budget caps
"""

from __future__ import annotations

import sqlalchemy as sa

import uuid
from datetime import datetime, timezone

from sqlalchemy import ARRAY, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class VirtualKey(Base):
    """Virtual API key for authentication and budget tracking."""

    __tablename__ = "virtual_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    rate_limit_rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_usd_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
