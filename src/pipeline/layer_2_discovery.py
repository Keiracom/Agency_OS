"""
Contract: src/pipeline/layer_2_discovery.py
Purpose: Layer 2 multi-source domain discovery engine — reads signal_configurations.discovery_config,
         runs 5 DFS sources concurrently, deduplicates by domain, writes to business_universe.
Layer: 4 - orchestration (uses asyncpg connection directly like stage_1_discovery)
Imports: clients, enrichment, utils
Consumers: orchestration flows
Directive: #272

v6 design: discovers broadly (all 5 sources), deduplicates, passes to Layer 3
for cheap filtering. No scoring here — pure discovery.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import asyncpg

from src.clients.dfs_labs_client import DFSLabsClient, get_dfs_labs_client
from src.enrichment.signal_config import SignalConfig, SignalConfigRepository
from src.utils.domain_blocklist import is_blocked

logger = logging.getLogger(__name__)

# Cost per source call (USD)
COST_DOMAIN_METRICS_BY_CATEGORIES = 0.10
COST_ADS_SEARCH = 0.006
COST_HTML_TERMS = 0.01
COST_JOBS = 0.006
COST_COMPETITORS_DOMAIN = 0.01


@dataclass
class DiscoveryStats:
    total_raw: int = 0
    unique_domains: int = 0
    written_new: int = 0
    written_skip: int = 0  # existing domain, skipped (idempotency)
    no_domain_count: int = 0
    blocked_count: int = 0
    sources_used: list[str] = field(default_factory=list)
    source_errors: list[str] = field(default_factory=list)
    estimated_cost_usd: float = 0.0
    budget_exceeded: bool = False


def _normalise_domain(url_or_domain: str) -> str:
    """Strip www., trailing slash, lowercase. Handle both URLs and bare domains."""
    s = url_or_domain.strip().lower()
    if s.startswith(("http://", "https://")):
        parsed = urlparse(s)
        s = parsed.netloc or s
    s = s.lstrip("www.").rstrip("/")
    return s


class Layer2Discovery:
    """
    Layer 2 of the v6 pipeline: multi-source domain discovery.

    Reads discovery_config from signal_configurations, runs 5 DFS sources
    concurrently, deduplicates, filters blocklist, and writes to business_universe.

    Usage:
        engine = Layer2Discovery(conn, dfs_client)
        stats = await engine.run("marketing_agency", daily_budget_usd=10.0)
    """

    def __init__(
        self,
        conn: asyncpg.Connection,
        dfs: DFSLabsClient,
    ) -> None:
        self._conn = conn
        self._dfs = dfs

    async def run(
        self,
        vertical: str,
        batch_id: uuid.UUID | None = None,
        daily_budget_usd: float = 10.0,
    ) -> DiscoveryStats:
        """
        Run full Layer 2 discovery for a vertical.

        Args:
            vertical: Vertical slug (e.g. "marketing_agency")
            batch_id: Optional batch UUID for tracking. Generated if not provided.
            daily_budget_usd: Stop discovery if accumulated cost would exceed this.

        Returns:
            DiscoveryStats with counts and cost estimate.
        """
        stats = DiscoveryStats()
        batch_id = batch_id or uuid.uuid4()

        # Load signal config
        config = await SignalConfigRepository(self._conn).get_config(vertical)
        discovery_cfg = config.discovery_config

        # Run all sources concurrently
        source_results = await self._run_all_sources(
            discovery_cfg, stats, daily_budget_usd
        )

        # Merge + deduplicate by domain
        seen_domains: dict[str, dict] = {}
        for item in source_results:
            domain = _normalise_domain(item.get("domain", ""))
            if not domain:
                stats.no_domain_count += 1
                continue
            if domain not in seen_domains:
                seen_domains[domain] = item

        stats.total_raw = len(source_results)
        stats.unique_domains = len(seen_domains)

        # Filter blocklist
        clean: dict[str, dict] = {}
        for domain, item in seen_domains.items():
            if is_blocked(domain):
                stats.blocked_count += 1
            else:
                clean[domain] = item

        # Write to BU
        for domain, item in clean.items():
            written = await self._upsert_domain(
                domain=domain,
                item=item,
                batch_id=batch_id,
            )
            if written:
                stats.written_new += 1
            else:
                stats.written_skip += 1

        logger.info(
            f"Layer2 [{vertical}] batch={batch_id}: "
            f"raw={stats.total_raw} unique={stats.unique_domains} "
            f"new={stats.written_new} skip={stats.written_skip} "
            f"blocked={stats.blocked_count} cost≈${stats.estimated_cost_usd:.3f}"
        )
        return stats

    async def _run_all_sources(
        self,
        cfg: dict,
        stats: DiscoveryStats,
        daily_budget_usd: float,
    ) -> list[dict]:
        """Run all 5 sources concurrently. Individual failures are caught and logged."""
        accumulated_cost = 0.0

        async def source_a() -> list[dict]:
            nonlocal accumulated_cost
            codes = cfg.get("category_codes", [])
            threshold = float(cfg.get("ad_spend_threshold", 0))
            if not codes:
                return []
            cost = COST_DOMAIN_METRICS_BY_CATEGORIES * len(codes)
            if accumulated_cost + cost > daily_budget_usd:
                logger.warning(f"Layer2 budget cap hit before source_a (would cost ${cost:.2f})")
                stats.budget_exceeded = True
                return []
            results = await self._dfs.domain_metrics_by_categories(
                category_codes=codes,
                paid_etv_min=threshold,
            )
            accumulated_cost += cost
            stats.estimated_cost_usd += cost
            stats.sources_used.append("domain_metrics_by_categories")
            return [{"domain": r["domain"], "dfs_paid_etv": r["paid_etv"]} for r in results]

        async def source_b() -> list[dict]:
            nonlocal accumulated_cost
            keywords = cfg.get("keywords_for_ads_search", [])
            if not keywords:
                return []
            cost = COST_ADS_SEARCH * len(keywords)
            if accumulated_cost + cost > daily_budget_usd:
                logger.warning("Layer2 budget cap hit before source_b")
                stats.budget_exceeded = True
                return []
            all_results = []
            for kw in keywords:
                results = await self._dfs.google_ads_advertisers(keyword=kw)
                all_results.extend([{"domain": r["domain"], "dfs_discovery_keyword": kw} for r in results])
            accumulated_cost += cost
            stats.estimated_cost_usd += cost
            stats.sources_used.append("google_ads_advertisers")
            return all_results

        async def source_c() -> list[dict]:
            nonlocal accumulated_cost
            combos = cfg.get("html_gap_combos", [])
            if not combos:
                return []
            cost = COST_HTML_TERMS * len(combos)
            if accumulated_cost + cost > daily_budget_usd:
                logger.warning("Layer2 budget cap hit before source_c")
                stats.budget_exceeded = True
                return []
            all_results = []
            for combo in combos:
                results = await self._dfs.domains_by_html_terms(
                    include_term=combo.get("has", ""),
                    exclude_term=combo.get("missing"),
                )
                all_results.extend([{"domain": r["domain"]} for r in results])
            accumulated_cost += cost
            stats.estimated_cost_usd += cost
            stats.sources_used.append("domains_by_html_terms")
            return all_results

        async def source_d() -> list[dict]:
            nonlocal accumulated_cost
            keywords = cfg.get("job_search_keywords", [])
            if not keywords:
                return []
            cost = COST_JOBS * len(keywords)
            if accumulated_cost + cost > daily_budget_usd:
                logger.warning("Layer2 budget cap hit before source_d")
                stats.budget_exceeded = True
                return []
            all_results = []
            for kw in keywords:
                results = await self._dfs.google_jobs_advertisers(keyword=kw)
                all_results.extend([{"domain": r["domain"], "dfs_discovery_keyword": kw} for r in results])
            accumulated_cost += cost
            stats.estimated_cost_usd += cost
            stats.sources_used.append("google_jobs_advertisers")
            return all_results

        async def source_e() -> list[dict]:
            nonlocal accumulated_cost
            if not cfg.get("competitor_expansion", False):
                return []
            # Get top BU domains from prior runs (pipeline_stage>=4, propensity>=50)
            prior_rows = await self._conn.fetch(
                "SELECT domain FROM business_universe "
                "WHERE pipeline_stage >= 4 AND propensity_score >= 50 "
                "AND domain IS NOT NULL LIMIT 20"
            )
            if not prior_rows:
                logger.info("Layer2 source_e: no prior BU data, skipping competitor expansion")
                return []
            cost = COST_COMPETITORS_DOMAIN * len(prior_rows)
            if accumulated_cost + cost > daily_budget_usd:
                logger.warning("Layer2 budget cap hit before source_e")
                stats.budget_exceeded = True
                return []
            all_results = []
            for row in prior_rows:
                competitors_result = await self._dfs.competitors_domain(target_domain=row["domain"])
                # competitors_domain returns {"items": [...]} not a plain list
                competitor_items = competitors_result.get("items", []) if isinstance(competitors_result, dict) else []
                all_results.extend([
                    {"domain": c.get("domain", "")}
                    for c in competitor_items
                    if c.get("domain")
                ])
            accumulated_cost += cost
            stats.estimated_cost_usd += cost
            stats.sources_used.append("competitors_domain")
            return all_results

        # Wrap each source to catch errors individually
        async def safe(coro_fn, name: str) -> list[dict]:
            try:
                return await coro_fn()
            except Exception as exc:
                logger.error(f"Layer2 source {name} failed: {exc}")
                stats.source_errors.append(f"{name}: {exc}")
                return []

        results = await asyncio.gather(
            safe(source_a, "source_a"),
            safe(source_b, "source_b"),
            safe(source_c, "source_c"),
            safe(source_d, "source_d"),
            safe(source_e, "source_e"),
        )
        return [item for sublist in results for item in sublist]

    async def _upsert_domain(
        self,
        domain: str,
        item: dict,
        batch_id: uuid.UUID,
    ) -> bool:
        """
        Insert domain into business_universe. Skip if domain already exists (idempotency).
        Returns True if new row written, False if skipped.
        """
        # Idempotency: check if domain already exists
        existing = await self._conn.fetchval(
            "SELECT id FROM business_universe WHERE domain = $1 LIMIT 1",
            domain,
        )
        if existing is not None:
            return False  # skip — already in BU

        await self._conn.execute(
            """
            INSERT INTO business_universe (
                domain,
                display_name,
                dfs_discovery_sources,
                discovery_batch_id,
                discovered_at,
                pipeline_stage,
                no_domain,
                dfs_discovery_keyword
            ) VALUES ($1, $2, $3, $4, NOW(), 1, false, $5)
            ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain <> ''
            DO NOTHING
            """,
            domain,
            item.get("display_name") or item.get("employer_name"),
            ["layer2"],
            batch_id,
            item.get("dfs_discovery_keyword"),
        )
        return True
