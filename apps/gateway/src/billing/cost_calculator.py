from __future__ import annotations

from decimal import Decimal

from patchbay_gateway.db.models import ProviderRoute


def calculate_cost(
    route: ProviderRoute, input_tokens: int, output_tokens: int
) -> Decimal:
    """Calculate actual cost based on route pricing and token usage."""
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * route.pricing_input_per_million_cents
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * route.pricing_output_per_million_cents
    return input_cost + output_cost
