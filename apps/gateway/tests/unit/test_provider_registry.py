from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from patchbay_gateway.providers.base import ProviderAdapter
from patchbay_gateway.providers.registry import ProviderRegistry


class TestProviderRegistry:
    def test_discover_loads_adapters(self) -> None:
        ProviderRegistry.discover()
        providers = ProviderRegistry.list_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    def test_get_adapter_returns_instance(self) -> None:
        ProviderRegistry.discover()
        adapter = ProviderRegistry.get_adapter("openai")
        assert isinstance(adapter, ProviderAdapter)
        assert adapter.provider_key == "openai"

    def test_get_adapter_caches_instance(self) -> None:
        ProviderRegistry.discover()
        a1 = ProviderRegistry.get_adapter("openai")
        a2 = ProviderRegistry.get_adapter("openai")
        assert a1 is a2

    def test_unknown_provider_raises(self) -> None:
        from patchbay_gateway.core.exceptions import UnknownProviderError
        with pytest.raises(UnknownProviderError):
            ProviderRegistry.get_adapter("nonexistent")
