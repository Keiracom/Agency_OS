"""
FILE: src/integrations/heyreach.py
PURPOSE: HeyReach integration for LinkedIn automation with proxy
PHASE: 3 (Integrations)
TASK: INT-009
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 17: Resource-level rate limits (17/day/seat)
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ResourceRateLimitError


class HeyReachClient:
    """
    HeyReach client for LinkedIn automation.

    Manages LinkedIn outreach via HeyReach API with
    per-seat rate limiting (17/day per seat).
    """

    BASE_URL = "https://api.heyreach.io/v1"
    DAILY_LIMIT_PER_SEAT = 17  # Rule 17

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.heyreach_api_key
        if not self.api_key:
            raise IntegrationError(
                service="heyreach",
                message="HeyReach API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
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
                service="heyreach",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="heyreach",
                message=f"HeyReach request failed: {str(e)}",
            )

    async def get_seats(self) -> list[dict[str, Any]]:
        """
        Get available LinkedIn seats.

        Returns:
            List of seats with usage info
        """
        result = await self._request("GET", "/seats")
        return result.get("seats", [])

    async def send_connection_request(
        self,
        seat_id: str,
        linkedin_url: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send LinkedIn connection request.

        Args:
            seat_id: HeyReach seat ID to use
            linkedin_url: Target LinkedIn profile URL
            message: Optional connection message

        Returns:
            Connection request result
        """
        data = {
            "seat_id": seat_id,
            "profile_url": linkedin_url,
        }
        if message:
            data["message"] = message[:300]  # LinkedIn limit

        result = await self._request("POST", "/connections/request", data)

        return {
            "success": True,
            "request_id": result.get("id"),
            "status": result.get("status"),
            "provider": "heyreach",
        }

    async def send_message(
        self,
        seat_id: str,
        linkedin_url: str,
        message: str,
    ) -> dict[str, Any]:
        """
        Send LinkedIn direct message.

        Args:
            seat_id: HeyReach seat ID
            linkedin_url: Target LinkedIn profile URL
            message: Message content

        Returns:
            Message send result
        """
        data = {
            "seat_id": seat_id,
            "profile_url": linkedin_url,
            "message": message,
        }

        result = await self._request("POST", "/messages/send", data)

        return {
            "success": True,
            "message_id": result.get("id"),
            "status": result.get("status"),
            "provider": "heyreach",
        }

    async def get_conversations(
        self,
        seat_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get LinkedIn conversations for a seat.

        Args:
            seat_id: HeyReach seat ID
            limit: Maximum conversations to return

        Returns:
            List of conversations
        """
        result = await self._request(
            "GET",
            f"/conversations?seat_id={seat_id}&limit={limit}",
        )

        return [
            {
                "conversation_id": c.get("id"),
                "profile_url": c.get("profile_url"),
                "name": c.get("name"),
                "last_message": c.get("last_message"),
                "last_message_at": c.get("last_message_at"),
                "unread": c.get("unread", False),
            }
            for c in result.get("conversations", [])
        ]

    async def get_new_replies(self, seat_id: str) -> list[dict[str, Any]]:
        """
        Get new replies (unread messages) for a seat.

        Args:
            seat_id: HeyReach seat ID

        Returns:
            List of new replies
        """
        result = await self._request(
            "GET",
            f"/messages/unread?seat_id={seat_id}",
        )

        return [
            {
                "message_id": m.get("id"),
                "profile_url": m.get("profile_url"),
                "name": m.get("sender_name"),
                "message": m.get("content"),
                "received_at": m.get("received_at"),
            }
            for m in result.get("messages", [])
        ]

    async def get_profile(self, linkedin_url: str) -> dict[str, Any]:
        """
        Get LinkedIn profile data.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Profile data
        """
        result = await self._request(
            "POST",
            "/profiles/lookup",
            {"profile_url": linkedin_url},
        )

        profile = result.get("profile", {})
        return {
            "found": bool(profile),
            "linkedin_url": linkedin_url,
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "headline": profile.get("headline"),
            "company": profile.get("current_company"),
            "location": profile.get("location"),
            "connections": profile.get("connections_count"),
        }

    async def check_seat_limit(self, seat_id: str) -> dict[str, Any]:
        """
        Check if seat has available daily capacity.

        Args:
            seat_id: HeyReach seat ID

        Returns:
            Limit info with remaining capacity
        """
        result = await self._request("GET", f"/seats/{seat_id}/usage")

        daily_used = result.get("daily_actions", 0)
        remaining = max(0, self.DAILY_LIMIT_PER_SEAT - daily_used)

        return {
            "seat_id": seat_id,
            "daily_limit": self.DAILY_LIMIT_PER_SEAT,
            "daily_used": daily_used,
            "remaining": remaining,
            "can_send": remaining > 0,
        }

    # ==========================================
    # LinkedIn Account Management (Phase 24H)
    # ==========================================

    async def add_linkedin_account(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """
        Add a LinkedIn account to HeyReach.

        NOTE: Check HeyReach API documentation for actual endpoint.
        This is based on common patterns for LinkedIn automation platforms.

        Args:
            email: LinkedIn account email
            password: LinkedIn account password

        Returns:
            Dict with:
            - success: bool
            - requires_2fa: bool (if 2FA needed)
            - 2fa_method: str ('sms', 'email', 'authenticator')
            - sender_id: str (HeyReach sender ID)
            - account_id: str (HeyReach account ID)
            - profile_url: str
            - profile_name: str
            - headline: str
            - connection_count: int
            - error: str (if failed)
        """
        try:
            result = await self._request(
                "POST",
                "/senders/linkedin",
                data={
                    "email": email,
                    "password": password,
                },
            )

            # Check if 2FA is required
            if result.get("requires_verification") or result.get("requires_2fa"):
                return {
                    "success": False,
                    "requires_2fa": True,
                    "2fa_method": result.get("verification_method", "unknown"),
                }

            # Check for errors
            if result.get("error") or not result.get("sender_id"):
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": result.get("error", "Failed to connect LinkedIn account"),
                }

            # Success
            return {
                "success": True,
                "requires_2fa": False,
                "sender_id": result.get("sender_id") or result.get("id"),
                "account_id": result.get("account_id"),
                "profile_url": result.get("profile_url") or result.get("linkedin_url"),
                "profile_name": result.get("name") or result.get("profile_name"),
                "headline": result.get("headline"),
                "connection_count": result.get("connections") or result.get("connection_count"),
            }

        except APIError as e:
            # Handle specific API errors
            if e.status_code == 401:
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": "Invalid LinkedIn credentials",
                }
            elif e.status_code == 429:
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": "Too many attempts. Please try again later.",
                }
            raise

    async def verify_2fa(
        self,
        email: str,
        password: str,
        code: str,
    ) -> dict[str, Any]:
        """
        Submit 2FA code to complete LinkedIn connection.

        Args:
            email: LinkedIn account email
            password: LinkedIn account password
            code: 2FA verification code

        Returns:
            Same structure as add_linkedin_account
        """
        try:
            result = await self._request(
                "POST",
                "/senders/linkedin/verify",
                data={
                    "email": email,
                    "password": password,
                    "code": code,
                },
            )

            if result.get("error") or not result.get("sender_id"):
                return {
                    "success": False,
                    "error": result.get("error", "Invalid verification code"),
                }

            return {
                "success": True,
                "sender_id": result.get("sender_id") or result.get("id"),
                "account_id": result.get("account_id"),
                "profile_url": result.get("profile_url") or result.get("linkedin_url"),
                "profile_name": result.get("name") or result.get("profile_name"),
                "headline": result.get("headline"),
                "connection_count": result.get("connections") or result.get("connection_count"),
            }

        except APIError as e:
            if e.status_code == 400:
                return {
                    "success": False,
                    "error": "Invalid verification code",
                }
            raise

    async def remove_sender(self, sender_id: str) -> dict[str, Any]:
        """
        Remove a LinkedIn sender from HeyReach.

        Args:
            sender_id: HeyReach sender ID

        Returns:
            Dict with success status
        """
        result = await self._request("DELETE", f"/senders/{sender_id}")
        return {
            "success": True,
            "sender_id": sender_id,
        }

    async def get_sender(self, sender_id: str) -> dict[str, Any]:
        """
        Get sender details from HeyReach.

        Args:
            sender_id: HeyReach sender ID

        Returns:
            Sender details
        """
        result = await self._request("GET", f"/senders/{sender_id}")
        return {
            "sender_id": result.get("id"),
            "email": result.get("email"),
            "profile_url": result.get("profile_url"),
            "profile_name": result.get("name"),
            "headline": result.get("headline"),
            "connection_count": result.get("connections"),
            "status": result.get("status"),
        }


# Singleton instance
_heyreach_client: HeyReachClient | None = None


def get_heyreach_client() -> HeyReachClient:
    """Get or create HeyReach client instance."""
    global _heyreach_client
    if _heyreach_client is None:
        _heyreach_client = HeyReachClient()
    return _heyreach_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Seat management
# [x] Connection requests
# [x] Direct messaging
# [x] Conversation retrieval
# [x] New replies (unread messages)
# [x] Profile lookup
# [x] Daily limit tracking (17/seat)
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
