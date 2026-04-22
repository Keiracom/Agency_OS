#!/usr/bin/env python3
"""
verify_manual.py — Read-only Drive Manual verification for four-store peer-check.

Any callsign with read access to /home/elliotbot/google-service-account.json
can invoke this to confirm the Drive mirror of the Agency OS Manual matches
what the writing callsign claims (LAW XV Store 4).

Usage:
    python scripts/verify_manual.py [--doc-id DOC_ID]

Output (stdout, key=value lines):
    name=...
    modifiedTime=...
    body_chars=...
    body_sha256_16=...
    first_120_chars=...

Exit codes:
    0 = doc fetched, fields printed
    2 = auth/file/API error
"""
import argparse
import hashlib
import sys

from google.oauth2 import service_account
from googleapiclient.discovery import build

DEFAULT_DOC_ID = "1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho"
SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doc-id", default=DEFAULT_DOC_ID)
    args = parser.parse_args()

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    drive = build("drive", "v3", credentials=creds)
    docs = build("docs", "v1", credentials=creds)

    meta = drive.files().get(fileId=args.doc_id, fields="name,modifiedTime").execute()
    doc = docs.documents().get(documentId=args.doc_id).execute()

    parts = []
    for el in doc.get("body", {}).get("content", []):
        for p in el.get("paragraph", {}).get("elements", []):
            t = p.get("textRun", {}).get("content", "")
            if t:
                parts.append(t)
    body_text = "".join(parts)
    body_hash = hashlib.sha256(body_text.encode()).hexdigest()[:16]

    print(f"name={meta.get('name')}")
    print(f"modifiedTime={meta.get('modifiedTime')}")
    print(f"body_chars={len(body_text)}")
    print(f"body_sha256_16={body_hash}")
    print(f"first_120_chars={body_text[:120].strip()!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
