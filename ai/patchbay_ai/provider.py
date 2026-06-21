"""Provider - LLM API provider abstraction."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

CONFIG_DIR = Path.home() / ".patchbay-ai"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def get_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        import yaml
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    import yaml
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def get_api_key(provider: str) -> str:
    """Get API key from config or environment."""
    config = get_config()

    key_map = {
        "openai": ("openai_api_key", "OPENAI_API_KEY"),
        "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
        "google": ("google_api_key", "GOOGLE_API_KEY"),
        "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
        "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY"),
        "patchbay": ("patchbay_api_key", "PATCHBAY_API_KEY"),
    }

    cfg_key, env_key = key_map.get(provider, (f"{provider}_api_key", f"{provider.upper()}_API_KEY"))

    key = config.get(cfg_key) or os.getenv(env_key, "")
    if not key:
        raise ValueError(
            f"No API key for {provider}. Set it with:\n"
            f"  patchbay-ai config set {cfg_key} <your-key>\n"
            f"  or set env var {env_key}"
        )
    return key


def get_provider_url(provider: str) -> str:
    """Get API base URL for a provider."""
    config = get_config()

    url_map = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "deepseek": "https://api.deepseek.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "patchbay": config.get("gateway_url", "http://localhost:8000") + "/v1",
    }

    return url_map.get(provider, config.get(f"{provider}_url", ""))


def chat_completion(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """Send a chat completion request. Yields chunks if streaming, returns dict if not."""

    if provider == "anthropic":
        return _anthropic_request(model, messages, tools, stream, temperature, max_tokens)
    else:
        return _openai_request(provider, model, messages, tools, stream, temperature, max_tokens)


def _openai_request(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """OpenAI-compatible API request."""
    api_key = get_api_key(provider)
    base_url = get_provider_url(provider)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    if stream:
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}

        with httpx.Client(timeout=120) as client:
            with client.stream("POST", f"{base_url}/chat/completions", json=body, headers=headers) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            yield chunk
                        except json.JSONDecodeError:
                            continue
    else:
        with httpx.Client(timeout=120) as client:
            r = client.post(f"{base_url}/chat/completions", json=body, headers=headers)
            r.raise_for_status()
            return r.json()


def _anthropic_request(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    stream: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 4096,
):
    """Anthropic API request."""
    api_key = get_api_key("anthropic")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
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

    if stream:
        body["stream"] = True

        with httpx.Client(timeout=120) as client:
            with client.stream("POST", "https://api.anthropic.com/v1/messages", json=body, headers=headers) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)
                            yield event
                        except json.JSONDecodeError:
                            continue
    else:
        with httpx.Client(timeout=120) as client:
            r = client.post("https://api.anthropic.com/v1/messages", json=body, headers=headers)
            r.raise_for_status()
            return r.json()
