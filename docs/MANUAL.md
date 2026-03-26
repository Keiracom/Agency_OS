# Agency OS Manual

Last updated: 2026-03-25 23:53 UTC
Restored by: Manual Restoration Directive, Mar 26 2026
Next scheduled update: Directive #256 completion (signal config schema)

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

- Last directive issued: #264 (Stage 6 + Stage 7 — reachability validation + Haiku message gen)
- Next directive: TBD
- Test baseline: 987 passed, 2 failed (pre-existing DFS serp client tests), 28 skipped
- Last merged PRs: #219 (live test fixes), #220 (DFS Labs client)
- Architecture: v5 ratified Mar 26 2026 — signal-first discovery
- **All 7 pipeline stages S1-S7 are built and tested as of March 26 2026**

---

## SECTION 3 — ARCHITECTURE v5 (ratified Mar 26 2026)

Core principle: Discovery is by SERVICE THE AGENCY SELLS, not by industry or location. Industry and location are OUTPUTS of enrichment, not inputs. A marketing agency selling SEO services triggers a signal config that looks for businesses running WordPress without SEO tools.

8-stage pipeline — DFS-signal-first:

| Stage | What | Source | Cost |
|-------|------|--------|------|
| S1 | DFS Domains by Technology | DataForSEO | ~$0.01/domain |
| S2 | GMB reverse lookup | Bright Data GMB | $0.001/record |
| S3 | DFS Rank + Technology profile | DataForSEO | $0.02/business |
| S4 | Score (budget/pain/gap/fit) | Internal scoring | Free |
| S5 | Decision-maker waterfall | Leadmagic | Variable |
| S6 | Reachability check | Internal | Free |
| S7 | Haiku message generation | Claude Haiku | ~$0.01/prospect |

All-in COGS: ~$0.49 USD ($0.76 AUD) per prospect.

**S1 Implementation (built #259):** `src/pipeline/stage_1_discovery.py` — `Stage1Discovery` class. Reads `signal_configurations` for vertical → extracts `all_dfs_technologies` → paginates `DFS.domains_by_technology()` per tech → deduplicates by domain → inserts/updates BU with `pipeline_stage=1`. Handles pagination (each page = $0.015). Delay configurable between techs (default 0.5s).

**S2 Implementation (built #260):** `src/pipeline/stage_2_gmb_lookup.py` — `Stage2GMBLookup` class. Lookup strategy: domain → business name (via `src/utils/domain_parser.py`) → Bright Data GMB search (`src/clients/bright_data_gmb_client.py`). Writes gmb_place_id, category, rating, review_count, work_hours, address fields, address_source='gmb' to BU. Progresses all rows to pipeline_stage=2 regardless of GMB match. Cost: $0.001/record. New column: `address_source TEXT` (migration 024).

**S3 Implementation (built #261):** `src/pipeline/stage_3_dfs_profile.py` — `Stage3DFSProfile` class. Calls `DFS.domain_rank_overview` + `DFS.domain_technologies` concurrently per domain. Field mapping: rank → dfs_organic_etv/keywords/pos_*, tech → tech_stack/categories/depth. Calculates tech_gaps (signal technologies NOT in domain's detected stack — key input for S4 gap scoring). pipeline_stage=3 on all processed rows. Cost: ~$0.03/business. Note: dfs_domain_rank and dfs_backlinks_count dropped (DFS rank endpoint does not return scalar rank; digital maturity signals = dfs_organic_etv + dfs_organic_keywords).

**S4 Implementation (built #262):** `src/pipeline/stage_4_scoring.py` — `Stage4Scorer` class. Scores per service signal; best match stored as `best_match_service` (S7 uses this to select outreach angle). Four dimensions: budget (digital spend signals), pain (reputation + gap signals), gap (service-specific tech gaps), fit (category + stack alignment). Reachability scored on confirmed channel access; recalculated after S5/S6. Gate: `min_score_to_enrich` from `signal_configurations` (default 30). All businesses progress to pipeline_stage=4 — low scorers filtered by `WHERE propensity_score < threshold` in downstream queries. New migration: `025_scoring_columns.sql` (score_reason, best_match_service, linkedin_company_url, scored_at).

**S5 Implementation (built #263):** `src/pipeline/stage_5_dm_waterfall.py` — `Stage5DMWaterfall` class. Gate: `min_score_to_dm` (default 50) from `signal_configurations`. Waterfall order (cheapest first): `GMBContactExtractor` (free, BU data) → `WebsiteContactScraper` (free, Jina AI) → `LeadmagicPersonFinder` (paid, ~$0.015/email). Protocol-based: adding BD LinkedIn = adding one class to sources list. Stops at first valid result (name + contact method). Recalculates `reachability_score` after DM found. All rows progress to pipeline_stage=5; rows with no DM get `dm_source='none'` (S7 generates company-level outreach). New columns: `dm_phone`, `dm_found_at` (migration 026).

**S6 Implementation (built #264):** `src/pipeline/stage_6_reachability.py` — `Stage6Reachability` class. Validates dm_email (format check), dm_phone (AU pattern), dm_linkedin_url (LinkedIn profile URL pattern), physical address. Determines `outreach_channels` (text[]) from validated channels filtered by `channel_config`. Recalculates `reachability_score` from confirmed channels. All rows progress to pipeline_stage=6. New columns: `outreach_channels TEXT[]`, `outreach_messages JSONB` (migration 027).

**S7 Implementation (built #264):** `src/pipeline/stage_7_haiku.py` — `Stage7Haiku` class. Gate: `min_score_to_outreach=65`. Generates channel-specific messages (email: 3-line cold email <100 words; linkedin: <300 char connection note; voice: structured knowledge card JSON; sms: 1 sentence). Model: `claude-haiku-4-5-20251001`. Messages stored in `outreach_messages JSONB` on BU. All rows progress to pipeline_stage=7. No campaign dependency — operates directly on BU.

**KEY PRINCIPLE:** Expensive enrichment (S3 at $0.02/biz) runs ONLY on businesses surviving S1–S2 filters. Cheap discovery first, expensive intelligence second. NEVER run DFS Rank on 4,000 businesses when only 600 survive the filters.

BD LinkedIn reinstated for social scraping ($0.0015/record) — deferred post-core pipeline build.

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
| Jina | Jina AI Reader | Website scraping fallback | Free | ✅ Live |
| BD Web | Bright Data Unlocker | Heavy scraping | Variable | ✅ Live |

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

## SECTION 9 — DFS GMAPS OPERATIONAL RULES (confirmed Mar 25 2026)

- depth=100 same cost as depth=20 ($0.002 per request)
- Suburb names FAIL (error 40501) — must use coordinates: `location_coordinate="-33.89,151.27,14z"`
- 14z = optimal zoom level
- place_id in every result — use for dedup
- $50 USD/day spending cap = 25,000 queries/day — not a blocker
- Full Sydney one category = $1.24 (620 suburbs)
- Elkfox CSV for AU suburb → lat/lng mapping (free, MIT licensed)

**DFS Labs API Critical Gotchas (from #254):**
1. Field name `technologies` NOT `technology_paths` (domains_by_technology)
2. domain_rank_overview result at `result[0].items[0]` NOT `result[0]`
3. historical_rank $0.106/call — gate behind propensity, NEVER batch
4. keywords_for_site has NO order_by — filters only
5. Redirected domains fail — use canonical `www.domain.com`
6. AU location_code = 2036
7. domain_metrics_by_categories 40501 with location_code — retry with location_name
8. BD LinkedIn `gd_lwxmeb2u1cniijd7t4` profiles + `gd_lwxkxvnf1cynvib9co` posts — $0.0015/record

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

Outreach sequence per prospect:
- Day 1: Email (personalised, references specific signals)
- Day 3: LinkedIn (connection + note, different angle)
- Day 6: Email follow-up (new angle, deeper signal ref)
- Day 8: Voice AI (TCP compliant, 4–5PM timing)
- Day 12: SMS (final touch, case study link)
- Conditional triggers between steps (if no reply). Re-engagement at 90 days.

---

## SECTION 11 — BUSINESS UNIVERSE

- BU is THE PRODUCT — one row per discovered business, all intelligence accumulates over time
- abn_registry = renamed 2.9M ABR table, enrichment source only (not the BU itself)
- campaign_leads junction table for agency claims on prospects
- ABR match bonus: ~10% SQL match, ~67% API match
- 468 leads + 429 lead_pool = historical test data, archived
- CIS tables all 0 rows (not yet populated)
- BU House Seed strategy: 10% of campaign volume, gap-fill by default, steerable toward institutional buyer industries when deal in pipeline — must be disclosed to customers with incentive

**New DFS intelligence columns (added #257, total BU columns: ~97):**

S1 Discovery:
- `dfs_technologies` jsonb — raw tech array from DFS domains_by_technology
- `dfs_discovery_sources` text[] — all sources that found this business
- `dfs_technology_detected_at` timestamptz

S3 DFS Rank Overview:
- `dfs_organic_etv` numeric — estimated organic traffic value (USD)
- `dfs_paid_etv` numeric — estimated paid traffic cost (USD) — THE BUDGET SIGNAL
- `dfs_organic_keywords` integer
- `dfs_paid_keywords` integer
- `dfs_organic_pos_1/2_3/4_10/11_20` integer — position distribution
- `dfs_rank_fetched_at` timestamptz

S3 DFS Domain Technologies:
- `tech_stack` text[] — flat deduplicated technology list
- `tech_categories` jsonb — nested dict by category
- `tech_stack_depth` integer — count of unique technologies
- `tech_gaps` text[] — must_not_have_tech items absent (computed)
- `dfs_tech_fetched_at` timestamptz

S4 Scoring (v5 budget/pain/gap/fit):
- `score_budget` integer (0-30)
- `score_pain` integer (0-30)
- `score_gap` integer (0-25)
- `score_fit` integer (0-15)
- (composite `propensity_score` + `reachability_score` retained from v4)

Meta:
- `pipeline_updated_at` timestamptz
- `enrichment_cost_usd` numeric (complements existing `enrichment_cost_aud`)

---

## SECTION 12 — BUILD SEQUENCE (active)

| Directive | What | Status |
|-----------|------|--------|
| #256 | Signal config schema + seed marketing_agency | IN PROGRESS |
| #257 | BU migration (add ~15 DFS intelligence columns) | Queued |
| #258 | Stage 1 redesign (3-source discovery) | Queued |
| #259 | Stage 1 DFS signal-first discovery | COMPLETE |
| #260 | Stage 2 new (marketing intelligence) | COMPLETE |
| #261 | Stage 3 DFS rank + technology profile (Stage3DFSProfile) | COMPLETE |
| #262 | Stage 4 scoring redesign (budget/pain/gap/fit) | COMPLETE |
| #263 | Stage 5 DM Waterfall (Stage5DMWaterfall) | COMPLETE |
| #264 | Stage 6 Reachability + Stage 7 Haiku message gen | COMPLETE — ALL STAGES S1-S7 BUILT |

Previously completed in current sprint:
- #247: Schema migration (BU fresh + abn_registry + junction tables) ✅
- #248: DFS GMaps client ✅
- #249: Pipeline Stages 1-2 ✅
- #250: Stages 3-4 ✅
- #251: Stages 5-6 ✅
- #252: Stage 7 + CampaignClaimer ✅
- #253: Live test v1 (dentists, 9 production bugs found + fixed) ✅
- #254: DFS API deep dive research ✅
- #255: DFS Labs client (7 endpoints, 17 tests) ✅

Note: #247–#252 were built against v4 architecture. #258–#263 rebuild them against v5.

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

Landing page: v5 built (`agency_os_v5.html`). Bloomberg aesthetic. "Who built yours?" hero headline.
- PENDING: Remotion video embedded as hero
- PENDING: Stripe Checkout wired to pricing CTAs
- PENDING: Live founding counter from Supabase (not hardcoded)

Video plan (5 versions):
- V1: Pure dashboard animation, looping, 30sec (website hero)
- V2: Maya in-dashboard walkthrough, 60–90sec (product demo)
- V3: Maya as HeyGen avatar presenter, 60sec (LinkedIn/social)
- V4: Customer-specific with industry variables, 30–60sec (outbound)
- V5: Results/case study, 60sec (post-launch social proof)

Tech: Remotion (React video renderer) + HeyGen (Maya avatar, ~$59/mo Creator plan)

Content pipeline: Prefect Flow #28 — Claude API → Remotion → HeyGen → Distribution APIs → Notify Dave.

Demo mode: Built into dashboard via `?demo=true` URL param. Seeded demo data in Supabase demo tenant.

Setup call: 15-minute activation call (not sales, not demo). Connect CRM + LinkedIn, watch dashboard populate live.

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
- Current leads table contains denormalised copies — contradicts ratified BU architecture, needs fixing
- ARCHITECTURE.md Section 5 needs T-DM3 corrected endpoints + price ($0.0015, not $0.0025)
- Remotion video + Stripe checkout pending for landing page
- Design system directive #027 not yet executed
- Facebook as discovery source 3: REJECTED (do not revisit)
- `test_dfs_serp_client.py` has pre-existing collection error (Pydantic v2 deprecation)
- `test_campaign_claimer.py` 5 failures: AsyncMock + `conn.transaction()` mock setup bug (pre-existing from #252)
- `test_dfs_gmaps_client.py` 2 failures: `gmb_work_hours` type mismatch + `fetch_task_results` attribute (pre-existing from #248)
- Google Drive Manual was stale at #168 — restored by Manual Restoration Directive (Mar 26 2026)
