# Agency OS Manual

Last updated: 2026-03-28 UTC
Directive #280: Sprint 1 — Discovery Engine v7 — COMPLETE
Next scheduled update: Directive #281 (Sprint 2 — Free Intelligence Sweep)

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

- Last directive issued: #299 (email discovery waterfall — PR #261 open)
- Test baseline: 1254 passed, 0 failed, 5 skipped
- Last merged PRs: #247–#260 | Open: #261
- PR #254 (Directive #291 — ProspectScorer) pending merge
- Architecture: **FINAL ratified Mar 30 2026** — service-signal discovery, two-dimension scoring, stage-parallel processing
- **Pipeline test Run 1 (Mar 29):** 100 DMs from 200 domains, $3.51, 7.3 min
- **Pipeline test Run 2 (Mar 30, partial):** 69/100 DMs from 300 domains before timeout. Intent gate working — rejecting 64% NOT_TRYING. ABN API bug fixed in #292.
- **ABN API Settings.abn_lookup_guid bug:** FIXED in #292 (was `settings.ABN_LOOKUP_GUID` → `settings.abn_lookup_guid`)
- ETV range 200–5000 validated as SMB sweet spot for dental AU

---

## SECTION 3 — PIPELINE FINAL ARCHITECTURE (ratified Mar 30 2026)

Core principle: Agency sells services. Prospects have problems. Industry is irrelevant to the match. Geography is a delivery constraint. Signals are the discovery engine.

---

### ONBOARDING

Agency connects CRM + LinkedIn. System extracts services and service area. No industry selection. No ICP definition. Two inputs: what they sell, where they operate.

System builds Agency Profile automatically. Signal config generated from their services — each service maps to category codes + scoring weights.
Output: Agency Profile + Signal Config + Exclusion List

**Status: BUILT** — HubSpot/GHL/Pipedrive/Close OAuth complete. Unipile LinkedIn complete. Onboarding flow complete.

---

### MONTHLY CYCLE

**Phase 1 — Re-score (days 1–2):** Re-scrape all prior-month rejects in agency's BU. Fresh Spider data through scoring. Promote any that now pass. Zero discovery cost.

**Phase 2 — Discover (days 2–3):** Fill remaining quota with fresh discovery across ALL categories within service area. Monthly rotation through categories. Pool never exhausts.

**Phase 3 — Enrich + Score + Identify (days 2–3):** Stage-parallel processing. All domains in batch go through each stage concurrently:

| Stage | Operation | Concurrency | Time/200 domains |
|-------|-----------|-------------|-----------------|
| 1 | httpx scrape (Spider fallback) | sem=15 | ~15s (httpx) / ~30s (Spider) |
| 2 | DNS + ABN | sem=20 | ~15s |
| 3 | AU country filter + Affordability gate | in-memory | <1s |
| 4 | Intent free gate | in-memory | <1s — rejects NOT_TRYING before paid enrichment |
| 5 | DFS Ads Search + Maps GMB | sem=20 | ~20s |
| 6 | Intent full scoring | in-memory | <1s |
| 7 | SERP LinkedIn DM | sem=20 | ~20s |
| 8 | Reachability check | in-memory | <1s |

**Target: 200 domains processed in under 2 minutes.**

### SCRAPER STACK (Directive #295)

**Primary: httpx** (`src/integrations/httpx_scraper.py`) — free, no rate limit, ~2–5s/domain.
- HTTPS-first, browser User-Agent, returns `status_code / html / title / content_length`
- Fallback to Spider if httpx returns `None` or HTML < 1000 chars (JS-rendered stub)
- `scraper_used: "httpx" | "spider"` tracked on every enrichment record

### AU COUNTRY FILTER (Directive #295)

Applied in `free_enrichment.py` after scrape, before affordability scoring.

`_is_au_domain(domain, html)`:
1. `.au` TLD → pass immediately
2. AU phone pattern (`02/03/04/07/08` or `+61`) in HTML → pass
3. AU state abbreviation (`NSW/VIC/QLD/SA/WA/TAS/NT/ACT`) in HTML → pass
4. 4-digit AU postcode pattern in HTML → pass
5. None found → `non_au: True` → rejected at affordability gate

Catches foreign domains that pass TLD check (e.g. `dentatur.com`, `uswatersystems.com`).

### SONNET/HAIKU INTELLIGENCE LAYER (Directive #296)

Replaces regex/rule-based analysis with LLM comprehension at five pipeline stages.

**Five stages** (`src/pipeline/intelligence.py`):

| Stage | Function | Model | Replaces | Cost/domain |
|-------|----------|-------|----------|-------------|
| 3b | `comprehend_website()` | Sonnet | Regex extraction | ~$0.010 |
| 7 | `classify_intent()` | Sonnet | Point-counting scorer | ~$0.008 |
| 7b | `analyse_reviews()` | Sonnet | No equivalent (new) | ~$0.005 |
| 4 | `judge_affordability()` | Haiku | Rule-based gates | ~$0.001 |
| 7c | `refine_evidence()` | Haiku | Hardcoded evidence strings | ~$0.002 |

**Total: ~$0.026/domain. ~$16.50/100 DMs at 23% yield. Ignition margin >96%.**

**Prompt caching design:** Static system prompt block (marked `cache_control: ephemeral`) always first; variable HTML/review content last. Anthropic prompt-caching-2024-07-31 beta header on every call.

**Semaphores:** `GLOBAL_SEM_SONNET=12` and `GLOBAL_SEM_HAIKU=15` defined in `intelligence.py`, imported by `pipeline_orchestrator.py`. Prevents circular import.

**Reliability:** httpx direct API (no SDK). JSON response with `try/except` fallback on every call — pipeline never crashes on LLM failure. Token usage logged per call for cost tracking.

**Wiring in `run_parallel()` when `intelligence=` is passed:**
```
httpx scrape → comprehend_website (Sonnet)
→ judge_affordability (Haiku) → affordability gate
→ DFS ads + GMB → classify_intent (Sonnet)
→ intent gate (NOT_TRYING rejected)
→ analyse_reviews (Sonnet) → refine_evidence (Haiku)
→ DM discovery → ProspectCard
```
Graceful fallback to rule-based scorer when `intelligence=None` (backwards compatible).

---

### PARALLEL WORKER ORCHESTRATOR (Directive #295)

`PipelineOrchestrator.run_parallel()` — for demo-speed dashboard population.

**Global semaphore pool** (module-level singletons shared across all workers):
| Semaphore | Limit | Controls |
|-----------|-------|---------|
| `GLOBAL_SEM_DFS` | 25 | All DFS API calls |
| `GLOBAL_SEM_SCRAPE` | 50 | httpx + Spider scrapes |
| `GLOBAL_SEM_SONNET` | 12 | Claude Sonnet calls |
| `GLOBAL_SEM_HAIKU` | 15 | Claude Haiku calls |

**Worker design:**
- `num_workers` coroutines (default 4) launched via `asyncio.gather`
- Round-robin across `category_codes` list
- Shared state: `asyncio.Lock` on results list, stats, seen_domains set
- Race-condition guard: target check inside `results_lock` before append
- `on_prospect_found` async callback for streaming to dashboard
- `exclude_domains` set passed in (caller builds from `campaign_leads`)

**Phase 4 — Rank + Present (day 3):** Dashboard populates. Sorted by STRUGGLING > TRYING > DABBLING. Evidence statements on each card.

---

### TWO-DIMENSION SCORING (Directive #291 — `src/pipeline/prospect_scorer.py`)

**Dimension 1: Affordability** — can they pay?

Hard gates (reject immediately): sole_trader, gst=False, unreachable (no website + no ABN).

Soft signals: entity_type (trust/company/partner), GST, professional email, CMS, SSL, multi-page. Max ~10.

Gate: score ≥ 3. Bands: **LOW (reject)** | **MEDIUM** | **HIGH** | **VERY_HIGH**

**Dimension 2: Intent** — will they buy?

Free signals (from Spider HTML — zero extra cost):

| Signal | Trigger | Points |
|--------|---------|--------|
| website_no_analytics | has website but no GA4/GTM | 2 |
| ads_tag_no_conversion | AW- tag in HTML, no conversion tracking | 3 |
| booking_no_analytics | has booking system, no analytics | 2 |
| meta_pixel | Facebook Pixel present | 1 |
| social_links | team page or social links | 1 |
| stale_cms | professional CMS present | 1 |

Gate: NOT_TRYING band skips paid enrichment entirely.

Paid signals (after free gate passes, gate passers only):

| Signal | Source | Points |
|--------|--------|--------|
| running_gads | DFS Ads Search $0.002 | 2 |
| gmb_established | GMB review count > 20 | 1 |

Bands: **NOT_TRYING (0–2, skip paid)** | **DABBLING (3–4)** | **TRYING (5–7)** | **STRUGGLING (8+)**

**Evidence strings:** Each signal produces a paired statement (effort + gap) for Haiku outreach generation. Examples:
- "Running Google Ads but missing conversion tracking — wasting budget"
- "Has a WordPress site but no analytics installed"
- "Has online booking but can't measure which channels drive bookings"

**Reachability:** Delivery gate only. Email OR LinkedIn required. Not scored.

---

### DM IDENTIFICATION WATERFALL

T-DM1 — DFS SERP site:linkedin.com/in (70% hit, $0.01/query, AU-filtered)
T-DM2 — Bright Data LinkedIn company lookup ($0.00075/record, fallback)
T-DM3 — Spider team page names (free)
T-DM4 — ABN entity surname (free, LOW confidence)

ABN multi-strategy matching (Directive #289, verified #297): 4-strategy keyword waterfall before live API call. 8/10 domains matched in live test.

**Directive #297 audit confirmed:** abn_registry has 2.4M rows and is queryable. FreeEnrichment.enrich_from_spider() correctly calls _match_abn() → _local_abn_match() → keyword intersection against abn_registry. The 0/300 result in Run 2 was caused by PR #252 not yet being merged + Settings.ABN_LOOKUP_GUID case bug — both fixed on main. ABN data (entity_type, gst_registered, abn_confidence) flows through enrichment dict to score_affordability() and judge_affordability() gates.

---

### TERRITORY

Locks by geography only, not industry. Two agencies in same city — different service areas or pool large enough (cross-category) that collision is minimal. First to discover claims the prospect.

---

### PROSPECT CARD FORMAT

Each viable prospect contains:

| Field | Source |
|-------|--------|
| Domain | DFS discovery |
| Company name | Spider page title (cleaned) |
| Location | JSON-LD suburb |
| Entity type | ABN registry |
| GST registered | ABN registry |
| Affordability band + score | ProspectScorer.score_affordability() |
| Intent band + score | ProspectScorer.score_intent_full() |
| Evidence statements | Intent signals — each produces effort+gap pair for Haiku |
| Google Ads active | DFS Ads Search ($0.002) or Spider AW- tag (free) |
| Ad count | DFS Ads Search |
| Meta Pixel | Spider HTML tag detection (free) |
| GMB rating | DFS Maps GMB ($0.0035) |
| GMB review count | DFS Maps GMB |
| GMB response rate | DFS Maps GMB (when available) |
| DM name | DMIdentification waterfall |
| DM title | DMIdentification waterfall |
| DM LinkedIn URL | T-DM1 SERP or T-DM2 Bright Data |
| DM confidence | HIGH/MEDIUM/LOW |
| DM tier | T-DM1/T-DM2/T-DM3/T-DM4 |

---

### COST MODEL

Variable cost per viable DM: **~$0.07**

| Step | Cost |
|------|------|
| Spider scrape | $0.01 |
| DFS Ads Search | $0.002 (gate passers only) |
| DFS Maps GMB | $0.0035 (gate passers only) |
| DFS SERP LinkedIn | $0.01 |
| DFS discovery (amortised) | $0.001 |
| **Total** | **~$0.027–$0.07** |

At Ignition tier (600 prospects/month): **~$42/month variable COGS**
Subscription: $2,500 AUD/month → **98.3% gross margin**

Per tier:
| Tier | Prospects | Variable COGS | Revenue | Margin |
|------|-----------|--------------|---------|--------|
| Spark | 150 | ~$10 | $750 AUD | 98.7% |
| Ignition | 600 | ~$42 | $2,500 AUD | 98.3% |
| Velocity | 1,500 | ~$105 | $5,000 AUD | 97.9% |

---

### PIPELINE ORCHESTRATOR (Directive #288 + #290 + #291)

`src/pipeline/pipeline_orchestrator.py` — `PipelineOrchestrator.run()`

```
while len(results) < target_count:
    domains = discovery.pull_batch(category_code, location, limit, offset)
    if not domains: break  # category exhausted
    for domain in domains:
        enrichment = free_enrichment.enrich(domain)   # Spider + DNS + ABN
        
        # GATE 1: Affordability
        afford = scorer.score_affordability(enrichment)
        if not afford.passed_gate: continue
        
        # GATE 2: Intent free (rejects NOT_TRYING before paid enrichment)
        intent_free = scorer.score_intent_free(enrichment)
        if not intent_free.passed_free_gate: continue
        
        # Paid enrichment (gate passers only)
        ads_data = await dfs.ads_search_by_domain(domain)
        gmb_data = await dfs.maps_search_gmb(company + suburb)
        
        # Full intent score with paid data
        intent = scorer.score_intent_full(enrichment, ads_data, gmb_data)
        
        dm = dm_identification.identify(domain, ...)
        if not dm.name: continue
        
        if not (dm.linkedin_url or has_email): continue  # reachability
        results.append(ProspectCard(evidence=intent.evidence, ...))
```

`PipelineStats`: discovered / enriched / affordability_rejected / intent_rejected / paid_enrichment_calls / dm_found / dm_not_found / unreachable / viable_prospects / total_cost_usd / elapsed_seconds

All dependencies injected (fully testable without DB).

---

### PIPELINE TEST RESULTS (Run 1: Mar 29 2026, pre-#291 scoring)

| Metric | Result |
|--------|--------|
| Target | 100 viable DMs |
| Domains tested | 200 |
| Enrichment success | 84% |
| Affordability gate pass | 74% of enriched |
| DM hit rate | 81% of gate passers |
| Viable prospects | 100/200 = 50% conversion |
| Cost | $3.51 = $0.035/DM |
| Time | 7.3 min |

Run 2 (Mar 30 2026, with #291 Intent gate): 69/100 DMs from 300 domains before timeout. Intent gate rejected 64% of affordable businesses (NOT_TRYING). Conversion 23% — correct behaviour, higher quality. Cost ~$0.071/DM. Speed blocked by ABN API fallback bug (fixed in #292).

---

### DEAD ENDPOINTS (do not use)


| Endpoint | Why Dead |
|----------|---------|
| DFS paid_etv | AU: top dental domain = $150/mo. Unusable for budget detection. |
| DFS Domain Technologies | AU: 1.3% coverage (1/78 domains). Cannot build tech gap signals. |
| DFS Ranked Keywords | AU: 20% coverage (16/78 domains). Unreliable for SEO gap signals. |
| DFS Backlinks | 40204 error — separate subscription not provisioned. |
| DFS Google Jobs | 40402 Invalid Path on all calls. Broken endpoint. |
| Layer 3 Bulk Traffic Estimation | Redundant — domain_metrics_by_categories already returns organic metrics. |

---

### PROVEN ENDPOINTS (v7 foundation)

| Endpoint | Coverage | Cost | Signal |
|----------|---------|------|--------|
| DFS domain_metrics_by_categories | 24,231 AU dental / 31,445 AU plumbing domains | $0.0015/domain | Organic ETV, keyword count, category confirmation |
| Google Ads Transparency Center | 5/5 AU coverage | FREE (Python scraper) | Binary: is business running Google Ads |
| Website scraping (direct HTTP) | 5/5 AU coverage | FREE | Full tech stack, CMS, tracking codes, team names, contact info |
| ABN verification (local JOIN) | 5/5 AU coverage | FREE | GST registration = $75k+ revenue confirmed |
| GMB + Reviews (DFS SERP) | 4/5 GMB match, 5/5 reviews | $0.0035/domain | Rating, review count, owner response rate, complaint themes |

---

### LAYER 1: AGENCY ONBOARDING

CRM connect → extract services sold, client history, deal sizes per service, industries won.
LinkedIn connect → communication style, connection exclusion list.
System builds Agency Profile automatically.
Signal config generated from their services — each service maps to category codes + scoring weights.
Output: Agency Profile + Signal Config + Exclusion List

**Status: BUILT** — HubSpot/GHL/Pipedrive/Close OAuth complete. Unipile LinkedIn complete. Onboarding flow complete. Signal configs seeded for marketing_agency.

---

### LAYER 2: DISCOVERY (domain_metrics_by_categories only)

Single DFS call: `domain_metrics_by_categories` with AU category codes for target industry.
Filter: location_code=2036 (AU), ordered by organic_etv descending.
Returns: domain, organic_etv, organic_keywords, category, subcategory.
Dedup against BU + blocklist. Insert new rows at pipeline_stage=1.

**v7 change from v6:** 5-source parallel discovery REPLACED with single endpoint. Rationale: Google Jobs broken (40402), HTML Terms unreliable for AU, Competitors expansion better as an enrichment step. domain_metrics_by_categories alone returns 22,592 AU dental domains — more than sufficient.

### MULTI-CATEGORY SERVICE-FIRST DISCOVERY (Directive #298)

**Architectural shift:** Campaign = service the agency sells. Discovery sweeps nationally across ALL DFS categories for businesses showing signals they need that service. Industry and geography are optional filters, not campaign definitions.

**`src/config/category_registry.py`** — Category registry:
- `SERVICE_CATEGORY_MAP`: seo / google_ads / social_media / web_design → 20 AU category codes each
- `INDUSTRY_VERTICALS`: dental, trades, legal, construction, hospitality, automotive, real_estate, accounting, medical, fitness, hair_beauty, veterinary, hvac, marketing
- `get_discovery_categories(services, preferred_industries)`: returns union of codes matching services; preferred_industries codes sort first
- `MAX_CATEGORIES_PER_CALL = 20` (safe DFS batch limit per call)

**`src/pipeline/discovery.py`** — `MultiCategoryDiscovery`:
- `discover_prospects(category_codes, location, exclude_domains, batch_callback)`: batches codes at 20/call, deduplicates, fires callback per batch
- `pull_batch()`: single-category stateless batch (orchestrator-compatible)

**`run_parallel(discover_all=True)`**: pre-fetches ALL domains across categories into `asyncio.Queue` before workers start — workers consume from queue instead of lazy `pull_batch` calls.

**Category coverage (20 unique AU categories across 14 verticals):**
Dental, Plumbing, Electrical, HVAC, Legal, Construction, Real Estate, Accounting, Medical, Fitness, Hair & Beauty, Veterinary, Home Services, Marketing.

Cost: $0.0015/domain (corrected Mar 2026 — was estimated $0.001)
Sprint: Sprint 1

**Dual discovery sources (Directive #284):**
- `DiscoverySource.DOMAIN_CATEGORIES` — `domain_metrics_by_categories` (default). Professional categories (dental, medical): clean. Trades categories (plumbing, construction): top-200 polluted by gov/suppliers; tail ($101–$500 ETV) is 90% real businesses.
- `DiscoverySource.MAPS_SERP` — DFS Maps SERP suburb sweep (stub only — Sprint 5). Required for trades categories where professional-to-aggregator ratio at top is 0%.

**Bug fixed (Directive #284):** `first_date`/`second_date` were missing from the API payload — all calls returned 40501 silently. Fixed: defaults to 6-month window, caller can override. Error no longer swallowed.

**Status: BUILT (v7)** — single `domain_metrics_by_categories` call, sequential per category, AU domain filter, trajectory computation, Gate 1 applied post-insert. Directive #280, PR #242. Date params fixed + DiscoverySource enum added: Directive #284, PR #247.

---

### GATE 1: Organic Signal Gate

PASS if organic_etv > 0 OR organic_keywords > 0
REJECT if both zero → pipeline_stage = -1, filter_reason = "no_organic_signal"
No-domain rows → advance for GMB-only path

---

### LAYER 3: FREE INTELLIGENCE SWEEP

All free. Run in parallel on passing domains:

**a) Website scrape (direct HTTP)**
- Full page HTML fetch
- Extract: tech stack (JS libraries, pixels, CMS, CDN), tracking codes (GA4, GTM, FB Pixel, Google Ads), team names (About page), contact info (email, phone)
- Cost: FREE
- Coverage: 5/5 proven

**b) Google Ads Transparency Center**
- Python scraper against `adstransparency.google.com`
- Output: binary `is_running_ads: true/false`
- Cost: FREE
- Coverage: 5/5 proven
- Note: scraper fragility — Google may change HTML structure. Monitor and maintain.

**c) DNS + TLS check**
- MX record presence → has email infrastructure
- SPF/DKIM presence → email sender configured
- TLS cert issuer → hosting provider signal
- Cost: FREE

**d) ABN registry JOIN (local)**
- Match `display_name` + `state` against 2.4M-row local table
- Output: abn, gst_registered (confirmed $75k+ revenue), entity_type, registration_date
- Cost: FREE
- Never describe as external API call

**e) Phone carrier lookup**
- AU mobile → carrier name (Telstra, Optus, Vodafone)
- Validates number is real + active AU mobile
- Cost: FREE API (planned Sprint 2)

Output: free_intelligence_complete, pipeline_stage = 2

Sprint: Sprint 2

---

### GATE 2: Revenue Confirmation Gate

PASS if: gst_registered = true (confirmed $75k+ revenue) OR organic_etv > configurable threshold
WARN if gst not matched (possible sole trader or young business)
NEVER hard-reject on GST alone — sole traders and new businesses are valid prospects

---

### LAYER 4: GMB + REVIEWS (paid enrichment, cheap)

DFS SERP Google Maps: Place ID, category, rating, review count, address, phone, hours, owner response rate.
Reviews analysis: complaint themes, sentiment (from review text sample).
GMB claimed status via Bright Data ($0.001/record) — optional, for top-tier prospects only.

Cost: $0.0035/domain (DFS SERP)
Coverage: 4/5 GMB match proven on AU dental sample
Sprint: Sprint 3

---

### GATE 3: Business Legitimacy Gate

PASS if: GMB listing found OR ABN matched
REJECT if: no GMB, no ABN, and no website → likely dissolved or non-trading business

---

### LAYER 5: COMPETITIVE + BRAND INTELLIGENCE (paid, selective)

Only for prospects passing Gate 3. Run in parallel:

**a) Competitors Domain ($0.01)** — top 5 SERP competitors per prospect
**b) Brand SERP / Indexed Pages ($0.005)** — how many pages indexed, brand search presence
**c) Google Ads Advertisers ($0.006)** — which keywords they actively bid on (supplements Transparency Center binary signal)

Cost: ~$0.02/domain average (not all get all endpoints)
Sprint: Sprint 3

---

### GATE 4: Scoring Gate (propensity threshold)

PASS if propensity_score >= 30
REJECT: stays in BU for future re-scoring when signals refresh

---

### LAYER 6: SCORING (v7 signal alignment)

v7 scoring uses only CONFIRMED AU signals (no dead DFS endpoints):

| Dimension | v7 Signal Source | v6 Source (replaced) |
|-----------|-----------------|---------------------|
| Budget | Google Ads Transparency (binary) + Competitors Domain ads spend | DFS paid_etv (DEAD) |
| Pain | GMB rating + review complaints + organic_etv trend | DFS Historical Rank (unreliable AU) |
| Gap | Website scrape tech stack gaps + ABN entity age | DFS Domain Technologies (DEAD) |
| Fit | GMB category + organic_keywords count + competitor analysis | DFS Ranked Keywords (weak AU) |

Score: 0-100 propensity. Best-matched service = outreach angle.
Revenue estimate: sum of agency retainers per matched service.
Score reason in plain English.

Sprint: Sprint 4

---

### GATE 5: DM Enrichment Gate

PASS if propensity_score >= 50

---

### LAYER 7: DECISION MAKER DISCOVERY

Waterfall (return on first hit — ordered by hit rate, not cost):

**T-DM1 — DFS Google SERP → LinkedIn Profiles (Directive #287)**
- Client: `src/clients/dfs_labs_client.py` method `search_linkedin_people(company_name)`
- Query: `site:linkedin.com/in "{company_name}"` → `/v3/serp/google/organic/live/advanced`
- AU location filter: prefer `au.linkedin.com` URLs; accept AU city/state in snippet; reject non-AU
- Score by title priority: owner > founder > co-founder > director > principal > managing > ceo > partner
- Confidence: HIGH (owner/founder/director) | MEDIUM (ceo/partner/president) | LOW (first result, no title match)
- **Hit rate: 70% (7/10 AU domains, Mar 2026 spike)**
- Cost: **$0.01/query**
- `source="serp_linkedin"`, `tier_used="T-DM1"`

**T-DM2 — Bright Data LinkedIn Company Lookup (Directive #286, fallback)**
- Client: `src/integrations/brightdata_client.py` (`BrightDataLinkedInClient`)
- Method: `lookup_company_people(company_name, domain, linkedin_url)`
- Dataset `gd_l1vikfnt1wgvvqz95w` → employees[] → `pick_decision_maker()`
- Cost: **$0.00075/record**
- `source="brightdata_linkedin"`, `tier_used="T-DM2"`

**T-DM3 — Website Scrape Fallback (free, from Layer 3)**
- Team page names from `spider_data.team_names` or Dr. names in page title
- Confidence: MEDIUM | Cost: FREE | `tier_used="T-DM3"`

**T-DM4 — ABN Entity Name Fallback**
- Extract non-biz-word from entity_name (sole trader surname candidate)
- Confidence: LOW | Cost: FREE | `tier_used="T-DM4"`

Orchestration: `src/pipeline/dm_identification.py` (`DMIdentification.identify()`)
Returns: `DMResult(name, title, source, confidence, linkedin_url, tier_used)`
Wired into pipeline via PipelineOrchestrator — Directive #290.
FreeEnrichment.enrich() calls DMIdentification; GMB enrichment added for gate passers.

Cost: $0.01/domain (T-DM1 SERP, 70% hit) → $0.00075/record (T-DM2 BD, fallback)
Sprint: Sprint 4 (Directive #287)

---

### SCORING (legacy reference — superseded by ProspectScorer)

`src/pipeline/affordability_scoring.py` — `AffordabilityScorer` — left in place, no longer primary scorer.
**Active scorer:** `src/pipeline/prospect_scorer.py` — `ProspectScorer` — see Two-Dimension Scoring above.

---

### LAYER 8: MESSAGE GENERATION (Haiku)

Model: `claude-haiku-4-5-20251001` with prompt caching (90% discount on system prompt).

Inputs:
- Agency Profile (voice, tone, case studies, value prop)
- ALL intelligence from Layers 3–7
- Best outreach angle (matched service with strongest gap evidence)
- Competitor data for pain amplification (Layer 5)
- Revenue estimate for internal prioritisation

Per channel:
- Email: reference one specific signal, ask one question, <150 words
- LinkedIn: shared context, connection note, <300 chars
- Voice: knowledge card JSON {trigger, talking_point, objective, fallback}
- SMS: direct, one line, <160 chars

Cost: ~$0.003/prospect (with caching)
Sprint: Sprint 6

---

### GATE 7: Outreach Approval Gate

Agency reviews top 10. Batch release: "Release All" / "Review More" / "Release with Exceptions".
Kill switch always visible.

---

### LAYER 9: SCHEDULING

All prospects found at start of month. Outreach scheduled across 30 days:
- Email: daily send limits per warmed inbox
- LinkedIn: 20–25 connections/day, business hours, randomised delays
- Voice AI: TCP Code calling hours (9am-8pm weekday, 9am-5pm Saturday, no Sunday, no public holidays)
- SMS: daily caps, DNCR pre-check

Follow-up sequences timed per channel.
Sprint: Sprint 6

---

### LAYER 10: QUOTA LOOP

Runs at start of month until tier target met:
1. Run Layers 2–9 (primary discovery)
2. Count outreach-ready prospects
3. If gap > 0: re-score BU backlog near threshold, advance stuck rows, expand discovery, cross-service discovery, retry DM failures
4. Loop until gap = 0 or strategies exhausted
5. If still short: deliver what we have + notify agency

Sprint: Sprint 6

---

### COST PER QUALIFIED PROSPECT (v7, proven AU data)

| Layer | v7 Cost | v6 Cost (replaced) |
|-------|---------|-------------------|
| Layer 2 Discovery | $0.001 amortised | $0.10 (5-source) |
| Layer 3 Free Sweep | FREE | $0.001 (bulk filter) |
| Layer 4 GMB + Reviews | $0.0035 | $0.001 |
| Layer 5 Competitive | $0.02 avg | $0.04 |
| Layer 6 Scoring | FREE | FREE |
| Layer 7 DM Discovery | $0.05–$0.15 | $0.02 |
| Layer 8 Haiku | $0.003 | $0.01 |
| **Total** | **$0.08–$0.15** | **$0.27** |

**Margin improvement (v7 vs v6):**
- Spark (150 records): COGS ~$12–$22 → margin **97%** at $750 AUD
- Ignition (600 records): COGS ~$48–$90 → margin **96%** at $2,500 AUD
- Velocity (1500 records): COGS ~$120–$225 → margin **95%** at $5,000 AUD

---

### SIGNAL CONFIG SCHEMA (v7)

`signal_configurations` table (v6 schema, Directive #271 — unchanged for v7):
- `vertical`: industry slug (marketing_agency, dental_practice, etc.)
- `services`: JSONB array with problem_signals/budget_signals/not_served_signals per service
- `discovery_config`: category_codes for domain_metrics_by_categories
- `enrichment_gates`: score thresholds
- `competitor_config`: expansion settings
- `channel_config`: email/LinkedIn/voice/SMS toggles

**v7 signal source mapping per service:**
Budget signals: Google Ads Transparency (binary) + Competitors Domain spend
Pain signals: GMB rating < 4.0, GMB review complaint themes, organic_etv decline
Gap signals: website scrape — missing tools/pixels/CMS capabilities
Fit signals: GMB category codes, organic_keywords, competitor SERP presence

---

## SECTION 4 — TIERS + PRICING (ratified Mar 26 2026)

| Tier | Price/mo AUD | Records/mo | Founding Price |
|------|-------------|------------|----------------|
| Spark | $750 | 150 | $375 |
| Ignition | $2,500 | 600 | $1,250 |
| Velocity | $5,000 | 1,500 | $2,500 |

- Dominance: REMOVED from launch (no AU marketing agency needs 3,500 records — add later for recruitment/MSP verticals or white-label)
- EVERY tier = full BDR: all DFS intelligence, all 4 channels, Haiku personalisation, full automation
- ONLY differentiator is volume
- Non-linear pricing prevents tier stacking
- Margins: Spark 85%, Ignition 82%, Velocity 77%

---

## SECTION 5 — CAMPAIGN MODEL (ratified Mar 26 2026)

- Campaign = service the agency sells, mapped to a signal pattern
- Agency confirms services from CRM analysis; system generates signal configs automatically
- Discovery is ONE unified sweep across ALL signals for all campaigns
- Haiku picks the best angle per prospect based on signal match
- Campaigns are dashboard VIEWS (like Gmail labels), not billing constraints
- No campaign count limits per tier
- Agency approves strategy, not individual prospects

---

## SECTION 6 — ONBOARDING + APPROVAL FLOW (ratified Mar 26 2026)

Onboarding sequence:
CRM + LinkedIn connect → Agency Profile auto-builds → Strategy Screen (signals explained in plain English, optional filters) → Dashboard populates LIVE (no email — agency watches pipeline stages fill, leaderboard builds row by row)

Approval flow:
- No per-prospect approval
- Agency reviews top 10 to confirm quality
- Then batch release: "Release All" / "Review More" / "Release with Exceptions"
- Month 2+: single Release button
- Kill switch always visible
- Full transparency — agency sees ALL prospects + intelligence + contacts
- Export permitted — they've paid, data is theirs
- Value = monthly refresh + automation + CIS, not data hostage-taking

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

## SECTION 8 — ENRICHMENT STACK (v7 — updated Mar 29 2026)

### FREE TIER (v7 foundation)

| Source | What | Cost | Status |
|--------|------|------|--------|
| ABN registry local JOIN | GST status (confirms $75k+ revenue), entity type, registration date | FREE | ✅ Live — 2,418,836 rows |
| Website scrape (Spider.cloud) | Tech stack, CMS, tracking codes (GA4, GTM, Meta Pixel, Google Ads), contact info, JSON-LD address | FREE (direct HTTP) / $0.01/page (Spider.cloud) | ✅ Proven (10/10 Segment 2 test, Mar 2026) |
| Google Ads Detection (two-tier) | Binary: is business running Google Ads | FREE (tag) + $0.002 (DFS) | ✅ LIVE — Directive #291. Tier 1: Spider AW-tag/Meta Pixel detection (free, 4/10 dental SMBs detected). Tier 2: DFS /ads_search/live/advanced (3/10 detected, complementary). Combined: 5/10 (50%) hit rate on dental SMBs. |
| DNS + MX/SPF/DKIM check | Email maturity scoring (PROFESSIONAL/WEBMAIL/NONE), MX provider | FREE | ✅ Live — Segment 2 validated. DKIM excluded from scoring (0/10 AU SMBs have detectable DKIM). |
| Phone carrier lookup | AU mobile carrier validation | FREE | Planned Sprint 5 |

**Free enrichment quality fixes (Directive #285, Mar 29 2026):**
- **ABN confidence scoring:** `ABNMatchConfidence` enum (EXACT ≥90% / PARTIAL 60–89% / LOW <60%) via `difflib.SequenceMatcher`. Prevents false gate failures on compound/acronym domains. `abn_confidence` returned from `_match_abn` (BU column pending migration).
- **JSON-LD address extraction:** `_extract_jsonld_address()` parses `<script type="application/ld+json">` blocks, handles `@graph` wrappers. Returns `{street, suburb, state, postcode}`. Fallback to regex if no JSON-LD. Expected coverage: 8+/10 vs 3/10 with regex alone.
- **Email maturity collapsed:** Old MATURE/BASIC/WEBMAIL/NONE → New PROFESSIONAL (custom MX + SPF) / WEBMAIL (MX, no SPF) / NONE. DKIM kept for data collection but excluded from classification.
- **Spider.cloud cost validated:** $0.01/page (10-page Segment 2 test = $0.10). DNS + ABN = FREE. Total per-domain free enrichment cost: ~$0.01.

**ABN multi-strategy matching (Directive #289, Mar 29 2026):**

Root cause of 0/200 ABN matches in E2E test: single `LIKE '%phrase%'` query never matched ABN entity names derived from domain strings ("dentists at pymble" ≠ "PYMBLE DENTAL PTY LTD").

Replaced with a 4-strategy waterfall in `_match_abn` — returns on first EXACT or PARTIAL hit, falls back to best LOW if all strategies return LOW, returns `abn_matched=False` only when all strategies find nothing:

| Strategy | Method | Notes |
|---|---|---|
| S1 Domain keywords | Strip TLD, split hyphens/stopwords (≥5-char threshold), AND-intersect keywords in local table | Handles `dentistsatpymble` → `["dentists","pymble"]` |
| S2 Title keywords | Clean Spider page title (strip "Home \|", nav suffixes), AND-intersect in local table | Dominant strategy in live test (5/10) |
| S3 Suburb + keyword | JSON-LD address suburb + primary domain keyword, AND-intersect | Needs `website_address.suburb` from Spider scrape |
| S4 Live ABN API | `ABRSearchByNameAdvancedSimpleProtocol2017` fuzzy search, cross-ref local table for `gst_registered`/`entity_type` | Fallback; ABN API returns individual profiles not gst_registered, so local ABN lookup follows |

New helpers: `_abn_clean_entity_name()` (strips PTY LTD, THE TRUSTEE FOR), `_extract_domain_keywords()`, `_local_abn_match()`, `_local_abn_gst()`, `_abn_result_from_row()`.

Live Task D validation: **8/10 domains matched** (vs 0/200 before fix). Cost: FREE (local table + ABN API free tier).

### PAID TIER

| Source | What | Cost | Status |
|--------|------|------|--------|
| DFS domain_metrics_by_categories | Domain discovery by AU industry category. Returns organic_etv, organic_keywords, category | $0.0015/domain | ✅ Proven (24,231 AU dental / 31,445 AU plumbing domains, Mar 2026 spike) |
| DFS SERP Google Maps | GMB: Place ID, category, rating, reviews, address, phone, hours | $0.0035/domain | ✅ Live — `DFSLabsClient.maps_search_gmb()` wired. Called for gate passers only. Returns `gmb_review_count` into affordability scorer. |
| DFS Competitors Domain | Top 5 SERP competitors per prospect | $0.01/call | ✅ Live |
| DFS Brand SERP / Indexed Pages | Brand search presence, indexed page count | $0.005/call | Planned Sprint 3 |
| DFS Google Ads Advertisers | Keywords actively bid on (complements Transparency binary) | $0.006/call | ✅ Live in layer_2_discovery.py |
| Bright Data GMB Dataset | GMB deep enrichment (claimed status, full hours, photos) | $0.001/record | ✅ Live — dataset `gd_m8ebnr0q2qlklc02fz` |
| Bright Data LinkedIn Company (company enrichment) | Company headcount, industry, LinkedIn URL via `bright_data_client.py` | $0.025/record | ✅ Live |
| DFS SERP LinkedIn People (Directive #287, T-DM1) | `search_linkedin_people()` → `site:linkedin.com/in "{company}"` → AU filter → title priority. 70% hit rate. | **$0.01/query** | ✅ Built — not yet wired to pipeline |
| Bright Data LinkedIn DM lookup (Directive #286, T-DM2) | Company employees + titles → pick_decision_maker() via `brightdata_client.py`. Key: `2bab0747...` | **$0.00075/record** | ✅ Built — not yet wired to pipeline |
| Leadmagic email-finder | DM email from name + domain | $0.015/call | ✅ Live (plan unpurchased — mock mode) |
| Leadmagic mobile-finder | DM mobile from LinkedIn URL | $0.077/call | ✅ Live (plan unpurchased) |
| Leadmagic employee-finder | Employees at domain | ~$0.05/domain | ✅ Live |
| ZeroBounce | Email verification (catch-all, invalid, spamtrap) | $0.005/call | ✅ Live |

### DEAD ENDPOINTS (do not re-enable)

| Endpoint | Why Dead | Confirmed |
|----------|---------|-----------|
| DFS paid_etv | AU: top dental domain = $150/mo. Unusable. | Mar 2026 live test |
| DFS Domain Technologies | AU: 1.3% coverage (1/78 domains). | Mar 2026 live test |
| DFS Ranked Keywords | AU: 20% coverage (16/78). | Mar 2026 live test |
| DFS Backlinks | 40204 error — subscription not provisioned. | Mar 2026 live test |
| DFS Google Jobs | 40402 Invalid Path. Broken endpoint. | Mar 2026 live test |
| DFS Bulk Traffic Estimation (Layer 3) | Redundant — domain_metrics_by_categories returns organic metrics. | v7 decision |
| Hunter.io | DEPRECATED | Directive #167 |
| Kaspr | DEPRECATED | Directive #167 |
| Proxycurl | DEPRECATED | Directive #167 |
| Apollo (enrichment) | DEPRECATED | Directive #167 |
| Clay (enrichment) | DEPRECATED | Directive #167 |
| Jina AI Reader (Stage 5) | Removed — too slow (16s per domain) | Directive #266 |

Domain blocklist (`src/utils/domain_blocklist.py`): platforms, social, government, builder/hosting domains. Checked at BU INSERT.

---

## SECTION 9 — DATA PROVIDER OPERATIONAL NOTES

- BD GMB dataset: `gd_m8ebnr0q2qlklc02fz` (Google Maps full information). Discovery mode: `type=discover_new&discover_by=keyword`. Enrichment mode: `discover_by=location` or `discover_by=place_id`.
- DFS spending cap: $50 USD/day — not a blocker for normal runs.
- AU suburb → lat/lng mapping: Elkfox CSV (`src/data/au_suburbs.csv`, MIT licensed, 16,875 records).

---

## SECTION 10 — OUTREACH STACK

| Channel | Provider | Status |
|---------|----------|--------|
| Email | Salesforge | Active |
| LinkedIn | Unipile | Active |
| Voice AI | ElevenAgents + Claude Haiku ("Alex") | Active |
| SMS | Telnyx | On hold until launch |
| Direct Mail | REMOVED from stack | — |

Voice AI / Alex details:
- Built on ElevenAgents + Claude Haiku (`claude-haiku-4-5-20251001`)
- Australian TCP Code compliance built in
- Mandatory recording disclosure as first spoken line
- Calling hour restrictions enforced programmatically
- "Show don't tell" personalisation — references prospect's situation, doesn't pitch features
- Knowledge base card per prospect: company name, trigger, talking point, objective, fallback

Outreach sequence timing: defined in Layer 10 scheduling engine (Directive #278).

---

## SECTION 11 — BUSINESS UNIVERSE

- BU is THE PRODUCT — one row per discovered business, all intelligence accumulates over time
- abn_registry = renamed 2.9M ABR table, enrichment source only (not the BU itself)
- campaign_leads junction table for agency claims on prospects
- ABR match rates: ~10% SQL match, ~67% API match
- 468 leads + 429 lead_pool = historical test data, archived
- CIS tables all 0 rows (not yet populated)
- BU House Seed strategy: 10% of campaign volume, gap-fill by default, steerable toward institutional buyer industries when deal in pipeline — must be disclosed to customers with incentive
- BU schema: ~97 columns. Query `information_schema.columns WHERE table_name = 'business_universe'` for current column list. Key signal fields: `dfs_paid_etv` (budget), `tech_gaps` (service gaps), `propensity_score` + `reachability_score` (two separate scores, both 0–100).

---

## SECTION 12 — BUILD SEQUENCE (active)

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
| Sprint 4 | #287 | SERP-first DM waterfall: DFS SERP T-DM1 (70% hit), BD T-DM2, AU location filter | COMPLETE — PR #250 (pending merge) |
| Sprint 5 | #288 | Composite affordability scorer (7 signals, 4 bands) + streaming PipelineOrchestrator + ProspectCard | COMPLETE — PR #251 (pending merge) |
| Sprint 5 | #289 | ABN multi-strategy matching waterfall (4 strategies, 8/10 live match rate) | COMPLETE — PR #252 merged |
| Sprint 5 | #290 | Wire orchestrator: pull_batch + enrich methods, DFS Maps GMB, ads transparency real | COMPLETE — PR #253 merged |
| Sprint 5 | #284–#291 | Discovery + enrichment quality + DM waterfall + scoring + ads detection + pipeline orchestrator | ALL COMPLETE — PRs #247–#254 |
| Sprint 6 | #292 | Architecture alignment: Manual final architecture + ABN Settings bug fix + merge #252 | COMPLETE |
| Sprint 7 | #293 | Stage-parallel pipeline refactor (SEM_SPIDER=15, SEM_ABN=1, SEM_PAID=20, SEM_DM=20) | COMPLETE — PR #255 |
| Sprint 7 | #294 | Multi-category rotation (15 categories, 5/month, monthly wrap) + exclude_domains + category_stats | COMPLETE — PR #256 |
| Sprint 7 | #295 | httpx primary scraper + GMB rating fix + AU country filter + parallel worker orchestrator | COMPLETE — PR #257 |
| Sprint 8 | — | Final 100-DM test: multi-category, parallel, ABN working, full ProspectCards | Queued |
| Segments 4–8 | #296–#300 | Email waterfall, phone, social, message generation (Haiku), outreach scheduling | Queued |
| Launch | #301 | Founding customer onboarding, territory locking, demo mode | Queued |

### Completed Directives Log

| Directive | What | Status |
|-----------|------|--------|
| #271 | Signal config schema v6 (migration 029 + model + 6-service seed) | COMPLETE — PR #235 merged |
| #272 | Layer 2 discovery engine (5-source — now superseded by v7) | COMPLETE — PR #236 merged |
| #273 | Fix DFS SERP test failures | COMPLETE — PR #237 merged |
| #274 | Layer 3 bulk filter (now superseded by v7) | COMPLETE — PR #238 merged |
| #275 | asyncpg JSONB codec fix | COMPLETE — PR open (branch feat/275-asyncpg-jsonb-codec) |
| #277 | Codebase audit (92 components, all sections) | COMPLETE — docs/v7-audit-results.md |
| #278 | v7 architecture alignment (this directive) | COMPLETE |
| #283 | Sprint 3: Paid enrichment + affordability gate | COMPLETE — PR #246 merged |
| #284 | DFS date params fix (first_date/second_date) + DiscoverySource enum | COMPLETE — PR #247 merged |
| #285 | Free enrichment quality: ABN confidence, JSON-LD address, EmailMaturity enum, silent exception fix | COMPLETE — PR #248 merged |
| #286 | DM Identification: BrightDataLinkedInClient (brightdata_client.py) + DMIdentification pipeline (4-tier fallback T-DM1→T-DM3) | COMPLETE — PR #249 merged |
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
| #299 | Email discovery waterfall: 4 layers (HTML/pattern/Leadmagic/Bright Data), GLOBAL_SEM_LEADMAGIC=10, ProspectCard email fields, Stage 9 wired. 16 tests. | PR #261 — pending merge |

---

## SECTION 13 — COMPETITIVE INTELLIGENCE

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

## SECTION 14 — RESEARCH-1 STANDING BRIEF (updated Mar 26 2026)

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

## SECTION 15 — ICP + MARKET

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

## SECTION 16 — GOVERNANCE + OPERATIONS

Three-node chain: Claude (CEO) → Dave (Founder/Chairman) → Elliottbot (CTO)

PR merge authority: Dave merges all PRs. Elliottbot may merge only when explicitly instructed via Telegram.

**Three-store completion rule (mandatory on save-trigger directives):**
1. `docs/MANUAL.md` in repo (CEO SSOT — primary)
2. Supabase `ceo_memory` (directive counter, completion status, key state changes)
3. `cis_directive_metrics` (execution metrics for learning system)

Mirror: After writing `docs/MANUAL.md`, copy content to Google Doc (best effort). If Drive write fails, log error but do not block completion.

**Verification:** Every save-trigger directive must include `cat docs/MANUAL.md | grep "SECTION"` output proving the write landed. "All three stores written" without this output is rejected.

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

## SECTION 17 — OUTREACH + CONTENT (pre-launch)

Landing page (`agency_os_v5.html`) is built with Bloomberg aesthetic and "Who built yours?" hero. Pending: Remotion video hero, Stripe Checkout on pricing CTAs, live founding counter from Supabase. Video strategy: 5 versions (dashboard animation, Maya walkthrough, HeyGen avatar, customer-specific, results) built via Remotion + HeyGen (Maya avatar). Content distribution via Prefect Flow #28 (Claude API → Remotion → HeyGen → distribution APIs). Demo mode active via `?demo=true` URL param with seeded Supabase demo tenant. Onboarding starts with a 15-minute activation call (CRM + LinkedIn connect, watch dashboard populate live).

---

## SECTION 18 — DESIGN SYSTEM

- Pure Bloomberg palette: warm charcoal `#0C0A08` + amber `#D4956A` only
- Lucide icons throughout (all emoji replaced)
- Aggressive glassmorphism cards with light-catching edges
- Typography: Instrument Serif + DM Sans + JetBrains Mono
- Directive #027 pending execution for full implementation

---

## SECTION 19 — INFRASTRUCTURE + CREDENTIALS

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
- `abn_registry` — 2.9M ABR records
- 29 security advisor errors unresolved

GitHub: Keiracom/Agency_OS

Deployment: Railway (`LEADMAGIC_API_KEY` must be present in env)

Orchestration: Prefect (flow orchestration)

Compliance: SPAM Act 2003, DNCR registered, TCP Code (voice), Australian-built

---

## SECTION 20 — KNOWN ISSUES + BACKLOG

### v7 Architecture Risks (identified Mar 28 2026)

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Google Ads Transparency scraper fragility | HIGH | Google may change HTML structure. Monitor weekly. Build CSS selector abstraction to allow fast updates. |
| 5-domain sample size | HIGH | v7 validated on 5 AU dental domains. 78-domain audit found dead endpoints but scrape coverage not re-tested at scale. Run 100-domain test in Sprint 8. |
| Uncalibrated scoring | HIGH | All 5 scorers use v6 signal assumptions. v7 signals (scrape-based, Ads Transparency) not yet wired. Scores meaningless until Sprint 4. |
| domain_metrics_by_categories coverage gaps | MEDIUM | Returns organic-signal domains. New businesses with low organic = excluded. Supplement with Google Ads Advertisers endpoint for paid-only businesses. |
| Leadmagic plan unpurchased | HIGH | All Leadmagic calls in mock mode. Must purchase before Sprint 5 go-live. Dave action required. |
| ABN JOIN false negatives | MEDIUM | ~10% SQL match rate (vs 67% API). Sole traders often registered under personal name, not trading name. Supplement with ABN live API for unmatched rows. |
| GMB match rate 80% | MEDIUM | 4/5 (80%) proven at small scale. May degrade at scale for rural or less-established businesses. No hard dependency — GMB miss = continue without GMB signals. |
| category_codes hardcoded | MEDIUM | [13418,13420,13421] for marketing_agency only. Multi-vertical requires Sprint 7 seed migrations. No dynamic mapping from client services to DFS codes. |
| Deprecated v6 Layer 2/3 code still present | LOW | layer_2_discovery.py rebuilt (Sprint 1 COMPLETE). layer_3_bulk_filter.py still present — remove in Sprint 2. |
| Sender ABN in email footer unconfirmed | MEDIUM | email_signature_service.py signature exists. ABN inclusion in footer not confirmed. Verify before outreach goes live. |

### Infrastructure Issues
- Supabase: 29 security advisor errors unresolved
- BD LinkedIn account needs funding before social scraping (T-DM3/T-DM4) works
- PR #275 (asyncpg JSONB codec) still open — Dave to merge before any live pipeline test
- PR #221 (research-1 brief config) still open — awaiting Dave



## SECTION 21 — SEGMENT TESTING STRATEGY

Ratified: March 29, 2026

Pipeline validated in 8 sequential segments. Each
segment tested with 10 FRESH real AU domains before
next segment is built. Domains are NOT recycled
between segment tests.

SEGMENT 1 — DISCOVERY
Find domains. DFS domain_metrics_by_categories.
Components: layer_2_discovery.py (Sprint 1)
Status: CODE COMPLETE — ready for live test

SEGMENT 2 — BUSINESS INTELLIGENCE
Understand the business. Website scrape (Spider.cloud),
DNS/MX/SPF/DKIM, ABN registry JOIN, affordability
gate, DFS bulk metrics, DFS Maps GMB + reviews.
Components: free_enrichment.py (Sprint 2),
paid_enrichment.py (Sprint 3)
Status: CODE COMPLETE — ready for live test

SEGMENT 3 — DECISION MAKER IDENTIFICATION
Find the human. GMB name, ABN legal name, team page
URLs, review mentions, Brand SERP knowledge panel.
Components: not yet built (Sprint 5)
Status: BLOCKED — awaiting Segment 1+2 validation

SEGMENT 4 — EMAIL DISCOVERY (Directive #299 — COMPLETE)
4-layer waterfall wired into run_parallel Stage 9:
- L1: Website HTML mailto:/regex (free, name-matched)
- L2: Pattern generation + MX check (free)
- L3: Leadmagic /email-finder ($0.015, SMTP-verified)
- L4: Bright Data LinkedIn profile ($0.00075)
Short-circuits on first hit. ProspectCard fields: dm_email, dm_email_verified, dm_email_source, dm_email_confidence, email_cost_usd.
GLOBAL_SEM_LEADMAGIC = 10.
Status: BUILT — src/pipeline/email_waterfall.py, PR #261

SEGMENT 5 — PHONE DISCOVERY
Get mobile/direct number. GMB phone carrier check,
Voice AI landline-to-mobile, Leadmagic mobile-finder.
Components: not yet built (Sprint 5)
Status: BLOCKED — awaiting Segment 4 validation

SEGMENT 6 — SOCIAL DISCOVERY
Find LinkedIn profile. Bright Data + Unipile.
Components: partially wired
Status: BLOCKED — awaiting Segment 5 validation

SEGMENT 7 — SCORING + MESSAGE GENERATION
Rank and write outreach. 5 scoring engines + Haiku
message gen (4 channels).
Components: built but need v7 signal recalibration
(Sprint 4 + Sprint 6)
Status: BLOCKED — awaiting Segments 1-6 validation

SEGMENT 8 — OUTREACH EXECUTION
Send across channels. Salesforge email, Unipile
LinkedIn, ElevenAgents Voice AI, SMS (provider TBD).
Components: email + LinkedIn + voice built, SMS not
Status: BLOCKED — awaiting Segment 7 validation

RULE: Do NOT build next segment until prior segment
passes live test with 10 fresh domains.

CURRENT STATE: Segments 1+2 code complete, awaiting
live test. All other segments blocked.
