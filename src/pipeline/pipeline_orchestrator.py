"""
Contract: src/pipeline/pipeline_orchestrator.py
Purpose:  CD Player v1 — per-domain streaming pipeline.
          Preserves the SSECardStreamer / worker-pool / semaphore architecture
          from Directive #293 but delegates ALL stage logic to cohort_runner's
          proven _run_stage2–_run_stage11 functions (tested at 730 domains).

Flow per domain:
  Stage 2  (SERP verify)        → DFSLabsClient
  Stage 3  (Gemini F3A)         → GeminiClient  GATE: enterprise/no-DM → DROP
  Stage 4  (DFS signal bundle)  → DFSLabsClient
  Stage 5  (composite score)    → pure logic     GATE: not viable / score < 30 → DROP
  Stage 6  (historical rank)    → DFSLabsClient  SKIP if score < 60
  Stage 7  (Gemini F3B)         → GeminiClient
  Stage 8  (contact waterfall)  → DFS + BD + LM + ContactOut
  Stage 9  (LinkedIn social)    → BrightDataClient  SKIP if no LinkedIn URLs
  Stage 10 (VR + messaging)     → pure logic     SKIP if no email
  Stage 11 (card assembly)      → pure logic     → emit via on_card

Layer: 2 - pipeline
Directive: CD Player v1 (refactor from #293)
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.config.category_registry import (  # noqa: F401
    SERVICE_CATEGORY_MAP,
    get_discovery_categories,
)

# ── Import proven stage functions from cohort_runner ─────────────────────────
from src.orchestration.cohort_runner import (
    _new_domain,
    _run_stage2,
    _run_stage3,
    _run_stage4,
    _run_stage5,
    _run_stage6,
    _run_stage7,
    _run_stage8,
    _run_stage9,
    _run_stage10,
    _run_stage11,
)

logger = logging.getLogger(__name__)


# ── Budget enforcement constants (P0 fix — CD Player) ────────────────────────
# Speculative per-domain reservation used by cost-aware admission control.
# Derived from cohort_runner paid-stage costs:
#   Stage2=0.01 + Stage4=0.078 + Stage6=0.106 + Stage8=0.015 + Stage9=0.027
#   + ~0.01 overhead  ≈ 0.25 USD
ESTIMATED_PER_DOMAIN_COST_USD = 0.25

# Max concurrent in-flight _process_one tasks. Default sized so worst-case
# in-flight spend (DEFAULT_MAX_IN_FLIGHT × ESTIMATED_PER_DOMAIN_COST_USD)
# stays below a spark-tier cap of ~$5 USD.
DEFAULT_MAX_IN_FLIGHT = 20


# ── FIX 4 — Default on_domain_complete callback ──────────────────────────────
# Fires after Stage 11 card assembly with the full domain_data dict. Lazy
# import of persist_stage8_to_db avoids circular-import pain during module
# load (pipeline_f_master_flow imports from this module).


async def _default_on_domain_complete(domain_data: dict) -> None:
    """Default persistence hook — writes the completed domain row to BU+BDM.

    Best-effort: any exception is logged and swallowed so streaming does not
    abort on transient DB errors. Callers who need stricter semantics pass
    an explicit on_domain_complete to the orchestrator.
    """
    try:
        from src.orchestration.flows.pipeline_f_master_flow import (
            persist_stage8_to_db,
        )

        # persist_stage8_to_db is a Prefect @task; the underlying async fn is
        # .fn when called outside a flow context.
        target = getattr(persist_stage8_to_db, "fn", persist_stage8_to_db)
        await target([domain_data])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "on_domain_complete persistence failed domain=%s: %s",
            domain_data.get("domain"),
            exc,
        )


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
        return cleaned.lower() not in ("com", "com.au", "net.au", "org.au", "au")

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

_AU_STATE_ABBR_RE = re.compile(r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", re.IGNORECASE)

_STATE_NAME_TO_ABBR: dict[str, str] = {
    "new south wales": "NSW",
    "victoria": "VIC",
    "queensland": "QLD",
    "western australia": "WA",
    "south australia": "SA",
    "tasmania": "TAS",
    "australian capital territory": "ACT",
    "northern territory": "NT",
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
    gmb_address = (gmb_data or {}).get("gmb_address") or (gmb_data or {}).get("address") or ""
    if gmb_address:
        state_match = _AU_STATE_ABBR_RE.search(gmb_address)
        if state_match:
            state = state_match.group(0).upper()
            before_state = gmb_address[: state_match.start()].strip().rstrip(",").strip()
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


# ── Global semaphore pool ─────────────────────────────────────────────────────
# Tuned for DFS 30-concurrent + Spider 15-concurrent limits.
# Module-level singletons shared across parallel workers.

SEM_SPIDER = 15  # Spider.cloud concurrent scrapes
SEM_ABN = 50  # asyncpg pool connections (Supabase Pro; pool max_size=50)
SEM_PAID = 20  # DFS Ads Search + GMB concurrent
SEM_DM = 20  # DFS SERP LinkedIn concurrent
SEM_LLM = 10  # Anthropic concurrent limit

GLOBAL_SEM_DFS = asyncio.Semaphore(28)  # DFS API concurrent calls
GLOBAL_SEM_SCRAPE = asyncio.Semaphore(80)  # httpx + Spider concurrent scrapes
GLOBAL_SEM_ADS_SCRAPER = asyncio.Semaphore(15)  # Ads Transparency concurrent scrapes
GLOBAL_SEM_ABN = asyncio.Semaphore(50)  # asyncpg ABN queries


# ── Dataclasses ───────────────────────────────────────────────────────────────


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
    gmb_rating: float | None = None
    dm_name: str | None = None
    dm_title: str | None = None
    dm_linkedin_url: str | None = None
    dm_confidence: str | None = None
    # Email waterfall fields (Directive #299)
    dm_email: str | None = None
    dm_email_verified: bool = False
    dm_email_source: str | None = None
    dm_email_confidence: str | None = None
    email_cost_usd: float = 0.0
    # Mobile waterfall fields (Directive #317)
    dm_mobile: str | None = None
    dm_mobile_source: str | None = None
    dm_mobile_tier: int | None = None
    # Location fields (Directive #305)
    location_suburb: str = ""
    location_state: str = ""
    location_display: str = ""
    # Intelligence endpoints (Directive #303)
    competitors_top3: list = field(default_factory=list)
    competitor_count: int = 0
    referring_domains: int = 0
    domain_rank: int = 0
    backlink_trend: str = "unknown"
    brand_position: int | None = None
    brand_gmb_showing: bool = False
    brand_competitors_bidding: bool = False
    indexed_pages: int = 0
    # Vulnerability Report (Directive #306)
    vulnerability_report: dict = field(default_factory=dict)
    # Full stage11 card (CD Player v1 — structured output from assemble_card)
    stage11_card: dict = field(default_factory=dict)


@dataclass
class PipelineResult:
    prospects: list  # list[ProspectCard]
    stats: PipelineStats


# ── SSECardStreamer ────────────────────────────────────────────────────────────


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


# ── Helper: build a ProspectCard from a completed domain_data dict ────────────


def _card_from_domain_data(domain_data: dict) -> ProspectCard | None:
    """
    Extract a ProspectCard from a completed domain_data dict (after stage11).
    Returns None if card assembly was not successful.
    """
    stage11 = domain_data.get("stage11") or {}
    if not stage11:
        return None

    domain = domain_data["domain"]
    identity = domain_data.get("stage3") or {}
    scores = domain_data.get("stage5") or {}
    contacts = domain_data.get("stage8_contacts") or {}
    email_data = contacts.get("email") or {}
    mobile_data = contacts.get("mobile") or {}
    linkedin_data = contacts.get("linkedin") or {}
    analyse = domain_data.get("stage7") or {}
    signals = domain_data.get("stage4") or {}

    company_name = (
        stage11.get("company_name") or identity.get("business_name") or domain.split(".")[0].title()
    )
    location_display = stage11.get("location") or stage11.get("location_display") or "Australia"
    location_suburb = stage11.get("location_suburb") or ""
    location_state = stage11.get("location_state") or ""

    dm = identity.get("dm_candidate") or {}
    dm_name = stage11.get("dm_name") or dm.get("name")
    dm_title = stage11.get("dm_title") or dm.get("role")
    dm_linkedin = (
        stage11.get("dm_linkedin_url")
        or linkedin_data.get("linkedin_url")
        or dm.get("linkedin_url")
    )

    rank_overview = signals.get("rank_overview") or {}

    return ProspectCard(
        domain=domain,
        company_name=company_name,
        location=location_display,
        location_suburb=location_suburb,
        location_state=location_state,
        location_display=location_display,
        services=stage11.get("services") or [],
        evidence=stage11.get("evidence") or analyse.get("evidence") or [],
        affordability_band=scores.get("affordability_band") or "UNKNOWN",
        affordability_score=int(scores.get("affordability_score") or 0),
        intent_band=scores.get("intent_band") or "UNKNOWN",
        intent_score=int(scores.get("intent_score") or scores.get("composite_score") or 0),
        is_running_ads=bool(stage11.get("is_running_ads")),
        gmb_review_count=int(stage11.get("gmb_review_count") or 0),
        gmb_rating=stage11.get("gmb_rating"),
        dm_name=dm_name,
        dm_title=dm_title,
        dm_linkedin_url=dm_linkedin,
        dm_confidence=stage11.get("dm_confidence") or dm.get("confidence"),
        dm_email=email_data.get("email"),
        dm_email_verified=bool(email_data.get("verified")),
        dm_email_source=email_data.get("source"),
        dm_email_confidence=email_data.get("confidence"),
        email_cost_usd=float(email_data.get("cost_usd") or 0),
        dm_mobile=mobile_data.get("mobile"),
        dm_mobile_source=mobile_data.get("source"),
        dm_mobile_tier=mobile_data.get("tier"),
        referring_domains=int(rank_overview.get("referring_domains") or 0),
        domain_rank=int(rank_overview.get("rank") or 0),
        vulnerability_report=stage11.get("vulnerability_report") or {},
        stage11_card=stage11,
    )


# ── PipelineOrchestrator ──────────────────────────────────────────────────────


class PipelineOrchestrator:
    """
    CD Player v1 — per-domain streaming pipeline orchestrator.

    Uses cohort_runner's proven _run_stage2–_run_stage11 functions for all
    stage logic. Preserves the per-domain worker-pool streaming architecture
    from Directive #293 for SSE compatibility.

    Primary entry point: run_streaming()
    Legacy entry point:  run() / run_parallel() — deprecated, kept for
                         backwards compatibility.

    Clients injected:
        dfs_client:     DFSLabsClient (stages 2, 4, 6, 8)
        gemini_client:  GeminiClient  (stages 3, 7)
        bd_client:      BrightDataClient (stages 8, 9)
        lm_client:      LeadmagicClient  (stage 8)
        discovery:      pull_batch(category_code, location, limit, offset) -> list[dict]
        on_card:        optional callable(ProspectCard) — fires as each card completes
    """

    def __init__(
        self,
        # CD Player v1 — real clients (primary constructor)
        dfs_client=None,
        gemini_client=None,
        bd_client=None,
        lm_client=None,
        discovery=None,
        on_card: Callable[[ProspectCard], None] | None = None,
        on_domain_complete: Callable[[dict], Any] | None = None,
        # Legacy keyword args — kept for backwards compatibility
        free_enrichment=None,
        scorer=None,
        dm_identification=None,
        gmb_client=None,
        ads_client=None,
        prospect_scorer=None,
        intelligence=None,
        leadmagic_client=None,
        brightdata_client=None,
    ):
        # CD Player v1 clients
        self._dfs = dfs_client
        self._gemini = gemini_client
        self._bd = bd_client or brightdata_client
        self._lm = lm_client or leadmagic_client
        self._discovery = discovery
        self._on_card = on_card
        # FIX 4 — persistence hook. Called after Stage 11 card assembly with
        # the full domain_data dict. Default wraps persist_stage8_to_db([d]).
        self._on_domain_complete = on_domain_complete or _default_on_domain_complete

        # Legacy shims — kept so existing callers don't break
        self._fe = free_enrichment
        self._scorer = scorer if scorer is not None else prospect_scorer
        self._dm = dm_identification
        self._gmb_client = gmb_client
        self._ads_client = ads_client
        self._intelligence = intelligence
        self._leadmagic_client = lm_client or leadmagic_client
        self._brightdata_client = bd_client or brightdata_client

    # ── Core per-domain processor ─────────────────────────────────────────

    async def _process_domain(
        self,
        domain_data: dict,
    ) -> ProspectCard | None:
        """
        Run stages 2–11 sequentially for a single domain.

        Uses cohort_runner's proven _run_stage functions.
        After each stage, checks domain_data["dropped_at"]; if set, returns None.
        After each PAID stage (2/4/6/8/9), the shared per-run cost counter
        (budget gate B) is advanced and compared against the budget cap —
        any breach sets dropped_at='budget_exceeded' and short-circuits.
        GOV-8: on_domain_complete fires on EVERY exit path (drop or success).
        On stage 11 completion, builds and returns a ProspectCard.

        Args:
            domain_data: dict produced by cohort_runner._new_domain()

        Returns:
            ProspectCard on success, None if domain was dropped at any stage.
        """
        clients = {
            "dfs": self._dfs,
            "gemini": self._gemini,
            "bd": self._bd,
            "lm": self._lm,
        }
        card: ProspectCard | None = None
        stage6_task: asyncio.Task | None = None

        try:
            # Stage 2 — SERP verify (PAID)
            async with GLOBAL_SEM_DFS:
                domain_data = await _run_stage2(domain_data, clients["dfs"])
            if domain_data.get("dropped_at"):
                return None
            if await self._check_budget_gate(domain_data, "stage2"):
                return None

            # Stage 3 — Gemini F3A (GATE: enterprise/no-DM → DROP)
            domain_data = await _run_stage3(domain_data, clients["gemini"])
            if domain_data.get("dropped_at"):
                return None

            # Stage 4 — DFS signal bundle (PAID)
            async with GLOBAL_SEM_DFS:
                domain_data = await _run_stage4(domain_data, clients["dfs"])
            if domain_data.get("dropped_at"):
                return None
            if await self._check_budget_gate(domain_data, "stage4"):
                return None

            # Stage 5 — composite scoring (GATE: score < 30 → DROP)
            domain_data = await _run_stage5(domain_data)
            if domain_data.get("dropped_at"):
                return None

            # T2 CAPACITY SKIP — Stage 6 is gated on composite_score >= 60.
            # When the gate passes we fire Stage 6 as a background task so
            # Stage 7 can run in parallel. Awaited before Stage 11.
            composite_score = (
                (domain_data.get("scores") or {}).get("composite_score")
                or domain_data.get("composite_score")
                or 0
            )
            if composite_score >= 60:

                async def _stage6_bg():
                    async with GLOBAL_SEM_DFS:
                        return await _run_stage6(domain_data, clients["dfs"])

                stage6_task = asyncio.create_task(_stage6_bg())

            # Stage 7 — Gemini F3B analysis (concurrent with stage 6)
            domain_data = await _run_stage7(domain_data, clients["gemini"])
            if domain_data.get("dropped_at"):
                return None

            # Stage 8 — contact waterfall (PAID)
            async with GLOBAL_SEM_DFS:
                domain_data = await _run_stage8(
                    domain_data,
                    clients["dfs"],
                    bd=clients["bd"],
                    lm=clients["lm"],
                )
            if domain_data.get("dropped_at"):
                return None
            if await self._check_budget_gate(domain_data, "stage8"):
                return None

            # Stage 9 — LinkedIn social (PAID — gate inside _run_stage9)
            domain_data = await _run_stage9(domain_data, clients["bd"])
            if domain_data.get("dropped_at"):
                return None
            if await self._check_budget_gate(domain_data, "stage9"):
                return None

            # Stage 10 — VR + messaging (SKIP if no email, gate inside)
            domain_data = await _run_stage10(domain_data)
            if domain_data.get("dropped_at"):
                return None

            # T2 — join the background stage 6 task before card assembly so
            # its historical-rank output is present on the card (PAID).
            if stage6_task is not None:
                try:
                    domain_data = await stage6_task
                except Exception as exc:
                    logger.warning("stage6 background task failed: %s", exc)
                stage6_task = None
                if domain_data.get("dropped_at"):
                    return None
                if await self._check_budget_gate(domain_data, "stage6"):
                    return None

            # Stage 11 — card assembly
            domain_data = await _run_stage11(domain_data)
            card = _card_from_domain_data(domain_data)
            return card
        finally:
            # Cancel any lingering stage 6 task (e.g. early return via drop)
            if stage6_task is not None and not stage6_task.done():
                stage6_task.cancel()

            # GOV-8 — persist EVERY domain (drops included), not just cards.
            # Exceptions in the hook are logged and swallowed so streaming
            # cannot abort on transient DB errors.
            if self._on_domain_complete is not None:
                try:
                    res = self._on_domain_complete(domain_data)
                    if inspect.isawaitable(res):
                        await res
                except Exception as exc:
                    logger.warning(
                        "on_domain_complete callback failed domain=%s: %s",
                        domain_data.get("domain"),
                        exc,
                    )

    async def _check_budget_gate(self, domain_data: dict, stage: str) -> bool:
        """Budget gate B — update the shared run-cost counter with this
        domain's latest cost_usd and return True if the run is over budget
        (in which case caller must set dropped_at and return None).

        Safe to call when no run is active (no cost state wired) — returns
        False so direct unit tests of _process_domain still execute.
        """
        cost_state = getattr(self, "_run_cost_state", None)
        if cost_state is None:
            return False

        lock: asyncio.Lock = cost_state["lock"]
        domain_id = id(domain_data)
        async with lock:
            seen_cost = cost_state["per_domain"].get(domain_id, 0.0)
            current_cost = float(domain_data.get("cost_usd", 0.0) or 0.0)
            delta = max(0.0, current_cost - seen_cost)
            cost_state["per_domain"][domain_id] = current_cost
            cost_state["total"] += delta
            total = cost_state["total"]
            cap = cost_state["cap"]

        if total >= cap:
            logger.warning(
                "budget_exceeded gate=%s domain=%s total=$%.3f cap=$%.3f",
                stage,
                domain_data.get("domain"),
                total,
                cap,
            )
            domain_data["dropped_at"] = "budget_exceeded"
            domain_data["drop_reason"] = f"budget_exceeded at {stage}"
            return True
        return False

    # ── Primary entry point ───────────────────────────────────────────────

    async def run_streaming(
        self,
        categories: list[str],
        target_cards: int = 20,
        budget_cap_aud: float = 50.0,
        tier_config: dict | None = None,
        num_workers: int = 8,
        batch_size: int = 50,
        location: str = "Australia",
        exclude_domains: set | None = None,
        refill_pct: float = 0.08,
        max_in_flight: int = DEFAULT_MAX_IN_FLIGHT,
    ) -> PipelineResult:
        """
        CD Player v1 — primary streaming entry point.

        Spawns num_workers coroutines pulling discovery batches from categories.
        Each worker calls _process_domain per domain — domains stream through
        stages 2–11 independently. Cards emitted immediately via on_card callback
        as each domain completes all stages.

        Stops accepting new domains when target_cards is reached OR budget_cap_aud
        (converted to USD) is exceeded.

        Args:
            categories:      Category name strings (keys in cohort_runner.CATEGORY_MAP)
                             OR raw DFS category code strings.
            target_cards:    Stop after this many cards are emitted.
            budget_cap_aud:  Hard budget cap in AUD. Pipeline stops when cost exceeds this.
            tier_config:     Optional tier configuration dict (reserved for future use).
            num_workers:     Parallel worker coroutines.
            batch_size:      Domains per discovery pull.
            location:        Location string for discovery.
            exclude_domains: Domains to skip (already claimed).

        Returns:
            PipelineResult with emitted cards and run stats.
        """
        from src.orchestration.cohort_runner import CATEGORY_MAP

        budget_cap_usd = budget_cap_aud / 1.55

        t0 = time.monotonic()
        results: list[ProspectCard] = []
        results_lock = asyncio.Lock()
        target_reached = asyncio.Event()
        cards_emitted = 0  # asyncio-safe counter via results_lock

        stats = PipelineStats()
        stats_lock = asyncio.Lock()

        seen_domains: set[str] = set(exclude_domains or [])
        seen_lock = asyncio.Lock()

        # ── Budget enforcement state (P0 fix) ──────────────────────────────
        # Gate B (per-stage) reads this via self._run_cost_state. Gates A
        # (cost-aware admission) and C (max_in_flight semaphore) read
        # budget_cap_usd + admission_sem directly from run_streaming scope.
        self._run_cost_state = {
            "total": 0.0,
            "cap": budget_cap_usd,
            "lock": asyncio.Lock(),
            "per_domain": {},  # id(domain_data) -> last cost
        }
        admission_sem = asyncio.Semaphore(max(1, max_in_flight))
        budget_exceeded = asyncio.Event()

        # T3 DROP-TRIGGERED REFILL — whenever drops_since_last_refill hits
        # refill_threshold we fire an extra DFS discovery batch so the worker
        # pool keeps draining new candidate domains. Each new domain becomes
        # its own _process_domain task concurrent with the workers.
        refill_threshold = max(1, int(target_cards * refill_pct))
        drops_since_last_refill = 0
        drops_lock = asyncio.Lock()
        # FIX 1 — set with discard-on-done avoids unbounded list growth.
        refill_tasks: set[asyncio.Task] = set()
        refill_offsets: dict[str, int] = {}
        # FIX 2 — dedicated counter for category round-robin (was using
        # len(refill_tasks) which mixed task types and skewed distribution).
        refill_counter = 0

        # Resolve category names to int codes (pass-through if already int strings)
        resolved_codes: list[str] = []
        for cat in categories:
            if cat in CATEGORY_MAP:
                resolved_codes.append(str(CATEGORY_MAP[cat]))
            else:
                resolved_codes.append(str(cat))  # assume already a code

        offsets: dict[str, int] = dict.fromkeys(resolved_codes, 0)
        offsets_lock = asyncio.Lock()

        async def _process_one(domain: str, category_label: str) -> None:
            """Run the full stages 2–11 pipeline for one domain + emit card
            (or count the drop). Shared by pool workers AND refill tasks."""
            nonlocal cards_emitted, drops_since_last_refill
            if target_reached.is_set() or budget_exceeded.is_set():
                return

            # Gate A — cost-aware admission. Reserve ESTIMATED_PER_DOMAIN_COST
            # against the shared counter BEFORE spending any API call. Skip
            # the domain if reservation would breach the cap.
            cost_state = self._run_cost_state
            async with cost_state["lock"]:
                projected = cost_state["total"] + ESTIMATED_PER_DOMAIN_COST_USD
                if projected >= cost_state["cap"]:
                    logger.warning(
                        "budget_exceeded admission_gate domain=%s total=$%.3f +est=$%.3f cap=$%.3f",
                        domain,
                        cost_state["total"],
                        ESTIMATED_PER_DOMAIN_COST_USD,
                        cost_state["cap"],
                    )
                    budget_exceeded.set()
                    target_reached.set()
                    return

            # Gate C — bound the worst-case concurrent in-flight spend
            # (max_in_flight × ESTIMATED_PER_DOMAIN_COST_USD).
            async with admission_sem:
                if target_reached.is_set() or budget_exceeded.is_set():
                    return

                domain_data = _new_domain(domain, category_label)
                try:
                    card = await self._process_domain(domain_data)
                except Exception as exc:
                    logger.warning("_process_domain failed domain=%s: %s", domain, exc)
                    card = None

                # If _process_domain dropped for budget, signal the run to stop.
                if domain_data.get("dropped_at") == "budget_exceeded":
                    budget_exceeded.set()
                    target_reached.set()

            async with stats_lock:
                stats.total_cost_usd += domain_data.get("cost_usd", 0.0)
                if domain_data.get("dropped_at"):
                    stage = domain_data["dropped_at"]
                    if stage in ("stage3", "stage4"):
                        stats.enrichment_failed += 1
                    elif stage == "stage5":
                        stats.affordability_rejected += 1

            if card is None:
                async with drops_lock:
                    drops_since_last_refill += 1
                    if drops_since_last_refill >= refill_threshold and not target_reached.is_set():
                        drops_since_last_refill = 0
                        # FIX 1 — auto-discard completed refill tasks.
                        _t = asyncio.create_task(_trigger_refill())
                        refill_tasks.add(_t)
                        _t.add_done_callback(refill_tasks.discard)
                return

            async with results_lock:
                if target_reached.is_set():
                    return
                results.append(card)
                cards_emitted += 1
                stats.viable_prospects += 1
                if self._on_card is not None:
                    try:
                        self._on_card(card)
                    except Exception as cb_exc:
                        logger.warning(
                            "on_card callback error domain=%s: %s",
                            domain,
                            cb_exc,
                        )
                logger.info(
                    "cd_player_card_emitted domain=%s cards=%d/%d cost=$%.3f",
                    domain,
                    cards_emitted,
                    target_cards,
                    stats.total_cost_usd,
                )
                if cards_emitted >= target_cards:
                    target_reached.set()

        async def _trigger_refill() -> None:
            """T3 — pull one extra DFS discovery batch + spawn _process_domain
            tasks per new domain. Stops as soon as target_cards is reached."""
            nonlocal refill_counter
            if target_reached.is_set() or budget_exceeded.is_set():
                return
            async with stats_lock:
                if stats.total_cost_usd >= budget_cap_usd:
                    return
            async with offsets_lock:
                # FIX 2 — dedicated round-robin counter (not len(refill_tasks)
                # which mixes pending-pull tasks with processing tasks).
                cat_code = resolved_codes[refill_counter % len(resolved_codes)]
                refill_counter += 1
                refill_offsets.setdefault(cat_code, offsets[cat_code])
                refill_offsets[cat_code] += batch_size
                offset = refill_offsets[cat_code]

            try:
                async with GLOBAL_SEM_DFS:
                    raw_batch = await self._discovery.pull_batch(
                        category_code=cat_code,
                        location_name=location,
                        limit=batch_size,
                        offset=offset,
                    )
            except Exception as exc:
                logger.warning("refill pull_batch error cat=%s: %s", cat_code, exc)
                return

            if not raw_batch:
                return

            category_label = cat_code
            for name, code in CATEGORY_MAP.items():
                if str(code) == cat_code:
                    category_label = name
                    break

            spawned = 0
            for domain_row in raw_batch:
                if target_reached.is_set():
                    break
                domain = (
                    domain_row.get("domain", "")
                    if isinstance(domain_row, dict)
                    else str(domain_row)
                )
                if not domain:
                    continue
                async with seen_lock:
                    if domain in seen_domains:
                        continue
                    seen_domains.add(domain)
                async with stats_lock:
                    stats.discovered += 1
                # FIX 1 — auto-discard completed refill tasks.
                _t = asyncio.create_task(_process_one(domain, category_label))
                refill_tasks.add(_t)
                _t.add_done_callback(refill_tasks.discard)
                spawned += 1
            logger.info(
                "cd_player_refill triggered cat=%s offset=%d spawned=%d drops_threshold=%d",
                cat_code,
                offset,
                spawned,
                refill_threshold,
            )

        async def _worker(worker_id: int) -> None:
            nonlocal cards_emitted, drops_since_last_refill
            cat_idx = worker_id

            while not target_reached.is_set():
                if budget_exceeded.is_set():
                    return
                # Budget check (legacy post-completion guard; gates A/B/C
                # above are the authoritative cost defences).
                async with stats_lock:
                    if stats.total_cost_usd >= budget_cap_usd:
                        logger.warning(
                            "worker_%d: budget cap reached $%.2f USD ($%.2f AUD) — stopping",
                            worker_id,
                            budget_cap_usd,
                            budget_cap_aud,
                        )
                        budget_exceeded.set()
                        target_reached.set()
                        return

                # Pull discovery batch
                async with offsets_lock:
                    cat_code = resolved_codes[cat_idx % len(resolved_codes)]
                    offset = offsets[cat_code]
                    offsets[cat_code] += batch_size
                    cat_idx += 1

                try:
                    async with GLOBAL_SEM_DFS:
                        raw_batch = await self._discovery.pull_batch(
                            category_code=cat_code,
                            location_name=location,
                            limit=batch_size,
                            offset=offset,
                        )
                except Exception as exc:
                    logger.warning("worker_%d pull_batch error: %s", worker_id, exc)
                    break

                if not raw_batch:
                    logger.info(
                        "worker_%d: category %s exhausted at offset %d", worker_id, cat_code, offset
                    )
                    break

                for domain_row in raw_batch:
                    if target_reached.is_set():
                        return

                    domain = (
                        domain_row.get("domain", "")
                        if isinstance(domain_row, dict)
                        else str(domain_row)
                    )
                    if not domain:
                        continue

                    # Dedup across workers
                    async with seen_lock:
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)

                    async with stats_lock:
                        stats.discovered += 1

                    # Resolve category label (first time only per cat_code)
                    category_label = cat_code
                    for name, code in CATEGORY_MAP.items():
                        if str(code) == cat_code:
                            category_label = name
                            break

                    # Process through all stages (shared with refill tasks)
                    await _process_one(domain, category_label)
                    if target_reached.is_set():
                        return

        workers = [_worker(i) for i in range(num_workers)]
        try:
            await asyncio.gather(*workers, return_exceptions=True)

            # T3 — drain any refill-spawned tasks still running. Snapshot the
            # set because add_done_callback mutates it as tasks complete.
            if refill_tasks:
                await asyncio.gather(*list(refill_tasks), return_exceptions=True)
        finally:
            # Clear per-run cost state so subsequent runs start fresh.
            self._run_cost_state = None

        stats.elapsed_seconds = time.monotonic() - t0
        if budget_exceeded.is_set():
            logger.warning(
                "run_streaming_budget_exceeded cards=%d discovered=%d cap_usd=$%.3f total_usd=$%.3f",
                len(results),
                stats.discovered,
                budget_cap_usd,
                stats.total_cost_usd,
            )
        logger.info(
            "run_streaming_complete cards=%d discovered=%d workers=%d elapsed=%.1fs cost_usd=$%.3f",
            len(results),
            stats.discovered,
            num_workers,
            stats.elapsed_seconds,
            stats.total_cost_usd,
        )
        return PipelineResult(prospects=results, stats=stats)

    # ── Legacy entry points (deprecated) ─────────────────────────────────

    async def run(
        self,
        category_codes: list[str] | str,
        location: str = "Australia",
        target_count: int = 100,
        batch_size: int = 50,
        exclude_domains: set | None = None,
    ) -> PipelineResult:
        """
        DEPRECATED — stage-parallel batch pipeline (Directive #293).

        Use run_streaming() for the CD Player v1 unified flow.
        This method preserves backwards compatibility for callers that
        pass legacy discovery/scorer/dm_identification dependencies.
        """
        warnings.warn(
            "PipelineOrchestrator.run() is deprecated. Use run_streaming() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # Fall back to run_streaming if CD Player clients are wired
        if self._dfs is not None and self._gemini is not None:
            codes = [category_codes] if isinstance(category_codes, str) else list(category_codes)
            return await self.run_streaming(
                categories=codes,
                target_cards=target_count,
                budget_cap_aud=500.0,
                location=location,
                exclude_domains=exclude_domains,
            )
        # No CD Player clients — return empty result rather than crash
        logger.error(
            "run() called without CD Player clients (dfs_client, gemini_client). "
            "Instantiate PipelineOrchestrator with dfs_client and gemini_client."
        )
        return PipelineResult(prospects=[], stats=PipelineStats())

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
        DEPRECATED — multi-worker parallel pipeline (Directive #295/#298).

        Use run_streaming() for the CD Player v1 unified flow.
        Delegates to run_streaming() when CD Player clients are wired;
        otherwise logs an error and returns empty.
        """
        warnings.warn(
            "PipelineOrchestrator.run_parallel() is deprecated. Use run_streaming() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if on_prospect_found is not None:
            # Wrap async on_prospect_found in a sync on_card shim
            orig_on_card = self._on_card

            def _shim(card: ProspectCard) -> None:
                asyncio.get_event_loop().create_task(on_prospect_found(card))
                if orig_on_card is not None:
                    orig_on_card(card)

            self._on_card = _shim

        return await self.run_streaming(
            categories=category_codes,
            target_cards=target_count,
            budget_cap_aud=500.0,
            num_workers=num_workers,
            batch_size=batch_size,
            location=location,
            exclude_domains=exclude_domains,
        )
