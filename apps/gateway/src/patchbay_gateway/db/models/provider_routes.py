"""Provider route model — maps logical models to physical provider endpoints.

A single logical model (e.g., "claude-opus-4-7") can have multiple
routes (direct Anthropic, Bedrock, Vertex AI) with different:
  - Pricing
  - Latency profiles
  - Rate limits
  - Geographic regions

The routing engine selects the optimal route based on the project's
routing policy and real-time conditions.
"""

from __future__ import annotations

import sqlalchemy as sa

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class ProviderRoute(Base):
    """Physical route to a provider for a specific model."""

    __tablename__ = "provider_routes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("models.id", ondelete="CASCADE"), nullable=False
    )
    provider_key: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_credential_ref: Mapped[str] = mapped_column(Text, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pricing_input_per_million_cents: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False
    )
    pricing_output_per_million_cents: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=100)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=sa.func.now()
    )
