from __future__ import annotations

from typing import Any

from patchbay_gateway.providers.schemas import NormalizedResponse


class SemanticCache:
    """pgvector-based semantic cache for near-duplicate prompts."""

    def __init__(self, db: Any, similarity_threshold: float = 0.95) -> None:
        self._db = db
        self._threshold = similarity_threshold

    async def lookup(self, project_id: str, prompt: str) -> NormalizedResponse | None:
        # In production, this computes embedding and does pgvector cosine search
        # Placeholder for Phase 4 implementation
        return None

    async def store(self, project_id: str, prompt: str, response: NormalizedResponse) -> None:
        # In production, this computes embedding and inserts into semantic_cache_entries
        pass
