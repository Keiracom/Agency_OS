"""
Contract: src/integrations/unipile.py
Purpose: Unipile API client for LinkedIn automation (replacing HeyReach)
Layer: 2 - integrations
Imports: models ONLY
Consumers: engines
Phase: Unipile Migration

Key differences from HeyReach:
- Hosted auth flow (no credential storage needed)
- OAuth-style LinkedIn connection
- Higher rate limits (80-100 connections/day vs 17)
- SOC 2 compliant
"""

from typing import Any
from datetime import datetime, timedelta

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ResourceRateLimitError


class UnipileClient:
    """
    Unipile client for LinkedIn automation.

    Manages LinkedIn outreach via Unipile API with:
    - Hosted auth flow for LinkedIn connection
    - Connection requests and messages
    - Profile data retrieval
    - Webhook-based status updates

    Rate limits (recommended by Unipile):
    - Connection requests: 80-100/day per account
    - Messages: 100-150/day per account
    """

    # Default rate limits (can be increased with Unipile)
    DAILY_CONNECTION_LIMIT = 80
    DAILY_MESSAGE_LIMIT = 100

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
    ):
        self.api_url = (api_url or settings.unipile_api_url).rstrip("/")
        self.api_key = api_key or settings.unipile_api_key

        if not self.api_url or not self.api_key:
            raise IntegrationError(
                service="unipile",
                message="Unipile API URL and API key are required",
            )

        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.api_url}/api/v1",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
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
        params: dict | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
                params=params,
            )
            response.raise_for_status()

            # Handle empty responses
            if response.status_code == 204:
                return {"success": True}

            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise ResourceRateLimitError(
                    resource_type="unipile",
                    resource_id="api",
                    message="Unipile API rate limit exceeded",
                )
            raise APIError(
                service="unipile",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="unipile",
                message=f"Unipile request failed: {str(e)}",
            )

    # ==========================================
    # Account Management (Hosted Auth)
    # ==========================================

    async def create_hosted_auth_link(
        self,
        providers: list[str] | None = None,
        success_redirect_url: str | None = None,
        failure_redirect_url: str | None = None,
        notify_url: str | None = None,
        name: str | None = None,
        expires_on: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a hosted auth link for LinkedIn connection.

        This generates a URL that users visit to connect their LinkedIn
        account via Unipile's hosted wizard. Eliminates need to store
        credentials or handle 2FA.

        Args:
            providers: List of providers (default: ["LINKEDIN"])
            success_redirect_url: URL to redirect on success
            failure_redirect_url: URL to redirect on failure
            notify_url: Webhook URL to receive account_id
            name: Internal identifier (e.g., client_id) for matching
            expires_on: When the link expires (default: 24 hours)

        Returns:
            Dict with:
            - url: The hosted auth URL for the user to visit
            - object: "HostedAuthLink"
        """
        if expires_on is None:
            expires_on = datetime.utcnow() + timedelta(hours=24)

        data = {
            "type": "create",
            "api_url": self.api_url,
            "providers": providers or ["LINKEDIN"],
            "expiresOn": expires_on.isoformat(),
        }

        if success_redirect_url:
            data["success_redirect_url"] = success_redirect_url
        if failure_redirect_url:
            data["failure_redirect_url"] = failure_redirect_url
        if notify_url:
            data["notify_url"] = notify_url
        if name:
            data["name"] = name

        result = await self._request("POST", "/hosted/accounts/link", data)

        return {
            "url": result.get("url"),
            "object": result.get("object", "HostedAuthLink"),
        }

    async def get_accounts(self) -> list[dict[str, Any]]:
        """
        Get all connected accounts.

        Returns:
            List of connected accounts with status
        """
        result = await self._request("GET", "/accounts")

        items = result.get("items", [])
        return [
            {
                "account_id": acc.get("id"),
                "provider": acc.get("type"),
                "status": acc.get("connection_status"),
                "name": acc.get("name"),
                "email": acc.get("email"),
                "created_at": acc.get("created_at"),
            }
            for acc in items
        ]

    async def get_account(self, account_id: str) -> dict[str, Any]:
        """
        Get a specific account's details.

        Args:
            account_id: Unipile account ID

        Returns:
            Account details including status
        """
        result = await self._request("GET", f"/accounts/{account_id}")

        return {
            "account_id": result.get("id"),
            "provider": result.get("type"),
            "status": result.get("connection_status"),
            "name": result.get("name"),
            "email": result.get("email"),
            "sources": result.get("sources", []),
            "created_at": result.get("created_at"),
        }

    async def delete_account(self, account_id: str) -> dict[str, Any]:
        """
        Disconnect and delete an account.

        Args:
            account_id: Unipile account ID

        Returns:
            Deletion confirmation
        """
        await self._request("DELETE", f"/accounts/{account_id}")

        return {
            "success": True,
            "account_id": account_id,
            "message": "Account disconnected",
        }

    # ==========================================
    # LinkedIn Messaging
    # ==========================================

    async def send_invitation(
        self,
        account_id: str,
        recipient_id: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send a LinkedIn connection invitation.

        Args:
            account_id: Unipile account ID (sender's LinkedIn)
            recipient_id: LinkedIn profile URN or URL of recipient
            message: Optional connection message (max 300 chars)

        Returns:
            Dict with invitation result
        """
        data = {
            "account_id": account_id,
            "attendees_ids": [recipient_id],
        }

        if message:
            data["text"] = message[:300]  # LinkedIn limit

        result = await self._request("POST", "/linkedin/invitations", data)

        return {
            "success": True,
            "invitation_id": result.get("id"),
            "status": result.get("status", "sent"),
            "provider": "unipile",
        }

    async def send_message(
        self,
        account_id: str,
        chat_id: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Send a LinkedIn direct message to an existing conversation.

        Args:
            account_id: Unipile account ID
            chat_id: Existing chat/conversation ID
            text: Message content

        Returns:
            Dict with message result
        """
        data = {
            "account_id": account_id,
            "text": text,
        }

        result = await self._request("POST", f"/chats/{chat_id}/messages", data)

        return {
            "success": True,
            "message_id": result.get("id"),
            "chat_id": chat_id,
            "status": result.get("status", "sent"),
            "provider": "unipile",
        }

    async def start_new_chat(
        self,
        account_id: str,
        recipient_id: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Start a new conversation with a LinkedIn connection.

        Args:
            account_id: Unipile account ID
            recipient_id: LinkedIn profile URN of recipient
            text: Initial message

        Returns:
            Dict with chat and message info
        """
        data = {
            "account_id": account_id,
            "attendees_ids": [recipient_id],
            "text": text,
        }

        result = await self._request("POST", "/chats", data)

        return {
            "success": True,
            "chat_id": result.get("id") or result.get("chat_id"),
            "message_id": result.get("message_id"),
            "status": "sent",
            "provider": "unipile",
        }

    # ==========================================
    # Conversations & Messages
    # ==========================================

    async def get_chats(
        self,
        account_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Get LinkedIn conversations for an account.

        Args:
            account_id: Unipile account ID
            limit: Maximum chats to return
            cursor: Pagination cursor

        Returns:
            Dict with chats list and pagination
        """
        params = {
            "account_id": account_id,
            "limit": limit,
        }
        if cursor:
            params["cursor"] = cursor

        result = await self._request("GET", "/chats", params=params)

        return {
            "chats": [
                {
                    "chat_id": c.get("id"),
                    "account_id": account_id,
                    "attendees": c.get("attendees", []),
                    "last_message_at": c.get("last_message_at"),
                    "unread_count": c.get("unread_count", 0),
                }
                for c in result.get("items", [])
            ],
            "cursor": result.get("cursor"),
            "has_more": result.get("cursor") is not None,
        }

    async def get_messages(
        self,
        chat_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """
        Get messages from a specific chat.

        Args:
            chat_id: Chat/conversation ID
            limit: Maximum messages to return
            cursor: Pagination cursor

        Returns:
            Dict with messages list and pagination
        """
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor

        result = await self._request("GET", f"/chats/{chat_id}/messages", params=params)

        return {
            "messages": [
                {
                    "message_id": m.get("id"),
                    "chat_id": chat_id,
                    "sender_id": m.get("sender_id"),
                    "text": m.get("text"),
                    "created_at": m.get("created_at"),
                    "is_sender": m.get("is_sender", False),
                }
                for m in result.get("items", [])
            ],
            "cursor": result.get("cursor"),
            "has_more": result.get("cursor") is not None,
        }

    async def get_new_messages(
        self,
        account_id: str,
        since: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get new/unread messages for an account.

        Args:
            account_id: Unipile account ID
            since: Only get messages after this time

        Returns:
            List of new messages
        """
        params = {"account_id": account_id}
        if since:
            params["after"] = since.isoformat()

        result = await self._request("GET", "/messages", params=params)

        return [
            {
                "message_id": m.get("id"),
                "chat_id": m.get("chat_id"),
                "sender_id": m.get("sender_id"),
                "sender_name": m.get("sender", {}).get("name"),
                "text": m.get("text"),
                "created_at": m.get("created_at"),
                "is_sender": m.get("is_sender", False),  # True if we sent this message
            }
            for m in result.get("items", [])
        ]

    # ==========================================
    # Profile Data
    # ==========================================

    async def get_profile(
        self,
        account_id: str,
        profile_id: str,
    ) -> dict[str, Any]:
        """
        Get LinkedIn profile data.

        Args:
            account_id: Unipile account ID (for authentication)
            profile_id: LinkedIn profile URN or URL

        Returns:
            Profile data
        """
        params = {"account_id": account_id}

        result = await self._request(
            "GET",
            f"/users/{profile_id}",
            params=params,
        )

        return {
            "found": True,
            "profile_id": result.get("id"),
            "linkedin_url": result.get("public_profile_url"),
            "first_name": result.get("first_name"),
            "last_name": result.get("last_name"),
            "headline": result.get("headline"),
            "company": result.get("current_company"),
            "location": result.get("location"),
            "connections": result.get("connections_count"),
            "profile_picture": result.get("profile_picture_url"),
        }

    async def get_user_posts(
        self,
        account_id: str,
        profile_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get recent posts from a LinkedIn profile.

        Useful for generating personalized icebreakers.

        Args:
            account_id: Unipile account ID
            profile_id: LinkedIn profile URN
            limit: Maximum posts to return

        Returns:
            List of recent posts
        """
        params = {
            "account_id": account_id,
            "limit": limit,
        }

        result = await self._request(
            "GET",
            f"/users/{profile_id}/posts",
            params=params,
        )

        return [
            {
                "post_id": p.get("id"),
                "text": p.get("text"),
                "created_at": p.get("created_at"),
                "likes_count": p.get("likes_count", 0),
                "comments_count": p.get("comments_count", 0),
                "shares_count": p.get("shares_count", 0),
            }
            for p in result.get("items", [])
        ]

    # ==========================================
    # Connection Status
    # ==========================================

    async def get_invitations(
        self,
        account_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get sent connection invitations.

        Args:
            account_id: Unipile account ID
            status: Filter by status (pending, accepted, declined)
            limit: Maximum invitations to return

        Returns:
            List of invitations with status
        """
        params = {
            "account_id": account_id,
            "limit": limit,
        }
        if status:
            params["status"] = status

        result = await self._request("GET", "/linkedin/invitations", params=params)

        return [
            {
                "invitation_id": inv.get("id"),
                "recipient_id": inv.get("recipient_id"),
                "recipient_name": inv.get("recipient", {}).get("name"),
                "status": inv.get("status"),
                "sent_at": inv.get("created_at"),
                "responded_at": inv.get("responded_at"),
            }
            for inv in result.get("items", [])
        ]

    # ==========================================
    # Webhook Parsing
    # ==========================================

    def parse_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Unipile webhook payload.

        Webhook events:
        - account.created: New account connected
        - account.reconnected: Account reconnected
        - account.credentials: Account needs re-authentication
        - account.deleted: Account disconnected
        - message.received: New message received
        - invitation.accepted: Connection accepted

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed event data
        """
        event_type = payload.get("event") or payload.get("type")
        data = payload.get("data", payload)

        if event_type in ("account.created", "CREATION_SUCCESS"):
            return {
                "event": "account_connected",
                "account_id": data.get("account_id") or data.get("id"),
                "name": data.get("name"),
                "provider": data.get("provider", "linkedin"),
                "status": "connected",
            }

        elif event_type in ("account.credentials", "CREDENTIALS"):
            return {
                "event": "account_needs_reauth",
                "account_id": data.get("account_id") or data.get("id"),
                "name": data.get("name"),
                "status": "credentials_required",
            }

        elif event_type in ("account.deleted", "DISCONNECTED"):
            return {
                "event": "account_disconnected",
                "account_id": data.get("account_id") or data.get("id"),
                "status": "disconnected",
            }

        elif event_type == "message.received":
            return {
                "event": "message_received",
                "account_id": data.get("account_id"),
                "chat_id": data.get("chat_id"),
                "message_id": data.get("message_id"),
                "sender_id": data.get("sender_id"),
                "text": data.get("text"),
            }

        elif event_type == "invitation.accepted":
            return {
                "event": "connection_accepted",
                "account_id": data.get("account_id"),
                "recipient_id": data.get("recipient_id"),
                "invitation_id": data.get("invitation_id"),
            }

        else:
            return {
                "event": "unknown",
                "raw": payload,
            }


# Singleton instance
_unipile_client: UnipileClient | None = None


def get_unipile_client() -> UnipileClient:
    """Get or create Unipile client instance."""
    global _unipile_client
    if _unipile_client is None:
        _unipile_client = UnipileClient()
    return _unipile_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Hosted auth link creation
# [x] Account management (get, delete)
# [x] Connection invitations
# [x] Direct messaging
# [x] Chat/conversation management
# [x] Profile data retrieval
# [x] User posts retrieval (for icebreakers)
# [x] Invitation status tracking
# [x] Webhook parsing
# [x] Error handling with custom exceptions
# [x] Rate limit handling
# [x] Retry logic with exponential backoff
# [x] All functions have type hints
# [x] All functions have docstrings
