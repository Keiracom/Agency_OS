"""
Stage 4 Scoring Engine — Architecture v5
Directive #262

Scores S3-profiled businesses on two dimensions:
- Propensity: quality of fit for the agency's services
- Reachability: breadth of channels available to reach them

Propensity is computed per service signal in the config.
The highest-scoring service determines the outreach angle for S7.
S4 is the budget gate — only high-propensity businesses progress to S5.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import asyncpg

from src.enrichment.signal_config import ServiceSignal, SignalConfig, SignalConfigRepository
from src.utils.domain_blocklist import is_blocked

logger = logging.getLogger(__name__)

PIPELINE_STAGE_S4 = 4


def _normalise_category(s: str | None) -> str:
    """Normalise a category string for comparison: lowercase, spaces→underscores."""
    if not s:
        return ""
    return re.sub(r"[\s\-]+", "_", s.strip().lower())


class Stage4Scorer:
    """
    Propensity + Reachability scorer for S3-profiled businesses.

    Usage:
        scorer = Stage4Scorer(signal_repo, conn)
        result = await scorer.run(vertical_slug="marketing_agency", batch_size=100)
    """

    def __init__(
        self,
        signal_repo: SignalConfigRepository,
        conn: asyncpg.Connection,
    ) -> None:
        self.signal_repo = signal_repo
        self.conn = conn

    async def run(
        self,
        vertical_slug: str,
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """
        Score all S3-completed businesses for a vertical.
        Returns {scored, above_threshold, below_threshold}
        """
        config = await self.signal_repo.get_config(vertical_slug)
        gate = config.enrichment_gates.get("min_score_to_enrich", 30)

        rows = await self.conn.fetch(
            """
            SELECT id, domain, gmb_category, gmb_rating, gmb_review_count,
                   gmb_place_id, phone, address, state, suburb, linkedin_company_url,
                   dfs_paid_keywords, dfs_paid_etv, dfs_organic_etv,
                   dfs_organic_keywords, tech_stack, tech_gaps,
                   tech_stack_depth, tech_categories, dfs_technologies
            FROM business_universe
            WHERE pipeline_stage = 3
            ORDER BY pipeline_updated_at ASC
            LIMIT $1
            """,
            batch_size,
        )

        scored = above = below = 0

        for row in rows:
            business = dict(row)

            # Pre-scoring qualification gate — answers "should we score this?"
            qualified, disqualify_reason = self._qualifies(business, config)
            if not qualified:
                await self._write_scores(
                    row_id=business["id"],
                    propensity=0,
                    reachability=0,
                    dim_scores={},
                    best_service=None,
                    reason=disqualify_reason,
                )
                scored += 1
                below += 1
                continue

            propensity, best_service, dim_scores = self._score_propensity(
                business, config
            )
            reachability = self._score_reachability(business)
            reason = self._generate_reason(business, best_service, dim_scores)

            await self._write_scores(
                row_id=business["id"],
                propensity=propensity,
                reachability=reachability,
                dim_scores=dim_scores,
                best_service=best_service.service_name if best_service else None,
                reason=reason,
            )
            scored += 1
            if propensity >= gate:
                above += 1
            else:
                below += 1

        return {"scored": scored, "above_threshold": above, "below_threshold": below}

    def _qualifies(
        self,
        business: dict,
        config: SignalConfig,
    ) -> tuple[bool, str]:
        """
        Pre-scoring qualification gate.
        Answers: "should we score this business at all?"

        Returns (True, "") if qualified.
        Returns (False, reason) if disqualified — business scores 0 and never reaches S5.

        Criteria (ALL must pass):
        1. Domain is not NULL, not empty, and not a blocked platform domain
        2. Has GMB listing (gmb_place_id) OR physical location (state/suburb)
        3. Has at least one DFS/tech signal column populated
        4. GMB category matches at least one category in the vertical's signal config
        """
        # 1. Domain check
        domain = business.get("domain") or ""
        if not domain or is_blocked(domain):
            return False, f"Does not meet qualification criteria: invalid or blocked domain ({domain!r})"

        # 2. Physical presence check
        has_gmb = bool(business.get("gmb_place_id"))
        has_address = bool(business.get("state") or business.get("suburb"))
        if not has_gmb and not has_address:
            return False, "Does not meet qualification criteria: no GMB listing and no physical address"

        # 3. At least one signal column populated
        signal_cols = [
            "dfs_paid_keywords", "dfs_paid_etv", "dfs_organic_etv",
            "dfs_organic_keywords", "tech_stack", "tech_stack_depth",
        ]
        has_signals = any(
            business.get(col) not in (None, 0, [], "")
            for col in signal_cols
        )
        if not has_signals:
            return False, "Does not meet qualification criteria: no DFS or technology signal data"

        # 4. GMB category matches vertical
        gmb_cat = _normalise_category(business.get("gmb_category"))
        if gmb_cat:
            all_cats = {_normalise_category(c) for c in config.all_gmb_categories}
            if all_cats and gmb_cat not in all_cats:
                return False, f"Does not meet qualification criteria: GMB category '{gmb_cat}' not in vertical"

        return True, ""

    def _score_propensity(
        self,
        business: dict,
        config: SignalConfig,
    ) -> tuple[int, ServiceSignal | None, dict[str, int]]:
        """
        Score propensity per service signal; return best match.
        Returns (score, winning_service, dimension_scores_for_winner)
        """
        best_score = -1
        best_service: ServiceSignal | None = None
        best_dims: dict[str, int] = {}

        for svc in config.service_signals:
            dims = self._score_dimensions(business, svc)
            weights = svc.scoring_weights
            composite = (
                dims["budget"] * weights.get("budget", 0)
                + dims["pain"] * weights.get("pain", 0)
                + dims["gap"] * weights.get("gap", 0)
                + dims["fit"] * weights.get("fit", 0)
            ) // 100
            composite = max(0, min(100, composite))
            if composite > best_score:
                best_score = composite
                best_service = svc
                best_dims = dims

        return best_score, best_service, best_dims

    def _score_dimensions(
        self,
        business: dict,
        svc: ServiceSignal,
    ) -> dict[str, int]:
        """
        Compute raw 0-100 scores for budget, pain, gap, fit dimensions.
        Inputs used per dimension are documented; scoring logic is proprietary.
        """
        # BUG-265-3: preserve None vs empty-list distinction for tech data
        tech_stack_raw = business.get("tech_stack")
        has_tech_data = tech_stack_raw is not None  # None = never fetched, [] = fetched but empty
        tech_stack: list[str] = list(tech_stack_raw or [])
        tech_stack_lower = {t.lower() for t in tech_stack}
        tech_gaps: list[str] = list(business.get("tech_gaps") or [])

        # Budget dimension: signals indicating the business spends on digital
        paid_kw = business.get("dfs_paid_keywords") or 0
        paid_etv = float(business.get("dfs_paid_etv") or 0)
        organic_etv = float(business.get("dfs_organic_etv") or 0)
        gmb_rating = float(business.get("gmb_rating") or 0)
        budget_score = _calc_budget_score(paid_kw, paid_etv, organic_etv, gmb_rating=gmb_rating)

        # Pain dimension: signals indicating visible business problems
        gmb_rating = float(business.get("gmb_rating") or 0)
        gmb_reviews = int(business.get("gmb_review_count") or 0)
        gap_count = len(tech_gaps)
        pain_score = _calc_pain_score(gmb_rating, gmb_reviews, gap_count)

        # Gap dimension: specific technology gaps matching this service's signals
        svc_techs_lower = {t.lower() for t in (svc.dfs_technologies or [])}
        svc_gaps_lower = {t.lower() for t in tech_gaps}
        gap_score = _calc_gap_score(svc_techs_lower, tech_stack_lower, svc_gaps_lower, has_tech_data=has_tech_data)

        # Fit dimension: alignment between business profile and service signals
        gmb_cat = _normalise_category(business.get("gmb_category"))
        svc_cats = {_normalise_category(c) for c in (svc.gmb_categories or [])}
        fit_score = _calc_fit_score(gmb_cat, svc_cats, svc_techs_lower, tech_stack_lower)

        return {
            "budget": budget_score,
            "pain": pain_score,
            "gap": gap_score,
            "fit": fit_score,
        }

    def _score_reachability(self, business: dict) -> int:
        """
        Score reachability based on confirmed channel access.
        Channels recalculated after S5/S6 as more data arrives.
        """
        score = 0
        if business.get("domain"):
            score += 30
        if business.get("phone"):
            score += 25
        if business.get("linkedin_company_url"):
            score += 20
        if business.get("address"):
            score += 15
        if business.get("gmb_place_id"):
            score += 10
        return min(score, 100)

    def _generate_reason(
        self,
        business: dict,
        best_service: ServiceSignal | None,
        dim_scores: dict[str, int],
    ) -> str:
        """
        Generate a plain-English reason for the score. Max 2 sentences.
        Describes what was found, not the numerical score.
        """
        if not best_service:
            return "Insufficient data to determine service fit."

        tech_stack: list[str] = list(business.get("tech_stack") or [])
        tech_gaps: list[str] = list(business.get("tech_gaps") or [])
        svc_techs = set(best_service.dfs_technologies or [])

        matched = [t for t in tech_stack if t in svc_techs]
        top_gaps = tech_gaps[:3]

        parts = []
        if matched:
            parts.append(f"Uses {', '.join(matched[:2])}")
        if top_gaps:
            parts.append(f"missing {', '.join(top_gaps[:2])}")

        sentence1 = (
            f"Best match: {best_service.label}. "
            + (" — ".join(parts) + "." if parts else "Limited tech signal detected.")
        )

        paid_kw = business.get("dfs_paid_keywords") or 0
        sentence2 = (
            "Active ad spend detected, indicating marketing budget exists."
            if paid_kw and int(paid_kw) > 0
            else "No active ad spend detected."
        )

        return f"{sentence1} {sentence2}"

    async def _write_scores(
        self,
        row_id: str,
        propensity: int,
        reachability: int,
        dim_scores: dict[str, int],
        best_service: str | None,
        reason: str,
    ) -> None:
        """Write all scores and stage progression to BU."""
        now = datetime.now(timezone.utc)
        await self.conn.execute(
            """
            UPDATE business_universe SET
                score_budget = $1,
                score_pain = $2,
                score_gap = $3,
                score_fit = $4,
                propensity_score = $5,
                reachability_score = $6,
                best_match_service = $7,
                score_reason = $8,
                scored_at = $9,
                pipeline_stage = $10,
                pipeline_updated_at = $11
            WHERE id = $12
            """,
            dim_scores.get("budget", 0),
            dim_scores.get("pain", 0),
            dim_scores.get("gap", 0),
            dim_scores.get("fit", 0),
            propensity,
            reachability,
            best_service,
            reason,
            now,
            PIPELINE_STAGE_S4,
            now,
            row_id,
        )


# ─── Proprietary scoring functions ───────────────────────────────────────────
# These functions contain the scoring algorithm. Logic is proprietary.
# Comments describe inputs and outputs only.

def _calc_budget_score(paid_kw: int, paid_etv: float, organic_etv: float, gmb_rating: float = 0.0) -> int:
    """Budget score from paid keyword activity and traffic value signals."""
    score = 0
    if paid_kw > 0:
        score += 50
    if paid_etv > 0:
        score += 25
    if organic_etv > 500:
        score += 25
    elif organic_etv > 100:
        score += 15
    elif organic_etv > 0:
        score += 5
    # BUG-265-3: partial GMB signal when no DFS data — business is active
    if paid_kw == 0 and organic_etv == 0 and gmb_rating > 0:
        score += 15
    return min(score, 100)


def _calc_pain_score(gmb_rating: float, gmb_reviews: int, gap_count: int) -> int:
    """Pain score from reputation signals and capability gap count."""
    score = 0
    if 0 < gmb_rating < 4.0:
        score += 40
    elif gmb_rating >= 4.0:
        score += 20
    if gmb_reviews > 50:
        score += 20
    elif gmb_reviews > 10:
        score += 10
    if gap_count >= 3:
        score += 40
    elif gap_count >= 1:
        score += 20
    return min(score, 100)


def _calc_gap_score(
    svc_techs: set[str],
    detected: set[str],
    gaps: set[str],
    has_tech_data: bool = True,
) -> int:
    """Gap score from service-specific technology gaps."""
    # BUG-265-3: neutral score when tech data was never fetched
    if not has_tech_data:
        return 25
    if not svc_techs:
        return 0
    service_gaps = svc_techs - detected
    matched_gaps = service_gaps & gaps
    if not service_gaps:
        return 0
    ratio = len(matched_gaps) / len(svc_techs)
    return min(int(ratio * 100), 100)


def _calc_fit_score(
    gmb_cat: str,
    svc_cats: set[str],
    svc_techs: set[str],
    detected: set[str],
) -> int:
    """Fit score from category and technology stack alignment."""
    score = 0
    if gmb_cat and gmb_cat in svc_cats:
        score += 60
    tech_overlap = svc_techs & detected
    if tech_overlap:
        score += min(len(tech_overlap) * 20, 40)
    return min(score, 100)
