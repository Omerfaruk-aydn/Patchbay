"""LLM model catalog — canonical model definitions.

Separates the logical model (e.g., "claude-opus-4-7") from the
provider-specific model ID (e.g., "claude-opus-4-20250514"). This
enables the same logical model to be available through multiple
provider routes (direct, Bedrock, Vertex).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class LLMModel(Base):
    """Canonical LLM model definition."""

    __tablename__ = "models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    family: Mapped[str] = mapped_column(String(100), nullable=False)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
