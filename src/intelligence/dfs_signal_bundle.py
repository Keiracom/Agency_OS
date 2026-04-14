"""F2 — DFS Signal Bundle enrichment per prospect.

Fetches all relevant DFS signals for a domain in parallel.
Partial failures are acceptable — each signal is try/excepted independently.

Available DFS methods used:
  competitors_domain()   — $0.011/call — top organic competitors
  keywords_for_site()    — $0.011/call — top organic keywords
  ads_search_by_domain() — $0.002/call — is domain running Google Ads
  brand_serp()           — $0.002/call — brand SERP position + GMB presence
  backlinks_summary()    — $0.020/call — referring domains, domain rank
  indexed_pages()        — $0.002/call — approximate indexed page count
  domain_technologies()  — $0.010/call — tech stack

TODO (not yet in DFS client):
  - google_ads_advertisers(keyword) — live ad copy from competitor keywords
    (client has this method but takes keyword, not domain — not applicable here)

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)


class DFSSignalBundle:
    """F2 stage: fetch all DFS signals for a domain in parallel."""

    def __init__(self, dfs_client: "DFSLabsClient") -> None:
        self.dfs = dfs_client
        self._cost = 0.0

    async def enrich(self, domain: str, business_name: str | None = None) -> dict:
        """
        Fetch all DFS signals for a domain.

        Runs 7 calls in parallel. Each wrapped in try/except — partial failure OK.
        Returns merged bundle dict.

        Args:
            domain: bare domain e.g. "example.com.au"
            business_name: canonical business name for brand_serp + maps queries

        Returns:
            {
              "competitors": list,
              "keywords": list,
              "ads": dict | None,
              "brand_serp": dict | None,
              "backlinks": dict | None,
              "indexed_pages": int | None,
              "tech_stack": dict | None,
              "cost_usd": float,
              "partial_failures": list[str],
            }
        """
        cost_before = self.dfs.total_cost_usd

        results = await asyncio.gather(
            self._fetch_competitors(domain),
            self._fetch_keywords(domain),
            self._fetch_ads(domain),
            self._fetch_brand_serp(business_name or domain),
            self._fetch_backlinks(domain),
            self._fetch_indexed_pages(domain),
            self._fetch_tech_stack(domain),
            return_exceptions=False,
        )

        (
            competitors,
            keywords,
            ads,
            brand,
            backlinks,
            indexed,
            tech,
        ) = results

        cost_after = self.dfs.total_cost_usd
        self._cost = cost_after - cost_before

        # Collect any None fields as partial failures for observability
        partial_failures: list[str] = []
        if competitors is None:
            partial_failures.append("competitors")
        if keywords is None:
            partial_failures.append("keywords")
        if ads is None:
            partial_failures.append("ads")
        if brand is None:
            partial_failures.append("brand_serp")
        if backlinks is None:
            partial_failures.append("backlinks")
        if indexed is None:
            partial_failures.append("indexed_pages")
        if tech is None:
            partial_failures.append("tech_stack")

        return {
            "competitors": (competitors or {}).get("items", [])[:5],
            "keywords": (keywords or {}).get("items", [])[:20],
            "ads": ads,
            "brand_serp": brand,
            "backlinks": backlinks,
            "indexed_pages": indexed,
            "tech_stack": tech,
            "cost_usd": round(self._cost, 4),
            "partial_failures": partial_failures,
        }

    async def _fetch_competitors(self, domain: str) -> dict | None:
        try:
            return await self.dfs.competitors_domain(domain, limit=5)
        except Exception as exc:
            logger.warning("F2 competitors_domain failed for %s: %s", domain, exc)
            return None

    async def _fetch_keywords(self, domain: str) -> dict | None:
        try:
            return await self.dfs.keywords_for_site(domain, limit=20)
        except Exception as exc:
            logger.warning("F2 keywords_for_site failed for %s: %s", domain, exc)
            return None

    async def _fetch_ads(self, domain: str) -> dict | None:
        try:
            return await self.dfs.ads_search_by_domain(domain)
        except Exception as exc:
            logger.warning("F2 ads_search_by_domain failed for %s: %s", domain, exc)
            return None

    async def _fetch_brand_serp(self, business_name: str) -> dict | None:
        try:
            return await self.dfs.brand_serp(business_name)
        except Exception as exc:
            logger.warning("F2 brand_serp failed for %s: %s", business_name, exc)
            return None

    async def _fetch_backlinks(self, domain: str) -> dict | None:
        try:
            return await self.dfs.backlinks_summary(domain)
        except Exception as exc:
            logger.warning("F2 backlinks_summary failed for %s: %s", domain, exc)
            return None

    async def _fetch_indexed_pages(self, domain: str) -> int | None:
        try:
            return await self.dfs.indexed_pages(domain)
        except Exception as exc:
            logger.warning("F2 indexed_pages failed for %s: %s", domain, exc)
            return None

    async def _fetch_tech_stack(self, domain: str) -> dict | None:
        try:
            return await self.dfs.domain_technologies(domain)
        except Exception as exc:
            logger.warning("F2 domain_technologies failed for %s: %s", domain, exc)
            return None
