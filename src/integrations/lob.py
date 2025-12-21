"""
FILE: src/integrations/lob.py
PURPOSE: Lob integration for direct mail
PHASE: 3 (Integrations)
TASK: INT-011
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ValidationError


class LobClient:
    """
    Lob client for direct mail.

    Handles sending physical letters and postcards.
    """

    BASE_URL = "https://api.lob.com/v1"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.lob_api_key
        if not self.api_key:
            raise IntegrationError(
                service="lob",
                message="Lob API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                auth=(self.api_key, ""),
                headers={"Content-Type": "application/json"},
                timeout=60.0,
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
                service="lob",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="lob",
                message=f"Lob request failed: {str(e)}",
            )

    async def verify_address(
        self,
        address_line1: str,
        city: str,
        state: str,
        zip_code: str,
        country: str = "AU",
        address_line2: str | None = None,
    ) -> dict[str, Any]:
        """
        Verify an address.

        Args:
            address_line1: Primary address line
            city: City name
            state: State/province
            zip_code: Postal code
            country: Country code (default AU for Australia)
            address_line2: Secondary address line

        Returns:
            Verification result
        """
        data = {
            "primary_line": address_line1,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
        }
        if address_line2:
            data["secondary_line"] = address_line2

        result = await self._request(
            "POST",
            "/us_verifications" if country == "US" else "/intl_verifications",
            data,
        )

        return {
            "deliverability": result.get("deliverability"),
            "valid": result.get("deliverability") in ["deliverable", "deliverable_missing_unit"],
            "primary_line": result.get("primary_line"),
            "secondary_line": result.get("secondary_line"),
            "city": result.get("city"),
            "state": result.get("state"),
            "zip_code": result.get("zip_code"),
            "country": result.get("country"),
        }

    async def send_letter(
        self,
        to_address: dict[str, str],
        from_address: dict[str, str],
        template_id: str,
        merge_variables: dict[str, Any],
        color: bool = True,
    ) -> dict[str, Any]:
        """
        Send a letter.

        Args:
            to_address: Recipient address dict
            from_address: Sender address dict
            template_id: Lob template ID
            merge_variables: Template variables
            color: Whether to print in color

        Returns:
            Letter send result
        """
        data = {
            "to": {
                "name": to_address.get("name"),
                "address_line1": to_address.get("address_line1"),
                "address_line2": to_address.get("address_line2"),
                "address_city": to_address.get("city"),
                "address_state": to_address.get("state"),
                "address_zip": to_address.get("zip_code"),
                "address_country": to_address.get("country", "AU"),
            },
            "from": {
                "name": from_address.get("name"),
                "address_line1": from_address.get("address_line1"),
                "address_line2": from_address.get("address_line2"),
                "address_city": from_address.get("city"),
                "address_state": from_address.get("state"),
                "address_zip": from_address.get("zip_code"),
                "address_country": from_address.get("country", "AU"),
            },
            "file": template_id,
            "merge_variables": merge_variables,
            "color": color,
        }

        result = await self._request("POST", "/letters", data)

        return {
            "success": True,
            "letter_id": result.get("id"),
            "url": result.get("url"),
            "expected_delivery_date": result.get("expected_delivery_date"),
            "tracking_number": result.get("tracking_number"),
            "carrier": result.get("carrier"),
            "provider": "lob",
        }

    async def send_postcard(
        self,
        to_address: dict[str, str],
        from_address: dict[str, str],
        front_template_id: str,
        back_template_id: str,
        merge_variables: dict[str, Any],
        size: str = "4x6",
    ) -> dict[str, Any]:
        """
        Send a postcard.

        Args:
            to_address: Recipient address dict
            from_address: Sender address dict
            front_template_id: Front template ID
            back_template_id: Back template ID
            merge_variables: Template variables
            size: Postcard size (4x6 or 6x9)

        Returns:
            Postcard send result
        """
        data = {
            "to": {
                "name": to_address.get("name"),
                "address_line1": to_address.get("address_line1"),
                "address_line2": to_address.get("address_line2"),
                "address_city": to_address.get("city"),
                "address_state": to_address.get("state"),
                "address_zip": to_address.get("zip_code"),
                "address_country": to_address.get("country", "AU"),
            },
            "from": {
                "name": from_address.get("name"),
                "address_line1": from_address.get("address_line1"),
                "address_line2": from_address.get("address_line2"),
                "address_city": from_address.get("city"),
                "address_state": from_address.get("state"),
                "address_zip": from_address.get("zip_code"),
                "address_country": from_address.get("country", "AU"),
            },
            "front": front_template_id,
            "back": back_template_id,
            "merge_variables": merge_variables,
            "size": size,
        }

        result = await self._request("POST", "/postcards", data)

        return {
            "success": True,
            "postcard_id": result.get("id"),
            "url": result.get("url"),
            "expected_delivery_date": result.get("expected_delivery_date"),
            "provider": "lob",
        }

    async def get_letter(self, letter_id: str) -> dict[str, Any]:
        """
        Get letter details.

        Args:
            letter_id: Lob letter ID

        Returns:
            Letter details
        """
        result = await self._request("GET", f"/letters/{letter_id}")

        return {
            "id": result.get("id"),
            "to": result.get("to"),
            "from": result.get("from_"),
            "url": result.get("url"),
            "expected_delivery_date": result.get("expected_delivery_date"),
            "tracking_number": result.get("tracking_number"),
            "tracking_events": result.get("tracking_events", []),
        }

    def parse_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Lob tracking webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed tracking event
        """
        event_type = payload.get("event_type", {})
        body = payload.get("body", {})

        return {
            "event_id": event_type.get("id"),
            "resource_type": body.get("object"),  # letter, postcard
            "resource_id": body.get("id"),
            "tracking_number": body.get("tracking_number"),
            "tracking_events": body.get("tracking_events", []),
            "carrier": body.get("carrier"),
            "expected_delivery_date": body.get("expected_delivery_date"),
        }


# Singleton instance
_lob_client: LobClient | None = None


def get_lob_client() -> LobClient:
    """Get or create Lob client instance."""
    global _lob_client
    if _lob_client is None:
        _lob_client = LobClient()
    return _lob_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Address verification
# [x] Letter sending with templates
# [x] Postcard sending
# [x] Letter status retrieval
# [x] Webhook parsing for tracking
# [x] Australian address support
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
