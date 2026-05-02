"""
Contract: src/integrations/telnyx_client.py
Purpose: Telnyx integration for Voice and SMS on a single provider
Layer: 2 - integrations
Imports: models only
Consumers: engines (sms.py, voice engines), orchestration

FILE: src/integrations/telnyx_client.py
PURPOSE: Telnyx REST API client — outbound SMS, call initiation, number management
PHASE: P3 (post-launch — Directive #167 Telnyx wiring)
TASK: INT-TELNYX-001
DEPENDENCIES:
  - httpx (async HTTP)
  - src/config/settings.py
  - src/exceptions.py
  - src/integrations/dncr.py (DNCR compliance point)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: No session instantiation inside integrations
  - LAW II: Australia-first — default country_code AU
  - DNCR integration point before SMS dispatch
  - Rate limit (429) handled with exponential backoff
  - No hardcoded credentials
"""

import asyncio
import contextlib
import logging
import os
from typing import Any

import httpx

from src.config.settings import settings
from src.exceptions import APIError, DNCRError, IntegrationError

logger = logging.getLogger(__name__)

TELNYX_BASE_URL = "https://api.telnyx.com/v2"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


class TelnyxClient:
    """
    Telnyx integration for Voice and SMS.

    Handles:
    - Outbound SMS with Australian DNCR compliance
    - Outbound call initiation (for voice AI pipeline)
    - Phone number management (list, search, purchase)
    - Status polling for messages and calls

    All methods are async and use httpx.AsyncClient.
    Auth: Bearer token from TELNYX_API_KEY env var (or settings).
    Base URL: https://api.telnyx.com/v2
    """

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.telnyx_api_key or os.getenv("TELNYX_API_KEY", "")
        if not self._api_key:
            raise IntegrationError(
                service="telnyx",
                message="TELNYX_API_KEY is required but not set",
            )
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Execute an authenticated Telnyx API request with retry on 429.

        Returns the parsed JSON response body.
        Raises APIError on non-2xx responses after exhausting retries.
        """
        url = f"{TELNYX_BASE_URL}{path}"
        attempt = 0
        last_exc: Exception | None = None

        while attempt < _MAX_RETRIES:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self._headers,
                        json=json,
                        params=params,
                    )

                logger.info(
                    "Telnyx API %s %s → %d (attempt %d)",
                    method,
                    path,
                    response.status_code,
                    attempt + 1,
                )

                if response.status_code == 429:
                    wait = _BACKOFF_BASE * (2**attempt)
                    logger.warning("Telnyx rate limited (429). Waiting %.1fs before retry.", wait)
                    await asyncio.sleep(wait)
                    attempt += 1
                    continue

                if response.status_code >= 400:
                    body: dict = {}
                    with contextlib.suppress(Exception):
                        body = response.json()
                    errors = body.get("errors", [{}])
                    detail = errors[0].get("detail", response.text) if errors else response.text
                    raise APIError(
                        service="telnyx",
                        status_code=response.status_code,
                        message=f"Telnyx API error {response.status_code}: {detail}",
                    )

                # 204 No Content
                if response.status_code == 204:
                    return {}

                return response.json()

            except APIError:
                raise
            except Exception as exc:
                last_exc = exc
                wait = _BACKOFF_BASE * (2**attempt)
                logger.warning("Telnyx request error: %s. Retrying in %.1fs.", exc, wait)
                await asyncio.sleep(wait)
                attempt += 1

        raise APIError(
            service="telnyx",
            status_code=0,
            message=f"Telnyx request failed after {_MAX_RETRIES} attempts: {last_exc}",
        )

    def _is_australian_number(self, phone_number: str) -> bool:
        """Return True if number is an Australian E.164 number."""
        return phone_number.startswith("+61")

    async def _dncr_check(self, phone_number: str) -> None:
        """
        Raise DNCRError if phone_number is on the Australian Do Not Call Register.

        Only called for +61 numbers. Uses cached result from dncr.py when available.
        """
        from src.integrations.dncr import get_dncr_client

        dncr_client = get_dncr_client()
        is_on_dncr = await dncr_client.check_number(phone_number)
        if is_on_dncr:
            raise DNCRError(
                phone=phone_number,
                message=f"Phone number {phone_number} is on the Do Not Call Register",
            )

    # ------------------------------------------------------------------
    # SMS
    # ------------------------------------------------------------------

    async def send_sms(
        self,
        to: str,
        from_number: str,
        body: str,
        messaging_profile_id: str | None = None,
        check_dncr: bool = True,
    ) -> dict[str, Any]:
        """
        Send SMS via Telnyx API.

        Args:
            to: Recipient E.164 number (AU: +61...)
            from_number: Sender E.164 number (must be on Telnyx account)
            body: SMS message text
            messaging_profile_id: Telnyx messaging profile (falls back to settings)
            check_dncr: Perform DNCR check for Australian numbers (default: True)

        Returns:
            dict with keys: message_id, status, provider, to, from_number

        Raises:
            DNCRError: If AU number is on DNCR list
            APIError: On Telnyx API failure
        """
        if check_dncr and self._is_australian_number(to):
            await self._dncr_check(to)

        profile_id = messaging_profile_id or settings.telnyx_messaging_profile_id or None

        payload: dict[str, Any] = {
            "from": from_number,
            "to": to,
            "text": body,
        }
        if profile_id:
            payload["messaging_profile_id"] = profile_id

        try:
            response = await self._request("POST", "/messages", json=payload)
            data = response.get("data", {})
            logger.info("Telnyx SMS sent to %s — id: %s", to, data.get("id"))
            return {
                "success": True,
                "message_id": data.get("id"),
                "status": data.get("to", [{}])[0].get("status")
                if data.get("to")
                else data.get("status"),
                "provider": "telnyx",
                "to": to,
                "from_number": from_number,
            }
        except DNCRError:
            raise
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error sending Telnyx SMS: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "provider": "telnyx",
                "to": to,
            }

    # ------------------------------------------------------------------
    # VOICE CALLS
    # ------------------------------------------------------------------

    async def make_call(
        self,
        to: str,
        from_number: str,
        connection_id: str | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        """
        Initiate an outbound call via Telnyx Call Control.

        Args:
            to: Destination E.164 number
            from_number: Caller ID (must be Telnyx number)
            connection_id: Telnyx voice connection ID (falls back to settings)
            webhook_url: Webhook for call events (falls back to base_url /voice/webhook)

        Returns:
            dict with keys: call_control_id, status, provider, to, from_number

        Raises:
            APIError: On Telnyx API failure
        """
        conn_id = connection_id or settings.telnyx_connection_id
        if not conn_id:
            raise IntegrationError(
                service="telnyx",
                message="telnyx_connection_id is required for outbound calls",
            )

        hook_url = webhook_url or f"{settings.base_url}/voice/webhook"

        payload: dict[str, Any] = {
            "connection_id": conn_id,
            "to": to,
            "from": from_number,
            "webhook_url": hook_url,
            "webhook_url_method": "POST",
        }

        try:
            response = await self._request("POST", "/calls", json=payload)
            data = response.get("data", {})
            call_control_id = data.get("call_control_id", "")
            logger.info("Telnyx call initiated to %s — call_control_id: %s", to, call_control_id)
            return {
                "success": True,
                "call_control_id": call_control_id,
                "status": data.get("state", "ringing"),
                "provider": "telnyx",
                "to": to,
                "from_number": from_number,
            }
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Unexpected error initiating Telnyx call: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "provider": "telnyx",
                "to": to,
            }

    # ------------------------------------------------------------------
    # PHONE NUMBER MANAGEMENT
    # ------------------------------------------------------------------

    async def list_phone_numbers(self) -> list[dict[str, Any]]:
        """
        List all phone numbers on the Telnyx account.

        Returns:
            List of number dicts with phone_number, status, features, etc.
        """
        try:
            response = await self._request("GET", "/phone_numbers")
            numbers = response.get("data", [])
            logger.info("Telnyx: retrieved %d phone numbers", len(numbers))
            return numbers
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Error listing Telnyx phone numbers: %s", exc)
            return []

    async def search_available_numbers(
        self,
        country_code: str = "AU",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for available phone numbers to purchase.

        Args:
            country_code: ISO country code (default: AU — Australia-first)
            limit: Max results to return (default: 10)

        Returns:
            List of available number dicts with phone_number, cost, features.
        """
        params: dict[str, Any] = {
            "filter[country_code]": country_code,
            "filter[features][]": ["sms", "voice"],
            "page[size]": limit,
        }
        try:
            response = await self._request("GET", "/available_phone_numbers", params=params)
            numbers = response.get("data", [])
            logger.info("Telnyx: found %d available numbers in %s", len(numbers), country_code)
            return numbers
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Error searching Telnyx available numbers: %s", exc)
            return []

    async def buy_number(
        self,
        phone_number: str,
        messaging_profile_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Purchase a phone number.

        Args:
            phone_number: E.164 number to purchase (e.g. +61299999999)
            messaging_profile_id: Assign to messaging profile immediately

        Returns:
            dict with order_id, phone_number, status
        """
        order_phone: dict[str, Any] = {"phone_number": phone_number}
        if messaging_profile_id:
            order_phone["messaging_profile_id"] = messaging_profile_id

        payload: dict[str, Any] = {"phone_numbers": [order_phone]}

        try:
            response = await self._request("POST", "/number_orders", json=payload)
            data = response.get("data", {})
            logger.info(
                "Telnyx number order placed for %s — order_id: %s", phone_number, data.get("id")
            )
            return {
                "success": True,
                "order_id": data.get("id"),
                "phone_number": phone_number,
                "status": data.get("status", "pending"),
            }
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Error purchasing Telnyx number %s: %s", phone_number, exc)
            return {
                "success": False,
                "error": str(exc),
                "phone_number": phone_number,
            }

    # ------------------------------------------------------------------
    # STATUS POLLING
    # ------------------------------------------------------------------

    async def get_call_status(self, call_control_id: str) -> dict[str, Any]:
        """
        Get status of an active or completed call.

        Args:
            call_control_id: Call Control ID from make_call()

        Returns:
            dict with call_control_id, state, duration, from, to
        """
        try:
            response = await self._request("GET", f"/calls/{call_control_id}")
            data = response.get("data", {})
            return {
                "call_control_id": call_control_id,
                "state": data.get("state"),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "duration": data.get("duration_secs"),
                "to": data.get("to"),
                "from_number": data.get("from"),
            }
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Error fetching Telnyx call status %s: %s", call_control_id, exc)
            return {"call_control_id": call_control_id, "error": str(exc)}

    async def get_message_status(self, message_id: str) -> dict[str, Any]:
        """
        Get delivery status of a sent SMS.

        Args:
            message_id: Message ID from send_sms()

        Returns:
            dict with message_id, status, to, from_number, errors
        """
        try:
            response = await self._request("GET", f"/messages/{message_id}")
            data = response.get("data", {})
            to_list = data.get("to", [{}])
            to_status = to_list[0].get("status") if to_list else None
            return {
                "message_id": message_id,
                "status": to_status or data.get("direction"),
                "to": data.get("to"),
                "from_number": data.get("from", {}).get("phone_number"),
                "errors": data.get("errors", []),
                "carrier_name": to_list[0].get("carrier", {}).get("name") if to_list else None,
            }
        except APIError:
            raise
        except Exception as exc:
            logger.exception("Error fetching Telnyx message status %s: %s", message_id, exc)
            return {"message_id": message_id, "error": str(exc)}


# ------------------------------------------------------------------
# SINGLETON
# ------------------------------------------------------------------

_telnyx_client: TelnyxClient | None = None


def get_telnyx_client() -> TelnyxClient:
    """Get or create the shared TelnyxClient instance."""
    global _telnyx_client
    if _telnyx_client is None:
        _telnyx_client = TelnyxClient()
    return _telnyx_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials — reads from settings / env
# [x] httpx.AsyncClient for all API calls
# [x] Base URL: https://api.telnyx.com/v2
# [x] Bearer token auth from TELNYX_API_KEY
# [x] Rate limit (429) with exponential backoff
# [x] Errors returned as dicts or raised as APIError/DNCRError
# [x] All API calls logged at INFO level
# [x] AU default country code (Australia-first LAW II)
# [x] DNCR check integration point before SMS dispatch
# [x] send_sms — message_id, status, provider
# [x] make_call — call_control_id, status, provider
# [x] list_phone_numbers — full account list
# [x] search_available_numbers — AU-first, configurable limit
# [x] buy_number — number_orders endpoint
# [x] get_call_status — call_control_id polling
# [x] get_message_status — message delivery polling
# [x] Singleton get_telnyx_client()
# [x] All methods have type hints and docstrings
