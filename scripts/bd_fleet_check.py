#!/usr/bin/env python3
"""bd fleet-check — capture last 10 lines of each agent tmux pane and post bullet
report to #ceo (KEI-94 + KEI-97).

Bypasses the Supabase task-state abstraction by reading tmux directly. Caught
the 2026-05-16 incident where tasks showed 'active' while the underlying tmux
sessions had been dead for an hour.

Usage:
    bd fleet-check                # capture + post to #ceo
    bd fleet-check --no-post      # capture + print to stdout only (dry run)
    bd fleet-check --channel ceo  # explicit channel (default ceo)

Exit codes:
    0 success (posted or dry-run completed)
    1 Slack post failed
    2 missing SLACK_BOT_TOKEN

Acceptance (Dave KEI-94 addendum 2026-05-17): Dave types 'check' in #ceo →
Elliot runs `bd fleet-check` → bullet report lands in #ceo within 60s.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

# Canonical tmux session names per infra/systemd/agents/*.service. Must stay
# aligned with scripts/agent_keepalive.sh callers.
FLEET = [
    ("ELLIOT", "elliottbot"),
    ("AIDEN", "aiden"),
    ("MAX", "maxbot"),
    ("ATLAS", "atlas"),
    ("ORION", "orion"),
    ("SCOUT", "scout"),
]

CHANNELS = {
    "ceo": "C0B2PM3TV0B",
    "execution": "C0B3QB0K1GQ",
}

CAPTURE_LINES = 10
TMUX_TIMEOUT_SEC = 5


def capture_pane(session: str) -> tuple[str, str]:
    """Return (status, last_n_lines). status is ALIVE | DEAD | ERROR."""
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", f"{session}:0.0", "-p"],
            capture_output=True,
            text=True,
            timeout=TMUX_TIMEOUT_SEC,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ("ERROR", "tmux capture timeout")
    except FileNotFoundError:
        return ("ERROR", "tmux not installed")

    if result.returncode != 0:
        stderr = (result.stderr or "").strip().lower()
        if "no server" in stderr or "can't find session" in stderr or "session not found" in stderr:
            return ("DEAD", stderr or "session absent")
        return ("ERROR", stderr or f"rc={result.returncode}")

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    tail = "\n".join(lines[-CAPTURE_LINES:]) if lines else "(empty pane)"
    return ("ALIVE", tail)


def build_report() -> tuple[str, dict[str, str]]:
    """Return (slack_text, status_map)."""
    lines = ["*Fleet check* — `bd fleet-check` (KEI-94)"]
    status_map: dict[str, str] = {}
    for label, session in FLEET:
        status, tail = capture_pane(session)
        status_map[label] = status
        marker = {
            "ALIVE": ":large_green_circle:",
            "DEAD": ":red_circle:",
            "ERROR": ":warning:",
        }.get(status, ":grey_question:")
        if status == "ALIVE":
            lines.append(
                f"\n*{marker} {label}* (tmux=`{session}`) — last {CAPTURE_LINES}:\n```{tail}```"
            )
        else:
            lines.append(f"\n*{marker} {label}* (tmux=`{session}`) — {status}: {tail}")
    return ("\n".join(lines), status_map)


def post_slack(channel_id: str, text: str) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("[fleet-check] SLACK_BOT_TOKEN not set", file=sys.stderr)
        return False
    payload = json.dumps({"channel": channel_id, "text": text}).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(f"[fleet-check] Slack post failed: {exc}", file=sys.stderr)
        return False
    if '"ok":true' not in body:
        print(f"[fleet-check] Slack response: {body}", file=sys.stderr)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--no-post", action="store_true", help="print report to stdout only")
    parser.add_argument("--channel", default="ceo", choices=sorted(CHANNELS.keys()))
    args = parser.parse_args(argv)

    started = time.monotonic()
    text, status_map = build_report()
    elapsed = time.monotonic() - started

    if args.no_post:
        print(text)
        print(f"\n(captured in {elapsed:.1f}s; statuses={status_map})", file=sys.stderr)
        return 0

    channel_id = CHANNELS[args.channel]
    if not os.environ.get("SLACK_BOT_TOKEN"):
        return 2
    ok = post_slack(channel_id, text)
    total = time.monotonic() - started
    print(
        f"[fleet-check] elapsed={total:.1f}s posted={ok} channel=#{args.channel}", file=sys.stderr
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
