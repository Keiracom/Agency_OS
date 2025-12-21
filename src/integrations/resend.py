"""
FILE: src/integrations/resend.py
PURPOSE: Resend API integration for email sending with threading
PHASE: 3 (Integrations)
TASK: INT-006
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 18: Email threading via In-Reply-To headers
"""

from typing import Any

import resend

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class ResendClient:
    """
    Resend email client.

    Handles outbound email sending with threading support
    for follow-up sequences.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.resend_api_key
        if not self.api_key:
            raise IntegrationError(
                service="resend",
                message="Resend API key is required",
            )
        resend.api_key = self.api_key

    async def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str | None = None,
        reply_to: str | None = None,
        # Threading support (Rule 18)
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        # Tracking
        tags: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via Resend.

        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text body (optional)
            reply_to: Reply-to address
            in_reply_to: Message-ID for threading (Rule 18)
            references: Reference message IDs for threading
            tags: Metadata tags

        Returns:
            Send result with message ID
        """
        try:
            # Build headers for threading
            headers = {}
            if in_reply_to:
                headers["In-Reply-To"] = in_reply_to
            if references:
                headers["References"] = " ".join(references)

            email_data = {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }

            if text_body:
                email_data["text"] = text_body
            if reply_to:
                email_data["reply_to"] = reply_to
            if headers:
                email_data["headers"] = headers
            if tags:
                email_data["tags"] = [{"name": k, "value": v} for k, v in tags.items()]

            result = resend.Emails.send(email_data)

            return {
                "success": True,
                "message_id": result.get("id"),
                "provider": "resend",
            }

        except Exception as e:
            raise APIError(
                service="resend",
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
            emails: List of email data dicts

        Returns:
            List of send results
        """
        try:
            batch_data = []
            for email in emails:
                headers = {}
                if email.get("in_reply_to"):
                    headers["In-Reply-To"] = email["in_reply_to"]
                if email.get("references"):
                    headers["References"] = " ".join(email["references"])

                item = {
                    "from": email["from_email"],
                    "to": [email["to_email"]],
                    "subject": email["subject"],
                    "html": email["html_body"],
                }
                if email.get("text_body"):
                    item["text"] = email["text_body"]
                if headers:
                    item["headers"] = headers

                batch_data.append(item)

            result = resend.Batch.send(batch_data)

            return [
                {"success": True, "message_id": r.get("id"), "provider": "resend"}
                for r in result.get("data", [])
            ]

        except Exception as e:
            raise APIError(
                service="resend",
                status_code=500,
                message=f"Batch send failed: {str(e)}",
            )

    async def get_email(self, email_id: str) -> dict[str, Any]:
        """
        Get email details by ID.

        Args:
            email_id: Resend email ID

        Returns:
            Email details
        """
        try:
            result = resend.Emails.get(email_id)
            return {
                "id": result.get("id"),
                "from": result.get("from"),
                "to": result.get("to"),
                "subject": result.get("subject"),
                "created_at": result.get("created_at"),
                "last_event": result.get("last_event"),
            }
        except Exception as e:
            raise APIError(
                service="resend",
                status_code=500,
                message=f"Failed to get email: {str(e)}",
            )


# Singleton instance
_resend_client: ResendClient | None = None


def get_resend_client() -> ResendClient:
    """Get or create Resend client instance."""
    global _resend_client
    if _resend_client is None:
        _resend_client = ResendClient()
    return _resend_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Email sending with HTML/text
# [x] Threading support via In-Reply-To (Rule 18)
# [x] References header for thread
# [x] Batch sending
# [x] Get email details
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
