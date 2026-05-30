"""concur_gate.py — outbound R1 gate (P0 per Max directive 2026-05-11).

Imported by scripts/slack_relay.py + scripts/coo_slack_relay.py to block
explicit governance-action messages from reaching Slack until at least
one peer has posted [CONCUR:<my-callsign>] in the recent message window.

Single source of truth for: trigger detection, peer concur lookup, hold
file location. Other modules MUST NOT reimplement R1 detection — extend
this module.

Trigger (KEI-38, Dave verbatim 2026-05-14):
  Gate fires ONLY on a literal [CONCUR:<callsign>] or [BLOCK:<callsign>]
  token. Prose containing the word "concur" does NOT trigger. Tokens
  with prefixes ([FINAL CONCUR:...], [CONCUR-REQUEST:...]) do NOT trigger
  either, since they signal a different governance action (final
  authorisation / hold-stub).

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
import re
import urllib.error
import urllib.request
from pathlib import Path

CONCUR_LOOKBACK = 10
EXECUTION_CHANNEL = "C0B3QB0K1GQ"

# Anchored trigger: literal [CONCUR:<callsign>] or [BLOCK:<callsign>].
# Requires `[` immediately followed by CONCUR: or BLOCK:, which excludes
# [FINAL CONCUR:...] (preceded by FINAL), [CONCUR-REQUEST:...] (uses `-`
# not `:` after CONCUR), and prose containing the word "concur".
_GATE_TRIGGER = re.compile(r"\[(?:CONCUR|BLOCK):[a-z][a-z0-9_-]*\]", re.IGNORECASE)

# Canonical 7-callsign roster (mirrors scripts/cache_hit_rate_ingest.py:44).
# Used by _eligible_reviewers() when ceo:agent_health is absent (Agency_OS-yvlr51).
_KNOWN_CALLSIGNS: frozenset[str] = frozenset(
    {"elliot", "aiden", "max", "atlas", "orion", "scout", "nova"}
)


def _pending_dir(callsign: str) -> Path:
    return Path(f"/tmp/{callsign}-pending-concur")


def _topic_sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


# KEI-79 escalation sentinel — bd escalate emits this BEFORE the direct-post call so
# downstream gates recognise the escalation as a Step-0 surrogate (Dave authorisation
# IS the gate event for an escalation path). Exempt from CONCUR matching.
_ESCALATION_SENTINEL = re.compile(
    r"\[ESCALATION-INITIATED:[a-z][a-z0-9_-]*:[A-Z]+-\d+\]", re.IGNORECASE
)


def _eligible_reviewers(my_callsign: str) -> list[str]:
    """Return sorted list of peers eligible to release a CONCUR-REQUEST.

    Agency_OS-yvlr51 — when ceo:agent_health is populated by the polling loop
    (KEI-63 follow-up, not yet shipped), this filters peers by API-cap (<70%
    weekly), idle window (<30 min), and recent HOLD/BLOCK absence. Until that
    infrastructure exists, fallback returns ALL non-author callsigns — the
    release lookup already accepts [CONCUR:<requester>] from any sender, so
    advertising the full roster keeps routing unblocked when a specific peer
    is at context cap (the V1-chain freeze scenario Dave diagnosed).
    """
    # TODO(yvlr51 follow-up): query ceo:agent_health via mcp-bridge supabase
    # and filter by (weekly_cap < 70%) AND (idle_minutes < 30) AND
    # (no_recent_hold_or_block). Fail-open to the fallback on any read error.
    return sorted(cs for cs in _KNOWN_CALLSIGNS if cs != my_callsign.lower())


def should_gate(text: str) -> bool:
    """True if the text contains a literal [CONCUR:<callsign>] or [BLOCK:<callsign>] token.

    KEI-79 carve-out: [ESCALATION-INITIATED:<callsign>:<task-id>] sentinels are NOT gated
    even if they incidentally contain a concur-shaped substring downstream.
    """
    if _ESCALATION_SENTINEL.search(text):
        return False
    return bool(_GATE_TRIGGER.search(text))


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


def gate_check(
    text: str, my_callsign: str, bot_token: str, peer_label: str = "peer"
) -> tuple[bool, str | None]:
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
    eligible = ", ".join(_eligible_reviewers(my_callsign))
    replacement = (
        f"[CONCUR-REQUEST:{my_callsign.upper()}] requesting concurrence from {peer_label} on: {topic}\n"
        f"Eligible reviewers: {eligible}\n"
        f"(held under /tmp/{my_callsign}-pending-concur/{sha}.txt; release on [CONCUR:{my_callsign}] in #execution)"
    )
    return False, replacement


def env_skip() -> bool:
    """Allow CI / one-shot scripts to skip the gate via env var."""
    return os.environ.get("CONCUR_GATE_SKIP", "").lower() in ("1", "true", "yes")
