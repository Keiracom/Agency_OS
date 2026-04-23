"""
Contract: src/integrations/dncr_client.py
Purpose: Client for the Australian Do-Not-Call Register (DNCR) B2B lookup API.
         Operators are obliged to check phone numbers against DNCR before
         initiating voice/SMS outreach under the Do Not Call Register Act 2006.
Layer: 2 - integrations
Imports: httpx, stdlib
Consumers: src/outreach/safety/compliance_guard.py (injection point as
           dncr_lookup callable), src/services/suppression_manager.py

Required env vars (Dave to configure in /home/elliotbot/.config/agency-os/.env):
  DNCR_API_KEY      — bearer token issued by ACMA / reseller
  DNCR_API_BASE_URL — API root (default https://api.dncr.acma.gov.au/v1 —
                      CONFIRM with Dave/ACMA docs before prod)
  DNCR_CACHE_TTL_HOURS — hours to cache a result (default 24)

When DNCR_API_KEY is unset, the client operates in DEGRADED MODE: lookup()
returns {"registered": None, "registered_at": None, "last_checked": now,
         "status": "degraded:no_api_key"}. This unblocks dev without
masking compliance risk — compliance_guard treats registered=None as a
caution signal (log + allow, with operator alert via deliverability path
in the production wire).

Failure modes (never raise):
  - Network timeout, connection error, non-2xx response  -> degraded:network
  - Invalid JSON response                                 -> degraded:parse
  - Rate limit (429)                                      -> degraded:rate_limited
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import httpx

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.dncr.acma.gov.au/v1"  # CONFIRM with Dave
DEFAULT_TIMEOUT = 10.0
DEFAULT_CACHE_TTL_HOURS = 24


@dataclass
class DNCRResult:
    registered: bool | None       # True = on register, False = not, None = degraded
    registered_at: datetime | None
    last_checked: datetime
    status: str                   # "ok" | "degraded:no_api_key" | "degraded:network" | "degraded:parse" | "degraded:rate_limited"


class DNCRClient:
    """Client with in-memory 24hr cache. Never raises — degraded on any failure."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        cache_ttl_hours: int | None = None,
        http_client: httpx.Client | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self.api_key = api_key or os.environ.get("DNCR_API_KEY")
        self.base_url = (base_url or os.environ.get("DNCR_API_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        ttl_hours = (
            cache_ttl_hours
            if cache_ttl_hours is not None
            else int(os.environ.get("DNCR_CACHE_TTL_HOURS", DEFAULT_CACHE_TTL_HOURS))
        )
        self.cache_ttl = timedelta(hours=ttl_hours)
        self._http = http_client
        self._now = now_fn
        self._cache: dict[str, tuple[datetime, DNCRResult]] = {}

    def lookup(self, phone_number: str) -> DNCRResult:
        normalised = self._normalise(phone_number)
        cached = self._cache_get(normalised)
        if cached is not None:
            return cached

        result = self._fetch(normalised) if self.api_key else self._degraded("no_api_key")
        self._cache_put(normalised, result)
        return result

    def _fetch(self, phone: str) -> DNCRResult:
        try:
            client = self._http or httpx.Client(timeout=self.timeout)
            resp = client.get(
                f"{self.base_url}/lookup",
                params={"phone": phone},
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if resp.status_code == 429:
                return self._degraded("rate_limited")
            if resp.status_code >= 400:
                logger.warning("DNCR lookup %s returned %s", phone, resp.status_code)
                return self._degraded("network")
            data = resp.json()
            return DNCRResult(
                registered=bool(data.get("registered")),
                registered_at=self._parse_iso(data.get("registered_at")),
                last_checked=self._now(),
                status="ok",
            )
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            logger.warning("DNCR network failure for %s: %s", phone, exc)
            return self._degraded("network")
        except (ValueError, KeyError) as exc:
            logger.warning("DNCR parse failure for %s: %s", phone, exc)
            return self._degraded("parse")

    def _degraded(self, kind: str) -> DNCRResult:
        return DNCRResult(
            registered=None, registered_at=None,
            last_checked=self._now(), status=f"degraded:{kind}",
        )

    def _cache_get(self, phone: str) -> DNCRResult | None:
        entry = self._cache.get(phone)
        if entry is None:
            return None
        stored_at, result = entry
        if self._now() - stored_at > self.cache_ttl:
            return None
        return result

    def _cache_put(self, phone: str, result: DNCRResult) -> None:
        # Do NOT cache degraded results — the next call should retry.
        if result.status != "ok":
            return
        self._cache[phone] = (self._now(), result)

    @staticmethod
    def _normalise(phone: str) -> str:
        """Strip spaces / dashes; keep leading + for E.164."""
        if not phone:
            return ""
        stripped = "".join(c for c in phone if c.isdigit() or c == "+")
        return stripped

    @staticmethod
    def _parse_iso(s: str | None) -> datetime | None:
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
