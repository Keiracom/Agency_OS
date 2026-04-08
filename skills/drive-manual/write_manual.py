#!/usr/bin/env python3
"""
write_manual.py — Agency OS Manual updater
Directive #168 | Maintained by Elliottbot (CTO)

Usage:
    python write_manual.py --doc-id <DOC_ID> --section <SECTION> --content <CONTENT>
    python write_manual.py --doc-id <DOC_ID> --full   # write full manual skeleton

The service account (elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com)
must have Editor access to the doc. It cannot create docs (quota=0), only write to existing ones.
"""

import argparse
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]

FULL_MANUAL = """Agency OS Manual

This content is dynamically loaded from docs/MANUAL.md.
For the --full flag, the script reads docs/MANUAL.md from the repo root and writes it to the Google Doc.

Service account: elliottbot@gen-lang-client-0442027069.iam.gserviceaccount.com
Limitation: Cannot create Drive files (quota=0). Can only write to shared docs.
"""


def get_services():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    docs = build("docs", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)
    return docs, drive


def clear_and_write(docs_service, doc_id: str, content: str):
    """Replace all doc content with new content."""
    # Get current doc to find end index
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_list = body.get("content", [])
    end_index = content_list[-1].get("endIndex", 1) if content_list else 1

    requests = []
    # Delete all existing content (only if there's more than the default empty paragraph)
    if end_index > 2:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index - 1}
            }
        })
    # Insert new content
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": content
        }
    })

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()
    print(f"✅ Written {len(content)} chars to doc {doc_id}")


def update_section(docs_service, doc_id: str, section: str, new_content: str):
    """Append a section update with timestamp."""
    from datetime import datetime, UTC
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    text = f"\n\n[{timestamp}] {section}:\n{new_content}"

    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_list = body.get("content", [])
    end_index = content_list[-1].get("endIndex", 1) if content_list else 1

    requests = [{
        "insertText": {
            "location": {"index": end_index - 1},
            "text": text
        }
    }]
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests}
    ).execute()
    print(f"✅ Appended section '{section}' to doc {doc_id}")


def main():
    parser = argparse.ArgumentParser(description="Update Agency OS Manual Google Doc")
    parser.add_argument("--doc-id", required=True, help="Google Doc ID")
    parser.add_argument("--full", action="store_true", help="Write full manual skeleton")
    parser.add_argument("--section", help="Section name to update")
    parser.add_argument("--content", help="Content to write to section")
    parser.add_argument("--date", default=None, help="Date string for full write")
    args = parser.parse_args()

    docs_service, drive_service = get_services()

    if args.full:
        manual_path = args.date or "docs/MANUAL.md"  # --date repurposed as --file path fallback
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(repo_root, "docs", "MANUAL.md")
        if not os.path.exists(file_path):
            print(f"ERROR: docs/MANUAL.md not found at {file_path}")
            sys.exit(1)
        content = open(file_path).read()
        clear_and_write(docs_service, args.doc_id, content)
    elif args.section and args.content:
        update_section(docs_service, args.doc_id, args.section, args.content)
    else:
        print("ERROR: Provide --full or both --section and --content")
        sys.exit(1)


if __name__ == "__main__":
    main()
