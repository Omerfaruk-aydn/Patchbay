"""Provider - Multi-provider LLM API client with streaming.

Supports:
  - OpenAI (and compatible: DeepSeek, OpenRouter, Patchbay Gateway)
  - Anthropic (Claude)
  - Google (Gemini)

Handles:
  - Streaming responses (SSE)
  - Tool call accumulation across chunks
  - Usage tracking
  - Error handling with retries
"""

from __future__ import annotations

import json
from typing import Any, Iterator

import httpx

from patchbay.config import get_api_key, get_provider_url, get_config


# ═══════════════════════════════════════════════════════════════
# STREAMING COMPLETION
# ═══════════════════════════════════════════════════════════════

def stream_completion(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Iterator[dict]:
    """Stream a chat completion from the specified provider.

    Yields raw API chunks. Caller is responsible for parsing.

    Args:
        provider: Provider name (openai, anthropic, deepseek, etc.)
        model: Model identifier
        messages: Conversation messages
        tools: Optional tool definitions
        temperature: Sampling temperature
        max_tokens: Maximum response tokens

    Yields:
        Raw API response chunks
    """
    if provider == "anthropic":
        yield from _stream_anthropic(model, messages, tools, temperature, max_tokens)
    elif provider == "google":
        yield from _stream_google(model, messages, tools, temperature, max_tokens)
    else:
        yield from _stream_openai_compatible(provider, model, messages, tools, temperature, max_tokens)


# ═══════════════════════════════════════════════════════════════
# OPENAI-COMPATIBLE PROVIDERS
# ═══════════════════════════════════════════════════════════════

def _stream_openai_compatible(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Iterator[dict]:
    """Stream from OpenAI-compatible API (OpenAI, DeepSeek, OpenRouter, Patchbay)."""
    api_key = get_api_key(provider)
    base_url = get_provider_url(provider)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    # OpenRouter specific headers
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://patchbay.dev"
        headers["X-Title"] = "Patchbay CLI"

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    url = f"{base_url}/chat/completions"

    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=10)) as client:
            with client.stream("POST", url, json=body, headers=headers) as response:
                response.raise_for_status()

                buffer = ""
                for chunk in response.iter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue
                        if line == "data: [DONE]":
                            return
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                yield json.loads(data)
                            except json.JSONDecodeError:
                                continue

    except httpx.HTTPStatusError as e:
        error_body = ""
        try:
            error_body = e.response.text[:500]
        except Exception:
            pass
        yield {"error": f"HTTP {e.response.status_code}: {error_body}"}
    except httpx.ConnectError:
        yield {"error": f"Cannot connect to {base_url}. Check your network and API key."}
    except httpx.TimeoutException:
        yield {"error": "Request timed out. The model may be overloaded."}
    except Exception as e:
        yield {"error": f"Provider error: {e}"}


# ═══════════════════════════════════════════════════════════════
# ANTHROPIC (CLAUDE)
# ═══════════════════════════════════════════════════════════════

def _stream_anthropic(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Iterator[dict]:
    """Stream from Anthropic Messages API."""
    api_key = get_api_key("anthropic")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "accept": "text/event-stream",
    }

    # Extract system message
    system_msg = ""
    filtered_messages = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            filtered_messages.append(m)

    body: dict[str, Any] = {
        "model": model,
        "messages": filtered_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    if system_msg:
        body["system"] = system_msg

    if tools:
        body["tools"] = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"],
            }
            for t in tools
        ]

    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=10)) as client:
            with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                json=body,
                headers=headers,
            ) as response:
                response.raise_for_status()

                buffer = ""
                for chunk in response.iter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line or not line.startswith("data: "):
                            continue

                        data = line[6:]
                        try:
                            event = json.loads(data)
                            yield event
                        except json.JSONDecodeError:
                            continue

    except httpx.HTTPStatusError as e:
        error_body = ""
        try:
            error_body = e.response.text[:500]
        except Exception:
            pass
        yield {"error": f"Anthropic HTTP {e.response.status_code}: {error_body}"}
    except httpx.ConnectError:
        yield {"error": "Cannot connect to Anthropic API. Check your network and API key."}
    except httpx.TimeoutException:
        yield {"error": "Anthropic request timed out."}
    except Exception as e:
        yield {"error": f"Anthropic error: {e}"}


# ═══════════════════════════════════════════════════════════════
# GOOGLE (GEMINI)
# ═══════════════════════════════════════════════════════════════

def _stream_google(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> Iterator[dict]:
    """Stream from Google Generative AI API."""
    api_key = get_api_key("google")

    # Convert messages to Gemini format
    contents = []
    system_instruction = ""
    for m in messages:
        if m["role"] == "system":
            system_instruction = m["content"]
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            content = m.get("content", "")
            if content:
                contents.append({"role": "model", "parts": [{"text": content}]})

    body: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }

    if system_instruction:
        body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"

    try:
        with httpx.Client(timeout=httpx.Timeout(120, connect=10)) as client:
            with client.stream("POST", url, json=body) as response:
                response.raise_for_status()

                buffer = ""
                for chunk in response.iter_bytes():
                    buffer += chunk.decode("utf-8", errors="replace")

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line or not line.startswith("data: "):
                            continue

                        data = line[6:]
                        try:
                            event = json.loads(data)
                            # Convert to OpenAI-like format
                            candidates = event.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                text = "".join(p.get("text", "") for p in parts)
                                yield {
                                    "choices": [{
                                        "delta": {"content": text},
                                        "finish_reason": candidates[0].get("finishReason"),
                                    }]
                                }
                        except json.JSONDecodeError:
                            continue

    except httpx.HTTPStatusError as e:
        yield {"error": f"Google HTTP {e.response.status_code}: {e.response.text[:300]}"}
    except httpx.ConnectError:
        yield {"error": "Cannot connect to Google API."}
    except Exception as e:
        yield {"error": f"Google error: {e}"}


# ═══════════════════════════════════════════════════════════════
# RESPONSE PARSING
# ═══════════════════════════════════════════════════════════════

class StreamAccumulator:
    """Accumulates streaming chunks into a complete response.

    Handles both OpenAI and Anthropic streaming formats,
    accumulating content and tool calls across chunks.
    """

    def __init__(self):
        self.content = ""
        self.tool_calls: list[dict] = []
        self._tool_call_acc: dict[int, dict] = {}
        self.usage: dict = {}
        self.error: str | None = None

    def process_chunk(self, chunk: dict) -> str | None:
        """Process a single chunk. Returns content text if present."""

        # Check for errors
        if "error" in chunk:
            self.error = chunk["error"]
            return None

        # ─── OpenAI format ───
        if "choices" in chunk:
            choice = chunk["choices"][0]
            delta = choice.get("delta", {})

            # Content
            text = delta.get("content", "")
            if text:
                self.content += text

            # Tool calls
            if delta.get("tool_calls"):
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", 0)
                    if idx not in self._tool_call_acc:
                        self._tool_call_acc[idx] = {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    entry = self._tool_call_acc[idx]
                    if tc.get("id"):
                        entry["id"] = tc["id"]
                    func = tc.get("function", {})
                    if func.get("name"):
                        entry["function"]["name"] = func["name"]
                    if func.get("arguments"):
                        entry["function"]["arguments"] += func["arguments"]

            # Usage
            if chunk.get("usage"):
                self.usage = chunk["usage"]

            return text or None

        # ─── Anthropic format ───
        if "type" in chunk:
            event_type = chunk["type"]

            if event_type == "content_block_delta":
                delta = chunk.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    self.content += text
                    return text
                elif delta.get("type") == "input_json_delta":
                    if self._tool_call_acc:
                        last_idx = max(self._tool_call_acc.keys())
                        self._tool_call_acc[last_idx]["function"]["arguments"] += delta.get("partial_json", "")

            elif event_type == "content_block_start":
                block = chunk.get("content_block", {})
                if block.get("type") == "tool_use":
                    idx = len(self._tool_call_acc)
                    self._tool_call_acc[idx] = {
                        "id": block.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": block.get("name", ""),
                            "arguments": "",
                        },
                    }

            elif event_type == "message_delta":
                if chunk.get("usage"):
                    self.usage.update(chunk["usage"])

        return None

    def finalize(self) -> dict:
        """Build the final assistant message."""
        # Clean up tool calls
        self.tool_calls = []
        for idx in sorted(self._tool_call_acc.keys()):
            tc = self._tool_call_acc[idx]
            if tc["function"]["name"]:
                try:
                    args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                self.tool_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": json.dumps(args),
                    },
                })

        msg: dict[str, Any] = {
            "role": "assistant",
            "content": self.content if self.content else None,
        }
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls

        return msg


# ═══════════════════════════════════════════════════════════════
# MODEL LISTING
# ═══════════════════════════════════════════════════════════════

def fetch_models(provider: str) -> list[dict]:
    """Fetch available models from a provider's API.

    Returns list of dicts with 'id', 'name', 'provider' keys.
    """
    config = get_config()

    # Try config for API key first (check both cases)
    api_key = config.get(f"{provider}_api_key") or config.get(f"{provider.upper()}_API_KEY") or ""

    if not api_key:
        from patchbay.config import PROVIDER_KEY_MAP
        _, env_key = PROVIDER_KEY_MAP.get(provider, ("", ""))
        api_key = __import__("os").getenv(env_key, "")

    if not api_key:
        return []

    try:
        if provider == "anthropic":
            return _fetch_models_anthropic(api_key)
        elif provider == "openrouter":
            return _fetch_models_openrouter(api_key)
        elif provider == "google":
            return _fetch_models_google(api_key)
        else:
            return _fetch_models_openai(provider, api_key)
    except Exception:
        return []


def _fetch_models_openai(provider: str, api_key: str) -> list[dict]:
    """Fetch models from OpenAI-compatible /models endpoint."""
    base_url = get_provider_url(provider)
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=15) as client:
        r = client.get(f"{base_url}/models", headers=headers)
        r.raise_for_status()
        data = r.json()

    models = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        models.append({
            "id": model_id,
            "name": model_id,
            "owned_by": m.get("owned_by", provider),
        })
    return models


def _fetch_models_openrouter(api_key: str) -> list[dict]:
    """Fetch all models from OpenRouter API."""
    headers = {"Authorization": f"Bearer {api_key}"}

    with httpx.Client(timeout=15) as client:
        r = client.get("https://openrouter.ai/api/v1/models", headers=headers)
        r.raise_for_status()
        data = r.json()

    models = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        if not model_id:
            continue
        models.append({
            "id": model_id,
            "name": m.get("name", model_id),
            "owned_by": m.get("owned_by", ""),
            "context_length": m.get("context_length", 0),
            "pricing": m.get("pricing", {}),
        })
    return models


def _fetch_models_anthropic(api_key: str) -> list[dict]:
    """Fetch Anthropic models."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    # Anthropic doesn't have a /models endpoint, so we list known models
    known = [
        {"id": "claude-opus-4-20250514", "name": "Claude 4 Opus", "context": 200000},
        {"id": "claude-sonnet-4-20250514", "name": "Claude 4 Sonnet", "context": 200000},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "context": 200000},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "context": 200000},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "context": 200000},
    ]
    return [{"id": m["id"], "name": f"{m['name']} ({m['context']//1000}k)", "owned_by": "anthropic"} for m in known]


def _fetch_models_google(api_key: str) -> list[dict]:
    """Fetch Google Gemini models."""
    with httpx.Client(timeout=15) as client:
        r = client.get(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        )
        r.raise_for_status()
        data = r.json()

    models = []
    for m in data.get("models", []):
        name = m.get("name", "")
        if "generateContent" in m.get("supportedGenerationMethods", []):
            model_id = name.replace("models/", "")
            models.append({
                "id": model_id,
                "name": m.get("displayName", model_id),
                "owned_by": "google",
            })
    return models


def fetch_models_cached(provider: str, cache_ttl: int = 3600) -> list[dict]:
    """Fetch models with simple file-based caching.

    Args:
        provider: Provider name
        cache_ttl: Cache time-to-live in seconds (default 1 hour)

    Returns:
        List of model dicts
    """
    import time
    from pathlib import Path

    cache_dir = Path.home() / ".patchbay" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"models_{provider}.json"

    # Check cache
    if cache_file.exists():
        try:
            cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
            if time.time() - cache_data.get("timestamp", 0) < cache_ttl:
                return cache_data.get("models", [])
        except Exception:
            pass

    # Fetch fresh
    models = fetch_models(provider)

    # Save cache
    if models:
        try:
            cache_file.write_text(json.dumps({
                "timestamp": time.time(),
                "models": models,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return models
