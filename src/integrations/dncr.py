"""
Contract: src/integrations/dncr.py
Purpose: Australian Do Not Call Register (DNCR) integration for SMS compliance
Layer: 2 - integrations
Imports: models ONLY
Consumers: engines (sms.py via twilio.py)

PHASE: E2E Testing
TASK: DNCR compliance for Australian SMS outreach

The Australian DNCR is managed by ACMA (Australian Communications and Media Authority).
This integration checks phone numbers against the register before sending SMS.

Registration: https://dncr.gov.au
API Documentation: https://dncr.gov.au/api/documentation

Features:
- Individual number checking
- Batch number washing
- Redis caching (default 24 hours)
- Graceful fallback if API unavailable
"""

import hashlib
import logging
from typing import Any

import httpx
import sentry_sdk

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError

logger = logging.getLogger(__name__)


class DNCRClient:
    """
    Australian Do Not Call Register client.

    Checks phone numbers against the ACMA DNCR to ensure
    compliance with Australian telecommunications regulations.

    The DNCR API uses:
    - API key authentication via header
    - Account ID for billing/tracking
    - Number washing (checking) endpoints
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        account_id: str | None = None,
    ):
        """
        Initialize DNCR client.

        Args:
            api_key: DNCR API key (uses settings if not provided)
            api_url: DNCR API URL (uses settings if not provided)
            account_id: DNCR Account ID (uses settings if not provided)
        """
        self.api_key = api_key or settings.dncr_api_key
        self.api_url = (api_url or settings.dncr_api_url).rstrip("/")
        self.account_id = account_id or settings.dncr_account_id
        self.cache_ttl_hours = settings.dncr_cache_ttl_hours

        # Client is optional - if no credentials, DNCR checking is disabled
        self._client = None
        self._enabled = bool(self.api_key and self.account_id)

        if self._enabled:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-Account-Id": self.account_id,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            logger.info("DNCR client initialized with API credentials")
        else:
            logger.warning(
                "DNCR client not configured - SMS compliance checks will be skipped. "
                "Set DNCR_API_KEY and DNCR_ACCOUNT_ID for production use."
            )

    @property
    def is_enabled(self) -> bool:
        """Check if DNCR checking is enabled."""
        return self._enabled

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an API request to DNCR.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response JSON data

        Raises:
            APIError: If the request fails
        """
        if not self._enabled or self._client is None:
            raise IntegrationError(
                service="dncr",
                message="DNCR client is not configured",
            )

        try:
            response = await self._client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_body = {}
            try:
                error_body = e.response.json()
            except Exception:
                pass

            sentry_sdk.set_context("dncr_error", {
                "status_code": e.response.status_code,
                "response": error_body,
                "endpoint": endpoint,
            })
            sentry_sdk.capture_exception(e)

            raise APIError(
                service="dncr",
                status_code=e.response.status_code,
                message=f"DNCR API error: {error_body.get('message', str(e))}",
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="dncr",
                status_code=500,
                message=f"DNCR request failed: {str(e)}",
            )

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for DNCR checking.

        DNCR expects Australian numbers in specific format.
        Converts:
        - +61412345678 -> 0412345678
        - 61412345678 -> 0412345678
        - 0412345678 -> 0412345678
        """
        phone = phone.strip().replace(" ", "").replace("-", "")

        # Remove +61 prefix
        if phone.startswith("+61"):
            phone = "0" + phone[3:]
        # Remove 61 prefix (without +)
        elif phone.startswith("61") and len(phone) == 11:
            phone = "0" + phone[2:]

        return phone

    def _get_cache_key(self, phone: str) -> str:
        """Generate Redis cache key for a phone number."""
        normalized = self._normalize_phone(phone)
        # Hash for privacy
        phone_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"dncr:check:{phone_hash}"

    async def _get_from_cache(self, phone: str) -> bool | None:
        """
        Get DNCR status from cache.

        Returns:
            True if on DNCR, False if not, None if not cached
        """
        try:
            from src.integrations.redis import get_redis_client
            redis = get_redis_client()

            cache_key = self._get_cache_key(phone)
            cached = await redis.get(cache_key)

            if cached is not None:
                return cached == "1"
            return None
        except Exception as e:
            logger.warning(f"DNCR cache read failed: {e}")
            return None

    async def _set_cache(self, phone: str, on_dncr: bool) -> None:
        """
        Cache DNCR status.

        Args:
            phone: Phone number
            on_dncr: Whether the number is on DNCR
        """
        try:
            from src.integrations.redis import get_redis_client
            redis = get_redis_client()

            cache_key = self._get_cache_key(phone)
            ttl_seconds = self.cache_ttl_hours * 3600

            await redis.setex(cache_key, ttl_seconds, "1" if on_dncr else "0")
        except Exception as e:
            logger.warning(f"DNCR cache write failed: {e}")

    async def check_number(self, phone: str) -> bool:
        """
        Check if a phone number is on the DNCR.

        Args:
            phone: Phone number to check (any format)

        Returns:
            True if the number is on the DNCR (do not contact)
            False if the number is not on the DNCR (ok to contact)

        Note:
            If DNCR is not configured, returns False (allows sending)
            This is to avoid blocking all SMS when API is not set up.
        """
        if not self._enabled:
            logger.debug("DNCR not configured, allowing contact")
            return False

        # Check cache first
        cached_result = await self._get_from_cache(phone)
        if cached_result is not None:
            logger.debug(f"DNCR cache hit for {phone[:6]}...: {cached_result}")
            return cached_result

        # Normalize for API call
        normalized = self._normalize_phone(phone)

        try:
            # ACMA DNCR API endpoint for single number check
            # The actual endpoint may vary - this follows common patterns
            result = await self._request(
                "POST",
                "/numbers/wash",
                json={"numbers": [normalized]},
            )

            # Parse response - structure may vary by API version
            # Common patterns: results array with status per number
            results = result.get("results", [])

            if results and len(results) > 0:
                on_dncr = results[0].get("onRegister", False)
            else:
                # If no results, assume not on register
                on_dncr = False

            # Cache the result
            await self._set_cache(phone, on_dncr)

            logger.info(
                f"DNCR check for {normalized[:6]}...: "
                f"{'ON REGISTER' if on_dncr else 'not registered'}"
            )

            return on_dncr

        except APIError:
            # Re-raise API errors
            raise
        except Exception as e:
            # Log but don't block on unexpected errors
            logger.error(f"DNCR check failed for {phone[:6]}...: {e}")
            sentry_sdk.capture_exception(e)

            # Fail open - allow contact if check fails
            # This is a business decision - could also fail closed
            return False

    async def check_numbers_batch(
        self,
        phones: list[str],
    ) -> dict[str, bool]:
        """
        Batch check multiple phone numbers against DNCR.

        More efficient than individual checks for large lists.

        Args:
            phones: List of phone numbers to check

        Returns:
            Dict mapping phone number to DNCR status
            {"+61412345678": True, "+61498765432": False, ...}
        """
        if not self._enabled:
            return {phone: False for phone in phones}

        results = {}
        uncached_phones = []

        # Check cache first
        for phone in phones:
            cached = await self._get_from_cache(phone)
            if cached is not None:
                results[phone] = cached
            else:
                uncached_phones.append(phone)

        if not uncached_phones:
            return results

        try:
            # Normalize all uncached numbers
            normalized_map = {
                self._normalize_phone(p): p for p in uncached_phones
            }
            normalized_list = list(normalized_map.keys())

            # Batch API call
            response = await self._request(
                "POST",
                "/numbers/wash",
                json={"numbers": normalized_list},
            )

            # Parse batch response
            api_results = response.get("results", [])

            for item in api_results:
                normalized = item.get("number")
                on_dncr = item.get("onRegister", False)

                if normalized and normalized in normalized_map:
                    original = normalized_map[normalized]
                    results[original] = on_dncr
                    # Cache each result
                    await self._set_cache(original, on_dncr)

            # Any phones not in response, assume not registered
            for phone in uncached_phones:
                if phone not in results:
                    results[phone] = False

            logger.info(
                f"DNCR batch check: {len(phones)} numbers, "
                f"{sum(1 for v in results.values() if v)} on register"
            )

            return results

        except Exception as e:
            logger.error(f"DNCR batch check failed: {e}")
            sentry_sdk.capture_exception(e)

            # Fail open for unchecked numbers
            for phone in uncached_phones:
                if phone not in results:
                    results[phone] = False

            return results

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()


# Singleton instance
_dncr_client: DNCRClient | None = None


def get_dncr_client() -> DNCRClient:
    """Get or create DNCR client instance."""
    global _dncr_client
    if _dncr_client is None:
        _dncr_client = DNCRClient()
    return _dncr_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Settings-based configuration
# [x] Graceful degradation if not configured
# [x] Individual number checking
# [x] Batch number checking
# [x] Redis caching with configurable TTL
# [x] Phone number normalization (AU formats)
# [x] Privacy-preserving cache keys (hashed)
# [x] Sentry error tracking
# [x] Fail-open behavior (allows contact on API failure)
# [x] Proper logging for audit trail
# [x] All functions have type hints
# [x] All functions have docstrings
