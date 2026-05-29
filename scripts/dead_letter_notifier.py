#!/usr/bin/env python3
"""dead_letter_notifier.py — dead-letter → #ceo notification (Agency_OS-gl3v).

Rehearsal pre-condition P6 + Run-D gate. When the work-loop consumer dead-letters
a task (after DEAD_LETTER_MAX_ATTEMPTS failed attempts), this fires a Slack #ceo
message within 60s containing: task id, what it was doing, retry count, final
error. The dead-lettered row STAYS in public.tasks (audit history — never deleted
by this notifier).

Non-negotiable for solo operation: a silently-dropped task destroys trust. This
watcher guarantees every dead-letter is surfaced to Dave.

Design: a standalone outbound watcher (NOT the inbound Socket Mode listener). It
polls public.tasks for dead-lettered rows every DEAD_LETTER_POLL_SECONDS (< 60s)
and posts each new one to #ceo. Boot-seed dedup: rows already dead-lettered at
startup are seeded as "notified" so a restart never replays old dead-letters.

Fail-open: a query / Slack / DB error logs and is retried next poll; the watcher
never crashes (a crashed notifier is itself a silent-drop).

CONTRACT (flagged to Atlas — the consumer's dead-letter impl must provide these):
  public.tasks dead-lettered row = status = DEAD_LETTER_STATUS ('dead_letter'),
  with retry_count + last_error columns populated. The #1283 confirmed schema does
  NOT yet have retry_count/last_error — until they land, the message degrades
  gracefully (retry='unknown', error='(not captured — see consumer logs)').

Stdlib only; psycopg lazy-imported on the live path.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("dead_letter_notifier")

CEO_CHANNEL = os.environ.get("CEO_DEAD_LETTER_CHANNEL", "C0B2PM3TV0B")
DEAD_LETTER_STATUS = os.environ.get("DEAD_LETTER_STATUS", "dead_letter")
DEAD_LETTER_MAX_ATTEMPTS = int(os.environ.get("DEAD_LETTER_MAX_ATTEMPTS", "3"))
POLL_SECONDS = float(os.environ.get("DEAD_LETTER_POLL_SECONDS", "30"))  # < 60s SLA
SLACK_POST_URL = "https://slack.com/api/chat.postMessage"  # NOSONAR S5332
# Contract columns on public.tasks (flagged — confirm with Atlas / producer stack).
RETRY_COL = os.environ.get("DEAD_LETTER_RETRY_COL", "retry_count")
ERROR_COL = os.environ.get("DEAD_LETTER_ERROR_COL", "last_error")


@dataclass(frozen=True)
class DeadLetterTask:
    task_id: str
    description: str  # what it was doing (the task title)
    retry_count: int | None  # None = not captured by the consumer yet
    final_error: str


def row_to_dead_letter(row: dict) -> DeadLetterTask:
    """Map a public.tasks dead-lettered row to a DeadLetterTask (defensive — the
    retry/error columns may not exist yet; absent → None/empty, message degrades)."""
    rc = row.get(RETRY_COL)
    return DeadLetterTask(
        task_id=str(row.get("id", "")),
        description=str(row.get("title") or ""),
        retry_count=int(rc) if rc is not None else None,
        final_error=str(row.get(ERROR_COL) or ""),
    )


def format_dead_letter_message(dlt: DeadLetterTask) -> str:
    """The #ceo message: task id, what it was doing, retry count, final error.
    Degrades gracefully when the consumer has not captured retry/error yet."""
    retry = dlt.retry_count if dlt.retry_count is not None else "unknown"
    err = dlt.final_error.strip() or "(not captured — see consumer logs)"
    # Plain-text marker (not an emoji) so it renders identically in every Slack
    # client — Aiden flag 2026-05-29.
    return (
        f"[DEAD-LETTER] task `{dlt.task_id}` dropped after {retry} attempts.\n"
        f"• What it was doing: {dlt.description or '(no title)'}\n"
        f"• Retry count: {retry}\n"
        f"• Final error: {err}\n"
        f"• Row retained in `public.tasks` (status=`{DEAD_LETTER_STATUS}`) for audit — not deleted."
    )


def post_dead_letter(
    dlt: DeadLetterTask, *, token: str | None = None, channel: str = CEO_CHANNEL
) -> bool:
    """Fire-and-forget post to #ceo. Fail-open — a notify outage logs locally and
    is retried next poll; it never crashes the watcher."""
    text = format_dead_letter_message(dlt)
    token = token or os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("no SLACK_BOT_TOKEN — dead-letter (local log only):\n%s", text)
        return False
    body = json.dumps({"channel": channel, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        SLACK_POST_URL,
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception:  # noqa: BLE001 — notify must never crash the watcher
        logger.warning(
            "dead-letter #ceo post failed for %s — retry next poll", dlt.task_id, exc_info=True
        )
        return False


def notify_new_dead_letters(
    rows: list[dict], notified: set, *, token: str | None = None, post=post_dead_letter
) -> int:
    """Post each not-yet-notified dead-letter; record it. Returns count posted.
    Mutates `notified` so each dead-letter fires exactly once per process run."""
    count = 0
    for row in rows:
        task_id = str(row.get("id", ""))
        if not task_id or task_id in notified:
            continue
        if post(row_to_dead_letter(row), token=token):
            count += 1
        notified.add(task_id)  # record even on post-failure: avoid spam; failure is logged
    return count


def _connect(dsn: str):
    import psycopg

    return psycopg.connect(
        dsn.replace("postgresql+asyncpg://", "postgresql://", 1), autocommit=True
    )


def fetch_dead_lettered(dsn: str) -> list[dict]:
    """SELECT dead-lettered public.tasks rows (contract: status + retry/error cols)."""
    sql = f"SELECT id, title, {RETRY_COL}, {ERROR_COL} FROM public.tasks WHERE status = %s"
    with _connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(sql, (DEAD_LETTER_STATUS,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def seed_notified(dsn: str) -> set:
    """Boot-seed: rows already dead-lettered at startup are 'notified' so a restart
    never replays old dead-letters (only NEW ones after boot fire)."""
    try:
        return {str(r.get("id", "")) for r in fetch_dead_lettered(dsn)}
    except Exception:  # noqa: BLE001
        logger.warning("dead-letter seed query failed — starting with empty set", exc_info=True)
        return set()


def main() -> int:
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("RETRIEVAL_EVENTS_DSN")
    if not dsn:
        logger.error("no DATABASE_URL/RETRIEVAL_EVENTS_DSN — dead-letter notifier cannot run")
        return 2
    notified = seed_notified(dsn)
    logger.info(
        "dead_letter_notifier up — channel=%s status=%s poll=%ss (seeded %d existing)",
        CEO_CHANNEL,
        DEAD_LETTER_STATUS,
        POLL_SECONDS,
        len(notified),
    )
    while True:
        try:
            posted = notify_new_dead_letters(fetch_dead_lettered(dsn), notified)
            if posted:
                logger.info("posted %d new dead-letter(s) to #ceo", posted)
        except Exception:  # noqa: BLE001 — a crashed notifier is itself a silent-drop
            logger.warning("dead-letter poll failed (non-fatal) — retry next cycle", exc_info=True)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
