"""
Stage 5 Decision-Maker Waterfall — Architecture v5
Directive #263

Finds decision makers for businesses above the DM score threshold.
Waterfall: cheapest source first, stop on first success.
Sources: GMBContactExtractor (free, instant) → LeadmagicPersonFinder (paid, fast)

S5 finds DMs ONLY. No message generation, no outreach.
"""
from __future__ import annotations

import logging
import re
from abc import abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

import asyncpg
import httpx

from src.enrichment.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S5 = 5
DM_SOURCE_NONE = "none"

# Title priority: owner/founder roles first, senior exec second
PRIORITY_TITLES = [
    "owner", "founder", "co-founder", "director", "ceo",
    "chief executive", "managing director", "md",
    "general manager", "head of", "principal", "partner",
]


@dataclass
class DMResult:
    """A found decision maker with at least name + one contact method."""
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    source: str = DM_SOURCE_NONE

    @property
    def is_valid(self) -> bool:
        """Valid = name plus at least one contact method."""
        return bool(self.name) and any([self.email, self.phone, self.linkedin_url])


class DMSource(Protocol):
    """Protocol for DM discovery sources. Implement to add a new source."""
    source_name: str

    @abstractmethod
    async def find(self, business: dict[str, Any]) -> DMResult | None:
        """Attempt to find a DM. Return DMResult if found, None otherwise."""
        ...


class GMBContactExtractor:
    """
    Free source — extract contact from GMB data already in BU.
    Uses existing gmb_phone and business name. No API calls.
    """
    source_name = "gmb"

    async def find(self, business: dict[str, Any]) -> DMResult | None:
        phone = business.get("phone")
        name = business.get("display_name") or business.get("domain")
        if not phone or not name:
            return None
        # GMB gives us a business phone, not a named DM — not valid per DMResult.is_valid
        # unless we can pair it with a name from the listing
        return None  # Intentionally returns None — GMB phone is company-level, not DM-level


class WebsiteContactScraper:
    """
    Free source — scrape /contact or /about page via Jina AI Reader.
    Extracts name, email, phone using patterns.
    """
    source_name = "website"
    _jina_base = "https://r.jina.ai"
    _timeout = 30

    async def find(self, business: dict[str, Any]) -> DMResult | None:
        domain = business.get("domain")
        if not domain:
            return None

        for path in ["/contact", "/about", "/about-us", "/"]:
            result = await self._scrape(f"https://{domain}{path}")
            if result:
                return result
        return None

    async def _scrape(self, url: str) -> DMResult | None:
        jina_url = f"{self._jina_base}/{url}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    jina_url,
                    headers={"Accept": "text/markdown", "X-No-Cache": "true"},
                    follow_redirects=True,
                )
                if resp.status_code != 200 or len(resp.text) < 200:
                    return None
                return self._extract_contact(resp.text)
        except Exception as e:
            logger.debug(f"Jina scrape failed for {url}: {e}")
            return None

    def _extract_contact(self, text: str) -> DMResult | None:
        # Email pattern
        emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
        # Filter out noreply/info/admin
        emails = [e for e in emails if not re.match(r"^(noreply|info|admin|hello|contact|support)@", e, re.I)]
        # Phone pattern (AU format)
        phones = re.findall(r"(?:\+61|0)[0-9\s\-\.]{8,12}", text)
        # Name: look for "Owner:" / "Founder:" / "Director:" labels
        name_match = re.search(
            r"(?:Owner|Founder|Director|CEO|Principal|Managing Director)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
            text,
        )

        email = emails[0] if emails else None
        phone = phones[0].strip() if phones else None
        name = name_match.group(1) if name_match else None

        if not (email or phone):
            return None

        return DMResult(
            name=name or "Unknown",
            email=email,
            phone=phone,
            source="website",
        )


class LeadmagicPersonFinder:
    """
    Paid source — find DM via Leadmagic employees + email lookup.
    Uses find_employees to identify owner/director, then find_email.
    Cost: ~$0.015 per email found.
    """
    source_name = "leadmagic"

    def __init__(self, leadmagic_client: Any) -> None:
        self.lm = leadmagic_client

    async def find(self, business: dict[str, Any]) -> DMResult | None:
        domain = business.get("domain")
        if not domain:
            return None

        # Step 1: Find employees and identify best DM candidate
        try:
            employees_resp = await self.lm.find_employees(domain, limit=10)
            employees = employees_resp if isinstance(employees_resp, list) else (employees_resp or {}).get("data", [])
        except Exception as e:
            logger.warning(f"Leadmagic find_employees failed for {domain}: {e}")
            employees = []

        person = self._pick_best_dm(employees)

        if not person:
            # Fallback: role finder for CEO/owner
            try:
                person = await self.lm.find_by_role(domain, "owner")
                if not person:
                    person = await self.lm.find_by_role(domain, "director")
            except Exception as e:
                logger.warning(f"Leadmagic find_by_role failed for {domain}: {e}")

        if not person:
            return None

        first = person.get("first_name", "")
        last = person.get("last_name", "")
        name = f"{first} {last}".strip() or None
        if not name:
            return None

        # Step 2: Find email
        email = None
        try:
            email_resp = await self.lm.find_email(first, last, domain)
            if isinstance(email_resp, dict):
                email = email_resp.get("email")
            elif hasattr(email_resp, "email"):
                email = email_resp.email  # EmailFinderResult object
            else:
                email = email_resp
        except Exception as e:
            logger.debug(f"Leadmagic email lookup failed for {domain}: {e}")

        return DMResult(
            name=name,
            title=person.get("title") or person.get("job_title"),
            email=email,
            linkedin_url=person.get("linkedin_url") or person.get("profile_url"),
            source="leadmagic",
        )

    def _pick_best_dm(self, employees: list[dict]) -> dict | None:
        """Pick highest-priority DM from employee list."""
        if not employees:
            return None
        for priority in PRIORITY_TITLES:
            for emp in employees:
                title = (emp.get("title") or emp.get("job_title") or "").lower()
                if priority in title:
                    return emp
        return employees[0] if employees else None


class Stage5DMWaterfall:
    """
    DM waterfall for S4-scored businesses above the DM gate threshold.

    Usage:
        stage = Stage5DMWaterfall(leadmagic_client, signal_repo, conn)
        result = await stage.run("marketing_agency", batch_size=25)
    """

    def __init__(
        self,
        leadmagic_client: Any,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
        extra_sources: list[DMSource] | None = None,
    ) -> None:
        self.conn = conn
        self.signal_repo = signal_repo
        # Waterfall order: GMB (free, instant) → Leadmagic (paid, fast)
        # WebsiteContactScraper removed — Jina latency (~16s/page × 4 pages) too slow for DM waterfall
        self.sources: list[DMSource] = [
            GMBContactExtractor(),
            LeadmagicPersonFinder(leadmagic_client),
            *(extra_sources or []),
        ]

    async def run(
        self,
        vertical_slug: str,
        batch_size: int = 25,
    ) -> dict[str, Any]:
        """
        Find DMs for businesses above DM score gate.
        Returns {found, not_found, skipped_low_score, sources_used, cost_usd}
        """
        config = await self.signal_repo.get_config(vertical_slug)
        dm_gate = config.enrichment_gates.get("min_score_to_dm", 50)

        rows = await self.conn.fetch(
            """
            SELECT id, domain, display_name, phone, address, gmb_place_id,
                   propensity_score, reachability_score, dm_email, dm_phone
            FROM business_universe
            WHERE pipeline_stage = 4
              AND propensity_score >= $1
            ORDER BY propensity_score DESC, pipeline_updated_at ASC
            LIMIT $2
            """,
            dm_gate,
            batch_size,
        )

        found = not_found = 0
        sources_used: dict[str, int] = {}

        for row in rows:
            business = dict(row)
            dm = await self._run_waterfall(business)
            if dm and dm.is_valid:
                found += 1
                sources_used[dm.source] = sources_used.get(dm.source, 0) + 1
            else:
                not_found += 1
            await self._write_result(business["id"], dm, business)

        return {
            "found": found,
            "not_found": not_found,
            "sources_used": sources_used,
            "cost_usd": 0.0,  # tracked per-call in Leadmagic client
        }

    async def _run_waterfall(self, business: dict[str, Any]) -> DMResult | None:
        """Try each source in order, return first valid result."""
        for source in self.sources:
            try:
                result = await source.find(business)
                if result and result.is_valid:
                    logger.info(f"DM found via {source.source_name} for {business.get('domain')}")
                    return result
            except Exception as e:
                logger.warning(f"Source {source.source_name} failed for {business.get('domain')}: {e}")
        return None

    async def _write_result(
        self,
        row_id: str,
        dm: DMResult | None,
        business: dict[str, Any],
    ) -> None:
        """Write DM result and recalculate reachability."""
        now = datetime.now(UTC)
        reachability = self._recalculate_reachability(business, dm)

        await self.conn.execute(
            """
            UPDATE business_universe SET
                dm_name = $1,
                dm_title = $2,
                dm_email = $3,
                dm_phone = $4,
                dm_linkedin_url = $5,
                dm_source = $6,
                dm_found_at = $7,
                reachability_score = $8,
                pipeline_stage = $9,
                pipeline_updated_at = $10
            WHERE id = $11
            """,
            dm.name if dm else None,
            dm.title if dm else None,
            dm.email if dm else None,
            dm.phone if dm else None,
            dm.linkedin_url if dm else None,
            dm.source if dm else DM_SOURCE_NONE,
            now if dm else None,
            reachability,
            PIPELINE_STAGE_S5,
            now,
            row_id,
        )

    def _recalculate_reachability(
        self,
        business: dict[str, Any],
        dm: DMResult | None,
    ) -> int:
        """Recalculate reachability score with confirmed DM channels."""
        score = 0
        email = (dm.email if dm else None) or business.get("dm_email")
        phone = (dm.phone if dm else None) or business.get("dm_phone") or business.get("phone")
        linkedin = (dm.linkedin_url if dm else None)

        if email:
            score += 30
        if phone:
            score += 25
        if linkedin:
            score += 20
        if business.get("address"):
            score += 15
        if business.get("gmb_place_id"):
            score += 10
        return min(score, 100)
