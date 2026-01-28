"""
FILE: src/integrations/twilio.py
PURPOSE: Twilio integration for SMS with DNCR check
PHASE: 3 (Integrations), updated E2E Testing
TASK: INT-008
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
  - src/integrations/dncr.py (for DNCR compliance)
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Australia DNCR compliance via ACMA API
"""

import asyncio
from typing import Any

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioBaseClient

from src.config.settings import settings
from src.exceptions import APIError, DNCRError, IntegrationError


class TwilioClient:
    """
    Twilio client for SMS messaging.

    Handles outbound SMS with Australian DNCR compliance.
    Uses DNCRClient integration for checking numbers against
    the Australian Do Not Call Register.
    """

    def __init__(
        self,
        account_sid: str | None = None,
        auth_token: str | None = None,
        phone_number: str | None = None,
    ):
        self.account_sid = account_sid or settings.twilio_account_sid
        self.auth_token = auth_token or settings.twilio_auth_token
        self.phone_number = phone_number or settings.twilio_phone_number

        if not all([self.account_sid, self.auth_token]):
            raise IntegrationError(
                service="twilio",
                message="Twilio credentials are required",
            )

        self._client = TwilioBaseClient(self.account_sid, self.auth_token)

    async def send_sms(
        self,
        to_number: str,
        message: str,
        from_number: str | None = None,
        check_dncr: bool = True,
    ) -> dict[str, Any]:
        """
        Send an SMS message.

        Args:
            to_number: Recipient phone number (E.164 format)
            message: SMS message content
            from_number: Sender phone number (defaults to configured)
            check_dncr: Whether to check DNCR first

        Returns:
            Send result with message SID

        Raises:
            DNCRError: If number is on DNCR list
        """
        from_number = from_number or self.phone_number

        # Check DNCR for Australian numbers
        if check_dncr and self._is_australian_number(to_number):
            is_on_dncr = await self.check_dncr(to_number)
            if is_on_dncr:
                raise DNCRError(
                    phone=to_number,
                    message=f"Phone number {to_number} is on the Do Not Call Register",
                )

        try:
            # Wrap sync Twilio call in thread to avoid blocking event loop
            message_obj = await asyncio.to_thread(
                self._client.messages.create,
                body=message,
                from_=from_number,
                to=to_number,
            )

            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "provider": "twilio",
            }

        except TwilioRestException as e:
            raise APIError(
                service="twilio",
                status_code=e.status,
                message=f"SMS send failed: {e.msg}",
            )

    async def check_dncr(self, phone_number: str) -> bool:
        """
        Check if phone number is on Australian DNCR.

        Uses the DNCRClient integration which:
        - Connects to ACMA DNCR API
        - Caches results in Redis (default 24h)
        - Fails open if API unavailable

        Args:
            phone_number: Phone number to check

        Returns:
            True if on DNCR list, False otherwise
        """
        from src.integrations.dncr import get_dncr_client

        dncr_client = get_dncr_client()
        return await dncr_client.check_number(phone_number)

    def _is_australian_number(self, phone_number: str) -> bool:
        """Check if phone number is Australian."""
        return phone_number.startswith("+61")

    def parse_inbound_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Twilio inbound SMS webhook.

        Args:
            payload: Raw webhook payload (form data)

        Returns:
            Parsed inbound SMS data
        """
        return {
            "message_sid": payload.get("MessageSid"),
            "from_number": payload.get("From"),
            "to_number": payload.get("To"),
            "body": payload.get("Body"),
            "num_media": int(payload.get("NumMedia", 0)),
            "from_city": payload.get("FromCity"),
            "from_state": payload.get("FromState"),
            "from_country": payload.get("FromCountry"),
            "from_zip": payload.get("FromZip"),
        }

    def parse_status_webhook(self, payload: dict) -> dict[str, Any]:
        """
        Parse Twilio message status webhook.

        Args:
            payload: Raw webhook payload

        Returns:
            Parsed status data
        """
        return {
            "message_sid": payload.get("MessageSid"),
            "message_status": payload.get("MessageStatus"),
            "to_number": payload.get("To"),
            "error_code": payload.get("ErrorCode"),
            "error_message": payload.get("ErrorMessage"),
        }

    async def get_message(self, message_sid: str) -> dict[str, Any]:
        """
        Get message details by SID.

        Args:
            message_sid: Twilio message SID

        Returns:
            Message details
        """
        try:
            # Wrap sync Twilio call in thread to avoid blocking event loop
            message = await asyncio.to_thread(
                self._client.messages(message_sid).fetch
            )
            return {
                "sid": message.sid,
                "from": message.from_,
                "to": message.to,
                "body": message.body,
                "status": message.status,
                "date_sent": str(message.date_sent) if message.date_sent else None,
                "direction": message.direction,
            }
        except TwilioRestException as e:
            raise APIError(
                service="twilio",
                status_code=e.status,
                message=f"Failed to get message: {e.msg}",
            )

    async def lookup_phone(self, phone_number: str) -> dict[str, Any]:
        """
        Look up phone number details.

        Args:
            phone_number: Phone number to look up

        Returns:
            Phone number details
        """
        try:
            # Wrap sync Twilio call in thread to avoid blocking event loop
            def _do_lookup():
                return self._client.lookups.v1.phone_numbers(phone_number).fetch(
                    type=["carrier", "caller-name"]
                )

            lookup = await asyncio.to_thread(_do_lookup)
            return {
                "phone_number": lookup.phone_number,
                "national_format": lookup.national_format,
                "country_code": lookup.country_code,
                "carrier": {
                    "name": lookup.carrier.get("name") if lookup.carrier else None,
                    "type": lookup.carrier.get("type") if lookup.carrier else None,
                } if lookup.carrier else None,
                "caller_name": lookup.caller_name.get("caller_name") if lookup.caller_name else None,
            }
        except TwilioRestException as e:
            raise APIError(
                service="twilio",
                status_code=e.status,
                message=f"Phone lookup failed: {e.msg}",
            )


# Singleton instance
_twilio_client: TwilioClient | None = None


def get_twilio_client() -> TwilioClient:
    """Get or create Twilio client instance."""
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = TwilioClient()
    return _twilio_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] SMS sending
# [x] DNCR check for Australian numbers
# [x] Inbound SMS webhook parsing
# [x] Status webhook parsing
# [x] Message lookup
# [x] Phone number lookup
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Sync Twilio SDK wrapped with asyncio.to_thread() (FIX-E2E-005)
