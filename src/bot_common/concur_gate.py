"""concur_gate.py — outbound R1 gate, inbox-signal source (Dave directive 2026-06-02).

Imported by scripts/slack_relay.py + scripts/coo_slack_relay.py to block explicit
governance-action messages from reaching Slack until at least 2 distinct non-author
deliberators have posted [CONCUR:<my-callsign>] in the recent inbox window.

History
-------
v1 (KEI-38, 2026-05-14): scanned the #execution Slack channel via
conversations.history for a single [CONCUR:<callsign>] within a 10-message
window. The channel was killed 2026-05-27 in the cutover sweep that retired
the #execution → relay-inbox architecture; the Slack-history scan has been
permanently broken since that date.

v2 (Dave directive 2026-06-02 — this module): repoint the signal source to the
inbox-watcher's processed/ directory (the file relay that replaced #execution),
enforce ≥2 distinct deliberator concurrers, enforce independence (author cannot
self-concur), fail closed, and remove the CONCUR_GATE_SKIP env-var bypass.

Source-of-signal choice (filesystem over NATS, documented per directive)
------------------------------------------------------------------------
The gate runs synchronously inside slack_relay.py (a sync script). The two
candidate sources were:

  (a) NATS JetStream `elliot_inbox` stream — durable, sequence-timestamped,
      authoritative. Requires nats-py async client + connect/subscribe cycle
      per gate-check invocation. Adds an async hop to a sync call site.

  (b) /tmp/telegram-relay-<callsign>/processed/*.json — the inbox-watcher's
      post-consumption store. Each file has `from` field (sender callsign),
      a body/text/subject containing the message, and file mtime as the
      authoritative timestamp. Sync access, zero extra deps, already populated
      by the same watcher that drains NATS.

Picked (b). The processed/ dir is the materialised view of the NATS stream
that the watcher has ALREADY acknowledged — using it avoids re-decoding
NATS in a sync gate, and the file mtime is wall-clock-stable for the lookback
window. The trade-off: if the inbox-watcher service is down, the gate sees
no new concurrers and fails closed. That is the correct failure mode.

Trigger detection (unchanged from KEI-38)
-----------------------------------------
Gate fires ONLY on a literal [CONCUR:<callsign>] or [BLOCK:<callsign>] token.
Prose containing the word "concur" does NOT trigger. Tokens with prefixes
([FINAL CONCUR:...], [CONCUR-REQUEST:...]) do NOT trigger either. The KEI-79
[ESCALATION-INITIATED:<callsign>:<task-id>] sentinel is exempt.

Behaviour
---------
gate_check(text, my_callsign, *, synthesis_author=None) -> (allow, replacement)
  allow=True, replacement=None   -> caller posts text as-is
  allow=False, replacement="..." -> caller posts replacement instead, original
                                    persisted under /tmp/<callsign>-pending-concur/

Independence rule
-----------------
The deliberation layer is a promotion, not a genealogy. Aiden and Max are the
only callsigns promoted to deliberator status (KEI-220, Dave directive
2026-06-02). Atlas, Orion, Nova, and Scout are workers — they may produce
substantive review input but their CONCUR signals do NOT satisfy the binding
2-of-N requirement, regardless of which deliberator (if any) they originated
from. There is no clone-resolution / principal-collapse step; promotion to
the deliberation layer is the only filter that matters.

A binding 2-of-N concurrence requires two from {aiden, max} or one from
{aiden, max} + dave. (The dave-as-second case is satisfied by Dave's direct
ratification on the held topic, not by R1 inbox-scan — handled out of band.)

If `synthesis_author` is provided, that callsign is excluded from valid
concurrers (direct discard, no resolution) and the threshold is 2 distinct
deliberators. If not provided, the safe default is to require BOTH
deliberators (aiden AND max) — the caller could not prove the author, so
cross-attestation cannot rule out self-concurrence; demand the full set.

The deliberation-layer-promotion rule is canonicalised in
``docs/governance/CONSOLIDATED_RULES.md §RULE 3 — APPROVE`` (Independence rule
subsection, Dave directive 2026-06-02).

CONCUR_GATE_SKIP bypass
-----------------------
REMOVED in v2. The env_skip() function was the largest hole in the v1 gate —
a single env var would silently disable all gating. There is no replacement
break-glass flag. If a future audit-logged break-glass path is required, it
must be a separate mechanism with an explicit audit row, not a simple env
flag readable by any process.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

# Callsigns promoted to the deliberation layer (KEI-220, Dave directive
# 2026-06-02). ONLY these CONCUR signals satisfy the binding 2-of-N
# requirement. Workers (atlas, orion, nova, scout) are excluded because
# they are not promoted — not because of clone ancestry. The set is closed
# under explicit promotion; do not infer membership from genealogy.
DELIBERATOR_CALLSIGNS: frozenset[str] = frozenset({"aiden", "max"})

# Window for concur-signal freshness. 60-min default per Dave directive
# 2026-06-02 ("allow for deliberation time").
DEFAULT_LOOKBACK_MINUTES = 60

# Processed-dir template (one per callsign). The inbox-watcher service
# (callsign-inbox-watcher.service) moves consumed JSON envelopes here.
_PROCESSED_DIR_TEMPLATE = "/tmp/telegram-relay-{callsign}/processed"

# Anchored trigger: literal [CONCUR:<callsign>] or [BLOCK:<callsign>].
# Excludes [FINAL CONCUR:...] (preceded by FINAL), [CONCUR-REQUEST:...]
# (uses `-` not `:` after CONCUR), and prose containing "concur".
_GATE_TRIGGER = re.compile(r"\[(?:CONCUR|BLOCK):[a-z][a-z0-9_-]*\]", re.IGNORECASE)

# KEI-79 escalation sentinel — Dave-authorised step-0 surrogate, exempt from
# CONCUR matching. bd escalate emits this BEFORE the direct-post call.
_ESCALATION_SENTINEL = re.compile(
    r"\[ESCALATION-INITIATED:[a-z][a-z0-9_-]*:[A-Z]+-\d+\]", re.IGNORECASE
)


def _pending_dir(callsign: str) -> Path:
    return Path(f"/tmp/{callsign}-pending-concur")


def _topic_sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _processed_dir(callsign: str) -> Path:
    return Path(_PROCESSED_DIR_TEMPLATE.format(callsign=callsign.lower()))


def _lookback_seconds() -> float:
    """Window for signal freshness. CONCUR_LOOKBACK_MINUTES env overrides default."""
    raw = os.environ.get("CONCUR_LOOKBACK_MINUTES", "").strip()
    if not raw:
        return DEFAULT_LOOKBACK_MINUTES * 60.0
    try:
        return float(raw) * 60.0
    except ValueError:
        return DEFAULT_LOOKBACK_MINUTES * 60.0


def _payload_text(payload: dict) -> str:
    """Concur tokens may appear in subject, body, text, brief, or message — check all."""
    parts: list[str] = []
    for key in ("body", "text", "message", "subject", "brief"):
        val = payload.get(key)
        if isinstance(val, str):
            parts.append(val)
    return "\n".join(parts)


def should_gate(text: str) -> bool:
    """True if the text contains a literal [CONCUR:<callsign>] or [BLOCK:<callsign>] token.

    KEI-79 carve-out: [ESCALATION-INITIATED:<callsign>:<task-id>] sentinels are
    NOT gated even if they incidentally contain a concur-shaped substring.
    """
    if _ESCALATION_SENTINEL.search(text):
        return False
    return bool(_GATE_TRIGGER.search(text))


def find_recent_concurrers(
    my_callsign: str,
    *,
    now: float | None = None,
    processed_dir: Path | None = None,
) -> set[str]:
    """Return the set of distinct callsigns that posted [CONCUR:<my_callsign>] within the window.

    Source: <processed_dir>/*.json (defaults to /tmp/telegram-relay-<my_callsign>/processed).
    Each JSON envelope must carry `from` (sender callsign) and at least one
    of body/text/message/subject/brief. mtime is compared against the lookback
    cutoff; envelopes older than the window are skipped.

    Fail-closed: missing dir, OS error, malformed JSON, missing `from`, or
    non-dict payload all SKIP the envelope silently. The gate then sees fewer
    concurrers and blocks — the correct failure mode.
    """
    needle = f"[concur:{my_callsign.lower()}]"
    if now is None:
        now = time.time()
    cutoff = now - _lookback_seconds()
    pdir = processed_dir or _processed_dir(my_callsign)
    if not pdir.exists() or not pdir.is_dir():
        return set()
    concurrers: set[str] = set()
    for path in pdir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            continue
        try:
            payload = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        sender = payload.get("from") or payload.get("sender")
        if not isinstance(sender, str) or not sender.strip():
            continue
        body = _payload_text(payload)
        if needle in body.lower():
            concurrers.add(sender.strip().lower())
    return concurrers


def gate_check(
    text: str,
    my_callsign: str,
    *,
    synthesis_author: str | None = None,
    peer_label: str = "peer",
    processed_dir: Path | None = None,
    now: float | None = None,
) -> tuple[bool, str | None]:
    """Return (allow, replacement_message).

    allow=True  -> caller posts text unchanged.
    allow=False -> caller posts replacement (CONCUR-REQUEST) instead; the
                   original text is persisted under /tmp/<my_callsign>-pending-concur/
                   keyed by topic-sha so the agent can retry after concur.

    Independence rule (Dave directive 2026-06-02 — deliberation-layer promotion):
      - DELIBERATOR_CALLSIGNS = {aiden, max} is the promotion list (KEI-220).
        Worker concurs (atlas, orion, nova, scout) do NOT count — they are
        excluded by the filter, full stop. There is no clone-resolution step;
        promotion is the only criterion.
      - synthesis_author=<callsign> -> excluded from valid concurrers (direct
        discard, no resolution); require 2 distinct deliberators.
      - synthesis_author=None       -> safe default: require BOTH deliberators
        (aiden AND max) — the gate cannot rule out self-concurrence when
        authorship is unknown.

    The CONCUR_GATE_SKIP env-var bypass that existed in v1 is REMOVED. There is
    no env-var path to skip this gate.
    """
    if not should_gate(text):
        return True, None

    raw = find_recent_concurrers(my_callsign, now=now, processed_dir=processed_dir)
    valid = {cs for cs in raw if cs in DELIBERATOR_CALLSIGNS}
    if synthesis_author:
        valid.discard(synthesis_author.strip().lower())
        required = 2
    else:
        required = len(DELIBERATOR_CALLSIGNS)

    if len(valid) >= required:
        return True, None

    sha = _topic_sha(text)
    pdir = _pending_dir(my_callsign)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / f"{sha}.txt").write_text(text)
    topic = text.splitlines()[0][:120] if text.splitlines() else ""
    have = ", ".join(sorted(valid)) if valid else "(none)"
    need_descr = (
        f"2 distinct deliberators excluding author={synthesis_author.lower()}"
        if synthesis_author
        else f"all {required} deliberators (synthesis_author not supplied)"
    )
    eligible = ", ".join(sorted(DELIBERATOR_CALLSIGNS))
    replacement = (
        f"[CONCUR-REQUEST:{my_callsign.upper()}] requesting concurrence from {peer_label} on: {topic}\n"
        f"Have: {have} — need {need_descr}\n"
        f"Eligible deliberators: {eligible}\n"
        f"(held under /tmp/{my_callsign}-pending-concur/{sha}.txt; "
        f"release on ≥{required} distinct non-author [CONCUR:{my_callsign}] in inbox window)"
    )
    return False, replacement
