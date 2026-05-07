## Active Enrichment Path

**Source of truth:** [ARCHITECTURE.md](../../ARCHITECTURE.md) §SECTION 2 (System Architecture Overview) + §SECTION 5 (Enrichment Tiers Complete Spec).

**DO NOT quote pipeline stages from this file.** Read ARCHITECTURE.md fresh every session.

The canonical pipeline shape is FLOW A (sync discovery, target <6min) + FLOW B (async parallel enrichment via `asyncio.gather`, target <10min). T0 is DataForSEO `domain_metrics_by_categories`, NOT Bright Data GMB scrape (GMB is T2 backfill only). Live channels and vendors are listed in ARCHITECTURE.md §SECTION 4.

Any pipeline prose previously living in this file was stale and removed (Layer 1 SSOT alignment, 2026-05-07).
