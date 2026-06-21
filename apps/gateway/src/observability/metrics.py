from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter(
    "patchbay_requests_total",
    "Total requests",
    ["provider", "model", "status"],
)

REQUEST_LATENCY = Histogram(
    "patchbay_request_latency_seconds",
    "Request latency in seconds",
    ["provider", "model"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_ROUTES = Gauge(
    "patchbay_active_routes",
    "Number of healthy routes",
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
