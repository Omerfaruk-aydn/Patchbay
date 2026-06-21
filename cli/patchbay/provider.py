"""LLM Provider abstraction - handles API keys, URLs, streaming."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

CONFIG_DIR = Path.home() / ".patchbay"
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


PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
}

PROVIDER_KEY_NAMES = {
    "openai": ("openai_api_key", "OPENAI_API_KEY"),
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
    "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY"),
    "google": ("google_api_key", "GOOGLE_API_KEY"),
}


def get_api_key(provider: str) -> str:
    config = get_config()
    cfg_key, env_key = PROVIDER_KEY_NAMES.get(provider, (f"{provider}_api_key", f"{provider.upper()}_API_KEY"))
    key = config.get(cfg_key) or os.getenv(env_key, "")
    if not key:
        raise ValueError(
            f"No API key for {provider}.\n"
            f"  Set env: {env_key}=sk-xxx\n"
            f"  Or config: patchbay config set {cfg_key} sk-xxx"
        )
    return key


def get_provider_url(provider: str) -> str:
    config = get_config()
    if provider == "patchbay":
        return config.get("gateway_url", "http://localhost:8000") + "/v1"
    return PROVIDER_URLS.get(provider, config.get(f"{provider}_url", ""))


def stream_completion(provider: str, model: str, messages: list[dict],
                      tools: list[dict] | None = None, temperature: float = 0.7,
                      max_tokens: int = 4096):
    """Stream chat completion. Yields chunks."""
    if provider == "anthropic":
        yield from _stream_anthropic(model, messages, tools, temperature, max_tokens)
    else:
        yield from _stream_openai(provider, model, messages, tools, temperature, max_tokens)


def _stream_openai(provider, model, messages, tools, temperature, max_tokens):
    api_key = get_api_key(provider)
    base_url = get_provider_url(provider)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body: dict[str, Any] = {
        "model": model, "messages": messages,
        "temperature": temperature, "max_tokens": max_tokens,
        "stream": True, "stream_options": {"include_usage": True},
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    with httpx.Client(timeout=120) as client:
        with client.stream("POST", f"{base_url}/chat/completions", json=body, headers=headers) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue


def _stream_anthropic(model, messages, tools, temperature, max_tokens):
    api_key = get_api_key("anthropic")
    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

    system_msg = ""
    filtered = []
    for m in messages:
        if m["role"] == "system":
            system_msg = m["content"]
        else:
            filtered.append(m)

    body: dict[str, Any] = {
        "model": model, "messages": filtered,
        "max_tokens": max_tokens, "temperature": temperature, "stream": True,
    }
    if system_msg:
        body["system"] = system_msg
    if tools:
        body["tools"] = [{"name": t["function"]["name"], "description": t["function"]["description"],
                          "input_schema": t["function"]["parameters"]} for t in tools]

    with httpx.Client(timeout=120) as client:
        with client.stream("POST", "https://api.anthropic.com/v1/messages", json=body, headers=headers) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line.startswith("data: "):
                    try:
                        yield json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
