#!/usr/bin/env python3
"""scripts/smoke_email_backend.py — live end-to-end smoke for Task #20.

Spins the FastAPI app via TestClient (no separate uvicorn needed), then:
  1. POST /api/email/send  — real Resend send to RECIPIENT
  2. GET  /api/email/status/{message_id}  — confirms queued row in DB
  3. POST /api/email/webhook  — locally simulated Resend webhook with a
     real HMAC-SHA256 signature over the raw body (matches what Resend
     would actually post). Sends `email.delivered`, then `email.opened`.
  4. GET  /api/email/status/{message_id}  — confirms status flipped to
     "opened" + events JSONB has all four entries (queued, delivered,
     opened, plus the original send insert).

Constraint we're honest about: real Resend → my localhost can't fire
without a public-tunnel URL (ngrok / Cloudflare Tunnel) or a deployed
Railway URL configured in the Resend dashboard. The webhook-receipt step
here uses a true HMAC signature against the live route + live DB, which
is the same code path Resend would exercise — just with the simulated
event payload instead of a real Resend egress.

To run with a real Resend-fired webhook, deploy the branch + add the
Railway URL `<deploy>/api/email/webhook` in the Resend dashboard webhooks
section, set RESEND_WEBHOOK_SECRET in the Railway env, then send.

Honest pre-revenue smoke: this does send a real email. Costs one Resend
free-tier credit. No fabricated data.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app  # noqa: E402

RECIPIENT = os.environ.get("SMOKE_EMAIL_TO", "dvidstephens@gmail.com")
WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET", "smoke-test-secret")


def _sign(body: bytes) -> str:
    """Build a Svix-style `v1,<base64>` signature header."""
    digest = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    return "v1," + base64.b64encode(digest).decode("ascii")


def _post_webhook(client: TestClient, message_id: str, event_type: str) -> dict:
    payload = {
        "type": event_type,
        "data": {
            "email_id": message_id,
            "from": "onboarding@resend.dev",
            "to": [RECIPIENT],
            "subject": "Task #20 smoke",
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    resp = client.post(
        "/api/email/webhook",
        content=raw,
        headers={
            "svix-signature": _sign(raw),
            "content-type": "application/json",
        },
    )
    print(f"  POST /webhook event_type={event_type} → {resp.status_code}")
    print(f"  body: {resp.text}")
    return resp.json() if resp.status_code == 200 else {}


def main() -> int:
    # Ensure webhook secret is set in this process so the route can verify.
    os.environ["RESEND_WEBHOOK_SECRET"] = WEBHOOK_SECRET

    client = TestClient(app)

    # ── Step 1: real send ────────────────────────────────────────────────
    payload = {
        "to": RECIPIENT,
        "subject": f"Task #20 e2e smoke {int(time.time())}",
        "body_text": (
            "End-to-end smoke for Task #20 email backend. "
            "Tests real Resend send + simulated Resend webhook receipt + "
            "event logging in keiracom_admin.email_events."
        ),
    }
    print("=== Step 1: POST /api/email/send (real Resend) ===")
    print("request:", json.dumps(payload, indent=2))
    resp = client.post("/api/email/send", json=payload)
    print(f"status: {resp.status_code}")
    print(f"body:   {resp.text}")
    if resp.status_code != 202:
        print("  send failed — bailing")
        return 1
    message_id = resp.json()["message_id"]

    # ── Step 2: confirm queued row ───────────────────────────────────────
    time.sleep(0.5)
    print()
    print(f"=== Step 2: GET /api/email/status/{message_id} (queued) ===")
    resp2 = client.get(f"/api/email/status/{message_id}")
    print(f"status: {resp2.status_code}")
    print(f"body:   {json.dumps(resp2.json(), indent=2, default=str)}")
    if resp2.status_code != 200:
        return 1

    # ── Step 3: simulated Resend webhooks (real HMAC, real DB) ───────────
    print()
    print("=== Step 3: POST /api/email/webhook (real HMAC, simulated payload) ===")
    print(
        "  (Resend → localhost requires a tunnel; we simulate the payload "
        "but use a true Svix-format HMAC against the live route + DB.)"
    )
    _post_webhook(client, message_id, "email.delivered")
    _post_webhook(client, message_id, "email.opened")

    # Negative case — bad signature must 401.
    bad_resp = client.post(
        "/api/email/webhook",
        content=b'{"type":"email.delivered","data":{"email_id":"x"}}',
        headers={"svix-signature": "v1,deadbeef"},
    )
    print(f"  bad-signature attempt → {bad_resp.status_code} (must be 401)")

    # ── Step 4: final status — webhook events visible? ───────────────────
    print()
    print(f"=== Step 4: GET /api/email/status/{message_id} (post-webhook) ===")
    resp3 = client.get(f"/api/email/status/{message_id}")
    print(f"status: {resp3.status_code}")
    body3 = resp3.json()
    print(f"body:   {json.dumps(body3, indent=2, default=str)}")
    expected_status = "opened"  # latest event mapped from email.opened
    actual_status = body3.get("status")
    event_types = [e.get("type") for e in body3.get("events", [])]
    print()
    print("=== Verification ===")
    ok_status = actual_status == expected_status
    ok_events = "email.delivered" in event_types and "email.opened" in event_types
    print(
        f"  status = {actual_status!r} (expected {expected_status!r}): "
        f"{'OK' if ok_status else 'FAIL'}"
    )
    print(f"  events contain delivered + opened: {'OK' if ok_events else 'FAIL'}  ({event_types})")
    return 0 if (ok_status and ok_events and bad_resp.status_code == 401) else 1


if __name__ == "__main__":
    raise SystemExit(main())
