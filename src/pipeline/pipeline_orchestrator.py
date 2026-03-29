"""
Contract: src/pipeline/pipeline_orchestrator.py
Purpose: Streaming pipeline that pulls domain batches until it reaches the
         target number of viable prospects with DMs.
Layer: 2 - pipeline
Imports: src.pipeline.affordability_scoring
Consumers: orchestration layer
Directive #288.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    discovered: int = 0
    enriched: int = 0
    enrichment_failed: int = 0
    gate_passed: int = 0
    gate_failed: int = 0
    dm_found: int = 0
    dm_failed: int = 0
    total_cost_usd: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class ProspectCard:
    domain: str
    company_name: str
    location: str
    services: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    affordability_band: str = "UNKNOWN"
    affordability_score: int = 0
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
        affordability_scorer: AffordabilityScorer instance
        dm_identification: DMIdentification instance
    """

    def __init__(
        self,
        discovery,
        free_enrichment,
        affordability_scorer,
        dm_identification,
        gmb_client=None,
    ):
        self._discovery = discovery
        self._enrichment = free_enrichment
        self._scorer = affordability_scorer
        self._dm = dm_identification
        self._gmb_client = gmb_client

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
            # --- Discovery ---
            try:
                domains = await self._discovery.pull_batch(
                    category_code=category_code,
                    location=location,
                    limit=batch_size,
                    offset=offset,
                )
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

                # --- Free enrichment ---
                try:
                    enrichment = await self._enrichment.enrich(domain)
                except Exception:
                    logger.exception("orchestrator_enrich_failed domain=%s", domain)
                    enrichment = None

                if not enrichment:
                    stats.enrichment_failed += 1
                    continue
                stats.enriched += 1

                # --- Affordability gate ---
                score = self._scorer.score(enrichment)
                if not score.passed_gate:
                    stats.gate_failed += 1
                    continue
                stats.gate_passed += 1

                # --- GMB reviews (optional, only for gate passers) ---
                if self._gmb_client is not None:
                    company_name_for_gmb = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    suburb = (enrichment.get("website_address") or {}).get("suburb", "")
                    gmb_query = f"{company_name_for_gmb} {suburb}".strip()
                    try:
                        gmb_data = await self._gmb_client.maps_search_gmb(
                            business_name=gmb_query,
                            location_name=location,
                        )
                        if gmb_data:
                            enrichment = {**enrichment, **gmb_data}
                            stats.total_cost_usd += 0.0035
                            # Re-score with GMB data
                            score = self._scorer.score(enrichment)
                    except Exception:
                        logger.exception("orchestrator_gmb_failed domain=%s", domain)

                # --- DM identification ---
                try:
                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    dm_result = await self._dm.identify(
                        domain=domain,
                        company_name=company_name,
                        spider_data=enrichment,
                        abn_data=enrichment,
                    )
                except Exception:
                    logger.exception("orchestrator_dm_failed domain=%s", domain)
                    dm_result = None

                if not dm_result or not dm_result.name:
                    stats.dm_failed += 1
                    continue
                stats.dm_found += 1

                # --- Build ProspectCard ---
                card = ProspectCard(
                    domain=domain,
                    company_name=company_name,
                    location=enrichment.get("website_address", {}).get("suburb", location),
                    services=enrichment.get("services") or [],
                    gaps=score.gaps,
                    affordability_band=score.band,
                    affordability_score=score.raw_score,
                    dm_name=dm_result.name,
                    dm_title=dm_result.title,
                    dm_linkedin_url=dm_result.linkedin_url,
                    dm_confidence=dm_result.confidence,
                )
                results.append(card)
                logger.info(
                    "prospect_found domain=%s band=%s dm=%s",
                    domain, score.band, dm_result.name,
                )

        stats.elapsed_seconds = time.monotonic() - t0
        logger.info(
            "orchestrator_complete prospects=%d discovered=%d elapsed=%.1fs",
            len(results), stats.discovered, stats.elapsed_seconds,
        )
        return PipelineResult(prospects=results, stats=stats)
