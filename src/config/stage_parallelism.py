"""
Canonical per-stage parallelism configuration.

Same pattern as category_etv_windows.py. All pipeline stages must use
get_parallelism() rather than hardcoding semaphore values.

Provider ceilings from Directive #337 concurrency audit (2026-04-11):
  DFS: 30 concurrent (hard limit), code uses 28 (93%)
  Anthropic Sonnet: 55 concurrent (prompt-cached ITPM reduction)
  Anthropic Haiku: 55 concurrent
  Leadmagic: 10 concurrent (conservative, may increase)
  ContactOut: 15 concurrent (undocumented, conservative)
  Bright Data: 100 concurrent batch limit
  Spider.cloud: 15-80 (dynamic)
  httpx scraping: 80 concurrent
  asyncpg (Supabase): 50 pool connections

Ratified: 2026-04-13. Origin: S1-RERUN pre-flight (M-PROCESS-01 applied).
"""

from typing import TypedDict


class StageConfig(TypedDict):
    stage_name: str
    concurrency: int
    provider: str
    provider_ceiling: int
    safety_margin: float
    notes: str


STAGE_PARALLELISM: dict[str, StageConfig] = {
    "stage_1_discovery": {
        "stage_name": "Stage 1 — Discovery (DFS domain_metrics_by_categories)",
        "concurrency": 10,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "Sequential per category (1 call/category). 10 = max parallel categories. DFS ceiling 30 shared across all stages.",
    },
    "stage_2_serp_name": {
        "stage_name": "Stage 2 Q1 — SERP organic: bare domain → business_name",
        "concurrency": 20,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "DFS organic SERP: '{domain}'. Extracts business_name from title. $0.002/call.",
    },
    "stage_2_maps_gmb": {
        "stage_name": "Stage 2 Q2 — DFS Maps: business_name → GMB panel",
        "concurrency": 20,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "DFS Maps: '{business_name}'. Returns address, phone, rating, reviews, category. $0.002/call.",
    },
    "stage_2_serp_abn": {
        "stage_name": "Stage 2 Q3 — SERP organic: business_name ABN → ABR snippet",
        "concurrency": 20,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "DFS organic SERP: '{business_name} ABN'. Extracts ABN from abr.business.gov.au snippet. $0.002/call.",
    },
    "stage_2_scrape_httpx": {
        "stage_name": "Stage 2 — Website Scrape (httpx primary)",
        "concurrency": 50,
        "provider": "httpx",
        "provider_ceiling": 100,
        "safety_margin": 0.50,
        "notes": "Free, no rate limit, CPU/network bound. Primary scraper for business_name + footer ABN + contacts + tech stack.",
    },
    "stage_2_sonnet_comprehend": {
        "stage_name": "Stage 2b — Sonnet Comprehension (business intelligence extraction)",
        "concurrency": 15,
        "provider": "anthropic_sonnet",
        "provider_ceiling": 60,
        "safety_margin": 0.25,
        "notes": "Sonnet TPM constraint. Extracts canonical_business_name, services, location, business_type from scraped HTML. Prompt caching on system prompt.",
    },
    "stage_2_scrape_spider": {
        "stage_name": "Stage 2 — Website Scrape (Spider.cloud fallback)",
        "concurrency": 5,
        "provider": "spider_cloud",
        "provider_ceiling": 15,
        "safety_margin": 0.33,
        "notes": "JS-rendered fallback only. ~$0.002/page. Triggered when httpx returns JS shell or blocked.",
    },
    "stage_3_serp_abn": {
        "stage_name": "Stage 3 — ABN Resolution via SERP (uses S2 business_name)",
        "concurrency": 20,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "DFS SERP: '{business_name} ABN'. Uses business_name from S2 scrape, not domain stem.",
    },
    "stage_3_abn_join": {
        "stage_name": "Stage 3 — ABN Local JOIN (exact ABN lookup)",
        "concurrency": 50,
        "provider": "asyncpg_local",
        "provider_ceiling": 50,
        "safety_margin": 1.0,
        "notes": "Exact ABN lookup in 2.4M registry. Returns entity_type + GST.",
    },
    "stage_2_scrape": {
        "stage_name": "Stage 2 — Website Scrape (httpx + Spider) [LEGACY]",
        "concurrency": 80,
        "provider": "httpx",
        "provider_ceiling": 100,
        "safety_margin": 0.80,
        "notes": "httpx sem=80, Spider fallback sem=15. No external rate limit on httpx. AUDIT: may be obsolete if Pipeline E renumbers stages.",
    },
    "stage_3_comprehension": {
        "stage_name": "Stage 3 — Website Comprehension (Sonnet)",
        "concurrency": 55,
        "provider": "anthropic_sonnet",
        "provider_ceiling": 60,
        "safety_margin": 0.92,
        "notes": "Prompt caching reduces ITPM. GLOBAL_SEM_SONNET=55 from pipeline_orchestrator.",
    },
    "stage_4_affordability": {
        "stage_name": "Stage 4 — Affordability Gate (Haiku)",
        "concurrency": 55,
        "provider": "anthropic_haiku",
        "provider_ceiling": 60,
        "safety_margin": 0.92,
        "notes": "Haiku rate limit higher than Sonnet. Same semaphore.",
    },
    "stage_5_dm_waterfall": {
        "stage_name": "Stage 5 — DM Identification (Leadmagic + SERP)",
        "concurrency": 10,
        "provider": "leadmagic",
        "provider_ceiling": 15,
        "safety_margin": 0.67,
        "notes": "Leadmagic rate limits per-endpoint. Conservative ceiling.",
    },
    "stage_6_dm_validation": {
        "stage_name": "Stage 6 — DM Validation (ContactOut + Haiku gate)",
        "concurrency": 15,
        "provider": "contactout",
        "provider_ceiling": 20,
        "safety_margin": 0.75,
        "notes": "ContactOut rate limits undocumented. 15 is conservative.",
    },
    "stage_7_contact": {
        "stage_name": "Stage 7 — Contact Discovery (email + mobile waterfall)",
        "concurrency": 10,
        "provider": "leadmagic",
        "provider_ceiling": 15,
        "safety_margin": 0.67,
        "notes": "Same Leadmagic ceiling as Stage 5.",
    },
    "stage_8_company_enrichment": {
        "stage_name": "Stage 8 — Company Enrichment (Hunter + Bright Data)",
        "concurrency": 15,
        "provider": "bright_data",
        "provider_ceiling": 100,
        "safety_margin": 0.15,
        "notes": "BD batch limit 100, but budget-gated. 15 is cost-controlled.",
    },
    "stage_9_vulnerability": {
        "stage_name": "Stage 9 — Vulnerability Report + Profile Enrichment",
        "concurrency": 15,
        "provider": "anthropic_sonnet+contactout",
        "provider_ceiling": 55,
        "safety_margin": 0.27,
        "notes": "Mixed providers. ContactOut (15) is the bottleneck, not Sonnet (55).",
    },
    "stage_10_messages": {
        "stage_name": "Stage 10 — Message Generation (Sonnet email + Haiku others)",
        "concurrency": 12,
        "provider": "anthropic_sonnet",
        "provider_ceiling": 60,
        "safety_margin": 0.20,
        "notes": "Sonnet sem=12, Haiku sem=15. Sonnet is the bottleneck for email channel.",
    },
    # ── PIPELINE F v2 STAGES ──────────────────────────────────────────────
    # v2 stage order: DISCOVER → VERIFY → IDENTIFY → SIGNAL → ANALYSE → CONTACT → CLASSIFY
    "stage_2_verify_serp": {
        "stage_name": "F2 — VERIFY: 4 SERP calls per domain (biz name, ABN, LinkedIn, DM)",
        "concurrency": 30,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 1.0,
        "notes": "4 parallel DFS SERP calls per domain. Feeds candidates to Stage 3 Gemini. $0.008/domain.",
    },
    "stage_3_identify": {
        "stage_name": "F3 — IDENTIFY: Gemini DM identification (grounding ON, 2-step verify)",
        "concurrency": 30,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 1.0,
        "notes": "Gemini 2.5-pro with grounding. Identity + DM only — no scoring. SERP candidates injected as user prompt context.",
    },
    "stage_f2_signal_bundle": {
        "stage_name": "F4 — SIGNAL: DFS Signal Bundle (rank_overview, competitors, keywords, tech)",
        "concurrency": 15,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.50,
        "notes": "Shares DFS ceiling. 4 DFS endpoints per domain, runs on Stage 3 survivors only.",
    },
    "stage_5_analyse": {
        "stage_name": "F5 — ANALYSE: Gemini scoring + VR + outreach drafts (grounding OFF)",
        "concurrency": 10,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "Grounding disabled. Receives F3a identity + DFS signal bundle. Generates affordability, intent, buyer_match, VR, drafts.",
    },
    "stage_6_contact": {
        "stage_name": "F6 — CONTACT: Contact Waterfall (ContactOut primary)",
        "concurrency": 10,
        "provider": "contactout",
        "provider_ceiling": 20,
        "safety_margin": 0.50,
        "notes": "ContactOut is the bottleneck. Three cascading waterfalls: LinkedIn URL, email, mobile.",
    },
    "stage_7_classify": {
        "stage_name": "F7 — CLASSIFY: Funnel classifier (Ready/Near-ready/Watchlist/Dropped)",
        "concurrency": 10,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "Enhanced VR + classification. Fires for qualified prospects only.",
    },
    # Legacy keys — retained for callers not yet migrated to v2 naming
    "stage_f3a_comprehend": {
        "stage_name": "F3a — Gemini identity + DM (grounding ON) [LEGACY: use stage_3_identify]",
        "concurrency": 10,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "DEPRECATED: use stage_3_identify / stage_5_analyse. Retained for backward compat only.",
    },
    "stage_f3b_compile": {
        "stage_name": "F3b — Gemini ANALYSE (grounding OFF) [LEGACY: use stage_5_analyse]",
        "concurrency": 10,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "DEPRECATED: use stage_3_identify / stage_5_analyse. Retained for backward compat only.",
    },
    "stage_f4_verify_serp": {
        "stage_name": "F4 — Verification Gap Fills (SERP) [LEGACY: use stage_2_verify_serp]",
        "concurrency": 20,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.67,
        "notes": "LEGACY key. Migrate callers to stage_2_verify_serp.",
    },
    "stage_f5_contact_waterfall": {
        "stage_name": "F5 — Contact Waterfall [LEGACY: use stage_6_contact]",
        "concurrency": 10,
        "provider": "contactout",
        "provider_ceiling": 20,
        "safety_margin": 0.50,
        "notes": "LEGACY key. Migrate callers to stage_6_contact.",
    },
    "stage_f5_apify_linkedin": {
        "stage_name": "F5 — Apify LinkedIn Actors (no-cookie family)",
        "concurrency": 10,
        "provider": "apify",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "Shared across harvestapi/linkedin-profile-search-by-name and apimaestro actors.",
    },
    "stage_f5_bd_web_unlocker": {
        "stage_name": "F5 — Bright Data Web Unlocker (LinkedIn profile fetch)",
        "concurrency": 5,
        "provider": "bright_data",
        "provider_ceiling": 100,
        "safety_margin": 0.05,
        "notes": "Budget-gated, not rate-limited. L3 fallback only.",
    },
    "stage_f6_enhanced_vr": {
        "stage_name": "F6 — Enhanced VR [LEGACY: use stage_7_classify]",
        "concurrency": 10,
        "provider": "gemini",
        "provider_ceiling": 30,
        "safety_margin": 0.33,
        "notes": "LEGACY key. Migrate callers to stage_7_classify.",
    },
    "dfs_global": {
        "stage_name": "Global DFS Semaphore",
        "concurrency": 28,
        "provider": "dataforseo",
        "provider_ceiling": 30,
        "safety_margin": 0.93,
        "notes": "Shared across all DFS-calling stages. Hard ceiling from provider.",
    },
}


def get_parallelism(stage_key: str) -> int:
    """Return concurrency limit for a pipeline stage. Raises KeyError if unknown."""
    if stage_key not in STAGE_PARALLELISM:
        raise KeyError(
            f"Stage '{stage_key}' not in parallelism config. "
            f"Available: {sorted(STAGE_PARALLELISM.keys())}"
        )
    return STAGE_PARALLELISM[stage_key]["concurrency"]


def get_stage_config(stage_key: str) -> StageConfig:
    """Return full config dict for a pipeline stage. Raises KeyError if unknown."""
    if stage_key not in STAGE_PARALLELISM:
        raise KeyError(
            f"Stage '{stage_key}' not in parallelism config. "
            f"Available: {sorted(STAGE_PARALLELISM.keys())}"
        )
    return STAGE_PARALLELISM[stage_key]
