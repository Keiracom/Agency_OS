#!/usr/bin/env python3
"""hook_failure_monitor.py — KEI-11 Outcome 3: PostToolUse/Stop hook failures
alert #execution within 5 min.

Per Linear KEI-11 outcome 3:
  "Hook failure alerting — PostToolUse/Stop hook failures alert #execution
   within 5 min"

Existing Claude Code hook scripts under .claude/hooks/ are fail-open: they
log crashes to stderr-redirected log files but never alert. This monitor
sweeps the hook log directories on a 5-min cadence and posts one Slack
alert per (log_file, callsign) breach per dedupe window.

Watched log directories (matched against .claude/hooks/session_store_*.sh
+ recorder_hook.sh):
    /tmp/agency-os-session-store/   ← session_store_{stop,posttooluse,userpromptsubmit}.sh
    /tmp/agency-os-recorder/        ← recorder_hook.sh

A "failure" is detected as either:
  a) Any *.err file with mtime in the last MTIME_WINDOW_SECONDS that has
     grown since the last sweep (tracked by byte-count in state file).
  b) Any *.log file containing the substring "ERROR" / "Traceback" /
     "failed:" in lines appended since the last sweep.

Best-effort: a Slack-post failure does NOT raise.

Wires via timer: infra/alerts/agency-os-hook-failure-monitor.timer
(OnCalendar *:0/5 — matches the KEI-11 "within 5 min" SLA).
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("hook_failure_monitor")

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
DEFAULT_STATE_PATH = Path("/tmp/agency-os-hook-failure-state.json")
MTIME_WINDOW_SECONDS = 300  # 5 minutes
DEDUPE_WINDOW_SECONDS = 300
TAIL_LINES = 10

WATCHED_DIRS: tuple[Path, ...] = (
    Path("/tmp/agency-os-session-store"),
    Path("/tmp/agency-os-recorder"),
)

ERROR_PATTERN = re.compile(r"(ERROR|Traceback|failed:|crashed)", re.IGNORECASE)


def callsign_from_log_path(path: Path) -> str:
    """Best-effort callsign extraction. Session-store logs are global per box;
    we surface the worktree the *current* monitor is running from as a hint."""
    cs = os.environ.get("CALLSIGN", "").strip().lower()
    return cs or "unknown"


def hook_name_from_log_path(path: Path) -> str:
    """e.g. /tmp/agency-os-session-store/posttooluse.log → 'posttooluse'."""
    return path.stem


def load_state(state_path: Path) -> dict[str, dict]:
    """{state_key: {bytes_seen: int, last_alerted_iso: str}}."""
    if not state_path.is_file():
        return {}
    try:
        return json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("state file unreadable, treating as empty: %s", exc)
        return {}


def save_state(state_path: Path, state: dict[str, dict]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True))


def file_grew_since(path: Path, bytes_seen: int) -> tuple[bool, int]:
    """Return (grew, current_size). current_size 0 if missing."""
    if not path.is_file():
        return False, 0
    try:
        size = path.stat().st_size
    except OSError:
        return False, 0
    return size > bytes_seen, size


def read_new_lines(path: Path, byte_offset: int) -> str:
    """Read bytes from offset to EOF as utf-8. Empty string on any failure."""
    if not path.is_file():
        return ""
    try:
        with path.open("rb") as fh:
            fh.seek(byte_offset)
            data = fh.read()
        return data.decode("utf-8", errors="replace")
    except OSError as exc:
        logger.warning("read_new_lines %s failed: %s", path, exc)
        return ""


def tail_lines(text: str, n: int = TAIL_LINES) -> list[str]:
    lines = text.splitlines()
    return lines[-n:] if len(lines) > n else lines


def is_recently_modified(
    path: Path, *, now: datetime, window_seconds: int = MTIME_WINDOW_SECONDS
) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except OSError:
        return False
    return (now - mtime).total_seconds() <= window_seconds


def scan_log_dir(log_dir: Path, state: dict[str, dict], *, now: datetime) -> list[dict]:
    """Return list of {state_key, log_path, severity, sample_lines, bytes_now}
    for files that show new error-ish content since the last sweep."""
    if not log_dir.is_dir():
        return []
    findings: list[dict] = []
    for p in sorted(log_dir.iterdir()):
        if not p.is_file():
            continue
        # Only watch .err + .log files — covers stderr redirects + appended logs.
        if p.suffix not in (".err", ".log"):
            continue
        # Skip files that haven't been touched recently.
        if not is_recently_modified(p, now=now):
            continue
        state_key = str(p)
        prior_bytes = state.get(state_key, {}).get("bytes_seen", 0)
        grew, current = file_grew_since(p, prior_bytes)
        if not grew:
            continue
        new_text = read_new_lines(p, prior_bytes)
        # .err files surface as failures unconditionally (any new stderr =
        # something printed to stderr-redirected hook log). .log files only
        # surface when new lines contain an error pattern.
        if p.suffix == ".err":
            severity = "stderr"
        else:
            if not ERROR_PATTERN.search(new_text):
                # Update bytes_seen even if no error — avoids re-scanning the
                # same clean lines forever.
                state.setdefault(state_key, {})["bytes_seen"] = current
                continue
            severity = "error_pattern"
        findings.append(
            {
                "state_key": state_key,
                "log_path": str(p),
                "severity": severity,
                "sample_lines": tail_lines(new_text),
                "bytes_now": current,
            }
        )
    return findings


def should_alert(state_key: str, state: dict[str, dict], *, now: datetime) -> bool:
    last = state.get(state_key, {}).get("last_alerted_iso")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True
    return (now - last_dt).total_seconds() >= DEDUPE_WINDOW_SECONDS


def format_alert(findings: list[dict], callsign: str) -> str:
    lines = [
        f":rotating_light: *Claude Code hook failure* — {len(findings)} hook log(s) "
        f"with new errors (callsign=`{callsign}`, last {MTIME_WINDOW_SECONDS}s)"
    ]
    for f in findings:
        hook = hook_name_from_log_path(Path(f["log_path"]))
        lines.append(f"\n  *{hook}* (`{f['log_path']}`, severity={f['severity']})")
        for line in f["sample_lines"]:
            if line.strip():
                lines.append(f"    `{line}`")
    lines.append(
        f"\n_KEI-11 outcome 3 enforcement. Dedupe window: {DEDUPE_WINDOW_SECONDS}s per (log_file)._"
    )
    return "\n".join(lines)


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post hook-failure alert")
        return False
    payload = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "HookFailureMonitor",
            "icon_emoji": ":x:",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            return bool(body.get("ok"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Slack post failed: %s", exc)
        return False


def run_once(
    state_path: Path | None = None,
    *,
    watched_dirs: tuple[Path, ...] | None = None,
    post_fn=None,
    now: datetime | None = None,
) -> dict:
    """One sweep. Returns {dirs_scanned, findings, alerted}."""
    state_path = state_path or DEFAULT_STATE_PATH
    watched = watched_dirs or WATCHED_DIRS
    post_fn = post_fn or post_to_slack
    now = now or datetime.now(UTC)

    state = load_state(state_path)
    all_findings: list[dict] = []
    for d in watched:
        all_findings.extend(scan_log_dir(d, state, now=now))

    to_alert = [f for f in all_findings if should_alert(f["state_key"], state, now=now)]

    alerted_count = 0
    if to_alert:
        callsign = os.environ.get("CALLSIGN", "unknown").lower() or "unknown"
        posted = post_fn(format_alert(to_alert, callsign))
        if posted:
            alerted_count = len(to_alert)
            for f in to_alert:
                entry = state.setdefault(f["state_key"], {})
                entry["bytes_seen"] = f["bytes_now"]
                entry["last_alerted_iso"] = now.isoformat()

    # Even rows we didn't alert on (e.g. dedupe-suppressed) should still
    # advance bytes_seen so we don't re-read the same lines next sweep.
    for f in all_findings:
        entry = state.setdefault(f["state_key"], {})
        entry["bytes_seen"] = f["bytes_now"]

    save_state(state_path, state)

    return {
        "dirs_scanned": len(watched),
        "findings": len(all_findings),
        "alerted": alerted_count,
    }


def main() -> int:
    summary = run_once()
    logger.info("hook_failure_monitor: %s", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
