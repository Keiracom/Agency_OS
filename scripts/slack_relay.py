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
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _resolve_callsign() -> str:
    """Resolve callsign from env → IDENTITY.md → hard fail.

    Per Dave directive #6 (callsign bug fix 2026-05-11): no silent default.
    A relay that defaults to 'aiden' when run from the wrong worktree can
    misattribute posts. Require explicit env OR ./IDENTITY.md resolution.
    """
    env_val = os.environ.get("CALLSIGN", "").strip()
    if env_val:
        return env_val.lower()
    identity_path = Path(__file__).resolve().parent.parent / "IDENTITY.md"
    if identity_path.exists():
        match = re.search(
            r"^\s*\*\*?CALLSIGN:?\*\*?\s*([A-Za-z]\w*)",
            identity_path.read_text(),
            re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group(1).lower()
    print(
        "ERROR: CALLSIGN unresolved — set CALLSIGN env var or ensure "
        f"{identity_path} contains a `**CALLSIGN:** <name>` header",
        file=sys.stderr,
    )
    sys.exit(2)


CALLSIGN = _resolve_callsign()
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

# Channel IDs (verified 2026-05-11 per AIDEN-SLACK-MIGRATION-001 dispatch).
# "ops" = Max's COO channel (mirrors coo_slack_relay.py CHANNELS dict).
CHANNELS = {
    "execution": "C0B3QB0K1GQ",
    "ceo": "C0B2PM3TV0B",
    "alerts": "C0B2EJU53EK",
    "completed_directives": "C0B2U15PSEA",
    "ops": "C0B2UCNRJ86",
}
DEFAULT_CHANNEL = os.environ.get("SLACK_DEFAULT_CHANNEL", CHANNELS["execution"])

# Per-callsign outbound allowlist (Dave directive #6 callsign bug fix 2026-05-11).
# Worktree's CALLSIGN determines which channels it may post to. #ceo is always
# Dave-Elliot exclusive; clones (atlas/orion/scout) post to #execution only.
# Aiden also writes #completed_directives per Protocol #4 (directive completion log).
_ALLOWED_CHANNELS_BY_CALLSIGN: dict[str, frozenset[str]] = {
    # Elliot (COO, runs prime worktree): execution + ceo + ops + completed_directives.
    # Per Elliot Step 0 12:00:24 UTC ("main = execution+ceo+ops") + Protocol #4
    # (completion log channel added to dispatch 2026-05-11 20:42).
    "elliot": frozenset(
        {
            CHANNELS["execution"],
            CHANNELS["ceo"],
            CHANNELS["ops"],
            CHANNELS["completed_directives"],
        }
    ),
    # Aiden (build agent): execution + completed_directives (Protocol #4 mandate).
    "aiden": frozenset({CHANNELS["execution"], CHANNELS["completed_directives"]}),
    # Max (CTO): execution only (mirrors coo_slack_relay.py).
    "max": frozenset({CHANNELS["execution"]}),
    # Clones (atlas/orion/scout): execution only per Step 0.
    "atlas": frozenset({CHANNELS["execution"]}),
    "orion": frozenset({CHANNELS["execution"]}),
    "scout": frozenset({CHANNELS["execution"]}),
}
ALLOWED_CHANNELS = _ALLOWED_CHANNELS_BY_CALLSIGN.get(CALLSIGN, frozenset({CHANNELS["execution"]}))


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
    if channel not in ALLOWED_CHANNELS:
        print(
            f"ERROR: {CALLSIGN}-relay refuses post to {channel} — "
            f"not in worktree allowlist {sorted(ALLOWED_CHANNELS)} "
            f"(Dave directive #6, callsign bug fix)",
            file=sys.stderr,
        )
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
    # S1 verify gate (Phase 6 — block fabricated PR# / commit-hash in completion
    # claims at outbound. Per Claude sign-off 2026-05-11.).
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
        pass  # repo not on sys.path; fall through ungated rather than break all posts
    # R1 outbound gate (P0 per Max directive 2026-05-11 — hold trigger-pattern
    # messages until peer concur is in the recent #execution window).
    try:
        from src.bot_common.concur_gate import env_skip, gate_check
    except ImportError:
        # Repo not on sys.path (rare — e.g. invoked from outside the repo
        # root). Fall through ungated rather than block all posts.
        env_skip = lambda: True  # noqa: E731
        gate_check = None
    if gate_check and not env_skip():
        allow, replacement = gate_check(message, CALLSIGN, BOT_TOKEN)
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
