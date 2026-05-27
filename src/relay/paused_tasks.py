"""paused_tasks — Postgres accessor for paused-pending-decision state-snapshots.

Per PR #1140 §5 (resume-spawn protocol) + §7 piece #2 (this module). The
dispatcher (PR #1188, Agency_OS-8416) writes via insert_from_envelope();
the resume-spawn path reads via get_by_task_ref(). A sweep job (separate
KEI) uses iter_expired() to find dead-letter candidates.

bd: Agency_OS-tjni

DI: caller passes any object implementing _DBProtocol (execute + fetchone +
fetchall). Same pattern as src/relay/spawn_composer.py + scripts/dispatcher/.
Module is asyncpg/psycopg-import-free → testable without live Supabase.

Envelope shape: paused_pending_decision (per my PR #1181 envelope schema):
  required: id, type, from, task_ref, paused_at, interim_state
The accessor validates `task_ref` + `paused_at` + `interim_state` only; the
HMAC + schema-type checks happen at the envelope layer (envelope_schema.py).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

# 7-day default per PR #1140 §5 line 102. Caller can override via
# insert_from_envelope(ttl_seconds=...) for tests + per-task customisation.
DEFAULT_TTL_SECONDS: int = 7 * 86400

STATE_PENDING = "pending"
STATE_RESUMED = "resumed"
STATE_DEAD_LETTERED = "dead_lettered"

_REQUIRED_ENVELOPE_FIELDS = frozenset({"task_ref", "paused_at", "interim_state"})


class _DBProtocol(Protocol):
    """Subset of a DB cursor we depend on. Mirrors PR #1184 composer + PR #1173."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


class PausedTasksStoreError(ValueError):
    """Raised on envelope-shape mismatch or invariant violation."""


@dataclass(frozen=True, kw_only=True)
class PausedTask:
    """Row shape from public.keiracom_paused_tasks."""

    task_ref: str
    callsign: str
    paused_at: int  # unix-int (DB stores TIMESTAMPTZ; accessor normalises to int)
    deadline_at: int
    interim_state: Mapping[str, Any]
    question: str | None
    options: Mapping[str, Any] | None
    state: str


class PausedTasksStore:
    """DB-backed paused-task lifecycle: insert (write) + get (read) + delete +
    iter_expired (dead-letter sweep)."""

    def __init__(self, *, db: _DBProtocol):
        self._db = db

    def insert_from_envelope(
        self,
        envelope: Mapping[str, Any],
        callsign: str,
        *,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Persist a paused_pending_decision envelope. Idempotent on task_ref.

        Raises PausedTasksStoreError if required envelope fields are missing.
        """
        missing = _REQUIRED_ENVELOPE_FIELDS - envelope.keys()
        if missing:
            raise PausedTasksStoreError(f"envelope missing required fields: {sorted(missing)}")
        if not callsign:
            raise PausedTasksStoreError("callsign is required")
        task_ref = envelope["task_ref"]
        paused_at = int(envelope["paused_at"])
        interim_state = envelope["interim_state"]
        question = envelope.get("question")
        options = envelope.get("options")
        deadline_at = paused_at + ttl_seconds
        self._db.execute(
            """
            INSERT INTO public.keiracom_paused_tasks (
                task_ref, callsign, paused_at, deadline_at,
                interim_state, question, options
            ) VALUES (
                $1, $2, to_timestamp($3), to_timestamp($4),
                $5::jsonb, $6, $7::jsonb
            )
            ON CONFLICT (task_ref) DO UPDATE SET
                interim_state = EXCLUDED.interim_state,
                question = EXCLUDED.question,
                options = EXCLUDED.options,
                deadline_at = EXCLUDED.deadline_at,
                state = 'pending',
                updated_at = NOW()
            """,
            task_ref,
            callsign,
            paused_at,
            deadline_at,
            interim_state,
            question,
            options,
        )

    def get_by_task_ref(self, task_ref: str) -> PausedTask | None:
        """Fetch a single row by task_ref. Returns None if not found."""
        self._db.execute(
            """
            SELECT task_ref, callsign,
                   EXTRACT(EPOCH FROM paused_at)::bigint,
                   EXTRACT(EPOCH FROM deadline_at)::bigint,
                   interim_state, question, options, state
              FROM public.keiracom_paused_tasks
             WHERE task_ref = $1
            """,
            task_ref,
        )
        row = self._db.fetchone()
        return _row_to_paused_task(row) if row else None

    def delete(self, task_ref: str) -> None:
        """Remove a row by task_ref. Idempotent — no error on missing row."""
        self._db.execute(
            "DELETE FROM public.keiracom_paused_tasks WHERE task_ref = $1",
            task_ref,
        )

    def mark_state(self, task_ref: str, new_state: str) -> None:
        """Transition lifecycle state (pending → resumed | dead_lettered)."""
        if new_state not in {STATE_PENDING, STATE_RESUMED, STATE_DEAD_LETTERED}:
            raise PausedTasksStoreError(f"unknown state {new_state!r}")
        self._db.execute(
            "UPDATE public.keiracom_paused_tasks SET state = $1 WHERE task_ref = $2",
            new_state,
            task_ref,
        )

    def iter_expired(self, now: int) -> Iterator[PausedTask]:
        """Yield pending rows whose deadline has elapsed (dead-letter sweep input)."""
        self._db.execute(
            """
            SELECT task_ref, callsign,
                   EXTRACT(EPOCH FROM paused_at)::bigint,
                   EXTRACT(EPOCH FROM deadline_at)::bigint,
                   interim_state, question, options, state
              FROM public.keiracom_paused_tasks
             WHERE state = 'pending' AND deadline_at < to_timestamp($1)
            """,
            now,
        )
        for row in self._db.fetchall() or []:
            yield _row_to_paused_task(row)


def _row_to_paused_task(row: Any) -> PausedTask:
    return PausedTask(
        task_ref=row[0],
        callsign=row[1],
        paused_at=int(row[2]),
        deadline_at=int(row[3]),
        interim_state=row[4] or {},
        question=row[5],
        options=row[6],
        state=row[7],
    )
