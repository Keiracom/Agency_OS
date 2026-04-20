"""
Contract: src/integrations/brightdata_client.py
Purpose: LinkedIn DM lookup via Bright Data Scrapers API (new Scrapers API key)
Layer: 2 - integrations
Imports: models only
Consumers: src/pipeline/dm_identification.py

brightdata_client.py — LinkedIn DM lookup via Bright Data Scrapers API.
Directive #286 | Cost: $0.00075/record ($0.75/1000)
"""
import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from src.integrations.circuit_breaker import circuit_breaker

logger = logging.getLogger(__name__)

BRIGHTDATA_SCRAPER_KEY = "636a81d7-4f89-4fb5-904b-f1e195ec20d2"  # updated 2026-03-31 (Directive #300g+h)
DATASET_LINKEDIN_COMPANY = "gd_l1vikfnt1wgvvqz95w"
DATASET_LINKEDIN_PROFILE = "gd_l1viktl72bvl7bjuj0"   # LinkedIn person profile dataset (confirmed 2026-04-01)
COST_PER_RECORD_USD = 0.00075

# DM title priority (lower index = higher priority)
DM_TITLE_PRIORITY = [
    "owner",
    "founder",
    "co-founder",
    "director",
    "principal",
    "managing director",
    "managing partner",
    "managing",
    "ceo",
    "chief executive",
    "proprietor",
    "partner",
    "president",
    "general manager",
]

# Threshold: titles at index < HIGH_CONFIDENCE_THRESHOLD get HIGH confidence
HIGH_CONFIDENCE_THRESHOLD = 6  # owner, founder, co-founder, director, principal, managing director


class BrightDataLinkedInClient:
    """Focused LinkedIn DM lookup client using new Scrapers API key."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or BRIGHTDATA_SCRAPER_KEY
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient()
        return self._client

    async def lookup_company_people(
        self,
        company_name: str,
        domain: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> list[dict]:
        """
        Returns list of dicts with keys: name, title, linkedin_url.
        Caps at 20 records. Never raises on empty results.
        """
        if linkedin_url:
            inputs = [{"url": linkedin_url}]
            discover_by = None
        else:
            search_url = f"https://www.linkedin.com/search/results/companies/?keywords={company_name}"
            inputs = [{"url": search_url}]
            discover_by = "keyword"

        try:
            results = await self._scraper_request(
                DATASET_LINKEDIN_COMPANY, inputs, discover_by=discover_by
            )
        except Exception:
            logger.exception("brightdata_lookup_failed company=%s", company_name)
            return []

        # Extract employees/staff array from company result
        people: list[dict] = []
        for record in results:
            employees = record.get("employees") or record.get("staff") or []
            if isinstance(employees, list):
                people.extend(employees)

        # If no nested employees, treat top-level records as people
        if not people:
            people = results

        people = people[:20]
        cost = COST_PER_RECORD_USD * len(people)
        logger.info(
            "brightdata_lookup_complete company=%s records=%d cost_usd=%.4f",
            company_name,
            len(people),
            cost,
        )
        return people

    def pick_decision_maker(self, people: list[dict]) -> Optional[dict]:
        """
        Synchronous. Scores each person by DM_TITLE_PRIORITY.
        Returns best match with confidence, or None if list is empty.
        """
        if not people:
            return None

        best_person = None
        best_index = len(DM_TITLE_PRIORITY) + 1

        for person in people:
            title_raw = (person.get("title") or "").lower()
            matched_index = len(DM_TITLE_PRIORITY)  # no match sentinel

            for idx, keyword in enumerate(DM_TITLE_PRIORITY):
                if keyword in title_raw:
                    matched_index = idx
                    break

            if matched_index < best_index:
                best_index = matched_index
                best_person = person

        if best_person is None:
            # All had no title match — return first person with LOW confidence
            best_person = people[0]
            confidence = "LOW"
        elif best_index < HIGH_CONFIDENCE_THRESHOLD:
            confidence = "HIGH"
        else:
            confidence = "MEDIUM"

        return {
            "name": best_person.get("name"),
            "title": best_person.get("title"),
            "linkedin_url": best_person.get("linkedin_url") or best_person.get("url"),
            "confidence": confidence,
        }

    @circuit_breaker("brightdata", failure_threshold=5, recovery_timeout=60)
    async def _scraper_request(
        self,
        dataset_id: str,
        inputs: list[dict],
        discover_by: Optional[str] = None,
    ) -> list[dict]:
        """
        Trigger → poll → download pattern. 120s timeout (24 × 5s).

        Supports two BD endpoint styles:
        - /v3/trigger (company dataset, existing)
        - /v3/scrape  (profile dataset, notify=false&include_errors=true)
        """
        base_url = "https://api.brightdata.com/datasets/v3"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        client = await self._get_client()

        # Profile dataset: synchronous /scrape endpoint (blocks until data ready, up to 300s)
        # Company dataset: async /trigger endpoint (returns snapshot_id, then poll)
        if dataset_id == DATASET_LINKEDIN_PROFILE:
            scrape_url = (
                f"{base_url}/scrape?dataset_id={dataset_id}"
                f"&notify=false&include_errors=true"
            )
            response = await client.post(
                scrape_url, headers=headers,
                json={"input": inputs},
                timeout=300.0,  # synchronous — wait up to 5 min
            )
            if response.status_code >= 400:
                raise ValueError(f"Bright Data API error: {response.status_code} {response.text[:200]}")
            if not response.text.strip():
                return []
            data = response.json()
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "name" in data:
                return [data]  # single record
            # Async 202 fallback — continue to poll
            snapshot_id_from_scrape = data.get("snapshot_id")
            if not snapshot_id_from_scrape:
                return []
            # Poll this snapshot
            for _ in range(60):
                await asyncio.sleep(5)
                prog = await client.get(
                    f"{base_url}/progress/{snapshot_id_from_scrape}", headers=headers, timeout=10.0
                )
                if prog.json().get("status") == "ready":
                    dl = await client.get(
                        f"{base_url}/snapshot/{snapshot_id_from_scrape}?format=json",
                        headers=headers, timeout=60.0
                    )
                    dl.raise_for_status()
                    return dl.json()
            raise TimeoutError(f"BD profile snapshot timeout (snapshot={snapshot_id_from_scrape})")

        trigger_url = f"{base_url}/trigger?dataset_id={dataset_id}&include_errors=true"
        if discover_by:
            trigger_url += f"&type=discover_new&discover_by={discover_by}"
        payload = inputs  # plain list for company

        response = await client.post(trigger_url, headers=headers, json=payload, timeout=30.0)
        if response.status_code >= 400:
            body = response.text
            raise ValueError(f"Bright Data API error: {response.status_code} {body}")
        # Handle empty response body
        if not response.text.strip():
            return []
        resp_data = response.json()
        # /scrape may return data directly (list or single dict) or a snapshot_id
        if isinstance(resp_data, list):
            return resp_data
        if isinstance(resp_data, dict):
            # Single record returned directly (synchronous /scrape)
            if "snapshot_id" not in resp_data and "id" in resp_data and "name" in resp_data:
                return [resp_data]
            # Snapshot async response
            snapshot_id = resp_data.get("snapshot_id") or resp_data.get("id")
            if not snapshot_id:
                raise ValueError(f"No snapshot_id in BD response: {resp_data}")
        logger.info("brightdata_triggered snapshot_id=%s dataset_id=%s", snapshot_id, dataset_id)

        # Poll until ready (max 300s = 60 × 5s intervals)
        for _ in range(60):
            await asyncio.sleep(5)
            try:
                progress = await client.get(
                    f"{base_url}/progress/{snapshot_id}", headers=headers, timeout=10.0
                )
                status_data = progress.json()
                status = status_data.get("status")

                if status == "ready":
                    logger.info(
                        "brightdata_ready snapshot_id=%s records=%s",
                        snapshot_id,
                        status_data.get("records", 0),
                    )
                    break
                elif status == "failed":
                    raise ValueError(f"Bright Data scraper job failed: {status_data}")
            except httpx.RequestError:
                pass  # retry on transient network errors

        else:
            raise TimeoutError(f"Bright Data scraper timed out after 300s (snapshot_id={snapshot_id})")

        # Download results
        data = await client.get(
            f"{base_url}/snapshot/{snapshot_id}?format=json",
            headers=headers,
            timeout=60.0,
        )
        data.raise_for_status()
        return data.json()
