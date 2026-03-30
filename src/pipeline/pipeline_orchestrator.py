"""
Contract: src/pipeline/pipeline_orchestrator.py
Purpose: Stage-parallel streaming pipeline — processes all domains in a batch
         concurrently per stage rather than one domain at a time.
Layer: 2 - pipeline
Directive: #293 (stage-parallel refactor)

Stage order:
  1. Discovery (pull_batch)
  2. Spider scrape ALL domains concurrently (sem=15)
  3. DNS + ABN ALL domains concurrently (sem=1 for asyncpg safety)
  4. Affordability gate (in-memory, instant)
  5. Intent free gate (in-memory, instant) — NOT_TRYING skips paid enrichment
  6. Paid enrichment: DFS Ads Search + DFS Maps GMB concurrently (sem=20)
  7. Intent full score (in-memory)
  8. DM identification ALL survivors concurrently (sem=20)
  9. Reachability check + ProspectCard build (in-memory)

Target throughput: 200 domains in under 2 minutes.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.pipeline.prospect_scorer import ProspectScorer, ProspectScore

logger = logging.getLogger(__name__)

# Semaphore limits — tuned for DFS 30-concurrent + Spider 15-concurrent limits
SEM_SPIDER = 15    # Spider.cloud concurrent scrapes
SEM_ABN    = 1     # asyncpg single-connection safety
SEM_PAID   = 20    # DFS Ads Search + GMB concurrent
SEM_DM     = 20    # DFS SERP LinkedIn concurrent

# Global semaphore pool — shared across parallel workers (module-level singletons)
GLOBAL_SEM_DFS    = asyncio.Semaphore(25)
GLOBAL_SEM_SCRAPE = asyncio.Semaphore(50)
GLOBAL_SEM_SONNET = asyncio.Semaphore(12)
GLOBAL_SEM_HAIKU  = asyncio.Semaphore(15)


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
    category_stats: dict = field(default_factory=dict)  # category_code -> prospects found


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
    Stage-parallel pipeline orchestrator (Directive #293).

    Processes all domains in a batch concurrently per stage.
    Each stage fans out with a semaphore, then the next stage
    receives only the survivors.

    Dependencies injected for testability:
        discovery:          pull_batch(category_code, location, limit, offset) -> list[dict]
        free_enrichment:    scrape_website(domain) -> dict
                            enrich_from_spider(domain, spider_data) -> dict | None
        scorer:             score_affordability(enrichment) -> AffordabilityResult
                            score_intent_free(enrichment) -> IntentResult (optional)
                            score_intent_full(enrichment, ads, gmb) -> IntentResult (optional)
        dm_identification:  identify(domain, company_name, spider_data, abn_data) -> DMResult | None
        gmb_client:         maps_search_gmb(business_name, location_name) -> dict | None
        ads_client:         callable async (domain) -> dict | None
    """

    def __init__(
        self,
        discovery,
        free_enrichment,
        scorer=None,
        dm_identification=None,
        gmb_client=None,
        ads_client=None,
        prospect_scorer=None,
    ):
        self._discovery = discovery
        self._fe = free_enrichment
        self._scorer = scorer if scorer is not None else prospect_scorer
        self._dm = dm_identification
        self._gmb_client = gmb_client
        self._ads_client = ads_client

    # ── Stage helpers ─────────────────────────────────────────────────────

    async def _stage_spider(self, sem: asyncio.Semaphore, domain: str) -> dict:
        """STAGE 2: Spider scrape one domain with semaphore."""
        async with sem:
            try:
                result = await self._fe.scrape_website(domain)
                return result or {}
            except Exception:
                logger.debug("stage_spider_failed domain=%s", domain)
                return {}

    async def _stage_enrich(
        self,
        sem: asyncio.Semaphore,
        domain: str,
        spider_data: dict,
    ) -> dict | None:
        """STAGE 3: DNS + ABN enrichment from pre-scraped Spider data."""
        async with sem:
            try:
                return await self._fe.enrich_from_spider(domain, spider_data)
            except Exception:
                logger.debug("stage_enrich_failed domain=%s", domain)
                return None

    async def _stage_paid(
        self,
        sem: asyncio.Semaphore,
        domain: str,
        company_name: str,
        suburb: str,
        location: str,
    ) -> dict:
        """STAGE 6: DFS Ads Search + DFS Maps GMB concurrently."""
        async with sem:
            async def _get_ads():
                if self._ads_client is None:
                    return None
                try:
                    return await self._ads_client(domain)
                except Exception:
                    return None

            async def _get_gmb():
                if self._gmb_client is None:
                    return None
                try:
                    q = f"{company_name} {suburb}".strip() or domain
                    return await self._gmb_client.maps_search_gmb(q, location_name=location)
                except Exception:
                    return None

            ads_data, gmb_data = await asyncio.gather(_get_ads(), _get_gmb())
            return {"ads_data": ads_data, "gmb_data": gmb_data}

    async def _stage_dm(
        self,
        sem: asyncio.Semaphore,
        domain: str,
        company_name: str,
        enrichment: dict,
    ) -> Any:
        """STAGE 8: DM identification for one domain."""
        async with sem:
            try:
                return await self._dm.identify(
                    domain=domain,
                    company_name=company_name,
                    spider_data=enrichment,
                    abn_data=enrichment,
                )
            except Exception:
                logger.debug("stage_dm_failed domain=%s", domain)
                return None

    # ── Main run ──────────────────────────────────────────────────────────

    async def run(
        self,
        category_codes: list[str] | str,
        location: str = "Australia",
        target_count: int = 100,
        batch_size: int = 50,
        exclude_domains: set | None = None,
    ) -> PipelineResult:
        """
        Stage-parallel pipeline run.

        Stages 1–9 process the batch concurrently per stage.
        Stops when target_count viable prospects are found or all categories exhausted.

        Args:
            category_codes: One or more DFS category codes to sweep. A single str
                            is accepted for backwards compatibility.
            location: Location string passed to discovery layer.
            target_count: Stop after this many viable prospects are found.
            batch_size: Discovery batch size per pull_batch call.
            exclude_domains: Optional set of already-claimed domains to skip.
                             Caller is responsible for querying campaign_leads to
                             build this set — the orchestrator is stateless.
                             (No DB migration needed: campaign_leads handles
                              multi-agency claiming via business_universe_id + campaign_id.)
        """
        results: list[ProspectCard] = []
        stats = PipelineStats()
        t0 = time.monotonic()

        # Create semaphores once per run (shared across batches)
        sem_spider = asyncio.Semaphore(SEM_SPIDER)
        sem_abn    = asyncio.Semaphore(SEM_ABN)
        sem_paid   = asyncio.Semaphore(SEM_PAID)
        sem_dm     = asyncio.Semaphore(SEM_DM)

        # Normalise to list for backwards compatibility
        if isinstance(category_codes, str):
            codes = [category_codes]
        else:
            codes = list(category_codes)

        for category_code in codes:
            if len(results) >= target_count:
                break
            offset = 0

            while len(results) < target_count:

                # ── STAGE 1: Discovery ────────────────────────────────────────
                try:
                    raw_domains = await self._discovery.pull_batch(
                        category_code=category_code,
                        location=location,
                        limit=batch_size,
                        offset=offset,
                    )
                except Exception:
                    logger.exception("stage1_discovery_failed category=%s offset=%d", category_code, offset)
                    break

                if not raw_domains:
                    logger.info("stage1_category_exhausted category=%s offset=%d", category_code, offset)
                    break

                offset += batch_size
                domains = [
                    (d if isinstance(d, str) else d.get("domain", ""))
                    for d in raw_domains
                    if (d if isinstance(d, str) else d.get("domain"))
                ]

                # Filter already-claimed domains (caller provides set)
                if exclude_domains:
                    before = len(domains)
                    domains = [d for d in domains if d not in exclude_domains]
                    excluded_count = before - len(domains)
                    if excluded_count:
                        logger.info(
                            "stage1_excluded_claimed category=%s excluded=%d",
                            category_code, excluded_count,
                        )

                if not domains:
                    continue

                stats.discovered += len(domains)
                logger.info(
                    "stage1_complete category=%s batch=%d domains=%d",
                    category_code, offset // batch_size, len(domains),
                )

                # ── STAGE 2: Spider scrape ALL concurrently ───────────────────
                spider_coros = [self._stage_spider(sem_spider, d) for d in domains]
                spider_results: list[dict] = list(
                    await asyncio.gather(*spider_coros, return_exceptions=False)
                )
                logger.info(
                    "stage2_complete scraped=%d non-empty=%d",
                    len(spider_results),
                    sum(1 for s in spider_results if s),
                )

                # ── STAGE 3: DNS + ABN ALL concurrently (sem=1 for asyncpg) ──
                enrich_coros = [
                    self._stage_enrich(sem_abn, d, s)
                    for d, s in zip(domains, spider_results)
                ]
                enrich_results: list[dict | None] = list(
                    await asyncio.gather(*enrich_coros, return_exceptions=False)
                )
                enriched_pairs: list[tuple[str, dict]] = []
                for domain, enrichment in zip(domains, enrich_results):
                    if enrichment:
                        stats.enriched += 1
                        enriched_pairs.append((domain, enrichment))
                    else:
                        stats.enrichment_failed += 1
                logger.info(
                    "stage3_complete enriched=%d failed=%d",
                    stats.enriched, stats.enrichment_failed,
                )

                # ── STAGE 4: Affordability gate (in-memory) ───────────────────
                afford_passed: list[tuple[str, dict, Any]] = []
                for domain, enrichment in enriched_pairs:
                    # Non-AU filter: reject before scoring
                    if enrichment.get("non_au"):
                        stats.affordability_rejected += 1
                        continue
                    try:
                        afford = self._scorer.score_affordability(enrichment)
                    except AttributeError:
                        # Legacy scorer fallback: score_affordability not available
                        afford = self._scorer.score(enrichment)
                    if afford.passed_gate:
                        afford_passed.append((domain, enrichment, afford))
                    else:
                        stats.affordability_rejected += 1
                logger.info(
                    "stage4_complete afford_passed=%d rejected=%d",
                    len(afford_passed), stats.affordability_rejected,
                )

                # ── STAGE 5: Intent free gate (in-memory) ─────────────────────
                intent_passed: list[tuple[str, dict, Any, Any]] = []
                for domain, enrichment, afford in afford_passed:
                    try:
                        intent_free = self._scorer.score_intent_free(enrichment)
                        if intent_free.band == "NOT_TRYING":
                            stats.intent_rejected += 1
                            continue
                    except AttributeError:
                        # Legacy scorer: no intent scoring — all pass
                        intent_free = None
                    intent_passed.append((domain, enrichment, afford, intent_free))
                logger.info(
                    "stage5_complete intent_passed=%d intent_rejected=%d",
                    len(intent_passed), stats.intent_rejected,
                )

                if not intent_passed:
                    continue

                # ── STAGE 6: Paid enrichment ALL survivors concurrently ────────
                paid_coros = []
                for domain, enrichment, afford, intent_free in intent_passed:
                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    suburb = (enrichment.get("website_address") or {}).get("suburb", "")
                    paid_coros.append(
                        self._stage_paid(sem_paid, domain, company_name, suburb, location)
                    )
                paid_results: list[dict] = list(
                    await asyncio.gather(*paid_coros, return_exceptions=False)
                )
                stats.paid_enrichment_calls += len(intent_passed)
                logger.info("stage6_complete paid_calls=%d", len(intent_passed))

                # ── STAGE 7: Intent full score (in-memory) ────────────────────
                dm_candidates: list[tuple[str, dict, Any, Any, dict]] = []
                for (domain, enrichment, afford, intent_free), paid in zip(
                    intent_passed, paid_results
                ):
                    ads_data = paid.get("ads_data")
                    gmb_data = paid.get("gmb_data")
                    # Merge GMB data into enrichment for scoring
                    if gmb_data:
                        enrichment = {**enrichment, **gmb_data}
                        stats.total_cost_usd += 0.0035
                    if ads_data:
                        stats.total_cost_usd += 0.002
                    try:
                        intent_full = self._scorer.score_intent_full(
                            enrichment, ads_data, gmb_data
                        )
                    except AttributeError:
                        intent_full = intent_free  # legacy fallback
                    dm_candidates.append((domain, enrichment, afford, intent_full, paid))

                # ── STAGE 8: DM identification ALL concurrently ───────────────
                dm_coros = []
                for domain, enrichment, afford, intent_full, paid in dm_candidates:
                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    dm_coros.append(
                        self._stage_dm(sem_dm, domain, company_name, enrichment)
                    )
                dm_results: list[Any] = list(
                    await asyncio.gather(*dm_coros, return_exceptions=False)
                )
                logger.info("stage8_complete dm_attempted=%d", len(dm_results))

                # ── STAGE 9: Reachability + ProspectCard build ────────────────
                for (domain, enrichment, afford, intent_full, paid), dm in zip(
                    dm_candidates, dm_results
                ):
                    if len(results) >= target_count:
                        break

                    if not dm or not dm.name:
                        stats.dm_not_found += 1
                        continue
                    stats.dm_found += 1

                    # Reachability gate
                    has_email = bool(enrichment.get("website_contact_emails"))
                    reachable = bool(dm.linkedin_url) or has_email
                    if not reachable:
                        stats.unreachable += 1
                        continue

                    company_name = (
                        enrichment.get("company_name")
                        or enrichment.get("abn_entity_name")
                        or domain
                    )
                    evidence = getattr(intent_full, "evidence", []) if intent_full else []
                    intent_band = getattr(intent_full, "band", "UNKNOWN") if intent_full else "UNKNOWN"
                    intent_score = getattr(intent_full, "raw_score", 0) if intent_full else 0

                    card = ProspectCard(
                        domain=domain,
                        company_name=company_name,
                        location=(enrichment.get("website_address") or {}).get("suburb", location),
                        services=enrichment.get("services") or [],
                        evidence=evidence,
                        affordability_band=afford.band,
                        affordability_score=afford.raw_score,
                        intent_band=intent_band,
                        intent_score=intent_score,
                        is_running_ads=(paid.get("ads_data") or {}).get("is_running_ads", False),
                        gmb_review_count=(paid.get("gmb_data") or {}).get("gmb_review_count", 0),
                        gmb_rating=(paid.get("gmb_data") or {}).get("gmb_rating"),
                        dm_name=dm.name,
                        dm_title=dm.title,
                        dm_linkedin_url=dm.linkedin_url,
                        dm_confidence=dm.confidence,
                    )
                    results.append(card)
                    stats.viable_prospects += 1
                    stats.category_stats[category_code] = stats.category_stats.get(category_code, 0) + 1
                    logger.info(
                        "prospect_found domain=%s afford=%s intent=%s dm=%s",
                        domain, afford.band, intent_band, dm.name,
                    )

        stats.elapsed_seconds = time.monotonic() - t0
        logger.info("orchestrator_complete prospects=%d discovered=%d elapsed=%.1fs",
                    len(results), stats.discovered, stats.elapsed_seconds)
        return PipelineResult(prospects=results, stats=stats)

    # ── Parallel worker run ───────────────────────────────────────────────

    async def run_parallel(
        self,
        category_codes: list[str],
        location: str = "Australia",
        target_count: int = 100,
        num_workers: int = 4,
        batch_size: int = 50,
        exclude_domains: set | None = None,
        on_prospect_found: Any = None,
    ) -> PipelineResult:
        """
        Multi-worker parallel pipeline (Directive #295 Task E).

        Spawns num_workers coroutines, each pulling batches from category_codes
        in round-robin. Workers share a global semaphore pool and accumulate
        results into a shared list protected by asyncio.Lock.

        Args:
            category_codes: DFS category codes to sweep (round-robin across workers).
            location: Location string passed to discovery layer.
            target_count: Stop once this many viable prospects are found.
            num_workers: Number of concurrent worker coroutines.
            batch_size: Domains per pull_batch call.
            exclude_domains: Domains already claimed — skipped without processing.
            on_prospect_found: Optional async callable(card: ProspectCard) called
                               immediately when each prospect is found (for streaming).
        """
        t0 = time.monotonic()

        # ── Shared state ─────────────────────────────────────────────────
        results: list[ProspectCard] = []
        results_lock = asyncio.Lock()
        target_reached = asyncio.Event()

        stats = PipelineStats()
        stats_lock = asyncio.Lock()

        seen_domains: set[str] = set(exclude_domains or [])
        seen_lock = asyncio.Lock()

        # Per-category offset counters (each worker advances its own category slot)
        offsets: dict[str, int] = {code: 0 for code in category_codes}
        offsets_lock = asyncio.Lock()

        # Per-worker semaphores (each worker gets its own; global sems still apply)
        sem_spider = asyncio.Semaphore(SEM_SPIDER)
        sem_abn    = asyncio.Semaphore(SEM_ABN)
        sem_paid   = asyncio.Semaphore(SEM_PAID)
        sem_dm     = asyncio.Semaphore(SEM_DM)

        # ── Worker coroutine ─────────────────────────────────────────────
        async def _worker(worker_id: int) -> None:
            cat_idx = worker_id  # each worker starts on a different category

            while not target_reached.is_set():
                # Round-robin category + advance offset
                async with offsets_lock:
                    cat_code = category_codes[cat_idx % len(category_codes)]
                    offset = offsets[cat_code]
                    offsets[cat_code] += batch_size
                    cat_idx += 1

                # STAGE 1: Discovery
                try:
                    async with GLOBAL_SEM_DFS:
                        batch = await self._discovery.pull_batch(
                            category_code=cat_code,
                            location_name=location,
                            limit=batch_size,
                            offset=offset,
                        )
                except Exception as exc:
                    logger.warning("worker_%d pull_batch error: %s", worker_id, exc)
                    break

                if not batch:
                    break  # category exhausted for this worker

                for domain_row in batch:
                    if target_reached.is_set():
                        return

                    domain = domain_row.get("domain", "")
                    if not domain:
                        continue

                    # Dedup across workers
                    async with seen_lock:
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)

                    async with stats_lock:
                        stats.discovered += 1

                    # STAGE 2: Scrape
                    async with GLOBAL_SEM_SCRAPE:
                        spider_data = await self._stage_spider(sem_spider, domain)

                    # STAGE 3: Enrich (DNS + ABN)
                    enrichment = await self._stage_enrich(sem_abn, domain, spider_data)
                    if enrichment is None:
                        async with stats_lock:
                            stats.enrichment_failed += 1
                        continue

                    async with stats_lock:
                        stats.enriched += 1

                    # Non-AU filter (Task D)
                    if enrichment.get("non_au"):
                        async with stats_lock:
                            stats.affordability_rejected += 1
                        continue

                    # GATE 1: Affordability
                    afford = self._scorer.score_affordability(enrichment)
                    if not afford.passed_gate:
                        async with stats_lock:
                            stats.affordability_rejected += 1
                        continue

                    # GATE 2: Intent free
                    intent_free = self._scorer.score_intent_free(enrichment)
                    if getattr(intent_free, "band", None) == "NOT_TRYING":
                        async with stats_lock:
                            stats.intent_rejected += 1
                        continue

                    # STAGE 6: Paid enrichment
                    company_name = enrichment.get("company_name") or domain
                    addr = enrichment.get("website_address") or {}
                    suburb = (addr.get("suburb") or addr.get("city") or "") if isinstance(addr, dict) else ""

                    async with GLOBAL_SEM_DFS:
                        paid = await self._stage_paid(sem_paid, domain, company_name, suburb, location)

                    async with stats_lock:
                        stats.paid_enrichment_calls += 1

                    ads_data = paid.get("ads_data")
                    gmb_data = paid.get("gmb_data")
                    if gmb_data:
                        enrichment = {**enrichment, **gmb_data}

                    # STAGE 7: Full intent score
                    intent = self._scorer.score_intent_full(enrichment, ads_data, gmb_data)
                    intent_band = getattr(intent, "band", "UNKNOWN")
                    evidence = getattr(intent, "evidence", [])

                    # STAGE 8: DM identification
                    async with GLOBAL_SEM_DFS:
                        dm = await self._stage_dm(sem_dm, domain, company_name, enrichment)

                    if not dm or not getattr(dm, "name", None):
                        async with stats_lock:
                            stats.dm_not_found += 1
                        continue

                    async with stats_lock:
                        stats.dm_found += 1

                    # GATE: Reachability
                    has_email = bool(enrichment.get("website_contact_emails"))
                    has_linkedin = bool(getattr(dm, "linkedin_url", None))
                    if not (has_email or has_linkedin):
                        async with stats_lock:
                            stats.unreachable += 1
                        continue

                    # Build ProspectCard
                    card = ProspectCard(
                        domain=domain,
                        company_name=company_name,
                        location=suburb,
                        evidence=evidence,
                        affordability_band=afford.band,
                        affordability_score=afford.raw_score,
                        intent_band=intent_band,
                        intent_score=getattr(intent, "raw_score", 0),
                        gmb_rating=enrichment.get("gmb_rating"),
                        gmb_review_count=enrichment.get("gmb_review_count", 0),
                        dm_name=dm.name,
                        dm_title=getattr(dm, "title", None),
                        dm_linkedin_url=getattr(dm, "linkedin_url", None),
                        dm_confidence=getattr(dm, "confidence", None),
                    )

                    async with results_lock:
                        if target_reached.is_set():
                            return  # another worker just hit the target
                        results.append(card)
                        if on_prospect_found is not None:
                            try:
                                await on_prospect_found(card)
                            except Exception:
                                pass
                        if len(results) >= target_count:
                            target_reached.set()

                    async with stats_lock:
                        stats.viable_prospects += 1
                        stats.category_stats[cat_code] = stats.category_stats.get(cat_code, 0) + 1
                        logger.info(
                            "parallel_prospect_found worker=%d domain=%s afford=%s intent=%s dm=%s",
                            worker_id, domain, afford.band, intent_band, dm.name,
                        )

        # ── Launch workers ────────────────────────────────────────────────
        workers = [_worker(i) for i in range(num_workers)]
        await asyncio.gather(*workers, return_exceptions=True)

        stats.elapsed_seconds = time.monotonic() - t0
        logger.info(
            "parallel_orchestrator_complete prospects=%d discovered=%d workers=%d elapsed=%.1fs",
            len(results), stats.discovered, num_workers, stats.elapsed_seconds,
        )
        return PipelineResult(prospects=results, stats=stats)
