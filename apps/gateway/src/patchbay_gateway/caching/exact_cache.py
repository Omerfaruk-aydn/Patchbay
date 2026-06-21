"""Exact-match cache using Redis with SHA-256 request hashing.

Provides instant, zero-cost responses for identical requests.
Used for:
  - CI/CD test environments (same prompts repeated)
  - Deduplication of concurrent identical requests
  - Cost optimization for deterministic workloads

Cache key: sha256(normalized_request) → cached response
TTL: Configurable per project (default: 1 hour)
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from patchbay_gateway.providers.schemas import NormalizedResponse

logger = logging.getLogger(__name__)


class ExactCache:
    """Redis-based exact-match cache using SHA-256 request hashing."""

    def __init__(self, redis: Any, ttl_seconds: int = 3600) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _make_key(self, project_id: str, request: dict[str, Any]) -> str:
        """Generate cache key from project ID and request content."""
        request_str = json.dumps(request, sort_keys=True, default=str)
        request_hash = hashlib.sha256(request_str.encode("utf-8")).hexdigest()
        return f"cache:exact:{project_id}:{request_hash}"

    async def lookup(
        self, project_id: str, request: dict[str, Any]
    ) -> NormalizedResponse | None:
        """Look up a cached response for the exact request.

        Returns:
            NormalizedResponse if cache hit, None if miss.
        """
        key = self._make_key(project_id, request)
        try:
            cached = await self._redis.get(key)
            if cached:
                logger.debug("exact_cache_hit", extra={"project_id": project_id})
                return NormalizedResponse(**json.loads(cached))
        except Exception as e:
            logger.warning("exact_cache_lookup_failed", extra={"error": str(e)})
        return None

    async def store(
        self,
        project_id: str,
        request: dict[str, Any],
        response: NormalizedResponse,
    ) -> None:
        """Store a response in the cache."""
        key = self._make_key(project_id, request)
        try:
            data = response.model_dump_json()
            await self._redis.setex(key, self._ttl, data)
        except Exception as e:
            logger.warning("exact_cache_store_failed", extra={"error": str(e)})

    async def invalidate(self, project_id: str) -> int:
        """Invalidate all cached entries for a project."""
        pattern = f"cache:exact:{project_id}:*"
        keys = []
        async for key in self._redis.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            return await self._redis.delete(*keys)
        return 0
