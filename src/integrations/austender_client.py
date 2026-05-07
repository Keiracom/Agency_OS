"""src/integrations/austender_client.py — AusTender OCDS API client.

Fetches Australian Government procurement data via the public OCDS-compliant
JSON API at api.tenders.gov.au. No authentication required — public open-
contracting data per AU Government policy.

Per LAW XII (canonical interface): callers go through skills/austender/
SKILL.md. Direct HTTP calls to AusTender outside this module are forbidden.
Per LAW XIII: any change to call patterns updates skills/austender/SKILL.md
in the same PR.

PR #587/#588 originally pointed at https://www.tenders.gov.au/Atm/Search/Ocds
which is WAF-blocked at the egress layer. The live, public OCDS feed is at
https://api.tenders.gov.au/ocds. This module:

  - Hits /findByDates/contractPublished/{startISO}/{endISO} with full ISO
    8601 UTC timestamps (e.g. 2026-05-04T00:00:00Z), not bare YYYY-MM-DD.
  - Walks links.next cursor pagination (100 releases per page).
  - Filters by value_min_aud client-side because the public API exposes no
    `min` query param.
  - Reads contract value from contracts[i].value.amount (string!) and the
    buyer party role is `procuringEntity` (the legacy parser used `buyer`,
    which never matched on the live feed).

Skill spec: skills/austender/SKILL.md (PR #583).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Public — F2.2 connectors and tests import from here.
__all__ = [
    "AusTenderClient",
    "AwardEvent",
    "MIN_CONTRACT_VALUE_AUD",
    "date_range_chunks",
]

_BASE_URL = "https://api.tenders.gov.au/ocds"
_PATH_TEMPLATE = "/findByDates/contractPublished/{start_iso}/{end_iso}"
_REQUEST_TIMEOUT = 30.0
_MAX_PAGES = 200  # safety belt — 200 × 100 releases ≈ 20k contracts/window
MIN_CONTRACT_VALUE_AUD = 50000  # Below this is panel-renewal noise.


def _to_iso_z(d: date) -> str:
    """Format `d` as a full ISO 8601 UTC timestamp ending in `Z`.

    The live API rejects bare YYYY-MM-DD; it expects e.g.
    `2026-05-04T00:00:00Z` in the URL path.
    """
    return datetime.combine(d, time.min, tzinfo=UTC).isoformat().replace("+00:00", "Z")


class AusTenderClient:
    """Lightweight client for the AusTender OCDS endpoints.

    Designed for daily-cron + ad-hoc backfill use. No auth, no rate-limit key —
    public REST. Wrapper enforces date-range sanity + value thresholds before
    hitting the network. Cursor pagination is automatic.
    """

    def __init__(
        self,
        base_url: str = _BASE_URL,
        timeout: float = _REQUEST_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_awards(
        self,
        date_from: date,
        date_to: date,
        value_min_aud: int = MIN_CONTRACT_VALUE_AUD,
    ) -> list[dict[str, Any]]:
        """Fetch OCDS releases with contractPublished in [date_from, date_to].

        Args:
            date_from: lower bound (inclusive). Reject if > today.
            date_to: upper bound (inclusive). Must be >= date_from.
            value_min_aud: minimum contract value AUD applied client-side.
                Reject below 1000 (noise).

        Returns:
            List of OCDS release dicts (raw, unparsed). The caller invokes
            AwardEvent.from_ocds_release() per element. Releases below
            value_min_aud are dropped here so the consumer doesn't waste
            cycles parsing them.

        Raises:
            ValueError on validation failure.
            httpx.HTTPStatusError on non-2xx (no retry — caller decides).
        """
        self._validate_range(date_from, date_to)
        if value_min_aud < 1000:
            raise ValueError(
                f"value_min_aud must be >= 1000 AUD (got {value_min_aud}); below is noise"
            )

        first_url = self._base_url + _PATH_TEMPLATE.format(
            start_iso=_to_iso_z(date_from),
            end_iso=_to_iso_z(date_to),
        )
        logger.info("[austender] GET %s", first_url)

        out: list[dict[str, Any]] = []
        seen_ocids: set[str] = set()
        url: str | None = first_url
        pages = 0
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while url and pages < _MAX_PAGES:
                pages += 1
                try:
                    response = await client.get(url)
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
                releases = data.get("releases") or []
                if not isinstance(releases, list):
                    logger.warning(
                        "[austender] unexpected releases shape on page %d: %s",
                        pages,
                        type(releases).__name__,
                    )
                    break

                for release in releases:
                    ocid = release.get("ocid") or release.get("id")
                    if not ocid or ocid in seen_ocids:
                        continue
                    if not _release_clears_value_threshold(
                        release,
                        value_min_aud,
                    ):
                        continue
                    seen_ocids.add(ocid)
                    out.append(release)

                url = (data.get("links") or {}).get("next")

        if pages >= _MAX_PAGES:
            logger.warning(
                "[austender] hit _MAX_PAGES=%d; cursor truncated",
                _MAX_PAGES,
            )
        logger.info(
            "[austender] %d releases ≥ AUD %d across %d page(s)",
            len(out),
            value_min_aud,
            pages,
        )
        return out

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
        # NOTE: the legacy 14-day cap was needed for the WAF-fronted
        # /Atm/Search/Ocds endpoint which timed out. The api.tenders.gov.au
        # feed paginates with `links.next`, so wide ranges work — we no
        # longer enforce a hard upper bound here. date_range_chunks() is
        # still exported for callers that want to slice for memory/log
        # reasons, but it's no longer required for correctness.


def _coerce_amount(raw: Any) -> float | None:
    """Convert OCDS value.amount to float. The live feed returns it as a
    string (e.g. '607987.88'); accept int/float too for forward-compat."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        try:
            return float(raw)
        except ValueError:
            return None
    return None


def _release_clears_value_threshold(
    release: dict[str, Any],
    value_min_aud: int,
) -> bool:
    """True iff ANY contract on the release has currency=AUD and amount
    >= value_min_aud. Releases without an AUD amount are dropped."""
    contracts = release.get("contracts") or []
    for c in contracts:
        value = c.get("value") or {}
        if value.get("currency") != "AUD":
            continue
        amount = _coerce_amount(value.get("amount"))
        if amount is not None and amount >= value_min_aud:
            return True
    # Fall back to award.value when contract.value is absent (older releases).
    awards = release.get("awards") or []
    for a in awards:
        value = a.get("value") or {}
        if value.get("currency") != "AUD":
            continue
        amount = _coerce_amount(value.get("amount"))
        if amount is not None and amount >= value_min_aud:
            return True
    return False


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
        agency_name (str | None): buyer / procuringEntity party name
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
    ) -> None:
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

        Live-feed reality (api.tenders.gov.au, 2026-05):
          - Buyer party role is `procuringEntity` (NOT `buyer` as the OCDS
            spec suggests). Accept both for forward-compat.
          - Award value lives at contracts[i].value, not awards[i].value.
            Fall back to award.value if contract.value is absent.
          - amount fields are strings ('607987.88'), not numbers.
        """
        from src.pipeline.abn_match import canonicalize_abn

        contract_id = release.get("ocid") or release.get("id")
        if not contract_id:
            return None

        # Find supplier and buyer parties. Live feed uses 'procuringEntity'
        # for the buyer; legacy data may also use 'buyer'.
        parties = release.get("parties") or []
        supplier = next(
            (p for p in parties if "supplier" in (p.get("roles") or [])),
            None,
        )
        buyer = next(
            (
                p
                for p in parties
                if any(r in (p.get("roles") or []) for r in ("procuringEntity", "buyer"))
            ),
            None,
        )

        # Supplier ABN canonicalisation (silent drop on non-AU / missing).
        # Live feed reality (api.tenders.gov.au, 2026-05):
        #   - ABN lives in `additionalIdentifiers` (an array), not the
        #     spec-bare `identifier` field. Check both.
        #   - countryName is uppercase 'AUSTRALIA', not the spec 'Australia'.
        supplier_abn = None
        supplier_country = None
        supplier_name = None
        if supplier:
            supplier_name = supplier.get("name")
            country = (supplier.get("address") or {}).get("countryName") or supplier.get("country")
            country_norm = (country or "").strip().upper()
            supplier_country = "AU" if country_norm in ("AU", "AUSTRALIA", "AUS") else country
            # Try `identifier` first (spec-bare), then walk
            # `additionalIdentifiers` for the AU-ABN entry.
            id_candidates: list[dict[str, Any]] = []
            primary = supplier.get("identifier")
            if isinstance(primary, dict):
                id_candidates.append(primary)
            extra = supplier.get("additionalIdentifiers") or []
            if isinstance(extra, list):
                id_candidates.extend(e for e in extra if isinstance(e, dict))
            for ident in id_candidates:
                if ident.get("scheme") in ("AU-ABN", "ABN"):
                    supplier_abn = canonicalize_abn(ident.get("id"))
                    if supplier_abn:
                        break

        # Award value — AUD only (LAW II). Prefer contract.value (where the
        # live feed actually puts it); fall back to award.value.
        contract_value_aud: int | None = None
        contracts = release.get("contracts") or []
        for c in contracts:
            value_obj = c.get("value") or {}
            if value_obj.get("currency") == "AUD":
                amount = _coerce_amount(value_obj.get("amount"))
                if amount is not None:
                    contract_value_aud = int(amount)
                    break
        if contract_value_aud is None:
            for a in release.get("awards") or []:
                value_obj = a.get("value") or {}
                if value_obj.get("currency") == "AUD":
                    amount = _coerce_amount(value_obj.get("amount"))
                    if amount is not None:
                        contract_value_aud = int(amount)
                        break

        # Award date + classification — prefer contract.dateSigned, fall
        # back to award.date, then release.date.
        awarded_date_raw: str | None = None
        classification_id: str | None = None
        if contracts:
            awarded_date_raw = contracts[0].get("dateSigned")
            items = contracts[0].get("items") or []
            if items:
                classification_id = (items[0].get("classification") or {}).get("id")
        if not awarded_date_raw:
            awards = release.get("awards") or []
            if awards:
                awarded_date_raw = awards[0].get("date")
                if classification_id is None:
                    items = awards[0].get("items") or []
                    if items:
                        classification_id = (items[0].get("classification") or {}).get("id")
        if not awarded_date_raw:
            awarded_date_raw = release.get("date")

        awarded_date: str | None = None
        if awarded_date_raw:
            try:
                parsed = datetime.fromisoformat(str(awarded_date_raw).replace("Z", "+00:00"))
                awarded_date = parsed.date().isoformat()
            except (ValueError, AttributeError):
                awarded_date = str(awarded_date_raw)

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


def date_range_chunks(
    start: date,
    end: date,
    step_days: int = 7,
) -> list[tuple[date, date]]:
    """Split a date range into chunks of <= step_days for paginated fetching.

    No longer required for correctness on api.tenders.gov.au (cursor paging
    handles wide ranges) — kept for callers that want bounded log output or
    progress checkpoints during large backfills.
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
