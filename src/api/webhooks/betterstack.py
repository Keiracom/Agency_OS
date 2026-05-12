"""src/api/webhooks/betterstack.py — Better Stack incident → Linear KEI auto-create webhook.

KEI-26 P1 per Dave restart-readiness directive. Receives Better Stack incident
webhooks (POST /api/webhooks/betterstack), verifies shared-secret token, and
dispatches to scripts/betterstack_to_linear.py to create a matching Linear
KEI issue with priority Urgent + status In Progress + assignee Elliot.

Inverse direction of PR #804 Linear→Beads inbound webhook. Same FastAPI +
subprocess-dispatch shape; same fail-open semantics (200 OK on every path
so BS doesn't retry-storm).

Better Stack outbound webhook signing was not confirmed during build probe
(docs page JS-rendered). Receiver verifies via BETTERSTACK_WEBHOOK_SECRET env
matched against X-Webhook-Secret header OR ?secret= query (operator-configured
shared-secret in the BS dashboard webhook URL). Missing/mismatch → 401.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks/betterstack", tags=["webhooks", "betterstack"])

_BS_WRAPPER = "/home/elliotbot/clawd/Agency_OS/scripts/betterstack_to_linear.py"


def _python_bin() -> str:
    """Prefer repo-local .venv (canonical post-PR #805 fix) over legacy shared venv."""
    candidates = (
        "/home/elliotbot/clawd/Agency_OS/.venv/bin/python3",
        "/home/elliotbot/clawd/venv/bin/python3",
    )
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "python3"


def _verify_token(request: Request, secret: str) -> bool:
    """Match the BETTERSTACK_WEBHOOK_SECRET against header OR query param."""
    if not secret:
        return False
    header_token = request.headers.get("x-webhook-secret", "")
    if header_token and header_token.strip() == secret:
        return True
    query_token = request.query_params.get("secret", "")
    return bool(query_token and query_token.strip() == secret)


def _unwrap_record(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Reduce a BS webhook payload to a single record dict, or None."""
    record = payload.get("data") or payload
    if isinstance(record, list):
        record = record[0] if record else None
    return record or None


def _normalise_incident(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract canonical BS incident shape per /api/v2/incidents response.

    Supports both webhook-direct payloads (which BS sends with same `data`
    envelope as the v2 API) and operator-flattened payloads.
    """
    record = _unwrap_record(payload)
    if not record:
        return None
    attrs = record.get("attributes") or {}
    incident_id = record.get("id") or attrs.get("id")
    if not incident_id:
        return None
    monitor_rel = (record.get("relationships") or {}).get("monitor", {}).get("data") or {}
    metadata = attrs.get("metadata") or {}
    return {
        "incident_id": str(incident_id),
        "monitor_name": (
            metadata.get("Monitor pronounceable name") or attrs.get("name") or "(unknown monitor)"
        ),
        "monitor_url": metadata.get("Monitor URL") or attrs.get("url") or "",
        "cause": attrs.get("cause") or "(no cause reported)",
        "status": (attrs.get("status") or "").lower(),
        "started_at": attrs.get("started_at") or "",
        "resolved_at": attrs.get("resolved_at") or "",
        "monitor_id": str(monitor_rel.get("id") or ""),
    }


def _dispatch_to_linear(event: dict[str, Any]) -> None:
    """Fire-and-forget subprocess to scripts/betterstack_to_linear.py. Fail-open."""
    try:
        subprocess.run(  # NOSONAR S603 — controlled args (absolute path + literal flag), no shell, no user input in argv
            [_python_bin(), _BS_WRAPPER, "--json"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        # OSError covers FileNotFoundError (subclass). subprocess.TimeoutExpired
        # is NOT an OSError subclass so it stays explicit.
        logger.warning("betterstack_to_linear dispatch failed: %s", exc)


_WEBHOOK_RESPONSES = {
    401: {"description": "Token verification failed (missing or wrong BETTERSTACK_WEBHOOK_SECRET)"},
    200: {
        "description": "Accepted (status='ok' on dispatch, 'ignored' on non-Started or non-Issue, 'malformed' on JSON parse failure)"
    },
}


@router.post("", responses=_WEBHOOK_RESPONSES)
@router.post("/", responses=_WEBHOOK_RESPONSES)
async def receive_betterstack_webhook(request: Request) -> dict[str, str]:
    secret = os.environ.get("BETTERSTACK_WEBHOOK_SECRET", "")
    if not _verify_token(request, secret):
        logger.warning("betterstack webhook token verify failed")
        raise HTTPException(status_code=401, detail="token verification failed")
    try:
        payload = await request.json()
    except ValueError:
        # JSONDecodeError is a ValueError subclass — single catch.
        logger.warning("betterstack webhook malformed json payload")
        return {"status": "malformed"}
    event = _normalise_incident(payload)
    if not event:
        return {"status": "ignored"}
    # Only auto-create on incident START. Resolved + acknowledged events are
    # informational; Linear closure is downstream of bd close → linear sync.
    if event["status"] not in {"started", "downtime", "down"}:
        return {"status": "ignored", "reason": f"status={event['status']!r} not actionable"}
    _dispatch_to_linear(event)
    return {"status": "ok", "incident_id": event["incident_id"], "monitor": event["monitor_name"]}
