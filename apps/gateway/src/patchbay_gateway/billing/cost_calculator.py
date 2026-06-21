"""Actual cost calculation using route pricing and provider-reported token usage.

Cost is calculated AFTER the request completes, using the real token counts
from the provider response (not estimates). This ensures billing accuracy.

Formula:
  cost = (input_tokens / 1,000,000) × input_price + (output_tokens / 1,000,000) × output_price
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from patchbay_gateway.db.models import ProviderRoute


def calculate_cost(
    route: ProviderRoute,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    """Calculate actual cost based on route pricing and token usage.

    Uses Decimal arithmetic for precise financial calculations.
    Prices are in cents per million tokens.

    Args:
        route: Provider route with pricing information.
        input_tokens: Actual input tokens from provider response.
        output_tokens: Actual output tokens from provider response.

    Returns:
        Cost in USD cents (Decimal for precision).
    """
    input_cost = (
        (Decimal(input_tokens) / Decimal(1_000_000))
        * route.pricing_input_per_million_cents
    )
    output_cost = (
        (Decimal(output_tokens) / Decimal(1_000_000))
        * route.pricing_output_per_million_cents
    )
    return (input_cost + output_cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def estimate_cost(
    route: ProviderRoute,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
) -> Decimal:
    """Estimate cost before sending the request (for budget checks).

    Uses the same formula as calculate_cost but with estimated tokens.
    """
    return calculate_cost(route, estimated_input_tokens, estimated_output_tokens)
