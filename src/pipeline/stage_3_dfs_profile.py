"""
Stage 3 DFS Rank + Technology Profile — Architecture v5
Directive #261

Takes S2-completed domains (pipeline_stage=2), pulls full digital
profile via DFS Labs: domain rank/traffic signals + complete tech stack.

Calculates tech_gaps: technologies from signal_config that the business
does NOT have (gap score input for S4).

Enriches ONLY. No scoring, no DM discovery, no outreach.
Cost: ~$0.03/business (rank $0.01 + tech $0.01-0.02).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import asyncpg

from src.clients.dfs_labs_client import DFSLabsClient
from src.enrichment.signal_config import SignalConfigRepository

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S3 = 3
COST_PER_DOMAIN_USD = 0.03  # rank ($0.01) + tech ($0.01-0.02)


class Stage3DFSProfile:
    """
    DFS digital profile enrichment for S2-completed domains.

    Usage:
        stage = Stage3DFSProfile(dfs_client, signal_repo, conn)
        result = await stage.run(vertical_slug="marketing_agency", batch_size=50)
    """

    def __init__(
        self,
        dfs_client: DFSLabsClient,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
        delay: float = 0.2,
    ) -> None:
        self.dfs = dfs_client
        self.signal_repo = signal_repo
        self.conn = conn
        self.delay = delay

    async def run(
        self,
        vertical_slug: str,
        batch_size: int = 50,
    ) -> dict[str, Any]:
        """
        Profile all S2-completed domains for a vertical.
        Returns {profiled, api_errors, cost_usd, cost_aud}
        """
        config = await self.signal_repo.get_config(vertical_slug)
        signal_technologies = set(config.all_dfs_technologies)

        rows = await self.conn.fetch(
            """
            SELECT id, domain
            FROM business_universe
            WHERE pipeline_stage = 2
            AND domain IS NOT NULL AND domain <> ''
            AND domain LIKE '%.au'
            ORDER BY pipeline_updated_at ASC
            LIMIT $1
            """,
            batch_size,
        )

        profiled = 0
        errors = 0

        for row in rows:
            # BUG-265-2: skip NULL/empty domain rows — do NOT call DFS
            if not row["domain"]:
                logger.warning(f"Stage 3: skipping NULL domain for row {row['id']}")
                continue
            try:
                await self._profile_domain(
                    row_id=row["id"],
                    domain=row["domain"],
                    signal_technologies=signal_technologies,
                )
                profiled += 1
            except Exception as e:
                logger.error(f"Stage 3 error for {row['domain']}: {e}")
                errors += 1
            if self.delay > 0:
                await asyncio.sleep(self.delay)

        cost_usd = float(self.dfs.total_cost_usd)
        result = {
            "profiled": profiled,
            "api_errors": errors,
            "cost_usd": cost_usd,
            "cost_aud": round(cost_usd * 1.55, 4),
        }
        logger.info(f"Stage 3 complete: {result}")
        return result

    async def _profile_domain(
        self,
        row_id: str,
        domain: str,
        signal_technologies: set[str],
    ) -> None:
        """Pull rank + tech data for a single domain and update BU."""
        now = datetime.now(UTC)

        # Call both endpoints concurrently
        rank_data, tech_data = await asyncio.gather(
            self.dfs.domain_rank_overview(domain),
            self.dfs.domain_technologies(domain),
            return_exceptions=True,
        )

        # Handle exceptions from gather
        if isinstance(rank_data, Exception):
            logger.warning(f"Rank overview failed for {domain}: {rank_data}")
            rank_data = None
        if isinstance(tech_data, Exception):
            logger.warning(f"Technologies failed for {domain}: {tech_data}")
            tech_data = None

        # Build update dict — start with what we always set
        update: dict[str, Any] = {
            "pipeline_stage": PIPELINE_STAGE_S3,
            "pipeline_updated_at": now,
            "dfs_rank_fetched_at": now if rank_data is not None else None,
            "dfs_tech_fetched_at": now if tech_data is not None else None,
        }

        # Rank fields (all nullable — small businesses may not rank)
        if rank_data:
            update.update(
                {
                    "dfs_organic_etv": rank_data.get("dfs_organic_etv"),
                    "dfs_paid_etv": rank_data.get("dfs_paid_etv"),
                    "dfs_organic_keywords": rank_data.get("dfs_organic_keywords"),
                    "dfs_paid_keywords": rank_data.get("dfs_paid_keywords"),
                    "dfs_organic_pos_1": rank_data.get("dfs_organic_pos_1"),
                    "dfs_organic_pos_2_3": rank_data.get("dfs_organic_pos_2_3"),
                    "dfs_organic_pos_4_10": rank_data.get("dfs_organic_pos_4_10"),
                    "dfs_organic_pos_11_20": rank_data.get("dfs_organic_pos_11_20"),
                }
            )

        # Tech fields
        if tech_data:
            tech_stack: list[str] = tech_data.get("tech_stack") or []
            update.update(
                {
                    "tech_stack": tech_stack,
                    "tech_categories": tech_data.get("tech_categories"),
                    "tech_stack_depth": tech_data.get("tech_stack_depth") or len(tech_stack),
                    "tech_gaps": self._calculate_tech_gaps(tech_stack, signal_technologies),
                }
            )

        await self._write_update(row_id, update)

    def _calculate_tech_gaps(
        self,
        detected_tech: list[str],
        signal_technologies: set[str],
    ) -> list[str]:
        """
        Technologies from signal_config that the business does NOT have.
        These are the gaps S4 uses to score outreach angle quality.
        """
        detected_set = {t.lower() for t in detected_tech}
        return [tech for tech in sorted(signal_technologies) if tech.lower() not in detected_set]

    async def _write_update(self, row_id: str, update: dict[str, Any]) -> None:
        """Write all non-None fields to BU in a single UPDATE."""
        # Build SET clause dynamically from non-None keys
        # Always set pipeline_stage and pipeline_updated_at
        always_set = {"pipeline_stage", "pipeline_updated_at"}
        fields = {k: v for k, v in update.items() if v is not None or k in always_set}

        if not fields:
            return

        cols = list(fields.keys())
        vals = list(fields.values())
        set_clause = ", ".join(f"{col} = ${i + 1}" for i, col in enumerate(cols))
        vals.append(row_id)

        await self.conn.execute(
            f"UPDATE business_universe SET {set_clause} WHERE id = ${len(vals)}",
            *vals,
        )
