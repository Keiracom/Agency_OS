#!/usr/bin/env python3
"""artifact_freshness_monitor.py — daily artifact-staleness sweep.

Per Dave System Health Monitoring directive 2026-05-12 Outcome 4:
  "Artifact freshness crons (ceo_memory >30d, pins >14d,
   completed_directives >60d)."

Three independent checks, each posts ONE summary alert to #execution on
non-zero stale count:

  1. ceo_memory_stale       — ceo:* entries (excl. _complete suffix) not
                              updated in 30 days → governance debt signal.
  2. slack_pins_stale       — pinned messages in #execution + #ceo older
                              than 14 days → archive candidate.
  3. completed_directives_stale — ceo:*_complete keys older than 60 days →
                              archive candidate.

Best-effort: a Slack-post failure does NOT raise. Each check is independent
— failure in one does not skip the others.

Run via timer: agency-os-artifact-freshness-monitor.timer (OnCalendar daily).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("artifact_freshness_monitor")

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
CEO_CHANNEL = "C0B3R4PV4HN"  # #ceo

CEO_MEMORY_STALE_DAYS = 30
SLACK_PIN_STALE_DAYS = 14
COMPLETED_DIRECTIVE_STALE_DAYS = 60

PINS_CHANNELS = (("execution", EXECUTION_CHANNEL), ("ceo", CEO_CHANNEL))


# ─────────────────────────────────────────────────────────────────────────────
# ceo_memory checks
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_ceo_memory_rows() -> list[dict]:
    """All rows from ceo_memory with key + updated_at. Empty on failure."""
    try:
        sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")
        from src.evo.supabase_client import sb_get  # noqa: E402
    except ImportError as exc:
        logger.warning("supabase_client import failed: %s", exc)
        return []
    try:
        return sb_get("ceo_memory", {"select": "key,updated_at"})
    except Exception as exc:
        logger.warning("ceo_memory SELECT failed: %s", exc)
        return []


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def check_ceo_memory_stale(rows: list[dict], now: datetime) -> list[dict]:
    """Return ceo:* entries (excl. _complete suffix) older than threshold."""
    threshold = now - timedelta(days=CEO_MEMORY_STALE_DAYS)
    stale: list[dict] = []
    for r in rows:
        key = r.get("key", "")
        if key.endswith("_complete"):
            continue
        updated = _parse_iso(r.get("updated_at", ""))
        if updated is None or updated >= threshold:
            continue
        stale.append({"key": key, "updated_at": r["updated_at"], "age_days": (now - updated).days})
    stale.sort(key=lambda x: x["age_days"], reverse=True)
    return stale


def check_completed_directives_stale(rows: list[dict], now: datetime) -> list[dict]:
    """Return ceo:*_complete entries older than threshold (archive candidates)."""
    threshold = now - timedelta(days=COMPLETED_DIRECTIVE_STALE_DAYS)
    stale: list[dict] = []
    for r in rows:
        key = r.get("key", "")
        if not key.endswith("_complete"):
            continue
        updated = _parse_iso(r.get("updated_at", ""))
        if updated is None or updated >= threshold:
            continue
        stale.append({"key": key, "updated_at": r["updated_at"], "age_days": (now - updated).days})
    stale.sort(key=lambda x: x["age_days"], reverse=True)
    return stale


# ─────────────────────────────────────────────────────────────────────────────
# Slack pins check
# ─────────────────────────────────────────────────────────────────────────────


def _slack_get(method: str, params: dict) -> dict:
    """GET https://slack.com/api/<method>?... → parsed JSON. {} on failure."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        return {}
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://slack.com/api/{method}?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Slack GET %s failed: %s", method, exc)
        return {}


def check_slack_pins_stale(now: datetime) -> list[dict]:
    """Return pinned messages in PINS_CHANNELS older than 14 days."""
    threshold_ts = (now - timedelta(days=SLACK_PIN_STALE_DAYS)).timestamp()
    stale: list[dict] = []
    for label, channel_id in PINS_CHANNELS:
        body = _slack_get("pins.list", {"channel": channel_id})
        if not body.get("ok"):
            continue
        for item in body.get("items", []):
            created = float(item.get("created", 0))
            if created and created < threshold_ts:
                age_days = int((now.timestamp() - created) / 86400)
                stale.append(
                    {
                        "channel": label,
                        "type": item.get("type", "?"),
                        "created": created,
                        "age_days": age_days,
                    }
                )
    stale.sort(key=lambda x: x["age_days"], reverse=True)
    return stale


# ─────────────────────────────────────────────────────────────────────────────
# Slack post
# ─────────────────────────────────────────────────────────────────────────────


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    """Best-effort Slack post. Returns True on success."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post freshness alert")
        return False
    payload = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "ArtifactFreshness",
            "icon_emoji": ":hourglass_flowing_sand:",
        }
    ).encode("utf-8")
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
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            return bool(body.get("ok"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Slack post failed: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────────────────────────────────────────


def format_ceo_memory_alert(stale: list[dict]) -> str:
    sample = "\n".join(f"  · {s['key']} ({s['age_days']}d)" for s in stale[:10])
    return (
        f"[ARTIFACT-FRESHNESS] ceo_memory — {len(stale)} entries stale "
        f"(>{CEO_MEMORY_STALE_DAYS}d). Top oldest:\n```\n{sample}\n```"
    )


def format_completed_directives_alert(stale: list[dict]) -> str:
    sample = "\n".join(f"  · {s['key']} ({s['age_days']}d)" for s in stale[:10])
    return (
        f"[ARTIFACT-FRESHNESS] completed_directives — {len(stale)} entries "
        f"archive-candidate (>{COMPLETED_DIRECTIVE_STALE_DAYS}d). Top oldest:\n"
        f"```\n{sample}\n```"
    )


def format_slack_pins_alert(stale: list[dict]) -> str:
    sample = "\n".join(f"  · #{s['channel']} {s['type']} ({s['age_days']}d)" for s in stale[:10])
    return (
        f"[ARTIFACT-FRESHNESS] slack_pins — {len(stale)} pin(s) stale "
        f"(>{SLACK_PIN_STALE_DAYS}d). Top oldest:\n```\n{sample}\n```"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    now = datetime.now(UTC)
    rows = _fetch_ceo_memory_rows()
    logger.info("Fetched %d ceo_memory rows", len(rows))

    ceo_stale = check_ceo_memory_stale(rows, now)
    dirs_stale = check_completed_directives_stale(rows, now)
    pins_stale = check_slack_pins_stale(now)

    logger.info(
        "Stale counts: ceo_memory=%d completed_directives=%d slack_pins=%d",
        len(ceo_stale),
        len(dirs_stale),
        len(pins_stale),
    )

    if ceo_stale:
        post_to_slack(format_ceo_memory_alert(ceo_stale))
    if dirs_stale:
        post_to_slack(format_completed_directives_alert(dirs_stale))
    if pins_stale:
        post_to_slack(format_slack_pins_alert(pins_stale))

    return 0


if __name__ == "__main__":
    sys.exit(main())
