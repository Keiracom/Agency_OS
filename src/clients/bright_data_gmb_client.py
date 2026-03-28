"""
Bright Data GMB Client — Stage 2 enrichment
Directive #260

Searches for a business's Google Maps listing by name.
Cost: $0.001 USD per record.
"""

from __future__ import annotations

import asyncio
import logging
import os
from decimal import Decimal
from typing import Any

import httpx
from dotenv import load_dotenv

# Load .env with override=True so Datasets key wins over Scrapers key in shell env (#268)
load_dotenv("/home/elliotbot/.config/agency-os/.env", override=True)

logger = logging.getLogger(__name__)

BRIGHT_DATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "")
BD_GMB_DATASET_ID = (
    "gd_m8ebnr0q2qlklc02fz"  # Google Maps full information (verified in BD inventory)
)
BD_API_BASE = "https://api.brightdata.com/datasets/v3"
COST_PER_RECORD_USD = Decimal("0.001")
POLL_INTERVAL_S = 5
MAX_POLL_ATTEMPTS = 60  # 5 min max


class BrightDataGMBClient:
    """
    Searches Bright Data's Google Maps dataset by business name.
    Returns structured GMB data: place_id, category, rating, review_count,
    work_hours, full_address.
    """

    def __init__(self, api_key: str = BRIGHT_DATA_API_KEY) -> None:
        self.api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._records_fetched = 0

    @property
    def total_cost_usd(self) -> Decimal:
        return COST_PER_RECORD_USD * self._records_fetched

    async def search_by_name(
        self,
        business_name: str,
        country: str = "Australia",
    ) -> dict[str, Any] | None:
        """
        Search for a GMB listing by business name.
        Returns mapped GMB dict or None if not found.
        """
        # With discover_by=location, country is passed separately in the body.
        # keyword = business name only (no country suffix needed).
        query = business_name
        async with httpx.AsyncClient(timeout=30) as client:
            # Trigger dataset snapshot
            snapshot_id = await self._trigger_snapshot(client, query)
            if not snapshot_id:
                return None

            # Poll for completion
            results = await self._poll_and_fetch(client, snapshot_id)
            if not results:
                return None

            # Return first matching result
            for item in results:
                mapped = self._map_item(item)
                if mapped:
                    self._records_fetched += 1
                    return mapped
            return None

    async def _trigger_snapshot(self, client: httpx.AsyncClient, query: str) -> str | None:
        """Trigger a Bright Data dataset snapshot. Returns snapshot_id.

        Uses discover_by=location with country=AU + keyword (not discover_by=keyword
        which is unsupported by this dataset). Fix: Directive #268.
        """
        url = f"{BD_API_BASE}/trigger"
        params = {
            "dataset_id": BD_GMB_DATASET_ID,
            "include_errors": "true",
            "type": "discover_new",
            "discover_by": "location",
        }
        body = [{"country": "AU", "keyword": query}]
        try:
            resp = await client.post(url, headers=self._headers, params=params, json=body)
            resp.raise_for_status()
            data = resp.json()
            return data.get("snapshot_id")
        except httpx.HTTPStatusError as e:
            logger.error(f"BD GMB trigger failed: {e.response.status_code} {e.response.text}")
            return None

    async def _poll_and_fetch(
        self, client: httpx.AsyncClient, snapshot_id: str
    ) -> list[dict] | None:
        """Poll until ready, then fetch results."""
        for attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_S)
            try:
                resp = await client.get(
                    f"{BD_API_BASE}/progress/{snapshot_id}",
                    headers=self._headers,
                )
                resp.raise_for_status()
                progress = resp.json()
                status = progress.get("status")
                if status == "ready":
                    return await self._fetch_snapshot(client, snapshot_id)
                elif status in ("failed", "stopped"):
                    logger.error(f"BD GMB snapshot {snapshot_id} {status}")
                    return None
                # else: running/pending — keep polling
            except httpx.HTTPStatusError as e:
                logger.warning(f"BD GMB poll attempt {attempt} failed: {e}")
        logger.error(f"BD GMB snapshot {snapshot_id} timed out after {MAX_POLL_ATTEMPTS} polls")
        return None

    async def _fetch_snapshot(
        self, client: httpx.AsyncClient, snapshot_id: str
    ) -> list[dict] | None:
        """Download completed snapshot as JSON."""
        try:
            resp = await client.get(
                f"{BD_API_BASE}/snapshot/{snapshot_id}",
                headers=self._headers,
                params={"format": "json"},
            )
            resp.raise_for_status()
            return resp.json() if isinstance(resp.json(), list) else [resp.json()]
        except httpx.HTTPStatusError as e:
            logger.error(f"BD GMB fetch failed: {e.response.status_code}")
            return None

    @staticmethod
    def _extract_category(raw_cat: Any) -> str | None:
        """
        Normalise BD GMB category field to a plain lowercase string.

        BD returns categories in several formats:
          - str: "Advertising agency"
          - list of dicts: [{"id": "advertising_agency", "title": "Advertising agency"}, ...]
          - str repr of list: "[{'id': 'advertising_agency', ...}]"

        We always extract the first category's id (snake_case) for consistent
        comparison with signal_configurations.gmb_categories.
        Directive #268 fix.
        """
        if not raw_cat:
            return None
        # Already a list of dicts (parsed JSON)
        if isinstance(raw_cat, list):
            first = raw_cat[0] if raw_cat else {}
            return str(first.get("id", "")).lower() or None
        # Plain string
        if isinstance(raw_cat, str):
            s = raw_cat.strip()
            if not s:
                return None
            # Python list repr: "[{'id': 'advertising_agency', ...}]"
            if s.startswith("[{"):
                import ast

                try:
                    parsed = ast.literal_eval(s)
                    if parsed and isinstance(parsed[0], dict):
                        return str(parsed[0].get("id", "")).lower() or None
                except Exception:
                    pass
            # Plain string category — normalise to snake_case
            return s.lower().replace(" ", "_").replace("-", "_")
        return None

    def _map_item(self, raw: dict) -> dict[str, Any] | None:
        """Map a Bright Data GMB record to BU column names."""
        place_id = raw.get("place_id") or raw.get("id")
        if not place_id:
            return None
        return {
            "gmb_place_id": place_id,
            "gmb_category": self._extract_category(raw.get("category") or raw.get("type")),
            "gmb_rating": raw.get("rating"),
            "gmb_review_count": raw.get("reviews") or raw.get("review_count"),
            "gmb_work_hours": raw.get("working_hours") or raw.get("work_hours"),
            "gmb_claimed": raw.get("claimed"),
            "gmb_maps_url": raw.get("url") or raw.get("maps_url"),
            "gmb_cid": raw.get("cid"),
            "address": raw.get("address") or raw.get("full_address"),
            "phone": raw.get("phone"),
            "lat": raw.get("latitude") or raw.get("lat"),
            "lng": raw.get("longitude") or raw.get("lng"),
        }
