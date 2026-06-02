#!/usr/bin/env python3
"""coo_slack_relay.py — Max COO Slack relay (Step 4).

Mirrors the `tg` interface for Max's outbound posting to Slack.

Usage:
    coo_slack_relay.py "message"              → post to #execution
    coo_slack_relay.py -g "message"           → post to #execution (group)
    coo_slack_relay.py -o "message"           → post to #ops (COO channel)
    coo_slack_relay.py -c <channel_id> "msg"  → post to specific channel
    echo "message" | coo_slack_relay.py       → read from stdin
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

CALLSIGN = "max"
CALLSIGN_TAG = "[MAX]"
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
USERNAME = "Max"

CHANNELS = {
    "execution": "C0B3QB0K1GQ",
    "ceo": "C0B2PM3TV0B",
    "alerts": "C0B2EJU53EK",
    "completed_directives": "C0B2U15PSEA",
    "ops": "C0B2UCNRJ86",
}
DEFAULT_CHANNEL = CHANNELS["execution"]
# Per Dave 2026-05-11 ts=1778481?: Max posts ONLY to #execution.
# Hard-reject any attempt to post to #ceo or other channels.
ALLOWED_CHANNELS = {CHANNELS["execution"]}


def parse_args(argv: list[str]) -> tuple[str, str]:
    channel = DEFAULT_CHANNEL
    parts: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-g", "--group"):
            channel = CHANNELS["execution"]
        elif a in ("-o", "--ops"):
            channel = CHANNELS["ops"]
        elif a in ("-c", "--channel"):
            i += 1
            if i >= len(argv):
                print("ERROR: -c requires a channel id", file=sys.stderr)
                sys.exit(2)
            arg = argv[i]
            channel = CHANNELS.get(arg.lstrip("#"), arg)
        elif a in ("-d", "--dm"):
            channel = CHANNELS["ceo"]
        else:
            parts.append(a)
        i += 1
    message = " ".join(parts) if parts else sys.stdin.read().strip()
    if not message:
        print("ERROR: no message provided", file=sys.stderr)
        sys.exit(2)
    return channel, message


def post(channel: str, text: str) -> dict:
    if not BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(2)
    # Dave directive 2026-05-27: kill all #execution posts. Block at relay layer.
    if channel == CHANNELS["execution"]:
        print(
            f"[coo_slack_relay] DROPPED post to #execution — "
            f"per Dave directive 2026-05-27 kill all #execution notifications. "
            f"msg_prefix={text[:60]!r}",
            file=sys.stderr,
        )
        return {"ok": True, "dropped": True, "reason": "execution_channel_killed"}
    if channel not in ALLOWED_CHANNELS:
        print(
            f"ERROR: Max-relay refuses post to {channel} — Max only posts to #execution per Dave 2026-05-11",
            file=sys.stderr,
        )
        sys.exit(2)
    if not text.startswith(CALLSIGN_TAG):
        text = f"{CALLSIGN_TAG} {text}"
    body = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": USERNAME,
            "icon_emoji": ":toolbox:",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        print(f"ERROR: network failure: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    channel, message = parse_args(sys.argv[1:])
    # S1 verify gate (Phase 6 — block fabricated PR#/commit-hash in completion claims)
    try:
        _repo = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        if _repo not in sys.path:
            sys.path.insert(0, _repo)
        from src.bot_common.verify_gate import gate_check as verify_gate_check

        ok, blocker = verify_gate_check(message)
        if not ok:
            print(f"R_VERIFY_BLOCKED: {blocker}", file=sys.stderr)
            return 2
    except ImportError:
        pass
    # R1 outbound gate (P0 per Max directive 2026-05-11; rewired Dave directive
    # 2026-06-02 — inbox-signal source, CONCUR_GATE_SKIP bypass removed).
    try:
        from src.bot_common.concur_gate import gate_check
    except ImportError:
        gate_check = None
    if gate_check:
        allow, replacement = gate_check(message, CALLSIGN)
        if not allow and replacement is not None:
            message = replacement
            print("⚠  concur-gate HELD original; posting CONCUR-REQUEST instead", file=sys.stderr)
    result = post(channel, message)
    if not result.get("ok"):
        print(f"ERROR: Slack rejected: {result}", file=sys.stderr)
        return 1
    ts = result.get("ts", "")
    ch = result.get("channel", channel)
    print(f"→ {CALLSIGN_TAG} sent to Slack #{ch} (ts {ts})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
