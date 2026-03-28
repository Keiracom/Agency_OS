"""
Contract: src/pipeline/layer_3_bulk_filter.py
Purpose: Layer 3 Bulk Filter — reads pipeline_stage=1 domains, calls DFS Bulk Domain Metrics
         in batches of 1000, applies thresholds, advances PASS to stage 2, rejects to stage -1.
Layer: 4 - orchestration (uses asyncpg connection directly)
Imports: clients, enrichment
Consumers: orchestration flows
Directive: #274

v6 design: cheapest possible gate before spending real money in Layer 4.
Cost: $0.10/task + $0.001/domain = $1.10 per 1,000 domains (DFS Historical Bulk Traffic Estimation).
1,500 domains = 2 batches = ~$2.20. Still 20x cheaper than individual domain_rank_overview ($0.02/domain).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import asyncpg

from src.clients.dfs_labs_client import DFSLabsClient
from src.enrichment.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000
DEFAULT_MIN_ORGANIC_ETV = 0.0     # any organic traffic = alive
DEFAULT_MIN_PAID_ETV = 0.0        # any paid spend = alive
DEFAULT_MIN_BACKLINKS = 5         # minimum backlinks to not be parked
DEFAULT_MAX_BATCH_COST_USD = 50.0  # hard stop (DFS $50/day cap)


@dataclass
class FilterStats:
    total_processed: int = 0
    passed: int = 0
    rejected: int = 0
    no_domain_advanced: int = 0   # no_domain rows passed through without API call
    batches_called: int = 0
    estimated_cost_usd: float = 0.0
    budget_exceeded: bool = False
    errors: list[str] = field(default_factory=list)


class Layer3BulkFilter:
    """
    Layer 3: Bulk Domain Metrics cheap filter.

    Reads pipeline_stage=1 domains from business_universe, batches them into
    groups of up to 1000, calls DFS Bulk Domain Metrics, applies configurable
    thresholds to pass/reject each domain.

    Usage:
        engine = Layer3BulkFilter(conn, dfs_client)
        stats = await engine.run("marketing_agency")
    """

    def __init__(self, conn: asyncpg.Connection, dfs: DFSLabsClient) -> None:
        self._conn = conn
        self._dfs = dfs

    async def run(
        self,
        vertical: str,
        daily_budget_usd: float = DEFAULT_MAX_BATCH_COST_USD,
    ) -> FilterStats:
        stats = FilterStats()

        # Load thresholds from signal config
        config = await SignalConfigRepository(self._conn).get_config(vertical)
        gates = config.enrichment_gates
        min_organic = float(gates.get("l3_min_organic_etv", DEFAULT_MIN_ORGANIC_ETV))
        min_paid = float(gates.get("l3_min_paid_etv", DEFAULT_MIN_PAID_ETV))
        min_backlinks = int(gates.get("l3_min_backlinks", DEFAULT_MIN_BACKLINKS))

        # 1. Advance no_domain rows (skip filter — go straight to pipeline_stage=2)
        no_domain_result = await self._conn.execute(
            """
            UPDATE business_universe
            SET pipeline_stage = 2, updated_at = NOW()
            WHERE pipeline_stage = 1 AND no_domain = true
            """
        )
        # Parse "UPDATE N" response
        no_domain_count = int(no_domain_result.split()[-1]) if no_domain_result else 0
        stats.no_domain_advanced = no_domain_count
        if no_domain_count:
            logger.info(f"Layer3: advanced {no_domain_count} no-domain rows to stage 2")

        # 2. Fetch all pipeline_stage=1 domains
        rows = await self._conn.fetch(
            """
            SELECT id, domain FROM business_universe
            WHERE pipeline_stage = 1
              AND no_domain = false
              AND domain IS NOT NULL
              AND domain <> ''
            ORDER BY discovered_at ASC
            """
        )

        if not rows:
            logger.info("Layer3: no pipeline_stage=1 domains to process")
            return stats

        # 3. Process in batches
        domains_all = [row["domain"] for row in rows]
        id_by_domain = {row["domain"]: row["id"] for row in rows}
        stats.total_processed = len(domains_all)

        accumulated_cost = 0.0
        for i in range(0, len(domains_all), BATCH_SIZE):
            batch = domains_all[i:i + BATCH_SIZE]
            batch_cost = 0.10 + len(batch) * 0.001  # $0.10/task + $0.001/domain (DFS bulk_traffic_estimation)

            if accumulated_cost + batch_cost > daily_budget_usd:
                logger.warning(
                    f"Layer3: budget cap hit at batch {stats.batches_called + 1}. "
                    f"Accumulated: ${accumulated_cost:.3f}, would add ${batch_cost:.3f}"
                )
                stats.budget_exceeded = True
                break

            try:
                metrics_list = await self._dfs.bulk_domain_metrics(domains=batch)
                stats.batches_called += 1
                accumulated_cost += batch_cost
                stats.estimated_cost_usd += batch_cost

                # Build metrics lookup
                metrics_by_domain = {m["domain"]: m for m in metrics_list}

                # Apply thresholds and update BU
                for domain in batch:
                    m = metrics_by_domain.get(domain, {})
                    organic_etv = m.get("organic_etv", 0.0)
                    paid_etv = m.get("paid_etv", 0.0)
                    backlinks = m.get("backlinks_count", 0)
                    domain_rank = m.get("domain_rank", 0)

                    passes = (
                        organic_etv > min_organic
                        or paid_etv > min_paid
                        or backlinks >= min_backlinks
                    )

                    domain_id = id_by_domain.get(domain)
                    if not domain_id:
                        continue

                    if passes:
                        await self._conn.execute(
                            """
                            UPDATE business_universe SET
                                pipeline_stage = 2,
                                dfs_organic_etv = COALESCE($2, dfs_organic_etv),
                                dfs_paid_etv = COALESCE($3, dfs_paid_etv),
                                backlinks_count = $4,
                                domain_rank = $5,
                                updated_at = NOW()
                            WHERE id = $1
                            """,
                            domain_id,
                            organic_etv if organic_etv > 0 else None,
                            paid_etv if paid_etv > 0 else None,
                            backlinks if backlinks > 0 else None,
                            domain_rank if domain_rank > 0 else None,
                        )
                        stats.passed += 1
                    else:
                        await self._conn.execute(
                            """
                            UPDATE business_universe SET
                                pipeline_stage = -1,
                                filter_reason = $2,
                                dfs_organic_etv = COALESCE($3, dfs_organic_etv),
                                dfs_paid_etv = COALESCE($4, dfs_paid_etv),
                                backlinks_count = $5,
                                domain_rank = $6,
                                updated_at = NOW()
                            WHERE id = $1
                            """,
                            domain_id,
                            "bulk_metrics_below_threshold",
                            organic_etv if organic_etv > 0 else None,
                            paid_etv if paid_etv > 0 else None,
                            backlinks if backlinks > 0 else None,
                            domain_rank if domain_rank > 0 else None,
                        )
                        stats.rejected += 1

            except Exception as exc:
                logger.error(f"Layer3: batch {stats.batches_called + 1} failed: {exc}")
                stats.errors.append(str(exc))

        logger.info(
            f"Layer3 [{vertical}]: processed={stats.total_processed} "
            f"passed={stats.passed} rejected={stats.rejected} "
            f"no_domain={stats.no_domain_advanced} "
            f"cost≈${stats.estimated_cost_usd:.4f}"
        )
        return stats
