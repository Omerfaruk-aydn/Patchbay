"""Prometheus metrics for the Patchbay Gateway.

Metrics exposed at /metrics endpoint for Prometheus scraping:
  - patchbay_requests_total (counter) — total requests by provider/model/status
  - patchbay_request_latency_seconds (histogram) — request latency distribution
  - patchbay_active_routes (gauge) — healthy routes per provider
  - patchbay_circuit_breaker_state (gauge) — circuit breaker state per route
  - patchbay_cache_hits_total (counter) — cache hits by cache type
  - patchbay_cost_usd_cents_total (counter) — total cost by provider/model
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "patchbay_requests_total",
    "Total number of requests processed",
    ["provider", "model", "status"],
)

REQUEST_LATENCY = Histogram(
    "patchbay_request_latency_seconds",
    "Request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

ACTIVE_ROUTES = Gauge(
    "patchbay_active_routes",
    "Number of healthy routes per provider",
    ["provider"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "patchbay_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["route_id"],
)

CACHE_HITS = Counter(
    "patchbay_cache_hits_total",
    "Total cache hits",
    ["cache_type"],
)

COST_TOTAL = Counter(
    "patchbay_cost_usd_cents_total",
    "Total cost in USD cents",
    ["provider", "model"],
)

FALLBACK_COUNT = Counter(
    "patchbay_fallback_total",
    "Total number of fallback attempts",
    ["from_provider", "to_provider"],
)

GUARDRAIL_VIOLATIONS = Counter(
    "patchbay_guardrail_violations_total",
    "Total guardrail violations",
    ["rule_type", "severity"],
)
