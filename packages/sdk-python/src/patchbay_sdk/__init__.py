"""Patchbay Python SDK — thin client for the Gateway API."""

from __future__ import annotations

from typing import Any

import httpx


class GatewayClient:
    """Client for the Patchbay Gateway API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60.0,
        )

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        max_tokens: int | None = None,
        temperature: float | None = None,
        routing_policy: str | None = None,
        mcp_servers: list[str] | None = None,
        stream: bool = False,
    ) -> dict:
        """Send a chat completion request."""
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        response = await self._client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    async def list_models(self) -> dict:
        """List available models."""
        response = await self._client.get("/v1/models")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self._client.aclose()
