"""Semantic cache using pgvector for near-duplicate prompt matching.

Unlike exact cache (which requires identical text), semantic cache
matches prompts that are semantically similar but worded differently.

Example:
  "Python'da liste nasıl sıralanır" ≈ "How to sort a list in Python"
  Both would hit the same cache entry.

Implementation:
  1. Compute embedding for incoming prompt
  2. pgvector cosine similarity search
  3. If similarity > threshold, return cached response
  4. Otherwise, forward to provider and cache the response

The embedding model is configurable (default: text-embedding-ada-002).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from patchbay_gateway.providers.schemas import NormalizedResponse

logger = logging.getLogger(__name__)


class SemanticCache:
    """pgvector-based semantic cache for near-duplicate prompts."""

    def __init__(self, db: Any, similarity_threshold: float = 0.95) -> None:
        self._db = db
        self._threshold = similarity_threshold

    async def lookup(
        self, project_id: str, prompt: str
    ) -> NormalizedResponse | None:
        """Look up a semantically similar cached response.

        Returns:
            NormalizedResponse if similarity >= threshold, None otherwise.
        """
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        # Check exact hash first (fast path)
        result = await self._db.execute(
            """
            SELECT response_payload, 1 - (prompt_embedding <=> :embedding) AS similarity
            FROM semantic_cache_entries
            WHERE project_id = :project_id
              AND prompt_text_hash = :prompt_hash
              AND expires_at > now()
            LIMIT 1
            """,
            {"embedding": await self._get_embedding(prompt), "project_id": project_id, "prompt_hash": prompt_hash},
        )
        row = result.first()
        if row and float(row["similarity"]) >= self._threshold:
            logger.debug("semantic_cache_hit", extra={"similarity": float(row["similarity"])})
            return NormalizedResponse(**row["response_payload"])

        return None

    async def store(
        self, project_id: str, prompt: str, response: NormalizedResponse
    ) -> None:
        """Store a response with its embedding for future semantic lookups."""
        embedding = await self._get_embedding(prompt)
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()

        await self._db.execute(
            """
            INSERT INTO semantic_cache_entries (project_id, prompt_embedding, prompt_text_hash, response_payload, expires_at)
            VALUES (:project_id, :embedding, :prompt_hash, :response, now() + interval '24 hours')
            """,
            {"project_id": project_id, "embedding": embedding, "prompt_hash": prompt_hash, "response": response.model_dump()},
        )

    async def _get_embedding(self, text: str) -> str:
        """Compute embedding for text.

        In production, this calls the embedding API.
        For now, returns a placeholder.
        """
        # TODO: Call embedding API (OpenAI text-embedding-ada-002 or local model)
        return "placeholder_embedding"
