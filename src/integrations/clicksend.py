"""
FILE: src/integrations/clicksend.py
PURPOSE: ClickSend integration for direct mail (Australian)
PHASE: 3 (Integrations)
TASK: INT-011
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No hardcoded credentials

ClickSend is an Australian company (Perth) providing:
- Direct mail (letters, postcards)
- SMS (also available)
- No minimum volumes
- REST API with Basic Auth
"""

import base64
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError


class ClickSendClient:
    """
    ClickSend client for direct mail.

    Australian-native provider for letters and postcards.
    https://www.clicksend.com/au/post/
    """

    BASE_URL = "https://rest.clicksend.com/v3"

    def __init__(self, username: str | None = None, api_key: str | None = None):
        self.username = username or settings.clicksend_username
        self.api_key = api_key or settings.clicksend_api_key
        if not self.username or not self.api_key:
            raise IntegrationError(
                service="clicksend",
                message="ClickSend username and API key are required",
            )
        # Basic auth: base64(username:api_key)
        credentials = f"{self.username}:{self.api_key}"
        self.auth_header = base64.b64encode(credentials.encode()).decode()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {self.auth_header}",
                },
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
                service="clicksend",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="clicksend",
                message=f"ClickSend request failed: {str(e)}",
            )

    async def get_account_details(self) -> dict[str, Any]:
        """
        Get account details and balance.

        Returns:
            Account information including balance
        """
        result = await self._request("GET", "/account")
        return result.get("data", {})

    async def send_letter(
        self,
        to_address: dict[str, str],
        from_address: dict[str, str],
        template_id: str | None = None,
        file_url: str | None = None,
        merge_variables: dict[str, Any] | None = None,
        colour: bool = True,
        duplex: bool = False,
        priority_post: bool = False,
    ) -> dict[str, Any]:
        """
        Send a letter via ClickSend.

        Args:
            to_address: Recipient address dict with name, address_line1, city, state, postal_code, country
            from_address: Sender address dict (for return address)
            template_id: ClickSend template ID (optional)
            file_url: URL to PDF file to print (alternative to template)
            merge_variables: Template variables for mail merge
            colour: Whether to print in colour (default True)
            duplex: Double-sided printing (default False)
            priority_post: Use priority post (default False)

        Returns:
            Letter send result with tracking info
        """
        # Build recipient
        recipient = {
            "address_name": to_address.get("name", ""),
            "address_line_1": to_address.get("address_line1", ""),
            "address_line_2": to_address.get("address_line2", ""),
            "address_city": to_address.get("city", ""),
            "address_state": to_address.get("state", ""),
            "address_postal_code": to_address.get("postal_code", to_address.get("zip_code", "")),
            "address_country": to_address.get("country", "AU"),
        }

        # Build return address
        return_addr = {
            "address_name": from_address.get("name", ""),
            "address_line_1": from_address.get("address_line1", ""),
            "address_line_2": from_address.get("address_line2", ""),
            "address_city": from_address.get("city", ""),
            "address_state": from_address.get("state", ""),
            "address_postal_code": from_address.get("postal_code", from_address.get("zip_code", "")),
            "address_country": from_address.get("country", "AU"),
        }

        data = {
            "recipients": [recipient],
            "return_address": return_addr,
            "colour": 1 if colour else 0,
            "duplex": 1 if duplex else 0,
            "priority_post": 1 if priority_post else 0,
        }

        # Either template or file URL
        if template_id:
            data["template_id"] = template_id
        elif file_url:
            data["file_url"] = file_url
        else:
            raise IntegrationError(
                service="clicksend",
                message="Either template_id or file_url is required",
            )

        result = await self._request("POST", "/post/letters/send", data)

        # Extract response
        response_data = result.get("data", {})
        messages = response_data.get("messages", [{}])
        first_message = messages[0] if messages else {}

        return {
            "success": result.get("http_code") == 200,
            "letter_id": first_message.get("message_id"),
            "status": first_message.get("status"),
            "price": first_message.get("message_price"),
            "schedule": first_message.get("schedule"),
            "provider": "clicksend",
        }

    async def send_postcard(
        self,
        to_address: dict[str, str],
        from_address: dict[str, str],
        front_file_url: str,
        back_file_url: str,
        merge_variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Send a postcard via ClickSend.

        Args:
            to_address: Recipient address dict
            from_address: Sender address dict
            front_file_url: URL to front image/PDF
            back_file_url: URL to back image/PDF
            merge_variables: Template variables (if using templates)

        Returns:
            Postcard send result
        """
        recipient = {
            "address_name": to_address.get("name", ""),
            "address_line_1": to_address.get("address_line1", ""),
            "address_line_2": to_address.get("address_line2", ""),
            "address_city": to_address.get("city", ""),
            "address_state": to_address.get("state", ""),
            "address_postal_code": to_address.get("postal_code", to_address.get("zip_code", "")),
            "address_country": to_address.get("country", "AU"),
        }

        return_addr = {
            "address_name": from_address.get("name", ""),
            "address_line_1": from_address.get("address_line1", ""),
            "address_line_2": from_address.get("address_line2", ""),
            "address_city": from_address.get("city", ""),
            "address_state": from_address.get("state", ""),
            "address_postal_code": from_address.get("postal_code", from_address.get("zip_code", "")),
            "address_country": from_address.get("country", "AU"),
        }

        data = {
            "recipients": [recipient],
            "return_address": return_addr,
            "file_urls": [front_file_url, back_file_url],
        }

        result = await self._request("POST", "/post/postcards/send", data)

        response_data = result.get("data", {})
        messages = response_data.get("messages", [{}])
        first_message = messages[0] if messages else {}

        return {
            "success": result.get("http_code") == 200,
            "postcard_id": first_message.get("message_id"),
            "status": first_message.get("status"),
            "price": first_message.get("message_price"),
            "provider": "clicksend",
        }

    async def get_letter_history(
        self,
        page: int = 1,
        limit: int = 15,
    ) -> dict[str, Any]:
        """
        Get letter sending history.

        Args:
            page: Page number
            limit: Results per page

        Returns:
            Letter history with pagination
        """
        result = await self._request(
            "GET",
            f"/post/letters/history?page={page}&limit={limit}",
        )
        return result.get("data", {})

    async def get_postcard_history(
        self,
        page: int = 1,
        limit: int = 15,
    ) -> dict[str, Any]:
        """
        Get postcard sending history.

        Args:
            page: Page number
            limit: Results per page

        Returns:
            Postcard history with pagination
        """
        result = await self._request(
            "GET",
            f"/post/postcards/history?page={page}&limit={limit}",
        )
        return result.get("data", {})

    async def calculate_price(
        self,
        recipients_count: int = 1,
        pages: int = 1,
        colour: bool = True,
        duplex: bool = False,
        priority_post: bool = False,
    ) -> dict[str, Any]:
        """
        Calculate letter price before sending.

        Args:
            recipients_count: Number of recipients
            pages: Number of pages
            colour: Colour printing
            duplex: Double-sided
            priority_post: Priority post

        Returns:
            Price calculation
        """
        data = {
            "recipients_count": recipients_count,
            "pages": pages,
            "colour": 1 if colour else 0,
            "duplex": 1 if duplex else 0,
            "priority_post": 1 if priority_post else 0,
        }

        result = await self._request("POST", "/post/letters/price", data)
        return result.get("data", {})

    def parse_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse ClickSend delivery webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed delivery event
        """
        return {
            "event_type": payload.get("event"),
            "message_id": payload.get("message_id"),
            "status": payload.get("status"),
            "timestamp": payload.get("timestamp"),
            "custom_string": payload.get("custom_string"),
        }


# Singleton instance
_clicksend_client: ClickSendClient | None = None


def get_clicksend_client() -> ClickSendClient:
    """Get or create ClickSend client instance."""
    global _clicksend_client
    if _clicksend_client is None:
        _clicksend_client = ClickSendClient()
    return _clicksend_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Letter sending with templates or file URL
# [x] Postcard sending
# [x] History retrieval
# [x] Price calculation
# [x] Webhook parsing for delivery tracking
# [x] Australian address support (native)
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
