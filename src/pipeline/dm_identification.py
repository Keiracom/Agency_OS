"""
Contract: src/pipeline/dm_identification.py
Purpose: Decision maker identification pipeline — tiered lookup (SERP LinkedIn → BD LinkedIn → website → ABN)
Layer: 4 - orchestration-adjacent pipeline
Imports: integrations
Consumers: enrichment_flow.py, lead_enrichment_flow.py

dm_identification.py — Decision maker identification pipeline.
Directive #287 — SERP-first DM waterfall + AU location filter.
"""

import logging
import re
import re as _re
from dataclasses import dataclass

_COMPANY_NAME_RE = _re.compile(
    r"\b(PTY|LTD|AUSTRALIA|GROUP|COMPANY|CORP|HOLDINGS|SERVICES|SOLUTIONS|INDUSTRIES)\b",
    _re.IGNORECASE,
)

_RE_CORP_SUFFIX = _re.compile(
    r"\s*(PTY\.?\s*LTD\.?|PROPRIETARY\s+LIMITED|PTY\s+LIMITED|LIMITED|LTD\.?|TRUST)\s*$",
    _re.IGNORECASE,
)
_RE_TITLE_SPLIT = _re.compile(r"\s*[\|\-\u2013]\s*.+$")


def _is_company_profile(candidate: dict) -> bool:
    """Return True if the LinkedIn candidate looks like a company page, not a person."""
    name = (candidate.get("name") or "").strip()
    title = (candidate.get("title") or "").strip()
    if not name:
        return False
    # ALL CAPS name (company page pattern)
    if name == name.upper() and len(name) > 3 and " " in name:
        return True
    # Corporate keyword in name with no job title
    return bool(_COMPANY_NAME_RE.search(name) and not title)


def _best_company_name(
    domain: str,
    abn_display: str | None = None,
    gmb_name: str | None = None,
    website_title: str | None = None,
) -> tuple[str, str]:
    """
    Return (company_name, source) using priority:
    1. ABN display_name (stripped of PTY LTD etc)
    2. GMB business_name
    3. Website title (stripped of nav suffixes)
    4. Domain stem (fallback — strips www. prefix)
    """
    if abn_display and len(abn_display.strip()) > 3:
        name = _RE_CORP_SUFFIX.sub("", abn_display).strip()
        if len(name) > 3:
            return name, "abn_display"
    if gmb_name and len(gmb_name.strip()) > 3:
        return gmb_name.strip(), "gmb_name"
    if website_title and len(website_title.strip()) > 3:
        title = _RE_TITLE_SPLIT.sub("", website_title).strip()
        if len(title) > 3:
            return title, "website_title"
    _d = domain[4:] if domain.startswith("www.") else domain
    stem = _d.split(".")[0].replace("-", " ").title()
    return stem, "domain_stem"


logger = logging.getLogger(__name__)

# Words that indicate a business entity name, not a person name
_BUSINESS_WORDS = {
    "PLUMBING",
    "DENTAL",
    "SERVICES",
    "PTY",
    "LTD",
    "LIMITED",
    "TRUST",
    "FAMILY",
    "AUSTRALIA",
    "MANAGEMENT",
    "GROUP",
    "HOLDINGS",
    "PARTNERS",
    "CONSULTING",
    "SOLUTIONS",
    "SYSTEMS",
    "TECHNOLOGIES",
    "ENTERPRISES",
    "INDUSTRIES",
    "TRADING",
    "INVESTMENTS",
    "PROPERTY",
    "PROPERTIES",
    "CONSTRUCTION",
    "ENGINEERING",
    "MEDICAL",
    "HEALTH",
    "CARE",
    "THE",
    "AND",
    "OF",
    "FOR",
}

# Title keywords that indicate a decision maker, scored by seniority
_DM_TITLE_KEYWORDS: dict[str, int] = {
    "owner": 10,
    "founder": 10,
    "director": 9,
    "ceo": 9,
    "coo": 8,
    "cfo": 8,
    "principal": 7,
    "partner": 7,
    "manager": 5,
    "head": 4,
}


@dataclass
class DMResult:
    name: str | None = None
    title: str | None = None
    source: str = "none"  # serp_linkedin | brightdata_linkedin | website_scrape | abn_entity
    confidence: str = "none"  # HIGH | MEDIUM | LOW | none
    linkedin_url: str | None = None
    tier_used: str = "none"  # T-DM1 | T-DM2 | T-DM3 | T-DM4 | none (for CIS tracking)
    dm_search_source: str = "none"  # abn_display | gmb_name | website_title | domain_stem


class DMIdentification:
    def __init__(self, bd_client=None, dfs_client=None):
        """
        bd_client: instance of BrightDataLinkedInClient (injected for testability).
        dfs_client: instance of DFSLabsClient for SERP LinkedIn lookup (injected for testability).
        """
        self._bd = bd_client
        self._dfs = dfs_client

    async def identify(
        self,
        domain: str,
        company_name: str,
        linkedin_company_url: str | None = None,
        spider_data: dict | None = None,
        abn_data: dict | None = None,
    ) -> DMResult:
        """
        Identify the decision maker for a business using tiered fallback logic.

        Waterfall (Directive #287):
          T-DM1: Google SERP site:linkedin.com/in (DFS Labs, AU-filtered)
          T-DM2: Bright Data LinkedIn company lookup
          T-DM3: Website scrape team_names / Dr. names
          T-DM4: ABN entity surname extraction

        Returns DMResult with source and tier_used for CIS tracking.
        """
        spider_data = spider_data or {}
        abn_data = abn_data or {}

        # --- T-DM1: Google SERP LinkedIn (Directive #287) ---
        if self._dfs is not None:
            try:
                people = await self._dfs.search_linkedin_people(
                    company_name=company_name,
                    location_name="Australia",
                )
                people = [p for p in people if not _is_company_profile(p)]
                dm = self._pick_serp_dm(people)
                if dm and dm.get("name"):
                    logger.info(
                        "dm_found source=serp_linkedin name=%s",
                        dm["name"],
                    )
                    return DMResult(
                        name=dm["name"],
                        title=dm.get("title") or None,
                        source="serp_linkedin",
                        confidence="HIGH",
                        linkedin_url=dm.get("linkedin_url") or None,
                        tier_used="T-DM1",
                    )
            except Exception:
                logger.exception("dm_serp_failed domain=%s", domain)

        # --- T-DM2: Bright Data LinkedIn ---
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
                        tier_used="T-DM2",
                    )
            except Exception:
                logger.exception("dm_brightdata_failed domain=%s", domain)

        # --- T-DM3: Website scrape fallback ---
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
                tier_used="T-DM3",
            )

        # --- T-DM4: ABN entity name fallback ---
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
                    tier_used="T-DM4",
                )

        # --- No DM found ---
        logger.info("dm_not_found domain=%s", domain)
        return DMResult()

    @staticmethod
    def _pick_serp_dm(people: list[dict]) -> dict | None:
        """
        Pick the best decision maker from SERP LinkedIn results.
        Scores by title keyword seniority; falls back to first result with a name.
        """
        if not people:
            return None

        def _score(p: dict) -> int:
            title_lower = (p.get("title") or "").lower()
            return max(
                (_DM_TITLE_KEYWORDS[kw] for kw in _DM_TITLE_KEYWORDS if kw in title_lower),
                default=0,
            )

        # Only consider results that have a name
        named = [p for p in people if p.get("name")]
        if not named:
            return None

        return max(named, key=_score)

    def _resolve_linkedin_url(
        self,
        spider_data: dict,
        linkedin_company_url: str | None,
    ) -> str | None:
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

    def _extract_name_from_entity(self, entity_name: str) -> str | None:
        """
        Try to extract a person surname from an ABN entity name.
        Returns title-cased word if found, else None.
        """
        words = entity_name.upper().split()
        # Filter business words and short/non-alpha tokens
        candidates = [w for w in words if w.isalpha() and len(w) > 2 and w not in _BUSINESS_WORDS]
        if candidates:
            return candidates[0].title()
        return None
