"""
Contract: src/pipeline/layer_2_discovery.py
Purpose: Layer 2 category-based domain discovery — single DFS source, sequential per-category
Layer: 4 - orchestration (uses asyncpg connection directly)
Imports: clients, enrichment, utils
Consumers: orchestration flows
Directive: #280

v7 design: single source (domain_metrics_by_categories), sequential per category code,
AU domain filter, blocklist, dedup, trajectory computation, writes to business_universe.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from urllib.parse import urlparse

import asyncpg
import httpx

from src.clients.dfs_labs_client import DFSLabsClient
from src.enrichment.signal_config import SignalConfigRepository
from src.utils.domain_blocklist import is_blocked

logger = logging.getLogger(__name__)


class DiscoverySource(str, Enum):
    DOMAIN_CATEGORIES = "domain_categories"
    MAPS_SERP = "maps_serp"


# pipeline_stage value for Layer 2 discoveries (matches Stage 1 convention)
PIPELINE_STAGE_DISCOVERED = 1

# Cost per domain_metrics_by_categories call (USD)
COST_PER_CATEGORY_CALL = Decimal("0.10")

# AU TLDs to keep unconditionally
_AU_TLDS = frozenset(
    {
        ".com.au",
        ".net.au",
        ".org.au",
        ".edu.au",
        ".id.au",
        ".asn.au",
    }
)

# Known foreign country-code TLDs to reject
_FOREIGN_TLDS = frozenset(
    {
        ".co.uk",
        ".co.nz",
        ".ca",
        ".ie",
        ".us",
        ".de",
        ".fr",
        ".co.in",
        ".co.za",
        ".co.jp",
        ".cn",
        ".nl",
        ".se",
        ".no",
        ".dk",
        ".fi",
        ".it",
        ".es",
        ".pt",
        ".ru",
        ".pl",
        ".com.br",
        ".com.mx",
        ".org.uk",
        ".me.uk",
    }
)


@dataclass
class DiscoveryStats:
    category_codes: list[int] = field(default_factory=list)
    domains_returned: int = 0
    domains_au_filtered: int = 0  # rejected by AU filter
    domains_blocked: int = 0  # rejected by blocklist
    domains_deduped: int = 0  # already in BU, skipped
    domains_inserted: int = 0  # new rows written
    cost_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    budget_exceeded: bool = False
    source_errors: list[str] = field(default_factory=list)
    # Trajectory counts (written to trajectory column in BU)
    trajectory_with_value: int = 0
    trajectory_none: int = 0


def _normalise_domain(url_or_domain: str) -> str:
    """Strip www., trailing slash, lowercase. Handle both URLs and bare domains."""
    s = url_or_domain.strip().lower()
    if s.startswith(("http://", "https://")):
        parsed = urlparse(s)
        s = parsed.netloc or s
    s = s.removeprefix("www.").rstrip("/")
    return s


def _is_au_domain(domain: str) -> bool:
    """
    Return True if domain is likely Australian.

    Keep: explicit .au TLDs (.com.au, .net.au, etc.)
    Keep: .com (assumed AU since returned from AU location query)
    Kill: known foreign country-code TLDs (.co.uk, .ca, .de, etc.)
    Keep: neutral TLDs (.io, .co, .net, .org) — no strong signal either way
    """
    d = domain.lower()
    for tld in _AU_TLDS:
        if d.endswith(tld):
            return True
    if d.endswith(".com"):
        return True
    return all(not d.endswith(tld) for tld in _FOREIGN_TLDS)  # neutral TLD — keep


def _compute_trajectory(organic_etv_current: float, organic_etv_prev: float | None) -> float | None:
    """
    Compute domain traffic trajectory from current vs previous organic ETV.

    Returns fractional change: (current - prev) / prev, e.g. 0.50 for +50%, -0.20 for -20%.
    Returns None if organic_etv_prev is None or <= 0.
    """
    if organic_etv_prev is None:
        return None
    if organic_etv_prev <= 0:
        return None
    return (organic_etv_current - organic_etv_prev) / organic_etv_prev


class Layer2Discovery:
    """
    Layer 2 of the v7 pipeline: category-based domain discovery using DFS.

    Reads category_codes from signal_configurations.discovery_config,
    calls domain_metrics_by_categories once per code (sequential, not parallel),
    applies AU filter + blocklist + dedup, and writes new rows to business_universe.

    Usage:
        engine = Layer2Discovery(conn, dfs_client)
        stats = await engine.run("marketing_agency")
    """

    def __init__(
        self,
        conn: asyncpg.Connection,
        dfs: DFSLabsClient,
        source: DiscoverySource = DiscoverySource.DOMAIN_CATEGORIES,
    ) -> None:
        self._conn = conn
        self._dfs = dfs
        self._source = source

    async def run(
        self,
        vertical_slug: str = "marketing_agency",
        batch_id: uuid.UUID | None = None,
        daily_budget_usd: float = 10.0,
    ) -> DiscoveryStats:
        """
        Run Layer 2 discovery for a vertical.

        Calls domain_metrics_by_categories once per category code (sequential).
        Applies AU filter, blocklist, dedup, then inserts new domains into BU.

        Args:
            vertical_slug: Vertical slug (e.g. "marketing_agency")
            batch_id: Optional batch UUID for tracking. Generated if not provided.
            daily_budget_usd: Stop if accumulated cost would exceed this (budget gate).

        Returns:
            DiscoveryStats with per-run counts and cost.
        """
        if self._source == DiscoverySource.MAPS_SERP:
            raise NotImplementedError("Maps SERP discovery not yet implemented — Sprint 5")

        run_id = batch_id or uuid.uuid4()
        stats = DiscoveryStats(run_id=run_id)

        # Load signal config
        config = await SignalConfigRepository(self._conn).get_config(vertical_slug)
        category_codes: list[int] = config.discovery_config.get("category_codes", [])
        stats.category_codes = category_codes

        if not category_codes:
            logger.warning(
                f"Layer2 [{vertical_slug}]: no category_codes in discovery_config, nothing to do"
            )
            return stats

        accumulated_cost = Decimal("0")

        # Sequential — one category at a time to avoid rate limits
        for code in category_codes:
            if accumulated_cost + COST_PER_CATEGORY_CALL > Decimal(str(daily_budget_usd)):
                logger.warning(
                    f"Layer2 [{vertical_slug}]: budget gate hit at ${accumulated_cost:.3f} "
                    f"(limit=${daily_budget_usd}), stopping after {stats.domains_inserted} inserts"
                )
                stats.budget_exceeded = True
                break

            try:
                results = await self._dfs.domain_metrics_by_categories(
                    category_codes=[code],
                    location_name="Australia",
                    paid_etv_min=0.0,
                )
            except (httpx.HTTPStatusError, ValueError) as exc:
                # API errors (4xx/5xx) and explicit protocol errors must propagate
                logger.error(
                    f"Layer2 [{vertical_slug}] category={code} DFS API error: {exc}\n"
                    f"{traceback.format_exc()}"
                )
                raise
            except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
                # Timeouts are expected and non-fatal — log and skip this category
                logger.warning(
                    f"Layer2 [{vertical_slug}] category={code} DFS timeout: {exc}"
                )
                stats.source_errors.append(f"category={code}: timeout: {exc}")
                continue
            except Exception as exc:
                # Unexpected errors — log full traceback and continue (do not abort run)
                logger.error(
                    f"Layer2 [{vertical_slug}] category={code} DFS unexpected error: {exc}\n"
                    f"{traceback.format_exc()}"
                )
                stats.source_errors.append(f"category={code}: {exc}")
                continue

            accumulated_cost += COST_PER_CATEGORY_CALL
            stats.cost_usd += COST_PER_CATEGORY_CALL
            stats.domains_returned += len(results)

            for item in results:
                raw_domain = item.get("domain", "")
                domain = _normalise_domain(raw_domain)
                if not domain:
                    continue

                # AU filter
                if not _is_au_domain(domain):
                    stats.domains_au_filtered += 1
                    continue

                # Blocklist check
                if is_blocked(domain):
                    stats.domains_blocked += 1
                    continue

                # Dedup: skip if domain already in BU
                existing = await self._conn.fetchval(
                    "SELECT 1 FROM business_universe WHERE domain = $1 LIMIT 1",
                    domain,
                )
                if existing is not None:
                    stats.domains_deduped += 1
                    continue

                # Trajectory computation — written to trajectory column in BU
                organic_etv_current = float(item.get("organic_etv") or 0)
                organic_etv_prev = item.get("organic_etv_prev")
                trajectory = _compute_trajectory(organic_etv_current, organic_etv_prev)
                if trajectory is not None:
                    stats.trajectory_with_value += 1
                else:
                    stats.trajectory_none += 1

                # Insert new domain
                await self._conn.execute(
                    """
                    INSERT INTO business_universe (
                        domain,
                        pipeline_stage,
                        pipeline_status,
                        discovery_source,
                        discovery_batch_id,
                        discovered_at,
                        dfs_discovery_category,
                        dfs_organic_etv,
                        dfs_paid_etv,
                        dfs_discovery_sources,
                        no_domain,
                        trajectory
                    ) VALUES ($1, $2, $3, $4, $5, NOW(), $6, $7, $8, $9, false, $10)
                    ON CONFLICT (domain) WHERE domain IS NOT NULL AND domain <> ''
                    DO NOTHING
                    """,
                    domain,
                    PIPELINE_STAGE_DISCOVERED,
                    "discovered",
                    "dfs_categories",
                    run_id,
                    str(code),
                    organic_etv_current,
                    float(item.get("paid_etv") or 0),
                    ["layer2"],
                    trajectory,
                )
                stats.domains_inserted += 1

        logger.info(
            f"Layer2 [{vertical_slug}] run={run_id}: "
            f"returned={stats.domains_returned} au_filtered={stats.domains_au_filtered} "
            f"blocked={stats.domains_blocked} deduped={stats.domains_deduped} "
            f"inserted={stats.domains_inserted} cost=${stats.cost_usd} "
            f"trajectory: with_value={stats.trajectory_with_value} none={stats.trajectory_none}"
        )

        # Auto-apply Gate 1 after all inserts
        gate_result = await self.apply_gate_1(run_id)
        logger.info(
            f"Layer2 [{vertical_slug}] Gate 1 result: "
            f"filtered_budget={gate_result['filtered_budget']} "
            f"filtered_organic={gate_result['filtered_organic']} "
            f"passed={gate_result['passed']}"
        )

        return stats

    async def apply_gate_1(self, batch_id: uuid.UUID) -> dict:
        """
        Gate 1: post-insert quality filters on newly discovered domains.

        Queries business_universe rows for this batch at pipeline_stage=1 and applies:
        - Budget floor: dfs_paid_traffic_cost < 1000 AND NOT NULL
          → pipeline_stage=-1, filter_reason='below_budget_floor'
          (NULL dfs_paid_traffic_cost skips this check)
        - No organic signal: dfs_organic_etv=0 AND dfs_organic_keywords=0
          → pipeline_stage=-1, filter_reason='no_organic_signal'

        Returns:
            {"filtered_budget": N, "filtered_organic": N, "passed": N}
        """
        r_budget = await self._conn.execute(
            """
            UPDATE business_universe
            SET pipeline_stage = -1, filter_reason = 'below_budget_floor'
            WHERE discovery_batch_id = $1
              AND pipeline_stage = 1
              AND dfs_paid_traffic_cost IS NOT NULL
              AND dfs_paid_traffic_cost < 1000
            """,
            batch_id,
        )
        filtered_budget = int(r_budget.split()[-1]) if isinstance(r_budget, str) else 0

        r_organic = await self._conn.execute(
            """
            UPDATE business_universe
            SET pipeline_stage = -1, filter_reason = 'no_organic_signal'
            WHERE discovery_batch_id = $1
              AND pipeline_stage = 1
              AND (dfs_organic_etv IS NULL OR dfs_organic_etv = 0)
              AND (dfs_organic_keywords IS NULL OR dfs_organic_keywords = 0)
            """,
            batch_id,
        )
        filtered_organic = int(r_organic.split()[-1]) if isinstance(r_organic, str) else 0

        passed = (
            await self._conn.fetchval(
                """
            SELECT COUNT(*) FROM business_universe
            WHERE discovery_batch_id = $1 AND pipeline_stage = 1
            """,
                batch_id,
            )
            or 0
        )

        logger.info(
            f"Gate 1 batch={batch_id}: filtered_budget={filtered_budget} "
            f"filtered_organic={filtered_organic} passed={passed}"
        )
        return {
            "filtered_budget": filtered_budget,
            "filtered_organic": filtered_organic,
            "passed": int(passed),
        }

    async def pull_batch(
        self,
        category_code: str,
        location: str = "Australia",
        limit: int = 50,
        offset: int = 0,
        etv_min: float | None = None,
        etv_max: float | None = None,
    ) -> list[dict]:
        """
        Stateless batch pull for pipeline orchestration.
        Does NOT write to DB. Does NOT apply blocklist/dedup.
        Returns list of {"domain": str, "organic_etv": float}.
        Used by PipelineOrchestrator.run(). Distinct from run() which reads
        signal_configurations and writes to BU.
        etv_min/etv_max required — use get_etv_window() from
        src.config.category_etv_windows.
        """
        if etv_min is None or etv_max is None:
            raise ValueError(
                "ETV window required. Use get_etv_window(category_code) from "
                "src.config.category_etv_windows to look up the canonical window."
            )
        # DO NOT pass explicit first_date/second_date here.
        # DFSLabsClient._get_latest_available_date() resolves the correct
        # date window dynamically. Hardcoding date.today() caused a regression
        # (#304 / #317.3) — DFS silently returns empty results for future dates.
        # Directive #317.3: deleted hardcoded dates, added regression test.

        try:
            code_int = int(category_code)
        except (ValueError, TypeError):
            logger.warning("pull_batch: invalid category_code %r", category_code)
            return []

        try:
            results = await self._dfs.domain_metrics_by_categories(
                category_codes=[code_int],
                location_name=location,
                paid_etv_min=0.0,
            )
        except Exception as exc:
            logger.error("pull_batch: DFS error category=%s offset=%d: %s", category_code, offset, exc)
            return []

        filtered = [
            {"domain": r["domain"], "organic_etv": r.get("organic_etv", 0.0)}
            for r in results
            if etv_min <= r.get("organic_etv", 0.0) <= etv_max
        ]
        return filtered[offset: offset + limit]

    async def run_batch(
        self,
        vertical_slugs: list[str],
    ) -> dict[str, DiscoveryStats]:
        """
        Run Layer 2 discovery for multiple verticals sequentially.

        Returns:
            dict mapping vertical_slug → DiscoveryStats
        """
        results: dict[str, DiscoveryStats] = {}
        for slug in vertical_slugs:
            results[slug] = await self.run(slug)
        return results
