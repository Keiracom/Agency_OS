# MEMORY.md — Agency OS Long-Term Memory

*Curated decisions, lessons, and persistent context.*

---

## Enrichment Infrastructure

### Tier 2 GMB: DIY Scraper DEPRECATED
**As of:** CEO Directive #031 (2026-02-17)

The DIY GMB scraper (`src/integrations/gmb_scraper.py`) has been **DEPRECATED**.

**Replaced by:** Bright Data Google Maps SERP at $0.0015/request.

**Validation:** Directive #020a (2026-02-16)

**New skill:** `skills/enrichment/brightdata-gmb/`

**Why deprecated:**
- Missing dependencies: `tools/autonomous_browser.py`, `tools/proxy_manager.py` never restored
- Cost: $0.006/lead (DIY) vs $0.0015/request (Bright Data) = 75% savings
- Quality: Bright Data returns email, phone, website, social media, reviews
- Reliability: Professional API vs brittle browser automation

The `tools/` directory (autonomous_browser.py, proxy_manager.py) is **no longer needed**.

---

## Credential Locations

**Primary .env:** `/home/elliotbot/.config/agency-os/.env`  
**Symlink:** `/home/elliotbot/clawd/.env` → primary

**Critical credentials (verified 2026-02-17):**
- `ABN_LOOKUP_GUID` — Tier 1 ABN Lookup (FREE)
- `BRIGHTDATA_API_KEY` — Tiers 1.5, 2 (LinkedIn, GMB)
- `LEADMAGIC_API_KEY` — Tier 3 (email discovery)

---

## Enrichment Skills Created

**Location:** `skills/enrichment/`  
**Created:** CEO Directive #031 (2026-02-17)

| Skill | Tier | Cost | Status |
|-------|------|------|--------|
| abn-lookup | 1 | FREE | ✅ |
| brightdata-linkedin | 1.5 | ~$0.01 | ✅ |
| brightdata-gmb | 2 | $0.0015 | ✅ |
| hunter-verify | 3 | $0.15 | ❌ DEPRECATED |
| leadmagic-email | 3 | $0.015 | ✅ |
| leadmagic-mobile | 5 | $0.077 | ✅ |

---

## Waterfall v3 Architecture (Active as of 2026-03-01)

**Decision:** CEO Directive #142, 2026-03-01
**Discovery method:** GMB-first (`MapsFirstDiscovery`). `ABNFirstDiscovery` deprecated per Waterfall v3 Decision #1.
**Providers:** Leadmagic (T3 email $0.015, T5 mobile $0.077). Hunter and Kaspr deprecated.
**ALS gates:** `PRE_ALS_GATE = 20` (was 30). `HOT_THRESHOLD = 85`.

**Active enrichment path (campaign_trigger.py `_enrich_lead`):**
T0 GMB → T1 ABN → T1.5a SERP Maps → T1.5b SERP LinkedIn → T2 LinkedIn Company → ALS gate (≥20) → T2.5 LinkedIn People → T3 Leadmagic Email → T5 Leadmagic Mobile

**Decision-maker path:**
T-DM0 DataForSEO ($0.0465, ICP pass) → T-DM1 BD Profile ($0.0015, ICP pass) → T-DM2/2b/3/4 (Propensity ≥70)

**Orphaned code (not wired into active campaign trigger — scheduled for deletion in Step 3):**
- `run_full_pipeline()` — exists in waterfall_v2.py but not called by campaign trigger
- `ParallelDiscovery` — thin wrapper, redundant since v3 Decision #1
- `_extract_decision_makers()` — dead method, never called
- `_sdk_disambiguate_trading_name()` — broken (self.supabase unset), unreachable in live path

---

*Last Updated: 2026-02-17*

## 2026-03-05 — business_universe Architecture Session

### Long-term vision
Agency OS is the Trojan Horse. business_universe is the long-term product.
See ceo_memory key: business_universe_long_term_vision

### New tables required (NOT BUILT YET)
- lead_outreach_history
- lead_agency_suppression
- lead_signal_changes
See ceo_memory key: business_universe_new_tables_required

### Open questions (DO NOT BUILD UNTIL RESOLVED)
See ceo_memory key: business_universe_open_questions

### Next directive: #172
Schema design and open question resolution. No code until all open questions answered.

## 2026-03-05 — Resolved decisions and build sequence

### Resolved open questions
- lead_claiming: locked at campaign submission
- angle_definition: hook category + proof point category, service-profile aware
- cis_cross_agency: anonymised aggregate learning approved
- reactivation_approval: automatic + Manual/Autopilot toggle
- saturated_markets: surface before subscription
- global_cooling_off: 30 days, queue delay not hard block
- one_off_detection: bidirectional CRM required, signal-based inference
- poaching_detection: parked
- tier_flexibility: post-launch research
- spam_act: legal review with T&Cs

### Build sequence ratified
1. Bidirectional HubSpot CRM
2. business_universe new status fields
3. New tables (lead_outreach_history etc)
4. QueryTranslator rebuild
5. Campaign submission lead locking

### CRM audit findings
Push-only confirmed. crm.objects.deals.read scope exists unused.
Full spec in ceo_memory: business_universe_crm_bidirectional_spec

See ceo_memory: business_universe_build_sequence
