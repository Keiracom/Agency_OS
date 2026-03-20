#!/usr/bin/env python3
"""
write_intelligence_feed.py — Agency OS Intelligence Feed updater
Directive #178 | Maintained by Elliottbot (CTO)

The Intelligence Feed is written by research-1 and read by the CEO (Claude).
Each entry is timestamped. Entries are appended — never overwritten.

Usage:
    python write_intelligence_feed.py --doc-id <DOC_ID> --category <CATEGORY> --content <CONTENT>

Categories: tooling | competitor | regulatory | saas_strategy | self_improvement | general
"""

import argparse
import sys
from datetime import datetime, UTC
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

VALID_CATEGORIES = [
    "tooling", "competitor", "regulatory",
    "saas_strategy", "self_improvement", "general"
]


def get_docs_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("docs", "v1", credentials=creds)


def append_entry(docs_service, doc_id: str, category: str, content: str):
    """Append a timestamped entry to the Intelligence Feed."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    entry = f"\n\n[{timestamp}] [{category.upper()}]\n{content}\n{'─' * 60}"

    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_list = body.get("content", [])
    end_index = content_list[-1].get("endIndex", 1) if content_list else 1

    requests = [{
        "insertText": {
            "location": {"index": end_index - 1},
            "text": entry
        }
    }]
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()
    print(f"✅ Appended [{category.upper()}] entry to Intelligence Feed ({doc_id})")


def main():
    parser = argparse.ArgumentParser(description="Write to Agency OS Intelligence Feed")
    parser.add_argument("--doc-id", required=True, help="Google Doc ID")
    parser.add_argument("--category", required=True,
                        choices=VALID_CATEGORIES,
                        help="Entry category")
    parser.add_argument("--content", required=True, help="Finding to record")
    args = parser.parse_args()

    docs_service = get_docs_service()
    append_entry(docs_service, args.doc_id, args.category, args.content)


if __name__ == "__main__":
    main()
