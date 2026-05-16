#!/usr/bin/env python3
"""auto_kei_enforcer.py — KEI-18 R12 enforcer (Dave-direct 2026-05-16).

One cron, one query, one notification:

    Every 1-2 min: scan #ceo last 7 min. For each message that has aged
    past the 5-min grace window (i.e. 5-7 min old), query public.tasks
    for any row created in [msg.ts, msg.ts + 5 min]. If zero rows: post
    an alert to #execution tagging Elliot to file it as a KEI.

Dedupe via state file at ~/.local/state/agency-os/auto-kei-alerted.txt
(one Slack ts per line). The state file is the only side-effect besides
the Slack alert; safe to delete to re-fire stale alerts.

Env:
    SLACK_BOT_TOKEN    (required) — same xoxb-... used by slack_relay.py
    DATABASE_URL       (required) — Supabase postgres DSN
    CHANNEL_CEO_ID     (default C0B2PM3TV0B) — #ceo channel id
    CHANNEL_ALERT_ID   (default C0B3QB0K1GQ) — #execution channel id
    KEI18_GRACE_SECONDS   (default 300) — wait window before alerting
    KEI18_SCAN_WINDOW_SECONDS (default 420) — total back-look window
    DRY_RUN            (default false) — when true, print but don't post

Run: python3 scripts/auto_kei_enforcer.py [--once|--loop]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("auto_kei_enforcer")

CHANNEL_CEO = os.environ.get("CHANNEL_CEO_ID", "C0B2PM3TV0B")
CHANNEL_ALERT = os.environ.get("CHANNEL_ALERT_ID", "C0B3QB0K1GQ")
GRACE_SECONDS = int(os.environ.get("KEI18_GRACE_SECONDS", "300"))
SCAN_WINDOW_SECONDS = int(os.environ.get("KEI18_SCAN_WINDOW_SECONDS", "420"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
ALERTED_STATE_PATH = Path(
    os.path.expanduser("~/.local/state/agency-os/auto-kei-alerted.txt")
)


def slack_get(method: str, params: dict) -> dict:
    """GET against Slack web API. Returns parsed JSON."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set")
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    req = urlrequest.Request(
        f"https://slack.com/api/{method}?{qs}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urlrequest.urlopen(req, timeout=15) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def slack_post(channel: str, text: str) -> dict:
    """POST chat.postMessage. Returns parsed response."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN not set")
    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urlrequest.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=15) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def read_ceo_messages(now: float) -> list[dict]:
    """Read #ceo channel for messages in [now-SCAN_WINDOW, now-GRACE]."""
    oldest = now - SCAN_WINDOW_SECONDS
    latest = now - GRACE_SECONDS
    resp = slack_get("conversations.history", {
        "channel": CHANNEL_CEO,
        "oldest": f"{oldest:.6f}",
        "latest": f"{latest:.6f}",
        "limit": "50",
    })
    if not resp.get("ok"):
        log.warning("slack history error: %s", resp.get("error"))
        return []
    return resp.get("messages", []) or []


def count_tasks_since(ts_iso: str, window_seconds: int = 300) -> int:
    """Query public.tasks for rows created in [ts, ts+window_seconds] via psycopg."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("RETRIEVAL_EVENTS_DSN")
    if not dsn:
        log.warning("DATABASE_URL not set; cannot cross-check tasks")
        return -1
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
    import psycopg  # local import — only needed when DSN is set
    with (
        psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT count(*) FROM public.tasks "
            "WHERE created_at >= %s::timestamptz "
            "AND created_at <= %s::timestamptz + interval '5 minutes'",
            (ts_iso, ts_iso),
        )
        return int(cur.fetchone()[0])


def load_alerted_set() -> set[str]:
    if not ALERTED_STATE_PATH.exists():
        return set()
    return {
        line.strip()
        for line in ALERTED_STATE_PATH.read_text().splitlines()
        if line.strip()
    }


def record_alerted(ts: str) -> None:
    ALERTED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTED_STATE_PATH.open("a") as f:
        f.write(f"{ts}\n")


def prune_alerted(alerted: set[str], now: float) -> set[str]:
    """Drop entries older than 24h to keep state file small."""
    cutoff = now - 86400
    kept = {ts for ts in alerted if _ts_to_unix(ts) > cutoff}
    if kept != alerted:
        ALERTED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        ALERTED_STATE_PATH.write_text("\n".join(sorted(kept)) + ("\n" if kept else ""))
    return kept


def _ts_to_unix(ts: str) -> float:
    try:
        return float(ts)
    except ValueError:
        return 0.0


def format_alert(msg: dict) -> str:
    ts = msg.get("ts", "?")
    user = msg.get("user", "?")
    text = (msg.get("text") or "").replace("\n", " ")[:300]
    msg_dt = datetime.fromtimestamp(_ts_to_unix(ts), tz=timezone.utc).isoformat()
    return (
        f"[ATLAS-AUTO-KEI] #ceo message at {msg_dt} (user={user}) has no "
        f"tasks row created within 5 min. Elliot — file as KEI.\n"
        f"> {text}"
    )


def scan_once(now: float | None = None) -> dict:
    now = now or time.time()
    messages = read_ceo_messages(now)
    log.info("scan: %d #ceo messages in 5-7 min window", len(messages))
    alerted = prune_alerted(load_alerted_set(), now)
    new_alerts = 0
    skipped_already = 0
    skipped_with_tasks = 0
    for msg in messages:
        ts = msg.get("ts", "")
        if not ts or msg.get("subtype") in {"channel_join", "channel_leave", "bot_message"}:
            continue
        if ts in alerted:
            skipped_already += 1
            continue
        msg_iso = datetime.fromtimestamp(_ts_to_unix(ts), tz=timezone.utc).isoformat()
        n = count_tasks_since(msg_iso)
        if n == -1:
            log.warning("skipping %s: no DSN", ts)
            continue
        if n > 0:
            skipped_with_tasks += 1
            continue
        alert_text = format_alert(msg)
        log.warning("ALERT: %s", alert_text[:200])
        if DRY_RUN:
            log.info("[DRY_RUN] would post to %s + record %s", CHANNEL_ALERT, ts)
            new_alerts += 1
            continue
        resp = slack_post(CHANNEL_ALERT, alert_text)
        if not resp.get("ok"):
            log.error("slack post failed: %s", resp.get("error"))
            continue
        record_alerted(ts)
        new_alerts += 1
    return {
        "messages_scanned": len(messages),
        "new_alerts": new_alerts,
        "skipped_already_alerted": skipped_already,
        "skipped_with_tasks": skipped_with_tasks,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run one scan + exit")
    ap.add_argument("--loop", action="store_true", help="run scan every 90s")
    args = ap.parse_args(argv)
    if not args.once and not args.loop:
        args.once = True
    if args.once:
        summary = scan_once()
        print(json.dumps(summary))
        return 0
    while True:
        try:
            summary = scan_once()
            log.info("loop summary: %s", json.dumps(summary))
        except Exception:  # noqa: BLE001
            log.exception("scan failed")
        time.sleep(90)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
