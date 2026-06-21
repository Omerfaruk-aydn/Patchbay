from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from patchbay_gateway.db.base import Base


class SemanticCacheEntry(Base):
    __tablename__ = "semantic_cache_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    prompt_embedding: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    response_payload: Mapped[dict] = mapped_column(nullable=False)
    similarity_threshold: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), default=Decimal("0.95")
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
