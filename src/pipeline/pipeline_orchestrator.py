"""
Contract: src/pipeline/pipeline_orchestrator.py
Purpose: Streaming pipeline that pulls domain batches until it reaches the
         target number of viable prospects with DMs.
Layer: 2 - pipeline
Imports: src.pipeline.prospect_scorer
Consumers: orchestration layer
Directive #291.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Any

from src.pipeline.prospect_scorer import ProspectScorer, ProspectScore

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    discovered: int = 0
    enriched: int = 0
    enrichment_failed: int = 0
    affordability_rejected: int = 0
    intent_rejected: int = 0
    paid_enrichment_calls: int = 0
    dm_found: int = 0
    dm_not_found: int = 0
    unreachable: int = 0
    viable_prospects: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class ProspectCard:
    domain: str
    company_name: str
    location: str
    services: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    affordability_band: str = "UNKNOWN"
    affordability_score: int = 0
    intent_band: str = "UNKNOWN"
    intent_score: int = 0
    is_running_ads: bool = False
    gmb_review_count: int = 0
    gmb_rating: Optional[float] = None
    dm_name: Optional[str] = None
    dm_title: Optional[str] = None
    dm_linkedin_url: Optional[str] = None
    dm_confidence: Optional[str] = None


@dataclass
class PipelineResult:
    prospects: list  # list[ProspectCard]
    stats: PipelineStats


class PipelineOrchestrator:
    """
    Streaming pipeline orchestrator.
    Pulls domain batches until target_count viable prospects with DMs are found.

    Injection-ready: all dependencies injected via __init__ for testability.

    Args:
        discovery: has method pull_batch(category_code, location, limit, offset) -> list[dict]
        free_enrichment: has method enrich(domain) -> dict | None
        prospect_scorer: ProspectScorer instance
        dm_identification: DMIdentification instance
        gmb_client: optional, has maps_search_gmb()
        ads_client: optional callable async (domain) -> dict|None
    """

    def __init__(
        self,
        discovery,
        free_enrichment,
        prospect_scorer,
        dm_identification,
        gmb_client=None,
        ads_client=None,
    ):
        self._discovery = discovery
        self._enrichment = free_enrichment
        self._scorer = prospect_scorer
        self._dm = dm_identification
        self._gmb_client = gmb_client
        self._ads_client = ads_client   # callable: async (domain) -> dict|None

    async def run(
        self,
        category_code: str,
        location: str = "Australia",
        target_count: int = 100,
        batch_size: int = 50,
    ) -> PipelineResult:
        """
        Pull domain batches until target_count prospects with DMs found.

        Stops early if category is exhausted (pull_batch returns empty).
        Tracks stats for cost/quality audit.
        """
        results: list[ProspectCard] = []
        offset = 0
        stats = PipelineStats()
        t0 = time.monotonic()

        while len(results) < target_count:
            try:
                domains = await self._discovery.pull_batch(
                    category_code=category_code, location=location,
                    limit=batch_size, offset=offset)
            except Exception:
                logger.exception("orchestrator_discovery_failed offset=%d", offset)
                break

            if not domains:
                logger.info("orchestrator_category_exhausted at offset=%d", offset)
                break

            offset += batch_size
            stats.discovered += len(domains)

            for domain_data in domains:
                if len(results) >= target_count:
                    break

                domain = domain_data if isinstance(domain_data, str) else domain_data.get("domain", "")
                if not domain:
                    stats.enrichment_failed += 1
                    continue

                # Free enrichment
                try:
                    enrichment = await self._enrichment.enrich(domain)
                except Exception:
                    logger.exception("orchestrator_enrich_failed domain=%s", domain)
                    enrichment = None

                if not enrichment:
                    stats.enrichment_failed += 1
                    continue
                stats.enriched += 1

                # GATE 1: Affordability
                afford = self._scorer.score_affordability(enrichment)
                if not afford.passed_gate:
                    stats.affordability_rejected += 1
                    continue

                # GATE 2: Intent (free signals)
                intent_free = self._scorer.score_intent_free(enrichment)
                if not intent_free.passed_free_gate:
                    stats.intent_rejected += 1
                    continue

                # Paid enrichment (gate passers only)
                ads_data = None
                gmb_data = None

                if self._ads_client is not None:
                    try:
                        ads_data = await self._ads_client(domain)
                        stats.paid_enrichment_calls += 1
                        if ads_data:
                            stats.total_cost_usd += 0.002
                    except Exception:
                        logger.exception("orchestrator_ads_failed domain=%s", domain)

                if self._gmb_client is not None:
                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    suburb = (enrichment.get("website_address") or {}).get("suburb", "")
                    gmb_query = f"{company_name} {suburb}".strip()
                    try:
                        gmb_data = await self._gmb_client.maps_search_gmb(
                            business_name=gmb_query, location_name=location)
                        stats.paid_enrichment_calls += 1
                        if gmb_data:
                            stats.total_cost_usd += 0.0035
                    except Exception:
                        logger.exception("orchestrator_gmb_failed domain=%s", domain)

                # Full intent score with paid data
                intent = self._scorer.score_intent_full(enrichment, ads_data, gmb_data)

                # DM identification
                try:
                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    dm_result = await self._dm.identify(
                        domain=domain, company_name=company_name,
                        spider_data=enrichment, abn_data=enrichment)
                except Exception:
                    logger.exception("orchestrator_dm_failed domain=%s", domain)
                    dm_result = None

                if not dm_result or not dm_result.name:
                    stats.dm_not_found += 1
                    continue
                stats.dm_found += 1

                # Reachability check
                reachable = bool(dm_result.linkedin_url) or bool(
                    enrichment.get("website_contact_emails"))
                if not reachable:
                    stats.unreachable += 1
                    continue

                # Build ProspectCard
                card = ProspectCard(
                    domain=domain,
                    company_name=company_name,
                    location=(enrichment.get("website_address") or {}).get("suburb", location),
                    services=enrichment.get("services") or [],
                    evidence=intent.evidence,
                    affordability_band=afford.band,
                    affordability_score=afford.raw_score,
                    intent_band=intent.band,
                    intent_score=intent.raw_score,
                    is_running_ads=(ads_data or {}).get("is_running_ads", False),
                    gmb_review_count=(gmb_data or {}).get("gmb_review_count", 0),
                    gmb_rating=(gmb_data or {}).get("gmb_rating"),
                    dm_name=dm_result.name,
                    dm_title=dm_result.title,
                    dm_linkedin_url=dm_result.linkedin_url,
                    dm_confidence=dm_result.confidence,
                )
                results.append(card)
                stats.viable_prospects += 1
                logger.info("prospect_found domain=%s afford=%s intent=%s dm=%s",
                            domain, afford.band, intent.band, dm_result.name)

        stats.elapsed_seconds = time.monotonic() - t0
        logger.info("orchestrator_complete prospects=%d discovered=%d elapsed=%.1fs",
                    len(results), stats.discovered, stats.elapsed_seconds)
        return PipelineResult(prospects=results, stats=stats)
