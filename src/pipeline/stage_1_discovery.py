"""
Stage 1 Discovery — DFS Signal-First
Directive #259 — Architecture v5

Discovers businesses by technology signals from signal_configurations.
Reads signal config → extracts technology list → calls DFS domains_by_technology
→ deduplicates by domain → inserts new rows to business_universe.

Discovers ONLY. No enrichment, no scoring, no outreach.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import asyncpg

from src.clients.dfs_labs_client import DFSLabsClient
from src.enrichment.signal_config import SignalConfig, SignalConfigRepository
from src.utils.domain_blocklist import is_blocked

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S1 = 1
DISCOVERY_SOURCE = "dfs_domains_by_tech"
DEFAULT_DELAY_BETWEEN_TECHS = 0.5  # seconds — rate limiting
DEFAULT_MAX_DOMAINS_PER_TECH = 1000
DEFAULT_PAGE_SIZE = 100  # DFS default, max per call


class Stage1Discovery:
    """
    DFS signal-first discovery.

    Usage:
        stage = Stage1Discovery(dfs_client, signal_repo, conn)
        result = await stage.run("marketing_agency")
    """

    def __init__(
        self,
        dfs_client: DFSLabsClient,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
        delay_between_techs: float = DEFAULT_DELAY_BETWEEN_TECHS,
    ) -> None:
        self.dfs = dfs_client
        self.signal_repo = signal_repo
        self.conn = conn
        self.delay = delay_between_techs

    async def run(self, vertical_slug: str) -> dict[str, Any]:
        """
        Full discovery run for a vertical.
        Returns: {discovered, duplicates_skipped, api_calls, cost_usd, technologies_searched}
        """
        config = await self.signal_repo.get_config(vertical_slug)
        technologies = config.all_dfs_technologies
        logger.info(
            f"Stage 1: {vertical_slug} — {len(technologies)} technologies to search: {technologies}"
        )
        return await self.run_batch(
            vertical_slug=vertical_slug,
            technologies=technologies,
            max_domains_per_tech=DEFAULT_MAX_DOMAINS_PER_TECH,
        )

    async def run_batch(
        self,
        vertical_slug: str,
        technologies: list[str],
        max_domains_per_tech: int = DEFAULT_MAX_DOMAINS_PER_TECH,
    ) -> dict[str, Any]:
        """
        Discovery run for a specific technology list (supports partial runs and testing).
        """
        total_discovered = 0
        total_duplicates = 0
        total_api_calls = 0

        for tech in technologies:
            logger.info(f"Stage 1: searching '{tech}'")
            discovered, dupes, calls = await self._discover_by_technology(
                technology_name=tech,
                max_domains=max_domains_per_tech,
            )
            total_discovered += discovered
            total_duplicates += dupes
            total_api_calls += calls
            if self.delay > 0:
                await asyncio.sleep(self.delay)

        cost_usd = float(self.dfs.total_cost_usd)
        result = {
            "discovered": total_discovered,
            "duplicates_skipped": total_duplicates,
            "api_calls": total_api_calls,
            "cost_usd": cost_usd,
            "cost_aud": round(cost_usd * 1.55, 4),
            "technologies_searched": len(technologies),
        }
        logger.info(f"Stage 1 complete: {result}")
        return result

    async def _discover_by_technology(
        self, technology_name: str, max_domains: int
    ) -> tuple[int, int, int]:
        """Fetch all pages for one technology. Returns (discovered, dupes, api_calls)."""
        discovered = 0
        dupes = 0
        api_calls = 0
        offset = 0

        while offset < max_domains:
            limit = min(DEFAULT_PAGE_SIZE, max_domains - offset)
            response = await self.dfs.domains_by_technology(
                technology_name=technology_name,
                limit=limit,
                offset=offset,
            )
            api_calls += 1
            items = response.get("items") or []
            total_count = response.get("total_count", 0)

            if not items:
                break

            for item in items:
                domain = item.get("domain")
                if not domain:
                    continue
                ok = await self._upsert_domain(domain, technology_name, item)
                if ok:
                    discovered += 1
                else:
                    dupes += 1

            offset += len(items)
            if offset >= total_count:
                break

        return discovered, dupes, api_calls

    async def _upsert_domain(
        self, domain: str, technology_name: str, item: dict
    ) -> bool:
        """
        Insert domain if new, append technology if exists.
        Returns True if new row inserted, False if existing row updated or blocked.
        Directive #267: checks domain blocklist before any DB operation;
        uses INSERT ... ON CONFLICT for atomic upsert (no TOCTOU races).
        """
        # AU-only filter: only accept domains with .au TLD (#268)
        # DFS country_iso_code=AU doesn't guarantee TLD — post-filter for quality
        if not domain.lower().endswith(".au"):
            logger.debug(f"S1: skipping non-AU domain {domain!r}")
            return False

        if is_blocked(domain):
            logger.debug(f"S1: skipping blocked domain {domain!r}")
            return False

        now = datetime.now(timezone.utc)

        result = await self.conn.fetchrow(
            """
            INSERT INTO business_universe (
                display_name,
                domain,
                dfs_technologies,
                dfs_discovery_sources,
                dfs_technology_detected_at,
                pipeline_stage,
                pipeline_updated_at,
                discovered_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain <> '' DO UPDATE
                SET dfs_technologies = (
                        SELECT jsonb_agg(DISTINCT elem ORDER BY elem)
                        FROM jsonb_array_elements_text(
                            COALESCE(business_universe.dfs_technologies, '[]'::jsonb)
                            || COALESCE(EXCLUDED.dfs_technologies, '[]'::jsonb)
                        ) AS elem
                    ),
                    dfs_technology_detected_at = EXCLUDED.dfs_technology_detected_at,
                    pipeline_updated_at = EXCLUDED.pipeline_updated_at
            RETURNING (xmax = 0) AS inserted
            """,
            item.get("title") or domain,   # display_name
            domain,
            [technology_name],              # dfs_technologies
            [DISCOVERY_SOURCE],             # dfs_discovery_sources
            now,
            PIPELINE_STAGE_S1,
            now,
            now,
        )
        return bool(result["inserted"]) if result else False
