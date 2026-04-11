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
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from src.pipeline.prospect_scorer import ProspectScorer, ProspectScore
from src.pipeline.intelligence import GLOBAL_SEM_SONNET, GLOBAL_SEM_HAIKU  # shared semaphores
from src.pipeline import intelligence as _intel_module  # optional: used when self._intelligence is set
from src.config.category_registry import get_discovery_categories, SERVICE_CATEGORY_MAP  # noqa: F401
from src.pipeline.email_waterfall import discover_email, GLOBAL_SEM_LEADMAGIC  # noqa: F401
from src.pipeline.mobile_waterfall import run_mobile_waterfall
from src.pipeline.contactout_enricher import enrich_dm_via_contactout

logger = logging.getLogger(__name__)

# ── Business name waterfall helpers (Directive #305) ─────────────────────────

_ABN_ENTITY_SUFFIX_RE = re.compile(
    r"\b(pty\.?\s*ltd\.?|pty\.?\s*limited|limited|ltd\.?|inc\.?|llc|"
    r"proprietary|trustee\s+for|the\s+trustee|as\s+trustee)\b",
    re.IGNORECASE,
)


def resolve_business_name(
    domain: str,
    enrichment: dict,
    gmb_data: dict | None = None,
) -> str:
    """
    Business name waterfall — returns the best available display name.

    Priority:
    1. ABN trading_name (if not just entity suffixes and not blank)
    2. GMB business name from gmb_data
    3. ABN legal_name (cleaned of entity suffixes)
    4. Page title prefix (enrichment["company_name"])
    5. Domain stem
    """
    def _is_valid(name: str) -> bool:
        if not name or not name.strip():
            return False
        cleaned = _ABN_ENTITY_SUFFIX_RE.sub("", name).strip(" .,")
        if not cleaned:
            return False  # was only suffixes
        if re.fullmatch(r"\d{9,11}", name.replace(" ", "")):
            return False  # ABN number
        if cleaned.lower() in ("com", "com.au", "net.au", "org.au", "au"):
            return False
        return True

    candidates = [
        enrichment.get("abn_trading_name", ""),
        (gmb_data or {}).get("gmb_name", ""),
        enrichment.get("abn_legal_name", ""),
        enrichment.get("company_name", ""),  # title-derived
    ]

    for name in candidates:
        if name and _is_valid(name.strip()):
            return name.strip()[:80]

    # Domain stem fallback
    stem = domain[4:] if domain.startswith("www.") else domain
    stem = stem.split(".")[0].replace("-", " ").replace("_", " ").title()
    return stem or domain


# ── Location waterfall helpers (Directive #305) ───────────────────────────────

_AU_STATE_ABBR_RE = re.compile(
    r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", re.IGNORECASE
)

_STATE_NAME_TO_ABBR: dict[str, str] = {
    "new south wales": "NSW", "victoria": "VIC", "queensland": "QLD",
    "western australia": "WA", "south australia": "SA", "tasmania": "TAS",
    "australian capital territory": "ACT", "northern territory": "NT",
}


def _postcode_to_state(postcode: str) -> str:
    """Map Australian postcode prefix to state abbreviation."""
    try:
        pc = int(postcode)
        if 1000 <= pc <= 2999:
            return "NSW"
        if 3000 <= pc <= 3999:
            return "VIC"
        if 4000 <= pc <= 4999:
            return "QLD"
        if 5000 <= pc <= 5999:
            return "SA"
        if 6000 <= pc <= 6999:
            return "WA"
        if 7000 <= pc <= 7999:
            return "TAS"
        if 800 <= pc <= 999:
            return "NT"
        if 200 <= pc <= 299:
            return "ACT"
    except (ValueError, TypeError):
        pass
    return ""


def resolve_location(
    domain: str,
    enrichment: dict,
    gmb_data: dict | None = None,
    default_location: str = "Australia",
) -> tuple[str, str, str]:
    """
    Location waterfall — returns (suburb, state, display_string).

    Priority:
    1. GMB address — parse suburb + state from "123 Main St, Surry Hills NSW 2010"
    2. website_address (JSON-LD) suburb + state
    3. ABN state (from abn_state field if available)
    4. State hint from enrichment
    5. default_location passed from discovery
    """
    suburb = ""
    state = ""

    # Priority 1: GMB address
    gmb_address = (
        (gmb_data or {}).get("gmb_address")
        or (gmb_data or {}).get("address")
        or ""
    )
    if gmb_address:
        state_match = _AU_STATE_ABBR_RE.search(gmb_address)
        if state_match:
            state = state_match.group(0).upper()
            before_state = gmb_address[:state_match.start()].strip().rstrip(",").strip()
            parts = [p.strip() for p in before_state.split(",") if p.strip()]
            if parts:
                suburb = parts[-1]

    # Priority 2: JSON-LD address from website
    if not suburb:
        wa = enrichment.get("website_address") or {}
        if isinstance(wa, dict):
            suburb = wa.get("suburb") or wa.get("addressLocality") or wa.get("city") or ""
            if not state:
                state = wa.get("state") or wa.get("addressRegion") or ""
                if state and len(state) > 3:
                    state = _STATE_NAME_TO_ABBR.get(state.lower(), state)
            if not state:
                postcode = wa.get("postcode") or wa.get("postalCode") or ""
                state = _postcode_to_state(str(postcode)) if postcode else ""

    # Priority 3: ABN state
    if not state:
        abn_state = enrichment.get("abn_state") or ""
        if abn_state:
            state = _STATE_NAME_TO_ABBR.get(abn_state.lower(), abn_state)

    # Priority 4: State hint from enrichment
    if not state:
        state_hint = enrichment.get("state_hint") or enrichment.get("state") or ""
        if state_hint:
            state = _STATE_NAME_TO_ABBR.get(state_hint.lower(), state_hint).upper()[:3]
            if not _AU_STATE_ABBR_RE.match(state):
                state = ""

    # Build display string
    if suburb and state:
        display = f"{suburb}, {state}"
    elif suburb:
        display = suburb
    elif state:
        display = state
    else:
        display = default_location or "Australia"

    return suburb, state, display


# Semaphore limits — tuned for DFS 30-concurrent + Spider 15-concurrent limits
SEM_SPIDER = 15    # Spider.cloud concurrent scrapes
SEM_ABN    = 50    # asyncpg pool connections (Supabase Pro; pool max_size=50)
SEM_PAID   = 20    # DFS Ads Search + GMB concurrent
SEM_DM     = 20    # DFS SERP LinkedIn concurrent
SEM_LLM    = 10    # Anthropic concurrent limit (Haiku: 50 RPM, Sonnet: 10 RPM — conservative)

# Global semaphore pool — shared across parallel workers (module-level singletons)
# GLOBAL_SEM_SONNET and GLOBAL_SEM_HAIKU are defined in intelligence.py and imported above
GLOBAL_SEM_DFS         = asyncio.Semaphore(28)   # DFS API concurrent calls
GLOBAL_SEM_SCRAPE      = asyncio.Semaphore(80)   # httpx + Spider concurrent scrapes
GLOBAL_SEM_ADS_SCRAPER = asyncio.Semaphore(15)   # Ads Transparency concurrent scrapes
GLOBAL_SEM_ABN         = asyncio.Semaphore(50)   # asyncpg ABN queries (Supabase Pro; pool max_size=50)


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
    # Email waterfall fields (Directive #299)
    dm_email: Optional[str] = None
    dm_email_verified: bool = False
    dm_email_source: Optional[str] = None
    dm_email_confidence: Optional[str] = None
    email_cost_usd: float = 0.0
    # Mobile waterfall fields (Directive #317)
    dm_mobile: Optional[str] = None
    dm_mobile_source: Optional[str] = None  # "contactout" | "html_regex" | "leadmagic" | "brightdata"
    dm_mobile_tier: Optional[int] = None
    # Location fields (Directive #305 — supplements single "location" string)
    location_suburb: str = ""
    location_state: str = ""
    location_display: str = ""  # "Surry Hills, NSW" or "NSW" or "Australia"
    # Intelligence endpoints (Directive #303)
    competitors_top3: list = field(default_factory=list)
    competitor_count: int = 0
    referring_domains: int = 0
    domain_rank: int = 0
    backlink_trend: str = "unknown"
    brand_position: Optional[int] = None
    brand_gmb_showing: bool = False
    brand_competitors_bidding: bool = False
    indexed_pages: int = 0
    # Vulnerability Report (Directive #306)
    vulnerability_report: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    prospects: list  # list[ProspectCard]
    stats: PipelineStats


class SSECardStreamer:
    """
    Converts ProspectCard callbacks into Server-Sent Events for dashboard streaming.
    Usage:
        streamer = SSECardStreamer(response_queue)
        orchestrator = PipelineOrchestrator(..., on_card=streamer.emit)
    """

    def __init__(self, queue: asyncio.Queue) -> None:
        self._queue = queue

    def emit(self, card: ProspectCard) -> None:
        """Serialize card and put onto asyncio queue for SSE emission."""
        import json
        from dataclasses import asdict
        data = asdict(card)
        self._queue.put_nowait({"event": "prospect_card", "data": json.dumps(data)})


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
        intelligence=None,
        on_card=None,
    ):
        self._discovery = discovery
        self._fe = free_enrichment
        self._scorer = scorer if scorer is not None else prospect_scorer
        self._dm = dm_identification
        self._gmb_client = gmb_client
        self._ads_client = ads_client
        self._intelligence = intelligence  # optional: IntelligenceLayer instance or module
        self._on_card = on_card  # optional: callable(ProspectCard) — fires as each card completes

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

    async def _stage_intelligence(
        self,
        domain: str,
        html: str,
        enrichment: dict,
        ads_data: dict | None,
        gmb_data: dict | None,
    ) -> dict:
        """
        STAGE 7b: Run intelligence pipeline for one domain.
        Calls comprehend_website → classify_intent → refine_evidence.
        Returns merged intel dict with evidence_statements, intent_band, services, etc.
        """
        try:
            intel = self._intelligence
            url = f"https://{domain}"

            # Comprehend website
            website_data = await intel.comprehend_website(domain, html or "", url)

            # Classify intent
            intent_data = await intel.classify_intent(domain, website_data, gmb_data, ads_data)

            # Analyse reviews if available
            reviews = (gmb_data or {}).get("reviews") or []
            review_data = await intel.analyse_reviews(domain, reviews)

            # Refine evidence into final card copy
            refined = await intel.refine_evidence(domain, intent_data, review_data, website_data)

            return {
                "website_data": website_data,
                "intent_data": intent_data,
                "review_data": review_data,
                "evidence_statements": refined.get("evidence_statements", []),
                "headline_signal": refined.get("headline_signal", ""),
                "recommended_service": refined.get("recommended_service", ""),
                "outreach_angle": refined.get("outreach_angle", ""),
                "intent_band": intent_data.get("band"),
                "intent_score": intent_data.get("score", 0),
                "services": website_data.get("services", []),
            }
        except Exception as exc:
            logger.warning("_stage_intelligence failed domain=%s: %s", domain, exc)
            return {}

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

                # ── STAGE 7b: Intelligence layer (optional, Sonnet/Haiku) ─────
                # Runs comprehend_website → classify_intent → refine_evidence
                # for each dm_candidate if intelligence module is wired.
                intel_results: dict[str, dict] = {}
                if self._intelligence is not None:
                    intel_coros = []
                    for domain, enrichment, afford, intent_full, paid in dm_candidates:
                        spider_html = enrichment.get("html", "")
                        ads_data = paid.get("ads_data")
                        gmb_data = paid.get("gmb_data")
                        intel_coros.append(
                            self._stage_intelligence(domain, spider_html, enrichment, ads_data, gmb_data)
                        )
                    intel_raw = await asyncio.gather(*intel_coros, return_exceptions=True)
                    for (domain, *_), intel in zip(dm_candidates, intel_raw):
                        if isinstance(intel, Exception):
                            logger.warning("intelligence failed domain=%s: %s", domain, intel)
                            intel_results[domain] = {}
                        else:
                            intel_results[domain] = intel or {}
                    logger.info("stage7b_intelligence_complete domains=%d", len(intel_results))

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

                    company_name = resolve_business_name(domain, enrichment)
                    # Use intelligence layer results if available, else fall back to scorer
                    intel = intel_results.get(domain, {})
                    if intel.get("evidence_statements"):
                        evidence = intel["evidence_statements"]
                        intent_band = intel.get("intent_band") or (getattr(intent_full, "band", "UNKNOWN") if intent_full else "UNKNOWN")
                        intent_score = intel.get("intent_score") or (getattr(intent_full, "raw_score", 0) if intent_full else 0)
                    else:
                        evidence = getattr(intent_full, "evidence", []) if intent_full else []
                        intent_band = getattr(intent_full, "band", "UNKNOWN") if intent_full else "UNKNOWN"
                        intent_score = getattr(intent_full, "raw_score", 0) if intent_full else 0

                    _loc_suburb, _loc_state, _loc_display = resolve_location(domain, enrichment, default_location=location)

                    # ── STAGE 7c: Vulnerability Report ───────────────────────────
                    vuln_report: dict = {}
                    if self._intelligence is not None:
                        _comp_data = {
                            "top3": (paid.get("ads_data") or {}).get("competitors_top3", []),
                            "count": (paid.get("ads_data") or {}).get("competitor_count", 0),
                        }
                        _bl_data = {
                            "referring_domains": enrichment.get("backlinks_referring_domains", 0),
                            "domain_rank": enrichment.get("backlinks_domain_rank", 0),
                            "trend": enrichment.get("backlinks_trend", "unknown"),
                        }
                        _brand_data = {
                            "position": enrichment.get("brand_serp_position"),
                            "gmb_showing": enrichment.get("brand_serp_gmb_showing", False),
                            "competitors_bidding": enrichment.get("brand_serp_competitors_bidding", False),
                        }
                        _indexed = enrichment.get("indexed_pages_count", 0)
                        vuln_report = await self._intelligence.generate_vulnerability_report(
                            domain=domain,
                            company_name=company_name,
                            enrichment=enrichment,
                            intelligence=intel,
                            competitors_data=_comp_data,
                            backlinks_data=_bl_data,
                            brand_serp_data=_brand_data,
                            indexed_pages=_indexed,
                        )

                    card = ProspectCard(
                        domain=domain,
                        company_name=company_name,
                        location=_loc_display,
                        location_suburb=_loc_suburb,
                        location_state=_loc_state,
                        location_display=_loc_display,
                        services=enrichment.get("services") or intel.get("services") or [],
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
                        vulnerability_report=vuln_report,
                    )
                    results.append(card)
                    if self._on_card is not None:
                        try:
                            self._on_card(card)
                        except Exception:
                            pass  # never let streaming break the pipeline
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
        discover_all: bool = False,
    ) -> PipelineResult:
        """
        Multi-worker parallel pipeline (Directive #295 Task E, extended #298).

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
            discover_all: If True and self._discovery has discover_prospects(),
                          pre-fetch ALL domains across all category_codes before
                          workers start. Domains fed into a shared asyncio.Queue.
                          Workers consume from queue instead of calling pull_batch.
                          Use for service-first multi-category sweeps (#298).
        """
        t0 = time.monotonic()

        # ── On-demand discovery queue (replaces pre-fetch model) ─────────────
        # When discover_all=True and discovery has next_batch(), use on-demand
        # batching: pull 100 domains at a time, refill when queue < 20.
        # Stops pulling as soon as target_reached fires — DFS cost tracks need.
        pre_fetched_queue: asyncio.Queue | None = None
        discovery_lock: asyncio.Lock | None = None
        discovery_refill_task: asyncio.Task | None = None

        if discover_all and hasattr(self._discovery, "next_batch"):
            logger.info("run_parallel: on-demand discovery mode")
            category_ints: list[int] = []
            for code in category_codes:
                try:
                    category_ints.append(int(code))
                except (ValueError, TypeError):
                    pass

            # Reset discovery pagination state
            if hasattr(self._discovery, "reset"):
                self._discovery.reset(category_ints)

            pre_fetched_queue = asyncio.Queue()
            discovery_lock = asyncio.Lock()

            async def _refill_loop() -> None:
                """Pull next_batch() whenever queue drops below REFILL_THRESHOLD."""
                REFILL_THRESHOLD = 20
                DISCOVERY_BATCH = 100
                while not target_reached.is_set():
                    if pre_fetched_queue.qsize() < REFILL_THRESHOLD:
                        async with GLOBAL_SEM_DFS:
                            try:
                                batch = await self._discovery.next_batch(
                                    category_codes=category_ints,
                                    location=location,
                                    batch_size=DISCOVERY_BATCH,
                                    exclude_domains=set(exclude_domains or []),
                                )
                            except Exception as exc:
                                logger.warning("discovery refill error: %s", exc)
                                break
                        if not batch:
                            logger.info("run_parallel: all discovery categories exhausted")
                            break
                        for item in batch:
                            await pre_fetched_queue.put(item)
                        logger.info(
                            "run_parallel: refilled queue with %d domains (qsize=%d)",
                            len(batch), pre_fetched_queue.qsize(),
                        )
                    else:
                        await asyncio.sleep(0.1)

            discovery_refill_task = asyncio.create_task(_refill_loop())

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

                # ── STAGE 1: Discovery ────────────────────────────────────
                if pre_fetched_queue is not None:
                    # Multi-category pre-fetch mode: consume from shared queue
                    batch = []
                    while len(batch) < batch_size:
                        try:
                            item = pre_fetched_queue.get_nowait()
                            batch.append(item)
                        except asyncio.QueueEmpty:
                            break
                    if not batch:
                        break  # queue exhausted
                else:
                    # Legacy per-category pull mode
                    async with offsets_lock:
                        cat_code = category_codes[cat_idx % len(category_codes)]
                        offset = offsets[cat_code]
                        offsets[cat_code] += batch_size
                        cat_idx += 1

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

                    intel = self._intelligence  # None if not wired
                    html = enrichment.get("html", "")
                    company_name = resolve_business_name(domain, enrichment)
                    addr = enrichment.get("website_address") or {}
                    suburb = (addr.get("suburb") or addr.get("city") or "") if isinstance(addr, dict) else ""

                    # ── STAGE 3b: Website comprehension (Sonnet, optional) ────
                    website_data: dict = {}
                    if intel is not None:
                        website_data = await intel.comprehend_website(domain, html, f"https://{domain}")

                    # ── GATE 1: Affordability ─────────────────────────────────
                    if intel is not None:
                        # Haiku affordability judgment replaces rule-based scorer
                        afford_intel = await intel.judge_affordability(domain, enrichment, website_data)
                        if afford_intel.get("hard_gate"):
                            async with stats_lock:
                                stats.affordability_rejected += 1
                            continue
                        # Build a duck-typed result compatible with ProspectCard fields
                        class _AffordResult:
                            band = afford_intel.get("band", "MEDIUM")
                            raw_score = afford_intel.get("score", 5)
                            passed_gate = not afford_intel.get("hard_gate", False)
                            gaps: list = []
                        afford = _AffordResult()
                    else:
                        afford = self._scorer.score_affordability(enrichment)
                        if not afford.passed_gate:
                            async with stats_lock:
                                stats.affordability_rejected += 1
                            continue

                    # ── STAGE 6: Paid enrichment ──────────────────────────────
                    async with GLOBAL_SEM_DFS:
                        paid = await self._stage_paid(sem_paid, domain, company_name, suburb, location)

                    async with stats_lock:
                        stats.paid_enrichment_calls += 1

                    ads_data = paid.get("ads_data")
                    gmb_data = paid.get("gmb_data")
                    if gmb_data:
                        enrichment = {**enrichment, **gmb_data}

                    # ── STAGE 7: Intent classification ────────────────────────
                    if intel is not None:
                        # Sonnet classify_intent replaces point-counting scorer
                        intent_data = await intel.classify_intent(domain, website_data, gmb_data, ads_data)
                        intent_band = intent_data.get("band", "NOT_TRYING")
                        intent_score = intent_data.get("score", 0)

                        # Intent gate: NOT_TRYING rejected
                        if intent_band == "NOT_TRYING":
                            async with stats_lock:
                                stats.intent_rejected += 1
                            continue

                        # Sonnet analyse_reviews
                        reviews = (gmb_data or {}).get("reviews") or []
                        review_data = await intel.analyse_reviews(domain, reviews)

                        # Haiku refine_evidence → final card copy
                        refined = await intel.refine_evidence(domain, intent_data, review_data, website_data)
                        evidence = refined.get("evidence_statements", [])
                    else:
                        # Fallback: rule-based scorer
                        intent_free = self._scorer.score_intent_free(enrichment)
                        if getattr(intent_free, "band", None) == "NOT_TRYING":
                            async with stats_lock:
                                stats.intent_rejected += 1
                            continue
                        intent = self._scorer.score_intent_full(enrichment, ads_data, gmb_data)
                        intent_band = getattr(intent, "band", "UNKNOWN")
                        intent_score = getattr(intent, "raw_score", 0)
                        evidence = getattr(intent, "evidence", [])

                    # ── STAGE 7c: Vulnerability Report ───────────────────────────
                    vuln_report: dict = {}
                    if intel is not None and hasattr(intel, "generate_vulnerability_report"):
                        try:
                            _comp_data = {
                                "top3": paid.get("competitors_top3", []) if isinstance(paid, dict) else [],
                                "count": paid.get("competitor_count", 0) if isinstance(paid, dict) else 0,
                            }
                            _bl_data = {
                                "referring_domains": paid.get("backlinks_referring_domains", 0) if isinstance(paid, dict) else 0,
                                "domain_rank": paid.get("backlinks_domain_rank", 0) if isinstance(paid, dict) else 0,
                                "trend": paid.get("backlinks_trend", "unknown") if isinstance(paid, dict) else "unknown",
                            }
                            _brand_data = {
                                "position": paid.get("brand_serp_position") if isinstance(paid, dict) else None,
                                "gmb_showing": paid.get("brand_serp_gmb_showing", False) if isinstance(paid, dict) else False,
                                "competitors_bidding": paid.get("brand_serp_competitors_bidding", False) if isinstance(paid, dict) else False,
                            }
                            _indexed = paid.get("indexed_pages_count", 0) if isinstance(paid, dict) else 0
                            _intel_data = {"intent_band": intent_band, "intent_score": intent_score} if not isinstance(intent_data, dict) else intent_data
                            vuln_report = await intel.generate_vulnerability_report(
                                domain=domain,
                                company_name=company_name,
                                enrichment=enrichment,
                                intelligence=_intel_data,
                                competitors_data=_comp_data,
                                backlinks_data=_bl_data,
                                brand_serp_data=_brand_data,
                                indexed_pages=_indexed,
                            )
                        except Exception as _vuln_exc:
                            logger.warning("vulnerability_report failed domain=%s: %s", domain, _vuln_exc)

                    # ── STAGE 8: DM identification ────────────────────────────
                    async with GLOBAL_SEM_DFS:
                        dm = await self._stage_dm(sem_dm, domain, company_name, enrichment)

                    if not dm or not getattr(dm, "name", None):
                        async with stats_lock:
                            stats.dm_not_found += 1
                        continue

                    async with stats_lock:
                        stats.dm_found += 1

                    # ── STAGE 9: ContactOut (once per DM — email + mobile) ────
                    # Called ONCE; result passed to both email and mobile waterfalls.
                    # Cost: 1 ContactOut credit if profile found, 0 if not.
                    dm_linkedin_url = getattr(dm, "linkedin_url", None)
                    contactout_result = await enrich_dm_via_contactout(dm_linkedin_url)

                    # ── STAGE 9a: Email waterfall ─────────────────────────────
                    email_result = await discover_email(
                        domain=domain,
                        dm_name=dm.name or "",
                        dm_linkedin=dm_linkedin_url,
                        html=enrichment.get("html") or enrichment.get("_raw_html") or "",
                        company_name=company_name,
                        contactout_result=contactout_result,
                    )

                    # ── STAGE 9b: Mobile waterfall ────────────────────────────
                    contact_data_for_mobile = enrichment.get("contact_data") or {}
                    mobile_result = await run_mobile_waterfall(
                        domain=domain,
                        dm_linkedin_url=dm_linkedin_url,
                        contact_data=contact_data_for_mobile,
                        contactout_result=contactout_result,
                    )

                    # GATE: Reachability — email OR LinkedIn required
                    has_email = bool(email_result.email) or bool(enrichment.get("website_contact_emails"))
                    has_linkedin = bool(dm_linkedin_url)
                    if not (has_email or has_linkedin):
                        async with stats_lock:
                            stats.unreachable += 1
                        continue

                    # Build ProspectCard
                    # Re-resolve with GMB data now available (gmb_data merged into enrichment above)
                    company_name = resolve_business_name(domain, enrichment, gmb_data)
                    _loc_suburb, _loc_state, _loc_display = resolve_location(domain, enrichment, gmb_data, default_location=location)
                    card = ProspectCard(
                        domain=domain,
                        company_name=company_name,
                        location=_loc_display,
                        location_suburb=_loc_suburb,
                        location_state=_loc_state,
                        location_display=_loc_display,
                        evidence=evidence,
                        affordability_band=afford.band,
                        affordability_score=afford.raw_score,
                        intent_band=intent_band,
                        intent_score=intent_score,
                        gmb_rating=enrichment.get("gmb_rating"),
                        gmb_review_count=enrichment.get("gmb_review_count", 0),
                        dm_name=dm.name,
                        dm_title=getattr(dm, "title", None),
                        dm_linkedin_url=dm_linkedin_url,
                        dm_confidence=getattr(dm, "confidence", None),
                        dm_email=email_result.email,
                        dm_email_verified=email_result.verified,
                        dm_email_source=email_result.source,
                        dm_email_confidence=email_result.confidence,
                        email_cost_usd=email_result.cost_usd,
                        dm_mobile=mobile_result.mobile,
                        dm_mobile_source=mobile_result.source,
                        dm_mobile_tier=mobile_result.tier_used,
                        vulnerability_report=vuln_report,
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

        # Cancel refill loop once workers are done
        if discovery_refill_task is not None and not discovery_refill_task.done():
            discovery_refill_task.cancel()
            try:
                await discovery_refill_task
            except asyncio.CancelledError:
                pass

        stats.elapsed_seconds = time.monotonic() - t0
        logger.info(
            "parallel_orchestrator_complete prospects=%d discovered=%d workers=%d elapsed=%.1fs",
            len(results), stats.discovered, num_workers, stats.elapsed_seconds,
        )
        return PipelineResult(prospects=results, stats=stats)
