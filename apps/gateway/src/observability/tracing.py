"""OpenTelemetry tracing integration for distributed request tracing.

Each request generates a trace with spans for:
  - gateway.request (top-level)
  - routing.select_route
  - guardrails.check_input
  - provider.{name}.send
  - mcp.tool_call (if applicable)
  - billing.calculate_cost

Traces are exported to Grafana Tempo for visualization.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class TracingService:
    """OpenTelemetry tracing service with automatic span creation."""

    def __init__(self, service_name: str = "patchbay-gateway") -> None:
        self._service_name = service_name
        self._tracer: Any = None
        self._initialized = False

    def init(self) -> None:
        """Initialize OpenTelemetry tracer (called once at startup)."""
        if self._initialized:
            return

        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": self._service_name})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self._service_name)
            self._initialized = True
            logger.info("tracing_initialized", extra={"service": self._service_name})
        except ImportError:
            logger.warning("opentelemetry_not_installed")
        except Exception as e:
            logger.error("tracing_init_failed", extra={"error": str(e)})

    def start_span(self, name: str, attributes: dict[str, Any] | None = None) -> Any:
        """Start a new tracing span."""
        if self._tracer is None:
            return None
        span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        return span

    def trace_request(self, request_id: str, model: str, provider: str) -> Any:
        """Start a top-level request trace."""
        return self.start_span(
            "gateway.request",
            {"request.id": request_id, "model": model, "provider": provider},
        )
