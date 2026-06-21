from __future__ import annotations

import hashlib
import json
from typing import Any

from patchbay_gateway.providers.schemas import NormalizedResponse


class ExactCache:
    """Redis-based exact-match cache using hash of normalized request."""

    def __init__(self, redis: Any, ttl_seconds: int = 3600) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    def _make_key(self, project_id: str, request: dict) -> str:
        request_str = json.dumps(request, sort_keys=True, default=str)
        request_hash = hashlib.sha256(request_str.encode()).hexdigest()
        return f"cache:exact:{project_id}:{request_hash}"

    async def lookup(self, project_id: str, request: dict) -> NormalizedResponse | None:
        key = self._make_key(project_id, request)
        cached = await self._redis.get(key)
        if cached:
            return NormalizedResponse(**json.loads(cached))
        return None

    async def store(self, project_id: str, request: dict, response: NormalizedResponse) -> None:
        key = self._make_key(project_id, request)
        data = response.model_dump_json()
        await self._redis.setex(key, self._ttl, data)
