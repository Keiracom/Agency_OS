# Agency OS System Audit — 2026-02-05

## Executive Summary

**Audit Result: 6/10 decisions COMPLETE, 2 PARTIAL, 2 NOT STARTED**

| Status | Count | Decisions |
|--------|-------|-----------|
| ✅ COMPLETE | 6 | FCO-001, FCO-002, FORGE-001, VOICE-001, CAMPAIGN-001, BUFFER-001 |
| 🟡 PARTIAL | 2 | SIEGE-001, ONBOARD-001 |
| 🔴 NOT STARTED | 2 | FCO-003 (Apify deprecation), MAYA-001 (Digital Employee UI) |

**Critical Gaps Found:**
1. **Missing integrations** for 5-tier Siege Waterfall (Hunter, Proxycurl, Lusha, Kaspr)
2. **Apify still active** — DIY GMB scraper not implemented
3. **Maya UI not started** — blocks Phase 20

---

## Decision Verification

### FCO-001: Fixed-Cost Fortress (Proxy Waterfall)
- **Status:** ✅ COMPLETE
- **Evidence:** 
  - `src/engines/proxy_waterfall.py` — Full implementation
  - Proxy tiering: Datacenter → ISP → Residential
  - Cost tracking in AUD ($0.001 → $0.008 → $0.015 per request)
  - Escalation on 403/429/503 codes
  - ~60% scraping cost reduction documented
- **Gaps:** None

---

### FCO-002: SDK Deprecation → Smart Prompts
- **Status:** ✅ COMPLETE
- **Evidence:**
  - `src/engines/smart_prompts.py` — Full implementation with:
    - Field priority system (HIGH/MEDIUM/LOW)
    - `SMART_EMAIL_PROMPT` template
    - `SMART_VOICE_KB_PROMPT` template
    - Lead context builders using all enriched data
  - SDK agents marked deprecated:
    - `src/agents/sdk_agents/email_agent.py` → "DEPRECATED: FCO-002"
    - `src/agents/sdk_agents/voice_kb_agent.py` → "DEPRECATED: FCO-002"
    - `src/agents/sdk_agents/enrichment_agent.py` → "DEPRECATED: FCO-002"
    - All emit `DeprecationWarning` on import
- **Gaps:** None (SDK agents remain for backwards compatibility but are deprecated)

---

### FCO-003: Apify Deprecation → DIY GMB Scraper
- **Status:** 🔴 NOT STARTED
- **Evidence:**
  - `src/integrations/apify.py` — **Still active** (47KB, not deprecated)
  - Apify actors still in use:
    - `GOOGLE_MAPS_SCRAPER = "apify/google-maps-scraper"`
    - `GOOGLE_REVIEWS_SCRAPER = "compass/google-maps-reviews-scraper"`
  - 12+ files still import from Apify integration
  - **No DIY GMB scraper found** in codebase
- **Gaps:**
  - [ ] Create `src/engines/gmb_scraper.py` (DIY using proxy waterfall)
  - [ ] Migrate GMB calls from Apify to DIY
  - [ ] Add deprecation warnings to Apify integration
- **Cost Impact:** Apify GMB = ~$6.20/1000 leads — DIY would reduce to $0

---

### FORGE-001: Salesforge Ecosystem (InfraForge + WarmForge + Salesforge)
- **Status:** ✅ COMPLETE
- **Evidence:**
  - `src/integrations/infraforge.py` — Domain provisioning (buy, list, alternatives)
  - `src/integrations/warmforge.py` — Warmup status monitoring (v1 API)
  - `src/integrations/salesforge.py` — Email sending with threading
  - All three have proper auth headers and error handling
  - Used by `src/orchestration/flows/warmup_monitor_flow.py`
- **Gaps:** None

---

### VOICE-001: Voice AI Stack (Vapi + Telnyx + Cartesia + Groq/Claude)
- **Status:** ✅ COMPLETE
- **Evidence:**
  - `src/engines/voice.py` (47KB) — Full Vapi orchestration:
    - STT: AssemblyAI Universal (via Vapi)
    - TTS: Cartesia Sonic-2 (90ms), ElevenLabs fallback
    - LLM: Hybrid Groq (90%) / Claude Haiku (10%) via Vapi Squads
    - Silent handoff triggers: `[HANDOFF_COMPLEX]` / `[HANDOFF_SIMPLE]`
  - `src/engines/voice_agent_telnyx.py` (23KB) — Raw Telnyx alternative:
    - 95% cost reduction ($2.00/min → $0.09/min)
    - ElevenLabs Flash v2.5 for Australian accents
    - <200ms latency target
  - `src/integrations/vapi.py` — VapiClient, VapiAssistantConfig, VapiSquadConfig
- **Gaps:** None

---

### SIEGE-001: Waterfall 5-tier Enrichment (ABN→GMB→Hunter→Proxycurl→Kaspr)
- **Status:** 🟡 PARTIAL
- **Evidence:**
  - **Engines implemented:**
    - `src/engines/waterfall_verification_worker.py` — ABN + GMB + Hunter + ZeroBounce
    - `src/engines/identity_escalation.py` — Proxycurl + Lusha/Kaspr logic
  - **Cost tracking present:** All costs in AUD
  - **ALS gating documented:** Tier 5 only for ALS ≥ 85
- **Gaps (CRITICAL):**
  - [ ] ❌ `src/integrations/hunter.py` — **NOT CREATED**
  - [ ] ❌ `src/integrations/proxycurl.py` — **NOT CREATED**
  - [ ] ❌ `src/integrations/lusha.py` — Comment says "to be created"
  - [ ] ❌ `src/integrations/kaspr.py` — **NOT CREATED**
  - Engines reference these but they don't exist — will error at runtime

---

### MAYA-001: Maya Digital Employee UI
- **Status:** 🔴 NOT STARTED
- **Evidence:**
  - Grep for "maya" found only 1 file: `src/engines/voice_agent_telnyx.py` (unrelated comment)
  - `frontend/src/components/` contains only `library/` and `ui/` (base components)
  - No Maya dashboard, employee card, or AI chat UI
  - Blueprint describes Maya but no code exists
- **Gaps:**
  - [ ] Design Maya employee card component
  - [ ] Implement Maya dashboard layout
  - [ ] Create AI chat interface for status/suggestions
  - [ ] Wire to backend campaign suggestions API
- **Blocks:** Phase 20 (UI Wiring)

---

### ONBOARD-001: Simplified Single-Page Onboarding
- **Status:** 🟡 PARTIAL
- **Evidence:**
  - **Backend exists:** `src/api/routes/onboarding.py` (24KB)
    - `POST /api/v1/onboarding/analyze` — Submit website for ICP extraction
    - `GET /api/v1/onboarding/status/{job_id}` — Check progress
    - `GET /api/v1/onboarding/result/{job_id}` — Get extracted ICP
    - `POST /api/v1/onboarding/confirm` — Confirm/edit ICP
  - **Frontend unclear:** No dedicated onboarding page found in `frontend/src/`
- **Gaps:**
  - [ ] Verify frontend single-page onboarding exists
  - [ ] Wire frontend to backend endpoints
  - [ ] Implement progress stepper UI

---

### CAMPAIGN-001: Campaign Lead Allocation (Sliders, 100% Pool)
- **Status:** ✅ COMPLETE
- **Evidence:**
  - `src/models/campaign.py`:
    - `lead_allocation_pct: int` — Percentage of lead pool (default 100)
    - `lead_count: int` — Calculated from pct × total leads
    - `campaign_type: str` — AI_SUGGESTED or CUSTOM
    - `ai_suggestion_reason: str` — Why AI suggested this
  - Blueprint Phase 37 referenced in model
  - `src/api/routes/campaign_generation.py` — AI campaign generation endpoint
- **Gaps:** 
  - [ ] Verify frontend slider UI for allocation
  - [ ] Verify "locked on launch" behavior

---

### BUFFER-001: Resource Pool Pre-warming (Domains, Phones, LinkedIn)
- **Status:** ✅ COMPLETE
- **Evidence:**
  - `src/models/resource_pool.py`:
    - `ResourceType` enum: EMAIL_DOMAIN, PHONE_NUMBER, LINKEDIN_SEAT
    - `ResourceStatus` enum: AVAILABLE, ASSIGNED, WARMING, RETIRED
    - `HealthStatus` enum: GOOD, WARNING, CRITICAL with thresholds
    - `TIER_ALLOCATIONS` dict with per-tier resource counts
  - `src/services/resource_assignment_service.py` — Assignment logic
  - `src/orchestration/flows/infra_provisioning_flow.py` — Provisioning automation
- **Gaps:** None

---

## Phase Status (Code-Verified)

| Phase | Name | Blueprint | Actual | Evidence |
|-------|------|-----------|--------|----------|
| 1-10 | Core Platform | ✅ | ✅ | Full src/ structure exists |
| 11 | ICP Discovery | ✅ | ✅ | `agents/icp_discovery_agent.py`, `api/routes/onboarding.py` |
| 16 | Conversion Intelligence | ✅ | ✅ | `detectors/`, `engines/scorer.py` |
| 17 | Launch Prerequisites | 🟡 | 🟡 | Health checks exist, Vapi integrated, Sentry utils present |
| 18 | Email Infrastructure | ✅ | ✅ | Salesforge ecosystem fully integrated |
| 19 | Siege Waterfall | 🟡 | 🟡 | Engines exist but **missing 4 integrations** |
| 20 | Landing Page + UI | 🟡 | 🔴 | **Maya not started**, onboarding backend only |
| 21 | E2E Journey Test | 🔴 | 🔴 | Blocked by Phase 19 + 20 gaps |
| 22 | Marketing Automation | 🔴 | 🔴 | Not started |
| 23 | Platform Intelligence | 📋 | 📋 | Post-launch |

---

## Missing Integrations (CRITICAL BLOCKERS)

These files are **referenced in engines but do not exist**:

| Integration | Referenced In | Status |
|-------------|---------------|--------|
| `hunter.py` | `waterfall_verification_worker.py` | ❌ Not created |
| `proxycurl.py` | `identity_escalation.py` | ❌ Not created |
| `lusha.py` | `identity_escalation.py` | ❌ Not created |
| `kaspr.py` | `identity_escalation.py` | ❌ Not created |

**Impact:** Siege Waterfall (Phase 19) will fail at runtime until these are implemented.

---

## Deprecated But Still Active Files

| File | Status | Action Required |
|------|--------|-----------------|
| `src/integrations/apify.py` | Active (47KB) | Add deprecation warning, migrate GMB to DIY |
| `src/integrations/heyreach.py` | Active (14KB) | Verify if still needed (LinkedIn via Unipile now) |
| `src/agents/sdk_agents/*.py` | Deprecated but exported | Remove from `__init__.py` exports |

---

## docs/architecture/ Updates Required

| File | Update Needed |
|------|---------------|
| `ARCHITECTURE_INDEX.md` | Add Siege Waterfall section |
| `business/SCORING.md` | Verify ALS thresholds match code |
| `distribution/` | Add GMB scraper spec |
| `TODO.md` | Mark completed items, add new gaps |

---

## Action Items (Prioritized)

### P0 — Blocks E2E (Phase 21)

1. **Create `src/integrations/hunter.py`**
   - Hunter.io email finder API
   - Required for Siege Tier 3

2. **Create `src/integrations/proxycurl.py`**
   - LinkedIn enrichment API
   - Required for Siege Tier 4

3. **Create `src/integrations/lusha.py`**
   - Mobile number enrichment
   - Required for Siege Tier 5

4. **Create `src/integrations/kaspr.py`**
   - Alternative mobile enrichment
   - Required for Siege Tier 5

### P1 — Cost Optimization

5. **Create DIY GMB Scraper**
   - `src/engines/gmb_scraper.py`
   - Use proxy waterfall for anti-detection
   - Replace Apify dependency

6. **Deprecate Apify fully**
   - Add warnings to `src/integrations/apify.py`
   - Migrate remaining callers

### P2 — UI/UX (Phase 20)

7. **Design Maya Digital Employee UI**
   - Component specs
   - API wiring plan

8. **Verify Frontend Onboarding**
   - Single-page flow
   - Wire to backend

### P3 — Cleanup

9. **Review HeyReach deprecation**
   - LinkedIn moved to Unipile
   - Can `heyreach.py` be removed?

10. **Remove SDK agent exports**
    - Clean up `__init__.py` after deprecation

---

## Appendix: File Evidence

### Verified Files (Exist and Implemented)
```
src/engines/proxy_waterfall.py          ✅ 4KB
src/engines/smart_prompts.py            ✅ 8KB+
src/engines/voice.py                    ✅ 47KB
src/engines/voice_agent_telnyx.py       ✅ 23KB
src/engines/waterfall_verification_worker.py  ✅ 12KB
src/engines/identity_escalation.py      ✅ 8KB
src/integrations/salesforge.py          ✅ 13KB
src/integrations/infraforge.py          ✅ 2.8KB
src/integrations/warmforge.py           ✅ 5.4KB
src/integrations/vapi.py                ✅ 22KB
src/models/resource_pool.py             ✅ 4KB+
src/models/campaign.py                  ✅ 6KB+
src/api/routes/onboarding.py            ✅ 24KB
```

### Missing Files (Referenced but Not Created)
```
src/integrations/hunter.py              ❌
src/integrations/proxycurl.py           ❌
src/integrations/lusha.py               ❌
src/integrations/kaspr.py               ❌
src/engines/gmb_scraper.py              ❌
frontend/src/components/maya/           ❌
```

---

*Audit completed: 2026-02-05*
*Next audit: After P0 items resolved*
