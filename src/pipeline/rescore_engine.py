"""
Contract: src/pipeline/rescore_engine.py
Purpose: Monthly re-score of pipeline_stage=-1 rejects against current signal configs.
         Promotes qualifying leads back to pipeline_stage=1 for re-enrichment.
Layer: 4 - orchestration
Imports: src.enrichment.signal_config, src.pipeline.stage_4_scoring
Consumers: src/orchestration/flows/rescore_flow.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import asyncpg

from src.enrichment.signal_config import SignalConfigRepository
from src.pipeline.stage_4_scoring import _calc_budget_score, _calc_pain_score

logger = logging.getLogger(__name__)

DEFAULT_RESCORE_THRESHOLD = 15


@dataclass
class RescoreResult:
    total_evaluated: int
    promoted: int
    still_rejected: int
    skipped: int
    dry_run: bool
    vertical: str | None
    estimated_cost_usd: float = field(default=0.0)


class RescoreEngine:
    """
    Monthly re-score engine for pipeline_stage=-1 rejects.

    Re-evaluates rejected leads against current signal configs and promotes
    those that now pass the combined budget+pain threshold back to stage 1.
    """

    def __init__(self, conn: asyncpg.Connection) -> None:
        self.conn = conn

    async def run(
        self,
        vertical: str | None = None,
        batch_size: int = 500,
        dry_run: bool = False,
    ) -> RescoreResult:
        """
        Re-score pipeline_stage=-1 rejects and promote qualifying leads.

        Args:
            vertical: Vertical slug to load signal config threshold from.
                      None = use default threshold, process all verticals.
            batch_size: Maximum rows to evaluate per run.
            dry_run: If True, compute scores but make no DB writes.

        Returns:
            RescoreResult with counts of promoted/rejected/skipped rows.
        """
        threshold = await self._load_threshold(vertical)
        self._threshold = threshold

        rows = await self._fetch_rejects(vertical, batch_size)

        promoted = 0
        still_rejected = 0
        skipped = 0

        for row in rows:
            outcome = await self._rescore_row(row)

            if outcome == "promoted":
                if not dry_run:
                    await self._promote(str(row["id"]))
                promoted += 1
            elif outcome == "still_rejected":
                if not dry_run:
                    await self._mark_rescored(str(row["id"]))
                still_rejected += 1
            else:
                skipped += 1

        total_evaluated = promoted + still_rejected + skipped

        logger.info(
            f"Rescore complete (dry_run={dry_run}): "
            f"evaluated={total_evaluated}, promoted={promoted}, "
            f"still_rejected={still_rejected}, skipped={skipped}"
        )

        return RescoreResult(
            total_evaluated=total_evaluated,
            promoted=promoted,
            still_rejected=still_rejected,
            skipped=skipped,
            dry_run=dry_run,
            vertical=vertical,
        )

    async def _load_threshold(self, vertical: str | None) -> int:
        """Load promotion threshold from signal config, or return default."""
        if vertical is None:
            return DEFAULT_RESCORE_THRESHOLD

        try:
            repo = SignalConfigRepository(self.conn)
            config = await repo.get_config(vertical)
            return int(config.enrichment_gates.get("min_rescore_threshold", DEFAULT_RESCORE_THRESHOLD))
        except Exception as exc:
            logger.warning(
                f"Could not load signal config for vertical '{vertical}': {exc}. "
                f"Using default threshold {DEFAULT_RESCORE_THRESHOLD}."
            )
            return DEFAULT_RESCORE_THRESHOLD

    async def _fetch_rejects(
        self,
        vertical: str | None,
        batch_size: int,
    ) -> list[asyncpg.Record]:
        """Fetch pipeline_stage=-1 rows eligible for re-scoring."""
        rows = await self.conn.fetch(
            """
            SELECT id, domain, gmb_category, gmb_rating, gmb_review_count,
                   dfs_organic_etv, dfs_paid_etv, backlinks_count,
                   filter_reason, pipeline_stage, updated_at
            FROM business_universe
            WHERE pipeline_stage = -1
              AND filter_reason != 'au_domain_filter'
              AND (last_rescored_at IS NULL OR last_rescored_at < NOW() - INTERVAL '30 days')
            ORDER BY updated_at ASC
            LIMIT $1
            """,
            batch_size,
        )
        return list(rows)

    async def _rescore_row(self, row: asyncpg.Record) -> str:
        """
        Evaluate a single reject row against current thresholds.

        Returns:
            "promoted"       — score >= threshold, ready for re-enrichment
            "still_rejected" — score below threshold, not yet ready
            "skip"           — au_domain_filter or other permanent disqualifier
        """
        # Defensive guard: never promote au_domain_filter rejects
        if row["filter_reason"] == "au_domain_filter":
            return "skip"

        paid_kw = 0  # Not in select — default to 0 for re-score
        paid_etv = float(row["dfs_paid_etv"] or 0)
        organic_etv = float(row["dfs_organic_etv"] or 0)
        gmb_rating = float(row["gmb_rating"] or 0)
        gmb_reviews = int(row["gmb_review_count"] or 0)

        budget_score = _calc_budget_score(paid_kw, paid_etv, organic_etv, gmb_rating=gmb_rating)
        pain_score = _calc_pain_score(gmb_rating, gmb_reviews, gap_count=0)
        combined = budget_score + pain_score

        if combined >= self._threshold:
            return "promoted"
        return "still_rejected"

    async def _promote(self, bu_id: str) -> None:
        """Reset stage to 1 and clear filter_reason so lead re-enters enrichment."""
        await self.conn.execute(
            """
            UPDATE business_universe
            SET pipeline_stage = 1,
                filter_reason = NULL,
                last_rescored_at = NOW()
            WHERE id = $1
            """,
            bu_id,
        )

    async def _mark_rescored(self, bu_id: str) -> None:
        """Update last_rescored_at without changing pipeline_stage."""
        await self.conn.execute(
            """
            UPDATE business_universe
            SET last_rescored_at = NOW()
            WHERE id = $1
            """,
            bu_id,
        )
