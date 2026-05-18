"""src/api/webhooks/github.py — GitHub → public.tasks inbound webhook.

KEI-97 Part A — Dave dispatch ts ~1779024750.
KEI-207 — PR merge → auto-close KEI tasks in public.tasks.

Receives GitHub webhook POSTs at /api/webhooks/github, verifies HMAC
signature against GITHUB_WEBHOOK_SECRET (X-Hub-Signature-256 header),
and upserts REVIEW-PR-<N> rows in public.tasks.

Event handling:
  - pull_request action='opened'|'reopened' → INSERT/upsert REVIEW-PR-<N>
    with status='available', excluded_callsign=PR author (lowercased).
  - pull_request action='closed' (merged or not) → UPDATE REVIEW-PR-<N> status='done'.
  - pull_request action='closed' AND merged=true → additionally close matching KEI
    task: parse KEI-\\d+ from PR title (first match); fallback: match via
    linear_url column. No match → log + skip, no error.

Fail-open: HMAC fail → 401; malformed payload → 200 logged warning
(retry-storm guard, same pattern as src/api/webhooks/linear.py).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

_KEI_RE = re.compile(r"KEI-\d+")

router = APIRouter(prefix="/api/webhooks/github", tags=["webhooks", "github"])

_OPEN_ACTIONS = frozenset({"opened", "reopened"})


def _verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """Constant-time HMAC SHA-256 verify per GitHub webhook docs.

    GitHub sends 'sha256=<hex>' in X-Hub-Signature-256. We strip the prefix
    before comparing so the caller can pass either the raw header value or
    just the hex portion.
    """
    if not signature_header or not secret:
        return False
    sig = signature_header.removeprefix("sha256=").strip()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _task_id(pr_number: int) -> str:
    return f"REVIEW-PR-{pr_number}"


def _upsert_review_task(pr: dict[str, Any]) -> None:
    """INSERT or UPDATE a REVIEW-PR-<N> row in public.tasks. Fail-open."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("github webhook tasks upsert skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    pr_number: int = pr["number"]
    pr_title: str = pr.get("title") or ""
    pr_url: str = pr.get("html_url") or ""
    pr_body: str = pr.get("body") or ""
    author: str = (pr.get("user") or {}).get("login") or ""
    author_lower = author.lower()

    task_id = _task_id(pr_number)
    task_title = f"Review PR #{pr_number} — {pr_title}"
    task_description = pr_url + "\n\n" + pr_body[:500]

    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.tasks (
                    id, title, description, status, phase, claim_source,
                    excluded_callsign, created_at, updated_at
                )
                VALUES (%s, %s, %s, 'available', 0, 'manual', %s, NOW(), NOW())
                ON CONFLICT (id) DO UPDATE
                    SET title             = EXCLUDED.title,
                        description       = EXCLUDED.description,
                        excluded_callsign = EXCLUDED.excluded_callsign,
                        updated_at        = NOW()
                """,
                (task_id, task_title, task_description, author_lower or None),
            )
            conn.commit()
        logger.info("github webhook: upserted task %s (author=%s)", task_id, author_lower)
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("github webhook tasks upsert failed for %s: %s", task_id, exc)


def _close_review_task(pr_number: int) -> None:
    """Mark REVIEW-PR-<N> done when PR is closed. Fail-open."""
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("github webhook tasks close skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    task_id = _task_id(pr_number)
    try:
        import psycopg

        with (
            psycopg.connect(dsn, connect_timeout=10, prepare_threshold=None) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                UPDATE public.tasks
                   SET status = 'done', updated_at = NOW()
                 WHERE id = %s
                """,
                (task_id,),
            )
            conn.commit()
        logger.info("github webhook: closed task %s", task_id)
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("github webhook tasks close failed for %s: %s", task_id, exc)


# ── KEI-207 — close KEI task on PR merge ─────────────────────────────────


def _close_kei_task_by_id(kei_id: str) -> None:
    """Mark a KEI task done by exact id match. Fail-open.

    KEI-207: called when KEI-\\d+ found in PR title on merge.
    prepare_threshold=None per reference_psycopg_supabase_pgbouncer (pgbouncer
    transaction mode drops PREPARE statements).
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("KEI-207: kei task close skipped — DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        import psycopg

        with (
            psycopg.connect(dsn, connect_timeout=10, prepare_threshold=None) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                "UPDATE public.tasks SET status = 'done', updated_at = NOW() WHERE id = %s",
                (kei_id,),
            )
            conn.commit()
        logger.info("KEI-207: closed kei task %s on PR merge", kei_id)
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("KEI-207: kei task close failed for %s: %s", kei_id, exc)


def _close_kei_task_by_pr_url(pr_url: str) -> bool:
    """Close KEI task by matching linear_url column. Returns True if a row was updated. Fail-open.

    KEI-207 fallback: when PR title contains no KEI-\\d+, attempt to match
    tasks.linear_url against the GitHub PR html_url. Returns False on DB error
    or no match.
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("KEI-207: fallback close skipped — DATABASE_URL/SUPABASE_DB_URL unset")
        return False
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)

    try:
        import psycopg

        with (
            psycopg.connect(dsn, connect_timeout=10, prepare_threshold=None) as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                "UPDATE public.tasks SET status = 'done', updated_at = NOW() WHERE linear_url = %s RETURNING id",
                (pr_url,),
            )
            rows = cur.fetchall()
            conn.commit()
        if rows:
            logger.info(
                "KEI-207: fallback closed kei task(s) %s via linear_url match", [r[0] for r in rows]
            )
            return True
        return False
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("KEI-207: fallback kei task close failed for url %s: %s", pr_url, exc)
        return False


def _handle_kei_task_close_on_merge(pr_title: str, pr_url: str) -> None:
    """KEI-207 entry point: parse KEI-\\d+ from title; fallback to linear_url query.

    Chain: title regex match → _close_kei_task_by_id.
    No title match → _close_kei_task_by_pr_url.
    No match either way → log + skip. No error raised; webhook stays fail-open.

    Note: regex is case-sensitive (`KEI-\\d+`) matching Linear's canonical
    uppercase convention. Lowercase 'kei-123' is intentionally not matched.
    """
    m = _KEI_RE.search(pr_title)
    if m:
        kei_id = m.group(0)
        logger.info("KEI-207: title match %s for PR %s", kei_id, pr_url)
        _close_kei_task_by_id(kei_id)
        return

    # Title parse failed — try linear_url fallback
    matched = _close_kei_task_by_pr_url(pr_url)
    if not matched:
        logger.info("KEI-207: no matching task for PR %s, skipping", pr_url)


_RECEIVE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "HMAC signature verification failed."}
}


@router.post("", responses=_RECEIVE_RESPONSES)
@router.post("/", responses=_RECEIVE_RESPONSES)
async def receive_github_webhook(request: Request) -> dict[str, str]:
    """Receive a GitHub webhook event, verify HMAC, dispatch to public.tasks.

    Handles pull_request events only:
      - opened/reopened → upsert REVIEW-PR-<N> task
      - closed          → mark task done
    All other event types return status='ignored'.
    """
    body = await request.body()
    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    signature = request.headers.get("x-hub-signature-256", "")

    if not _verify_signature(secret, body, signature):
        logger.warning("github webhook signature verify failed")
        raise HTTPException(status_code=401, detail="signature verification failed")

    # Check event type header — GitHub sends X-GitHub-Event
    event_type = request.headers.get("x-github-event", "")
    if event_type != "pull_request":
        return {"status": "ignored", "event": event_type}

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        logger.warning("github webhook malformed json payload")
        return {"status": "malformed"}

    action = payload.get("action", "")
    pr = payload.get("pull_request") or {}
    pr_number = pr.get("number")

    if pr_number is None:
        logger.warning("github webhook: pull_request payload missing number field")
        return {"status": "malformed"}

    if action in _OPEN_ACTIONS:
        _upsert_review_task(pr)
        return {"status": "ok", "action": action, "task_id": _task_id(pr_number)}

    if action == "closed":
        _close_review_task(pr_number)
        # KEI-207: if the PR was actually merged, also close the matching KEI task.
        if pr.get("merged") is True:
            pr_title: str = pr.get("title") or ""
            pr_url: str = pr.get("html_url") or ""
            _handle_kei_task_close_on_merge(pr_title, pr_url)
        return {"status": "ok", "action": action, "task_id": _task_id(pr_number)}

    # Other actions (assigned, labeled, synchronize, etc.) — ignore
    return {"status": "ignored", "action": action}
