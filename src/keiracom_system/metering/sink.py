"""sink.py — write aggregated MeteringRow batches to keiracom_tenant_metering.

Phase 2 build wave 2 item 3.

The sink is the only DB-touching surface in the metering pipeline. Tests
inject a _DBProtocol-conformant fake; production wires a psycopg-backed
client via from_env() (P1 follow-up — see below).

Idempotency contract: UPSERT on (tenant_id, date_utc, model) with cumulative
ADD on the count + token columns. Re-running the pipeline over the same log
range therefore produces the correct totals as long as the same log lines
appear (the underlying log shipper is assumed to provide exactly-once).

For V1 the upsert SQL is owned by the database adapter (so the sink stays
SQL-dialect-free). Production wiring lands in P1 follow-up bd alongside
the psycopg adapter.
"""

from __future__ import annotations

import logging
from typing import Protocol

from .aggregator import MeteringRow

log = logging.getLogger(__name__)


class _DBProtocol(Protocol):
    """Minimal sink-side DB surface. One method, intentionally narrow."""

    def upsert_metering_rows(self, rows: list[MeteringRow]) -> int:
        """Apply rows to keiracom_tenant_metering. Returns affected count."""
        ...


class PostgresSink:
    """Write MeteringRow batches to keiracom_tenant_metering via injected db.

    Holds no connection state — single round-trip per write_rows call.
    Connection pooling + transaction management are the adapter's job
    (per Atlas's provisioning.py pattern).
    """

    def __init__(self, db: _DBProtocol):
        self._db = db

    def write_rows(self, rows: list[MeteringRow]) -> int:
        """Persist rows; returns rows-affected count. Empty input is a no-op."""
        if not rows:
            return 0
        return self._db.upsert_metering_rows(rows)
