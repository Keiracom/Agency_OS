#!/usr/bin/env python3
"""slack_history_ingest.py — KEI-201: bulk Slack history → Weaviate slack_history.

One-shot bulk extractor that paginates conversations.history for the 5 named
channels, filters noise, classifies by message_type, and POSTs to Weaviate's
new `slack_history` collection.

Channels:
  #ceo, #execution, #completed_directives, #alerts, #ops

Filters:
  - [READY:callsign] heartbeats — pure noise
  - Fleet status posts that already mirror to agent_memories (KEI-200 covers)
  - Duplicates by content hash within a channel

Message-type classifier (regex on text + channel hint):
  - ceo_directive
  - agent_escalation
  - architectural_decision
  - supervisor_observation
  - completion_report
  - debug_session
  - governance_event

Target Weaviate class: `Slack_history` with text2vec-transformers vectorizer.

Usage:
    SLACK_BOT_TOKEN=xoxb-... python3 scripts/orchestrator/slack_history_ingest.py --dry-run
    SLACK_BOT_TOKEN=xoxb-... python3 scripts/orchestrator/slack_history_ingest.py --channel ceo --limit 500

The script is one-shot. The companion incremental daemon was decommissioned
on 2026-05-19 (Agency_OS-7377) when Slack relays were retired — see commit
history for slack_history_indexer.py. The Slack_history Weaviate collection
(14,772 messages) remains queryable; only the writer was removed.

Deterministic UUID per (channel, ts) tuple → re-ingest is idempotent (Weaviate
422 already-exists treated as no-op).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import logging
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts" / "orchestrator"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

logger = logging.getLogger("slack_history_ingest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CORPUS_CLASS = "Slack_history"
SOURCE_NAME = "slack_history"

WEAVIATE_HOST = os.environ.get("WEAVIATE_HOST", "127.0.0.1")
WEAVIATE_PORT = int(os.environ.get("WEAVIATE_PORT", "8090"))
WEAVIATE_BASE = f"http://{WEAVIATE_HOST}:{WEAVIATE_PORT}"  # NOSONAR

SLACK_API = "https://slack.com/api"
BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")  # for text2vec-google AI Studio auth

# Channel id → friendly slug used in metadata + filtering.
# The actual channel ids are looked up via conversations.list at runtime; this
# slug map is the canonical friendly-name set per ratification.
CHANNEL_SLUGS: tuple[str, ...] = (
    "ceo",
    "execution",
    "completed_directives",
    "alerts",
    "ops",
)

CORPUS_SCHEMA = {
    "class": CORPUS_CLASS,
    # Dave Option A (KEI-196 swap): text2vec-google over text2vec-transformers
    # — no self-hosted inference container. AI Studio endpoint (not Vertex)
    # avoids projectId requirement. modelId=gemini-embedding-001 is the AI Studio
    # name (KEI-196 commit 12cfaf93a's "text-embedding-004" is the Vertex name —
    # empirically 404s on AI Studio v1beta; gemini-embedding-001 is the supported
    # name per ListModels). Auth via X-Goog-Studio-Api-Key header per request.
    "vectorizer": "text2vec-google",
    "moduleConfig": {
        "text2vec-google": {
            "apiEndpoint": "generativelanguage.googleapis.com",
            "modelId": "gemini-embedding-001",
            "vectorizeClassName": False,
        }
    },
    "properties": [
        {"name": "raw_text", "dataType": ["text"]},
        {"name": "environment_hash", "dataType": ["text"]},
        {"name": "created_at", "dataType": ["date"]},
        {"name": "agent", "dataType": ["text"]},
        {"name": "kei", "dataType": ["text"]},
        {"name": "channel", "dataType": ["text"]},
        {"name": "message_type", "dataType": ["text"]},
        {"name": "ts", "dataType": ["text"]},
        {"name": "thread_ts", "dataType": ["text"]},
    ],
}


# ---------------------------------------------------------------------------
# Noise filters
# ---------------------------------------------------------------------------

_READY_HEARTBEAT_RE = re.compile(r"^\s*\[READY:[a-z0-9_-]+\]\s*$", re.IGNORECASE)
_FLEET_STATUS_RE = re.compile(
    r"^\s*(?:\[FLEET-?STATUS:[a-z0-9_-]+\]|\[SUPERVISOR\]\s+(?:fleet|cycle))",
    re.IGNORECASE,
)
_BARE_CALLSIGN_RE = re.compile(
    r"^\s*\[(?:atlas|orion|scout|nova|max|aiden|elliot|claude|dave)\]\s*$",
    re.IGNORECASE,
)
_VERCEL_RATELIMIT_RE = re.compile(
    r"vercel.*(?:rate.?limit|too many requests|429)|"
    r"(?:rate.?limit|too many requests|429).*vercel",
    re.IGNORECASE,
)


def is_noise(text: str) -> bool:
    """Return True if the message is a heartbeat / fleet-mirror / bare-ping / Vercel-throttle."""
    if not text or not text.strip():
        return True
    if _READY_HEARTBEAT_RE.match(text):
        return True
    if _FLEET_STATUS_RE.match(text):
        return True
    if _BARE_CALLSIGN_RE.match(text):
        return True
    if _VERCEL_RATELIMIT_RE.search(text):  # noqa: SIM103 — explicit return clearer than chain
        return True
    return False


# ---------------------------------------------------------------------------
# Message-type classifier
# ---------------------------------------------------------------------------

_TYPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Architectural decision — design or architecture ratification. Checked
    # FIRST so phrases like "3-way ratified" are classified as architectural,
    # not as a generic CEO directive (which the ratification ALSO matches).
    (
        "architectural_decision",
        re.compile(
            r"\[ARCH(ITECTURE)?|3-way (concur|ratified|locked)|"
            r"design (decision|ratification)|architecture (ratification|decision)",
            re.IGNORECASE,
        ),
    ),
    # CEO directive — Dave's instructions or solo ratifications
    (
        "ceo_directive",
        re.compile(
            r"\[(CEO|DIRECTIVE)|Dave (directive|verbatim|2026)|"
            r"AUTHORIZED|EXECUTION GREENLIT|PRIORITY OVERRIDE",
            re.IGNORECASE,
        ),
    ),
    # Agent escalation — flagging a blocker or asking for help
    (
        "agent_escalation",
        re.compile(
            r"\[(BLOCKED|ESCALATE|HOLD|HELP)|BLOCKER:|cannot|cannot proceed|"
            r"need (dave|elliot|aiden|max|atlas|orion|scout|nova)",
            re.IGNORECASE,
        ),
    ),
    # Supervisor observation — fleet supervisor detection + action
    (
        "supervisor_observation",
        re.compile(
            r"\[SUPERVISOR\]|fleet supervisor|claim filter|claim drift|"
            r"auto-?claim(ed)?|DRIFT-?RELEASE",
            re.IGNORECASE,
        ),
    ),
    # Completion report — task completion with evidence
    (
        "completion_report",
        re.compile(
            r"\[(SHIPPED|MERGED|DONE|COMPLETED?)|bd complete|merged at|"
            r"PR #\d+ (merged|shipped|complete)",
            re.IGNORECASE,
        ),
    ),
    # Debug session — problem diagnosis and resolution
    (
        "debug_session",
        re.compile(
            r"\[(DIAGNOSIS|DEBUG|ROOT-?CAUSE|TRACE)|"
            r"root cause|verbatim grep|empirical (probe|check|smoke)",
            re.IGNORECASE,
        ),
    ),
    # Governance event — CONCUR / HOLD / ratification
    (
        "governance_event",
        re.compile(
            r"\[(CONCUR|HOLD|REVIEW|APPROVE|DEDUP|RETRACT)|"
            r"\[REVIEW:(approve|HOLD):|CONCUR-?LOCK",
            re.IGNORECASE,
        ),
    ),
)

_DEFAULT_TYPE = "agent_chatter"  # fallback for messages that don't match any pattern


def classify_message(text: str) -> str:
    """Return one of the 7 ratified message_types, or 'agent_chatter' as fallback."""
    for label, pattern in _TYPE_PATTERNS:
        if pattern.search(text):
            return label
    return _DEFAULT_TYPE


# ---------------------------------------------------------------------------
# Slack pagination
# ---------------------------------------------------------------------------


def _slack_get(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Call a Slack Web API method. Raises on non-2xx + non-ok responses."""
    if not BOT_TOKEN:
        raise SystemExit("SLACK_BOT_TOKEN not set — required for history extract")
    qs = "&".join(f"{k}={urlrequest.quote(str(v))}" for k, v in params.items())
    url = f"{SLACK_API}/{method}?{qs}"
    req = urlrequest.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {BOT_TOKEN}")
    with urlrequest.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    if not body.get("ok"):
        raise RuntimeError(f"slack.{method} failed: {body.get('error', 'unknown')}")
    return body


def resolve_channel_ids(slugs: tuple[str, ...]) -> dict[str, str]:
    """Return {slug: channel_id} via conversations.list — slug = name without '#'."""
    mapping: dict[str, str] = {}
    cursor = ""
    while True:
        params: dict[str, Any] = {"limit": 200, "exclude_archived": True}
        if cursor:
            params["cursor"] = cursor
        body = _slack_get("conversations.list", params)
        for ch in body.get("channels", []) or []:
            name = ch.get("name", "")
            if name in slugs:
                mapping[name] = ch.get("id", "")
        cursor = body.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            break
    return mapping


def paginate_history(
    channel_id: str,
    limit_per_page: int = 200,
    total_cap: int = 100_000,
    oldest: str = "",
):
    """Yield message dicts from conversations.history for one channel.

    Sleeps 1.0s between pages to stay well under Slack's tier-2 rate limit
    (20 req/min on conversations.history for many workspaces).

    `oldest`: if set (Slack ts like "1779065531.123456"), only messages with
    ts > oldest are returned — used by the incremental indexer for the
    since-last-checkpoint window.
    """
    cursor = ""
    yielded = 0
    while yielded < total_cap:
        params: dict[str, Any] = {"channel": channel_id, "limit": limit_per_page}
        if cursor:
            params["cursor"] = cursor
        if oldest:
            params["oldest"] = oldest
        try:
            body = _slack_get("conversations.history", params)
        except (urlerror.URLError, urlerror.HTTPError, RuntimeError) as exc:
            logger.warning(
                "conversations.history %s page failed: %s — stopping early", channel_id, exc
            )
            return
        for msg in body.get("messages", []) or []:
            yield msg
            yielded += 1
            if yielded >= total_cap:
                return
        cursor = body.get("response_metadata", {}).get("next_cursor", "")
        if not cursor:
            return
        time.sleep(1.0)


# ---------------------------------------------------------------------------
# Message → Weaviate object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SlackMessage:
    channel: str  # slug like 'ceo'
    ts: str  # Slack ts like '1779065531.123456'
    text: str
    user: str
    thread_ts: str
    message_type: str

    def deterministic_id(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"slack:{self.channel}:{self.ts}"))

    def env_hash(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:16]


def slack_to_message(channel_slug: str, raw: dict[str, Any]) -> SlackMessage | None:
    """Convert a Slack message dict to a SlackMessage, or None if it's noise."""
    text = (raw.get("text") or "").strip()
    if is_noise(text):
        return None
    ts = raw.get("ts", "")
    if not ts:
        return None
    user = raw.get("user") or raw.get("bot_id") or "unknown"
    thread_ts = raw.get("thread_ts", "") or ""
    return SlackMessage(
        channel=channel_slug,
        ts=ts,
        text=text,
        user=user,
        thread_ts=thread_ts,
        message_type=classify_message(text),
    )


def build_object(msg: SlackMessage) -> dict[str, Any]:
    """Build a Weaviate object payload for one Slack message."""
    # Convert Slack ts (unix seconds float as string) to ISO 8601.
    try:
        unix = float(msg.ts)
        iso = _dt.datetime.fromtimestamp(unix, tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, OverflowError):
        iso = ""
    return {
        "class": CORPUS_CLASS,
        "id": msg.deterministic_id(),
        "properties": {
            "raw_text": msg.text,
            "environment_hash": msg.env_hash(),
            "created_at": iso,
            "agent": msg.user,
            "kei": "KEI-201",
            "channel": msg.channel,
            "message_type": msg.message_type,
            "ts": msg.ts,
            "thread_ts": msg.thread_ts,
        },
    }


def post_object(obj: dict[str, Any]) -> bool:
    """POST one object to Weaviate. Returns True on 200/422 (idempotent).

    Sends X-Goog-Studio-Api-Key header so Weaviate's text2vec-google module can
    auth against AI Studio (Weaviate process does not have GOOGLE_APIKEY in
    its env — see KEI-196 swap notes).
    """
    data = json.dumps(obj).encode()
    req = urlrequest.Request(f"{WEAVIATE_BASE}/v1/objects", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if GOOGLE_API_KEY:
        req.add_header("X-Goog-Studio-Api-Key", GOOGLE_API_KEY)
    try:
        with urlrequest.urlopen(req, timeout=30) as resp:
            return resp.status in (200, 201)
    except urlerror.HTTPError as exc:
        if exc.code == 422:
            return True  # already exists — idempotent
        logger.warning("post_object %s failed: %s", obj.get("id"), exc)
        return False
    except urlerror.URLError as exc:
        logger.warning("post_object %s transport error: %s", obj.get("id"), exc)
        return False


def ensure_class() -> None:
    """Idempotent class create (404 → POST schema)."""
    req = urlrequest.Request(f"{WEAVIATE_BASE}/v1/schema/{CORPUS_CLASS}", method="GET")
    try:
        with urlrequest.urlopen(req, timeout=30):
            return
    except urlerror.HTTPError as exc:
        if exc.code != 404:
            raise
    data = json.dumps(CORPUS_SCHEMA).encode()
    req = urlrequest.Request(f"{WEAVIATE_BASE}/v1/schema", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlrequest.urlopen(req, timeout=30) as resp:
        resp.read()
    logger.info("created class %s", CORPUS_CLASS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="parse + count, do not POST to Weaviate",
    )
    parser.add_argument(
        "--channel",
        choices=CHANNEL_SLUGS,
        default=None,
        help="restrict to one channel (default: all 5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10_000,
        help="max messages per channel (default 10k; bumps higher for full backfill)",
    )
    return parser


def _process_channel(
    slug: str,
    ch_id: str,
    limit: int,
    dry_run: bool,
    by_type: dict[str, int],
) -> tuple[int, int, int, int]:
    """Returns (kept, posted, failed, noise) for one channel."""
    kept = posted = failed = noise = 0
    for raw in paginate_history(ch_id, total_cap=limit):
        msg = slack_to_message(slug, raw)
        if msg is None:
            noise += 1
            continue
        by_type[msg.message_type] = by_type.get(msg.message_type, 0) + 1
        kept += 1
        if dry_run:
            continue
        if post_object(build_object(msg)):
            posted += 1
        else:
            failed += 1
    return kept, posted, failed, noise


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    channels = (args.channel,) if args.channel else CHANNEL_SLUGS
    if not BOT_TOKEN:
        logger.error("SLACK_BOT_TOKEN not set — required for history extract")
        return 1

    if not args.dry_run:
        ensure_class()

    channel_ids = resolve_channel_ids(channels)
    if not channel_ids:
        logger.error("none of the named channels resolved — check bot permissions")
        return 2

    by_channel: dict[str, int] = {}
    by_type: dict[str, int] = {}
    total_posted = total_noise = total_failed = 0

    for slug in channels:
        ch_id = channel_ids.get(slug)
        if not ch_id:
            logger.warning("channel #%s did not resolve — skipping", slug)
            continue
        logger.info("extracting #%s (%s, limit=%d)", slug, ch_id, args.limit)
        kept, posted, failed, noise = _process_channel(
            slug, ch_id, args.limit, args.dry_run, by_type
        )
        by_channel[slug] = kept
        total_posted += posted
        total_failed += failed
        total_noise += noise
        logger.info("#%s done: %d messages kept", slug, kept)

    logger.info(
        "summary: by_channel=%s by_type=%s skipped_noise=%d posted=%d failed=%d",
        json.dumps(by_channel),
        json.dumps(by_type),
        total_noise,
        total_posted,
        total_failed,
    )
    return 0 if total_failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
