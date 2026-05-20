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
import time
import urllib.error
import urllib.request
from pathlib import Path

# Slack access restricted to elliot only (Dave directive 2026-05-19 — only elliot
# may post to Slack; default channel is #ceo). Other callsigns invoking this
# script exit 2 with a clear denial message so callers know access was blocked.
_CALLSIGN_ENFORCE = os.environ.get("CALLSIGN", "").strip().lower()
if _CALLSIGN_ENFORCE and _CALLSIGN_ENFORCE != "elliot":
    sys.stderr.write(
        f"SLACK_ACCESS_DENIED: callsign={_CALLSIGN_ENFORCE!r} blocked. "
        f"Only elliot may post to Slack per Dave directive 2026-05-19.\n"
    )
    sys.exit(2)
# Elliot's default channel is #ceo (C0B2PM3TV0B), not #execution. Override the
# module-default SLACK_DEFAULT_CHANNEL when running as elliot and no explicit
# channel was set in the environment.
if _CALLSIGN_ENFORCE == "elliot" and not os.environ.get("SLACK_DEFAULT_CHANNEL"):
    os.environ["SLACK_DEFAULT_CHANNEL"] = "C0B2PM3TV0B"

# KEI-40: rate-limit retry config. Slack chat.postMessage returns HTTP 429 with
# Retry-After header on tier-3 method rate-limits (~1 req/sec for chat.postMessage).
# Exponential backoff with header-respect avoids the governance-noise pattern
# Dave flagged ts ~1778666400 (relay exit non-zero without retry = false stuck signal).
_KEI40_MAX_RETRIES = 5
_KEI40_BASE_BACKOFF_SECONDS = 1.0
_KEI40_MAX_BACKOFF_SECONDS = 30.0

# KEI-80: escalation-keyword scan (Dave 30-min hot-patch 2026-05-16).
# Any outbox message containing one of these phrases fires a direct post to
# #ceo BEFORE the normal relay. Both posts happen — the CEO post is additive.
# Store as module-level constant so tests can patch it.
ESCALATION_KEYWORDS: list[str] = [
    "awaiting",
    "decision needed",
    "option a",
    "option b",
    "option c",
    "blocked",
    "ceo decision",
    "dave decision",
    "your call",
    "holding for",
]
# Maximum body length (chars) forwarded in the [ESCALATION] prefix post.
# Longer bodies are truncated with an ellipsis marker to avoid Slack friction.
_ESCALATION_MAX_BODY_CHARS = 500

from typing import Final

_LAST_POST_STATE_PATH: Final[Path] = Path(
    os.path.expanduser("~/.local/state/agency-os/callsign-last-post.json")
)


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

# Per-callsign outbound allowlist (Dave directive #6 callsign bug fix 2026-05-11;
# deliberation-layer #ceo grant 2026-05-18 per Dave directive).
# Worktree's CALLSIGN determines which channels it may post to. Deliberation
# layer (Elliot/Aiden/Max) may post to #ceo; clones (atlas/orion/scout/nova)
# post to #execution only.
# Aiden also writes #completed_directives per Protocol #4 (directive completion log).
_ALLOWED_CHANNELS_BY_CALLSIGN: dict[str, frozenset[str]] = {
    # Elliot (COO, runs prime worktree): execution + ceo + ops + completed_directives.
    "elliot": frozenset(
        {
            CHANNELS["execution"],
            CHANNELS["ceo"],
            CHANNELS["ops"],
            CHANNELS["completed_directives"],
        }
    ),
    # Aiden (deliberator — governance lens): execution + ceo + completed_directives.
    "aiden": frozenset(
        {
            CHANNELS["execution"],
            CHANNELS["ceo"],
            CHANNELS["completed_directives"],
        }
    ),
    # Max (deliberator — quality lens): execution + ceo.
    "max": frozenset({CHANNELS["execution"], CHANNELS["ceo"]}),
    # Clones (atlas/orion/scout/nova): execution only per Step 0.
    "atlas": frozenset({CHANNELS["execution"]}),
    "orion": frozenset({CHANNELS["execution"]}),
    "scout": frozenset({CHANNELS["execution"]}),
    "nova": frozenset({CHANNELS["execution"]}),
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
        response = _post_with_retry(req)
    except urllib.error.URLError as e:
        print(f"ERROR: network failure: {e}", file=sys.stderr)
        sys.exit(1)
    _record_last_post(CALLSIGN)  # KEI-34 v3 HOLE B — track progress-cadence
    return response


def _post_with_retry(req: urllib.request.Request) -> dict:
    """KEI-40 — POST with exponential-backoff retry on HTTP 429 rate-limits.

    Respects Slack's Retry-After header when present; falls back to exponential
    delay (1s / 2s / 4s / 8s / 16s capped at 30s). Non-429 HTTPError + other
    URLError types fail-fast (re-raised — no retry). After _KEI40_MAX_RETRIES
    exhausted on 429s, the final HTTPError is re-raised.
    """
    for attempt in range(_KEI40_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == _KEI40_MAX_RETRIES:
                raise
            retry_after_header = e.headers.get("Retry-After", "") if e.headers else ""
            try:
                wait = float(retry_after_header)
            except (ValueError, TypeError):
                wait = min(_KEI40_BASE_BACKOFF_SECONDS * (2**attempt), _KEI40_MAX_BACKOFF_SECONDS)
            print(
                f"WARN: Slack 429, retry {attempt + 1}/{_KEI40_MAX_RETRIES} after {wait}s",
                file=sys.stderr,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable — loop should always return or raise")


def _record_last_post(callsign: str) -> None:
    """KEI-34 v3 HOLE B — record per-callsign last-Slack-post timestamp.
    Polling-loop reads this file to detect long-running tracks silent past
    LONG_RUNNING_TRACK_PROGRESS_MIN (30 min default). Best-effort; failure
    is non-fatal.

    Path is a module-level Final[Path] constant (NOT user-controlled input) so
    the read-modify-write is not a SonarCloud S2083 path-injection vector.
    The isinstance(state, dict) guard defends against a tampered state file
    that could otherwise hand a non-dict back into the update path."""
    try:
        _LAST_POST_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        state: dict = {}
        if _LAST_POST_STATE_PATH.exists():
            try:
                loaded = json.loads(_LAST_POST_STATE_PATH.read_text() or "{}")
                if isinstance(loaded, dict):
                    state = loaded
            except (OSError, json.JSONDecodeError):
                state = {}
        from datetime import UTC as _utc
        from datetime import datetime as _dt

        state[callsign] = _dt.now(_utc).isoformat()
        _LAST_POST_STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True))
    except OSError:
        pass


def _contains_escalation_keyword(text: str) -> bool:
    """KEI-80: Return True if text contains any ESCALATION_KEYWORDS (case-insensitive)."""
    lower = text.lower()
    return any(kw.lower() in lower for kw in ESCALATION_KEYWORDS)


# ---------------------------------------------------------------------------
# KEI-33 — R13 BLOCKER ESCALATION (Dave directive 2026-05-18)
# ---------------------------------------------------------------------------
# Hard-redirect (not additive) outbound blocker messages from #execution to
# #ceo. Triggered by canonical R13 markers + the dispatch's listed phrases.
# Unlike KEI-80's additive escalation, R13 swaps the channel BEFORE the
# post — so the message lands in #ceo ONLY (no duplicate to original
# channel, no double-fire with KEI-80 since KEI-80 no-ops when
# channel == #ceo).
#
# Gating: only redirect when the caller's CALLSIGN is permitted to post
# #ceo. Clones (atlas/orion/scout/nova) keep their existing #execution
# routing — they should escalate via dispatch chain, not by posting #ceo
# directly. KEI-80's additive path still applies to clones (it goes via
# the same bot token, not the clone's allowlist).

# Anchored matchers (full regex). Case-insensitive. Compiled at import time.
_R13_BLOCKER_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Canonical R13 marker: [BLOCKED:<callsign>] anywhere in the message.
    re.compile(r"\[BLOCKED:[A-Z][A-Z0-9_-]*\]", re.IGNORECASE),
    # Dispatch-listed phrasings.
    re.compile(r"\bblocked on ceo\b", re.IGNORECASE),
    re.compile(r"\bawaiting decision\b", re.IGNORECASE),
    re.compile(r"\boption [abcd]\b/[abcd]", re.IGNORECASE),  # "option A/B/C"
    re.compile(r"\boption [abcd]/[abcd](/[abcd])?\b", re.IGNORECASE),
)


def _is_r13_blocker(text: str) -> bool:
    """Return True if text contains any canonical R13 blocker marker."""
    return any(p.search(text) for p in _R13_BLOCKER_PATTERNS)


def _r13_maybe_redirect(channel: str, text: str) -> str:
    """KEI-33: If text contains an R13 blocker marker AND this callsign is
    allowed to post #ceo, swap the outbound channel to #ceo. Otherwise
    return the channel unchanged.

    Pre-empts KEI-80's additive post (`_maybe_escalate_to_ceo` no-ops
    when channel == ceo_channel) so we don't double-fire to #ceo.
    """
    ceo = CHANNELS["ceo"]
    if channel == ceo:
        return channel  # already heading to #ceo
    if not _is_r13_blocker(text):
        return channel
    if ceo not in ALLOWED_CHANNELS:
        # Clone callsigns can't post #ceo. Leave the message on #execution;
        # the clone must escalate via the dispatch chain instead.
        return channel
    print(
        f"R13: blocker marker detected in outbound from {CALLSIGN} — "
        f"redirecting #execution → #ceo per Dave directive 2026-05-18",
        file=sys.stderr,
    )
    return ceo


def _maybe_escalate_to_ceo(channel: str, text: str, callsign: str) -> None:
    """KEI-80: Fire a direct #ceo post when outbox message contains escalation language.

    Rules (per Dave 30-min hot-patch spec 2026-05-16):
    - Skipped when target channel is already #ceo (avoid double-post).
    - Skipped when message body already has [ESCALATION] prefix (avoid re-fire).
    - Body truncated at _ESCALATION_MAX_BODY_CHARS chars; appends '…(truncated)'.
    - CEO post fires BEFORE normal relay; failure is non-fatal (try/except → log).
    - Uses a raw urllib POST identical to _post_with_retry but targeted at #ceo.
    """
    ceo_channel = CHANNELS["ceo"]
    if channel == ceo_channel:
        return
    if text.startswith("[ESCALATION]"):
        return
    if not _contains_escalation_keyword(text):
        return
    if not BOT_TOKEN:
        print("KEI-80 WARN: SLACK_BOT_TOKEN not set — skipping CEO escalation", file=sys.stderr)
        return
    body_text = text
    if len(body_text) > _ESCALATION_MAX_BODY_CHARS:
        body_text = body_text[:_ESCALATION_MAX_BODY_CHARS] + "…(truncated)"
    ceo_text = f"[ESCALATION] {callsign} · {body_text}"
    payload: dict = {"channel": ceo_channel, "text": ceo_text, "username": USERNAME}
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
            result = json.loads(r.read())
        if not result.get("ok"):
            print(f"KEI-80 WARN: CEO escalation post rejected: {result}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"KEI-80 WARN: CEO escalation post failed: {exc}", file=sys.stderr)


def main() -> int:
    channel, message = parse_args(sys.argv[1:])
    # KEI-33 — R13 BLOCKER ESCALATION. Runs FIRST so the channel-swap is
    # visible to every downstream gate (R11 #ceo-format, KEI-80 additive
    # escalation). Redirect is a no-op for clone callsigns and for
    # messages already headed to #ceo.
    channel = _r13_maybe_redirect(channel, message)
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
    # LAW XV mechanical gate (Outcome 2 — block completion claims that haven't
    # written all 3 queryable stores. Per Max spec ts 1778553034 / Dave directive
    # 2026-05-12.).
    try:
        from src.bot_common.session_end_gate import gate_check as law_xv_gate_check

        ok, blocker = law_xv_gate_check(message)
        if not ok:
            print(blocker, file=sys.stderr)
            return 2
    except ImportError:
        pass
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
    # R11 CEO-FORMAT-GATE — block #ceo posts violating plain-English bullets-only
    # convention (Dave directive ts ~1778582530). Runs AFTER concur-gate so the
    # system-generated CONCUR-REQUEST replacement passes through (it's exempt).
    try:
        from src.bot_common.enforcer_deterministic import check_r11

        ceo_block = check_r11(message, channel=channel)
        if ceo_block is not None:
            print(f"R_CEO_FORMAT_BLOCKED: {ceo_block['detail']}", file=sys.stderr)
            print(f"  should_have: {ceo_block['should_have']}", file=sys.stderr)
            return 2
    except ImportError:
        pass  # repo not on sys.path; fall through ungated rather than break all posts
    # KEI-80: escalation-keyword scan — fires direct #ceo post BEFORE normal relay.
    # Failure of CEO post is non-fatal; normal relay always continues.
    _maybe_escalate_to_ceo(channel, message, CALLSIGN)
    result = post(channel, message)
    if not result.get("ok"):
        print(f"ERROR: Slack rejected: {result}", file=sys.stderr)
        return 1
    ts = result.get("ts", "")
    ch = result.get("channel", channel)
    print(f"→ {CALLSIGN_TAG} sent to Slack #{ch} (ts {ts})")
    # Layer-3 mechanical self-assignment (Dave directive ts ~1778584800).
    # On [READY:<callsign>] emission, fire bd ready + claim first unblocked
    # so the agent self-assigns immediately rather than waiting for the
    # 60s polling loop. Best-effort: subprocess failures log + drop.
    _maybe_self_assign(message)
    return 0


def _is_ready_marker(message: str, callsign: str) -> bool:
    """True iff message contains an ANCHORED [READY:<callsign>] state marker.

    v2 anchoring (Dave directive + Elliot dispatch ts ~1778586700) — fixes the
    false-positive from the empirical first-fire (PR #783 announce post had
    [READY:aiden] in PROSE describing the hook behaviour; the substring-anywhere
    match fired + claimed an unrelated P0 issue).

    Match position rules (any one matches → ready):
      - Start of message (optionally preceded by whitespace)
      - Start of any line in the message
      - Right after the callsign tag prefix '[<CALLSIGN>]' at start

    Prose mentions of '[READY:aiden]' embedded mid-sentence DO NOT match.
    """
    # `]` is a literal delimiter — no \b needed; the brackets themselves are
    # the bookends. Anchored at (start-of-string | newline) + optional callsign
    # tag prefix, so prose 'Next live [READY:aiden] emission' (mid-sentence)
    # does NOT match.
    pattern = re.compile(
        rf"(?:^|\n)\s*(?:\[{re.escape(callsign.upper())}\]\s*)?\[READY:{re.escape(callsign)}\]",
        re.IGNORECASE,
    )
    return bool(pattern.search(message))


# Clone callsigns never auto-claim primary build work — the polling loop is
# their canonical dispatch path. Empirical false-positives (Scout 2026-05-12
# on Agency_OS-dhe + Agency_OS-yvz: research [READY:scout] in doc-completion
# posts auto-claimed unrelated build issues) drove this guard. Polling loop
# itself is currently broken (Agency_OS-yvz) — clones go idle silently until
# that fix lands, which is preferable to the wrong-issue claim.
_CLONE_CALLSIGNS: frozenset[str] = frozenset({"atlas", "orion", "scout"})

# KEI-72: second-gate window for the Step-0-RESTATE auto-claim check.
# Scans this many most-recently-processed inbox messages for the agent's
# own [STEP-0-RESTATE:<callsign>] marker. Larger windows risk stale-claim
# (an old Step 0 from a different directive); smaller windows tighten the
# requirement but may miss legitimate Step 0s separated by peer chatter.
# 5 is Elliot's directive value.
_STEP0_INBOX_SCAN_DEPTH = 5
# Inbox base dir, env-overridable for tests. Defaults to /tmp which is the
# documented runtime location for the per-callsign relay inbox; tests override
# via AGENCY_OS_RELAY_INBOX_BASE. The S5443 suppression is the inline marker
# on the assignment below.
_RELAY_INBOX_BASE = os.environ.get("AGENCY_OS_RELAY_INBOX_BASE", "/tmp")  # NOSONAR


def _has_recent_step0_restate(callsign: str) -> bool:
    """KEI-72: True if a [STEP-0-RESTATE:<callsign>] marker appears in any of
    the last `_STEP0_INBOX_SCAN_DEPTH` processed inbox messages.

    Scans `<_RELAY_INBOX_BASE>/telegram-relay-<callsign>/processed/`.
    Messages there are JSON dicts with at least a `text` field; the relay
    listener moves files here once they're consumed. The agent's own
    Step-0-RESTATE outbound (posted via tg) is echoed back through the
    central listener into the same inbox, so this scan covers self-emitted
    markers.

    Returns False (and skips the auto-claim) when the marker isn't found —
    fail-fast at the validation layer. Closes the gap left by KEI-71 (which
    only handled the env-unset path).
    """
    inbox_processed = Path(_RELAY_INBOX_BASE) / f"telegram-relay-{callsign.lower()}" / "processed"
    if not inbox_processed.is_dir():
        return False
    needle = f"[STEP-0-RESTATE:{callsign.upper()}]"
    try:
        files = sorted(
            (p for p in inbox_processed.iterdir() if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:_STEP0_INBOX_SCAN_DEPTH]
    except OSError:
        return False
    for path in files:
        try:
            data = json.loads(path.read_text() or "{}")
        except (OSError, json.JSONDecodeError):
            continue
        text = data.get("text", "") or ""
        if needle in text:
            return True
    return False


def _maybe_self_assign(message: str) -> None:
    """If message contains an anchored [READY:<my-callsign>], try bd ready → bd claim.

    Best-effort + non-blocking: subprocess timeouts + missing bd binary log
    + return. Never raises. The polling loop is the safety net if this fails.

    Clones (atlas/orion/scout) skip-claim entirely — see _CLONE_CALLSIGNS.

    KEI-72: also refuse claim when there's no recent [STEP-0-RESTATE:<callsign>]
    marker in the last _STEP0_INBOX_SCAN_DEPTH inbox messages. Closes the
    'CALLSIGN-set-but-no-Step-0' auto-reclaim loop Elliot flagged at
    2026-05-14T09:08Z.
    """
    if CALLSIGN.lower() in _CLONE_CALLSIGNS:
        return
    if not _is_ready_marker(message, CALLSIGN):
        return
    if not _has_recent_step0_restate(CALLSIGN):
        print(
            f"[self-assign] refusing claim — no [STEP-0-RESTATE:{CALLSIGN.upper()}] "
            f"in the last {_STEP0_INBOX_SCAN_DEPTH} processed inbox messages. "
            "Agent must post a Step 0 RESTATE before slack_relay auto-claims (KEI-72).",
            file=sys.stderr,
        )
        return
    import subprocess as _sub

    try:
        proc = _sub.run(["bd", "ready", "--json"], capture_output=True, text=True, timeout=10)
    except (_sub.TimeoutExpired, OSError) as exc:
        print(f"[self-assign] bd ready unavailable: {exc}", file=sys.stderr)
        return
    if proc.returncode != 0:
        print(f"[self-assign] bd ready exit {proc.returncode}", file=sys.stderr)
        return
    try:
        issues = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        print(f"[self-assign] bd ready json parse: {exc}", file=sys.stderr)
        return
    if not issues:
        print("[self-assign] bd ready empty — nothing to claim", file=sys.stderr)
        return
    first_id = issues[0].get("id")
    if not first_id:
        return
    try:
        claim = _sub.run(
            ["bd", "update", first_id, "--claim"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (_sub.TimeoutExpired, OSError) as exc:
        print(f"[self-assign] bd claim unavailable: {exc}", file=sys.stderr)
        return
    if claim.returncode != 0:
        print(
            f"[self-assign] claim race on {first_id} (exit {claim.returncode}) — "
            f"falling back to polling-loop dispatch",
            file=sys.stderr,
        )
        return
    print(f"[self-assign] claimed {first_id} — work starts immediately", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
