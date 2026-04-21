# Agency OS Manual

Last updated: 2026-04-21 UTC
Directive AGENCY-PROFILE-TRUTH-AUDIT: Agency profile truth audit + writer/critic architecture (PRs #371-#373)
Next scheduled update: Next architecture change or milestone

> **Primary store.** This file is the CEO SSOT. Google Doc is an auto-generated mirror.
> After every save-trigger write, verify with: `cat docs/MANUAL.md | grep "SECTION"`

---

## SECTION 1 — PRODUCT VISION

Agency OS is an AI-powered BDR-as-a-service platform that automates multi-channel client acquisition for B2B service businesses. Starting with Australian marketing agencies, expanding to recruitment agencies, IT MSPs, web/software agencies, and accounting firms. Eventual goal: horizontal GTM platform serving any B2B company.

Positioned as "The Bloomberg Terminal for Client Acquisition."

Second product: Business Universe (BU) — a live, outcome-weighted intelligence layer on Australian B2B commerce, built as an Agency OS byproduct. Not sellable until four readiness thresholds are crossed: Coverage ≥40%, Verified ≥55%, 500+ outcomes, Trajectory ≥30%.

Revenue model for BU: API subscriptions, Salesforce/HubSpot marketplace, bulk annual licenses. Three moats: data, verification, temporal.

---

## SECTION 2 — CURRENT STATE

**Last directive:** AGENCY-PROFILE-TRUTH-AUDIT (agency profile truth audit — DEFAULT_AGENCY eliminated, pre-revenue discipline enforced)
**Pipeline F status:** P5 COMPLETE, AGENCY-PROFILE-TRUTH-AUDIT COMPLETE
**P5 result:** 5 dental domains → 2 cards (glenferriedental, dentalaspects). 8 messages across 4 channels. Exit gate MET.
**Next directive:** TBD (critic timeout tuning, BDM enrichment bottleneck, P1.5-OUTBOUND-READINESS)
**Test baseline:** 1505 passed, 1 failed (pre-existing campaign_flow), 28 skipped
**Last merged PR:** #373 (agency profile truth audit)

### EVO Track (Autonomous Loop — all complete)

| Stage | Title | Status |
|-------|-------|--------|
| EVO-001 | Foundation | Complete |
| EVO-002 | Foundation | Complete |
| EVO-003 | Prefect→Elliottbot callback bridge | Complete |
| EVO-004 | Dynamic Prefect flow generator | Complete |
| EVO-005 | Task queue consumer + API guardrails | Complete |
| EVO-006 | Live fire test + MCP servers | Complete |
| EVO-007 | Execution path fix (Railway orchestrates, VPS executes) | Complete |
| EVO-008 | Claude Code migration — OpenClaw retired 2026-04-07 | Complete |

Full autonomous loop verified: Prefect → evo_task_queue → VPS consumer → result written → Telegram alert. Loop latency: 1212s.

### Infrastructure State (as of 2026-04-15)

- **Harness:** Claude Code (EVO-008). OpenClaw retired permanently 2026-04-07.
- **MCP status:** 12/13 custom MCP servers active. keiramail (work email) + keiradrive (Google Drive) confirmed loaded.
- **Telegram bot:** Live. All CTO communication via Telegram (chat_id 7267788033). Terminal output not monitored.
- **crm-sync-flow:** Killed permanently 2026-04-08 (schema mismatch, flow removed from Prefect).
- **Prefect pool:** agency-os-pool, concurrency 10.
- **4-store save:** Automated via scripts/three_store_save.py. CI enforcement: .github/workflows/directive-save-check.yml. Session-end check: scripts/session_end_check.py.

### Governance Updates (2026-04-15)

- LAW XII (Skills-First Integration) restored
- LAW XIII (Skill Currency Enforcement) restored
- LAW XV-D: Step 0 RESTATE HARD BLOCK added to both CLAUDE.md files
- LAW XV: Four-Store Completion now mechanized via three_store_save.py (D1.8)
- LAW XVI: Clean Working Tree — report dirty tree before new directive work
- Session startup HARD BLOCK: Read Drive Manual via keiradrive_read_manual before any directive
- File-based memory (MEMORY.md, HANDOFF.md) deprecated — Supabase elliot_internal.memories is SOLE persistent memory
- 7 governance rules established (see Section 17): verify-before-claim, cost-authorization, pre-directive check, optimistic completion, audit-fix-reaudit cycle, four-store mechanism, letter-prefix convention
- Schema correction: ceo_memory and cis_directive_metrics are in PUBLIC schema (not elliot_internal)

### Pipeline Status

Integration test #300 passed all 11 stages. 730 AU domains (Dental, Construction, Legal) fully processed:

| Stage | In | Out | Notes |
|-------|----|-----|-------|
| 1 Discovery | — | 730 | DFS domain_metrics_by_categories |
| 2 Scrape | 730 | 730 | httpx primary (97.5% success), Spider fallback |
| 3 Comprehend | 730 | 730 | Sonnet website comprehension |
| 4 Affordability | 730 | 517 | Haiku gate — 29% rejected |
| 5 Intent | 517 | 370 | Sonnet — 28% NOT_TRYING rejected |
| 6 DM Identification | 370 | 260 | DFS SERP LinkedIn — 70% hit rate |
| 7 Email Waterfall | 370 | 228 | 32 Leadmagic-verified, 86 company HTML |
| 8 Mobile Waterfall | 370 | 87 | HTML regex only ($0 cost) |
| 9 LinkedIn Company | 370 | 117 | BD company scraper — 32% had LI URL |
| 10 LinkedIn DM Profile | BLOCKED | — | BD batch takes 30+ min — SLA issue |
| 11 Haiku Evidence + Draft Emails | 260 | 260 | $0.42 Haiku, full prospect cards |

**Total cost: ~$26 USD (~$40 AUD). Cost per qualified DM card: ~$0.10 USD (~$0.155 AUD)**

### Build Phase

Sprints 0–6 complete (#279–#306). All core pipeline modules built:
- Discovery engine (DFS domain_metrics_by_categories, multi-category rotation)
- Free intelligence sweep (httpx scrape, DNS/MX, ABN registry)
- Paid enrichment (DFS GMB, DFS SERP, Google Ads)
- Two-dimension scoring (Affordability + Intent, 4 bands each)
- DM identification waterfall (DFS SERP LinkedIn 70%, BD fallback)
- Email waterfall (4 layers: HTML / pattern / Leadmagic / BD)
- Mobile waterfall (3 tiers: HTML regex / ABN phone / Leadmagic)
- Social enrichment (LinkedIn company + DM profile via BD)
- Intelligence layer (5-stage Sonnet/Haiku, prompt caching)
- Stage-parallel orchestrator (9 semaphore-controlled concurrent stages)
- Haiku evidence refinement + draft email generation (Stage 11)
- Marketing Vulnerability Report (Stage 7c — Directive #306)

### Current Phase

**Testing + provider resolution.**

- 87% of emails unverified (pattern/HTML only — no SMTP confirmation)
- ContactOut: subscribed ($49/mo), API key demo-locked — waiting on support
- Forager: best APAC benchmarks, API key returns 404 — waiting on support
- Reacher: open source SMTP verifier, Docker ready, port 25 blocked on Vultr AND Railway
- Leadmagic mobile: 0% AU coverage — dead for mobile enrichment
- Stage 10 (LinkedIn DM profiles): BD batch takes 30+ min for 260 URLs — SLA unresolved

### Blocking Items

| Blocker | Owner | Status |
|---------|-------|--------|
| ContactOut API key demo-locked | Dave | Waiting on ContactOut support |
| Forager API 404 | Dave | Waiting on Forager support |
| Reacher port 25 blocked (Vultr + Railway) | Dave | Needs dedicated VPS or Oracle Cloud free tier |
| BD LinkedIn DM batch SLA (30+ min for 260 URLs) | Dave | Needs BD support ticket |
| Email verification: 87% unverified | — | Blocked on above provider resolutions |

---

## SECTION 3 — PIPELINE ARCHITECTURE (v7, proven Apr 2026)

### Team Roster (Multi-Instance Operation, LAW XVII)

| Callsign | Workspace | Branch | Telegram Bot | Service | Created |
|----------|-----------|--------|--------------|---------|---------|
| **ELLIOT** | `/home/elliotbot/clawd/Agency_OS/` | main + feature branches | existing | `telegram-chat-bot.service` (active) | 2026-04 (origin) |
| **AIDEN** | `/home/elliotbot/clawd/Agency_OS-aiden/` | `aiden/scaffold` (does not merge to main) | `@Aaaaidenbot` | `aiden-telegram.service` (registered, awaiting Dave enable) | 2026-04-16 |

Each callsign reads its own `./IDENTITY.md` at session start. Workspace isolation via git worktree + per-worktree CLAUDE.md + `--setting-sources=project`.

Core principle: Agency sells services. Prospects have problems. Industry is irrelevant to the match. Geography is a delivery constraint. Signals are the discovery engine.

### DISCOVERY

**Single source:** DFS `domain_metrics_by_categories`
- $0.10 per 100 domains ($0.012 amortised per domain after AU TLD filtering)
- Categories run in parallel via `asyncio.gather`, DFS calls within category sequential
- `GLOBAL_SEM_DFS=28` ceiling (peak observed: 10 for 10 categories)
- Sampling: AU-TLD + ETV window filter FIRST, then take middle 10 of AU SMB pool (~30% position)
- 22,592 AU dental domains confirmed, 31,445 AU plumbing — pool never exhausts
- Monthly rotation across categories — refill loop at threshold=20, stops on target_reached
- `claimed_by` exclusion applied at discovery — never returns already-claimed domains
- 15 AU categories active across 14 verticals (dental, trades, legal, construction, hospitality, automotive, real estate, accounting, medical, fitness, hair & beauty, veterinary, HVAC, marketing)
- **RATIFIED 2026-04-13:** 100 domains across 10 categories in 41.2s, $1.20. Ignition (60 cats) projected 4.1 min.

### Category ETV Windows (Calibrated #328.1, Apr 11 2026)

Per-category organic traffic value windows measured empirically across 21 DFS categories. Replaces the prior universal 100-5000 window which was only correct for ~2/21 categories. Canonical source: `src/config/category_etv_windows.py`. CI guard: `tests/ci_guards/test_no_hardcoded_etv.py` rejects hardcoded ranges.

| Code | Category | ETV Min | ETV Max | $/KW | Sample |
|------|----------|---------|---------|------|--------|
| 10020 | Dining & Nightlife | 7,605 | 1,503,904 | 21.58 | 897 |
| 10123 | Fitness | 1,171 | 262,498 | 5.50 | 1,434 |
| 10163 | Legal | 1,128 | 153,118 | 3.25 | 1,208 |
| 10193 | Vehicle Repair & Maintenance | 864 | 102,580 | 4.64 | 1,493 |
| 10282 | Building Construction & Maintenance | 6,578 | 641,326 | 6.83 | 1,478 |
| 10333 | Hair Salons & Styling Services | 1,645 | 187,963 | 7.83 | 1,043 |
| 10418 | Home Heating & Cooling | 32 | 19,484 | 1.42 | 743 |
| 10514 | Dentists & Dental Services | 813 | 39,684 | 6.21 | 1,449 |
| 10520 | Hospitals & Health Clinics | 886 | 72,618 | 8.46 | 1,323 |
| 10531 | Real Estate Investments | 140 | 13,454 | 2.08 | 372 |
| 11093 | Accounting & Auditing | 365 | 176,701 | 2.35 | 1,425 |
| 11138 | Building Painting Services | 116 | 26,609 | 2.23 | 812 |
| 11147 | HVAC Service & Repair | 59 | 25,433 | 2.79 | 898 |
| 11284 | HVAC & Climate Control | 305 | 65,747 | 3.23 | 1,490 |
| 11295 | Electrical Wiring | 158 | 19,777 | 2.58 | 808 |
| 11979 | Veterinary | 379 | 68,772 | 5.05 | 1,457 |
| 12049 | Fitness Instruction Training | 4 | 10,638 | 0.88 | 263 |
| 12391 | Bookkeeping | 964 | 130,487 | 2.75 | 217 |
| 12975 | Restaurant Reviews & Listings | 765 | 144,863 | 17.36 | 973 |
| 13462 | Plumbing | 826 | 175,251 | 4.10 | 1,460 |
| 13686 | Attorneys & Law Firms | 426 | 67,159 | 2.68 | 1,144 |

Total: 21 categories, 22,387 calibration samples. Methodology: 20 DFS Labs pages/category (100 domains/page), junk floor applied, SMB band = p20-p95, window = (p20*0.8, p95*5.5). Universal 100-5000 was only approximately correct for Real Estate Investments and Electrical Wiring.

PR: #295 (merged Apr 11 2026). Directive: #328.1.

### Per-Stage Parallelism (Canonical Config)

Canonical source: `src/config/stage_parallelism.py`. Helpers: `get_parallelism(stage_key)` returns concurrency int, `get_stage_config(stage_key)` returns full dict. Same pattern as `category_etv_windows.py`. Provider ceilings from Directive #337 concurrency audit. Created 2026-04-13.

### SCRAPING

**Primary:** httpx (`src/integrations/httpx_scraper.py`)
- sem=80, persistent client, 0.23s average, 97.5% success rate
- Contact data extracted at scrape time (contact_data: company_email, company_phone, social links)
- **Fallback:** Spider.cloud for JS-rendered pages (~10% of domains)

### INTELLIGENCE LAYER (5-stage Sonnet/Haiku)

All stages in `src/pipeline/intelligence.py`. Prompt caching (`cache_control: ephemeral`) on all system prompts — ~90% token discount on repeated calls.

| Stage | Function | Model | Cost/domain | What it produces |
|-------|----------|-------|-------------|-----------------|
| 3 | `comprehend_website()` | Sonnet | ~$0.0165 | Services, tech signals, maturity, location signals, pain indicators |
| 4 | `judge_affordability()` | Haiku | ~$0.00056 | Affordability band + hard gate decision |
| 5 | `classify_intent()` | Sonnet | ~$0.0084 | Intent band, evidence statements, score |
| 5b | `analyse_reviews()` | Sonnet | ~$0.005 | Sentiment trend, pain themes (not yet wired to GMB deep reviews) |
| 7c | `generate_vulnerability_report()` | Sonnet | ~$0.02–0.03 | 6-section Marketing Vulnerability Report: search visibility, technical SEO, backlinks, paid ads, reputation, competitive position |
| 11 | `refine_evidence()` | Haiku | ~$0.003 | Headline signal, recommended service, outreach angle, draft email subject + body |

**Stage 7c — Marketing Vulnerability Report** runs after intent classification and before evidence refinement. Sonnet reads all available intelligence (ads, GMB, competitors, backlinks, brand SERP, indexed pages, website comprehension) and returns a structured JSON report with grades (A–F), specific findings, a priority action, and a 3-month roadmap. Stored as `vulnerability_report` dict on `ProspectCard`. Feeds into Haiku evidence refinement so draft emails can reference report findings.

`refine_evidence` context includes: `business_name`, `dm_name`, `dm_title`, `location`, `category`, GMB signals, LinkedIn company/DM data. Draft emails address DM by first name.

### SCORING: TWO DIMENSIONS

**Dimension 1 — Affordability** (`score_affordability()`)
Hard gates (reject): sole_trader, gst=False, unreachable (no website + no ABN)
Soft signals: entity_type, GST registered, professional email, CMS, SSL, multi-page
Max score: ~10 | Gate: ≥3
Bands: LOW (reject) | MEDIUM | HIGH | VERY_HIGH

**Dimension 2 — Intent** (`score_intent_free()` + `score_intent_full()`)
Free signals (from website HTML — zero API cost):

| Signal | Trigger | Points |
|--------|---------|--------|
| website_no_analytics | has website but no GA4/GTM | 2 |
| ads_tag_no_conversion | AW- tag in HTML, no conversion tracking | 3 |
| booking_no_analytics | booking system, no analytics | 2 |
| meta_pixel | Facebook Pixel present | 1 |
| social_links | team page or social links | 1 |
| stale_cms | professional CMS present | 1 |

Free gate: NOT_TRYING band skips all paid enrichment.

Paid signals (gate passers only):

| Signal | Source | Cost | Points |
|--------|--------|------|--------|
| running_gads | DFS Ads Search | $0.002 | 2 |
| gmb_established | GMB review count > 20 | $0.0035 | 1 |

Bands: NOT_TRYING (0–2, skip paid) | DABBLING (3–4) | TRYING (5–7) | STRUGGLING (8+)

### INTELLIGENCE ENDPOINTS (post-intent-gate, Directive #303)

Runs in parallel via `asyncio.gather` + `GLOBAL_SEM_DFS` after intent gate. Only processes domains that passed NOT_TRYING rejection.

| Endpoint | Method | Cost | Stores |
|----------|--------|------|--------|
| DFS Competitors Domain | `competitors_domain()` | $0.01 | `competitors_top3`, `competitor_count` |
| DFS Backlinks Summary | `backlinks_summary()` | $0.02 | `referring_domains`, `domain_rank`, `backlink_trend` |
| DFS Brand SERP | `brand_serp(business_name)` | $0.002 | `brand_position`, `brand_gmb_showing`, `brand_competitors_bidding` |
| DFS Indexed Pages | `indexed_pages(domain)` | $0.002 | `indexed_pages_count` |

Total added cost per domain: **$0.034**. Results written to BU + returned in `stats["intelligence_enriched"]`.
These fields feed the **Vulnerability Report** (designed, not yet built — see Section 9).

### DM IDENTIFICATION

**T-DM1 — DFS SERP site:linkedin.com/in**
- Hit rate: 70.3% | Cost: $0.01/query
- AU location filter: prefers au.linkedin.com; accepts AU state in snippet; rejects non-AU
- Title priority: owner > founder > director > principal > ceo > partner
- Contamination check: ALL CAPS names = company profile (rejected); non-AU LinkedIn on .au domain (rejected)

**T-DM2 — Bright Data LinkedIn company dataset** (fallback)
- Dataset: gd_l1vikfnt1wgvvqz95w | Cost: $0.00075/record

**T-DM3 — Website team page** (free fallback)
**T-DM4 — ABN entity name** (free, LOW confidence)

### EMAIL WATERFALL (4 layers, `src/pipeline/email_waterfall.py`)

Short-circuits on first hit. DM name-match gate on Layers 0 + 1 — rejects company emails where local part does not contain a name component from dm_name.

| Layer | Source | Cost | Verified? |
|-------|--------|------|-----------|
| 0 | Contact registry (HTML scrape, name-match gated) | FREE | No |
| 1 | Website HTML (mailto: + regex, name-scored) | FREE | No |
| 2 | Leadmagic /email-finder | $0.015 | Yes (SMTP) |
| 3 | Bright Data LinkedIn profile | $0.00075 | No |

`GLOBAL_SEM_LEADMAGIC = 10`

Placeholder filter at card assembly (both `dm_email` and `company_email`): rejects `example@`, `test@`, `you@`, `@example.com`, `@mail.com`, etc.

### CONTACT COVERAGE (from #300 integration test, 370 DMs attempted)

| Channel | Count | Rate | Notes |
|---------|-------|------|-------|
| Email found | 228 | 96% | 13% verified (Leadmagic), 87% unverified |
| Email Leadmagic-confirmed | 32 | 14% | SMTP verified |
| Mobile | 87 | 23% | HTML regex only ($0) — Leadmagic AU coverage = 0% |
| LinkedIn DM URL | 260 | 70% | T-DM1 SERP hit rate |
| LinkedIn Company | 117 | 32% | BD scraper (only 32% had company URL in scrape data) |

### PARALLEL WORKERS (global semaphore pool)

All defined in `src/pipeline/pipeline_orchestrator.py`:

| Semaphore | Limit | Controls |
|-----------|-------|---------|
| `SEM_DFS` | 28 | All DFS API calls |
| `SEM_SCRAPE` | 80 | httpx + Spider scrapes |
| `SEM_SONNET` / `GLOBAL_SEM_SONNET` | 55 | Claude Sonnet calls |
| `SEM_HAIKU` / `GLOBAL_SEM_HAIKU` | 55 | Claude Haiku calls |
| `SEM_ADS_SCRAPER` | 15 | Google Ads Transparency scraper |
| `GLOBAL_SEM_LEADMAGIC` | 10 | Leadmagic API calls |

### PROSPECT CARD FORMAT (Stage 11 output)

Each card contains: domain, category, business_name, location, intent_band, intent_score, dm_name, dm_title, dm_email, dm_email_verified, dm_mobile, dm_linkedin, company_email, landline, channels_available, headline_signal, recommended_service, outreach_angle, evidence_statements (2–5), draft_email_subject, draft_email_body.

**Location fields (Directive #305):** `location_suburb`, `location_state`, `location_display` ("Surry Hills, NSW"). Waterfall: GMB address → JSON-LD → ABN postcode → state hint → "Australia".

### CARD QUALITY WATERFALLS (Directive #305)

**Business name waterfall** (`resolve_business_name()` in `pipeline_orchestrator.py`):
1. ABN `trading_name` (if not just entity suffixes like "Pty Ltd")
2. GMB business name
3. ABN `legal_name` (cleaned)
4. Page title prefix (from `company_name` field)
5. Domain stem (e.g. "dental1" → "Dental1")

ABN result dict now includes `abn_trading_name` + `abn_legal_name` (added to `_abn_result_from_row()` in `free_enrichment.py`).

**Location waterfall** (`resolve_location()` in `pipeline_orchestrator.py`):
1. GMB address — parsed for suburb and state abbreviation
2. JSON-LD `website_address` suburb + state
3. ABN postcode → state (via `_postcode_to_state()`)
4. State hint from enrichment
5. "Australia" fallback only when all above fail

**Placeholder filter** (`is_placeholder_email()` / `is_placeholder_phone()` in `email_waterfall.py`):
- Blocklist: 16 known placeholder emails (`example@mail.com`, `you@mail.com`, etc.)
- Pattern filter: rejects emails with local part matching `example|yourname|placeholder|test|yourdomain`
- Phone blocklist + all-same-digit + sequential digit rejection
- Applied to Layers 0+1 of `discover_email()` (free layers only; Leadmagic/BD trusted)

### COST MODEL (proven, #300 integration test)

| Component | Cost |
|-----------|------|
| DFS discovery (amortised) | $0.001 |
| httpx scrape | FREE |
| DFS Ads Search | $0.002 |
| DFS Maps GMB | $0.0035 |
| DFS SERP LinkedIn (DM) | $0.01 |
| Sonnet comprehension + intent | $0.025 |
| Haiku affordability + evidence | $0.003 |
| **Total per qualified DM card** | **~$0.10 USD / ~$0.155 AUD** |

At Ignition (600 DMs): **~$60 USD / ~$93 AUD pipeline cost**
Month 1 all-in (pipeline + infra + outreach): **~$464 AUD per customer**

---


### Directive BU-DISCOVERY-RULE (PR #0, 2026-04-16)
BU Discovery Rule (ratified 2026-04-16): Once a domain is in business_universe, it is NEVER re-discovered via Stage 1. Stage 1 always excludes all BU entries and returns only virgin domains. Updates to existing BU rows happen via a separate refresh flow (re-runs Stages 4/6/9 in place). No exceptions for temporal staleness at discovery level. Customer-level ownership via claimed_by prevents cross-customer duplicates. Strategic vision post-capital: always-on inventory pipeline — discovers continuously in background, customer arrives and claims from pre-built BU inventory (instant delivery, no processing wait). BU moat compounds monotonically. Eventually BU becomes sellable product per Manual vision.
## SECTION 4 — TIERS + PRICING (ratified Mar 26 2026)

| Tier | Price AUD/mo | Records/mo | Founding (50% off) |
|------|-------------|------------|-------------------|
| Spark | $750 | 150 | $375 |
| Ignition | $2,500 | 600 | $1,250 |
| Velocity | $5,000 | 1,500 | $2,500 |

- **Dominance tier: REMOVED** from launch. No AU marketing agency needs 3,500 records at launch — reintroduce for recruitment/MSP expansion.
- **Every tier = full BDR.** All intelligence, all 4 channels, Haiku personalisation, full automation. Volume is the only differentiator.
- Non-linear pricing prevents tier stacking.

### Margins

Proven pipeline cost: ~$0.10 USD (~$0.155 AUD) per DM card.

| Tier | Records | Pipeline COGS (AUD) | Infra + Outreach (AUD) | Month 1 Total | Revenue | Month 1 Margin | Month 6+ Margin |
|------|---------|---------------------|----------------------|---------------|---------|----------------|----------------|
| Spark | 150 | ~$23 | ~$80 | ~$103 | $750 full / $375 founding | 86% / 73% | 97% / 94% |
| Ignition | 600 | ~$93 | ~$371 | ~$464 | $2,500 full / $1,250 founding | 81% / 63% | 96% / 93% |
| Velocity | 1,500 | ~$233 | ~$600 | ~$833 | $5,000 full / $2,500 founding | 83% / 67% | 95% / 91% |

Month 6+ margin assumes infra cost flat, outreach amortised — only pipeline COGS remain variable.

---

## SECTION 5 — CAMPAIGN MODEL (ratified Mar 26 2026)

- **Campaign = service the agency sells.** Discovery sweeps ALL DFS categories within the agency's service area for businesses showing signals they need that service.
- Industry and geography are optional **dashboard filters**, not campaign definitions.
- System finds prospects wherever they are — dentists, builders, lawyers — all in the same sweep.
- No campaign count limits per tier.

### Territory

No geographic exclusivity. One business, one agency. First to claim owns it via `claimed_by` on BU. Pipeline excludes already-claimed domains at discovery. Two agencies in the same city get different prospects.

### Monthly Cycle

1. **Re-score (days 1–2):** Re-scrape all prior-month rejects. Promote any that now pass (signal refresh). Zero discovery cost.
2. **Discover (days 2–3):** Fill remaining quota with fresh discovery across ALL categories within service area. Monthly rotation through categories. Pool never exhausts.
3. **Enrich + Score + DM (days 2–3):** Stage-parallel processing — all 11 stages concurrent per domain batch.
4. **Rank + Present (day 3):** Dashboard populates, sorted by intent score (STRUGGLING → TRYING → DABBLING).

### Approval Flow

- Agency reviews top 10 to confirm quality.
- Batch release: **"Release All" / "Review More" / "Release with Exceptions"**
- Month 2+: single Release button.
- Kill switch always visible.
- Full transparency: agency sees all prospects + all intelligence + all contacts.
- Export permitted — data is theirs.

---

## SECTION 6 — ONBOARDING (ratified Mar 26 2026)

Simple: "what do you sell, where do you operate."

1. **CRM connect** (HubSpot / GHL / Pipedrive / Close — OAuth)
2. System auto-extracts services from CRM deals + deal sizes
3. **LinkedIn connect** (Unipile OAuth) — communication style, connection exclusion list
4. Agency confirms services + sets service area (metro / state / national)
5. NO industry selection. NO ICP definition. System discovers across all categories within service area.
6. Dashboard populates LIVE — agency watches pipeline stages fill in real time

### Speed

- First card appears: ~90 seconds
- 50+ cards: 5–7 minutes
- Full tier quota: 5–15 minutes (depending on tier and Sonnet throughput)

### Optional Dashboard Filters

- Industry (dental, trades, legal, etc.)
- Geography (suburb, city, state)
- Intent band (STRUGGLING / TRYING / DABBLING)
- Recommended service (SEO, Google Ads, social media, etc.)

Filters are views only — they do not restrict discovery or billing.

---

## SECTION 7 — FOUNDING CUSTOMER STRUCTURE

- 20 founding spots at 50% lifetime discount
- $500 AUD refundable deposit to secure spot via Stripe Checkout
- Refund clause: fully refundable if product doesn't launch within 90 days or doesn't meet needs
- Dual CTA: pay deposit directly OR book demo call (Calendly/Cal.com)
- Post-deposit: thank you page, welcome email from Maya, private Slack/WhatsApp group, fortnightly progress updates
- Onboarding: sequential, 5 per week over 4 weeks
- Territory lock: first-claim priority on prospects in their market

---

## SECTION 8 — PROVIDER STACK (current state, Apr 2026)

### LIVE AND PROVEN

| Provider | What | Cost | Proven |
|----------|------|------|--------|
| DFS `domain_metrics_by_categories` | Domain discovery by AU industry category. Returns organic_etv, organic_keywords, category | $0.10/100 domains | 22,592 AU dental, 31,445 AU plumbing domains |
| DFS Maps SERP (GMB) | GMB rating, reviews, phone, address, hours | $0.002/query | 169/517 coverage. Rating + reviews flowing through pipeline. |
| DFS SERP Organic | site:linkedin.com/in DM search | $0.01/call (corrected from $0.002) | 70.3% DM hit rate across 730 domains |
| DFS Competitors Domain | Top 5 SERP competitors per domain — domains sharing organic keyword overlap | $0.01/domain | 100% AU coverage. **Wired in pipeline (#303).** Returns competitors_top3 + competitor_count. |
| DFS Brand SERP | Brand search presence — position, GMB knowledge panel, competitor bidding on brand | $0.002/domain | 100% AU coverage. **Wired in pipeline (#303).** Returns brand_position, brand_gmb_showing, brand_competitors_bidding. |
| DFS Indexed Pages | Approximate indexed page count via site: query | $0.002/domain | 100% AU coverage. **Wired in pipeline (#303).** Returns indexed_pages_count. |
| DFS Backlinks Summary | Referring domains, domain rank, backlink trend | $0.02/domain | 100% AU coverage. **Wired in pipeline (#303). #276 parser bug fixed** — data was at tasks[0].result[0] not items[]. |
| Google Ads Transparency | Binary: is business running Google Ads | FREE | 119/517 ads detected. Real-time scraper. |
| httpx website scraping | Tech stack, contact data, tracking pixels | FREE | 97.5% success rate, 0.23s average, 730-domain test |
| ABN registry (local JOIN) | GST status, entity type, registration date | FREE | 91% match rate on 730 domains |
| Social profile detection | Facebook, Instagram, LinkedIn from HTML | FREE | 100% coverage |
| DNS / MX / SPF | Email infrastructure maturity scoring | FREE | 100% coverage |
| Anthropic Sonnet (`claude-sonnet-4-5`) | Website comprehension + intent classification | $0.003/1K input tokens | 5 pipeline stages. Prompt caching active. |
| Anthropic Haiku (`claude-haiku-4-5-20251001`) | Affordability gate + evidence refinement + draft emails | $0.00025/1K input tokens | 2 pipeline stages. Draft emails with DM personalisation. |
| Salesforge | Email sending | — | Wired and ready |
| Unipile | LinkedIn outreach | — | Wired and ready |
| ElevenAgents | Voice AI (Australian TCP Code compliant) | — | Wired and ready |
| Bright Data LinkedIn Company | Company headcount, followers, activity | $0.0015/record | Working. 117/370 scraped in #300 test. |

### PROVEN BUT NOT YET IN PIPELINE

| Provider | What | Cost | Status |
|----------|------|------|--------|
| DFS Ranked Keywords | Keyword-level SEO gap analysis | $0.002/domain | 20% AU coverage — useful as enrichment where available, not reliable for gate |
| DFS Keyword Suggestions | Keyword opportunity discovery | $0.002/call | Untested at scale |
| DFS SERP keyword scraping | Broader keyword landscape | $0.002/call | Untested at scale. Part of keyword discovery Track B (designed, not built). |
| DFS Google Ads Detailed | Full ads keyword + spend breakdown | $0.05/domain | Untested. High value if AU coverage proves out. |
| DFS Historical Rank | Rank trajectory over time | varies | In codebase, never called. Coverage unknown for AU. |
| Google PageSpeed API | Core Web Vitals signals | FREE | Needs API key. Blocked — Dave action required. |

### CONTACT PROVIDERS — UNRESOLVED

| Provider | What | Cost | Status |
|----------|------|------|--------|
| ContactOut | Email + phone finder, strong AU coverage | $49/mo subscribed | **API key demo-locked.** Web dashboard works for AU. Waiting on support for production key. |
| Forager | Email + mobile, best APAC accuracy in benchmarks | [TBD] | **API key returns 404.** Waiting on Forager support. Highest priority when unblocked. |
| Leadmagic | Email finder: works ($0.015/call). Mobile: 0% AU coverage — dead for mobile. | $0.015 email / $0.077 mobile | Email: live in pipeline. Mobile: do not use for AU. |
| Datagma | Email + phone, AU fallback option | $32/mo, 600 credits | Last resort — lower AU accuracy than ContactOut/Forager. |
| Reacher | Open source SMTP email verifier (Docker) | FREE | Docker image ready. **Port 25 blocked on Vultr AND Railway** (standard cloud policy). Needs dedicated VPS with port 25 unblocked, or Railway Pro, or Oracle Cloud free tier. |

### DEAD — DO NOT USE

| Provider | Reason | Confirmed |
|----------|--------|-----------|
| DFS Domain Technologies | 1.3% AU coverage (1/78 domains). Unusable for tech gap signals. | Mar 2026 live test |
| DFS paid_etv | AU: top dental domain = $150/mo. Cannot distinguish SMB budget. | Mar 2026 live test |
| Kaspr | Replaced by Leadmagic | Directive #167 |
| Hunter.io | Replaced by Leadmagic | Directive #167 |
| Proxycurl | Dead — LinkedIn lawsuit | Directive #167 |
| ZeroBounce | Never used in v7. Not needed while Reacher blocked. | — |
| Spider.cloud (as primary) | Replaced by httpx. Kept as JS fallback only (~10% of domains). | Directive #295 |

---

## SECTION 9 — DECISIONS PENDING

Items that are designed, blocked, or awaiting external resolution before build can proceed. Each item must be resolved (or formally de-scoped) before the next launch-gate is passed.

### Contact Provider Resolution (Dave action required)

**Email verification — 87% of pipeline emails are unverified.**
Three paths exist; all blocked:
- **Reacher (SMTP):** Docker image ready on Railway. Port 25 blocked on Vultr, Railway Standard, and all standard managed cloud. Needs a dedicated VPS with port 25 unblocked (e.g. Oracle Cloud free tier, Hetzner, Linode) or Railway Pro with custom networking. Dave to provision.
- **ContactOut:** $49/mo subscribed. Web dashboard confirms AU coverage is strong. API key is demo-locked — production key not provisioned. Dave to follow up on support ticket.
- **Forager:** Best APAC accuracy in independent benchmarks. API key returns 404. Dave to follow up on support ticket. Highest priority when unblocked.

Until one of these is resolved, email channel goes out unverified. Acceptable for initial testing; not acceptable for at-scale live outreach.

### DFS Intelligence Endpoints

**WIRED (Directive #303, PR #266):** Competitors Domain, Backlinks Summary, Brand SERP, Indexed Pages. All four run in parallel after the intent gate via `asyncio.gather + GLOBAL_SEM_DFS`. Data flows to ProspectCard and BU columns.

**NOT YET WIRED:**

| Endpoint | Signal | Cost | Build needed |
|----------|--------|------|-------------|
| DFS Google Ads Detailed | Full keyword + spend breakdown (supplements binary Transparency signal) | $0.05/domain | Evaluate AU coverage before wiring — expensive if low |
| DFS On-Page SEO | On-page signals — meta, H1, schema | $0.002/domain | Untested. Evaluate AU coverage first. |

The **Vulnerability Report** (structured gap analysis showing exactly where a prospect's marketing fails vs competitors) now has all its data dependencies satisfied. It is designed but not yet built as a rendered output.

### Keyword Discovery Architecture — Designed, Not Tested

Dual-track discovery designed to supplement `domain_metrics_by_categories`:
- **Track A (category):** Current pipeline. DFS `domain_metrics_by_categories` — returns domains ranking in a category. Proven.
- **Track B (keyword SERP):** DFS SERP scraping for target keywords (e.g. "plumber sydney") — returns domains actively competing for commercial intent searches. Untested at scale.

Track B fills a gap: businesses with good SEO but no organic keyword volume (new businesses, service-area businesses) are invisible to Track A. Track B catches them.

Estimated cost: ~$5/customer/month added to pipeline COGS at Ignition tier (600 records × ~$0.008/keyword SERP call).
Status: Architecture designed, code not written, not tested.

### Client Monitoring — Designed, Not Built

Weekly refresh loop per active agency client:
1. Re-run DFS enrichment on all in-pipeline prospects (detect signal changes)
2. Delta detection: did their ads start/stop? GMB rating change? New reviews?
3. Alert generation: surface prospects whose situation changed since last month

Use case: a prospect who was DABBLING last month is now running 15 ads — they've entered the buying window. System surfaces them to the agency automatically.

Architecture: designed. Code: not written. Depends on BU lifecycle schema (see below).

### BU Lifecycle Schema — Designed, Not Built

The `business_universe` table currently tracks discovery and pipeline state. It does not track outreach history, response signals, or client monitoring state.

Fields needed (not yet in schema):
- `outreach_status`: pending / active / replied / converted / suppressed
- `last_outreach_at`: timestamp per channel
- `signal_snapshot_at`: when signals were last re-checked
- `signal_delta`: JSON diff of what changed since last check
- `agency_notes`: freetext field for human annotations

Status: schema designed in ceo_memory (`ceo:bu_lifecycle_schema`). Migration not written. Build depends on outreach execution being live-tested first.

### Vertical Config Architecture — Designed, Not Built

The pipeline currently has one hardcoded signal config (`marketing_agency` vertical). For multi-vertical launch (recruitment, MSPs, accounting, etc.), the pipeline needs to be vertical-agnostic — loading config from a `vertical_config` JSON per customer.

Design: `vertical_config.json` per vertical → pipeline loads at runtime → scoring weights, category codes, service mappings, and DM title priorities all vary by vertical.
Status: Design ratified. `signal_configurations` table exists. Migration for non-marketing verticals not written. Not a blocker for marketing agency launch.

### Landing Page — Built, Incomplete

`agency_os_v5.html` exists with Bloomberg aesthetic and "Who built yours?" hero copy. Three things missing before external use:
- **Vertical tabs:** currently marketing-agency only. Add recruitment/MSP/accounting tabs with vertical-specific copy.
- **Remotion video:** dashboard animation and Maya walkthrough. Assets not rendered.
- **Stripe Checkout:** pricing CTAs link to nothing. Dave to add Stripe product IDs.

### Dave's LinkedIn Profile

Critically underdeveloped before any external outreach begins. The outreach sequences reference the agency founder — if Dave's LinkedIn doesn't reflect the product, conversion drops significantly. Needs: updated headline, current role (Agency OS founder), recent activity, headshot. Dave to update before first founding customer outreach.

---

## SECTION 10 — DATA PROVIDER OPERATIONAL NOTES

- BD GMB dataset: `gd_m8ebnr0q2qlklc02fz` (Google Maps full information). Discovery mode: `type=discover_new&discover_by=keyword`. Enrichment mode: `discover_by=location` or `discover_by=place_id`.
- DFS spending cap: $50 USD/day — not a blocker for normal runs.
- AU suburb → lat/lng mapping: Elkfox CSV (`src/data/au_suburbs.csv`, MIT licensed, 16,875 records).
- BD API key location: `/home/elliotbot/clawd/Agency_OS/config/.env` key `636a81d7-4f89-4fb5-904b-f1e195ec20d2`.
- Leadmagic balance: check before large enrichment runs. AU mobile coverage = 0% — do not call `find_mobile()` for AU domains.

---

## SECTION 11 — OUTREACH STACK

| Channel | Provider | Status |
|---------|----------|--------|
| Email | Salesforge | Wired, ready |
| LinkedIn | Unipile | Wired, ready |
| Voice AI | ElevenAgents + Claude Haiku ("Alex") | Wired, ready |
| SMS | Telnyx | On hold until launch |

Voice AI / Alex details:
- Built on ElevenAgents + Claude Haiku (`claude-haiku-4-5-20251001`)
- Australian TCP Code compliance built in
- Mandatory recording disclosure as first spoken line
- Calling hour restrictions enforced programmatically
- Knowledge base card per prospect: company name, trigger, talking point, objective, fallback

---

## SECTION 12 — BUSINESS UNIVERSE

- BU is THE PRODUCT — one row per discovered business, all intelligence accumulates over time
- `abn_registry` = 2.4M ABR records, enrichment source only (not the BU itself)
- `campaign_leads` junction table for agency claims on prospects
- BU schema: ~97 columns. Key signal fields: `pipeline_stage`, `claimed_by`, `propensity_score`, `intent_band`, `outreach_messages`, `outreach_channels`, `dm_name`, `dm_email`, `dm_mobile`
- `claimed_by` exclusion: domains already claimed by another agency are excluded at Stage 1 discovery
- BU House Seed: 10% of campaign volume, gap-fill by default

---

## SECTION 13 — BUILD SEQUENCE (active)

v5 era (#247–#270): all 7 pipeline stages built on main. Superseded.
v6 era (#271–#277): Layer 2 (discovery), Layer 3 (bulk filter), signal config v6 built. Superseded by v7.

### v7 Sprint Plan (starts #279)

| Sprint | Directive(s) | What | Status |
|--------|-------------|------|--------|
| Sprint 0 | #279 | Clean house: delete 7 deprecated stage files, fix DNCR hard-block, verify test baseline 1032/0/28 | COMPLETE — PR feat/279-sprint0-cleanup |
| Sprint 1 | #280 | Discovery engine: rebuild layer_2_discovery.py → single domain_metrics_by_categories call, remove 4 dead sources | COMPLETE — PR #242 |
| Sprint 2 | #281–#282 | Free intelligence sweep: website scrape (Spider.cloud), DNS/MX/SPF/DKIM, ABN registry JOIN, free_enrichment.py | COMPLETE — PR #245 |
| Sprint 3 | #283 | Paid enrichment: affordability gate + DFS bulk metrics + DFS Maps GMB, paid_enrichment.py | COMPLETE — PR #246 |
| Sprint 4 | #284 | DFS date params fix + DiscoverySource enum (DOMAIN_CATEGORIES / MAPS_SERP stub) | COMPLETE — PR #247 merged |
| Sprint 4 | #285 | Free enrichment quality: ABN confidence, JSON-LD address, email maturity collapse, silent exception fix | COMPLETE — PR #248 merged |
| Sprint 4 | #286 | DM Identification: BrightDataLinkedInClient + DMIdentification pipeline (4-tier fallback) | COMPLETE — PR #249 merged |
| Sprint 4 | #287 | SERP-first DM waterfall: DFS SERP T-DM1 (70% hit), BD T-DM2, AU location filter | COMPLETE — PR #250 merged |
| Sprint 5 | #288 | Composite affordability scorer (7 signals, 4 bands) + streaming PipelineOrchestrator + ProspectCard | COMPLETE — PR #251 merged |
| Sprint 5 | #289 | ABN multi-strategy matching waterfall (4 strategies, 8/10 live match rate) | COMPLETE — PR #252 merged |
| Sprint 5 | #290 | Wire orchestrator: pull_batch + enrich methods, DFS Maps GMB, ads transparency real | COMPLETE — PR #253 merged |
| Sprint 5 | #284–#291 | Discovery + enrichment quality + DM waterfall + scoring + ads detection + pipeline orchestrator | ALL COMPLETE — PRs #247–#254 |
| Sprint 6 | #292 | Architecture alignment: Manual final architecture + ABN Settings bug fix | COMPLETE |
| Sprint 6 | #293 | Stage-parallel pipeline refactor (SEM_SPIDER=15, SEM_ABN=1, SEM_PAID=20, SEM_DM=20) | COMPLETE — PR #255 |
| Sprint 6 | #294 | Multi-category rotation (15 categories, 5/month, monthly wrap) + exclude_domains + category_stats | COMPLETE — PR #256 |
| Sprint 6 | #295 | httpx primary scraper + GMB rating fix + AU country filter + parallel worker orchestrator | COMPLETE — PR #257 |
| Sprint 6 | #296 | Sonnet/Haiku intelligence layer: 5-stage comprehend/afford/intent/reviews/evidence. Prompt caching. | COMPLETE — PR #258 |
| Sprint 6 | #297 | ABN matching audit: confirmed working on main (2.4M rows, live match verified). 11 tests. | COMPLETE — PR #259 |
| Sprint 6 | #298 | Multi-category service-first discovery: category_registry.py, MultiCategoryDiscovery, 14 verticals | COMPLETE — PR #260 |
| Sprint 6 | #299 | Email discovery waterfall: 4 layers (HTML/pattern/Leadmagic/BD), Stage 9 wired. 16 tests. | COMPLETE — PR #261 merged |
| Sprint 6 | #300 | Integration test: all 11 stages, 730 domains, 260 DM cards, $26 total | COMPLETE |
| Sprint 6 | #300-FIX | 14 quality fixes (Stages 1–6): AU filter, GMB scraper, DM filter, contact registry | COMPLETE — PR #264 merged |
| Sprint 6 | #300-FIX-2 | Contact data schema split: company_* vs dm_* fields | COMPLETE |
| Sprint 6 | #300-FIX-3 | Leadmagic mobile 0% AU coverage diagnosed. Email pattern diagnosis. | COMPLETE |
| Sprint 6 | #300-FIX-4 | _parse_name rebuilt (Dr./Prof. prefix, LinkedIn noise). Email waterfall: pattern as Leadmagic hint only. | COMPLETE |
| Sprint 6 | #300-FIX-5 | Placeholder email filter. Stages 9+10 run. BD API key corrected. | COMPLETE |
| Sprint 6 | #300-FIX-6 | Draft emails: business_name/dm_name/location passed to refine_evidence. Business name chain + location chain. BD snapshot merged. | COMPLETE — commit ecbe0b9 |
| Sprint 6 | #300-FIX-8 | AU location filter on lidm.location. DM name-email match gate (email_waterfall L0). company_email placeholder scan. | COMPLETE — PR fad25df |
| Sprint 6 | #301 | SMTP email verifier (email_verifier.py, 13 patterns, MX resolution). Railway Reacher deployed. Port 25 blocked everywhere. | COMPLETE — committed |
| Testing | #302 | Manual full rewrite: Sections 2–8 + Section 9 Decisions Pending | COMPLETE — PR #265 merged |
| Testing | #303 | Wire four intelligence endpoints: Competitors, Backlinks, Brand SERP, Indexed Pages. Fix #276 backlinks parser. ProspectCard +9 fields. 11 new tests. | COMPLETE — PR #266 merged |
| Testing | #304 | Keyword discovery test: 382 domains, 83.8% AU, $0.25 cost. Track B validated. | COMPLETE — test only |
| Testing | #304-FIX | Fix domain_metrics_by_categories: second_date exceeded available_history window. Dynamic _get_latest_available_date() with session cache. Discovery restored. | COMPLETE — PR #267 merged |
| Testing | #305 | Card quality: business name waterfall, location waterfall (suburb+state+display), placeholder email/phone filter. 13 new tests. | COMPLETE — PR #268 merged |
| Testing | #306 | Marketing Vulnerability Report: generate_vulnerability_report() Sonnet Stage 7c, 6 sections, grades + roadmap, wired in both run() and run_parallel(). vulnerability_report on ProspectCard. 8 tests. | PR #269 open |

| Calibration | #328.1 | Canonical category ETV windows: 21 categories calibrated empirically (22,387 samples). CI guard added. Universal 100-5000 retired. | COMPLETE — PR #295 merged Apr 11 |
| Phase 0 | F2.1-F7 | Foundation sprint: RLS, dm_messages, vulnerability_report column, evo_flow_callbacks, agent_comms | COMPLETE — PRs #300-#302 merged |
| Phase 1 | P1/P1.5 | Stage 10 message gen (Sonnet email + Haiku others) + Stage 9 VR enrichment | COMPLETE — PRs #304, #305 merged |
| Phase 1 | P1.6 | BDM dedup + blocklist enforcement + name hygiene | COMPLETE — PR #307 merged |
| Phase 1 | P1.7 | NULL-URL BDM cleanup + write-path guards + AU TLD enforcement | COMPLETE — PR #309 |
| Phase 1 | HOTFIX-01 | Decimal serialization + pgbouncer pool compatibility | COMPLETE — PR #306 merged |
| Phase 1 | P4 | Prefect flow for automated Stage 9→10 pipeline | COMPLETE — PR #308 merged |
| Phase 1 | P5 | E2E automated live-fire: 25 BDMs, 97/100 dm_messages | COMPLETE — $1.56 USD |
| Process | M-PROCESS-01 | Directive contract discipline ratified — see AGENTS.md. CTO must STOP and report when directive constraint is infeasible, not autonomously alter methodology. | RATIFIED 2026-04-13 |
| Process | STYLE | Directive style: CEO specifies outcome + constraints + gates; CTO engineers fastest compliant path. | RATIFIED 2026-04-13 |
| Stage 1 | S1 | Stage 1 ratified. 41.2s for 100 domains across 10 categories via parallel asyncio.gather. Middle-of-AU-SMB-pool sampling. Baseline locked for Stage 2 input. | RATIFIED 2026-04-13 |
| Config | stage_2_abn_gst | stage_2_abn_gst added to stage_parallelism.py (50 concurrent, local JOIN). Audit flagged legacy key stage_2_scrape may be obsolete — preserved pending Pipeline E full ratification. | 2026-04-13 |

### Post-Test Build Queue (next priorities after provider resolution)

1. Expanded signals: GMB deep review scrape, Sonnet prompt expansion for comprehension
2. BU lifecycle schema: status fields for outreach tracking
3. Connection pool optimisation
4. ContactOut / Forager integration (when API keys unblocked)
5. Email verification (when Reacher / port 25 resolved)

### Completed Directives Log

| Directive | What | Status |
|-----------|------|--------|
| #271 | Signal config schema v6 (migration 029 + model + 6-service seed) | COMPLETE — PR #235 merged |
| #272 | Layer 2 discovery engine (5-source — now superseded by v7) | COMPLETE — PR #236 merged |
| #273 | Fix DFS SERP test failures | COMPLETE — PR #237 merged |
| #274 | Layer 3 bulk filter (now superseded by v7) | COMPLETE — PR #238 merged |
| #275 | asyncpg JSONB codec fix | COMPLETE — PR open (branch feat/275-asyncpg-jsonb-codec) |
| #277 | Codebase audit (92 components, all sections) | COMPLETE — docs/v7-audit-results.md |
| #278 | v7 architecture alignment | COMPLETE |
| #283 | Sprint 3: Paid enrichment + affordability gate | COMPLETE — PR #246 merged |
| #284 | DFS date params fix (first_date/second_date) + DiscoverySource enum | COMPLETE — PR #247 merged |
| #285 | Free enrichment quality: ABN confidence, JSON-LD address, EmailMaturity enum, silent exception fix | COMPLETE — PR #248 merged |
| #286 | DM Identification: BrightDataLinkedInClient + DMIdentification pipeline (4-tier fallback T-DM1→T-DM3) | COMPLETE — PR #249 merged |
| #287 | SERP-first DM waterfall: DFS SERP site:linkedin.com/in as T-DM1 (70% hit), BD as T-DM2, AU location filter | COMPLETE — PR #250 merged |
| #288 | Composite affordability scorer (AffordabilityScorer, 7 signals, 4 bands) + PipelineOrchestrator + ProspectCard | COMPLETE — PR #251 merged |
| #289 | ABN multi-strategy matching: 4-strategy waterfall, domain/title/suburb/live-API, PTY LTD stripping, 8/10 live match rate | COMPLETE — PR #252 |
| #290 | Orchestrator wiring: pull_batch + enrich methods, DFS Maps GMB (maps_search_gmb), ads transparency real | COMPLETE — PR #253 merged |
| #291 | Two-dimension ProspectScorer: score_affordability + score_intent_free + score_intent_full. DFS Ads Search ($0.002/call). Spider AW-tag/Meta Pixel detection (free). | COMPLETE — PR #254 |
| #292 | Manual final architecture (ratified Mar 30 2026) + ABN Settings.abn_lookup_guid fix + PR #252 merge | COMPLETE |
| #293 | Stage-parallel orchestrator: 9-stage concurrent processing, SEM_SPIDER=15/SEM_ABN=1/SEM_PAID=20/SEM_DM=20 | COMPLETE — PR #255 |
| #294 | Multi-category rotation: 15 AU categories, 5/month rotation, exclude_domains, category_stats | COMPLETE — PR #256 |
| #295 | httpx primary scraper (Spider fallback), GMB rating dict→scalar fix, AU country filter, run_parallel() + global semaphore pool | COMPLETE — PR #257 |
| #296 | Sonnet/Haiku intelligence layer: comprehend_website, classify_intent, analyse_reviews, judge_affordability, refine_evidence. Wired into run_parallel(). Prompt caching. | COMPLETE — PR #258 |
| #297 | ABN matching audit: confirmed working on main (2.4M rows, live match verified). PR #249 abandoned (6k lines behind). 11 verification tests. | COMPLETE — PR #259 |
| #298 | Multi-category service-first discovery: category_registry.py, MultiCategoryDiscovery, run_parallel(discover_all=True). 14 verticals, 20 codes. 13 tests. | COMPLETE — PR #260 |
| #299 | Email discovery waterfall: 4 layers (HTML/pattern/Leadmagic/Bright Data), GLOBAL_SEM_LEADMAGIC=10, ProspectCard email fields, Stage 9 wired. 16 tests. | COMPLETE — PR #261 merged |
| #300 | Integration test: all 11 stages, 730 domains, 260 qualified DM cards, ~$26 USD total, ~$0.10/card | COMPLETE |
| #300-FIX | 14 quality fixes across Stages 1–6: AU filter, GMB scraper fix, DM company profile filter, contact registry split, httpx persistent client, social enrichment | COMPLETE — PR #264 merged |
| #300-FIX-2 | Contact data schema split: company_* fields from HTML scrape vs dm_* from paid waterfalls | COMPLETE |
| #300-FIX-3 | Diagnosed: Leadmagic mobile 0% AU coverage, pattern email 20% confirm rate, _parse_name bugs | COMPLETE |
| #300-FIX-4 | _parse_name rebuilt (Dr./Prof./Mr./Mrs., LinkedIn noise, role words). Email waterfall: pattern as Leadmagic hint only, verified=True on Leadmagic/BD only. | COMPLETE |
| #300-FIX-5 | Placeholder filter expanded. Stage 9 BD company scrape ran (117/370). Stage 10 blocked on BD batch timeout. BD API key corrected (636a81d7). | COMPLETE |
| #300-FIX-6 | refine_evidence context: business_name, dm_name, dm_title, location, category passed. Business name chain (lico→dm_title→lidm→title tag→stem). Location chain (AU-filtered lidm→lico→comp→title). BD snapshot sd_mnfd94hgsyllcqjlx: 257 profiles merged. | COMPLETE — ecbe0b9 |
| #300-FIX-8 | AU location filter on lidm.location (skip if non-AU). DM name-email match gate (email_waterfall Layer 0). company_email placeholder scan at card assembly. Test baseline: 204 passed. | COMPLETE — fad25df |
| #301 | SMTP email discovery: email_verifier.py (13 patterns, MX resolution, SMTP RCPT TO). Railway Reacher deployed. Port 25 blocked on Vultr AND Railway. SMTP not viable on managed cloud. | COMPLETE |
| #302 | Manual full rewrite: Sections 2–8 current state + Section 9 Decisions Pending | COMPLETE — PRs #265 merged |
| #303 | Wire four proven DFS endpoints into paid_enrichment.py: Competitors Domain, Backlinks Summary (fix #276 parser), Brand SERP, Indexed Pages. 3 new dfs_labs_client methods. ProspectCard +9 fields. 11 new tests. | PR #266 open |

---


### Directive 3002 (PR #277, 2026-04-15)
TIERS-002: Code-Manual tier alignment. 30 files. Spark added, Ignition/Velocity fixed, Dominance removed. PR #277 merged.

### Directive 3003 (PR #279, 2026-04-15)
DASH-002: 17 fixes + Cycles model + Industries filter + Insights rebuild + funnel extension. PR #279.

### Directive 3004 (PR #281, 2026-04-15)
DASH-004: Ship-ready dashboard. 13 items, 50 prospects, briefing page, three-state pipeline, pagination. PR #281.

### Directive 3005 (PR #282, 2026-04-15)
DASH-005: Marketing site live on Vercel. Landing + demo. DNS handoff pending. PR #282.

### Directive 309 (PR #283, 2026-04-15)
Onboarding rebuild. 4 pages, auth fixed, OAuth redirect fixed, deprecated deleted, schema migration, LinkedIn warmup. PR #283.

### Directive 310 (PR #284, 2026-04-15)
Billing lifecycle wired. Stripe consolidated, 5 webhook handlers, activation email. Blocked on Stripe keys. PR #284.

### Directive 311 (PR #285, 2026-04-15)
Outreach scheduler. 4 tables, 5 services, firing engine. 801 LOC. Dry-run default. PR #285.

### Directive 312 (PR #286, 2026-04-15)
Domain pool. 3 tables, naming generator, pool manager, replenishment flow. 842 LOC. Dry-run. PR #286.

### Directive 314 (PR #288, 2026-04-15)
Customer-facing flow. Welcome page, activation email, 4-state dashboard, Maya tour, reveal animation, Pause Cycle. 2393 LOC. PR #288.

### Directive 315 (PR #289, 2026-04-15)
crm-sync-flow PERMANENTLY DELETED. 883 lines removed. Deployment deleted. CI guard added. PR #289.

### Directive 317 (PR #317, 2026-04-15)
ContactOut validated (74% email match, 100% AU mobile). Waterfall reordered. 5 sub-directives. 5 pilot runs. 3.88 AUD total spend.

### Directive 3001 (PR #320, 2026-04-15)
V3: Stage 9 build + Stage 10 live-fire. 25/25 VRs, 100/100 dm_messages. Cost 1.574 USD (2.440 AUD). verification_first_pass=false due to Decimal serialization + pgbouncer bugs.

### Directive 4001 (PR #312, 2026-04-15)
M-S1-PREP: Category ETV windows surfaced. Manual Section 3 backfilled with 21-category table. Section 13 build log updated.

### Directive 5001 (PR #312, 2026-04-15)
S1: Stage 1 Discovery. 100/100 domains (10 cats x 10). Cost 1.10 USD. 137.9s wall.

### Directive A (PR #324, 2026-04-15)
Foundation: tests fixed, naming standardised (F3a/F3b to Stage naming), blocklist +62 domains (total 274), parallel.py utility (4 tests). pytest: 1498 passed.

### Directive B (PR #325, 2026-04-15)
Module fixes: Facebook SERP query added to Stage 2, scoring separation (Stage 7 no longer scores), structured vulnerability report format. pytest: 1498 passed.

### Directive C (PR #326, 2026-04-15)
4 missing modules built: Stage 6 ENRICH (historical_rank_overview, 0.106/domain), Stage 9 SOCIAL (BD LinkedIn DM+company posts), Stage 10 VR+MSG (Gemini structured VR + personalised outreach), Stage 11 CARD (binary lead_pool_eligible). pytest: 1498 passed.

### Directive D1 (PR #327, 2026-04-15)
Cohort runner (cohort_runner.py) + 7 bug fixes (D1.1): budget hard cap, cost tracking constants, stage naming, blocklist +39 (total 313), Gemini error capture, BD env key fix, parallel cost tests. 100-domain smoke: 28% conversion, 17.7 min wall. pytest: 1498+ passed.

### Directive D1.3 (PR #328, 2026-04-15)
Audit fix sweep: 35 findings from D1.2 seam audit addressed. preflight_check.py created. Cost constant Stage 4 0.073 to 0.078. ABN signal fix (C1), Stage 9 verified URL (H2), data contract fixes (M1-M3, L1-L4). +6 new tests. pytest: 1504 passed.

### Directive D1.8 (PR #329, 2026-04-15)
3-store save mechanism fix: (1) CLAUDE.md schema refs corrected (public.ceo_memory/cis_directive_metrics), (2) three_store_save.py automation script + skill, (3) CI directive-save-check.yml + session_end_check.py enforcement, (4) 19 directives backfilled from git history. Save mechanism now: one script, one call, 4 stores written.

### Directive ECON-F21-correction (PR #329, 2026-04-15)
Pipeline F v2.1 Economics Correction (n=100 actuals). Original projection: 0.25 USD/card (n=9, 80% conversion assumed). Actual: 0.53 USD/card (n=100, 28% conversion). Post-fix target: 0.23-0.36 USD/card at 60-65% conversion. Bottlenecks: Gemini 18% failure rate, DM identification 82%, wall-clock 17.7 min. Source: 07_cost_reports.md

### Directive D1.1 (PR #327, 2026-04-15)
7 bug fixes from 100-domain smoke test: budget hard cap (_check_budget helper, pre-run estimate, hard cap after stages 2/3/4/6/7/8/9/10), Stage 9 fixed cost $0.027 added, stage naming drop_reason renamed, blocklist +3 categories (313 domains), Gemini retry structured error_detail, BD env key fix, 3 parallel cost tests. 28% conversion, 17.7 min wall. [source: 01_dave_directives.md L6006; git 836745e0; PR #327]

### Directive D1.2 (PR #0, 2026-04-15)
Read-only seam audit of all 11 Pipeline F v2.1 stage modules + cohort runner. 7 reports in research/d1_2_audit/ (2648 lines). 35 findings: 1 critical, 4 high, 7 medium, 8 low, 15 info. Top findings: ABN signal zeroed, Stage 9 unverified LinkedIn URL, Stage 4 cost constant drift. No code changes. [source: 01_dave_directives.md L6010; git d075ea40; 05_ceo_ratifications.md L9611]

### Directive D1.4 (PR #0, 2026-04-15)
Post-fix re-audit verifying all 35 D1.2 findings resolved by D1.3. 7 re-audit reports in research/d1_4_reaudit/ (1125 lines). Result: 35/35 RESOLVED. Also surfaced 4 new LOW/INFO findings (N1-N4), triggering D1.5. Stage 4 $0.078 and Stage 8a $0.008 cost fixes confirmed accurate. [source: 01_dave_directives.md L6014; git 56bfc3fa; 05_ceo_ratifications.md L9614]

### Directive D1.5 (PR #328, 2026-04-15)
Fixed 4 LOW/INFO re-audit findings (N1-N4) before PR #328 merge. N2: cohort_runner exports STAGE cost constants; test imports + asserts them. N3: funnel_classifier.py stage10_status fallback comment added. N4: Stage 8 reads verify_fills._cost dynamically, fallback constant. N1: prospect_scorer NOTE added. Merged as beaa0ba5. [source: 01_dave_directives.md L6015; git 6f31d4b2; 05_ceo_ratifications.md L9448]

### Directive D1.6 (PR #0, 2026-04-15)
Session-end protocol execution: Supabase SESSION_HANDOFF entry written, docs/daily_log.md created and committed (git 3e67854c, 39 lines). 3-store save claimed complete but D1.7 investigation later revealed ceo_memory was stale (single 2026-02-03 entry) — partial save failure suspected. [source: 01_dave_directives.md L6017; git 3e67854c; 05_ceo_ratifications.md L9766]

### Directive D1.7 (PR #0, 2026-04-15)
Read-only forensic audit of 3-store save mechanism for PRs #324-#328. Findings: ceo_memory had single entry from 2026-02-03 (stale 71 days), Manual last updated 2026-04-08 (stale 7 days). ~15 directives missing from all 3 stores. Output fed directly into D1.8 backfill scope. No code changes. [source: 02_elliottbot_restates.md L1763; 03_pr_creations.md L70-74]

### Directive D1.8.3 (PR #330, 2026-04-15)
Synthesis + write in one pass. 7 governance rules written to Manual S17 + ceo_memory. 6 missing directives (D1.1-D1.7) backfilled to all 3 stores. Economics correction (0.25 projected vs 0.53 actual USD/card) written. 10 optimistic-completion catches documented. Total: 15 three_store_save.py invocations, all succeeded. Source: 1406 extraction entries from D1.8.2.

### Directive D2 (PR #0, 2026-04-15)
20-domain validation rerun. Headline 35% conversion ($0.42/card USD). Pipeline mechanically validated — 0 Gemini failures, 100% DM identification on cards. On 13-domain SMB-clean cohort (excluding 6 enterprise + 1 directory drops at Stage 3): 54% conversion, ~$0.37/card USD adjusted. Pipeline F v2.1 PASSES validation. Contamination upstream: DFS domain_metrics_by_categories returns head-of-distribution domains by default. Triggers D2.1 discovery filter tuning.

### Directive D2.1A (PR #331, 2026-04-15)
Blocklist expansion 313 to 1515 entries. 13 new categories (banks, retail, telco, education, hospitals, franchises, transport, real estate, allied health, charities, childcare, gambling, sporting). All 6 D2 enterprise drops now caught at Stage 1 gate. is_blocked() logic unchanged. pytest 1505/1/28.

### Directive D2.1B (PR #332, 2026-04-15)
Unified contact waterfall fix. Swapped cohort_runner Stage 8 from legacy contact_waterfall.py (/v1/people/linkedin, 0 email credits) to Directive #317 modules: contactout_enricher.py (/v1/people/enrich, 2765 search credits) + email_waterfall.py + mobile_waterfall.py. One ContactOut call captures email + mobile + full profile. No field discarded. Stage 10 gate updated. pytest 1505/1/28.

### Directive D2.2-PREP (PR #333, 2026-04-15)
Validation run enablement. --domains CLI flag (bypass Stage 1, replay specific domains). 4 new verticals: recruitment (12371), itmsp (12202), webdev (11493), coaching (11098). ETV windows calibrated. Tier tracking in summary.json (GOV-8 verification). GOV-9 Two-Layer Directive Scrutiny ratified.

### Directive D2.2-PREP-CLOSE (PR #333, 2026-04-16)
Resolved all open items. --dry-run flag (DRY_RUN env var in 7 clients, zero spend). webdev offset raised 50->80 (55% platform contamination). itmsp confirmed clean at offset=50 (65%). Pre-validation evidence documented.

### Directive CASCADE-DESIGN-V2 (PR #338, 2026-04-16)
ARCHITECTURE.md v2 ratified. Fork concurrency fix (per-track sub-dict isolation), state-in-queues, Gemini multi-project pool (sem=30), per-stage timeouts + per-provider circuit breakers, tenant context on domain_state, GOV-8 extended to raw responses on success path, Q4 pause-on-cancel override, build 9 days. PR #338.

### Directive D2.2-RUN (PR #0, 2026-04-16)
Pipeline F v2.1 validation rerun complete 2026-04-16. 17 domains (5 replay + 12 fresh), 7 cards shipped (41% overall, 83% post-Stage-3 SMB-clean). Cost 2.52 USD / 0.36 per card. Wall 13m 40s combined. REPLAY (5 D2-lost domains): 2/5 resolved (was 0/5 in D2), mobile 5/5, email 2/5 via L0 Gemini extract. FRESH (12 discovered): 5 cards (5/5 Hunter email, 4/5 ContactOut mobile). Enterprise filter caught 5/6 drops correctly. Provider coverage findings: ContactOut email credits = 0 (emails BLOCKED by credit type, not wiring), ContactOut phone credits work (returns mobile reliably via /v1/people/enrich). Leadmagic 0/4 email on dentals (has_mx=false — domains have no email infrastructure). Bright Data returns profile data only, never contact info. Stage 11 drops (4 domains): all had verified DM + mobile + score + signals but NO email, dropped at gate. Classification: YELLOW overall.
## SECTION 14 — COMPETITIVE INTELLIGENCE

Direct competitors (signal-based AI BDR category):

| Company | Funding | Valuation | ARR | Key Fact |
|---------|---------|-----------|-----|----------|
| 11x.ai (Alice) | $76M | ~$350M | ~$25M | a16z-backed. Credibility questions (TechCrunch Mar 2025). |
| Artisan (Ava) | $46M | ~$30M+ | ~$5M | YC-backed. 250 customers. Founded 2023. |
| Amplemarket (Duo) | $12M | Undisclosed | ~$15M | Most mature. Lean funding vs revenue. Gartner Cool Vendor. |
| Coldreach | $500K | Undisclosed | ~$600K | YC. 4 employees. Signal-first philosophy closest to ours. |
| AiSDR | $3.5M | Undisclosed | ~$500K | YC. $900/mo transparent pricing. Predefined signals only. |

Secondary monitor: Apollo.io (acquired Pocus signal platform Mar 2025)

Our wedges vs all five:
- AU-native data (ABN registry, GMB-first, DFS signal detection)
- Vertical-native configs (out-of-box for each industry, not DIY)
- Three-way message matching (prospect signals × agency capabilities × channel format)
- Voice AI with Australian TCP Code compliance
- Flat managed-service pricing (not per-user or credit-based)
- Agency Profile built from customer's own CRM + LinkedIn

DROPPED from primary watchlist: Apollo (tool), Instantly (email-only), Smartlead (email infra), Saleshandy (basic sequences), Clay (technical enrichment, no execution)

---

## SECTION 15 — RESEARCH-1 STANDING BRIEF (updated Mar 26 2026)

Schedule: daily 20:00 UTC
Writes to: Intelligence Feed (`1CHG295kALLODiT5orRG4lfsKJ1Ts8Ma1AHy-A6r0zFc`) + Supabase `cis_improvement_log`

**Brief A — Tooling + Infrastructure:**
- `OpenClaw new features updates 2026`
- `MCP server new tools agents 2026`
- `Bright Data API new endpoints scrapers 2026`
- `DataForSEO API new endpoints 2026`

**Brief B — Direct Competitors (signal-based AI BDR):**
- `Amplemarket Duo AI update [current month] 2026`
- `11x.ai Alice AI SDR update [current month] 2026`
- `Artisan AI Ava update [current month] 2026`
- `Coldreach AI SDR signal outbound [current month] 2026`
- `AiSDR update features [current month] 2026`

**Brief B2 — Secondary Competitor Monitor:**
- `Apollo.io Pocus signal integration [current month] 2026`

**Brief C — Regulatory (Australian):** unchanged from prior brief

**Brief D — SaaS Strategy:** unchanged from prior brief

**Brief E — Self-improvement + Category Intelligence:**
- `AI agent orchestration multi-agent best practices 2026`
- `AI BDR SDR market trends funding 2026`
- `signal-based outbound sales benchmarks reply rates 2026`

Config tracked in repo: `governance/research1-standing-brief.md` (PR #221)

---

## SECTION 16 — ICP + MARKET

Primary ICP: Australian marketing agencies, 5–50 employees, $30k–$300k MRR
Core addressable market: ~900–1,200 agencies

Vertical expansion sequence (post-launch):
1. Recruitment agencies (P1 — 1,200–1,800 ICP, propensity 9/10)
2. IT MSPs (P1 — 1,500–3,000 ICP, propensity 9/10)
3. Web/software agencies (P2 — 2,000–4,000 ICP, propensity 9/10)
4. Accounting firms (P3 — 2,500–4,000 ICP, propensity 7/10)
5. Management consultants, business coaches, migration agents (P3)
6. Legal, HR, insurance, mortgage brokers (P4–P5, compliance required)

Combined P1–P3 TAM: 6,600–10,000 businesses in Australia alone.

Geographic expansion: Australia → NZ → UK → US

Wave 2: Pivot from vertical SaaS to horizontal GTM platform serving any B2B company.

---

## SECTION 17 — GOVERNANCE + OPERATIONS

Three-node chain: Claude (CEO) → Dave (Founder/Chairman) → Elliottbot (CTO)

PR merge authority: Dave merges all PRs. Elliottbot may merge only when explicitly instructed via Telegram.

**Three-store completion rule (mandatory on save-trigger directives):**
1. `docs/MANUAL.md` in repo (CEO SSOT — primary)
2. Supabase `ceo_memory` (directive counter, completion status, key state changes)
3. `cis_directive_metrics` (execution metrics for learning system)

Mirror: After writing `docs/MANUAL.md`, copy content to Google Doc (best effort). If Drive write fails, log error but do not block completion.

**Verification:** Every save-trigger directive must include `cat docs/MANUAL.md | grep "SECTION"` output proving the write landed. "All four stores written" without this output is rejected.

Directive format: Context / Constraint / Action / Output / Save / Governance
- Mobile-friendly: triple backticks, single continuous blocks, no nested code
- All directives include `confirm pwd = /home/elliotbot/clawd/Agency_OS/`
- LAW XIV: verbatim terminal output, no paraphrasing

Dave's lane:
- API keys, subscriptions, external account access
- PR merges (no exceptions)
- Spend decisions above ratified amounts
- Founder credibility decisions

---


### Directive GOV-1-verify-before-claim (PR #329, 2026-04-15)
Governance Rule 1: Verify-Before-Claim. Done must only be reported after ALL verification commands have been run and verbatim output included. CEO gate exists to CONFIRM done, not DISCOVER incomplete work. Emerged 2026-04-15 when PR #327 pre-merge check caught two misses Elliottbot had claimed done. Sources: 06_governance_language.md L12432, L13307-13309; 09_ceo_verification_asks.md L10555.

### Directive GOV-2-cost-authorization (PR #329, 2026-04-15)
Governance Rule 2: Cost-Authorization. If mid-run API spend exceeds 5x the ratified pre-run estimate, kill the run and report immediately. CTO does not authorise spend above the ratified amount. Emerged 2026-04-15 after 100-domain run reported $155 USD vs ratified ~$1.60 USD estimate. Sources: 06_governance_language.md L12423-12424, L13219-13224; 09_ceo_verification_asks.md L10556.

### Directive BUGPAT-2026-04-15 (PR #329, 2026-04-15)
Optimistic Completion Catches — Session 2026-04-15. 10 catches documented across 4 structural variants: (1) Action!=Result — saves claimed but never landed, (2) Partial!=Complete — 17.5% verified vs 67.5% found conflation, (3) Stated!=Measured — $155 reported vs $15 actual cost, (4) Process!=Outcome — Drive Manual always stale due to hardcoded skeleton in write_manual.py. Prevention: 7 governance rules established (verify-before-claim, cost-auth, pre-directive check, optimistic-completion naming, audit-fix-reaudit cycle, three-store mechanism, letter-prefix convention). Source: 08_bug_discoveries.md, 09_ceo_verification_asks.md

### Directive GOV-3a-cto-ready-state (PR #329, 2026-04-15)
Governance Rule 3a: CTO Ready-State Check. Before Task A of any directive, Elliottbot must paste a structured 8-item ready-state confirmation to Telegram: (1) pwd, (2) service status, (3) git branch + log, (4) ceo_memory handoff content verbatim, (5) .env key presence, (6) MCP server confirmation, (7) ARCHITECTURE.md head, (8) clean working tree (git status). This is a CTO self-check — Elliottbot verifies its own environment before starting work. Sources: 06_governance_language.md L13339-13351.

### Directive GOV-3b-ceo-pre-directive-gate (PR #329, 2026-04-15)
Governance Rule 3b: CEO Pre-Directive Gate. After Step 0 RESTATE and before any execution, CEO reviews the restatement and confirms "go." CEO may revise scope, add constraints, or reject. This is a CEO decision gate — Dave confirms the directive is correctly understood before work begins. Distinct from GOV-3a (CTO self-check) which verifies environment readiness. Sources: 06_governance_language.md L13339-13351.

### Directive GOV-4-optimistic-completion-pattern (PR #329, 2026-04-15)
Governance Rule 4: Optimistic Completion Pattern (named failure mode). Elliottbot has a recognised failure mode of reporting tasks complete before running verification, treating the CEO review gate as a place to finish work rather than confirm it. Named and caught 3x during Apr 8-15 session: Directive A naming, D1.1 pre-merge, D1.3 verification. Sources: 06_governance_language.md L3749, L13025, L13633; 08_bug_discoveries.md L5026.

### Directive GOV-5-audit-fix-reaudit-cycle (PR #329, 2026-04-15)
Governance Rule 5: Audit-Fix-Re-Audit-Fix-Merge Cycle. Before merging new code, run a read-only audit to find all seam bugs, fix them in a separate directive, then re-audit to verify no regressions. Module isolation tests alone are insufficient for integration bugs. Emerged from D1.2/D1.3/D1.4/D1.5 cycle that caught 35 seam bugs all isolation tests missed. Sources: 06_governance_language.md L12441-12442; 08_bug_discoveries.md L4922-4932.

### Directive GOV-6-three-store-completion-mechanized (PR #329, 2026-04-15)
Governance Rule 6: Three-Store Completion (Mechanized via three_store_save.py). A directive is not complete until docs/MANUAL.md, public.ceo_memory, and public.cis_directive_metrics are all written, enforced via three_store_save.py that fails loud on partial success. D1.7 forensic audit found 16 directives with save_completed=true but 0/3 stores written. D1.8 fixed with script + CI. Sources: 06_governance_language.md L13632-13764.

### Directive GOV-7-letter-prefix-directive-convention (PR #329, 2026-04-15)
Governance Rule 7: Letter-Prefix Directive Convention. Foundation-sequencing work uses letter-prefix naming (A, B, C, D1.x) establishing an ordered build sequence where each is a prerequisite for the next. Emerged 2026-04-15 with Directive A referencing B/C/D as subsequent stages. D1.x sub-directives emerged naturally from D1 cohort run surfacing bugs. Sources: 06_governance_language.md L12361, L12370, L12388, L12405, L13782.

### Directive GOV-8-maximum-extraction (PR #332, 2026-04-15)
GOV-8: Maximum Extraction Per Call. Every API call captures all fields. Write to BU regardless of card eligibility. Never re-fetch. Emerged from D2.1B: Stage 3 Gemini already reads website but discarded data. Fixed: Stage 3 now extracts dm_email, dm_phone, office_address, services_offered. Website HTML layer removed from waterfall. CEO ratified 2026-04-15.

### Directive GOV-9-two-layer-directive-scrutiny (PR #333, 2026-04-15)
GOV-9: Two-Layer Directive Scrutiny. Every directive passes two scrutiny layers before Step 0. Layer 1 (CEO): query ceo_memory for ratified state, trace call path, flag uncertainties. Layer 2 (CTO): scrutinise for gaps (missing capabilities, config, instrumentation, contradicted assumptions). Report DIRECTIVE SCRUTINY — N GAPS FOUND or CLEAR before executing. Both layers mandatory. Emergence: 5 consecutive D2 directives had drafting gaps caught only by manual scrutiny prompt.

### Directive GOV-10-resolve-now-not-later (PR #335, 2026-04-16)
GOV-10: Resolve-Now-Not-Later. Fix bounded gaps in current PR cycle. Deferred fixes accumulate. Exceptions: policy decisions, deprecated code, external deps. Emerged 2026-04-15 from D2.2-PREP --dry-run deferral corrected by CEO.

### Directive GOV-11-structural-audit-before-validation (PR #335, 2026-04-16)
GOV-11: Structural Audit Before Validation-Scale Run. Stage audit within 7 days before any N>=20 validation run. Covers data flow gaps, GOV-8 violations, dead code, gate enforcement, template tokens, cascade risk. Emerged 2026-04-16 when pipeline audit found 3 CRITICAL bugs 1 directive before validation.

### Directive GOV-12-gates-as-code-not-comments (PR #335, 2026-04-16)
GOV-12: Gates As Code Not Comments. Runtime enforcement required for all gates. Comment-only gates create false confidence. Emerged 2026-04-16 when Hunter dm_verified gate found as comment only. CEO authorizes systematic gate audit.

### LAW XVII — Callsign Discipline (AIDEN-SCAFFOLD, 2026-04-16)
Every Step 0 RESTATE, Telegram outbound message, PR title, commit trailer, and three-store write MUST prefix or tag the session callsign ([ELLIOT] or [AIDEN]). Ambiguous identity in multi-session operation is a governance violation. Callsign is read from `./IDENTITY.md` at session start and must match `CALLSIGN` env var when set. Empty `CALLSIGN` is a hard fail — three_store_save.py raises SystemExit. Each session occupies its own git worktree (Elliot: /home/elliotbot/clawd/Agency_OS, Aiden: /home/elliotbot/clawd/Agency_OS-aiden). Workspace isolation via worktree + per-worktree CLAUDE.md + IDENTITY.md + --setting-sources=project (no CLAUDE_CONFIG_DIR required).


### [ELLIOT] Directive AIDEN-SCAFFOLD (PR #340, 2026-04-16)
Second Claude Code instance scaffold (callsign aiden). Worktree at /home/elliotbot/clawd/Agency_OS-aiden on branch aiden/scaffold. IDENTITY.md per worktree. LAW XVII Callsign Discipline ratified. three_store_save.py callsign-aware (default elliot, empty fails loud per GOV-12). chat_bot.py parameterised by CALLSIGN + WORK_DIR_OVERRIDE. systemd unit aiden-telegram.service registered (not enabled — Dave enables after token verification). Migration: cis_directive_metrics.callsign TEXT NOT NULL DEFAULT elliot. .env.aiden created (gitignored, chmod 600). pytest 1510/1/28 (+5 callsign tests).

### [ELLIOT] Directive LISTENER-GOV-F2 (PR #0, 2026-04-18)
v1→v1.5 ratified post-hoc. Migration 103 committed to repo (supabase/migrations/103_cognitive_columns.sql). ceo_memory key ceo:listener_architecture_v1_5 written with full scope delta. 17 columns beyond v1 spec formally ratified by Dave 2026-04-18.

### [ELLIOT+AIDEN] Directive FM-BUILD-V1 (2026-04-19/20)
One-shot FM sourcing job for electrical test-and-tag client. 81/100 FM records delivered (email-only, no phone). Cost: $2.18 AUD. 549 target companies across 9 sectors (incl. fm_providers). ContactOut search yielded 771 profiles from 74 companies before credits exhausted. Leadmagic email enriched 81 (47% hit rate). Phone blocked: ContactOut locked (email credits 0 gates enrich endpoint), Leadmagic mobile 0% AU. 14 failures documented in post-mortem (docs/postmortems/FM_BUILD_V1_POSTMORTEM_2026-04-20.md). Key lessons: pilot before production, no silent try/except, scout for research not build agents, real-time credit checks, fix at discovery not defer.

### [ELLIOT+AIDEN] Directive LISTENER-KNOWLEDGE-SEED-V1 (2026-04-19)
Curated fact ingest into agent_memories for listener whisper capability. 178 rows seeded: 39 from CLAUDE.md (Elliot — enrichment path, ALS gates, dead refs, governance laws, stack info) + 139 from Manual + ARCHITECTURE.md (Aiden — pricing, competitors, vendors, directive history, scoring, compliance). All source_type='verified_fact', state='confirmed', trust='dave_confirmed'. Hit Rate@5: 9/10. Meta-prose leakage: 0/20. Total agent_memories corpus: 567 rows. Chunking rules documented in docs/governance_chunking.md. Follow-up: V2 auto-ingest-on-commit deferred as separate directive.

### [ELLIOT] Directive LISTENER-COST-F4-PART2-SETUP (PR #362, 2026-04-19)
OpenAI cost tracking at all 6 call sites: memory_listener.py (query expansion + embeddings), listener_discernment.py (L2 discernment), save_handler.py (save extraction), store.py (write embeddings), organise.py (backfill embeddings). New module openai_cost_logger.py writes append-only JSONL to /home/elliotbot/clawd/logs/openai-cost.jsonl. Daily rollup at 23:55 AEST (systemd timer enabled) posts TG summary. Weekly rollup Friday 18:00 AEST writes to ceo:openai_weekly_cost. 7-day collection window started — F4-PART2-RATIFY scheduled 2026-04-25.

### [ELLIOT] Directive LISTENER-SCHEMA-F1 (PR #361, 2026-04-18)
Schema cleanup per F1 audit finding. Dropped 5 dead columns (provenance, signoff_status, category, business_score, learning_score) via migration 106. Wired promoted_from_id on tentative→confirmed promotion (self-referencing FK + typed_metadata.promoted_at breadcrumb — Dave-approved pattern). PROMOTION FIRED log line added. Backfill script run: 2/17 superseded rows matched (backfill_inferred: true), 15 failed (below 0.85 threshold, backfill_failed: true), 0 ambiguous. contradicted_by_id deferred with SQL COMMENT. Technical debt documented in ceo:technical_debt.promoted_from_id_semantics (FK asymmetry: supersedes_id→other row, promoted_from_id→self). Aiden peer-reviewed: caught RPC name mismatch + ambiguity handler gap, both fixed pre-merge.

### [ELLIOT] Directive LISTENER-GOV-F4-PART1 (2026-04-18)
OpenAI ratified as permanent LLM provider for the listener subsystem. Rationale: Dave stays on Anthropic Max plan (no API billing); OpenAI keeps listener spend in separate credit pool; Anthropic has no embeddings API. Models ratified: text-embedding-3-small (embeddings in memory_listener.py), gpt-4o-mini (discernment in listener_discernment.py, save extraction in save_handler.py, query expansion MultiQueryRetriever in memory_listener.py). Budget trigger DEFERRED to F4-PART2 (scheduled 2026-04-25, requires 7 days cost tracking data). Migration triggers: if Anthropic releases embedding API on Max plan, or if monthly OpenAI spend exceeds Part 2 threshold.

### [ELLIOT+AIDEN] Directive LISTENER-MEASURE-V1 (2026-04-18)
Retrieval quality metrics for listener. Elliot side: src/telegram_bot/retrieval_metrics.py — tokenize(), compute_cited_flags() (2-token overlap threshold), compute_hit_rate() (Hit Rate@5), compute_mrr() (MRR@5), compute_source_type_breakdown(), generate_summary(). Stopwords: English common + callsigns + AU-biz domain terms. Commit 9606475d. Aiden side: outbox-watcher annotation hook in chat_bot.py — _annotate_last_retrieval_with_cited_terms() fires before each outbox send, appends mv_annotation JSONL event with per-item bot_cited flags. 60s window, same-callsign scoping, no-recursion guard. Commit c373956b. Both on main.

### Session 2026-04-21 (Elliot + Aiden)

**Directives completed:**
- P5-STEP-3: Pipeline F master flow end-to-end. 5 dental domains → 2 cards (glenferriedental, dentalaspects). 8 messages across 4 channels. Exit gate MET.
- WRITER-CRITIC-ARCHITECTURE: Anthropic writes (Sonnet email, Haiku others), Gemini Flash critiques (6-criteria fit-based rubric). HARD-FAIL on hallucination + social proof. Max 2 revisions per draft. PR #371.
- AGENCY-PROFILE-TRUTH-AUDIT: DEFAULT_AGENCY eliminated from production (architectural antipattern). Moved to test fixture. AgencyProfileMissingError hard-fail. _KEIRACOM_PROFILE truthful (no case_study — pre-revenue). social_proof_sourced HARD-FAIL gate in critic. PRs #372, #373.

**PRs merged:** #368 (GOV-8 drop-reason), #369 (completion_hook asyncio), #370 (JSONB codec), #371 (writer/critic), #372 (critic social proof gate, Aiden), #373 (agency profile truth audit)

**Bugs fixed (9):** GOV-8 drop-reason logging, completion_hook asyncio.run, asyncpg JSONB codec for pgbouncer, AnthropicClient wrapper, outreach_channels NULL default, dropped_at key parse, dm_messages_gate channel filter, rule-gate downgrade to WARN, agency_profile signature threading.

**Architecture decisions:**
- Writer/critic: Anthropic primary writer, Gemini Flash critic. Critic is sole runtime quality gate (rule-based email_scoring_gate downgraded to WARN).
- Agency profile: production code requires agency_profile param, hard-fails if missing. No hardcoded fallbacks. CRM/onboarding path pending.
- Pre-revenue discipline: zero clients. All social proof claims REJECTED unless Dave confirms. Applies through first paying customer.

**Learnings:**
1. "Check data location not just content" — when data bug found, ask "should this data exist here?" not just "is it correct?"
2. Pre-revenue reality check — DEFAULT_AGENCY contained fabricated Bondi dental case study that passed through spec build, P4 build, and multiple reviews undetected.
3. Production fallback antipattern — hardcoded defaults that silently populate real outputs are architectural flaws.

**P1 Exit Gate:** MET. Flow 1176392a COMPLETED 2026-04-21T11:08:03Z. 8 dm_messages written, 2 cards produced. P1 closure pending Dave card acceptance.

**Open / ship decisions PENDING (verbatim card bodies for next session):**

CARD 1 — DENTAL ASPECTS (dentalaspects.com.au):

Email (critic 100, SEND-READY):
Subject: Your GMB listing - quick question
Body: Hi there, I noticed Dental Aspects doesn't have any Google reviews yet, which means you're missing out on that local search visibility that's crucial for dental practices. Are you actively working on building your online presence, or is it something that's been on the back burner? If you're open to a quick chat about strategies for building online reputation, I'd be happy to share some general insights. Cheers, Dave

Voice (critic 96, DAVE REVIEW — industry assertion 'Most dental practices in Australia are investing in local search visibility right now' is unsourced):
Trigger: No Google Business Profile reviews despite having a GMB listing. Talking point: Most dental practices in Australia are investing in local search visibility right now, and you're not running any paid keywords. Objective: 15-min discovery call. Fallback: Send short email with local dental marketing observations.

CARD 2 — GLENFERRIE DENTAL (glenferriedental.com.au):

Email (critic timed out, body CLEAN on manual read):
Subject: Your GMB setup
Body: G'day, I noticed Glenferrie Dental doesn't have any Google My Business reviews yet, which is pretty unusual for a dental practice in your area. Are you finding it challenging to get patients to leave reviews, or is this something that's just not been a priority? Happy to jump on a quick call if you'd like to chat about some simple ways to build that social proof up. Cheers, Dave

Voice: REJECTED ('Most dental practices we work with' = pre-revenue violation).
LinkedIn x2: Writer refused (insufficient signals).
SMS x2: Writer refused (insufficient signals).

**Railway worker:** HEALTHY. Deployed ca197dad at 2026-04-21T10:54:25Z. Last flow 1176392a completed 11:08 UTC. Pro plan.
**Stripe AU:** DAVE ACTION PENDING (8th mention). 2-3 week lead time. 15-20 min Dave time. Blocks P5 Commercial / P1.5 close. Highest leverage non-code action.

**Followups (next session):**
- Critic timeout tuning 15s → 25s (25% timeout rate)
- Regex guard on critic timeout for social proof phrases
- Writer refusal detection before critic (prevent scoring refusal essays)
- BDM enrichment bottleneck (2/5 domains had no BDM at Stage 8)
- P1.5-OUTBOUND-READINESS halted until truth audit ships
- Resend domain verification (agencyxos.ai failed, no keiracom.com)

**Infrastructure:**
- Railway: Pro plan, worker healthy, auto-deploys from main
- Prefect: deployment 752d8120, worker polling, 5 flow runs this session
- Anthropic: topped up (was zero credits earlier in session)
- Gemini: working (Stage 9 VR + critic)

## SECTION 18 — OUTREACH + CONTENT (pre-launch)

Landing page (`agency_os_v5.html`) is built with Bloomberg aesthetic and "Who built yours?" hero. Pending: Remotion video hero, Stripe Checkout on pricing CTAs, live founding counter from Supabase. Video strategy: 5 versions (dashboard animation, Maya walkthrough, HeyGen avatar, customer-specific, results) built via Remotion + HeyGen (Maya avatar). Content distribution via Prefect Flow #28 (Claude API → Remotion → HeyGen → distribution APIs). Demo mode active via `?demo=true` URL param with seeded Supabase demo tenant. Onboarding starts with a 15-minute activation call (CRM + LinkedIn connect, watch dashboard populate live).

---

## SECTION 19 — DESIGN SYSTEM

- Pure Bloomberg palette: warm charcoal `#0C0A08` + amber `#D4956A` only
- Lucide icons throughout (all emoji replaced)
- Aggressive glassmorphism cards with light-catching edges
- Typography: Instrument Serif + DM Sans + JetBrains Mono
- Directive #027 pending execution for full implementation

---

## SECTION 20 — INFRASTRUCTURE + CREDENTIALS

Elliottbot:
- Vultr Sydney server
- OpenClaw 2026.3.8
- Managed by systemd (`openclaw.service` — never use clawdbot commands)
- Workspace: `~/clawd`
- Config: `~/.openclaw/openclaw.json`
- 6 sub-agents: build-2, build-3, test-4, review-5, devops-6, research-1

Supabase: Pro plan
- `ceo_memory` — CEO session state
- `cis_directive_metrics` — execution tracking
- `elliot_internal.memories` — Elliottbot's SSOT
- `business_universe` — live BU table
- `abn_registry` — 2.4M ABR records
- 29 security advisor errors unresolved

GitHub: Keiracom/Agency_OS

Deployment: Railway (`LEADMAGIC_API_KEY` must be present in env)

Orchestration: Prefect (flow orchestration)

Compliance: SPAM Act 2003, DNCR registered, TCP Code (voice), Australian-built

---

## SECTION 21 — KNOWN ISSUES + BACKLOG

### Active Blockers

| Issue | Severity | Status |
|-------|----------|--------|
| ContactOut API key demo-locked | HIGH | Dave: waiting on ContactOut support ticket |
| Forager API 404 | HIGH | Dave: waiting on Forager support ticket |
| Reacher port 25 blocked (Vultr + Railway) | HIGH | Dave: needs dedicated VPS or Oracle Cloud free tier |
| BD LinkedIn DM batch SLA (30+ min for 260 URLs) | HIGH | Dave: needs BD support ticket on Stage 10 batch timing |
| Email verification: 87% unverified | HIGH | Blocked on all above |
| Leadmagic mobile: 0% AU coverage | MEDIUM | Dead for AU — replaced when Forager/ContactOut unblocked |

### Resolved (Directive #305)

| Issue | Resolution |
|-------|-----------|
| Business name = domain stem on 14% of cards | Fixed: ABN trading_name → GMB name → ABN legal_name → title prefix waterfall in `resolve_business_name()` |
| Location = "Australia" on 54% of cards | Fixed: GMB address → JSON-LD → postcode → state hint waterfall in `resolve_location()`. Cards now carry `location_suburb`, `location_state`, `location_display`. |
| Placeholder emails leaking (example@mail.com, etc.) | Fixed: `is_placeholder_email()` blocklist + pattern filter applied to Layers 0+1 of email discovery |

### Infrastructure Issues
- Supabase: 29 security advisor errors unresolved
- PR #275 (asyncpg JSONB codec) open on old branch — needs rebase or close

### Technical Debt
- DFS Backlinks parser: data returns but parser needs fix for clean field extraction
- Google PageSpeed API: needs API key from Dave before wiring
- Stage 10 (LinkedIn DM profiles) timing: BD batch takes 30+ min — needs async trigger + polling pattern rather than synchronous wait
- `analyse_reviews()` (Sonnet Stage 5b): not yet wired to actual GMB review text — needs GMB deep review scrape integration

---

## SECTION 22 — SEGMENT TESTING STRATEGY

Ratified: March 29, 2026

Pipeline validated via integration test #300 (730 domains, all 11 stages). Segment-by-segment approach replaced with full end-to-end pipeline test. All core stages BUILT and PROVEN:

| Segment | What | Status |
|---------|------|--------|
| 1 — Discovery | DFS domain_metrics_by_categories | PROVEN — 730 domains |
| 2 — Business Intelligence | httpx scrape, DNS, ABN, affordability, intent | PROVEN — 730 domains |
| 3 — DM Identification | DFS SERP LinkedIn T-DM1 | PROVEN — 70% hit rate (260/370) |
| 4 — Email Discovery | 4-layer waterfall | PROVEN — 228/370 emails (87% unverified) |
| 5 — Phone Discovery | HTML regex (free tier only) | PARTIAL — 87/370 mobiles (Leadmagic AU = 0%) |
| 6 — Social Discovery | BD LinkedIn company + DM profile | PARTIAL — Stage 10 batch SLA unresolved |
| 7 — Scoring + Message Generation | Two-dimension scoring + Haiku draft emails | PROVEN — 260 cards with full draft emails |
| 8 — Outreach Execution | Salesforge + Unipile + ElevenAgents | WIRED, not yet live-tested |

**Current gate:** Provider resolution (ContactOut, Forager, Reacher) before outreach goes live.
