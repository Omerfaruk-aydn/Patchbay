from __future__ import annotations

import pytest
import asyncio
from typing import Any
from dataclasses import dataclass, field


@dataclass
class FakeRoute:
    id: str = "route-1"
    provider_key: str = "openai"
    provider_model_id: str = "gpt-4"
    is_healthy: bool = True
    is_active: bool = True
    priority: int = 100
    avg_latency_ms: int | None = None
    pricing_input_per_million_cents: float = 50.0
    pricing_output_per_million_cents: float = 150.0
    auth_credential_ref: str = "test-key"
    region: str | None = None


@dataclass
class FakeRedis:
    _data: dict[str, Any] = field(default_factory=dict)

    async def hget(self, key: str, field: str) -> str | None:
        return self._data.get(key, {}).get(field)

    async def hset(self, key: str, field: str, value: str) -> None:
        if key not in self._data:
            self._data[key] = {}
        self._data[key][field] = value

    async def incr(self, key: str) -> int:
        return 1
