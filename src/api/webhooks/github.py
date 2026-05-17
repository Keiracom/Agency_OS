"""src/api/webhooks/github.py — GitHub → public.tasks inbound sync webhook.

KEI-97 Part A1: Receives GitHub webhook POSTs at /api/webhooks/github,
verifies HMAC-SHA-256 signature against GITHUB_WEBHOOK_SECRET, and manages
review-task rows in public.tasks for pull_request events.

Event handling:
  - pull_request.opened / reopened / synchronize
      → INSERT/UPSERT REVIEW-PR-{number} row with status='available'
  - pull_request.closed (merged or not)
      → UPDATE status='done' with KEI-84 never-downgrade guard

Fail-open discipline:
  - HMAC verify: 401 on missing header or mismatch (NOT fail-open —
    silent HMAC failure was the KEI-91 incident pattern; misconfig here
    means no events would be acted on, so 401 is explicit and correct).
  - DB insert/update: fail-open (log warning, return 200) per webhook
    discipline — GitHub retries on 5xx, not on 200.

KEI-91 Gate 4: heartbeat outcome counter increments ONLY on HMAC-PASSED
events (not all 200s), matching the linear.py sentinel pattern.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.observability.heartbeat import tick as _heartbeat_tick

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/github", tags=["webhooks", "github"])

# Maximum title length stored in public.tasks — truncate safely.
_TITLE_MAX = 200

# PR task ID prefix — makes REVIEW rows visually distinct in the queue.
_TASK_ID_PREFIX = "REVIEW-PR"


def _verify_github_signature(secret: str, body: bytes, header: str) -> bool:
    """Constant-time HMAC-SHA-256 verify per GitHub webhook docs.

    GitHub sends: X-Hub-Signature-256: sha256=<hex>
    We strip the 'sha256=' prefix before compare_digest.
    Returns False if secret is blank or header is missing/malformed.
    """
    if not secret or not header:
        return False
    if not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    provided = header[len("sha256=") :]
    return hmac.compare_digest(expected, provided)


def _task_id(pr_number: int) -> str:
    return f"{_TASK_ID_PREFIX}-{pr_number}"


def _truncate(s: str, max_len: int) -> str:
    return s[:max_len] if len(s) > max_len else s


def _upsert_review_task(pr_number: int, pr_title: str, pr_url: str) -> None:
    """INSERT or UPDATE the REVIEW-PR-N row in public.tasks. Fail-open.

    ON CONFLICT (id) DO UPDATE makes this idempotent for synchronize events —
    re-delivery or a force-push on the same PR just refreshes the title/url.
    priority=2 (medium) — reviews are important but not P1 urgent.
    """
    task_id = _task_id(pr_number)
    title = _truncate(f"Review PR #{pr_number} — {pr_title}", _TITLE_MAX)
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("github webhook tasks upsert skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.tasks
                    (id, title, priority, status, linear_url, created_at, updated_at)
                VALUES (%s, %s, 2, 'available', %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                   SET title      = EXCLUDED.title,
                       linear_url = EXCLUDED.linear_url,
                       updated_at = NOW()
                """,
                (task_id, title, pr_url),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — fail-open per webhook discipline
        logger.warning("github tasks upsert failed for %s: %s", task_id, exc)


def _mark_review_done(pr_number: int) -> None:
    """UPDATE REVIEW-PR-N to status='done'. Fail-open.

    KEI-84 never-downgrade guard: the WHERE clause omits `AND status != 'done'`
    for the done-transition itself (we ARE setting to done), but we never
    re-open a done row — closed events only ever write 'done', so any row
    already at 'done' gets a harmless no-op UPDATE (same value, updated_at
    refreshed). This mirrors the linear.py:265-272 done-path pattern exactly:
    no WHERE-status guard on the done UPDATE — the guard (`AND status != 'done'`)
    is only on non-done transitions (see linear.py:282).
    """
    task_id = _task_id(pr_number)
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("github webhook tasks mark-done skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.tasks
                   SET status     = 'done',
                       claimed_by = NULL,
                       claimed_at = NULL,
                       updated_at = NOW()
                 WHERE id = %s
                """,
                (task_id,),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — fail-open per webhook discipline
        logger.warning("github tasks mark-done failed for %s: %s", task_id, exc)


def _handle_pull_request(payload: dict[str, Any]) -> dict[str, str]:
    """Dispatch pull_request event to the correct DB operation.

    Returns a dict that becomes the JSON response body.
    """
    action = payload.get("action", "")
    pr = payload.get("pull_request") or {}
    pr_number = pr.get("number")
    if not pr_number:
        logger.warning("github pr webhook missing pull_request.number")
        return {"status": "ignored", "reason": "missing pr number"}

    if action in ("opened", "reopened", "synchronize"):
        _upsert_review_task(
            pr_number=pr_number,
            pr_title=pr.get("title") or "(no title)",
            pr_url=pr.get("html_url") or "",
        )
        return {"status": "ok", "op": "upsert", "task_id": _task_id(pr_number)}

    if action == "closed":
        _mark_review_done(pr_number=pr_number)
        return {"status": "ok", "op": "done", "task_id": _task_id(pr_number)}

    # Other actions (labeled, assigned, review_requested, etc.) — no-op.
    return {"status": "ignored", "action": action}


@router.post("")
@router.post("/")
async def receive_github_webhook(request: Request) -> dict[str, str]:
    """Receive a GitHub webhook event, verify HMAC, manage public.tasks rows.

    KEI-91 Gate 4: outcome counter increments only on HMAC-PASSED events,
    matching the linear.py sentinel pattern. Silent HMAC failure keeps the
    counter at 0 while the handler still returns HTTP responses — the
    zero_outcome_window monitor rule fires within minutes.
    """
    body = await request.body()
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    signature_header = request.headers.get("x-hub-signature-256", "")

    if not _verify_github_signature(secret, body, signature_header):
        logger.warning("github webhook signature verify failed (header=%r)", signature_header[:20])
        _heartbeat_tick(
            "github-webhook-handler",
            outcome_increment=0,
            status="error",
            error_message="HMAC verification failed",
        )
        raise HTTPException(status_code=401, detail="signature verification failed")

    event_type = request.headers.get("x-github-event", "")
    if event_type != "pull_request":
        # HMAC passed, non-PR event — acknowledge and no-op.
        _heartbeat_tick("github-webhook-handler", outcome_increment=1, status="ok")
        return {"status": "ignored", "event": event_type}

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        logger.warning("github webhook malformed json payload")
        _heartbeat_tick(
            "github-webhook-handler",
            outcome_increment=1,
            status="degraded",
            error_message="malformed json payload",
        )
        return {"status": "malformed"}

    result = _handle_pull_request(payload)
    _heartbeat_tick("github-webhook-handler", outcome_increment=1, status="ok")
    return result


# ---------------------------------------------------------------------------
# TODO (KEI-NN1 — to be filed): Author exclusion
#
# The KEI-97 spec mentions author-exclusion (skip REVIEW-PR rows for PRs
# opened by certain bot authors, e.g. dependabot[bot], renovate[bot]).
# This is intentionally NOT implemented in Part A1 because the storage
# architecture for the exclusion list is an open decision:
#   Option A — column on public.tasks or a separate allowlist table.
#   Option B — title-prefix convention matched at claim time.
#   Option C — bd-sync exclusion list in a config file.
# File KEI-NN1 to capture the decision and implement. Until then, ALL
# PR authors produce a REVIEW-PR row; bot PRs will need manual closure
# or a follow-up migration once the exclusion architecture is ratified.
# ---------------------------------------------------------------------------
