# Agency OS Manual

Last updated: 2026-03-26 21:55 UTC
Directive #271: Signal config schema v6 — migration 029 in progress
Next scheduled update: Directive #271 completion (PR merge)

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

- Last directive issued: #274 (Layer 3 Bulk Domain Filter — COMPLETE, PR #238 merged)
- Next directive: #275 (Layer 4 qualification)
- Test baseline: 1032 passed, 0 failed, 28 skipped
- Test baseline: 1009 passed, 2 failed (pre-existing DFS serp client tests), 28 skipped
- Last merged PRs: #233 (dedup + blocklist), #232 (bug fixes), #231 (live test v2), #230 (stages 6+7)
- Architecture: **v6 ratified Mar 27 2026** — spend + gaps + fit discovery (10-layer engine)
- **All 7 pipeline stages S1-S7 built and on main (v5 era). v6 rebuild starts at #271 — see Section 12**
- **Live Test v2 (#265–#266): PASS. Pipeline working end-to-end. First Haiku messages produced.**
- **Open bugs: BUG-268-1 (S1 unnest jsonb) + BUG-268-2 (BD GMB 401) — fix in v6 sprint**

---

## SECTION 3 — ARCHITECTURE v6 (ratified Mar 27 2026)

Core principle: Discovery by SPEND + GAPS + FIT. Industry and location are outputs of enrichment. Each agency's services map to specific DFS endpoint conditions that define what "perfect fit" looks like for their prospects. The pipeline runs ALL service checks and stacks the results. More matched gaps = higher propensity = bigger potential retainer.

---

### LAYER 1: AGENCY ONBOARDING

CRM connect → extract services sold, client history, deal sizes per service, industries won.
LinkedIn connect → communication style, connection exclusion list.
System builds Agency Profile automatically.
Signal config generated from their services — each service maps to DFS endpoint conditions.
Output: Agency Profile + Signal Config + Exclusion List

---

### LAYER 2: DISCOVERY (find businesses worth investigating)

Sources (run in parallel, dedup at BU write):

**a) Domain Metrics by Categories ($0.10)**
Input: Google Ads category codes for prospect industries. Filter: location_code=AU, paid_etv > configurable threshold.
Output: AU businesses with confirmed ad spend in target industries.

**b) Google Ads Search ($0.006/keyword)**
Input: industry-specific keywords ("dentist Sydney", "plumber Melbourne" etc).
Output: businesses actively bidding on those keywords RIGHT NOW. Real-time budget signal.

**c) Domains by HTML Terms ($0.01)**
Input: tech gap combinations (has Google Ads pixel but NOT conversion tracking, has WordPress but NOT Yoast, etc).
Output: businesses with specific provable gaps.

**d) Google Jobs ($0.006/keyword)**
Input: "marketing manager [city]" etc.
Output: businesses hiring = growth signal. A business hiring a $70k marketer should hear "for $2,500/month you get a team not one person."

**e) Competitors Domain (from prior month, $0.01)**
Input: top prospects from previous month.
Output: their SERP competitors. Network expansion — one good prospect generates 5-10 more.

All results deduped against BU + agency exclusion list.
Output: raw domains into BU, pipeline_stage = 1.

**Layer 2 implementation (Directive #272 — COMPLETE, PR #236):**
- Class: `src/pipeline/layer_2_discovery.py` → `Layer2Discovery`
- 5 sources run concurrently via asyncio.gather (source failure does not abort run)
- New DFS endpoints added to `dfs_labs_client.py`: `domain_metrics_by_categories`, `google_ads_advertisers`, `domains_by_html_terms`, `google_jobs_advertisers`
- Rate limiting: configurable `daily_budget_usd` (default $10.0) — stops when budget would be exceeded
- Idempotency: skips existing BU rows by domain/place_id
- Migration 030: adds `discovery_batch_id uuid`, `no_domain boolean`, `dfs_discovery_category text`, `dfs_discovery_keyword text`
- Cost per run: ~$0.47 (marketing_agency, all 5 sources) → expected 500–2,000 raw domains
- Note: uses DFS Labs/SERP endpoints per v6 spec — NOT DFS GMaps coordinate sweep (v4/v5 pattern)

---

### LAYER 3: CHEAP FILTER (kill junk before spending)

a) Bulk Domain Metrics ($0.001 per domain, 1000/call) — remove zero-traffic, zero-spend, dead domains.
b) Domain blocklist (platforms, government, etc).
c) AU verification (domain TLD or GMB confirms AU).

Output: surviving domains, pipeline_stage = 2.

**Layer 3 implementation (Directive #274 — COMPLETE, PR #238):**
- Class: `src/pipeline/layer_3_bulk_filter.py` → `Layer3BulkFilter`
- Endpoint 12 added to `dfs_labs_client.py`: `bulk_domain_metrics` (batch up to 1000 domains/call)
- Filter thresholds (configurable via enrichment_gates): REJECT if organic_etv=0 AND paid_etv=0 AND backlinks<5; PASS if organic_etv>0 OR paid_etv>0 OR backlinks≥10
- REJECT → pipeline_stage=-1, filter_reason='bulk_metrics_below_threshold'
- no_domain rows: advance to pipeline_stage=2 without API call (→ Layer 7 GMB path)
- Migration 031: adds filter_reason text, backlinks_count int, domain_rank int
- Pricing: $0.10/task + $0.001/domain = $1.10 per 1,000 domains (DFS confirmed). 1,500 domains = $2.20. 20× cheaper than individual domain_rank_overview ($0.02/domain)
- Cost for 1,500 domains: 2 batches

---

### LAYER 4: QUALIFICATION (is this business worth $0.15?)

Per domain, three calls:

**a) Domain Technologies ($0.01)**
Full tech stack. Identify gaps per agency service. "Not well-served" check: no agency tools (no HubSpot, no SEMrush, no marketing automation = nobody managing this for them).

**b) Domain Rank Overview ($0.02)**
Paid ETV = budget confirmation. Organic ETV = traffic baseline. Paid vs organic ratio: high paid + low organic = over-dependent on ads, spending badly. Keyword count + position distribution.

**c) Historical Rank Overview ($0.02)**
Traffic trajectory: declining = active pain NOW. Paid spend rising while organic falls = panicking, throwing money at ads to compensate. TIMING signal: recent pain, not chronic.

Output: budget + gap + pain signals populated, pipeline_stage = 3. Cost: $0.05/domain.

---

### LAYER 5: FIT SCORING (how many ways can the agency help?)

For each service the agency sells:
- Check: does this business have the matching problem? (from Layer 4 data)
- Check: is the gap provable? (specific data points)
- Score: 0-100 per service

Composite propensity = weighted sum across all matching services. Weight per service configurable (PPC weighted higher — confirmed budget).

Revenue estimate = sum of agency's average retainer per matched service (from CRM onboarding data).

Score reason in plain English: "SEO weak (page 2 for 30 keywords), running ads without conversion tracking, no CRM. Estimated retainer: $4,500/mo."

Gate: propensity >= threshold → proceed. Below threshold → stays in BU for future re-scoring.

Output: scored + revenue-estimated, pipeline_stage = 4.

---

### LAYER 6: COMPETITIVE INTELLIGENCE (deepen + expand)

Only for prospects passing Layer 5 gate:

**a) Competitors Domain ($0.01)**
Top 5 SERP competitors per prospect. Store top 3 for messaging: "competitor X ranks above you for Y." Feed competitor domains back to Layer 2 for network expansion in next round.

**b) Google Ads Advertisers ($0.006)** — top prospects only
Their ad strategy: keywords, ad copy, landing pages. Specific ammunition for messaging.

**c) On-Page Summary ($0.01)** — top prospects only
Technical SEO: load time, broken links, mobile, SSL. Specific provable problems.

**d) Backlinks Summary ($0.02)** — top prospects only
Authority gap vs competitors.

**e) Categories for Domain ($0.01)**
Industry confirmation. Cross-check with GMB.

Output: enriched with competitive + technical intelligence, pipeline_stage = 5.

---

### LAYER 7: GMB ENRICHMENT (physical identity)

Bright Data GMB lookup ($0.001/record): Place ID, category, rating, reviews, address, phone, hours. Suburb, state, postcode extracted. GMB rating declining = additional pain signal.

Output: physically located, pipeline_stage = 6.

---

### LAYER 8: DECISION MAKER DISCOVERY

Waterfall (cheapest first):
a) GMB contact extraction (free)
b) Leadmagic ($0.02) — name, title, email, phone, LinkedIn

Reachability validation: Email format, AU phone format, LinkedIn URL. Confirmed channels array. Reachability score from confirmed channels.

Output: DM found + channels confirmed, pipeline_stage = 7.

---

### LAYER 9: MESSAGE GENERATION (Haiku)

Inputs to Haiku:
- Agency Profile (voice, tone, case studies)
- ALL intelligence from Layers 4–7
- Best angle: lead with strongest gap matching agency's best case study
- Competitor data for pain amplification
- Revenue estimate for internal prioritisation

Per channel:
- Email: reference one signal, ask one question
- LinkedIn: shared context, 300 chars
- Voice: knowledge card for Alex
- SMS: direct, one line

Output: messages ready for approval, pipeline_stage = 8.

---

### LAYER 10: SCHEDULING

All prospects found at start of month. Outreach scheduled across 30 days respecting:
- Email daily send limits per inbox
- LinkedIn 20–25 connections/day, business hours, randomised delays
- Voice AI calling hours (TCP Code)
- SMS daily caps

Follow-up sequences timed per channel. Agency sees full schedule on day 1.

---

### QUOTA LOOP

Runs at start of month until tier target met:
1. Run Layers 2–9 (primary discovery)
2. Count outreach-ready prospects
3. If gap > 0:
   a) Re-score BU backlog near threshold ($0.05 each — re-run Layer 4 for fresh signals)
   b) Advance stuck rows through remaining layers
   c) Expand discovery: broader category codes, deeper pagination, competitor network expansion
   d) Cross-service discovery: lean into different service signals
   e) Retry DM discovery on prior failures
4. Loop until gap = 0 or strategies exhausted
5. If still short: deliver what we have + notify

---

### COST PER QUALIFIED PROSPECT (estimated)

| Layer | Cost |
|-------|------|
| Layer 2 Discovery | ~$0.10 (amortised across batch) |
| Layer 3 Cheap Filter | ~$0.001 |
| Layer 4 Qualification | ~$0.05 |
| Layer 5 Scoring | free |
| Layer 6 Competitive | ~$0.04 (average, not all get all endpoints) |
| Layer 7 GMB | ~$0.001 |
| Layer 8 DM | ~$0.02 |
| Layer 9 Haiku | ~$0.01 |
| **Total** | **~$0.27/prospect** |

Tier economics:
- Spark (150): ~$40 COGS → 95% margin at $750
- Ignition (600): ~$162 COGS → 94% margin at $2,500
- Velocity (1500): ~$405 COGS → 92% margin at $5,000

Network expansion from Layer 6 reduces Layer 2 cost each subsequent month. By month 3, competitor-sourced domains skip Layer 2 entirely → effective cost drops to ~$0.17/prospect.

---

### SIGNAL CONFIG SCHEMA (updated for v6)

`signal_configurations` table redesign (Directive #270):

```
services: jsonb array of:
  {
    service_name: "SEO",
    weight: 1.0,
    problem_signals: {
      ranked_keywords: {condition: "positions 11-30 count > 20"},
      historical_rank: {condition: "organic_etv declined > 20% in 90 days"},
      backlinks_summary: {condition: "referring_domains < 50"}
    },
    budget_signals: {
      domain_rank_overview: {condition: "paid_etv > 200"}
    },
    not_served_signals: {
      domain_technologies: {condition: "missing: [semrush, ahrefs, moz]"}
    }
  }

discovery_config: jsonb:
  {
    category_codes: [13418, ...],
    ad_spend_threshold: 200,
    keywords_for_ads_search: ["dentist Sydney", ...],
    html_gap_combos: [
      {has: "google-ads-pixel", missing: "gtag-conversion"},
      ...
    ],
    job_search_keywords: ["marketing manager", ...],
    competitor_expansion: true,
    max_competitors_per_prospect: 5
  }

enrichment_gates: jsonb:
  {
    min_score_to_qualify: 30,
    min_score_to_compete: 50,
    min_score_to_dm: 50,
    min_score_to_outreach: 65
  }

competitor_config: jsonb:
  {
    max_competitors_per_prospect: 5,
    min_competitor_organic_etv: 100,
    store_top_n_for_messaging: 3,
    feed_back_to_discovery: true
  }
```

Migration 029 (Directive #271): DROP old table → CREATE v6 schema (`vertical`, `services`, `discovery_config`, `enrichment_gates`, `competitor_config`, `channel_config`) → seed marketing_agency with 6 services (paid_ads, seo, social_media_marketing, web_design, marketing_automation, content_marketing). Python model updated (`src/enrichment/signal_config.py`). BUG-268-1 confirmed pre-fixed (stage_1_discovery.py already uses jsonb_array_elements_text). DFS v2 audit: PASS — all calls on /v3/.

---

### v5 IMPLEMENTATION NOTES (retained for reference — v5 era stages S1–S7)

v5 stages (S1–S7) are built and on main. They are the starting point for v6 rebuild. Key files:
- `src/pipeline/stage_1_discovery.py` — Stage1Discovery (DFS domains by technology)
- `src/pipeline/stage_2_gmb_lookup.py` — Stage2GMBLookup
- `src/pipeline/stage_3_dfs_profile.py` — Stage3DFSProfile
- `src/pipeline/stage_4_scoring.py` — Stage4Scorer
- `src/pipeline/stage_5_dm_waterfall.py` — Stage5DMWaterfall
- `src/pipeline/stage_6_reachability.py` — Stage6Reachability
- `src/pipeline/stage_7_haiku.py` — Stage7Haiku

Migrations applied: 022, 022b, 023, 024, 025, 026, 027, 028. Next: 029.

Two separate scores:
- Reachability (channel access, 100 pts)
- Propensity (fit + timing signals, service-aware, ICP-configured, 100 pts)

Dashboard shows priority rank + plain English reason only. No raw scores exposed. Algorithm is proprietary; no weight documentation in code comments.

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

## SECTION 8 — ENRICHMENT STACK (current)

| Tier | Provider | What | Cost | Status |
|------|----------|------|------|--------|
| T1 | ABN Supabase JOIN | ABN lookup (3.6M records) | Free | ✅ Live |
| T1.25 | ABR SearchByASIC | Trading name lookup | Free | ✅ Live |
| T1.5 | Bright Data LinkedIn | Company enrichment | $0.75/1k | ✅ Live |
| T-DM0 | DataForSEO | Ad spend detection | Variable | ✅ Live |
| T2 | Bright Data GMB | GMB discovery + enrichment | $0.001/record | ✅ Live — dataset `gd_m8ebnr0q2qlklc02fz` (Google Maps full information), keyword discovery mode: `type=discover_new&discover_by=keyword` |
| T3+T5 | Leadmagic | Email + mobile (Essential plan) | Variable | ✅ Live |
| DFS | DataForSEO Labs | 7 endpoints (PR #220) | Variable | ✅ Live |
| Jina | Jina AI Reader | Website scraping fallback | Free | ~~Live~~ Removed from S5 (#267) |
| BD Web | Bright Data Unlocker | Heavy scraping | Variable | ✅ Live |

Domain blocklist (`src/utils/domain_blocklist.py`) filters platform/social/government domains before BU insert. Blocklist checked in S1 before any INSERT. Covers: social platforms (facebook.com, instagram.com, etc.), search/tech giants (google.com, etc.), website builders, hosting/infra, and *.gov.au subdomains. Directive #267.

DEPRECATED — do not use: Hunter.io, Kaspr, Proxycurl, Apollo (enrichment), Clay (enrichment)

Deferred post-core pipeline:
- T-DM3: BD LinkedIn Profiles: `gd_lwxmeb2u1cniijd7t4`, Posts: `gd_lwxkxvnf1cynvib9co` ($0.0015/record). Gate: Propensity ≥70.
- T-DM4: Facebook business page posts via Bright Data ($0.00075–0.0015/post). Gate: Propensity ≥70.

Key data provider details:
- Bright Data Scrapers API key: `2bab0747-ede2-4437-9b6f-6a77e8f0ca3e`
- ABN Lookup Web Services GUID: `d894987c-8df1-4daa-a527-04208c677c0b`
- BD LinkedIn needs funding before social scraping works

T1 is a local JOIN, not an API call. Never describe it as external.
Siege Waterfall is proprietary. Never describe it as a vendor.

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

v5 era (#247–#270): all 7 pipeline stages built, tested, and live on main. Superseded by v6.

### v6 Build Sequence (active — starts #271)

| Directive | What | Status |
|-----------|------|--------|
| #271 | Signal config schema redesign (services + competitor_config + discovery_config) | Next |
| #272 | Layer 2 discovery engine (multi-source: Categories, Ads Search, HTML Terms, Jobs, Competitors) | COMPLETE — PR #236 merged |
| #273 | Fix pre-existing DFS SERP test failures | COMPLETE — PR #237 merged |
| #274 | Layer 3 cheap filter + Bulk Domain Metrics client | COMPLETE — PR #238 merged |
| #274 | Layer 4 qualification (Domain Technologies + Rank Overview + Historical Rank) | Queued |
| #275 | Layer 5 fit scoring (multi-service, per-service problem/budget/gap scoring) | Queued |
| #276 | Layer 6 competitive intelligence (5 endpoints, top-prospect gating) | Queued |
| #277 | Layer 7–8 (GMB enrichment + DM waterfall — mostly reuse from v5) | Queued |
| #278 | Layer 9 message generation (Haiku redesign with Agency Profile + competitive data) | Queued |
| #279 | Layer 10 scheduling engine | Queued |
| #280 | Quota loop | Queued |
| #281 | Full pipeline live test v3 | Queued |
| #282 | Prefect wiring | Queued |

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

- Supabase: 29 security advisor errors need resolution
- BD LinkedIn account needs funding before social scraping (T-DM3/T-DM4) works
- ARCHITECTURE.md Section 5 needs T-DM3 corrected endpoints + price ($0.0015, not $0.0025)
- Remotion video + Stripe checkout pending for landing page
- S7 prompt engineering needed (backlog — deferred post-#281)
- S2 parallelisation needed (production speed — currently sequential)
- BUG-268-1: CONFIRMED PRE-FIXED — stage_1_discovery.py already uses jsonb_array_elements_text() (no action needed)
- BUG-268-2: BD GMB returning 401 on new-domain discovery requests — credentials issue in BD account (Dave to check dashboard)

### Directive Log
| Directive | What | Status |
|-----------|------|--------|
| #271 | Signal config schema v6 (migration 029 + model + 6-service seed) | COMPLETE — PR #235 open |


