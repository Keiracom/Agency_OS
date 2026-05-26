"""paused_tasks_store — durable-wait state accessor for ephemeral agent decisions.

Per docs/architecture/ephemeral_agent_system_scoping.md §5 + §7 piece 2
(PR #1140), Agency_OS-70hb.

ROLE: when an agent pauses pending a decision_response, the dispatcher writes
a row HERE with task_ref + question + state_snapshot. On decision_response
arrival, dispatcher reads the row + hands the state_snapshot to the resume
spawn (per Nova PR #1184 spawn_composer's resume-context branch). Stale rows
(>7 days) sweep to expired + dead-letter to Elliot.

DI: caller passes any DB cursor implementing _DBProtocol — no asyncpg/psycopg
import inside this module. Production wires asyncpg; unit tests inject fakes.
Lives in src/relay/ alongside Nova's envelope_schema.py (PR #1181) +
redis_relay.py + relay_consumer.py.

PROTOCOL (per §5):
  1. Agent emits paused_pending_decision event → dispatcher calls
     `PausedTasksStore.insert(task_ref, callsign, decision_target, question,
     state_snapshot)`.
  2. Agent terminates.
  3. decision_response arrives → dispatcher calls
     `PausedTasksStore.fetch(task_ref)` to retrieve state_snapshot.
  4. Dispatcher spawns resume agent + calls `mark_resumed(task_ref)`.
  5. Daily sweep calls `sweep_expired()` → returns expired rows for
     dead-lettering to Elliot inbox.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Default TTL — 7 days per §5 ("e.g. 7 days"). Caller can override at insert.
DEFAULT_TTL_DAYS: int = 7

# Status enum — mirrors the SQL CHECK on paused_tasks.status.
STATUS_ACTIVE: str = "active"
STATUS_RESUMED: str = "resumed"
STATUS_EXPIRED: str = "expired"
STATUS_ABORTED: str = "aborted"

VALID_STATUSES: frozenset[str] = frozenset(
    {STATUS_ACTIVE, STATUS_RESUMED, STATUS_EXPIRED, STATUS_ABORTED}
)


class PausedTasksStoreError(RuntimeError):
    """Raised on invalid input or store-side error."""


class _DBProtocol(Protocol):
    """Subset of DB cursor we depend on. Mirrors PR #1173 / #1185 _DBProtocol."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


@dataclass(frozen=True, kw_only=True)
class PausedTaskRow:
    """In-memory representation of one paused_tasks row.

    Frozen — mutations create new instances (mark_resumed etc. issue UPDATE
    statements and re-fetch via the store rather than mutating in place).
    """

    task_ref: str
    callsign: str
    decision_target: str
    question: str
    state_snapshot: dict[str, Any]
    status: str
    created_at: datetime
    expires_at: datetime
    resumed_at: datetime | None = None
    expired_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.task_ref:
            raise PausedTasksStoreError("task_ref must be non-empty")
        if self.status not in VALID_STATUSES:
            raise PausedTasksStoreError(f"status {self.status!r} not in {sorted(VALID_STATUSES)}")


class PausedTasksStore:
    """Durable-wait accessor for the paused_tasks table.

    Caller injects a DB cursor; the store owns all SQL. No asyncpg/psycopg
    imports inside this module (the cache + atomization layers follow the
    same DI pattern — boundary-matrix-v1 guard b compatible even though
    src/relay/ is outside BMV1 scope).
    """

    def __init__(self, *, db: _DBProtocol, now_provider=None):
        self._db = db
        # Injectable now() for deterministic tests; default = utcnow.
        self._now = now_provider or (lambda: datetime.now(UTC))

    def insert(
        self,
        *,
        task_ref: str,
        callsign: str,
        decision_target: str,
        question: str,
        state_snapshot: dict[str, Any] | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
    ) -> None:
        """Write a paused_pending_decision state row.

        Idempotent on task_ref via Postgres ON CONFLICT DO NOTHING — re-issuing
        the same paused_pending_decision (e.g. dispatcher retry) doesn't
        clobber the original timestamp + TTL window.
        """
        if not task_ref:
            raise PausedTasksStoreError("task_ref must be non-empty")
        if not callsign:
            raise PausedTasksStoreError("callsign must be non-empty")
        if not decision_target:
            raise PausedTasksStoreError("decision_target must be non-empty")
        if not question:
            raise PausedTasksStoreError("question must be non-empty")
        if ttl_days <= 0:
            raise PausedTasksStoreError("ttl_days must be > 0")
        now = self._now()
        expires_at = now + timedelta(days=ttl_days)
        snapshot_json = json.dumps(state_snapshot or {})
        self._db.execute(
            "INSERT INTO paused_tasks ("
            "task_ref, callsign, decision_target, question, state_snapshot, "
            "status, created_at, expires_at"
            ") VALUES (%s, %s, %s, %s, %s, 'active', %s, %s) "
            "ON CONFLICT (task_ref) DO NOTHING",
            task_ref,
            callsign,
            decision_target,
            question,
            snapshot_json,
            now,
            expires_at,
        )

    def fetch(self, task_ref: str) -> PausedTaskRow | None:
        """Look up by task_ref. Returns None if absent.

        Used by dispatcher on decision_response arrival to retrieve the
        state_snapshot for handoff to the resume spawn.
        """
        if not task_ref:
            raise PausedTasksStoreError("task_ref must be non-empty")
        self._db.execute(
            "SELECT task_ref, callsign, decision_target, question, "
            "state_snapshot, status, created_at, expires_at, resumed_at, "
            "expired_at "
            "FROM paused_tasks WHERE task_ref = %s",
            task_ref,
        )
        row = self._db.fetchone()
        if row is None:
            return None
        return self._row_to_paused_task(row)

    def mark_resumed(self, task_ref: str) -> None:
        """Flip status from active → resumed. Called when dispatcher spawns
        the resume agent on decision_response arrival.
        """
        if not task_ref:
            raise PausedTasksStoreError("task_ref must be non-empty")
        now = self._now()
        self._db.execute(
            "UPDATE paused_tasks SET status = 'resumed', resumed_at = %s "
            "WHERE task_ref = %s AND status = 'active'",
            now,
            task_ref,
        )

    def mark_aborted(self, task_ref: str) -> None:
        """Flip status from active → aborted. Used when decision_response
        carries decision='abort' (per §5 edge case)."""
        if not task_ref:
            raise PausedTasksStoreError("task_ref must be non-empty")
        self._db.execute(
            "UPDATE paused_tasks SET status = 'aborted' WHERE task_ref = %s AND status = 'active'",
            task_ref,
        )

    def sweep_expired(self) -> list[PausedTaskRow]:
        """TTL sweep: mark all expired-eligible rows as expired + return them.

        Caller (a daily/hourly cron) iterates the returned rows and writes
        dead-letter JSON to Elliot's inbox for review.

        Atomic: SELECT + UPDATE in one transaction via UPDATE ... RETURNING.
        """
        now = self._now()
        self._db.execute(
            "UPDATE paused_tasks SET status = 'expired', expired_at = %s "
            "WHERE status = 'active' AND expires_at <= %s "
            "RETURNING task_ref, callsign, decision_target, question, "
            "state_snapshot, status, created_at, expires_at, resumed_at, "
            "expired_at",
            now,
            now,
        )
        rows = self._db.fetchall() or []
        return [self._row_to_paused_task(r) for r in rows]

    def list_by_callsign(
        self, callsign: str, *, status: str = STATUS_ACTIVE
    ) -> list[PausedTaskRow]:
        """Show all paused tasks for a callsign with the given status.

        Useful for "what is orion waiting on?" diagnostics or per-callsign
        cleanup queries.
        """
        if status not in VALID_STATUSES:
            raise PausedTasksStoreError(f"status {status!r} not in {sorted(VALID_STATUSES)}")
        self._db.execute(
            "SELECT task_ref, callsign, decision_target, question, "
            "state_snapshot, status, created_at, expires_at, resumed_at, "
            "expired_at "
            "FROM paused_tasks WHERE callsign = %s AND status = %s "
            "ORDER BY created_at DESC",
            callsign,
            status,
        )
        rows = self._db.fetchall() or []
        return [self._row_to_paused_task(r) for r in rows]

    def list_pending_for_target(self, decision_target: str) -> list[PausedTaskRow]:
        """Show all active tasks awaiting a decision from `decision_target`.

        Used by per-callsign dispatchers + the "orion is waiting on aiden"
        operational query.
        """
        if not decision_target:
            raise PausedTasksStoreError("decision_target must be non-empty")
        self._db.execute(
            "SELECT task_ref, callsign, decision_target, question, "
            "state_snapshot, status, created_at, expires_at, resumed_at, "
            "expired_at "
            "FROM paused_tasks WHERE decision_target = %s AND status = 'active' "
            "ORDER BY created_at ASC",
            decision_target,
        )
        rows = self._db.fetchall() or []
        return [self._row_to_paused_task(r) for r in rows]

    # ------------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------------

    @staticmethod
    def _row_to_paused_task(row: Any) -> PausedTaskRow:
        """Build a PausedTaskRow from a DB row tuple in canonical column order."""
        task_ref, callsign, decision_target, question, state_snapshot = row[:5]
        status, created_at, expires_at, resumed_at, expired_at = row[5:]
        return PausedTaskRow(
            task_ref=str(task_ref),
            callsign=str(callsign),
            decision_target=str(decision_target),
            question=str(question),
            state_snapshot=_parse_jsonb(state_snapshot),
            status=str(status),
            created_at=_coerce_datetime(created_at),
            expires_at=_coerce_datetime(expires_at),
            resumed_at=_coerce_datetime(resumed_at) if resumed_at else None,
            expired_at=_coerce_datetime(expired_at) if expired_at else None,
        )


def _parse_jsonb(value: Any) -> dict[str, Any]:
    """Postgres JSONB may come back as dict (psycopg adapts) or str (raw)."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return json.loads(value)
    return {}


def _coerce_datetime(value: Any) -> datetime:
    """Tolerate either a datetime or an ISO-format string from the DB layer."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        # Handle both 'Z' and offset notations.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise PausedTasksStoreError(f"unexpected datetime shape: {type(value).__name__}")


def dead_letter_payload(rows: Iterable[PausedTaskRow]) -> list[dict[str, Any]]:
    """Render expired paused_tasks rows as JSON-serializable dicts.

    Caller (the TTL sweep) writes these to Elliot's inbox at
    /tmp/telegram-relay-elliot/inbox/paused_tasks_expired_<ts>.json so Elliot
    can review the stale-decision queue + escalate to Dave if needed.

    Empty list → no dead-letter file needed.
    """
    return [
        {
            "task_ref": r.task_ref,
            "callsign": r.callsign,
            "decision_target": r.decision_target,
            "question": r.question,
            "state_snapshot": r.state_snapshot,
            "created_at": r.created_at.isoformat(),
            "expires_at": r.expires_at.isoformat(),
            "expired_at": r.expired_at.isoformat() if r.expired_at else None,
        }
        for r in rows
    ]
