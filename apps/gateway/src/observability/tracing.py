from __future__ import annotations

from typing import Any


class TracingService:
    """OpenTelemetry tracing integration."""

    def __init__(self, service_name: str = "patchbay-gateway") -> None:
        self._service_name = service_name
        self._tracer = None

    def init(self) -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": self._service_name})
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(
                __import__("opentelemetry.sdk.trace.export", fromlist=["BatchSpanProcessor"]).BatchSpanProcessor(
                    ConsoleSpanExporter()
                )
            )
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self._service_name)
        except ImportError:
            pass

    def start_span(self, name: str) -> Any:
        if self._tracer:
            return self._tracer.start_span(name)
        return None
