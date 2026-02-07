# Agency OS Integration Master Plan

**Created:** 2026-02-05
**Author:** Elliot (CTO)
**Status:** PLANNING → Awaiting Dave's Sign-Off

---

## Executive Summary

This plan consolidates ALL recent architectural decisions into a single integration roadmap. We're replacing the old "Rented Data" model with the new "Manufacturing Intel" architecture.

**The Transformation:**
| Before | After |
|--------|-------|
| Apollo (SPOF) | Siege Waterfall (5-Tier) |
| Apify ($15/mo) | Autonomous Stealth Browser |
| SDK Agents ($400/mo) | Smart Prompts ($6/mo) |
| Twilio Voice | Telnyx + Groq/Claude Hybrid |
| Static Avatar | Maya Digital Employee |
| Multi-step Onboarding | Single Page Flow |

**Projected Savings:** ~$540/month (48% → 70% margin on Ignition tier)

---

## Part 1: Systems to REMOVE

### 1.1 Apollo Integration (DEPRECATE)
**Current Location:** `src/integrations/apollo.py` (520 lines)

**Files to Modify:**
| File | Current Use | Replacement |
|------|-------------|-------------|
| `src/engines/scout.py` | `enrich_person()` | Siege Waterfall Tiers 1-4 |
| `src/engines/icp_scraper.py` | `enrich_company()` | ABN + GMB (Tiers 1-2) |
| `src/orchestration/tasks/enrichment_tasks.py` | All Apollo calls | Waterfall worker |
| `src/orchestration/flows/pool_population_flow.py` | `search_people_for_pool()` | Proxycurl + Hunter |
| `src/services/lead_pool_service.py` | Apollo enrichment | Waterfall enrichment |
| `src/agents/icp_discovery_agent.py` | Company lookup | ABN + GMB scraper |
| `src/agents/skills/portfolio_fallback.py` | Apollo fallback | Remove (redundant) |

**Test Files to Update:**
- `tests/test_engines/test_scout.py`
- `tests/test_engines/test_deep_research.py`
- `tests/test_api/test_leads.py`
- `tests/test_e2e/test_full_flow.py`
- `tests/live/config.py`
- `tests/fixtures/api_responses.py`

**Migration Strategy:**
1. Create `src/integrations/siege_waterfall.py` (unified interface)
2. Update each consumer to use new interface
3. Keep Apollo as optional fallback (feature flag)
4. Remove after 30-day validation

### 1.2 Apify Integration (DEPRECATE)
**Current Location:** `src/integrations/apify.py` (900+ lines)

**Files to Modify:**
| File | Current Use | Replacement |
|------|-------------|-------------|
| `src/engines/scout.py` | Website scraping | Autonomous Browser |
| `src/engines/icp_scraper.py` | Waterfall scraping | Autonomous Browser |
| `src/engines/client_intelligence.py` | Social scraping | Proxycurl + direct APIs |
| `src/agents/skills/social_enricher.py` | LinkedIn/Twitter | Proxycurl |
| `src/agents/skills/social_profile_discovery.py` | Profile discovery | Proxycurl |
| `src/agents/skills/research_skills.py` | General scraping | Autonomous Browser |
| `src/agents/sdk_agents/sdk_tools.py` | Apify tools | Remove |

**Apify Functions → Replacements:**
| Function | Replacement |
|----------|-------------|
| `scrape_website_with_waterfall()` | `autonomous_browser.fetch()` |
| `scrape_linkedin_profiles()` | Proxycurl Person API |
| `scrape_linkedin_company()` | Proxycurl Company API |
| `scrape_google_business()` | DIY GMB Scraper |
| `scrape_instagram_profile()` | Skip (low value) |
| `scrape_facebook_page()` | Skip (low value) |
| `scrape_twitter_profile()` | Skip or direct API |
| `scrape_*_reviews()` | Autonomous Browser |

**Migration Strategy:**
1. Build `src/integrations/gmb_scraper.py` (FCO-003)
2. Update website scraping to use Autonomous Browser
3. Replace LinkedIn calls with Proxycurl
4. Remove social scraping (low ROI)
5. Remove Apify after validation

### 1.3 SDK Agents (DEPRECATE) — FCO-002
**Current Locations:**
- `src/agents/sdk_agents/enrichment_agent.py` — REMOVE
- `src/agents/sdk_agents/email_agent.py` — REMOVE  
- `src/agents/sdk_agents/voice_kb_agent.py` — REMOVE
- `src/agents/sdk_agents/sdk_eligibility.py` — KEEP (objection routing only)
- `src/agents/sdk_agents/sdk_tools.py` — UPDATE (remove enrichment tools)

**Files Calling SDK:**
| File | Current Call | Replacement |
|------|--------------|-------------|
| `src/engines/scout.py` | `run_sdk_enrichment()` | Remove (Siege Waterfall) |
| `src/engines/content.py` | `generate_email_content()` | `smart_prompts.generate()` |
| `src/engines/voice.py` | `generate_knowledge_base()` | `smart_prompts.voice_kb()` |
| `src/orchestration/tasks/` | SDK task calls | Smart Prompts tasks |

**Migration Strategy:**
1. Update `content.py` to use `smart_prompts.py` exclusively
2. Update `voice.py` to use `SMART_VOICE_KB_PROMPT`
3. Remove SDK enrichment calls from scout engine
4. Keep SDK eligibility for complex objection routing (10%)
5. Delete deprecated agent files

---

## Part 2: Systems to BUILD

### 2.1 Siege Waterfall Unified Interface
**New File:** `src/integrations/siege_waterfall.py`

```python
class SiegeWaterfall:
    """
    Unified interface for 5-tier enrichment.
    Replaces Apollo as single source.
    """
    
    async def enrich_lead(self, lead: Lead) -> EnrichedLead:
        """Full 5-tier enrichment."""
        # Tier 1: ABN Bulk (FREE)
        lead = await self.tier1_abn(lead)
        
        # Tier 2: GMB/Ads Signals ($0.006)
        lead = await self.tier2_gmb(lead)
        
        # Tier 3: Hunter.io ($0.012)
        lead = await self.tier3_hunter(lead)
        
        # Tier 4: Proxycurl ($0.024)
        lead = await self.tier4_proxycurl(lead)
        
        # Tier 5: Identity Gold ($0.45) — ALS ≥85 only
        if lead.als_score >= 85:
            lead = await self.tier5_identity(lead)
        
        return lead
```

**Dependencies:**
- `src/integrations/abn_client.py` (new)
- `src/integrations/gmb_scraper.py` (new — FCO-003)
- `src/integrations/hunter.py` (exists)
- `src/integrations/proxycurl.py` (exists, needs update)
- `src/integrations/kaspr.py` (new)

### 2.2 GMB Scraper (FCO-003)
**New File:** `src/integrations/gmb_scraper.py`

Replaces Apify Google Maps scraping using Autonomous Browser.

**Functions:**
- `search_business(name, postcode)` — Find business on Maps
- `scrape_details(place_id)` — Get phone, address, hours, reviews
- `batch_scrape(businesses)` — Bulk operation

**Uses:**
- `src/engines/proxy_waterfall.py` — Webshare proxy rotation
- Autonomous Stealth Browser — JS rendering

### 2.3 Proxycurl Integration (Upgrade)
**File:** `src/integrations/proxycurl.py`

**New Functions Needed:**
- `get_person_profile(linkedin_url)` — Full profile data
- `get_company_profile(linkedin_url)` — Company data
- `get_person_activity(linkedin_url)` — Recent posts (for ALS)
- `search_employees(company_domain, titles)` — Find decision makers

**Cost:** $0.012-0.024/request = ~$15/mo for Ignition tier

### 2.4 Kaspr Integration (New)
**New File:** `src/integrations/kaspr.py`

Tier 5 mobile enrichment for ALS ≥85 leads.

**Functions:**
- `enrich_mobile(linkedin_url)` — Get verified mobile
- `batch_enrich(profiles)` — Bulk operation

**Cost:** $0.43-0.56/phone, API on Starter plan

### 2.5 ABN Client (New)
**New File:** `src/integrations/abn_client.py`

Tier 1 free data from data.gov.au.

**Functions:**
- `search_by_abn(abn)` — Lookup by ABN
- `search_by_name(name, state)` — Search businesses
- `bulk_import(industry, state)` — Seed lead pool

**Data Available:** Business name, ABN, ACN, state, postcode, status

---

## Part 3: Systems to UPDATE

### 3.1 Smart Prompts Engine
**File:** `src/engines/smart_prompts.py` (39KB — exists)

**Required Updates:**
- Add `generate_sms_content()` 
- Add `generate_voice_knowledge_base()`
- Add `generate_linkedin_message()`
- Ensure all use Siege Waterfall data fields

### 3.2 Content Engine
**File:** `src/engines/content.py` (67KB)

**Changes:**
- Remove all SDK imports
- Route all generation through `smart_prompts.py`
- Update cost tracking ($0.02/lead vs $0.50)

### 3.3 Voice Engine
**File:** `src/engines/voice.py` (47KB)

**Changes:**
- Remove SDK voice KB calls
- Use `smart_prompts.voice_kb()`
- Update to Telnyx provider
- Implement Groq/Claude hybrid (90%/10%)

### 3.4 Scout Engine
**File:** `src/engines/scout.py` (53KB)

**Changes:**
- Remove `run_sdk_enrichment()` calls
- Replace Apollo calls with Siege Waterfall
- Replace Apify website scraping with Autonomous Browser
- Update scoring to use new data fields

### 3.5 ICP Scraper
**File:** `src/engines/icp_scraper.py` (66KB)

**Changes:**
- Replace Apify waterfall with Autonomous Browser
- Update portfolio detection logic
- Use Siege Waterfall for enrichment

### 3.6 Identity Escalation
**File:** `src/engines/identity_escalation.py` (31KB — recent)

**Status:** Recently built for Tier 5. Verify integration with:
- Kaspr API
- Director Hunt (ASIC)
- ALS ≥85 gate

### 3.7 Waterfall Verification Worker
**File:** `src/engines/waterfall_verification_worker.py` (30KB — recent)

**Status:** Recently built for Tiers 1-4. Verify:
- ABN integration
- Hunter.io integration
- ZeroBounce escalation
- Proxycurl social scoring

---

## Part 4: Voice AI Stack Update

### Current → New
| Component | Current | New |
|-----------|---------|-----|
| Telephony | Twilio (+61240126220) | Telnyx (AU mobile +614xx) |
| TTS | ElevenLabs | Cartesia (10x cheaper) |
| LLM | Claude 100% | Groq 90% + Claude 10% |
| Knowledge Base | SDK Agent | Smart Prompts |

### Files to Update
| File | Change |
|------|--------|
| `src/engines/voice.py` | Add Telnyx provider |
| `src/engines/voice_agent_telnyx.py` | New Telnyx implementation |
| `src/integrations/vapi.py` | Update to Telnyx phone |
| `src/integrations/telnyx.py` | New integration |
| `src/integrations/cartesia.py` | New TTS integration |

### Hybrid LLM Routing
```python
def route_llm(turn_context: TurnContext) -> str:
    """Route to appropriate LLM based on complexity."""
    if turn_context.is_objection and turn_context.complexity > 0.7:
        return "claude-3-haiku"  # 10% of calls
    return "groq-llama-3.1-70b"  # 90% of calls
```

---

## Part 5: Frontend Updates

### 5.1 Onboarding Simplification
**Current:** Multi-step wizard
**New:** Single page

**Components:**
1. Website URL input → triggers ICP extraction
2. Connect CRM button (OAuth)
3. Connect LinkedIn button (Unipile OAuth)

**Backend Auto-Provisioning (Kitchen Talk):**
- Pre-warmed email address from buffer
- Pre-warmed phone number from buffer
- User never sees this

### 5.2 Maya Digital Employee
**New Components:**
- `MayaAvatar.tsx` — Circular hologram frame
- `MayaOnboarding.tsx` — Step-by-step guide
- `MayaChat.tsx` — Support chat interface
- `MayaBriefing.tsx` — Daily voice/text updates

**Backend:**
- `src/engines/maya.py` — Personality + content generation
- `src/integrations/cartesia.py` — Voice synthesis
- Pre-rendered video library (onboarding steps)

### 5.3 Campaign Lead Allocation
**New Component:** `CampaignAllocationSlider.tsx`

**Behavior:**
- Sliders share 100% pool (zero-sum)
- Tier determines max campaigns (Ignition = 5)
- AI suggests allocation based on ICP
- **LOCKED after launch** — no adjustments

### 5.4 Industry Dropdown (Pending)
Replace 8 checkboxes with searchable ANZSIC dropdown (500+ industries).

---

## Part 6: Database Migrations

### Migration 055 (Ready)
**File:** `055_waterfall_enrichment_architecture.sql`

**Adds:**
- `enrichment_lineage` JSONB column
- Intent signal columns
- `lead_lineage_log` table
- Composite + BRIN indexes

**Status:** Ready for Supabase execution

### New Migrations Needed

**056 — Siege Waterfall Fields:**
```sql
ALTER TABLE lead_pool ADD COLUMN tier1_abn_data JSONB;
ALTER TABLE lead_pool ADD COLUMN tier2_gmb_data JSONB;
ALTER TABLE lead_pool ADD COLUMN tier3_hunter_data JSONB;
ALTER TABLE lead_pool ADD COLUMN tier4_proxycurl_data JSONB;
ALTER TABLE lead_pool ADD COLUMN tier5_identity_data JSONB;
ALTER TABLE lead_pool ADD COLUMN enrichment_cost_aud DECIMAL(10,4);
```

**057 — Maya Tables:**
```sql
CREATE TABLE maya_conversations (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    messages JSONB[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE maya_briefings (
    id UUID PRIMARY KEY,
    client_id UUID REFERENCES clients(id),
    content TEXT,
    audio_url TEXT,
    delivered_at TIMESTAMPTZ
);
```

---

## Part 7: Environment Variables

### New Variables Needed
```env
# Siege Waterfall
ABN_API_KEY=           # data.gov.au (if needed)
HUNTER_API_KEY=        # hunter.io
PROXYCURL_API_KEY=     # Proxycurl/Nubela
KASPR_API_KEY=         # Kaspr Starter

# Voice AI
TELNYX_API_KEY=        # Telnyx
TELNYX_PHONE_ID=       # AU mobile number
CARTESIA_API_KEY=      # Cartesia TTS
GROQ_API_KEY=          # Groq LLM

# Maya
MIDJOURNEY_FACE_URL=   # Maya's face asset
```

### Variables to Remove (After Migration)
```env
# APOLLO_API_KEY=      # Deprecated
# APIFY_API_KEY=       # Deprecated
```

---

## Part 8: Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Core infrastructure without breaking existing

| Task | Owner | Effort |
|------|-------|--------|
| Run migration 055 | Dave | 5 min |
| Create Telnyx account + ID verify | Dave | 30 min |
| Build `siege_waterfall.py` interface | Elliot | M |
| Build `gmb_scraper.py` (FCO-003) | Elliot | M |
| Build `kaspr.py` integration | Elliot | S |
| Test Proxycurl trial | Elliot | S |

### Phase 2: Enrichment Migration (Week 2)
**Goal:** Replace Apollo with Siege Waterfall

| Task | Owner | Effort |
|------|-------|--------|
| Update `scout.py` to use Siege Waterfall | Elliot | L |
| Update `icp_scraper.py` | Elliot | M |
| Update enrichment tasks | Elliot | M |
| Update pool population flow | Elliot | M |
| Feature flag Apollo (fallback) | Elliot | S |

### Phase 3: Scraping Migration (Week 2-3)
**Goal:** Replace Apify with Autonomous Browser

| Task | Owner | Effort |
|------|-------|--------|
| Update website scraping in scout | Elliot | M |
| Update icp_scraper waterfall | Elliot | M |
| Replace social scraping with Proxycurl | Elliot | M |
| Remove client_intelligence Apify calls | Elliot | S |

### Phase 4: SDK Deprecation (Week 3)
**Goal:** Smart Prompts replaces SDK

| Task | Owner | Effort |
|------|-------|--------|
| Update content.py to Smart Prompts only | Elliot | M |
| Update voice.py to Smart Prompts | Elliot | M |
| Remove SDK enrichment calls | Elliot | S |
| Delete deprecated SDK agents | Elliot | S |
| Update cost tracking | Elliot | S |

### Phase 5: Voice AI Upgrade (Week 3-4)
**Goal:** Telnyx + Groq/Claude hybrid

| Task | Owner | Effort |
|------|-------|--------|
| Build Telnyx integration | Elliot | M |
| Build Cartesia integration | Elliot | S |
| Implement hybrid LLM routing | Elliot | M |
| Update Vapi configuration | Elliot | S |
| Test end-to-end voice call | Both | M |

### Phase 6: Frontend Updates (Week 4-5)
**Goal:** New UX components

| Task | Owner | Effort |
|------|-------|--------|
| Build single-page onboarding | Elliot | L |
| Build campaign allocation sliders | Elliot | M |
| Build Maya avatar component | Elliot | M |
| Build Maya chat component | Elliot | M |
| Industry searchable dropdown | Elliot | S |

### Phase 7: Cleanup & Validation (Week 5-6)
**Goal:** Remove old systems, validate new

| Task | Owner | Effort |
|------|-------|--------|
| 30-day parallel run (old + new) | Auto | - |
| Remove Apollo feature flag | Elliot | S |
| Delete apollo.py | Elliot | S |
| Delete apify.py | Elliot | S |
| Delete SDK agent files | Elliot | S |
| Update all tests | Elliot | M |
| Final E2E validation | Both | L |

---

## Part 9: Risk Mitigation

### Risk 1: Enrichment Quality Drop
**Mitigation:** 
- Run parallel for 30 days
- Compare Siege Waterfall vs Apollo results
- Fallback to Apollo if quality <80%

### Risk 2: Scraping Failures
**Mitigation:**
- Autonomous Browser has 215k proxies
- Implement retry with proxy rotation
- Queue failed scrapes for manual review

### Risk 3: Voice Call Quality
**Mitigation:**
- Test Telnyx AU mobile extensively
- Keep Twilio as backup
- Groq latency is actually lower than Claude

### Risk 4: SDK Content Quality
**Mitigation:**
- A/B test Smart Prompts vs SDK output
- Human review first 100 emails
- Rollback path via feature flag

---

## Part 10: Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Ignition Margin | 48% | 70% |
| Enrichment Cost/Lead | $0.50+ | $0.105 |
| SDK Cost/Month | $400 | $6 |
| Voice Cost/Call | $0.50+ | $0.10 |
| Apify Dependency | Yes | No |
| Apollo Dependency | Yes | No |

---

## Sign-Off

**Dave (CEO):** _________________ Date: _______

**Elliot (CTO):** Ready to execute upon approval.

---

*Generated: 2026-02-05 23:45 UTC*
