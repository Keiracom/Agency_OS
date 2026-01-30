"""
Contract: src/integrations/salesforge.py
Purpose: Salesforge API integration for email sending with threading
Layer: 2 - integrations
Imports: models ONLY
Consumers: engines

PHASE: 18/21 (Email Infrastructure + E2E Testing)
TASK: Replace Resend with Salesforge

Salesforge is the primary email sending provider that works with
Warmforge-warmed mailboxes. This replaces Resend to preserve warmup progress.

API Reference:
- Base URL: https://api.salesforge.ai/public/v2
- Auth: Authorization header (plain key, not Bearer)
- Swagger: https://api.salesforge.ai/public/v2/swagger/index.html
"""

import contextlib
import logging
from typing import Any

import httpx
import sentry_sdk

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError

logger = logging.getLogger(__name__)


class SalesforgeClient:
    """
    Salesforge email client.

    Handles outbound email sending with threading support
    for follow-up sequences. Uses mailboxes warmed via Warmforge.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
    ):
        """
        Initialize Salesforge client.

        Args:
            api_key: Salesforge API key (uses settings if not provided)
            api_url: Salesforge API URL (uses settings if not provided)
        """
        self.api_key = api_key or settings.salesforge_api_key
        self.api_url = (api_url or settings.salesforge_api_url).rstrip("/")

        if not self.api_key:
            raise IntegrationError(
                service="salesforge",
                message="Salesforge API key is required",
            )

        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            headers={
                "Authorization": self.api_key,  # Salesforge uses plain Authorization header, not X-API-KEY
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an API request to Salesforge.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            APIError: If the request fails
        """
        try:
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_body = {}
            with contextlib.suppress(Exception):
                error_body = e.response.json()

            sentry_sdk.set_context(
                "salesforge_error",
                {
                    "status_code": e.response.status_code,
                    "response": error_body,
                    "endpoint": endpoint,
                },
            )
            sentry_sdk.capture_exception(e)

            raise APIError(
                service="salesforge",
                status_code=e.response.status_code,
                message=f"Salesforge API error: {error_body.get('message', str(e))}",
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="salesforge",
                status_code=500,
                message=f"Salesforge request failed: {str(e)}",
            )

    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        reply_to: str | None = None,
        # Threading support
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        # Tracking
        tags: dict[str, str] | None = None,
        # Salesforge-specific
        mailbox_id: str | None = None,
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via Salesforge.

        Args:
            from_email: Sender email address (must be a warmed mailbox)
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text body (optional)
            reply_to: Reply-to address
            in_reply_to: Message-ID for threading
            references: Reference message IDs for threading
            tags: Metadata tags (lead_id, campaign_id, client_id)
            mailbox_id: Salesforge mailbox ID to use
            campaign_id: Salesforge campaign ID (optional)

        Returns:
            Send result with message ID
        """
        try:
            # Build the email payload for Salesforge API
            email_data = {
                "to": to_email,
                "subject": subject,
                "htmlBody": html_body,
            }

            # Parse from_email to extract name if present
            if "<" in from_email and ">" in from_email:
                # Format: "Name <email@domain.com>"
                parts = from_email.split("<")
                from_name = parts[0].strip().strip('"')
                from_addr = parts[1].rstrip(">").strip()
                email_data["fromName"] = from_name
                email_data["from"] = from_addr
            else:
                email_data["from"] = from_email

            if text_body:
                email_data["textBody"] = text_body
            if reply_to:
                email_data["replyTo"] = reply_to
            if mailbox_id:
                email_data["mailboxId"] = mailbox_id

            # Threading headers
            custom_headers = {}
            if in_reply_to:
                custom_headers["In-Reply-To"] = in_reply_to
            if references:
                custom_headers["References"] = " ".join(references)
            if custom_headers:
                email_data["customHeaders"] = custom_headers

            # Metadata for tracking
            if tags:
                email_data["metadata"] = tags

            # Send via Salesforge API
            result = await self._request("POST", "/emails/send", json=email_data)

            # Extract message ID from response
            message_id = result.get("messageId") or result.get("id") or result.get("email_id")

            logger.info(f"Salesforge email sent: {message_id} to {to_email}")

            return {
                "success": True,
                "message_id": message_id,
                "provider": "salesforge",
                "salesforge_response": result,
            }

        except APIError:
            raise
        except Exception as e:
            sentry_sdk.set_context(
                "salesforge_email",
                {
                    "to": to_email,
                    "subject": subject[:50],
                    "from": from_email,
                },
            )
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="salesforge",
                status_code=500,
                message=f"Failed to send email: {str(e)}",
            )

    async def send_batch(
        self,
        emails: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Send multiple emails in batch.

        Args:
            emails: List of email data dicts with keys:
                - from_email: Sender email
                - to_email: Recipient email
                - subject: Email subject
                - html_body: HTML content
                - text_body: Plain text (optional)
                - in_reply_to: Threading (optional)
                - references: Threading (optional)

        Returns:
            List of send results
        """
        results = []

        # Salesforge may support batch sending, but for now we'll
        # send individually to maintain thread consistency
        for email in emails:
            try:
                result = await self.send_email(
                    from_email=email["from_email"],
                    to_email=email["to_email"],
                    subject=email["subject"],
                    html_body=email["html_body"],
                    text_body=email.get("text_body"),
                    in_reply_to=email.get("in_reply_to"),
                    references=email.get("references"),
                    tags=email.get("tags"),
                    mailbox_id=email.get("mailbox_id"),
                )
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "error": str(e),
                        "provider": "salesforge",
                        "to_email": email["to_email"],
                    }
                )

        return results

    async def get_email(self, email_id: str) -> dict[str, Any]:
        """
        Get email details by ID.

        Args:
            email_id: Salesforge email/message ID

        Returns:
            Email details
        """
        try:
            result = await self._request("GET", f"/emails/{email_id}")
            return {
                "id": result.get("id") or result.get("messageId"),
                "from": result.get("from"),
                "to": result.get("to"),
                "subject": result.get("subject"),
                "created_at": result.get("createdAt") or result.get("sentAt"),
                "status": result.get("status"),
                "opened": result.get("opened", False),
                "clicked": result.get("clicked", False),
                "replied": result.get("replied", False),
            }
        except Exception as e:
            raise APIError(
                service="salesforge",
                status_code=500,
                message=f"Failed to get email: {str(e)}",
            )

    async def get_mailboxes(self) -> list[dict[str, Any]]:
        """
        Get list of available mailboxes.

        Returns:
            List of mailbox details including warmup status
        """
        try:
            result = await self._request("GET", "/mailboxes")
            return result.get("data", result.get("mailboxes", []))
        except Exception as e:
            raise APIError(
                service="salesforge",
                status_code=500,
                message=f"Failed to get mailboxes: {str(e)}",
            )

    async def get_mailbox_by_email(self, email: str) -> dict[str, Any] | None:
        """
        Find a mailbox by email address.

        Args:
            email: Email address to search

        Returns:
            Mailbox details or None if not found
        """
        mailboxes = await self.get_mailboxes()
        email_lower = email.lower()

        for mailbox in mailboxes:
            mailbox_email = mailbox.get("email", "").lower()
            if mailbox_email == email_lower:
                return mailbox

        return None

    async def check_warmup_status(self, email: str) -> dict[str, Any]:
        """
        Check warmup status for a mailbox.

        Args:
            email: Mailbox email address

        Returns:
            Warmup status details
        """
        mailbox = await self.get_mailbox_by_email(email)
        if not mailbox:
            return {
                "email": email,
                "found": False,
                "is_warmed": False,
            }

        return {
            "email": email,
            "found": True,
            "mailbox_id": mailbox.get("id"),
            "warmup_enabled": mailbox.get("warmupEnabled", False),
            "warmup_status": mailbox.get("warmupStatus", "unknown"),
            "reputation_score": mailbox.get("reputationScore"),
            "daily_limit": mailbox.get("dailyLimit"),
            "is_warmed": mailbox.get("warmupStatus", "").lower() in ("completed", "ready"),
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton instance
_salesforge_client: SalesforgeClient | None = None


def get_salesforge_client() -> SalesforgeClient:
    """Get or create Salesforge client instance."""
    global _salesforge_client
    if _salesforge_client is None:
        _salesforge_client = SalesforgeClient()
    return _salesforge_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Email sending with HTML/text
# [x] Threading support via In-Reply-To headers
# [x] References header for thread
# [x] Batch sending
# [x] Get email details
# [x] Get mailboxes for sender selection
# [x] Check warmup status
# [x] Error handling with custom exceptions
# [x] Sentry integration for error tracking
# [x] All functions have type hints
# [x] All functions have docstrings
