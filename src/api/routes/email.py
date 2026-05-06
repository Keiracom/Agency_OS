"""src/api/routes/email.py — email send + status + webhook routes.

Task #20 — Email Integration Backend (aiden/email-backend).

Three endpoints, all under prefix `/api/email`:

  POST /send                      — send via Resend, insert queued row
  GET  /status/{message_id}       — read row + event log
  POST /webhook                   — Resend HMAC-verified webhook receiver

curl examples:

  # Send
  curl -X POST $API/api/email/send \\
    -H 'content-type: application/json' \\
    -d '{"to":"a@b.com","subject":"hi","body_text":"hello","body_html":null}'

  # Status
  curl $API/api/email/status/<message_id>

  # Webhook (server-side; Resend posts directly)
  # Header: svix-signature: v1,<hmac-sha256-hex>
  curl -X POST $API/api/email/webhook \\
    -H 'svix-signature: v1,<sig>' \\
    -d '{"type":"email.delivered","data":{"email_id":"<message_id>"}}'

DB layer: psycopg with `prepare_threshold=None` so the Supabase pgbouncer
pooler doesn't choke on prepared statements. DATABASE_URL is stripped of
any `postgresql+asyncpg://` prefix so the SQLAlchemy URL works as a
psycopg DSN.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from src.integrations.resend_client import (
    ResendError,
    send_email,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])


# ── DB connection helper ─────────────────────────────────────────────────────


def _psycopg_dsn() -> str:
    """Strip the SQLAlchemy `postgresql+asyncpg://` prefix from DATABASE_URL
    so psycopg can use it directly. Falls back to DATABASE_URL_MIGRATIONS
    if DATABASE_URL is unset (CI / local)."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_MIGRATIONS") or ""
    if not url:
        raise HTTPException(status_code=500, detail="DATABASE_URL not configured")
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    elif url.startswith("postgres+asyncpg://"):
        url = "postgresql://" + url[len("postgres+asyncpg://") :]
    return url


def _connect():
    """Open a psycopg connection with prepare_threshold=None (pooler-safe)."""
    try:
        import psycopg  # type: ignore
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"psycopg not installed: {exc}") from exc
    return psycopg.connect(_psycopg_dsn(), prepare_threshold=None)


# ── Request / response models ────────────────────────────────────────────────


class EmailSendRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=998)
    body_html: str | None = None
    body_text: str | None = None
    from_address: str | None = Field(default=None, alias="from")

    model_config = {"populate_by_name": True}


class EmailSendResponse(BaseModel):
    message_id: str
    status: str = "queued"


class EmailStatusResponse(BaseModel):
    message_id: str
    status: str
    to_email: str
    from_email: str
    subject: str | None
    sent_at: datetime | None
    last_event_at: datetime | None
    events: list[dict[str, Any]]


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("/send", response_model=EmailSendResponse, status_code=status.HTTP_202_ACCEPTED)
def post_send(req: EmailSendRequest) -> EmailSendResponse:
    """Send an email via Resend, insert a queued row, return the message_id."""
    if not req.body_html and not req.body_text:
        raise HTTPException(status_code=422, detail="body_html or body_text required")
    try:
        result = send_email(
            to=req.to,
            subject=req.subject,
            body_html=req.body_html,
            body_text=req.body_text,
            from_address=req.from_address,
        )
    except ResendError as exc:
        raise HTTPException(status_code=502, detail=f"resend: {exc}") from exc

    message_id = str(result["id"])
    sender = req.from_address or os.environ.get(
        "RESEND_DEFAULT_FROM",
        "noreply@keiracom.com",
    )
    now = datetime.now(UTC)

    sql = (
        "INSERT INTO keiracom_admin.email_events "
        "(message_id, to_email, from_email, subject, status, "
        " events, sent_at, last_event_at) "
        "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s) "
        "ON CONFLICT (message_id) DO NOTHING"
    )
    initial_event = json.dumps(
        [
            {"type": "queued", "ts": now.isoformat()},
        ]
    )
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        message_id,
                        str(req.to),
                        sender,
                        req.subject,
                        "queued",
                        initial_event,
                        now,
                        now,
                    ),
                )
            conn.commit()
    except HTTPException:
        raise
    except Exception as exc:
        # Send already succeeded; log but don't fail the response.
        logger.error("[email/send] db insert failed message_id=%s: %s", message_id, exc)
    return EmailSendResponse(message_id=message_id, status="queued")


@router.get("/status/{message_id}", response_model=EmailStatusResponse)
def get_status(message_id: str) -> EmailStatusResponse:
    sql = (
        "SELECT message_id, to_email, from_email, subject, status, "
        "       events, sent_at, last_event_at "
        "FROM keiracom_admin.email_events WHERE message_id = %s LIMIT 1"
    )
    try:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(sql, (message_id,))
            row = cur.fetchone()
    except Exception as exc:
        logger.error("[email/status] db query failed: %s", exc)
        raise HTTPException(status_code=500, detail="db error") from exc
    if row is None:
        raise HTTPException(status_code=404, detail="message_id not found")
    events_field = row[5]
    if isinstance(events_field, str):
        try:
            events_field = json.loads(events_field)
        except json.JSONDecodeError:
            events_field = []
    return EmailStatusResponse(
        message_id=row[0],
        to_email=row[1],
        from_email=row[2],
        subject=row[3],
        status=row[4],
        events=events_field or [],
        sent_at=row[6],
        last_event_at=row[7],
    )


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def post_webhook(request: Request) -> dict[str, Any]:
    """Resend webhook receiver. HMAC-verifies via RESEND_WEBHOOK_SECRET,
    appends event to the row, updates `status` + `last_event_at`."""
    raw = await request.body()
    sig = request.headers.get("svix-signature") or request.headers.get("resend-signature")
    msg_id = request.headers.get("svix-id")
    timestamp = request.headers.get("svix-timestamp")
    if not verify_webhook_signature(raw, sig, msg_id=msg_id, timestamp=timestamp):
        raise HTTPException(status_code=401, detail="invalid signature")
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"bad json: {exc}") from exc

    event_type = str(payload.get("type", "")).strip()
    data = payload.get("data") or {}
    message_id = str(data.get("email_id") or data.get("id") or "").strip()
    if not message_id or not event_type:
        raise HTTPException(status_code=400, detail="missing type or email_id")

    # Translate Resend event_type → row.status. Mapping must stay within the
    # email_events.status CHECK constraint: queued/sent/delivered/opened/
    # clicked/bounced/complained/failed. Events outside the enum (e.g.
    # email.delivery_delayed) map to None — recorded in events jsonb array
    # but the row's status column is left unchanged via COALESCE below.
    status_map: dict[str, str | None] = {
        "email.sent": "sent",
        "email.delivered": "delivered",
        "email.delivery_delayed": None,
        "email.bounced": "bounced",
        "email.complained": "complained",
        "email.opened": "opened",
        "email.clicked": "clicked",
        "email.failed": "failed",
    }
    new_status = status_map.get(event_type)
    now = datetime.now(UTC)
    event_row = {
        "type": event_type,
        "ts": now.isoformat(),
        "data": data,
    }

    sql = (
        "UPDATE keiracom_admin.email_events SET "
        "  status = COALESCE(%s, status), "
        "  events = events || %s::jsonb, "
        "  last_event_at = %s "
        "WHERE message_id = %s"
    )
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (new_status, json.dumps([event_row]), now, message_id),
                )
            conn.commit()
    except Exception as exc:
        logger.error("[email/webhook] db update failed: %s", exc)
        raise HTTPException(status_code=500, detail="db error") from exc
    return {"ok": True, "message_id": message_id, "applied_status": new_status}
