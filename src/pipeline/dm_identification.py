"""
Contract: src/pipeline/dm_identification.py
Purpose: Decision maker identification pipeline — tiered lookup (LinkedIn → website → ABN)
Layer: 4 - orchestration-adjacent pipeline
Imports: integrations
Consumers: enrichment_flow.py, lead_enrichment_flow.py

dm_identification.py — Decision maker identification pipeline.
Directive #286
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Words that indicate a business entity name, not a person name
_BUSINESS_WORDS = {
    "PLUMBING", "DENTAL", "SERVICES", "PTY", "LTD", "LIMITED", "TRUST",
    "FAMILY", "AUSTRALIA", "MANAGEMENT", "GROUP", "HOLDINGS", "PARTNERS",
    "CONSULTING", "SOLUTIONS", "SYSTEMS", "TECHNOLOGIES", "ENTERPRISES",
    "INDUSTRIES", "TRADING", "INVESTMENTS", "PROPERTY", "PROPERTIES",
    "CONSTRUCTION", "ENGINEERING", "MEDICAL", "HEALTH", "CARE",
    "THE", "AND", "OF", "FOR",
}


@dataclass
class DMResult:
    name: Optional[str] = None
    title: Optional[str] = None
    source: str = "none"         # brightdata_linkedin | website_scrape | abn_entity
    confidence: str = "none"     # HIGH | MEDIUM | LOW | none
    linkedin_url: Optional[str] = None
    tier_used: str = "none"      # T-DM1 | T-DM2 | T-DM3 | none (for CIS tracking)


class DMIdentification:
    def __init__(self, bd_client=None):
        """bd_client: instance of BrightDataLinkedInClient (injected for testability)."""
        self._bd = bd_client

    async def identify(
        self,
        domain: str,
        company_name: str,
        linkedin_company_url: Optional[str] = None,
        spider_data: Optional[dict] = None,
        abn_data: Optional[dict] = None,
    ) -> DMResult:
        """
        Identify the decision maker for a business using tiered fallback logic.

        Returns DMResult with source and tier_used for CIS tracking.
        """
        spider_data = spider_data or {}
        abn_data = abn_data or {}

        # --- Step 1: Bright Data LinkedIn ---
        if self._bd is not None:
            linkedin_url = self._resolve_linkedin_url(spider_data, linkedin_company_url)
            try:
                people = await self._bd.lookup_company_people(
                    company_name, domain=domain, linkedin_url=linkedin_url
                )
                dm = self._bd.pick_decision_maker(people)
                if dm and dm.get("name"):
                    logger.info(
                        "dm_found source=brightdata_linkedin name=%s confidence=%s",
                        dm["name"],
                        dm["confidence"],
                    )
                    return DMResult(
                        name=dm["name"],
                        title=dm.get("title"),
                        source="brightdata_linkedin",
                        confidence=dm["confidence"],
                        linkedin_url=dm.get("linkedin_url"),
                        tier_used="T-DM1",
                    )
            except Exception:
                logger.exception("dm_brightdata_failed domain=%s", domain)

        # --- Step 2: Website scrape fallback ---
        team_names: list[str] = spider_data.get("team_names") or []

        # Also check title field for Dr. names
        title_text = spider_data.get("title") or ""
        dr_names = re.findall(r"\bDr\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?", title_text)
        all_names = team_names + dr_names

        if all_names:
            first_name = all_names[0]
            logger.info("dm_found source=website_scrape name=%s", first_name)
            return DMResult(
                name=first_name,
                title=None,
                source="website_scrape",
                confidence="MEDIUM",
                tier_used="T-DM2",
            )

        # --- Step 3: ABN entity name fallback ---
        entity_name = abn_data.get("entity_name") or ""
        if entity_name:
            candidate = self._extract_name_from_entity(entity_name)
            if candidate:
                logger.info("dm_found source=abn_entity name=%s", candidate)
                return DMResult(
                    name=candidate,
                    title=None,
                    source="abn_entity",
                    confidence="LOW",
                    tier_used="T-DM3",
                )

        # --- Step 4: No DM found ---
        logger.info("dm_not_found domain=%s", domain)
        return DMResult()

    def _resolve_linkedin_url(
        self,
        spider_data: dict,
        linkedin_company_url: Optional[str],
    ) -> Optional[str]:
        """Try to extract LinkedIn URL from spider_data socials, fallback to param."""
        socials = spider_data.get("socials") or {}
        if isinstance(socials, dict):
            linkedin_slug = socials.get("linkedin")
            if linkedin_slug:
                # If it looks like a full URL, use it directly
                if linkedin_slug.startswith("http"):
                    return linkedin_slug
                # Otherwise reconstruct from slug
                slug = linkedin_slug.strip("/").split("/")[-1]
                if slug:
                    return f"https://www.linkedin.com/company/{slug}"
        return linkedin_company_url

    def _extract_name_from_entity(self, entity_name: str) -> Optional[str]:
        """
        Try to extract a person surname from an ABN entity name.
        Returns title-cased word if found, else None.
        """
        words = entity_name.upper().split()
        # Filter business words and short/non-alpha tokens
        candidates = [
            w for w in words
            if w.isalpha()
            and len(w) > 2
            and w not in _BUSINESS_WORDS
        ]
        if candidates:
            return candidates[0].title()
        return None
