from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from patchbay_gateway.billing.cost_calculator import calculate_cost


class FakeRoute:
    pricing_input_per_million_cents = 100
    pricing_output_per_million_cents = 300


class TestCostCalculator:
    def test_basic_calculation(self):
        route = FakeRoute()
        cost = calculate_cost(route, 1000, 500)
        # 1000/1M * 100 + 500/1M * 300 = 0.1 + 0.15 = 0.25
        assert float(cost) == 0.25

    def test_zero_tokens(self):
        route = FakeRoute()
        cost = calculate_cost(route, 0, 0)
        assert float(cost) == 0.0
