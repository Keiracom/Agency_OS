"""store.py — tenant-scoped Postgres access for keiracom_paused_tasks.

Phase A8 §7 piece 2. Mirrors PR #1185 AtomStore + PR #1173 ValkeyClient
tenant-prefix-guard discipline: every read + write path enforces
`tenant_id = self._tenant_id` so no cross-tenant data can leak.

CI guard `scripts/ci/check_no_raw_paused_tasks_outside_module.sh` rejects
direct SQL on the table from outside this module (mirrors the A7 CB-10 +
boundary-matrix-v1 import-detection pattern).

bd: Agency_OS-70hb
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

DEFAULT_TTL_DAYS = 7


class PausedTaskStoreError(RuntimeError):
    """Accessor-specific error (tenant mismatch / not found / db error wrapper)."""


class _CursorProtocol(Protocol):
    def execute(self, sql: str, params: tuple | dict | None = ...) -> Any: ...
    def fetchone(self) -> tuple | None: ...
    def fetchall(self) -> list[tuple]: ...


class _DBProtocol(Protocol):
    def cursor(self) -> _CursorProtocol: ...
    def commit(self) -> None: ...


@dataclass(frozen=True)
class PausedTaskRecord:
    paused_task_id: str
    tenant_id: str
    callsign: str
    task_ref: str
    question: str
    state_snapshot: dict[str, Any]
    paused_at: datetime
    expires_at: datetime
    status: str  # 'paused' | 'resolved' | 'aborted' | 'expired'
    resolved_at: datetime | None
    decision_response_ref: str | None


_SELECT_COLUMNS = (
    "paused_task_id, tenant_id, callsign, task_ref, question, "
    "state_snapshot, paused_at, expires_at, status, "
    "resolved_at, decision_response_ref"
)


def _row_to_record(row: tuple) -> PausedTaskRecord:
    return PausedTaskRecord(
        paused_task_id=str(row[0]),
        tenant_id=str(row[1]),
        callsign=row[2],
        task_ref=row[3],
        question=row[4],
        state_snapshot=row[5] or {},
        paused_at=row[6],
        expires_at=row[7],
        status=row[8],
        resolved_at=row[9],
        decision_response_ref=row[10],
    )


class PausedTaskStore:
    """Tenant-scoped accessor — every query auto-bounds to self._tenant_id."""

    def __init__(self, *, db: _DBProtocol, tenant_id: str) -> None:
        if not tenant_id:
            raise PausedTaskStoreError("tenant_id required (cross-tenant isolation invariant)")
        self._db = db
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def insert_paused(
        self,
        *,
        callsign: str,
        task_ref: str,
        question: str,
        state_snapshot: dict[str, Any] | None = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
        now: datetime | None = None,
    ) -> str:
        if not callsign or not task_ref or not question:
            raise PausedTaskStoreError("callsign, task_ref, question all required")
        if ttl_days <= 0:
            raise PausedTaskStoreError("ttl_days must be positive")
        snapshot = state_snapshot or {}
        ts_now = now or datetime.now(UTC)
        expires = ts_now + timedelta(days=ttl_days)
        cur = self._db.cursor()
        cur.execute(
            """
            INSERT INTO public.keiracom_paused_tasks
                (tenant_id, callsign, task_ref, question, state_snapshot,
                 paused_at, expires_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
            RETURNING paused_task_id
            """,
            (
                self._tenant_id,
                callsign,
                task_ref,
                question,
                snapshot,
                ts_now,
                expires,
            ),
        )
        row = cur.fetchone()
        self._db.commit()
        return str(row[0])

    def find_by_task_ref(self, task_ref: str) -> PausedTaskRecord | None:
        cur = self._db.cursor()
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} FROM public.keiracom_paused_tasks "
            "WHERE tenant_id = %s AND task_ref = %s "
            "ORDER BY paused_at DESC LIMIT 1",
            (self._tenant_id, task_ref),
        )
        row = cur.fetchone()
        return _row_to_record(row) if row else None

    def find_paused_by_callsign(self, callsign: str) -> list[PausedTaskRecord]:
        cur = self._db.cursor()
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} FROM public.keiracom_paused_tasks "
            "WHERE tenant_id = %s AND callsign = %s AND status = 'paused' "
            "ORDER BY paused_at",
            (self._tenant_id, callsign),
        )
        return [_row_to_record(r) for r in cur.fetchall()]

    def resolve(self, *, task_ref: str, decision_response_ref: str) -> bool:
        cur = self._db.cursor()
        cur.execute(
            "UPDATE public.keiracom_paused_tasks "
            "SET status = 'resolved', resolved_at = NOW(), "
            "    decision_response_ref = %s "
            "WHERE tenant_id = %s AND task_ref = %s AND status = 'paused'",
            (decision_response_ref, self._tenant_id, task_ref),
        )
        self._db.commit()
        return _affected_rows(cur) > 0

    def abort(self, *, task_ref: str) -> bool:
        cur = self._db.cursor()
        cur.execute(
            "UPDATE public.keiracom_paused_tasks "
            "SET status = 'aborted' "
            "WHERE tenant_id = %s AND task_ref = %s AND status = 'paused'",
            (self._tenant_id, task_ref),
        )
        self._db.commit()
        return _affected_rows(cur) > 0

    def expire_old(self, *, now: datetime | None = None) -> int:
        """Mark paused rows past expires_at as 'expired'. Returns row count."""
        ts_now = now or datetime.now(UTC)
        cur = self._db.cursor()
        cur.execute(
            "UPDATE public.keiracom_paused_tasks "
            "SET status = 'expired' "
            "WHERE tenant_id = %s AND status = 'paused' AND expires_at <= %s",
            (self._tenant_id, ts_now),
        )
        self._db.commit()
        return _affected_rows(cur)


def _affected_rows(cur: Any) -> int:
    return getattr(cur, "rowcount", 0) or 0
