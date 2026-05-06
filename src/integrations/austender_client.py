"""src/integrations/austender_client.py — AusTender OCDS API client.

Fetches Australian Government procurement data via the public OCDS-compliant
JSON API at tenders.gov.au. No authentication required — public open-
contracting data per AU Government policy.

Per LAW XII (canonical interface): callers go through skills/austender/
SKILL.md. Direct HTTP calls to AusTender outside this module are forbidden.
Per LAW XIII: any change to call patterns updates skills/austender/SKILL.md
in the same PR.

Skill spec: skills/austender/SKILL.md (PR #583).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Public — F2.2 connectors and tests import from here.
__all__ = [
    "AusTenderClient",
    "AwardEvent",
    "MIN_CONTRACT_VALUE_AUD",
]

_BASE_URL = "https://www.tenders.gov.au/Atm/Search/Ocds"
_REQUEST_TIMEOUT = 30.0
_MAX_DATE_RANGE_DAYS = 14  # OCDS endpoints time out on wide ranges
MIN_CONTRACT_VALUE_AUD = 50000  # Below this is panel-renewal noise.


class AusTenderClient:
    """Lightweight client for the AusTender OCDS endpoints.

    Designed for daily-cron + ad-hoc backfill use. No auth, no rate-limit key —
    public REST. Wrapper enforces date-range limits and value thresholds before
    hitting the network.
    """

    def __init__(self, base_url: str = _BASE_URL, timeout: float = _REQUEST_TIMEOUT):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_awards(
        self,
        date_from: date,
        date_to: date,
        value_min_aud: int = MIN_CONTRACT_VALUE_AUD,
    ) -> list[dict[str, Any]]:
        """Fetch award events between two dates (inclusive).

        Args:
            date_from: lower bound (inclusive). Reject if > today.
            date_to: upper bound (inclusive). Reject if range > 14 days.
            value_min_aud: minimum contract value AUD. Reject below 1000 (noise).

        Returns:
            List of OCDS release dicts — raw, unparsed. Caller filters / parses.

        Raises:
            ValueError on validation failure.
            httpx.HTTPStatusError on non-2xx after retries.
        """
        self._validate_range(date_from, date_to)
        if value_min_aud < 1000:
            raise ValueError(
                f"value_min_aud must be >= 1000 AUD (got {value_min_aud}); below is noise"
            )

        params = {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
            "min": str(value_min_aud),
        }
        url = f"{self._base_url}/contracts.json"
        logger.info("[austender] GET %s params=%s", url, params)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "[austender] %d %s for %s",
                    exc.response.status_code,
                    exc.response.reason_phrase,
                    url,
                )
                raise
            except httpx.RequestError as exc:
                logger.error("[austender] request error %s: %s", url, exc)
                raise

        data = response.json()
        releases = data.get("releases") or data.get("contracts") or []
        if not isinstance(releases, list):
            logger.warning("[austender] unexpected response shape: %s", type(releases).__name__)
            return []
        logger.info("[austender] fetched %d releases", len(releases))
        return releases

    async def fetch_release_by_id(self, ocid: str) -> dict[str, Any] | None:
        """Fetch a single OCDS release by Open Contracting ID."""
        if not ocid or not isinstance(ocid, str):
            raise ValueError(f"ocid must be a non-empty string, got {ocid!r}")
        url = f"{self._base_url}/release/{ocid}"
        logger.info("[austender] GET %s", url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.get(url)
            except httpx.RequestError as exc:
                logger.error("[austender] request error %s: %s", url, exc)
                raise

        if response.status_code == 404:
            logger.info("[austender] 404 not_found %s", url)
            return None
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _validate_range(date_from: date, date_to: date) -> None:
        if not isinstance(date_from, date) or not isinstance(date_to, date):
            raise ValueError("date_from and date_to must be datetime.date instances")
        if date_to < date_from:
            raise ValueError(f"date_to {date_to} is before date_from {date_from}")
        if date_to > date.today():
            raise ValueError(f"date_to {date_to} is in the future")
        if (date_to - date_from).days > _MAX_DATE_RANGE_DAYS:
            raise ValueError(
                f"range too wide: {(date_to - date_from).days} days > "
                f"{_MAX_DATE_RANGE_DAYS} (use multiple calls)"
            )


# ── Parser ────────────────────────────────────────────────────────────────────


class AwardEvent:
    """Trimmed AusTender award event — only the fields we persist to BU.

    Built from a raw OCDS release dict. Fields:
        contract_id (str): OCDS release.id
        supplier_abn (str | None): canonical "XX XXX XXX XXX" — None if missing/non-AU
        supplier_name (str | None): supplier party name
        supplier_country (str | None): for filter; we only persist 'AU'
        contract_value_aud (int | None): cast to int AUD, None if non-AUD or missing
        awarded_date (str | None): ISO 8601 date string
        agency_name (str | None): buyer party name
        classification_id (str | None): UNSPSC or AusTender category code
    """

    __slots__ = (
        "agency_name",
        "awarded_date",
        "classification_id",
        "contract_id",
        "contract_value_aud",
        "supplier_abn",
        "supplier_country",
        "supplier_name",
    )

    def __init__(
        self,
        *,
        contract_id: str,
        supplier_abn: str | None,
        supplier_name: str | None,
        supplier_country: str | None,
        contract_value_aud: int | None,
        awarded_date: str | None,
        agency_name: str | None,
        classification_id: str | None,
    ):
        self.contract_id = contract_id
        self.supplier_abn = supplier_abn
        self.supplier_name = supplier_name
        self.supplier_country = supplier_country
        self.contract_value_aud = contract_value_aud
        self.awarded_date = awarded_date
        self.agency_name = agency_name
        self.classification_id = classification_id

    def is_au_supplier(self) -> bool:
        """True iff supplier has an AU ABN. Matches F2.2 V0-ICP filter."""
        return self.supplier_abn is not None and self.supplier_country == "AU"

    @classmethod
    def from_ocds_release(cls, release: dict[str, Any]) -> AwardEvent | None:
        """Parse an OCDS release dict into an AwardEvent.

        Returns None if the release lacks required structural fields
        (contract_id, supplier party). Filtering on supplier ABN / country /
        currency happens at this layer; downstream gets a typed object or None.
        """
        from src.pipeline.abn_match import canonicalize_abn

        contract_id = release.get("ocid") or release.get("id")
        if not contract_id:
            return None

        # Find supplier and buyer parties
        parties = release.get("parties") or []
        supplier = next(
            (p for p in parties if "supplier" in (p.get("roles") or [])),
            None,
        )
        buyer = next(
            (p for p in parties if "buyer" in (p.get("roles") or [])),
            None,
        )

        # Supplier ABN canonicalisation (silent drop on non-AU / missing)
        supplier_abn = None
        supplier_country = None
        supplier_name = None
        if supplier:
            supplier_name = supplier.get("name")
            country = (supplier.get("address") or {}).get("countryName") or supplier.get("country")
            supplier_country = "AU" if country in ("AU", "Australia", "AUS") else country
            identifier = supplier.get("identifier") or {}
            if identifier.get("scheme") in ("AU-ABN", "ABN"):
                supplier_abn = canonicalize_abn(identifier.get("id"))

        # Award value — AUD only (LAW II)
        contract_value_aud: int | None = None
        awarded_date: str | None = None
        awards = release.get("awards") or []
        if awards:
            first_award = awards[0]
            value_obj = first_award.get("value") or {}
            currency = value_obj.get("currency")
            amount = value_obj.get("amount")
            if currency == "AUD" and isinstance(amount, int | float):
                contract_value_aud = int(amount)
            awarded_date_raw = first_award.get("date") or release.get("date")
            if awarded_date_raw:
                # Normalise to YYYY-MM-DD
                try:
                    parsed = datetime.fromisoformat(awarded_date_raw.replace("Z", "+00:00"))
                    awarded_date = parsed.date().isoformat()
                except (ValueError, AttributeError):
                    awarded_date = awarded_date_raw

            # Classification
            items = first_award.get("items") or []
            classification_id = None
            if items:
                cls_obj = items[0].get("classification") or {}
                classification_id = cls_obj.get("id")
        else:
            classification_id = None

        return cls(
            contract_id=str(contract_id),
            supplier_abn=supplier_abn,
            supplier_name=supplier_name,
            supplier_country=supplier_country,
            contract_value_aud=contract_value_aud,
            awarded_date=awarded_date,
            agency_name=buyer.get("name") if buyer else None,
            classification_id=classification_id,
        )


def date_range_chunks(start: date, end: date, step_days: int = 7) -> list[tuple[date, date]]:
    """Split a date range into chunks of <= step_days for paginated fetching.

    Used by the backfill flow to avoid OCDS timeouts on wide ranges.
    """
    if end < start:
        return []
    chunks: list[tuple[date, date]] = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=step_days - 1), end)
        chunks.append((cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    return chunks
