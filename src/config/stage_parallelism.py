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
    "stage_2_scrape_httpx": {
        "stage_name": "Stage 2 — Website Scrape (httpx primary)",
        "concurrency": 50,
        "provider": "httpx",
        "provider_ceiling": 100,
        "safety_margin": 0.50,
        "notes": "Free, no rate limit, CPU/network bound. Primary scraper for business_name + footer ABN + contacts + tech stack.",
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
