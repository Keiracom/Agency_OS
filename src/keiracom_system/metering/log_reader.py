"""log_reader.py — read Hindsight JSON log lines, emit per-tenant metering events.

Phase 2 build wave 2 item 3.

CANONICAL KEY ANCHOR — ceo:memory_abstraction_layer_v1 (RATIFIED 2026-05-24):

  eleven_agreed_positions[4] (position 5) verbatim:
    "Collective scope: tenant-bounded only, never cross-tenant inference
     (BYOK sovereignty)"

This pipeline materialises the Keiracom-side of that sovereignty contract:
tenants pay LLM providers DIRECTLY via their own BYOK key; this pipeline
captures aggregate spend for our observability + future overage-billing
view ONLY. Never used to bill tenants for inference (provider already did
that) and never used to route to a Keiracom-owned LLM key.

PR #1128 §7 P2 framing verbatim:
  "P2 — log-based per-tenant metering pipeline (Atlas #1126 G4).
   Vector/Filebeat → metering service → control plane spend table."

PR #1128 §5 mechanism 1 verbatim:
  "Hindsight-side log emission (Atlas #1126 finding #5): every JSON log
   line carries `tenant` field. Keiracom log-shipper (Vector / Filebeat /
   etc.) routes logs to a metering service that aggregates per-tenant
   spend over time."

PR #1128 §5 recommendation verbatim:
  "ship V1 with log-based metering only (mechanism 1). Add provider-
   billing-API integration (mechanism 2) as a P2 follow-up after first
   paying customer."

V1 SCOPE: log-based read-aggregate-sink. Provider-billing-API integration
(mechanism 2 from §5) is a separate P3 follow-up bd issue deferred to
post-first-paying-customer.

DESIGN: field map is injectable so future Hindsight log-schema drift can be
absorbed via env-var config rather than a code change. Non-LLM-call event
types are filtered out at the reader so the aggregator only sees billing-
relevant events.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import IO, Any

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MeteringEvent:
    """Per-call LLM spend event extracted from a Hindsight JSON log line.

    `timestamp` is timezone-aware UTC. `date_utc` is the YYYY-MM-DD bucket
    used by the aggregator — derived here so the aggregator stays free of
    timezone concerns.
    """

    tenant_id: str
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime

    @property
    def date_utc(self) -> str:
        return self.timestamp.astimezone(UTC).date().isoformat()


def _dig(obj: dict[str, Any], dotted_key: str) -> Any:
    """Walk a nested dict via dotted-key path (e.g. 'usage.input_tokens')."""
    cur: Any = obj
    for part in dotted_key.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


# Default Hindsight log field map. Override via the constructor when Hindsight
# updates its log schema — no code change needed in this reader.
DEFAULT_FIELD_MAP: dict[str, str] = {
    "tenant_id": "tenant",
    "model": "model",
    "input_tokens": "usage.input_tokens",
    "output_tokens": "usage.output_tokens",
    "timestamp": "ts",
    "event_type": "event",
}

# Only LLM-call event types contribute to metering rows. Hindsight emits
# many other event types (retain/recall/healthcheck) — those don't consume
# LLM tokens so we skip them at the reader rather than the aggregator.
LLM_CALL_EVENT_TYPES: frozenset[str] = frozenset({"llm_call", "reflect", "synthesize"})


class LogReader:
    """Stream Hindsight JSON-lines log → MeteringEvent iterator.

    Defensive against malformed input: bad JSON lines are logged + skipped
    (not raised) so a single bad log line doesn't poison a batch run.
    Lines that lack required fields, fail timestamp parsing, or carry a
    non-LLM event type are skipped without raising.
    """

    def __init__(
        self,
        stream: IO[str],
        field_map: dict[str, str] | None = None,
    ):
        self._stream = stream
        self._fmap = dict(field_map) if field_map else dict(DEFAULT_FIELD_MAP)

    def read_events(self) -> Iterator[MeteringEvent]:
        for line_num, raw in enumerate(self._stream, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                log.warning("log_reader: line %d malformed JSON: %s", line_num, exc)
                continue
            if not isinstance(obj, dict):
                log.warning("log_reader: line %d not a JSON object", line_num)
                continue
            event = self._extract_event(obj, line_num)
            if event is not None:
                yield event

    def _extract_event(self, obj: dict[str, Any], line_num: int) -> MeteringEvent | None:
        event_type = _dig(obj, self._fmap.get("event_type", "event"))
        if event_type not in LLM_CALL_EVENT_TYPES:
            return None

        tenant_id = _dig(obj, self._fmap["tenant_id"])
        model = _dig(obj, self._fmap["model"])
        ts_raw = _dig(obj, self._fmap["timestamp"])

        if not tenant_id or not model or ts_raw is None:
            log.warning("log_reader: line %d missing required fields (tenant/model/ts)", line_num)
            return None

        ts = self._parse_timestamp(ts_raw, line_num)
        if ts is None:
            return None

        return MeteringEvent(
            tenant_id=str(tenant_id),
            model=str(model),
            input_tokens=int(_dig(obj, self._fmap["input_tokens"]) or 0),
            output_tokens=int(_dig(obj, self._fmap["output_tokens"]) or 0),
            timestamp=ts,
        )

    @staticmethod
    def _parse_timestamp(raw: Any, line_num: int) -> datetime | None:
        """Accept ISO-8601 str (with optional trailing Z) or Unix epoch number."""
        try:
            if isinstance(raw, str):
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if isinstance(raw, int | float):
                return datetime.fromtimestamp(raw, tz=UTC)
        except (ValueError, TypeError, OSError) as exc:
            log.warning("log_reader: line %d bad timestamp %r: %s", line_num, raw, exc)
            return None
        log.warning(
            "log_reader: line %d timestamp type %s unsupported", line_num, type(raw).__name__
        )
        return None
