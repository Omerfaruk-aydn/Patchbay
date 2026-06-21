"""Organization model — top-level entity for multi-tenant isolation.

Organizations own projects, which own virtual keys, which own request logs.
This hierarchy enables both single-user self-hosted deployments and
multi-customer SaaS deployments using the same data model.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class Organization(Base):
    """Top-level tenant entity."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
