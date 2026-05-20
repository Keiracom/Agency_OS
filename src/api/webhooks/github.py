"""src/api/webhooks/github.py — GitHub → public.tasks inbound webhook.

KEI-97 Part A — Dave dispatch ts ~1779024750.

Receives GitHub webhook POSTs at /api/webhooks/github, verifies HMAC
signature against GITHUB_WEBHOOK_SECRET (X-Hub-Signature-256 header),
and upserts REVIEW-PR-<N> rows in public.tasks.

Event handling:
  - pull_request action='opened'|'reopened' → INSERT/upsert REVIEW-PR-<N>
    with status='available', excluded_callsign=PR author (lowercased).
  - pull_request action='closed' (merged or not) → UPDATE status='done'.

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

router = APIRouter(prefix="/api/webhooks/github", tags=["webhooks", "github"])

_OPEN_ACTIONS = frozenset({"opened", "reopened"})

# Sonar S1192 — DSN dialect strings used 3× each across helpers; module-level
# constants keep the strip-call expression single-source.
_DSN_ASYNCPG_PREFIX = "postgresql+asyncpg://"
_DSN_SYNC_PREFIX = "postgresql://"

# KEI-207 — auto-close matching KEI task on PR merge. Title parse first;
# fallback to linear_url match from a Linear URL in the PR body.
_KEI_TITLE_RE = re.compile(r"\bKEI-(\d+)\b", re.IGNORECASE)
_LINEAR_URL_RE = re.compile(
    r"https?://linear\.app/[\w-]+/issue/(KEI-\d+)[/\w-]*",
    re.IGNORECASE,
)


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
    dsn = dsn.replace(_DSN_ASYNCPG_PREFIX, _DSN_SYNC_PREFIX, 1)

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
    dsn = dsn.replace(_DSN_ASYNCPG_PREFIX, _DSN_SYNC_PREFIX, 1)

    task_id = _task_id(pr_number)
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
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


def extract_kei_id(pr_title: str, pr_body: str) -> str | None:
    """KEI-207 — parse `KEI-\\d+` from PR title (primary) then PR body (fallback).

    Returns the canonical `KEI-N` form (uppercase, no surrounding text), or
    None if neither source contains a match. Title is the strong signal
    (PR titles follow `[CALLSIGN] feat(kei-N): ...` convention); body is
    the fallback (often contains "Closes KEI-N" or a Linear URL).
    """
    for source in (pr_title, pr_body):
        if not source:
            continue
        m = _KEI_TITLE_RE.search(source)
        if m:
            return f"KEI-{m.group(1)}"
    return None


def extract_linear_url_kei(pr_body: str) -> str | None:
    """KEI-207 fallback — pull a `KEI-N` out of a linear.app URL in the PR body.

    Returns the canonical `KEI-N` form or None. Used when extract_kei_id()
    fails (title + body have no bare KEI-N reference) but the PR body still
    links to the Linear issue.
    """
    if not pr_body:
        return None
    m = _LINEAR_URL_RE.search(pr_body)
    if m:
        return m.group(1).upper()
    return None


def _close_kei_task(pr: dict[str, Any]) -> None:
    """KEI-207 — on PR merge, auto-close the matching public.tasks KEI row.

    Resolution order (mirrors Dave's KEI-207 spec):
      1. Regex `KEI-\\d+` against PR title (then body) → UPDATE WHERE id = KEI-N.
      2. Fallback: regex linear.app URL in PR body → UPDATE WHERE
         linear_url LIKE '%KEI-N%' (catches tasks keyed by URL not slug).
      3. No match: log and skip.

    Idempotent: UPDATE with rowcount==0 on already-done rows is a no-op.
    Fail-open per the file-level webhook discipline.
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("github webhook KEI close skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace(_DSN_ASYNCPG_PREFIX, _DSN_SYNC_PREFIX, 1)

    pr_number = pr.get("number")
    pr_title = pr.get("title") or ""
    pr_body = pr.get("body") or ""

    kei_id = extract_kei_id(pr_title, pr_body)
    fallback_kei = None if kei_id else extract_linear_url_kei(pr_body)
    target_kei = kei_id or fallback_kei

    if target_kei is None:
        logger.info(
            "github webhook PR #%s: no KEI-N in title/body/linear_url — skipping", pr_number
        )
        return

    sql_by_id = "UPDATE public.tasks SET status = 'done', updated_at = NOW() WHERE id = %s"
    sql_by_url = (
        "UPDATE public.tasks SET status = 'done', updated_at = NOW() WHERE linear_url ILIKE %s"
    )
    url_pattern = f"%{target_kei}%"

    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(sql_by_id, (target_kei,))
            rows_by_id = cur.rowcount
            if rows_by_id == 0:
                cur.execute(sql_by_url, (url_pattern,))
                rows_by_url = cur.rowcount
            else:
                rows_by_url = 0
            conn.commit()
        logger.info(
            "github webhook PR #%s: KEI close target=%s by_id=%d by_url=%d",
            pr_number,
            target_kei,
            rows_by_id,
            rows_by_url,
        )
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("github webhook KEI close failed for %s: %s", target_kei, exc)


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
        # KEI-207 — only auto-close the matching KEI task when the PR was
        # actually merged. Closed-without-merge means the work didn't ship.
        if pr.get("merged") is True:
            _close_kei_task(pr)
        return {"status": "ok", "action": action, "task_id": _task_id(pr_number)}

    # Other actions (assigned, labeled, synchronize, etc.) — ignore
    return {"status": "ignored", "action": action}
