#!/usr/bin/env python3
"""
write_manual_mirror.py — Mirror docs/MANUAL.md to Google Drive doc.

Best-effort: logs failure but does NOT raise or block directive completion.
Primary store is docs/MANUAL.md (repo). Google Doc is a mirror only.

Usage:
    python scripts/write_manual_mirror.py

Requirements:
    - /home/elliotbot/google-service-account.json
    - pip install google-api-python-client google-auth (in clawd venv)

Run from any directory. Uses absolute paths internally.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

GOOGLE_DOC_ID = os.environ.get(
    "GOOGLE_MANUAL_DOC_ID", "1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho"
)
SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
MANUAL_PATH = Path(__file__).parent.parent / "docs" / "MANUAL.md"
SCOPES = ["https://www.googleapis.com/auth/documents"]


def read_manual() -> str:
    if not MANUAL_PATH.exists():
        raise FileNotFoundError(f"MANUAL.md not found at {MANUAL_PATH}")
    return MANUAL_PATH.read_text(encoding="utf-8")


def mirror_to_drive(content: str) -> None:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        logger.error(
            "google-api-python-client not installed. "
            "Run: pip install google-api-python-client google-auth"
        )
        logger.warning("Mirror skipped — Drive write unavailable. Primary store (docs/MANUAL.md) is up to date.")
        return

    if not Path(SERVICE_ACCOUNT_FILE).exists():
        logger.error(f"Service account not found: {SERVICE_ACCOUNT_FILE}")
        logger.warning("Mirror skipped. Primary store (docs/MANUAL.md) is up to date.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build("docs", "v1", credentials=creds)

        # Get current doc length
        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        end_index = body_content[-1].get("endIndex", 2)

        requests = []

        # Clear existing content
        if end_index > 2:
            requests.append({
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index - 1}
                }
            })

        # Get updated end index after clear
        if requests:
            service.documents().batchUpdate(
                documentId=GOOGLE_DOC_ID, body={"requests": requests}
            ).execute()

        # Re-fetch doc after clear
        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        end_index = body_content[-1].get("endIndex", 2)

        # Insert new content
        service.documents().batchUpdate(
            documentId=GOOGLE_DOC_ID,
            body={"requests": [{"insertText": {"location": {"index": end_index - 1}, "text": content}}]},
        ).execute()

        # Verify
        doc = service.documents().get(documentId=GOOGLE_DOC_ID).execute()
        body_content = doc.get("body", {}).get("content", [])
        total_chars = sum(
            len(e.get("textRun", {}).get("content", ""))
            for b in body_content
            for e in b.get("paragraph", {}).get("elements", [])
        )
        logger.info(f"Mirror written successfully. Google Doc: {total_chars} chars.")

    except Exception as exc:
        logger.error(f"Drive mirror failed: {exc}")
        logger.warning(
            "Primary store (docs/MANUAL.md) is up to date. "
            "Google Doc mirror will be stale until next save-trigger directive."
        )


def main() -> None:
    logger.info(f"Reading MANUAL.md from {MANUAL_PATH}")
    content = read_manual()
    logger.info(f"MANUAL.md: {len(content)} chars")
    logger.info("Mirroring to Google Drive...")
    mirror_to_drive(content)
    logger.info("Done.")


if __name__ == "__main__":
    main()
