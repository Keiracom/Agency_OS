#!/usr/bin/env python3
"""scripts/smoke_email_backend.py — live end-to-end smoke for Task #20.

Spins the FastAPI app via TestClient (no separate uvicorn needed), sends a
real email via Resend to RECIPIENT (default dvidstephens@gmail.com — Dave),
queries /status, and prints both responses verbatim.

Honest pre-revenue smoke: this does send a real email. Costs one Resend
free-tier credit. No fabricated data.
"""
from __future__ import annotations

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


def main() -> int:
    client = TestClient(app)
    payload = {
        "to": RECIPIENT,
        "subject": f"Task #20 smoke {int(time.time())}",
        "body_text": (
            "Smoke test for Task #20 email backend. "
            "If you got this, /api/email/send hit Resend live and "
            "logged a queued row in keiracom_admin.email_events."
        ),
    }
    print("=== POST /api/email/send ===")
    print("request:", json.dumps(payload, indent=2))
    resp = client.post("/api/email/send", json=payload)
    print(f"status: {resp.status_code}")
    print(f"body:   {resp.text}")
    if resp.status_code != 202:
        return 1
    message_id = resp.json()["message_id"]

    # Resend updates async; let DB row settle, then read.
    time.sleep(1.0)
    print()
    print(f"=== GET /api/email/status/{message_id} ===")
    resp2 = client.get(f"/api/email/status/{message_id}")
    print(f"status: {resp2.status_code}")
    print(f"body:   {json.dumps(resp2.json(), indent=2, default=str)}")
    return 0 if resp2.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
