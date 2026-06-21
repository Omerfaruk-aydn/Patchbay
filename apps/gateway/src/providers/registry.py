from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from patchbay_gateway.core.exceptions import UnknownProviderError
from patchbay_gateway.providers.base import ProviderAdapter


class ProviderRegistry:
    """Auto-discovery registry for provider adapters.

    All adapters are discovered at startup by scanning the providers package.
    Adding a new provider requires only creating a new file — no existing
    code changes needed.
    """

    _adapters: dict[str, type[ProviderAdapter]] = {}
    _instances: dict[str, ProviderAdapter] = {}

    @classmethod
    def register(cls, adapter_cls: type[ProviderAdapter]) -> type[ProviderAdapter]:
        cls._adapters[adapter_cls.provider_key] = adapter_cls
        return adapter_cls

    @classmethod
    def get_adapter(cls, provider_key: str) -> ProviderAdapter:
        if provider_key not in cls._instances:
            if provider_key not in cls._adapters:
                raise UnknownProviderError(provider_key)
            cls._instances[provider_key] = cls._adapters[provider_key]()
        return cls._instances[provider_key]

    @classmethod
    def list_providers(cls) -> list[str]:
        return list(cls._adapters.keys())

    @classmethod
    def discover(cls) -> None:
        """Import all modules in the providers package to trigger registration."""
        package = importlib.import_module("patchbay_gateway.providers")
        for _, name, _ in pkgutil.iter_modules(package.__path__):
            if name not in ("base", "registry", "schemas", "__init__"):
                importlib.import_module(f"patchbay_gateway.providers.{name}")
