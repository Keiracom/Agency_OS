"""src/api/webhooks/linear.py — Linear → Beads inbound sync webhook.

PR-1 of the Linear↔Beads sync automation directive (Dave Urgent ts ~1778620420).
Receives Linear webhook POSTs at /api/webhooks/linear, verifies HMAC signature
against LINEAR_WEBHOOK_SECRET, and dispatches to bd CRUD via the
scripts/linear_to_bd.py subprocess wrapper.

Event handling:
  - Issue.create   → bd create with title + priority + external-ref Linear URL
  - Issue.update status=Done    → bd close <agency_os_id-from-external-ref>
  - Issue.update status=Started → bd update --status active
  - IssueRelation.create        → bd dep add (when both ends mapped)

Idempotency:
  Each Linear event carries an `data.id` and webhook delivery `Linear-Delivery`
  header. Re-delivered events are recognised by matching the external-ref on
  an existing bd issue + skipped if state already matches.

Fail-open: malformed payload / unmatched event type / subprocess failure
returns 200 OK so Linear doesn't retry-storm. Errors logged to journal.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/linear", tags=["webhooks", "linear"])

# Linear → bd priority map (Linear is 0=no-priority,1=urgent,2=high,3=medium,4=low;
# bd is 0=critical, 1=high, 2=medium, 3=low, 4=backlog). Linear-urgent → bd-0.
LINEAR_TO_BD_PRIORITY: dict[int, int] = {0: 4, 1: 0, 2: 1, 3: 2, 4: 3}

# Linear state name → bd status (Linear's StateType enum: triage/backlog/unstarted/started/completed/canceled).
# KEI-84 extension: backlog/unstarted (Todo) → available; canceled → 'cancelled' (own bucket, not 'closed').
LINEAR_STATE_TO_BD: dict[str, str] = {
    "backlog": "available",
    "unstarted": "available",
    "triage": "available",
    "started": "active",
    "completed": "closed",
    "canceled": "cancelled",
}

# KEI-84: separate Linear state → public.tasks.status mapping per spec acceptance
# (Backlog/Todo → available; In Progress/In Review → active; Done → done;
# Cancelled/Duplicate → cancelled). 'In Review' shares Linear's started StateType
# with 'In Progress'; both → active. 'Duplicate' is a custom state that Linear
# canonically maps under canceled StateType → cancelled.
LINEAR_STATE_TO_TASK_STATUS: dict[str, str] = {
    "backlog": "available",
    "unstarted": "available",
    "triage": "available",
    "started": "active",
    "completed": "done",
    "canceled": "cancelled",
}

_BD_WRAPPER = "/home/elliotbot/clawd/Agency_OS/scripts/linear_to_bd.py"


def _python_bin() -> str:
    """Prefer repo-local .venv (canonical) over the legacy shared
    /home/elliotbot/clawd/venv. Max's PR-2 review flagged the shared venv
    as corrupt per Atlas's cognee-recall SKILL.md; switch to repo-local."""
    candidates = (
        "/home/elliotbot/clawd/Agency_OS/.venv/bin/python3",
        "/home/elliotbot/clawd/venv/bin/python3",
    )
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "python3"


def _verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    """Constant-time HMAC SHA-256 verify per Linear webhook docs."""
    if not signature_header or not secret:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


def _normalise_event(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the minimal canonical shape used by linear_to_bd.py from a raw
    Linear webhook payload. Return None for events we don't handle.

    Linear webhook payload (simplified, per developers.linear.app):
      {
        "action": "create" | "update" | "remove",
        "type": "Issue" | "Comment" | "IssueRelation",
        "data": { "id": "...", "identifier": "KEI-NN", "title": "...",
                   "priority": 0..4, "state": {"name": "...", "type": "..."},
                   "url": "https://linear.app/...", ... },
        "createdAt": "...",
      }
    """
    action = payload.get("action")
    obj_type = payload.get("type")
    data = payload.get("data") or {}
    if not (action and obj_type):
        return None
    if obj_type != "Issue":
        # PR-2 will handle IssueRelation; out of scope here.
        return None

    identifier = data.get("identifier")
    if not identifier:
        return None

    if action == "create":
        return {
            "op": "create",
            "identifier": identifier,
            "title": data.get("title") or "(no title)",
            "priority": LINEAR_TO_BD_PRIORITY.get(data.get("priority", 0), 2),
            "url": data.get("url") or f"https://linear.app/keiracom/issue/{identifier}",
        }
    if action == "update":
        state = (data.get("state") or {}).get("type") or ""
        if state in LINEAR_STATE_TO_BD:
            return {
                "op": "status",
                "identifier": identifier,
                "bd_status": LINEAR_STATE_TO_BD[state],
                "task_status": LINEAR_STATE_TO_TASK_STATUS.get(state),
                "url": data.get("url") or f"https://linear.app/keiracom/issue/{identifier}",
            }
    if action == "remove":
        # KEI-84: Linear issue deleted → flip task to cancelled (preserve row + history).
        return {
            "op": "remove",
            "identifier": identifier,
            "task_status": "cancelled",
            "url": data.get("url") or f"https://linear.app/keiracom/issue/{identifier}",
        }
    return None


def _dispatch_to_bd(event: dict[str, Any]) -> None:
    """Fire-and-forget subprocess to scripts/linear_to_bd.py. Fail-open."""
    try:
        subprocess.run(  # noqa: S603 — controlled args, no shell, payload validated
            [_python_bin(), _BD_WRAPPER, "--json"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("linear_to_bd dispatch failed: %s", exc)


# KEI-22 (Dave directive 2026-05-14): tasks table is now the canonical queue
# source. Linear webhook writes here in addition to bd during transition.
# Linear priority enum (0=none,1=urgent,2=high,3=medium,4=low) maps to a
# small-int priority on public.tasks (1=Urgent, 2=High, 3=Medium, 4=Low,
# matching the bd convention 0=critical/1=high/... but tasks table uses
# Linear's own range: P1 is the highest fired by webhook).
LINEAR_TO_TASKS_PRIORITY: dict[int, int] = {0: 4, 1: 1, 2: 2, 3: 3, 4: 4}


def _dispatch_to_tasks(event: dict[str, Any]) -> None:
    """Mirror a Linear event into public.tasks. Fail-open.

    On create: INSERT (id, title, priority, status='available', linear_url).
    On status update: UPDATE status using the Linear state mapping —
    started → active, completed/canceled → done (also clears claimed_by).
    Conflicts on existing id: UPDATE the mutable fields rather than skipping,
    so the webhook is idempotent against re-deliveries.
    """
    op = event.get("op")
    identifier = event.get("identifier")
    url = event.get("url") or f"https://linear.app/keiracom/issue/{identifier}"
    if not (op and identifier):
        return
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("tasks dispatch skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            if op == "create":
                cur.execute(
                    """
                    INSERT INTO public.tasks (id, title, priority, status, linear_url, created_at, updated_at)
                    VALUES (%s, %s, %s, 'available', %s, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE
                       SET title = EXCLUDED.title,
                           priority = EXCLUDED.priority,
                           linear_url = EXCLUDED.linear_url,
                           updated_at = NOW()
                    """,
                    (
                        identifier,
                        event.get("title") or "(no title)",
                        LINEAR_TO_TASKS_PRIORITY.get(event.get("priority", 0), 3),
                        url,
                    ),
                )
            elif op == "status":
                # KEI-84: full status mapping per spec acceptance.
                # task_status is the spec'd target ('available'|'active'|'done'|'cancelled');
                # falls back to legacy bd_status if older normalised event arrives.
                new_status = event.get("task_status")
                if new_status is None:
                    new_status = "done" if event.get("bd_status") == "closed" else "active"
                # KEI-84 invariant: never downgrade a 'done' task (Linear could
                # legitimately re-open via state change, but the spec hard-no's
                # downgrade). Skip the UPDATE on done rows.
                if new_status == "done":
                    cur.execute(
                        """
                        UPDATE public.tasks
                           SET status = 'done', claimed_by = NULL, claimed_at = NULL,
                               linear_url = COALESCE(linear_url, %s), updated_at = NOW()
                         WHERE id = %s
                        """,
                        (url, identifier),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE public.tasks
                           SET status = %s,
                               linear_url = COALESCE(linear_url, %s),
                               updated_at = NOW()
                         WHERE id = %s AND status != 'done'
                        """,
                        (new_status, url, identifier),
                    )
            elif op == "remove":
                # KEI-84: Linear issue deletion → flip to cancelled. Same never-downgrade-done guard.
                cur.execute(
                    """
                    UPDATE public.tasks
                       SET status = 'cancelled',
                           linear_url = COALESCE(linear_url, %s),
                           updated_at = NOW()
                     WHERE id = %s AND status != 'done'
                    """,
                    (url, identifier),
                )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — fail-open per webhook discipline
        logger.warning("tasks dispatch failed for %s: %s", identifier, exc)


@router.post("")
@router.post("/")
async def receive_linear_webhook(request: Request) -> dict[str, str]:
    """Receive a Linear webhook event, verify HMAC, dispatch to bd CRUD."""
    body = await request.body()
    secret = os.environ.get("LINEAR_WEBHOOK_SECRET", "")
    signature = request.headers.get("linear-signature", "")
    if not _verify_signature(secret, body, signature):
        logger.warning("linear webhook signature verify failed")
        raise HTTPException(status_code=401, detail="signature verification failed")
    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError:
        logger.warning("linear webhook malformed json payload")
        return {"status": "malformed"}
    event = _normalise_event(payload)
    if not event:
        return {"status": "ignored"}
    _dispatch_to_bd(event)
    _dispatch_to_tasks(event)  # KEI-22 — Supabase tasks SSOT (parallel to bd during transition)
    _dispatch_to_indexing_queue("linear", payload)  # KEI-61 — durable staging buffer
    return {"status": "ok", "op": event["op"], "identifier": event["identifier"]}


def _dispatch_to_indexing_queue(source: str, raw_payload: dict[str, Any]) -> None:
    """KEI-61: enqueue the raw webhook payload for durable async indexing.

    Webhooks fire fast and return 200 to the sender; the indexing_queue_worker
    drains the queue, processes via LlamaIndex+Weaviate, and writes the audit
    log. Survives downstream restarts because the row is persisted before any
    processing runs. Fail-open per webhook discipline.
    """
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL", "")
    if not dsn:
        logger.warning("indexing_queue dispatch skipped: DATABASE_URL/SUPABASE_DB_URL unset")
        return
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.indexing_queue (source, payload, status)
                VALUES (%s, %s::jsonb, 'pending')
                """,
                (source, json.dumps(raw_payload)),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — webhook discipline: fail-open
        logger.warning("indexing_queue dispatch failed for %s: %s", source, exc)
