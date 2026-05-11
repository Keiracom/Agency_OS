"""concur_gate.py — outbound R1 gate (P0 per Max directive 2026-05-11).

Imported by scripts/slack_relay.py + scripts/coo_slack_relay.py to block
trigger-pattern messages from reaching Slack until at least one peer has
posted [CONCUR:<my-callsign>] in the recent message window.

Single source of truth for: trigger detection, peer concur lookup, hold
file location. Other modules MUST NOT reimplement R1 detection — extend
this module.

Behaviour:
  gate_check(text, callsign, ...) -> (allow, replacement)
    allow=True, replacement=None      -> caller posts text as-is
    allow=False, replacement="[CONCUR-REQUEST:CALLSIGN] ..."
                                      -> caller posts replacement INSTEAD,
                                         original message persisted to
                                         /tmp/<callsign>-pending-concur/

v1 is synchronous + manual-retry: agent re-invokes slack_relay.py after
peer concur is seen. v2 (deferred) adds an auto-release daemon.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from src.bot_common.enforcer_rules import TRIGGER_PATTERNS

CONCUR_LOOKBACK = 10
EXECUTION_CHANNEL = "C0B3QB0K1GQ"


def _pending_dir(callsign: str) -> Path:
    return Path(f"/tmp/{callsign}-pending-concur")


def _topic_sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def should_gate(text: str) -> bool:
    """True if the text matches an R1 trigger pattern."""
    lower = text.lower()
    return any(p in lower for p in TRIGGER_PATTERNS)


def has_peer_concur(my_callsign: str, bot_token: str, channel: str = EXECUTION_CHANNEL) -> bool:
    """Look back CONCUR_LOOKBACK messages in #execution for [CONCUR:<my-callsign>]."""
    needle = f"[concur:{my_callsign.lower()}]"
    url = f"https://slack.com/api/conversations.history?channel={channel}&limit={CONCUR_LOOKBACK}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bot_token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False
    if not data.get("ok"):
        return False
    return any(needle in (msg.get("text") or "").lower() for msg in data.get("messages", []))


def gate_check(text: str, my_callsign: str, bot_token: str, peer_label: str = "peer") -> tuple[bool, str | None]:
    """Return (allow, replacement_message).

    allow=True  -> caller posts text unchanged.
    allow=False -> caller posts replacement (CONCUR-REQUEST) instead;
                   the original text is persisted under /tmp/<callsign>-pending-concur/
                   keyed by topic-sha so the agent can retry after concur.
    """
    if not should_gate(text):
        return True, None
    if has_peer_concur(my_callsign, bot_token):
        return True, None
    # Hold the message; ask for concur.
    sha = _topic_sha(text)
    pdir = _pending_dir(my_callsign)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"{sha}.txt").write_text(text)
    topic = text.splitlines()[0][:120]
    replacement = (
        f"[CONCUR-REQUEST:{my_callsign.upper()}] requesting concurrence from {peer_label} on: {topic}\n"
        f"(held under /tmp/{my_callsign}-pending-concur/{sha}.txt; release on [CONCUR:{my_callsign}] in #execution)"
    )
    return False, replacement


def env_skip() -> bool:
    """Allow CI / one-shot scripts to skip the gate via env var."""
    return os.environ.get("CONCUR_GATE_SKIP", "").lower() in ("1", "true", "yes")
