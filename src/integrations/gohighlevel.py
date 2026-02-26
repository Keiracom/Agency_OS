"""
FILE: src/integrations/gohighlevel.py
PURPOSE: GoHighLevel CRM API integration
PHASE: 24E - CRM Push
TASK: CRM-010 (GoHighLevel Adapter)
DEPENDENCIES:
  - httpx
  - src/config/settings.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 17: Rate limiting (GHL has strict limits)

GoHighLevel API Reference:
- Base URL: https://services.leadconnectorhq.com
- OAuth Token: https://services.leadconnectorhq.com/oauth/token
- Requires Version header: 2021-07-28
- Access tokens expire in ~24 hours
- Refresh tokens valid for 1 year or until used
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.config.settings import settings

logger = logging.getLogger(__name__)

# GoHighLevel API Configuration
GHL_API_BASE = "https://services.leadconnectorhq.com"
GHL_OAUTH_URL = "https://marketplace.gohighlevel.com/oauth/chooselocation"
GHL_API_VERSION = "2021-07-28"

# Rate limiting: GHL has strict limits
# - 100 requests per 10 seconds per location
# - Burst protection
GHL_RATE_LIMIT_REQUESTS = 100
GHL_RATE_LIMIT_WINDOW = 10  # seconds


class GoHighLevelRateLimiter:
    """Rate limiter for GoHighLevel API calls."""

    def __init__(self, max_requests: int = GHL_RATE_LIMIT_REQUESTS, window: int = GHL_RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window = window
        self.requests: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait until a request slot is available."""
        async with self._lock:
            now = time.time()
            # Remove requests outside the window
            self.requests = [t for t in self.requests if now - t < self.window]

            if len(self.requests) >= self.max_requests:
                # Wait until oldest request expires
                wait_time = self.window - (now - self.requests[0])
                if wait_time > 0:
                    logger.debug(f"GHL rate limit: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            self.requests.append(time.time())


class GoHighLevelClient:
    """
    GoHighLevel API client with OAuth support.

    Handles:
    - OAuth 2.0 authorization code flow
    - Token refresh
    - Rate limiting
    - Contacts, Opportunities, Pipelines, Users APIs
    """

    def __init__(
        self,
        access_token: str | None = None,
        refresh_token: str | None = None,
        location_id: str | None = None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.location_id = location_id
        self.http = httpx.AsyncClient(timeout=30.0)
        self.rate_limiter = GoHighLevelRateLimiter()

    async def close(self) -> None:
        """Close HTTP client."""
        await self.http.aclose()

    def _headers(self) -> dict[str, str]:
        """Get standard headers for GHL API calls."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Version": GHL_API_VERSION,
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        json: dict | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Make rate-limited request to GHL API."""
        await self.rate_limiter.acquire()

        url = f"{GHL_API_BASE}{endpoint}"

        response = await self.http.request(
            method,
            url,
            params=params,
            json=json,
            headers=self._headers(),
            **kwargs,
        )

        if response.status_code == 429:
            # Rate limited - wait and retry
            retry_after = int(response.headers.get("Retry-After", 10))
            logger.warning(f"GHL rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            return await self._request(method, endpoint, params, json, **kwargs)

        response.raise_for_status()
        return response.json()

    # =========================================================================
    # OAUTH METHODS
    # =========================================================================

    @staticmethod
    def get_oauth_url(state: str) -> str:
        """
        Generate GoHighLevel OAuth authorization URL.

        Users are redirected here to authorize the app.
        After authorization, they're redirected back with an authorization code.
        """
        from urllib.parse import urlencode

        params = {
            "response_type": "code",
            "client_id": settings.ghl_client_id,
            "redirect_uri": settings.ghl_redirect_uri,
            "scope": settings.ghl_scopes.replace(",", " "),
            "state": state,
        }
        return f"{GHL_OAUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code(code: str) -> dict[str, Any]:
        """
        Exchange authorization code for access tokens.

        Returns:
            {
                "access_token": "...",
                "refresh_token": "...",
                "expires_in": 86399,
                "token_type": "Bearer",
                "scope": "...",
                "userType": "Location",
                "locationId": "...",
                "companyId": "...",
            }
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GHL_API_BASE}/oauth/token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "client_id": settings.ghl_client_id,
                    "client_secret": settings.ghl_client_secret,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.ghl_redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
        """
        Refresh expired access token using refresh token.

        Note: Using a refresh token invalidates it and returns a new one.
        The new refresh token must be saved.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GHL_API_BASE}/oauth/token",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "client_id": settings.ghl_client_id,
                    "client_secret": settings.ghl_client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            return response.json()

    # =========================================================================
    # CONTACTS API
    # =========================================================================

    async def search_contact_by_email(self, email: str) -> dict | None:
        """Search for a contact by email."""
        if not self.location_id:
            raise ValueError("location_id required for contact operations")

        try:
            result = await self._request(
                "GET",
                "/contacts/",
                params={
                    "locationId": self.location_id,
                    "query": email,
                    "limit": 1,
                },
            )
            contacts = result.get("contacts", [])

            # Filter by exact email match
            for contact in contacts:
                if contact.get("email", "").lower() == email.lower():
                    return contact
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def create_contact(
        self,
        email: str,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        website: str | None = None,
        tags: list[str] | None = None,
        custom_fields: dict | None = None,
    ) -> dict[str, Any]:
        """Create a new contact in GoHighLevel."""
        if not self.location_id:
            raise ValueError("location_id required for contact operations")

        body: dict[str, Any] = {
            "locationId": self.location_id,
            "email": email,
        }

        if first_name:
            body["firstName"] = first_name
        if last_name:
            body["lastName"] = last_name
        if phone:
            body["phone"] = phone
        if company_name:
            body["companyName"] = company_name
        if website:
            body["website"] = website
        if tags:
            body["tags"] = tags
        if custom_fields:
            body["customFields"] = custom_fields

        result = await self._request("POST", "/contacts/", json=body)
        return result.get("contact", result)

    async def update_contact(self, contact_id: str, **updates) -> dict[str, Any]:
        """Update an existing contact."""
        result = await self._request("PUT", f"/contacts/{contact_id}", json=updates)
        return result.get("contact", result)

    async def get_contacts(
        self,
        limit: int = 100,
        skip: int = 0,
        start_after_id: str | None = None,
    ) -> dict[str, Any]:
        """Get contacts with pagination."""
        if not self.location_id:
            raise ValueError("location_id required for contact operations")

        params: dict[str, Any] = {
            "locationId": self.location_id,
            "limit": limit,
        }
        if skip:
            params["skip"] = skip
        if start_after_id:
            params["startAfterId"] = start_after_id

        return await self._request("GET", "/contacts/", params=params)

    # =========================================================================
    # OPPORTUNITIES API (GHL's term for Deals)
    # =========================================================================

    async def get_pipelines(self) -> list[dict[str, Any]]:
        """Get all pipelines for the location."""
        if not self.location_id:
            raise ValueError("location_id required for pipeline operations")

        result = await self._request(
            "GET",
            "/opportunities/pipelines",
            params={"locationId": self.location_id},
        )
        return result.get("pipelines", [])

    async def create_opportunity(
        self,
        pipeline_id: str,
        stage_id: str,
        contact_id: str,
        name: str,
        monetary_value: float | None = None,
        assigned_to: str | None = None,
        status: str = "open",
        custom_fields: dict | None = None,
    ) -> dict[str, Any]:
        """Create an opportunity (deal) in GoHighLevel."""
        if not self.location_id:
            raise ValueError("location_id required for opportunity operations")

        body: dict[str, Any] = {
            "locationId": self.location_id,
            "pipelineId": pipeline_id,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "name": name,
            "status": status,
        }

        if monetary_value is not None:
            body["monetaryValue"] = monetary_value
        if assigned_to:
            body["assignedTo"] = assigned_to
        if custom_fields:
            body["customFields"] = custom_fields

        result = await self._request("POST", "/opportunities/", json=body)
        return result.get("opportunity", result)

    async def get_opportunities(
        self,
        pipeline_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
        start_after_id: str | None = None,
    ) -> dict[str, Any]:
        """Get opportunities with optional filtering."""
        if not self.location_id:
            raise ValueError("location_id required for opportunity operations")

        params: dict[str, Any] = {
            "locationId": self.location_id,
            "limit": limit,
        }
        if pipeline_id:
            params["pipelineId"] = pipeline_id
        if status:
            params["status"] = status
        if start_after_id:
            params["startAfterId"] = start_after_id

        return await self._request("GET", "/opportunities/search", params=params)

    async def update_opportunity(
        self,
        opportunity_id: str,
        status: str | None = None,
        stage_id: str | None = None,
        monetary_value: float | None = None,
        **updates,
    ) -> dict[str, Any]:
        """Update an existing opportunity."""
        body = {**updates}
        if status:
            body["status"] = status
        if stage_id:
            body["pipelineStageId"] = stage_id
        if monetary_value is not None:
            body["monetaryValue"] = monetary_value

        result = await self._request("PUT", f"/opportunities/{opportunity_id}", json=body)
        return result.get("opportunity", result)

    # =========================================================================
    # USERS API
    # =========================================================================

    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users for the location (for owner assignment)."""
        if not self.location_id:
            raise ValueError("location_id required for user operations")

        result = await self._request(
            "GET",
            "/users/",
            params={"locationId": self.location_id},
        )
        return result.get("users", [])

    # =========================================================================
    # CALENDARS API (for sync)
    # =========================================================================

    async def get_calendars(self) -> list[dict[str, Any]]:
        """Get all calendars for the location."""
        if not self.location_id:
            raise ValueError("location_id required for calendar operations")

        result = await self._request(
            "GET",
            "/calendars/",
            params={"locationId": self.location_id},
        )
        return result.get("calendars", [])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def calculate_token_expiry(expires_in: int) -> datetime:
    """Calculate token expiration datetime from expires_in seconds."""
    return datetime.utcnow() + timedelta(seconds=expires_in)


def is_token_expired(expires_at: datetime | None, buffer_minutes: int = 5) -> bool:
    """Check if token is expired or expiring soon."""
    if not expires_at:
        return True
    return datetime.utcnow() + timedelta(minutes=buffer_minutes) >= expires_at


# ============================================================================
# VERIFICATION CHECKLIST
# ============================================================================
# [x] Contract comment at top
# [x] Rate limiter class for GHL's strict limits
# [x] OAuth URL generation
# [x] Code exchange for tokens
# [x] Token refresh
# [x] Contacts API (search, create, update, list)
# [x] Opportunities API (pipelines, create, update, list)
# [x] Users API
# [x] Calendars API
# [x] All async methods
# [x] Proper error handling
# [x] Version header (2021-07-28)
