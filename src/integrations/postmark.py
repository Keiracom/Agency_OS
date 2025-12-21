"""
FILE: src/integrations/postmark.py
PURPOSE: Postmark integration for inbound email webhooks
PHASE: 3 (Integrations)
TASK: INT-007
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 18: Email threading via In-Reply-To headers
  - Rule 20: Webhook-first architecture
"""

import hashlib
import hmac
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class PostmarkClient:
    """
    Postmark client for inbound email handling.

    Handles webhook parsing and email operations.
    """

    BASE_URL = "https://api.postmarkapp.com"

    def __init__(self, server_token: str | None = None):
        self.server_token = server_token or settings.postmark_server_token
        if not self.server_token:
            raise IntegrationError(
                service="postmark",
                message="Postmark server token is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-Postmark-Server-Token": self.server_token,
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                service="postmark",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="postmark",
                message=f"Postmark request failed: {str(e)}",
            )

    def parse_inbound_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Postmark inbound webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed inbound email data
        """
        # Extract threading headers (Rule 18)
        headers = payload.get("Headers", [])
        header_dict = {h["Name"].lower(): h["Value"] for h in headers}

        return {
            "message_id": payload.get("MessageID"),
            "from_email": payload.get("FromFull", {}).get("Email"),
            "from_name": payload.get("FromFull", {}).get("Name"),
            "to_email": payload.get("ToFull", [{}])[0].get("Email") if payload.get("ToFull") else None,
            "subject": payload.get("Subject"),
            "text_body": payload.get("TextBody"),
            "html_body": payload.get("HtmlBody"),
            "stripped_text": payload.get("StrippedTextReply"),
            "date": payload.get("Date"),
            # Threading (Rule 18)
            "in_reply_to": header_dict.get("in-reply-to"),
            "references": header_dict.get("references", "").split(),
            "original_recipient": payload.get("OriginalRecipient"),
            # Metadata
            "mailbox_hash": payload.get("MailboxHash"),
            "tag": payload.get("Tag"),
            "attachments": [
                {
                    "name": a.get("Name"),
                    "content_type": a.get("ContentType"),
                    "content_length": a.get("ContentLength"),
                }
                for a in payload.get("Attachments", [])
            ],
        }

    def parse_bounce_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Postmark bounce webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed bounce data
        """
        return {
            "message_id": payload.get("MessageID"),
            "bounce_type": payload.get("Type"),
            "email": payload.get("Email"),
            "name": payload.get("Name"),
            "description": payload.get("Description"),
            "details": payload.get("Details"),
            "bounced_at": payload.get("BouncedAt"),
            "can_activate": payload.get("CanActivate"),
        }

    def parse_delivery_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Postmark delivery webhook payload.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed delivery data
        """
        return {
            "message_id": payload.get("MessageID"),
            "recipient": payload.get("Recipient"),
            "delivered_at": payload.get("DeliveredAt"),
            "server_id": payload.get("ServerID"),
        }

    def parse_open_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Postmark open tracking webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed open event data
        """
        return {
            "message_id": payload.get("MessageID"),
            "recipient": payload.get("Recipient"),
            "opened_at": payload.get("ReceivedAt"),
            "user_agent": payload.get("UserAgent"),
            "geo": {
                "city": payload.get("Geo", {}).get("City"),
                "country": payload.get("Geo", {}).get("Country"),
            },
            "platform": payload.get("Platform"),
            "client": payload.get("Client", {}).get("Name"),
        }

    def parse_click_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Postmark click tracking webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed click event data
        """
        return {
            "message_id": payload.get("MessageID"),
            "recipient": payload.get("Recipient"),
            "clicked_at": payload.get("ReceivedAt"),
            "original_link": payload.get("OriginalLink"),
            "user_agent": payload.get("UserAgent"),
            "geo": {
                "city": payload.get("Geo", {}).get("City"),
                "country": payload.get("Geo", {}).get("Country"),
            },
            "platform": payload.get("Platform"),
        }

    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_body: str | None = None,
        text_body: str | None = None,
        tag: str | None = None,
        # Threading (Rule 18)
        in_reply_to: str | None = None,
        references: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via Postmark.

        Args:
            from_email: Sender email
            to_email: Recipient email
            subject: Email subject
            html_body: HTML body
            text_body: Text body
            tag: Email tag for categorization
            in_reply_to: Message-ID for threading
            references: Reference message IDs

        Returns:
            Send result
        """
        data = {
            "From": from_email,
            "To": to_email,
            "Subject": subject,
        }

        if html_body:
            data["HtmlBody"] = html_body
        if text_body:
            data["TextBody"] = text_body
        if tag:
            data["Tag"] = tag

        # Threading headers (Rule 18)
        headers = []
        if in_reply_to:
            headers.append({"Name": "In-Reply-To", "Value": in_reply_to})
        if references:
            headers.append({"Name": "References", "Value": " ".join(references)})
        if headers:
            data["Headers"] = headers

        result = await self._request("POST", "/email", data)

        return {
            "success": True,
            "message_id": result.get("MessageID"),
            "provider": "postmark",
        }


# Singleton instance
_postmark_client: PostmarkClient | None = None


def get_postmark_client() -> PostmarkClient:
    """Get or create Postmark client instance."""
    global _postmark_client
    if _postmark_client is None:
        _postmark_client = PostmarkClient()
    return _postmark_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Inbound webhook parsing
# [x] Bounce webhook parsing
# [x] Delivery webhook parsing
# [x] Open tracking webhook parsing
# [x] Click tracking webhook parsing
# [x] Email sending with threading (Rule 18)
# [x] Webhook-first architecture (Rule 20)
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
