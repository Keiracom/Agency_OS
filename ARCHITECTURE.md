# ARCHITECTURE.md
# Agency OS — Locked System Architecture
# Ratified: March 17 2026 | Authority: CEO (Claude)
# DO NOT MODIFY without an explicit CEO directive that
# names this file and specifies the exact change.
#
# Elliottbot — this is the first thing you read.
# Every session. No exceptions.
# If this file is missing: stop, report to Dave,
# do not recreate it, do not proceed.

---

## RULE ZERO

Before writing any code that calls an external service:
1. Check SECTION 3 (DEPRECATED VENDORS) in this file
2. If the service is listed there — stop. Do not call it.
   Report to CEO immediately.
3. Check SECTION 4 (LIVE VENDORS) for the correct service,
   endpoint, env var, and cost for the tier you are building.

---

## SECTION 1 — WHAT IS SIEGE WATERFALL

Siege Waterfall is Agency OS proprietary orchestration
logic. It is NOT a vendor. It is NOT a service you call.
It is OUR CODE.

Siege Waterfall is the orchestration layer that:
- Decides which vendor to call, in what order
- Runs tiers in parallel where dependencies allow
- Applies fallback rules when a tier returns no data
- Validates enrichment output against confidence thresholds
- Tracks cost per lead across tiers
- Gates expensive tiers behind score thresholds

The vendors Siege Waterfall calls are in SECTION 4.
The orchestration logic lives in:
  src/integrations/siege_waterfall.py
  src/engines/scout.py

Siege Waterfall is never deprecated. It is our core IP.
Vendors inside it are replaced. The orchestrator improves.

---

## SECTION 2 — SYSTEM ARCHITECTURE OVERVIEW

### FLOW A — Synchronous discovery (target under 6 minutes)
1. Verify ICP (2s)
2. Generate campaign name — Claude Haiku (11s)
3. Create draft campaign (1s)
4. GMB discovery — Bright Data batched (4 min, 400+ records)
   Captures all 14 fields including open_website → domain
5. Bulk insert to lead_pool (2s)
6. business_universe ABN match — local Supabase JOIN (2s)
   NOT an API call. Query our own DB. Free and instant.
   Known issue: 0% match rate due to name format mismatch
   (e.g. "Acme Digital" vs "ACME DIGITAL PTY LTD").
   Fuzzy/trigram matching needed — tracked separately.
7. Bulk assign to campaign (2s)
8. Bulk promote to leads with all GMB fields intact (2s)
9. Activate campaign (1s)
10. Fire Flow B (async, fire and forget)

### FLOW B — Async enrichment (target under 10 minutes)
batch_size: 500 (not 100)
No Clay budget cap. CLAY_MAX_PERCENTAGE is dead.

Parallel architecture — fire simultaneously per lead:
  GROUP A (all have domain from GMB, no dependencies):
    T1 — business_universe JOIN (local, free)
    T1.25 — ABR SearchByASIC (trading name, free)
    T1.5 — Bright Data LinkedIn Company
    T2 — Bright Data GMB (full fields if not from T0)
    T3 — Leadmagic email
    T-DM0 — DataForSEO ad spend + DM discovery
    All six fire via asyncio.gather() simultaneously.

  THEN (depends on T1.5 LinkedIn company URL):
    Stage 2 — Person discovery

  THEN (depends on Stage 2 person data):
    Stage 2.5 — Social presence (gated Propensity ≥70)
    T5 — Leadmagic mobile (gated Propensity ≥85)

  THEN:
    ALS Scoring (local, instant)

---

## SECTION 3 — DEPRECATED VENDORS

These must never appear as active code paths.
If found in code you are about to write or run: stop.
Report to CEO before continuing.

| Vendor      | Was used for       | Replaced by            |
|-------------|---------------------|------------------------|
| Clay        | Person enrichment   | Removed — not needed   |
| Hunter.io   | Email finding       | Leadmagic (T3)         |
| Kaspr       | Mobile finding      | Leadmagic (T5)         |
| Proxycurl   | LinkedIn data       | Bright Data            |
| Apollo      | Contact database    | Bright Data + BU JOIN  |
| Apify       | Web scraping        | Bright Data            |
| Webshare    | Proxy rotation      | Bright Data            |
| SERP API    | Search results      | DataForSEO             |
| Direct mail | Outreach channel    | Removed permanently    |
| ZeroBounce  | Email validation    | Parked — do not build  |

---

## SECTION 4 — LIVE VENDORS

These are the only external services called in production.

| Vendor                | Purpose                 | Env var               |
|-----------------------|-------------------------|-----------------------|
| Bright Data           | GMB, LinkedIn, scrape   | BRIGHTDATA_API_KEY    |
| ABR (data.gov.au)     | ABN + trading name      | ABN_LOOKUP_GUID       |
| Leadmagic             | Email + mobile          | LEADMAGIC_API_KEY     |
| DataForSEO            | Ad spend + DM signals   | DATAFORSEO_LOGIN      |
|                       |                         | DATAFORSEO_PASSWORD   |
| Jina AI Reader        | Web scrape (free)       | None required         |
| Anthropic API         | Claude Haiku            | ANTHROPIC_API_KEY     |
| Salesforge            | Email outreach          | Verify with Dave      |
| Unipile               | LinkedIn outreach       | Verify with Dave      |
| ElevenAgents          | Voice AI (Alex)         | Verify with Dave      |
| Telnyx                | SMS outreach            | On hold until launch  |

Note: business_universe is a Supabase table we own.
T1 ABN lookup is a local JOIN — not an external API call.

---

## SECTION 5 — ENRICHMENT TIERS (COMPLETE SPEC)

### GMB Discovery fields (all 14 must be captured and
### promoted to leads table intact)
company_name, phone_number, company_website (open_website),
company_domain (derived), address, city, state (parsed),
company_country (AU), gmb_category, gmb_rating,
gmb_review_count, gmb_place_id, gmb_cid, latitude, longitude

---

### STAGE 1 — Company enrichment (parallel)

T1: business_universe JOIN
  Source: Supabase table (3.6M ABN records, already loaded)
  Method: local JOIN on company_name or domain
  Cost: FREE — no API call
  Returns: ABN, legal_name, trading_name, entity_type,
           state, postcode
  Known issue: 0% match rate — name format mismatch.
  Fix tracked separately. Do not block on this.

T1.25: ABR SearchByASIC
  Source: abr.business.gov.au SearchByASIC endpoint
  Env var: ABN_LOOKUP_GUID
  Cost: FREE
  Returns: trading_name, GST status, entity type,
           registered business names
  Purpose: resolves trading name from legal entity.
           Critical for GMB name matching.

T1.5: Bright Data LinkedIn Company
  Env var: BRIGHTDATA_API_KEY
  API key: 2bab0747-ede2-4437-9b6f-6a77e8f0ca3e
  GUID: d894987c-8df1-4daa-a527-04208c677c0b
  Cost: $0.0025 per record ($0.75 per 1,000)
  Bulk: 500 URLs per job
  Returns: company LinkedIn URL, employee count,
           industry, company posts (T-DM2b, free)

T2: Bright Data GMB full scrape
  Dataset: gd_m8ebnr0q2qlklc02fz
  Env var: BRIGHTDATA_API_KEY
  Cost: $0.001 per record
  Gate: skip if all 14 fields already captured at T0
  Returns: full GMB fields if T0 was incomplete

T2.5: Bright Data GMB Reviews
  Dataset: gd_luzfs1dn2oa0teb81
  Env var: BRIGHTDATA_API_KEY
  URL transform: !4m8!3m7+!9m1!1b1+?entry=ttu
  Cost: $0.001 per record
  Gate: Propensity >= 75 AND gmb_place_id present
  Returns: full review text, reviewer details
  Purpose: portfolio intelligence (reveals agency client
           names from review authors) + reputation signals

T3: Leadmagic email
  Env var: LEADMAGIC_API_KEY
  Cost: $0.015 per record
  Returns: verified work email + confidence score
  Replaces: Hunter.io (DEPRECATED — never reference)

T-DM0: DataForSEO
  Env var: DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD
  Cost: $0.0045 per record
  Gate: all leads regardless of score
  Returns: DM name, title, LinkedIn URL, ad spend
           detected, job listings, SEO rankings,
           site traffic signals

---

### STAGE 2 — Person discovery
Requires: LinkedIn company URL from T1.5.
If T1.5 returns no company URL: Stage 2 skips entirely.

T-DM1: Bright Data LinkedIn DM Profile
  Env var: BRIGHTDATA_API_KEY
  Cost: $0.0015 per record
  Returns: full DM profile, seniority, tenure,
           connection count, confirms authority
  Title priority: Owner → Founder → Director → CEO → MD

---

### STAGE 2.5 — Social presence (gated, person level)
Requires: person LinkedIn URL from Stage 2.
Gate: Propensity >= 70 for all tiers in this stage.
Purpose: feeds ALS propensity scoring AND message
         personalisation. A message referencing what
         the DM posted last week is not cold outreach.

T-DM2: Bright Data LinkedIn DM Posts (90 days)
  Env var: BRIGHTDATA_API_KEY
  Cost: $0.0015 per record
  Returns: DM personal posts, engagement, topics
  Purpose: hook selection for outreach opener

T-DM2b: Company LinkedIn posts
  Cost: FREE — comes from T1.5 updates field
  No additional API call required
  Returns: company announcements, activity signals

T-DM3: Bright Data X (Twitter) Profiles API
  Env var: BRIGHTDATA_API_KEY
  Cost: $0.0025 per record
  Gate: Propensity >= 70
  Returns: DM + company X posts (90d), engagement
  Validation: 4-criterion layer rejects false positives

T-DM4: Bright Data Facebook page posts
  Env var: BRIGHTDATA_API_KEY
  Cost: $0.00075 to $0.0015 per post
  Gate: Propensity >= 70
  Returns: post content, date, engagement, hashtags
  Purpose: authentic local business voice signal

---

### STAGE 3 — Person enrichment
Requires: first_name + last_name + domain from Stage 2.
If Stage 2 returns no person: Stage 3 skips entirely.

T5: Leadmagic mobile
  Env var: LEADMAGIC_API_KEY
  Cost: $0.077 per record
  Gate: Reachability gap present AND Propensity >= 85
  Returns: verified direct mobile number
  Replaces: Kaspr (DEPRECATED — never reference)

---

### SCRAPER WATERFALL (for JS-heavy sites outside GMB)
Tier 2 — Jina AI Reader
  Endpoint: r.jina.ai/[target-url]
  Cost: FREE — always try first

Tier 3 — Bright Data Web Unlocker
  Env var: BRIGHTDATA_API_KEY
  Cost: pay per use — only if Jina fails

---

## SECTION 6 — ALS SCORING (PROPRIETARY)

Two separate scores. Never expose weights or raw scores
to agency customers. Dashboard shows priority rank and
plain English reason only. Weights are never documented
in code comments. This is our core IP.

REACHABILITY (100 points max)
Measures channel access — can we reach this lead?
  email confirmed: 40 points
  LinkedIn DM confirmed: 30 points
  mobile confirmed: 20 points
  LinkedIn URL only: 10 points

PROPENSITY (100 points max)
Measures fit and timing — should we contact them now?
Service-aware. ICP-configured per agency at onboarding.
Fed by: GMB signals, DataForSEO ad spend, T-DM2/2b/3/4
social posts, review trends, hiring activity, ABN age.
Weights: proprietary — never documented in code.

CIS — Conversion Intelligence System
Learns from campaign outcomes over time.
Scores improve as results feed back into the model.
Schema required before launch.

Gate thresholds:
  T2.5 GMB Reviews: Propensity >= 75
  T-DM2/2b/3/4 Social: Propensity >= 70
  T5 Mobile: Propensity >= 85

---

## SECTION 7 — OUTREACH STACK

Active channels (in launch priority order):
  Email: Salesforge (dedicated infrastructure)
  LinkedIn: Unipile (DM + connection requests)
  Voice AI: ElevenAgents + Alex persona (Claude Haiku)
  SMS: Telnyx (on hold until post-launch)

Manual mode: every message reviewed before sending.
Autopilot mode: available after Manual validated.
Kill switch: pauses all campaigns instantly.
Always visible. Cannot be hidden.

---

## SECTION 8 — VALIDATION RULES

Company-level validation (Stage 1 output):
  found = True
  confidence >= 0.70
  company OR company_name present
  AND (domain OR phone OR gmb_place_id present)

CRITICAL: All GMB-discovered leads have gmb_place_id.
The _has_company_data fallback evaluates True for these
leads even when sources_used = 0. This is correct and
intentional. Do not remove this fallback. Do not weaken
this logic. It saves all 409 GMB leads from falling
through to deprecated Clay.

Person-level validation (Stage 3 output):
  email present
  first_name present
  last_name present
  company present

Confidence calculation:
  0 sources + gmb_place_id present: 0.70 (passthrough)
  1 source used: 0.80
  2 sources used: 0.85
  Formula: 0.75 + (sources_used × 0.05), floor 0.70

---

## SECTION 9 — ENVIRONMENT VARIABLES

| Variable             | Service            | Status on Railway  |
|----------------------|--------------------|--------------------|
| BRIGHTDATA_API_KEY   | Bright Data all    | Confirmed          |
| ABN_LOOKUP_GUID      | ABR endpoint       | Confirmed          |
| DATAFORSEO_LOGIN     | DataForSEO         | Confirmed          |
| DATAFORSEO_PASSWORD  | DataForSEO         | Confirmed          |
| LEADMAGIC_API_KEY    | Leadmagic T3 + T5  | VERIFY — absent    |
|                      |                    | from local env     |
| ANTHROPIC_API_KEY    | Claude Haiku       | Confirmed          |

LEADMAGIC_API_KEY was absent from local env per #210.
Confirm it exists on Railway before Directive #212.
Dave action required: verify Leadmagic key on Railway.

---

## SECTION 10 — KNOWN TECHNICAL DEBT

These are documented issues, not active blockers.
Do not fix without an explicit CEO directive.
Report if you encounter them. Do not route around them.

1. Silent exception swallowing: _enrich_tier1 except
   block returns None without logging. Fix: #212.
2. Clay references in scout.py: CLAY_MAX_PERCENTAGE,
   clay_budget, _enrich_tier2. Remove in #212.
3. Stale docstrings: _enrich_tier1 still references
   Hunter, Kaspr, Proxycurl. Clean in #212.
4. batch_size = 100: raise to 500 in #212.
5. business_universe match rate 0%: name format
   mismatch. Fuzzy matching needed. Separate directive.
6. Stage 2 person discovery: not yet built.
7. Stage 2.5 social presence: not yet built.
8. Message generation: untested with real data.
9. LEADMAGIC_API_KEY: absent from local env.
   Dave to verify Railway.
