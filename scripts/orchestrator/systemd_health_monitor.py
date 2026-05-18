#!/usr/bin/env python3
"""KEI-141 — systemd service health monitor.

Polls `systemctl --user list-units --state=failed --no-legend` every 30s
(via the .timer below) for failed Agency_OS fleet units. Posts a #ceo
alert via the `tg` CLI on first detection of each failure; dedups
subsequent cycles via an on-disk state file so we don't spam alerts.

When a previously-failed unit returns to 'active', clears it from
the state file (and posts a #ceo recovery note).

Fleet patterns monitored (all matched against `systemctl --user
list-units --all` output, NOT hardcoded — picks up new units automatically):
  - *-agent.service          (agent services)
  - *-indexer.service        (Weaviate indexers)
  - *-watcher.service        (relay watchers)
  - central-listener.service (Slack relay listener)
  - fleet-supervisor.service (the supervisor itself)

NOT in scope this PR:
  - Restart-loop cap via StartLimitBurst/StartLimitIntervalSec on each
    unit file — that's Atlas's unit-files lane; file as KEI-141-followup.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("systemd_health_monitor")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Reasonable defaults; overridable via env for testing
DEFAULT_STATE_PATH = Path(
    os.environ.get(
        "HEALTH_MONITOR_STATE",
        "/home/elliotbot/clawd/logs/systemd_health_state.json",
    )
)
DEFAULT_TG_CLI = os.environ.get("HEALTH_MONITOR_TG_CLI", "/home/elliotbot/.local/bin/tg")
SYSTEMCTL = "systemctl"

# Patterns we care about — anything matching one of these globs is in fleet scope
FLEET_PATTERNS = (
    "*-agent.service",
    "*-indexer.service",
    "*-watcher.service",
    "central-listener.service",
    "fleet-supervisor.service",
)


def _matches_fleet(name: str) -> bool:
    return any(fnmatch.fnmatch(name, pattern) for pattern in FLEET_PATTERNS)


def _run_systemctl(extra_args: list[str]) -> list[str]:
    """Run systemctl --user with extra_args; return stdout lines.

    Raises FileNotFoundError if systemctl is absent (config error → exit 2).
    Returns [] on any other subprocess error (fail-open per monitor discipline).
    """
    cmd = [SYSTEMCTL, "--user", "--no-legend", "--plain", "--all"] + extra_args
    try:
        result = subprocess.run(  # noqa: S603 — controlled args, no shell
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.stdout.splitlines()
    except FileNotFoundError:
        raise
    except Exception as exc:  # noqa: BLE001 — fail-open per monitor discipline
        logger.warning("systemctl invocation error — fail-open: %s", exc)
        return []


def list_failed_units() -> list[str]:
    """Return names of fleet units currently in failed state.

    Uses systemctl --user list-units --state=failed --no-legend --plain --all
    + fnmatch filter against FLEET_PATTERNS.
    """
    lines = _run_systemctl(["list-units", "--state=failed"])
    names: list[str] = []
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        if _matches_fleet(name):
            names.append(name)
    return names


def list_active_units() -> list[str]:
    """Return names of fleet units currently in active state.

    Used for recovery detection — checks which previously-failed units are
    now healthy.
    """
    lines = _run_systemctl(["list-units", "--state=active"])
    names: list[str] = []
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        if _matches_fleet(name):
            names.append(name)
    return names


def load_state(path: Path) -> dict:
    """Load on-disk state file. Returns {} on missing/malformed."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 — fail-open per monitor discipline
        logger.warning("load_state: failed to read %s — returning empty: %s", path, exc)
        return {}


def save_state(path: Path, state: dict) -> None:
    """Best-effort save. Logs on failure but doesn't raise."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2))
    except Exception as exc:  # noqa: BLE001 — fail-open per monitor discipline
        logger.warning("save_state: failed to write %s: %s", path, exc)


def post_alert(tg_cli: str, message: str) -> bool:
    """Run `tg -c ceo <message>` via subprocess. Returns True on success.

    Logs warning and returns False on any error — never raises (fail-open
    so monitor keeps running even if tg breaks).
    """
    try:
        result = subprocess.run(  # noqa: S603 — controlled args, no shell
            [tg_cli, "-c", "ceo", message],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "post_alert: tg returned rc=%d — stderr: %s",
                result.returncode,
                result.stderr.strip(),
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001 — fail-open per monitor discipline
        logger.warning("post_alert: tg invocation failed: %s", exc)
        return False


def _derive_callsign(unit: str) -> str:
    """Derive a human-readable callsign from unit name.

    <callsign>-agent.service → <callsign>
    All other patterns      → "system"
    """
    if unit.endswith("-agent.service"):
        return unit[: -len("-agent.service")]
    return "system"


def detect_changes(
    failed_now: list[str],
    active_now: list[str],
    previously_failed: list[str],
) -> tuple[list[str], list[str]]:
    """Return (newly_failed, recovered) for alert generation.

    - newly_failed: in failed_now AND NOT in previously_failed
    - recovered:    in active_now AND in previously_failed
    """
    failed_now_set = set(failed_now)
    active_now_set = set(active_now)
    prev_set = set(previously_failed)

    newly_failed = sorted(failed_now_set - prev_set)
    recovered = sorted(active_now_set & prev_set)
    return newly_failed, recovered


def main(argv: list[str] | None = None) -> int:
    """One-shot run. systemd timer invokes every 30s.

    Flow:
      1. List failed + active fleet units now.
      2. Load previously-failed state.
      3. Detect newly-failed (alert with 🚨) and recovered (alert with ✅).
      4. Save new state = currently-failed.
      5. Exit 0 unless DETECTOR itself errored (systemctl not present etc.)
         — fail-open on alert failure (logged).
    """
    parser = argparse.ArgumentParser(description="KEI-141 systemd health monitor")
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to on-disk dedup state file",
    )
    parser.add_argument(
        "--tg-cli",
        default=DEFAULT_TG_CLI,
        help="Path to the tg CLI binary",
    )
    args = parser.parse_args(argv)

    ts = _dt.datetime.now(_dt.UTC).isoformat()

    try:
        failed_now = list_failed_units()
        active_now = list_active_units()
    except FileNotFoundError:
        logger.error("systemctl not found — cannot monitor fleet (configuration error)")
        return 2

    state = load_state(args.state)
    previously_failed: list[str] = state.get("failed_units", [])

    newly_failed, recovered = detect_changes(failed_now, active_now, previously_failed)

    for unit in newly_failed:
        callsign = _derive_callsign(unit)
        msg = f"🚨 systemd: {unit} failed (callsign={callsign} at {ts})"
        logger.warning(msg)
        post_alert(args.tg_cli, msg)

    for unit in recovered:
        msg = f"✅ systemd: {unit} recovered"
        logger.info(msg)
        post_alert(args.tg_cli, msg)

    save_state(args.state, {"failed_units": failed_now, "updated_at": ts})

    logger.info(
        "scan complete — failed=%d newly_failed=%d recovered=%d",
        len(failed_now),
        len(newly_failed),
        len(recovered),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
