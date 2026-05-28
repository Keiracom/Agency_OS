"""Bounded-spawn enforcement — Agency_OS-gcpm (RED-7).

The bounded-spawn discipline (per ``docs/architecture/ephemeral_persistence_boundary.md``)
is load-bearing for the dispatcher: each spawn (tmux session / container) handles
exactly ONE task. PR #1201 keepalive enforces fresh ``claude`` respawn at the
chokepoint, but nothing previously stopped the dispatcher itself from handing a
second task to an already-active spawn slot — honour-system in production.

This module closes that gap with kill-on-violation:

  - Track ``{callsign: SpawnRecord}`` for every successful ``/dispatcher/spawn``.
  - On the next spawn for the same callsign, classify as VIOLATION when the
    new request carries a different task identifier than the active record.
  - On violation: append a JSONL audit row, fire a structured alert, and kill
    the prior spawn via the provided terminate callback.

Failure mode is fail-open by design — any internal exception (audit-write
failure, alerts emitter raise) MUST NOT block a legitimate spawn. The hard
floor for the enforcer is: "never block a fresh task because telemetry broke".
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — env knobs + defaults
# ---------------------------------------------------------------------------

ENFORCER_AUDIT_LOG_ENV = "DISPATCHER_BOUNDED_SPAWN_AUDIT_LOG"
DEFAULT_AUDIT_LOG_PATH = "/tmp/bounded_spawn_violations.jsonl"

# Decision names — kept stable so dashboards / alert routing can filter.
DECISION_RECORDED = "recorded"
DECISION_REPEAT_TASK = "repeat_task"  # same callsign + same task_id (idempotent)
DECISION_VIOLATION = "second_task_on_active_spawn"


@dataclasses.dataclass(frozen=True)
class SpawnRecord:
    """Snapshot of one active spawn slot."""

    key: str
    callsign: str
    task_id: str
    backend: str
    started_at: float  # time.monotonic()
    started_at_unix: float  # time.time() — wall clock, for audit log


@dataclasses.dataclass(frozen=True)
class EnforcementResult:
    """Outcome of a ``record_spawn`` check."""

    decision: str  # DECISION_*
    reason: str
    prior: SpawnRecord | None
    killed: bool


# ---------------------------------------------------------------------------
# Terminate callback signature — injected so the enforcer is decoupled from
# session_manager / FastAPI state. Returns True when the kill succeeded.
# ---------------------------------------------------------------------------

TerminateCallback = Callable[[str], bool]
AlertEmitter = Callable[[dict[str, Any]], None]


class BoundedSpawnEnforcer:
    """One-task-per-spawn enforcement layer.

    Thread-safe (lock around state mutation). Designed for module-level
    singleton use from ``src.dispatcher.main`` plus DI in tests.
    """

    def __init__(
        self,
        *,
        terminate_cb: TerminateCallback,
        alerts_emitter: AlertEmitter | None = None,
        audit_log_path: str | Path | None = None,
    ) -> None:
        self._terminate_cb = terminate_cb
        self._alerts_emitter = alerts_emitter or _default_alert_emitter
        self._audit_log_path = Path(
            audit_log_path or os.environ.get(ENFORCER_AUDIT_LOG_ENV, DEFAULT_AUDIT_LOG_PATH)
        )
        self._active: dict[str, SpawnRecord] = {}
        self._lock = threading.Lock()

    # -- spawn record / violation detection ---------------------------------

    def record_spawn(
        self,
        *,
        key: str,
        callsign: str,
        task_id: str,
        backend: str,
    ) -> EnforcementResult:
        """Record a new spawn slot; classify against prior active record.

        Returns ``EnforcementResult`` describing outcome. Callers should
        consult ``.killed`` to know whether the prior spawn was terminated.
        Even on violation, the new spawn is recorded as the active slot.
        """
        with self._lock:
            prior = self._active.get(callsign)

            if prior is None:
                rec = self._fresh_record(key, callsign, task_id, backend)
                self._active[callsign] = rec
                return EnforcementResult(
                    decision=DECISION_RECORDED,
                    reason="new spawn slot",
                    prior=None,
                    killed=False,
                )

            if prior.task_id == task_id:
                # Same callsign + same task_id = idempotent re-spawn (probably
                # keepalive bouncing through dispatcher). Refresh start time
                # but do not flag violation.
                rec = self._fresh_record(key, callsign, task_id, backend)
                self._active[callsign] = rec
                return EnforcementResult(
                    decision=DECISION_REPEAT_TASK,
                    reason="same task on same callsign — idempotent",
                    prior=prior,
                    killed=False,
                )

            # Different task_id while prior spawn still active = VIOLATION.
            killed = self._kill_violator(prior, new_task_id=task_id)
            self._audit_violation(prior, new_task_id=task_id, killed=killed)
            self._emit_alert(prior, new_task_id=task_id, killed=killed)
            # Record the new task as the canonical active spawn.
            self._active[callsign] = self._fresh_record(key, callsign, task_id, backend)
            return EnforcementResult(
                decision=DECISION_VIOLATION,
                reason=f"second task on active spawn ({prior.task_id!r}→{task_id!r})",
                prior=prior,
                killed=killed,
            )

    def would_violate(self, *, callsign: str, task_id: str) -> bool:
        """Read-only check: would a record_spawn for (callsign, task_id) violate?

        Used by the interceptor_proxy / governance_proxy hook to gate model
        calls that carry bounded-spawn metadata before they reach LiteLLM.
        Returns True when there is an active slot for ``callsign`` whose
        ``task_id`` differs from the supplied one.
        """
        with self._lock:
            prior = self._active.get(callsign)
            if prior is None:
                return False
            return prior.task_id != task_id

    def release_spawn(self, key: str) -> SpawnRecord | None:
        """Drop the active record for ``key``. Called from /dispatcher/terminate.

        Returns the released record (or None if no match) for caller logging.
        """
        with self._lock:
            for callsign, rec in list(self._active.items()):
                if rec.key == key:
                    self._active.pop(callsign, None)
                    return rec
            return None

    def snapshot(self) -> dict[str, dict[str, Any]]:
        """Return a JSON-safe snapshot of currently-active slots."""
        with self._lock:
            return {callsign: dataclasses.asdict(rec) for callsign, rec in self._active.items()}

    # -- internals ----------------------------------------------------------

    @staticmethod
    def _fresh_record(key: str, callsign: str, task_id: str, backend: str) -> SpawnRecord:
        return SpawnRecord(
            key=key,
            callsign=callsign,
            task_id=task_id,
            backend=backend,
            started_at=time.monotonic(),
            started_at_unix=time.time(),
        )

    def _kill_violator(self, prior: SpawnRecord, *, new_task_id: str) -> bool:
        """Invoke the terminate callback for the violating spawn. Fail-open."""
        try:
            ok = bool(self._terminate_cb(prior.key))
        except Exception:  # noqa: BLE001 — fail-open per module contract
            logger.exception(
                "bounded-spawn: terminate_cb raised for key=%s callsign=%s",
                prior.key,
                prior.callsign,
            )
            return False
        if not ok:
            logger.warning(
                "bounded-spawn: terminate_cb returned falsy for key=%s callsign=%s new_task=%s",
                prior.key,
                prior.callsign,
                new_task_id,
            )
        return ok

    def _audit_violation(
        self,
        prior: SpawnRecord,
        *,
        new_task_id: str,
        killed: bool,
    ) -> None:
        """Append a JSONL audit row. Fail-open (telemetry never blocks spawn)."""
        row = {
            "ts": time.time(),
            "event": "bounded_spawn_violation",
            "callsign": prior.callsign,
            "prior_key": prior.key,
            "prior_task_id": prior.task_id,
            "prior_backend": prior.backend,
            "prior_started_at_unix": prior.started_at_unix,
            "prior_lifetime_s": time.monotonic() - prior.started_at,
            "new_task_id": new_task_id,
            "killed": killed,
        }
        try:
            self._audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._audit_log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row) + "\n")
        except Exception:  # noqa: BLE001 — never block spawn on audit failure
            logger.exception(
                "bounded-spawn: audit append failed (non-fatal) path=%s",
                self._audit_log_path,
            )

    def _emit_alert(
        self,
        prior: SpawnRecord,
        *,
        new_task_id: str,
        killed: bool,
    ) -> None:
        """Fire a structured alert. Fail-open."""
        payload = {
            "alert": "bounded_spawn_violation",
            "severity": "critical",
            "callsign": prior.callsign,
            "prior_task_id": prior.task_id,
            "new_task_id": new_task_id,
            "killed": killed,
            "prior_lifetime_s": time.monotonic() - prior.started_at,
        }
        try:
            self._alerts_emitter(payload)
        except Exception:  # noqa: BLE001 — fail-open
            logger.exception("bounded-spawn: alerts_emitter raised (non-fatal)")


def _default_alert_emitter(payload: dict[str, Any]) -> None:
    """Default alerts go to logger.error so they surface in dispatcher logs.

    Production wiring may inject a Better Stack / Slack relay emitter; this
    default ensures *something* is on the wire even without that injection.
    """
    logger.error("bounded-spawn ALERT: %s", json.dumps(payload, default=str))


__all__ = [
    "DECISION_RECORDED",
    "DECISION_REPEAT_TASK",
    "DECISION_VIOLATION",
    "BoundedSpawnEnforcer",
    "EnforcementResult",
    "SpawnRecord",
]
