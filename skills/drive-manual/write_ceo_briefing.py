#!/usr/bin/env python3
"""
write_ceo_briefing.py — Agency OS CEO Briefing writer
Directive #178 | Maintained by Elliottbot (CTO)

The CEO Briefing is prepared by the CTO before each expected CEO session.
CEO reads this doc first to get up to speed quickly.

Each briefing REPLACES the previous one (CEO only needs latest).

Usage:
    python write_ceo_briefing.py --doc-id <DOC_ID> \
        --since <LAST_DIRECTIVE> \
        --completed <COMPLETED_ITEMS> \
        --blockers <BLOCKERS> \
        --priorities <RECOMMENDED_PRIORITIES> \
        --research <KEY_RESEARCH_FINDINGS>

Or pipe full briefing text:
    python write_ceo_briefing.py --doc-id <DOC_ID> --full-content "..."
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


def get_docs_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("docs", "v1", credentials=creds)


def write_briefing(docs_service, doc_id: str, content: str):
    """Replace entire CEO Briefing with new content."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    body = doc.get("body", {})
    content_list = body.get("content", [])
    end_index = content_list[-1].get("endIndex", 1) if content_list else 1

    requests = []
    if end_index > 2:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index - 1}
            }
        })
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
    print(f"✅ CEO Briefing written to doc {doc_id}")


def build_briefing(since: str, completed: str, blockers: str,
                   priorities: str, research: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""CEO BRIEFING — Agency OS
Prepared by: Elliottbot (CTO)
Prepared at: {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SINCE LAST SESSION (from Directive #{since})
{completed}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT BLOCKERS (Dave action required)
{blockers}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDED PRIORITIES (next session)
{priorities}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEY RESEARCH FINDINGS (from Intelligence Feed)
{research}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Read the Intelligence Feed for full research detail.
Read the Agency OS Manual for current system state.
"""


def main():
    parser = argparse.ArgumentParser(description="Write CEO Briefing to Google Doc")
    parser.add_argument("--doc-id", required=True, help="Google Doc ID")
    parser.add_argument("--full-content", help="Full briefing text (replaces structured args)")
    parser.add_argument("--since", help="Last directive number")
    parser.add_argument("--completed", help="What was completed")
    parser.add_argument("--blockers", help="Current blockers")
    parser.add_argument("--priorities", help="Recommended next priorities")
    parser.add_argument("--research", help="Key research findings")
    args = parser.parse_args()

    docs_service = get_docs_service()

    if args.full_content:
        write_briefing(docs_service, args.doc_id, args.full_content)
    elif all([args.since, args.completed, args.blockers, args.priorities, args.research]):
        content = build_briefing(
            args.since, args.completed, args.blockers,
            args.priorities, args.research
        )
        write_briefing(docs_service, args.doc_id, content)
    else:
        print("ERROR: Provide --full-content or all structured args (--since, --completed, --blockers, --priorities, --research)")
        sys.exit(1)


if __name__ == "__main__":
    main()
