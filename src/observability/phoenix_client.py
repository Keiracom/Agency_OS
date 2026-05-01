"""GOV-PHASE2 Auditor — Phoenix OTLP adapter.

Converts public.governance_events rows into Phoenix spans via OTLP HTTP.
Used by scripts/phoenix_export_loop.py to ship rows on a watermark loop.

Env:
    PHOENIX_OTLP_ENDPOINT  — default http://localhost:4318/v1/traces
    PHOENIX_PROJECT        — default agency-os-governance
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = os.environ.get(
    "PHOENIX_OTLP_ENDPOINT", "http://localhost:4318/v1/traces"
)
DEFAULT_PROJECT = os.environ.get("PHOENIX_PROJECT", "agency-os-governance")


def init_tracer(project: str = DEFAULT_PROJECT, endpoint: str = DEFAULT_ENDPOINT):
    """Register a Phoenix OTel tracer. Returns a tracer or None on failure.

    `phoenix.otel.register()` returns a TracerProvider — call `.get_tracer()` on
    it to get the actual Tracer that has `start_as_current_span`. Wrapped —
    observability never blocks the caller.
    """
    try:
        from phoenix.otel import register
        provider = register(project_name=project, endpoint=endpoint)
        return provider.get_tracer(__name__)
    except Exception as exc:  # pragma: no cover - import / network failure
        logger.warning("init_tracer failed (%s)", exc)
        return None


def export_event(tracer, event: dict[str, Any]) -> bool:
    """Convert one governance_events row to a Phoenix span. Returns True on
    success, False on any failure. Wrapped — never raises."""
    if tracer is None:
        return False
    try:
        span_name = str(event.get("event_type") or "governance_event")
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("callsign", str(event.get("callsign") or ""))
            span.set_attribute("tool_name", str(event.get("tool_name") or ""))
            span.set_attribute("file_path", str(event.get("file_path") or ""))
            span.set_attribute("directive_id", str(event.get("directive_id") or ""))
            event_data = event.get("event_data") or {}
            if isinstance(event_data, dict):
                for k, v in event_data.items():
                    span.set_attribute(f"event_data.{k}", str(v))
            ts = event.get("timestamp")
            if ts is not None:
                span.set_attribute("source_timestamp", str(ts))
        return True
    except Exception as exc:  # pragma: no cover - export failure
        logger.warning("export_event failed for event_type=%s: %s",
                       event.get("event_type"), exc)
        return False
