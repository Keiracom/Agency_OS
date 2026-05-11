#!/usr/bin/env python3
"""slack_relay.py — Aiden-bot Slack relay (AIDEN-SLACK-MIGRATION-001).

Mirrors the `tg` interface so callsites that switch from `tg -g "..."` to
`slack_relay.py -g "..."` get the same call shape.

Usage:
    slack_relay.py "message"              → post to #execution (default)
    slack_relay.py -g "message"           → post to #execution (group)
    slack_relay.py -c <channel_id> "..."  → post to specific channel ID
    echo "message" | slack_relay.py       → read from stdin

Reads from env:
    SLACK_BOT_TOKEN          (required) — xoxb-... bot token
    SLACK_BOT_USERNAME       (optional) — default "Aiden"
    SLACK_DEFAULT_CHANNEL    (optional) — default channel ID for -g
                              (defaults to #execution = C0B3QB0K1GQ)
    CALLSIGN                 (optional) — prefix tag, default "aiden"

Per AIDEN-SLACK-MIGRATION-001 constraints:
    - Uses chat:write.customize scope for username override
    - Flat posting (no threads)
    - Callsign tag preserved: "[AIDEN] message"

Failures exit non-zero with raw Slack API error on stderr — non-fatal for
callers, but visible.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

CALLSIGN = os.environ.get("CALLSIGN", "aiden")
CALLSIGN_TAG = f"[{CALLSIGN.upper()}]"
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
USERNAME = os.environ.get("SLACK_BOT_USERNAME", CALLSIGN.capitalize())
# Optional per-callsign icon override. Slack accepts either an emoji shortcode
# (":technologist:") via icon_emoji OR a fully-qualified URL via icon_url. We
# expose both so callers can choose; URL wins if both are set.
# Per Dave 2026-05-11: Elliot's :technologist: must be permanent (no inline
# env required). Per-callsign defaults below; env override still wins.
_DEFAULT_ICON_BY_CALLSIGN: dict[str, str] = {
    "elliot": ":technologist:",
    "enforcer": ":rotating_light:",
}
ICON_EMOJI = os.environ.get("SLACK_BOT_ICON_EMOJI", _DEFAULT_ICON_BY_CALLSIGN.get(CALLSIGN, ""))
ICON_URL = os.environ.get("SLACK_BOT_ICON_URL", "")

# Channel IDs (verified 2026-05-11 per AIDEN-SLACK-MIGRATION-001 dispatch)
CHANNELS = {
    "execution": "C0B3QB0K1GQ",
    "ceo": "C0B2PM3TV0B",
    "alerts": "C0B2EJU53EK",
    "completed_directives": "C0B2U15PSEA",
}
DEFAULT_CHANNEL = os.environ.get("SLACK_DEFAULT_CHANNEL", CHANNELS["execution"])


def parse_args(argv: list[str]) -> tuple[str, str]:
    """Return (channel_id, message)."""
    channel = DEFAULT_CHANNEL
    parts: list[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-g", "--group"):
            channel = CHANNELS["execution"]
        elif a in ("-c", "--channel"):
            i += 1
            if i >= len(argv):
                print("ERROR: -c requires a channel id", file=sys.stderr)
                sys.exit(2)
            # Accept either channel ID (C...) or named channel
            arg = argv[i]
            channel = CHANNELS.get(arg.lstrip("#"), arg)
        elif a in ("-d", "--dm"):
            print("ERROR: -d (DM) not supported in Slack relay yet", file=sys.stderr)
            sys.exit(2)
        else:
            parts.append(a)
        i += 1
    message = " ".join(parts) if parts else sys.stdin.read().strip()
    if not message:
        print("ERROR: no message provided", file=sys.stderr)
        sys.exit(2)
    return channel, message


def post(channel: str, text: str) -> dict:
    """POST to Slack chat.postMessage. Returns parsed response."""
    if not BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set", file=sys.stderr)
        sys.exit(2)
    if not text.startswith(CALLSIGN_TAG):
        text = f"{CALLSIGN_TAG} {text}"
    payload: dict = {"channel": channel, "text": text, "username": USERNAME}
    if ICON_URL:
        payload["icon_url"] = ICON_URL
    elif ICON_EMOJI:
        payload["icon_emoji"] = ICON_EMOJI
    body = json.dumps(payload).encode("utf-8")
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
