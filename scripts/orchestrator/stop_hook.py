#!/usr/bin/env python3
"""scripts/orchestrator/stop_hook.py — Continuous-operation Stop hook.

Fires on Claude Code Stop events (model finished its turn → agent idle).
Reads the next unblocked bd task for this callsign, writes a dispatch JSON
to /tmp/telegram-relay-<callsign>/inbox/ so the agent picks it up on resume.

STRUCTURAL BAR — RUNTIME-ENFORCED (per ceo:rule:continuous_operation_hooks):
This script's `_safe_run` and `_safe_write` helpers scan every subprocess
argv and every JSON/text payload against FORBIDDEN_TOKENS before executing
or writing. A match raises StructuralBarViolation BEFORE the call lands.

Forbidden surface (all attestation/merge paths):
  - `gh pr merge`
  - any payload referencing `gate_proof_runs`
  - any payload setting `status='proven'` (in any quote style)
  - any `attest(` / `attest_` symbol

This is NOT a comment-only bar (GOV-12). Tests under
tests/scripts/orchestrator/test_stop_hook.py exercise the negative path.

Failure path: every uncaught exception is logged to /tmp/stop-hook-error.log
and posted to #ceo via slack_relay.py. The hook always exits 0 — a hook
failure must never block the Claude Code agent from stopping cleanly.

Dedup: if the same bd task_id was last dispatched within DEDUP_WINDOW_SEC
(default 300s/5min), the new fire is treated as a stall — counter bumps;
at >=STALL_THRESHOLD it escalates via _alert_failure.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CALLSIGN = (os.environ.get("CALLSIGN") or "").strip().lower()

ERROR_LOG = Path("/tmp/stop-hook-error.log")
DEDUP_FILE = Path("/tmp/stop-hook-last-dispatch.json")
SLACK_RELAY = Path("/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py")
BD_BIN = os.environ.get("AGENCY_OS_BD_BIN") or str(Path.home() / ".local" / "bin" / "bd")

DEDUP_WINDOW_SEC = 300
STALL_THRESHOLD = 3

FORBIDDEN_TOKENS: tuple[str, ...] = (
    "gh pr merge",
    "status='proven'",
    'status="proven"',
    "status=proven",
    "gate_proof_runs",
    "attest(",
    "attest_",
)


class StructuralBarViolation(RuntimeError):
    """Raised when the hook would perform a forbidden attestation/merge op."""


def _assert_no_forbidden(payload: str, where: str) -> None:
    """Scan `payload` for FORBIDDEN_TOKENS — raise on first match."""
    lowered = payload  # tokens are exact (case-sensitive) by design
    for token in FORBIDDEN_TOKENS:
        if token in lowered:
            raise StructuralBarViolation(
                f"forbidden token {token!r} in {where}: "
                "stop_hook is structurally barred from attestation/merge ops"
            )


def _safe_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """subprocess.run with a forbidden-token guard on the joined argv."""
    _assert_no_forbidden(" ".join(cmd), f"subprocess argv ({cmd[0] if cmd else '?'})")
    return subprocess.run(cmd, **kwargs)


def _safe_write(path: Path, payload: str) -> None:
    """Path.write_text with a forbidden-token guard on the payload."""
    _assert_no_forbidden(payload, f"file write to {path}")
    path.write_text(payload)


def _alert_failure(msg: str) -> None:
    """Loud failure: error log + Slack #ceo. Never raises."""
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"{ts} [{CALLSIGN or '?'}] stop_hook: {msg}\n"
    with contextlib.suppress(Exception), ERROR_LOG.open("a") as fh:
        fh.write(line)
    if SLACK_RELAY.exists():
        with contextlib.suppress(Exception):
            subprocess.run(
                [
                    "python3",
                    str(SLACK_RELAY),
                    "-c",
                    "ceo",
                    f"stop_hook[{CALLSIGN or '?'}]: {msg}",
                ],
                timeout=10,
                check=False,
            )


def _load_dedup() -> dict:
    if not DEDUP_FILE.exists():
        return {}
    try:
        data = json.loads(DEDUP_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _save_dedup(state: dict) -> None:
    try:
        DEDUP_FILE.write_text(json.dumps(state))
    except Exception as e:  # noqa: BLE001
        _alert_failure(f"could not persist dedup file: {e!r}")


def _is_recent_dup(task_id: str, *, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    state = _load_dedup()
    last_ts = (state.get("last") or {}).get(task_id)
    if not isinstance(last_ts, (int, float)):
        return False
    return (now - last_ts) < DEDUP_WINDOW_SEC


def _bump_stall(task_id: str) -> int:
    state = _load_dedup()
    counts = state.setdefault("counts", {})
    counts[task_id] = int(counts.get(task_id, 0)) + 1
    _save_dedup(state)
    return counts[task_id]


def _reset_stall(task_id: str) -> None:
    state = _load_dedup()
    counts = state.get("counts") or {}
    if task_id in counts:
        del counts[task_id]
        state["counts"] = counts
        _save_dedup(state)


def _record_dispatch(task_id: str, *, now: float | None = None) -> None:
    now = time.time() if now is None else now
    state = _load_dedup()
    last = state.setdefault("last", {})
    last[task_id] = now
    cutoff = now - DEDUP_WINDOW_SEC * 4
    state["last"] = {k: v for k, v in last.items() if isinstance(v, (int, float)) and v > cutoff}
    _save_dedup(state)


def _bd_ready_top() -> dict | None:
    """Read-only bd query — never writes. Returns top task or None."""
    if not CALLSIGN:
        return None
    try:
        r = _safe_run(
            [BD_BIN, "ready", "--json", "--limit", "1", "--callsign", CALLSIGN],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        _alert_failure(f"bd ready failed: {e!r}")
        return None
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return None
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def _write_dispatch(task: dict) -> Path:
    task_id = str(task.get("id") or "unknown")
    title = str(task.get("title") or "")
    inbox = Path(f"/tmp/telegram-relay-{CALLSIGN}/inbox")
    inbox.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    fname = inbox / f"stop_hook_dispatch_{task_id}_{ts}.json"
    payload = {
        "type": "task_dispatch",
        "from": "stop_hook",
        "to": CALLSIGN,
        "subject": f"Continuous-op dispatch ({task_id})",
        "brief": (
            f"You completed your last turn idle. Next unblocked bd task: {task_id}. "
            f"Title: {title}. Run `bd show {task_id}` for full spec, then `bd claim "
            f"{task_id}` to start. Structural bar: stop_hook did NOT attest, merge, "
            "or write proven status."
        ),
        "task_ref": task_id,
        "max_task_minutes": 30,
    }
    body = json.dumps(payload, indent=2)
    _safe_write(fname, body)
    return fname


def main() -> int:
    if not CALLSIGN:
        _alert_failure("CALLSIGN env var not set — cannot dispatch")
        return 0
    try:
        task = _bd_ready_top()
        if task is None:
            return 0
        task_id = str(task.get("id") or "").strip()
        if not task_id:
            return 0
        if _is_recent_dup(task_id):
            stall_n = _bump_stall(task_id)
            if stall_n >= STALL_THRESHOLD:
                _alert_failure(
                    f"stall escalation: task {task_id} re-dispatched {stall_n} "
                    f"times within {DEDUP_WINDOW_SEC}s — agent not progressing"
                )
            return 0
        _write_dispatch(task)
        _record_dispatch(task_id)
        _reset_stall(task_id)
    except StructuralBarViolation as e:
        _alert_failure(f"structural bar tripped: {e}")
        return 0
    except Exception as e:  # noqa: BLE001 — hooks must never propagate
        _alert_failure(f"unexpected error: {e!r}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
