"""Config - Configuration management for Patchbay CLI.

Handles:
  - Config file at ~/.patchbay/config.yaml
  - Environment variable overrides
  - Default values
  - Config validation
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path.home() / ".patchbay"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULTS = {
    "provider": "openai",
    "model": "gpt-4o",
    "gateway_url": "http://localhost:8000",
    "dashboard_url": "http://localhost:3000",
    "blender_host": "localhost",
    "blender_port": 9876,
    "mcp_host": "localhost",
    "mcp_port": 8456,
    "temperature": 0.7,
    "max_tokens": 4096,
    "theme": "tokyo-night",
    "auto_save": True,
    "auto_save_interval": 20,
    "max_tool_rounds": 15,
    "stream": True,
}


def ensure_config_dir() -> None:
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def get_config() -> dict[str, Any]:
    """Load configuration, merging defaults, file, and env vars."""
    ensure_config_dir()

    config = dict(DEFAULTS)

    # Load from file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}
            config.update(file_config)
        except Exception:
            pass

    # Environment variable overrides
    env_map = {
        "PATCHBAY_PROVIDER": "provider",
        "PATCHBAY_MODEL": "model",
        "PATCHBAY_GATEWAY_URL": "gateway_url",
        "PATCHBAY_DASHBOARD_URL": "dashboard_url",
        "PATCHBAY_BLENDER_HOST": "blender_host",
        "PATCHBAY_BLENDER_PORT": "blender_port",
        "PATCHBAY_MCP_HOST": "mcp_host",
        "PATCHBAY_MCP_PORT": "mcp_port",
        "PATCHBAY_TEMPERATURE": "temperature",
        "PATCHBAY_MAX_TOKENS": "max_tokens",
    }

    for env_key, cfg_key in env_map.items():
        val = os.getenv(env_key)
        if val is not None:
            try:
                if cfg_key in ("blender_port", "mcp_port", "max_tokens"):
                    config[cfg_key] = int(val)
                elif cfg_key == "temperature":
                    config[cfg_key] = float(val)
                else:
                    config[cfg_key] = val
            except (ValueError, TypeError):
                pass

    return config


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def set_config_value(key: str, value: Any) -> None:
    """Set a single config value."""
    config = get_config()

    # Type coercion
    if key in ("blender_port", "mcp_port", "max_tokens", "max_tool_rounds", "auto_save_interval"):
        try:
            value = int(value)
        except (ValueError, TypeError):
            pass
    elif key == "temperature":
        try:
            value = float(value)
        except (ValueError, TypeError):
            pass
    elif key in ("auto_save", "stream"):
        value = str(value).lower() in ("true", "1", "yes", "on")

    config[key] = value
    save_config(config)


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a single config value."""
    return get_config().get(key, default)


def reset_config() -> None:
    """Reset config to defaults."""
    save_config(dict(DEFAULTS))


# ═══════════════════════════════════════════════════════════════
# API KEY MANAGEMENT
# ═══════════════════════════════════════════════════════════════

PROVIDER_KEY_MAP = {
    "openai": ("openai_api_key", "OPENAI_API_KEY"),
    "anthropic": ("anthropic_api_key", "ANTHROPIC_API_KEY"),
    "deepseek": ("deepseek_api_key", "DEEPSEEK_API_KEY"),
    "openrouter": ("openrouter_api_key", "OPENROUTER_API_KEY"),
    "google": ("google_api_key", "GOOGLE_API_KEY"),
    "azure": ("azure_api_key", "AZURE_API_KEY"),
    "patchbay": ("patchbay_api_key", "PATCHBAY_API_KEY"),
}

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "google": "https://generativelanguage.googleapis.com/v1beta",
    "azure": "https://api.openai.azure.com",
}


def get_api_key(provider: str) -> str:
    """Get API key for a provider from config or environment."""
    config = get_config()
    cfg_key, env_key = PROVIDER_KEY_MAP.get(
        provider, (f"{provider}_api_key", f"{provider.upper()}_API_KEY")
    )

    key = config.get(cfg_key) or os.getenv(env_key, "")
    if not key:
        raise ValueError(
            f"No API key for '{provider}'.\n"
            f"  Option 1: Set env var  {env_key}=sk-xxx\n"
            f"  Option 2: Run  patchbay config set {cfg_key} sk-xxx"
        )
    return key


def get_provider_url(provider: str) -> str:
    """Get API base URL for a provider."""
    config = get_config()
    if provider == "patchbay":
        return config.get("gateway_url", "http://localhost:8000") + "/v1"
    return PROVIDER_URLS.get(provider, config.get(f"{provider}_url", ""))


def validate_provider(provider: str) -> bool:
    """Check if a provider has an API key configured."""
    try:
        get_api_key(provider)
        return True
    except ValueError:
        return False
