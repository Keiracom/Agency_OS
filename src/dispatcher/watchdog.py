"""KEI-211 — Dispatcher Watchdog: liveness probe + hang detection.

Companion to KEI-163 (container_monitor) and KEI-184 (tmux_lifecycle /
container_lifecycle). KEI-163 reaps containers on clean *exit*; this module
detects sessions that are *still running but not progressing* (hung agents,
unresponsive containers) and raises an alert via callback.

Detection model:
- TMUX:      capture-pane output hashed; signature unchanged across
             ``hung_threshold_s`` -> HUNG.
- CONTAINER: GET <health_path> on each poll; non-2xx (or unreachable) for a
             continuous window >= ``hung_threshold_s`` -> HUNG.

Best-effort by design: probe failures never raise out of ``probe_all`` so
this can run in a long-lived supervisor without crashing on a single bad
session. The supervisor's health_snapshot() reports "degraded" when any
entry is HUNG.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import logging
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from src.dispatcher.container_lifecycle import ContainerHandle
from src.dispatcher.tmux_lifecycle import SessionHandle

logger = logging.getLogger(__name__)

DEFAULT_HUNG_THRESHOLD_S = 300.0  # 5 min default
DEFAULT_PROBE_TIMEOUT_S = 2.0
DEFAULT_TMUX_CMD_TIMEOUT_S = 5.0
TMUX_CLI = "tmux"

State = Literal["alive", "hung", "dead"]

AlertFn = Callable[[str, "WatchdogEntry", str], None]
"""Callback signature: (key, entry, reason) -> None. Called on transition
to HUNG. Caller routes to TG/Slack/PagerDuty as appropriate."""


@dataclass
class WatchdogEntry:
    """Tracked session/container state. Mutated in place by probes."""

    handle: SessionHandle | ContainerHandle
    hung_threshold_s: float = DEFAULT_HUNG_THRESHOLD_S
    last_signature: str = ""
    last_progress_at: float = 0.0  # monotonic
    state: State = "alive"
    consecutive_unhealthy_since: float | None = None  # monotonic; CONTAINER only


def _capture_tmux_pane(session_name: str) -> str | None:
    """Return the pane content, or None on error.

    Errors (tmux missing, session gone, timeout) are swallowed and reported
    as None so the watchdog can keep polling other entries.
    """
    try:
        result = subprocess.run(  # noqa: S603  # controlled args
            [TMUX_CLI, "capture-pane", "-t", session_name, "-p"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_TMUX_CMD_TIMEOUT_S,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.debug("watchdog capture-pane(%s) failed: %s", session_name, exc)
        return None
    if result.returncode != 0:
        # Session gone -> caller treats as DEAD upstream
        return None
    return result.stdout


def _hash_pane(pane: str) -> str:
    return hashlib.sha256(pane.encode("utf-8", errors="replace")).hexdigest()


def _probe_http_health(host: str, port: int, path: str) -> bool:
    """Return True iff GET responds 2xx within DEFAULT_PROBE_TIMEOUT_S."""
    conn: http.client.HTTPConnection | None = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=DEFAULT_PROBE_TIMEOUT_S)
        conn.request("GET", path)
        resp = conn.getresponse()
        ok = 200 <= resp.status < 300
        resp.read()
        return ok
    except (OSError, http.client.HTTPException):
        return False
    finally:
        if conn is not None:
            with contextlib.suppress(OSError):
                conn.close()


class Watchdog:
    """Periodic liveness sweeper across registered sessions/containers.

    Usage::

        wd = Watchdog(alert_fn=my_alert)
        wd.register("orion-task-42", session_handle)
        wd.register("tenant-7-container", container_handle, hung_threshold_s=120)
        # in a supervisor loop:
        wd.probe_all()
        snapshot = wd.health_snapshot()
    """

    def __init__(
        self,
        *,
        alert_fn: AlertFn | None = None,
        container_host: str = "127.0.0.1",
    ) -> None:
        self._entries: dict[str, WatchdogEntry] = {}
        self._alert: AlertFn = alert_fn or (lambda _k, _e, _r: None)
        self._container_host = container_host

    # ------------------------------------------------------------------
    # registry
    # ------------------------------------------------------------------

    def register(
        self,
        key: str,
        handle: SessionHandle | ContainerHandle,
        *,
        hung_threshold_s: float = DEFAULT_HUNG_THRESHOLD_S,
    ) -> None:
        """Track ``handle`` under ``key``. Re-registering resets progress."""
        now = time.monotonic()
        self._entries[key] = WatchdogEntry(
            handle=handle,
            hung_threshold_s=hung_threshold_s,
            last_progress_at=now,
            state="alive",
        )

    def unregister(self, key: str) -> None:
        self._entries.pop(key, None)

    @property
    def tracked(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # probes
    # ------------------------------------------------------------------

    def _probe_tmux(self, entry: WatchdogEntry) -> State:
        handle = entry.handle
        assert isinstance(handle, SessionHandle)
        pane = _capture_tmux_pane(handle.session_name)
        if pane is None:
            entry.state = "dead"
            return "dead"
        sig = _hash_pane(pane)
        now = time.monotonic()
        if sig != entry.last_signature:
            entry.last_signature = sig
            entry.last_progress_at = now
            entry.state = "alive"
            return "alive"
        if (now - entry.last_progress_at) >= entry.hung_threshold_s:
            entry.state = "hung"
            return "hung"
        return "alive"

    def _probe_container(self, entry: WatchdogEntry) -> State:
        handle = entry.handle
        assert isinstance(handle, ContainerHandle)
        ok = _probe_http_health(self._container_host, handle.port, handle.health_path)
        now = time.monotonic()
        if ok:
            entry.last_progress_at = now
            entry.consecutive_unhealthy_since = None
            entry.state = "alive"
            return "alive"
        # Not OK — start or continue the unhealthy window.
        if entry.consecutive_unhealthy_since is None:
            entry.consecutive_unhealthy_since = now
        elapsed = now - entry.consecutive_unhealthy_since
        if elapsed >= entry.hung_threshold_s:
            entry.state = "hung"
            return "hung"
        return "alive"

    def probe_one(self, key: str) -> State:
        """Probe one entry; mutate its state; fire alert on transition to HUNG.

        Returns the new state. Unknown ``key`` -> "dead" (no entry to track).
        """
        entry = self._entries.get(key)
        if entry is None:
            return "dead"
        prev = entry.state
        if isinstance(entry.handle, SessionHandle):
            new = self._probe_tmux(entry)
        else:
            new = self._probe_container(entry)
        if new == "hung" and prev != "hung":
            reason = self._format_reason(entry)
            logger.warning("KEI-211 watchdog HUNG %s — %s", key, reason)
            with contextlib.suppress(Exception):
                self._alert(key, entry, reason)
        return new

    def probe_all(self) -> dict[str, State]:
        """Probe every registered entry. Errors are swallowed per-entry."""
        results: dict[str, State] = {}
        for key in list(self._entries):
            try:
                results[key] = self.probe_one(key)
            except Exception as exc:  # noqa: BLE001 — must not crash the sweep
                logger.exception("KEI-211 watchdog probe_one(%s) raised: %s", key, exc)
                results[key] = "dead"
        return results

    @staticmethod
    def _format_reason(entry: WatchdogEntry) -> str:
        elapsed = time.monotonic() - entry.last_progress_at
        if isinstance(entry.handle, SessionHandle):
            return (
                f"tmux session {entry.handle.session_name!r} pane unchanged "
                f"for {elapsed:.0f}s (threshold {entry.hung_threshold_s:.0f}s)"
            )
        return (
            f"container {entry.handle.id[:12]} /healthz unhealthy "
            f"for {elapsed:.0f}s (threshold {entry.hung_threshold_s:.0f}s)"
        )

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------

    def health_snapshot(self) -> dict[str, object]:
        """Status block for the dispatcher health endpoint.

        ``status`` is "green" when no entry is HUNG/DEAD, otherwise "degraded".
        """
        hung = sum(1 for e in self._entries.values() if e.state == "hung")
        dead = sum(1 for e in self._entries.values() if e.state == "dead")
        status = "green" if (hung == 0 and dead == 0) else "degraded"
        return {
            "component": "watchdog",
            "status": status,
            "tracked": len(self._entries),
            "hung": hung,
            "dead": dead,
        }
