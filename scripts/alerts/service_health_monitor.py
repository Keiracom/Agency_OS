#!/usr/bin/env python3
"""service_health_monitor.py — 5-min systemd timer health check.

Per Dave System Health Monitoring directive 2026-05-12 Outcome 1.

Checks the systemd --user services that comprise the Slack listener +
per-callsign relay infrastructure. Any service in non-active state →
post to #execution with service name, callsign, state, and last log lines.

Best-effort: a Slack-post failure does NOT raise. The monitor's job is
liveness reporting; failures in reporting must not cascade into restart
loops.

Run via timer: agency-os-service-health-monitor.timer (OnCalendar *:0/5).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("service_health_monitor")

# Services that comprise the Slack listener + per-callsign relay infrastructure.
# Refreshed 2026-05-20 to the live fleet-comms units: the legacy
# *-relay-watcher / agency-os-slack-central-listener names were removed when
# the relay layer moved to per-callsign *-inbox-watcher + NATS bridges.
# Edit deliberately when adding new agents / clones.
MONITORED_SERVICES: tuple[str, ...] = (
    "agency-os-elliot-slack-listener",
    "aiden-inbox-watcher",
    "atlas-inbox-watcher",
    "elliot-inbox-watcher",
    "max-inbox-watcher",
    "nova-inbox-watcher",
    "orion-inbox-watcher",
    "scout-inbox-watcher",
    "aiden-nats-review-bridge",
    "atlas-nats-dispatch-bridge",
    "elliot-nats-inbox-bridge",
    "max-nats-review-bridge",
    "nova-nats-dispatch-bridge",
    "orion-nats-dispatch-bridge",
    "scout-nats-dispatch-bridge",
)

# Slack #execution channel ID
EXECUTION_CHANNEL = "C0B3QB0K1GQ"


def systemctl_user(*args: str) -> tuple[int, str]:
    """Run `systemctl --user <args>` and return (returncode, stdout+stderr)."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return 1, f"systemctl invocation failed: {exc}"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def get_service_state(service: str) -> str:
    """Return systemd ActiveState ('active'|'inactive'|'failed'|'unknown')."""
    rc, output = systemctl_user("is-active", service)
    if rc == 0:
        return "active"
    # is-active returns non-zero for inactive/failed/etc; the stdout is the state.
    return (output.strip() or "unknown").splitlines()[0]


def get_recent_log(service: str, n: int = 5) -> str:
    """Last N journal lines for the service. Empty string if unavailable."""
    try:
        result = subprocess.run(
            ["journalctl", "--user", "-u", service, "-n", str(n), "--no-pager"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""
    return (result.stdout or "").strip()


def callsign_from_service_name(service: str) -> str:
    """Best-effort callsign extraction from service name prefix."""
    for cs in ("aiden", "atlas", "max", "nova", "orion", "scout", "elliot"):
        if service.startswith(cs + "-"):
            return cs
    return "central"  # agency-os-elliot-slack-listener has no bare callsign prefix


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    """Best-effort Slack post. Returns True on success, False otherwise.

    Reads SLACK_BOT_TOKEN from env. No retry, no exception propagation.
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post health alert")
        return False
    payload = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "ServiceHealth",
            "icon_emoji": ":heartbeat:",
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


def check_all_services() -> list[dict]:
    """Check each monitored service, return list of {service, callsign, state, log}
    entries for services that are NOT active.
    """
    failures: list[dict] = []
    for service in MONITORED_SERVICES:
        state = get_service_state(service)
        if state == "active":
            continue
        failures.append(
            {
                "service": service,
                "callsign": callsign_from_service_name(service),
                "state": state,
                "log": get_recent_log(service),
            }
        )
    return failures


def format_alert(failure: dict) -> str:
    return (
        f"[SERVICE-HEALTH] {failure['service']} — callsign={failure['callsign']} "
        f"state={failure['state']}\n"
        f"Recent journal:\n```\n{failure['log'][-500:] or '(no recent log)'}\n```"
    )


def main() -> int:
    failures = check_all_services()
    if not failures:
        logger.info("All %d monitored services active.", len(MONITORED_SERVICES))
        return 0
    logger.warning("Detected %d failed/inactive service(s).", len(failures))
    for f in failures:
        text = format_alert(f)
        posted = post_to_slack(text)
        logger.info("Alert for %s: posted=%s", f["service"], posted)
    return 0


if __name__ == "__main__":
    sys.exit(main())
