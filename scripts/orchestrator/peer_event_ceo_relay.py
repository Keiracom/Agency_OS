#!/usr/bin/env python3
"""peer_event_ceo_relay.py — surface peer NATS events to Slack #ceo.

Closes the gap diagnosed 2026-05-19: elliot_stop_hook.py only sees elliot's
own assistant text. Peer events (atlas/orion/scout/nova/aiden/max stop hooks
publishing to keiracom.elliot.inbox + keiracom.review.<N>) arrive in elliot's
pane as user-injected text, never reach the stop-hook classifier. Result:
Dave saw no alerts from elliot about agent activity unless elliot wrote
a status post himself.

This service runs independently of elliot's session. It subscribes to the
two peer-event subjects, classifies each envelope, applies throttle + dedup,
and posts plain-English summaries to #ceo via slack_relay.py.

Subjects:
  - keiracom.elliot.inbox    — any peer-to-elliot completion/status
  - keiracom.review.>        — PR review verdicts (approve/HOLD)

Post triggers (per notification policy):
  - kind == "shipped"     → "**Agent shipped** — <author> finished <pr_or_task>"
  - kind == "blocker"     → "**Blocker** — <author> stuck on <topic>" (bypass throttle)
  - kind == "incident"    → "**Incident** — <author> reports <details>" (bypass throttle)
  - kind == "review"      → only if approval flips PR to dual-concur (state-tracked)
  - kind == "deliberation" → only on deadlock or final ratify candidate
  - kind == "status"      → IGNORED (too noisy)

Throttle: 60s cool-down per (kind, author) pair; blockers/incidents bypass.
Dedup: by SHA1(envelope.summary[:300] + envelope.from) within 5 minutes.

Fail-open per message: any error logged + skip; service stays up.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path

import nats

NATS_URL = os.environ.get("NATS_URL", "nats://127.0.0.1:4222")
SUBJECTS = ("keiracom.elliot.inbox", "keiracom.review.>")
STATE_PATH = Path("/tmp/peer_event_ceo_relay_state.json")
RELAY = "/home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py"
PYTHON = "/home/elliotbot/clawd/Agency_OS/.venv/bin/python3"
ENV_FILE = "/home/elliotbot/.config/agency-os/.env"

COOL_DOWN_SECONDS = 60
DEDUP_WINDOW_SECONDS = 300

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("peer_event_ceo_relay")

# Track per-PR concur progression for review kind. State: pr -> {approvers:set,
# holders:set, posted_merge_ready:bool, last_event_ts:float}
PR_STATE: dict[str, dict] = {}

# Throttle + dedup state
_throttle: dict[tuple, float] = {}
_dedup: dict[str, float] = {}


def _load_state() -> None:
    if not STATE_PATH.exists():
        return
    try:
        data = json.loads(STATE_PATH.read_text())
        for pr, s in data.get("pr_state", {}).items():
            PR_STATE[pr] = {
                "approvers": set(s.get("approvers", [])),
                "holders": set(s.get("holders", [])),
                "posted_merge_ready": s.get("posted_merge_ready", False),
                "last_event_ts": s.get("last_event_ts", 0),
            }
    except (OSError, json.JSONDecodeError) as e:
        log.warning("state load fail: %s", e)


def _save_state() -> None:
    try:
        STATE_PATH.write_text(json.dumps({
            "pr_state": {
                pr: {
                    "approvers": sorted(s["approvers"]),
                    "holders": sorted(s["holders"]),
                    "posted_merge_ready": s["posted_merge_ready"],
                    "last_event_ts": s["last_event_ts"],
                }
                for pr, s in PR_STATE.items()
            }
        }))
    except OSError as e:
        log.warning("state save fail: %s", e)


def _is_throttled(key: tuple) -> bool:
    now = time.time()
    last = _throttle.get(key, 0)
    return (now - last) < COOL_DOWN_SECONDS


def _is_duplicate(envelope: dict) -> bool:
    """SHA1(from + first 300 chars of summary) within DEDUP_WINDOW_SECONDS."""
    h = hashlib.sha1(
        (str(envelope.get("from", "")) + "::" + str(envelope.get("summary", ""))[:300]).encode()
    ).hexdigest()
    now = time.time()
    last = _dedup.get(h, 0)
    if (now - last) < DEDUP_WINDOW_SECONDS:
        return True
    _dedup[h] = now
    # cleanup old
    cutoff = now - DEDUP_WINDOW_SECONDS * 2
    for k, ts in list(_dedup.items()):
        if ts < cutoff:
            del _dedup[k]
    return False


REVIEW_VERDICT_RE = re.compile(
    r"\[REVIEW:(approve|HOLD)[:\s]+([a-z]+)\]|\[CONCUR:([a-z]+)\]",
    re.IGNORECASE,
)


def _extract_review_verdict(summary: str) -> tuple[str | None, str | None]:
    """Return (verdict, reviewer) — verdict in {'approve','hold'} or None."""
    m = REVIEW_VERDICT_RE.search(summary or "")
    if not m:
        return None, None
    if m.group(3):
        return "approve", m.group(3).lower()
    verdict = (m.group(1) or "").lower()
    reviewer = (m.group(2) or "").lower()
    return verdict, reviewer


def _post_ceo(category: str, body: str) -> None:
    """Send plain-English bullet block to #ceo via slack_relay."""
    msg = f"**{category}**\n{body}".rstrip()
    env = os.environ.copy()
    if "SLACK_BOT_TOKEN" not in env:
        try:
            for line in open(ENV_FILE):
                if line.startswith("SLACK_BOT_TOKEN="):
                    env["SLACK_BOT_TOKEN"] = line.split("=", 1)[1].strip()
                    break
        except OSError:
            pass
    env["CALLSIGN"] = "elliot"
    try:
        r = subprocess.run(
            [PYTHON, RELAY, "-c", "ceo", msg],
            capture_output=True, text=True, timeout=15, env=env, check=False,
        )
        if r.returncode != 0:
            log.warning("slack post failed rc=%d stderr=%s", r.returncode, r.stderr[:200])
        else:
            log.info("posted to #ceo: %s", category)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.warning("slack post err: %s", e)


def _summary_to_bullets(summary: str, max_bullets: int = 5) -> str:
    """Plain-English bullets, strip technical tokens per #ceo format gate."""
    if not summary:
        return "- (no detail)"
    lines = [s.strip() for s in summary.split("\n") if s.strip()]
    bullets: list[str] = []
    for ln in lines[:max_bullets * 3]:
        ln = re.sub(r"^[#*\-•]+\s*", "", ln).strip()
        if not ln:
            continue
        bullets.append(f"- {ln}")
        if len(bullets) >= max_bullets:
            break
    body = "\n".join(bullets)
    body = re.sub(r"PR\s*#\d+", "a PR", body, flags=re.IGNORECASE)
    body = re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", body)
    body = re.sub(r"/home/\S+", "<path>", body)
    body = re.sub(r"`[^`]+`", "<code>", body)
    body = re.sub(r"```[\s\S]+?```", "<code>", body)
    return body


def _handle_envelope(subject: str, envelope: dict) -> None:
    kind = (envelope.get("kind") or "").lower()
    sender = (envelope.get("from") or "unknown").lower()
    summary = envelope.get("summary") or ""

    if not summary or not summary.strip():
        return  # nothing to surface

    if _is_duplicate(envelope):
        log.debug("dup skip: from=%s kind=%s", sender, kind)
        return

    # Review verdicts — track approver/holder per PR, only post on flips
    if kind == "review":
        pr = envelope.get("pr_number") or _pr_from_subject(subject)
        if not pr:
            return
        verdict, reviewer = _extract_review_verdict(summary)
        if not verdict or not reviewer:
            return
        s = PR_STATE.setdefault(pr, {
            "approvers": set(), "holders": set(),
            "posted_merge_ready": False, "last_event_ts": 0,
        })
        s["last_event_ts"] = time.time()
        if verdict == "approve":
            s["approvers"].add(reviewer)
            s["holders"].discard(reviewer)
        else:
            s["holders"].add(reviewer)
            s["approvers"].discard(reviewer)
        _save_state()
        # Dual-concur intermediate state — Dave directive 2026-05-20: silent
        # (we'll batch the actual-merge events in the half-hourly digest)
        if len(s["approvers"]) >= 2 and not s["holders"] and not s["posted_merge_ready"]:
            s["posted_merge_ready"] = True
            _save_state()
        elif verdict == "hold" and not _is_throttled(("review_hold", sender, pr)):
            _throttle[("review_hold", sender, pr)] = time.time()
            body = (
                f"- {reviewer} holds a PR pending author fix\n"
                f"- One-line reason in the comment thread for the author\n"
                f"- Author has been dispatched"
            )
            _post_ceo("Reviewer HOLD", body)
        return

    if kind == "blocker":
        body = f"- Source: {sender}\n{_summary_to_bullets(summary, max_bullets=4)}"
        _post_ceo("Blocker — needs decision", body)
        return

    if kind == "incident":
        body = f"- Source: {sender}\n{_summary_to_bullets(summary, max_bullets=4)}"
        _post_ceo("Incident — critical state change", body)
        return

    if kind == "shipped":
        if _is_throttled(("shipped", sender)):
            return
        _throttle[("shipped", sender)] = time.time()
        body = f"- {sender} just completed a piece of work\n{_summary_to_bullets(summary, max_bullets=4)}"
        _post_ceo("Agent shipped", body)
        return

    if kind == "deliberation":
        # Only on deadlock or ratify candidate — keyword filter
        low = summary.lower()
        if "deadlock" in low or "ratify" in low or "ratification" in low:
            if _is_throttled(("deliberation", sender)):
                return
            _throttle[("deliberation", sender)] = time.time()
            body = f"- {sender} reports a deliberation milestone\n{_summary_to_bullets(summary, max_bullets=4)}"
            _post_ceo("Deliberation milestone", body)
        return

    # kind == 'status' or unknown — silent
    return


def _pr_from_subject(subject: str) -> str | None:
    """Extract PR number from subject like keiracom.review.<N>."""
    m = re.match(r"keiracom\.review\.(\d+)", subject)
    return m.group(1) if m else None


async def main() -> None:
    _load_state()
    nc = await nats.connect(NATS_URL)
    log.info("connected to NATS %s", NATS_URL)

    async def handler(msg: nats.aio.msg.Msg) -> None:  # type: ignore[name-defined]
        raw = msg.data.decode("utf-8", errors="replace")
        envelope: dict
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                envelope = parsed
            else:
                envelope = {"summary": str(parsed)}
        except json.JSONDecodeError:
            # Plain-text fallback: peer publishers on review subjects post
            # verdict comments as raw text. Synthesise an envelope so the
            # review-verdict tracker still updates dual-concur state.
            envelope = {
                "summary": raw,
                "kind": "review" if msg.subject.startswith("keiracom.review.") else "status",
            }
            # Try to extract sender from "[REVIEW:...:<callsign>]" tag
            m = re.search(r"\[REVIEW:(?:approve|HOLD)[:\s]+([a-z]+)\]|\[CONCUR:([a-z]+)\]", raw, re.I)
            if m:
                envelope["from"] = (m.group(1) or m.group(2) or "unknown").lower()
        try:
            _handle_envelope(msg.subject, envelope)
        except Exception as e:  # noqa: BLE001 fail-open
            log.warning("handler err: %s", e)

    for subj in SUBJECTS:
        await nc.subscribe(subj, cb=handler)
        log.info("subscribed: %s", subj)

    # Keep running
    while True:
        await asyncio.sleep(60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
