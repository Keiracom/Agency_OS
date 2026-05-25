"""aggregator.py — bucket MeteringEvent stream by (tenant_id, date_utc, model).

Phase 2 build wave 2 item 3.

Pure in-memory accumulator. Sink writes to DB. Separation keeps the
aggregator deterministic + trivially testable (no DB in test path) and
lets the sink swap (PostgresSink for prod, FakeSink for tests, future
NullSink for dry-run replay).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .log_reader import MeteringEvent


@dataclass(frozen=True)
class _BucketKey:
    tenant_id: str
    date_utc: str
    model: str


@dataclass
class MeteringRow:
    """Aggregated metering row — one row per (tenant_id, date_utc, model) tuple.

    Mirrors the primary key of public.keiracom_tenant_metering. The sink
    UPSERTs on this composite key so re-running the pipeline over a
    previously-processed log range is idempotent.
    """

    tenant_id: str
    date_utc: str
    model: str
    request_count: int = 0
    input_tokens_sum: int = 0
    output_tokens_sum: int = 0

    def add(self, event: MeteringEvent) -> None:
        self.request_count += 1
        self.input_tokens_sum += event.input_tokens
        self.output_tokens_sum += event.output_tokens


class Aggregator:
    """Stream MeteringEvents → flushable batch of MeteringRows.

    Memory bounded by the number of distinct (tenant, date, model) buckets
    in a flush window. For V1 the pipeline runs daily over the previous
    day's log range, so cardinality is bounded by tenant_count * model_count
    (typically <1000 rows).
    """

    def __init__(self) -> None:
        self._buckets: dict[_BucketKey, MeteringRow] = {}

    def add_event(self, event: MeteringEvent) -> None:
        key = _BucketKey(event.tenant_id, event.date_utc, event.model)
        row = self._buckets.get(key)
        if row is None:
            row = MeteringRow(
                tenant_id=event.tenant_id,
                date_utc=event.date_utc,
                model=event.model,
            )
            self._buckets[key] = row
        row.add(event)

    def add_events(self, events: Iterable[MeteringEvent]) -> None:
        for ev in events:
            self.add_event(ev)

    def flush(self) -> list[MeteringRow]:
        """Drain accumulator → list of MeteringRow + reset internal state.

        Order is insertion-order of first event per bucket — stable for
        snapshot diffing but not sorted. Sink is responsible for any
        sorting it needs (e.g. for deterministic SQL parameter binding).
        """
        rows = list(self._buckets.values())
        self._buckets.clear()
        return rows
