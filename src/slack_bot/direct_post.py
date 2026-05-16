"""src/slack_bot/direct_post.py — KEI-79 Option D hybrid #ceo post.

bd escalate calls post_to_ceo() synchronously. On Slack API failure
(network/429/5xx) it falls back to enqueueing a completion_sync_queue
row with target_sink='ceo_post_retry'; the existing KEI-74 worker
drains it on the regular cadence. ceo_decision_id is the idempotency
key — worker checks ceo_decisions.slack_ts IS NULL before re-posting.

Returns dict {status: 'posted'|'queued_retry', ok: bool, ts: str|None}.
"""

from __future__ import annotations

import contextlib
import json
import os
from typing import Any
from urllib import error as urlerror
from urllib import request as urlrequest

CEO_CHANNEL = "C0B2PM3TV0B"
SLACK_API = "https://slack.com/api/chat.postMessage"


def _post_via_urllib(text: str, blocks: list[dict] | None) -> dict[str, Any]:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN missing")
    payload: dict[str, Any] = {"channel": CEO_CHANNEL, "text": text}
    if blocks:
        payload["blocks"] = blocks
    req = urlrequest.Request(
        SLACK_API,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    with urlrequest.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read())
    if not body.get("ok"):
        raise RuntimeError(f"slack rejected: {body.get('error') or body}")
    return body


def _enqueue_retry(ceo_decision_id: str, error: str) -> None:
    import psycopg

    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not dsn:
        return
    dsn = dsn.replace("+asyncpg", "")
    with (
        psycopg.connect(dsn, prepare_threshold=None, autocommit=True) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "INSERT INTO public.completion_sync_queue "
            "(task_id, target_sink, target_status, error_message) "
            "VALUES (%s, 'ceo_post_retry', 'pending', %s) "
            "ON CONFLICT (task_id, target_sink) WHERE processed = FALSE DO UPDATE "
            "SET error_message = EXCLUDED.error_message, updated_at = NOW()",
            (ceo_decision_id, error[:500]),
        )


def post_to_ceo(
    text: str,
    blocks: list[dict] | None = None,
    ceo_decision_id: str | None = None,
) -> dict[str, Any]:
    """Post to #ceo via Slack API; fall back to completion_sync_queue on failure."""
    try:
        body = _post_via_urllib(text, blocks)
        return {"status": "posted", "ok": True, "ts": body.get("ts")}
    except (urlerror.URLError, OSError, RuntimeError) as exc:
        if ceo_decision_id:
            with contextlib.suppress(Exception):
                _enqueue_retry(ceo_decision_id, str(exc))
        return {"status": "queued_retry", "ok": False, "ts": None, "error": str(exc)}
