"""Tests for cost calculation and budget enforcement."""

from __future__ import annotations

import pytest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from patchbay_gateway.billing.cost_calculator import calculate_cost


class FakeRoute:
    """Test double for ProviderRoute."""
    pricing_input_per_million_cents = Decimal("100")
    pricing_output_per_million_cents = Decimal("300")


class TestCostCalculator:
    """Tests for token cost calculation."""

    def test_basic_calculation(self):
        route = FakeRoute()
        cost = calculate_cost(route, 1000, 500)
        # 1000/1M * 100 + 500/1M * 300 = 0.1 + 0.15 = 0.25
        assert cost == Decimal("0.2500")

    def test_zero_tokens(self):
        route = FakeRoute()
        cost = calculate_cost(route, 0, 0)
        assert cost == Decimal("0.0000")

    def test_large_token_count(self):
        route = FakeRoute()
        cost = calculate_cost(route, 1000000, 500000)
        # 1M/1M * 100 + 500K/1M * 300 = 100 + 150 = 250
        assert cost == Decimal("250.0000")

    def test_precision(self):
        route = FakeRoute()
        cost = calculate_cost(route, 123, 456)
        assert cost == Decimal("0.0161")

    def test_different_pricing(self):
        route = FakeRoute()
        route.pricing_input_per_million_cents = Decimal("10")
        route.pricing_output_per_million_cents = Decimal("30")
        cost = calculate_cost(route, 100000, 50000)
        # 100K/1M * 10 + 50K/1M * 30 = 1 + 1.5 = 2.5
        assert cost == Decimal("2.5000")
