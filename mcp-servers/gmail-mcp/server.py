"""
Gmail MCP Server — Python stdio transport
Uses Google service account domain-wide delegation to access david.stephens@keiracom.com
"""

import base64
import email as email_lib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html.parser import HTMLParser
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
SERVICE_ACCOUNT_FILE = "/home/elliotbot/google-service-account.json"
SUBJECT_EMAIL = "david.stephens@keiracom.com"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]

# ── MCP server ───────────────────────────────────────────────────────────────
mcp = FastMCP("gmail-mcp")


# ── Gmail client factory ─────────────────────────────────────────────────────
def _build_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES,
        subject=SUBJECT_EMAIL,
    )
    return build("gmail", "v1", credentials=creds)


# ── HTML stripping ────────────────────────────────────────────────────────────
class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return re.sub(r"\s+", " ", "".join(self._parts)).strip()


def _strip_html(html: str) -> str:
    s = _HTMLStripper()
    s.feed(html)
    return s.get_text()


# ── Message parsing helpers ───────────────────────────────────────────────────
def _decode_part(part: dict) -> str:
    """Base64-decode a message part body."""
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _extract_body(payload: dict) -> str:
    """Return plain text body; fall back to stripped HTML."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        return _decode_part(payload)

    if mime == "text/html":
        return _strip_html(_decode_part(payload))

    parts = payload.get("parts", [])
    # Prefer text/plain
    for p in parts:
        if p.get("mimeType") == "text/plain":
            text = _decode_part(p)
            if text:
                return text
    # Fall back to HTML
    for p in parts:
        if p.get("mimeType") == "text/html":
            text = _strip_html(_decode_part(p))
            if text:
                return text
    # Recurse into multipart
    for p in parts:
        text = _extract_body(p)
        if text:
            return text
    return ""


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _summarise_message(msg: dict) -> dict:
    payload = msg.get("payload", {})
    return {
        "message_id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "snippet": msg.get("snippet", ""),
        "from": _header(payload, "From"),
        "to": _header(payload, "To"),
        "subject": _header(payload, "Subject"),
        "date": _header(payload, "Date"),
    }


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def gmail_get_profile() -> dict:
    """Get Gmail mailbox profile for david.stephens@keiracom.com."""
    try:
        svc = _build_service()
        return svc.users().getProfile(userId="me").execute()
    except HttpError as e:
        return {"error": str(e)}


@mcp.tool()
def gmail_search_messages(q: str, max_results: int = 20) -> list[dict]:
    """
    Search Gmail messages using Gmail search syntax.

    Args:
        q: Gmail search query (e.g. 'from:alice@example.com', 'subject:invoice', 'is:unread')
        max_results: Maximum number of results to return (default 20, max 20)
    """
    try:
        svc = _build_service()
        limit = min(max_results, 20)
        resp = svc.users().messages().list(userId="me", q=q, maxResults=limit).execute()
        msg_ids = resp.get("messages", [])
        if not msg_ids:
            return []

        results = []
        for ref in msg_ids:
            msg = svc.users().messages().get(
                userId="me", id=ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"]
            ).execute()
            results.append({
                "message_id": msg.get("id"),
                "thread_id": msg.get("threadId"),
                "snippet": msg.get("snippet", ""),
                "from": _header(msg.get("payload", {}), "From"),
                "subject": _header(msg.get("payload", {}), "Subject"),
                "date": _header(msg.get("payload", {}), "Date"),
            })
        return results
    except HttpError as e:
        return [{"error": str(e)}]


@mcp.tool()
def gmail_read_message(message_id: str) -> dict:
    """
    Read a single Gmail message by ID.

    Args:
        message_id: The Gmail message ID
    """
    try:
        svc = _build_service()
        msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
        payload = msg.get("payload", {})
        return {
            "message_id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "from": _header(payload, "From"),
            "to": _header(payload, "To"),
            "subject": _header(payload, "Subject"),
            "date": _header(payload, "Date"),
            "snippet": msg.get("snippet", ""),
            "body": _extract_body(payload),
            "label_ids": msg.get("labelIds", []),
        }
    except HttpError as e:
        return {"error": str(e)}


@mcp.tool()
def gmail_read_thread(thread_id: str) -> dict:
    """
    Read a full Gmail thread by thread ID.

    Args:
        thread_id: The Gmail thread ID
    """
    try:
        svc = _build_service()
        thread = svc.users().threads().get(userId="me", id=thread_id, format="full").execute()
        messages = []
        for msg in thread.get("messages", []):
            payload = msg.get("payload", {})
            messages.append({
                "message_id": msg.get("id"),
                "from": _header(payload, "From"),
                "to": _header(payload, "To"),
                "subject": _header(payload, "Subject"),
                "date": _header(payload, "Date"),
                "snippet": msg.get("snippet", ""),
                "body": _extract_body(payload),
            })
        return {
            "thread_id": thread_id,
            "message_count": len(messages),
            "messages": messages,
        }
    except HttpError as e:
        return {"error": str(e)}


@mcp.tool()
def gmail_list_labels() -> list[dict]:
    """List all Gmail labels for the mailbox."""
    try:
        svc = _build_service()
        resp = svc.users().labels().list(userId="me").execute()
        return [
            {"id": l["id"], "name": l["name"], "type": l.get("type", "")}
            for l in resp.get("labels", [])
        ]
    except HttpError as e:
        return [{"error": str(e)}]


@mcp.tool()
def gmail_send_email(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """
    Send an email from david.stephens@keiracom.com.

    Args:
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Plain text email body
        cc: CC email address(es), comma-separated (optional)
        bcc: BCC email address(es), comma-separated (optional)
        reply_to: Reply-To address (optional)
    """
    try:
        svc = _build_service()
        msg = MIMEMultipart("alternative")
        msg["From"] = SUBJECT_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return {
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
            "status": "sent",
        }
    except HttpError as e:
        return {"error": str(e)}


@mcp.tool()
def gmail_create_draft(
    to: str,
    subject: str,
    body: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
) -> dict:
    """
    Create a Gmail draft email.

    Args:
        to: Recipient email address(es), comma-separated
        subject: Email subject
        body: Plain text email body
        cc: CC email address(es), comma-separated (optional)
        bcc: BCC email address(es), comma-separated (optional)
    """
    try:
        svc = _build_service()
        msg = MIMEMultipart("alternative")
        msg["From"] = SUBJECT_EMAIL
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        msg.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        result = svc.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()
        return {
            "draft_id": result.get("id"),
            "message_id": result.get("message", {}).get("id"),
            "thread_id": result.get("message", {}).get("threadId"),
            "status": "draft_created",
        }
    except HttpError as e:
        return {"error": str(e)}


@mcp.tool()
def gmail_list_drafts(max_results: int = 20) -> list[dict]:
    """
    List Gmail drafts.

    Args:
        max_results: Maximum number of drafts to return (default 20)
    """
    try:
        svc = _build_service()
        resp = svc.users().drafts().list(userId="me", maxResults=min(max_results, 20)).execute()
        drafts = resp.get("drafts", [])
        if not drafts:
            return []

        results = []
        for d in drafts:
            detail = svc.users().drafts().get(userId="me", id=d["id"], format="metadata").execute()
            msg = detail.get("message", {})
            payload = msg.get("payload", {})
            results.append({
                "draft_id": d["id"],
                "message_id": msg.get("id"),
                "subject": _header(payload, "Subject"),
                "to": _header(payload, "To"),
                "date": _header(payload, "Date"),
                "snippet": msg.get("snippet", ""),
            })
        return results
    except HttpError as e:
        return [{"error": str(e)}]


# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
