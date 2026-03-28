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

- Last directive issued: #281 (Sprint 2 Prep: Schema + Audit — COMPLETE)
- Next directive: #282 (Sprint 2 — Free Intelligence Sweep Implementation)
- Test baseline: 990 passed, 0 failed, 28 skipped (+4 from #281)
- Last merged PR: #242 (Sprint 1 — Discovery Engine v7); PRs open: #243 (schema), #244 (tests)
- Architecture: **v7 ratified Mar 28 2026** — signal-first organic discovery, free intelligence sweep, proven with live AU data across 5 dental domains
- **v6 pipeline SUPERSEDED. Layer 2 (5-source parallel) and Layer 3 (bulk filter) replaced. Layer 4 (DFS tech/rank/historical) replaced with free scrape stack.**
- **Live testing confirmed: domain_metrics_by_categories returns 22,592 AU dental domains at $0.001/domain. Google Ads Transparency free scraper: 5/5 AU coverage. Website scraping direct HTTP: 5/5 coverage, full tech stack, FREE.**

---

## SECTION 3 — ARCHITECTURE v7 (ratified Mar 28 2026)

Core principle: Signal-first organic discovery. Find businesses spending on Google Ads in target industries. Sweep them for free. Score against agency services. Only spend money at DM stage.

**PROVEN WITH LIVE AU DATA (5-domain dental sample, Mar 2026)**

---

### DEAD ENDPOINTS (do not use in v7)

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
| DFS domain_metrics_by_categories | 22,592 AU dental domains returned | $0.001/domain | Organic ETV, keyword count, category confirmation |
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

Cost: $0.001/domain
Sprint: Sprint 1

**Status: BUILT (v7)** — single `domain_metrics_by_categories` call, sequential per category, AU domain filter, trajectory computation, Gate 1 applied post-insert. Directive #280, PR #242.

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

Waterfall (cheapest first):
a) Website scrape contact extraction (free — from Layer 3 data)
b) GMB phone/contact (free — from Layer 4 data)
c) Leadmagic employee-finder ($0.05/domain) → name, title, LinkedIn
d) Leadmagic email-finder ($0.015) → verified email
e) Leadmagic mobile-finder ($0.077) → AU mobile
f) ZeroBounce verification ($0.005) → catch-all/invalid filter

Cost: ~$0.05-$0.15/domain depending on waterfall depth
Sprint: Sprint 5

---

### GATE 6: Reachability Gate

PASS if: at least one confirmed channel (email OR LinkedIn OR phone)
REJECT to BU backlog if no contact found

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

## SECTION 8 — ENRICHMENT STACK (v7 — updated Mar 28 2026)

### FREE TIER (v7 foundation)

| Source | What | Cost | Status |
|--------|------|------|--------|
| ABN registry local JOIN | GST status (confirms $75k+ revenue), entity type, registration date | FREE | ✅ Live — 2,418,836 rows |
| Website scrape (direct HTTP) | Tech stack, CMS, tracking codes (GA4, GTM, FB Pixel, Google Ads), team names, contact info | FREE | ✅ Proven (5/5 AU coverage) |
| Google Ads Transparency Center | Binary: is business running Google Ads | FREE | ✅ Proven (5/5 AU coverage) — Python scraper, monitor for HTML changes |
| DNS + TLS check | MX record, SPF/DKIM, TLS cert (hosting signal) | FREE | Planned Sprint 2 |
| Phone carrier lookup | AU mobile carrier validation | FREE | Planned Sprint 2 |

### PAID TIER

| Source | What | Cost | Status |
|--------|------|------|--------|
| DFS domain_metrics_by_categories | Domain discovery by AU industry category. Returns organic_etv, organic_keywords, category | $0.001/domain | ✅ Proven (22,592 AU dental domains) |
| DFS SERP Google Maps | GMB: Place ID, category, rating, reviews, address, phone, hours | $0.0035/domain | ✅ Live — 4/5 AU GMB match proven |
| DFS Competitors Domain | Top 5 SERP competitors per prospect | $0.01/call | ✅ Live |
| DFS Brand SERP / Indexed Pages | Brand search presence, indexed page count | $0.005/call | Planned Sprint 3 |
| DFS Google Ads Advertisers | Keywords actively bid on (complements Transparency binary) | $0.006/call | ✅ Live in layer_2_discovery.py |
| Bright Data GMB Dataset | GMB deep enrichment (claimed status, full hours, photos) | $0.001/record | ✅ Live — dataset `gd_m8ebnr0q2qlklc02fz` |
| Bright Data LinkedIn Company | Company headcount, industry, LinkedIn URL | $0.025/record | ✅ Live |
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
| Sprint 2 | #281–#282 | Free intelligence sweep: website scraper (direct HTTP), Google Ads Transparency Center (Python scraper), DNS+TLS check, phone carrier lookup | Queued |
| Sprint 3 | #283–#284 | Paid enrichment: Brand SERP, Indexed Pages, Competitors expansion, GMB full enrichment, Reviews sentiment | Queued |
| Sprint 4 | #285 | Scoring redesign: align all 5 scorers to v7 signals (remove dead DFS signals, add scrape signals, add Ads Transparency) | Queued |
| Sprint 5 | #286–#287 | DM discovery: email waterfall (scrape→Leadmagic→ZeroBounce), mobile waterfall, reachability v7 | Queued |
| Sprint 6 | #288–#289 | Message generation + outreach wiring: Haiku redesign with v7 signal inputs, scheduling engine, quota loop | Queued |
| Sprint 7 | #290 | Multi-vertical: seed dental, recruitment, IT MSP signal configs + category codes | Queued (parallel with 4–6) |
| Sprint 8 | #291 | Integration test + hardening: live pipeline test against 100 real domains, cost/quality audit | Queued |
| Sprint 9 | #292 | Founding customer prep: onboarding wizard, approval flow, territory locking, demo mode | Queued |
| Sprint 10 | #293 | Launch | Queued |

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


