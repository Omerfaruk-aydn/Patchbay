"""Provider adapter registry with auto-discovery.

All adapters are automatically discovered at startup by scanning
the providers package. Adding a new provider requires only creating
a new file with the @ProviderRegistry.register decorator — no existing
code changes needed.

Usage:
  # At startup (in main.py or startup hook):
  ProviderRegistry.discover()

  # Later:
  adapter = ProviderRegistry.get_adapter("openai")
  response = await adapter.send(route, request)
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any

from patchbay_gateway.core.exceptions import UnknownProviderError
from patchbay_gateway.providers.base import ProviderAdapter

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """Singleton registry for provider adapters with auto-discovery."""

    _adapters: dict[str, type[ProviderAdapter]] = {}
    _instances: dict[str, ProviderAdapter] = {}
    _discovered: bool = False

    @classmethod
    def register(cls, adapter_cls: type[ProviderAdapter]) -> type[ProviderAdapter]:
        """Decorator to register a provider adapter.

        Usage:
            @ProviderRegistry.register
            class MyAdapter(ProviderAdapter):
                provider_key = "my_provider"
                ...
        """
        cls._adapters[adapter_cls.provider_key] = adapter_cls
        logger.debug("provider_registered", extra={"provider": adapter_cls.provider_key})
        return adapter_cls

    @classmethod
    def get_adapter(cls, provider_key: str) -> ProviderAdapter:
        """Get a provider adapter instance by key.

        Instances are cached (singleton per provider key).

        Raises:
            UnknownProviderError: If the provider key is not registered.
        """
        if not cls._discovered:
            cls.discover()

        if provider_key not in cls._instances:
            if provider_key not in cls._adapters:
                raise UnknownProviderError(provider_key)
            cls._instances[provider_key] = cls._adapters[provider_key]()

        return cls._instances[provider_key]

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider keys."""
        if not cls._discovered:
            cls.discover()
        return sorted(cls._adapters.keys())

    @classmethod
    def has_provider(cls, provider_key: str) -> bool:
        """Check if a provider is registered."""
        if not cls._discovered:
            cls.discover()
        return provider_key in cls._adapters

    @classmethod
    def discover(cls) -> None:
        """Auto-discover all provider adapters by importing the providers package.

        This scans all Python modules in the providers directory and imports them,
        which triggers the @ProviderRegistry.register decorator on each adapter class.
        """
        if cls._discovered:
            return

        package = importlib.import_module("patchbay_gateway.providers")
        discovered_count = 0

        for _, name, _ in pkgutil.iter_modules(package.__path__):
            if name in ("base", "registry", "schemas", "__init__"):
                continue
            try:
                importlib.import_module(f"patchbay_gateway.providers.{name}")
                discovered_count += 1
            except Exception as e:
                logger.error(
                    "provider_discovery_failed",
                    extra={"module": name, "error": str(e)},
                )

        cls._discovered = True
        logger.info(
            "providers_discovered",
            extra={"count": discovered_count, "providers": list(cls._adapters.keys())},
        )
