"""Structured JSON logging configuration.

Outputs JSON-formatted logs to stdout for easy parsing by
centralized logging systems (Loki, ELK, CloudWatch).

Log entry format:
  {
    "timestamp": "2026-06-21T12:00:00Z",
    "level": "INFO",
    "logger": "patchbay_gateway.routing.engine",
    "message": "route_selected",
    "module": "engine",
    "function": "select_route",
    "line": 42,
    "extra": {"model": "gpt-4o", "provider": "openai", "latency_ms": 12.5}
  }
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with optional extra context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        extra_fields = {}
        for key in ("model", "provider", "route_id", "latency_ms", "status",
                     "error", "attempt", "elapsed_ms", "strategy", "candidates",
                     "extra"):
            value = getattr(record, key, None)
            if value is not None:
                extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging() -> None:
    """Configure structured JSON logging for the application.

    Suppresses noisy loggers and sets appropriate levels:
      - SQLALchemy engine: WARNING (queries are too verbose)
      - Uvicorn access: WARNING (handled by structured logs)
      - Root logger: INFO
    """
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root.handlers.clear()
    root.addHandler(handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
