#!/usr/bin/env python3
"""KEI-93 — Dave-triggered fleet-restart handler (Phase 0.5, KEI-140 part c).

Polls Slack #ceo for messages from Dave matching `^reset all$` (case-insensitive,
trim, with optional `[CEO]` relay prefix stripped). On match:
  1. Post `[SYSTEM] Fleet reset initiated by Dave. Restarting agents...` to #ceo.
  2. systemctl --user restart on the 5 agent units (aiden/atlas/max/orion/scout)
     in parallel; wait 30s for ExecStartPre to settle (Atlas KEI-140 a+b).
  3. systemctl --user restart elliot-agent LAST.
  4. Per-agent health probe (tmux session alive, cognee context mtime <60s,
     self-claim loop active, Gate 4 outcome counter recent).
  5. Aggregated report to #ceo within 5min: per-agent 4-bullet status + headline.

Cooldown: 60s between consecutive `reset all` triggers to prevent double-fire.
Cooldown state is persisted to a lockfile so a systemd Restart=always does not
reset the in-memory timer.

Security: only `sender == 'U091TGTPB9U'` (Dave's Slack user_id) triggers.

Runtime paths:
  Lockfile + cognee-context sentinel files live under
  $AGENCY_OS_RUNTIME_DIR (default /run/user/1001/agency-os).
  The cognee signal in health_probe reads from the same directory.
  NOTE: cognee_session_start.py currently writes to /tmp via
  tempfile.gettempdir(). Until KEI-107 migrates that script to the runtime
  dir, the `cognee` health signal will return False for all callsigns. The
  health probe degrades gracefully — other three signals still report.

Env (loaded from /home/elliotbot/.config/agency-os/.env via the systemd unit):
  SLACK_BOT_TOKEN        — xoxb-… for channels.history + chat.postMessage.
  AGENCY_OS_RUNTIME_DIR  — override for lockfile + cognee-context paths
                           (default /run/user/1001/agency-os).
  DATABASE_URL           — Postgres DSN for heartbeat ceo_memory queries
                           (optional; Gate 4 degrades to is-active if absent).
"""

from __future__ import annotations

import contextlib
import logging
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger("reset_all_handler")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CEO_CHANNEL_ID = "C0B2PM3TV0B"
DAVE_USER_ID = "U091TGTPB9U"
RESET_RE = re.compile(r"^(?:\[CEO\][:\s]*)?reset all\s*$", re.IGNORECASE)
AGENTS = ("aiden", "atlas", "max", "orion", "scout")
ELLIOT_LAST = "elliot"
POLL_SECONDS = 5
COOLDOWN_SECONDS = 60
SLACK_API = "https://slack.com/api"

_TRIGGER_LOCK = threading.Lock()


def _runtime_dir() -> Path:
    """Return the agency-os runtime directory, creating it if needed."""
    path = Path(os.environ.get("AGENCY_OS_RUNTIME_DIR", "/run/user/1001/agency-os"))
    with contextlib.suppress(OSError):
        path.mkdir(parents=True, exist_ok=True)
    return path


def _lockfile_path() -> Path:
    return _runtime_dir() / "reset-all-handler.lock"


def _read_last_trigger() -> float:
    """Read persisted last_trigger epoch from lockfile; return 0.0 on missing/error."""
    p = _lockfile_path()
    try:
        return float(p.read_text().strip())
    except (OSError, ValueError):
        return 0.0


def _write_last_trigger(ts: float) -> None:
    """Atomically write last_trigger epoch to lockfile via tmp+rename."""
    p = _lockfile_path()
    dir_ = p.parent
    try:
        fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".reset-lock-")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(str(ts))
        except Exception:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
        os.replace(tmp, p)
    except OSError as exc:
        logger.warning("could not write lockfile %s: %s", p, exc)


def _dsn() -> str | None:
    return os.environ.get("DATABASE_URL")


def matches_reset(sender: str, text: str) -> bool:
    if sender != DAVE_USER_ID:
        return False
    return RESET_RE.match((text or "").strip()) is not None


def fetch_recent(token: str, oldest_ts: str | None) -> list[dict]:
    params = {"channel": CEO_CHANNEL_ID, "limit": "20"}
    if oldest_ts:
        params["oldest"] = oldest_ts
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{SLACK_API}/conversations.history", params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
    if not payload.get("ok"):
        logger.warning("Slack history failed: %s", payload)
        return []
    return list(payload.get("messages") or [])


def post(token: str, text: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{SLACK_API}/chat.postMessage",
                headers=headers,
                json={"channel": CEO_CHANNEL_ID, "text": text},
            )
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("Slack post failed: %s", exc)


def _relay_outcome_healthy(callsign: str) -> bool:
    """Gate 4: check KEI-91 heartbeat outcome counter in ceo_memory.

    Reads ceo_memory['heartbeat:relay-watcher-<callsign>'] jsonb and checks
    that last_tick_at is within the last 60s AND outcome_count > 0.
    Falls back to systemctl is-active on DB error with a warning.
    """
    dsn = _dsn()
    if dsn:
        try:
            import psycopg  # type: ignore[import-untyped]

            key = f"heartbeat:relay-watcher-{callsign}"
            with psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn:
                row = conn.execute(
                    "SELECT value FROM public.ceo_memory WHERE key = %s LIMIT 1", (key,)
                ).fetchone()
            if row is not None:
                data = row[0] if isinstance(row[0], dict) else {}
                last_tick = data.get("last_tick_at")
                outcome_count = int(data.get("outcome_count", 0))
                if last_tick is not None:
                    # last_tick_at may be epoch float or ISO string
                    if isinstance(last_tick, (int, float)):
                        age = time.time() - float(last_tick)
                    else:
                        import datetime

                        dt = datetime.datetime.fromisoformat(str(last_tick))
                        age = time.time() - dt.timestamp()
                    return age < 60 and outcome_count > 0
            # key not found — service not yet registered
            return False
        except Exception as exc:
            logger.warning(
                "relay_outcome_healthy(%s): DB read failed (%s); falling back to is-active",
                callsign,
                exc,
            )
    # degraded path: liveness only
    result = subprocess.run(
        ["systemctl", "--user", "is-active", f"relay-watcher-{callsign}.service"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def health_probe(callsign: str) -> dict[str, bool]:
    """Return 4-signal health dict for *callsign*.

    Signal paths:
      tmux      — tmux has-session -t <callsign>:0.0
      cognee    — $AGENCY_OS_RUNTIME_DIR/cognee-context-<callsign>.md mtime <60s.
                  NOTE: cognee_session_start.py currently writes to /tmp (via
                  tempfile.gettempdir()). Until KEI-107 migrates that script to
                  $AGENCY_OS_RUNTIME_DIR, this signal will always be False.
      self_claim — systemctl is-active agent-self-claim-loop@<callsign>.service
      relay     — KEI-91 heartbeat outcome counter via _relay_outcome_healthy()
    """
    tmux_alive = (
        subprocess.run(
            ["tmux", "has-session", "-t", f"{callsign}:0.0"], capture_output=True, check=False
        ).returncode
        == 0
    )
    cognee_path = _runtime_dir() / f"cognee-context-{callsign}.md"
    cognee_fresh = cognee_path.exists() and (time.time() - cognee_path.stat().st_mtime) < 60
    self_claim = (
        subprocess.run(
            ["systemctl", "--user", "is-active", f"agent-self-claim-loop@{callsign}.service"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    relay_active = _relay_outcome_healthy(callsign)
    return {
        "tmux": tmux_alive,
        "cognee": cognee_fresh,
        "self_claim": self_claim,
        "relay": relay_active,
    }


def _restart_agent(cs: str) -> None:
    """Restart <cs>-agent.service and log any failure."""
    result = subprocess.run(
        ["systemctl", "--user", "restart", f"{cs}-agent.service"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace").strip()
        logger.warning("restart %s-agent.service rc=%d stderr=%s", cs, result.returncode, stderr)


def trigger_reset(token: str) -> None:
    """Execute the full fleet reset sequence (runs in a daemon thread)."""
    post(token, "[SYSTEM] Fleet reset initiated by Dave. Restarting agents...")
    for cs in AGENTS:
        _restart_agent(cs)
    time.sleep(30)
    _restart_agent(ELLIOT_LAST)
    time.sleep(15)
    report_lines: list[str] = []
    healthy = 0
    for cs in (*AGENTS, ELLIOT_LAST):
        h = health_probe(cs)
        marks = " ".join(f"{k}={'✓' if v else '✗'}" for k, v in h.items())
        report_lines.append(f"- {cs}: {marks}")
        if all(h.values()):
            healthy += 1
    headline = f"[SYSTEM] Fleet reset complete. {healthy} of 6 agents healthy."
    post(token, headline + "\n" + "\n".join(report_lines))


@dataclass
class _PollState:
    last_seen_ts: str | None = None
    last_trigger: float = field(default_factory=_read_last_trigger)


def _poll_iteration(token: str, state: _PollState) -> None:
    """Single poll iteration: fetch messages, update state, fire reset if matched."""
    messages = fetch_recent(token, state.last_seen_ts)
    for m in messages:
        ts = m.get("ts", "")
        if ts and (state.last_seen_ts is None or ts > state.last_seen_ts):
            state.last_seen_ts = ts
        if matches_reset(m.get("user", ""), m.get("text", "")):
            if time.time() - state.last_trigger < COOLDOWN_SECONDS:
                logger.info("cooldown: skipping reset all (ts=%s)", ts)
                continue
            now = time.time()
            state.last_trigger = now
            _write_last_trigger(now)
            logger.info("reset all triggered by Dave at ts=%s", ts)
            if _TRIGGER_LOCK.acquire(blocking=False):
                threading.Thread(
                    target=_run_trigger_with_lock,
                    args=(token,),
                    daemon=True,
                ).start()
            else:
                logger.info("trigger_reset already running; skipping overlapping trigger")


def _run_trigger_with_lock(token: str) -> None:
    """Wrapper that releases _TRIGGER_LOCK after trigger_reset completes."""
    try:
        trigger_reset(token)
    finally:
        _TRIGGER_LOCK.release()


def main() -> int:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.error("SLACK_BOT_TOKEN not set")
        return 2
    state = _PollState(last_seen_ts=str(time.time()))
    while True:
        try:
            _poll_iteration(token, state)
        except Exception as exc:
            logger.warning("poll iteration failed: %s", exc)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
