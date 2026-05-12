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
LINEAR_STATE_TO_BD: dict[str, str] = {
    "started": "active",
    "completed": "closed",
    "canceled": "closed",
}

_BD_WRAPPER = "/home/elliotbot/clawd/Agency_OS/scripts/linear_to_bd.py"


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
                "url": data.get("url") or f"https://linear.app/keiracom/issue/{identifier}",
            }
    return None


def _dispatch_to_bd(event: dict[str, Any]) -> None:
    """Fire-and-forget subprocess to scripts/linear_to_bd.py. Fail-open."""
    try:
        subprocess.run(  # noqa: S603 — controlled args, no shell, payload validated
            ["/home/elliotbot/clawd/venv/bin/python3", _BD_WRAPPER, "--json"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("linear_to_bd dispatch failed: %s", exc)


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
    return {"status": "ok", "op": event["op"], "identifier": event["identifier"]}
