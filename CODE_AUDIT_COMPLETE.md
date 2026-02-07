# Agency OS Code Audit - Complete Analysis
**Generated:** 2025-02-06  
**Scope:** `/home/elliotbot/clawd/Agency_OS/src/`  
**Total Python Files:** 220

---

## Executive Summary

### Critical Findings
1. **Integration Wiring Gaps:** Many integrations exist but aren't exported in `__init__.py` or aren't wired to flows
2. **Stub Code in Production:** 3 integration stubs (Hunter, ProxyCurl, GMB) in siege_waterfall.py
3. **13 Active TODOs:** Several incomplete implementations marked for future work
4. **Engines Layer:** Only `BaseEngine` exported via `__init__.py` - all other engines imported directly

---

## 1. ENGINES FOLDER (`src/engines/`)

### 1.1 File Inventory (24 files)

| File | Size | Purpose | Used By |
|------|------|---------|---------|
| `base.py` | 14KB | BaseEngine, EngineResult, OutreachEngine abstract classes | All engines inherit |
| `allocator.py` | 30KB | Lead allocation with ALS scoring | enrichment_flow, outreach_flow, patterns |
| `campaign_suggester.py` | 16KB | AI campaign suggestions from CIS patterns | post_onboarding_flow, campaigns API |
| `client_intelligence.py` | 24KB | Website/business intelligence extraction | onboarding_flow |
| `closer.py` | 25KB | Intent classification + response generation | reply_tasks, reply_recovery_flow, webhooks |
| `content.py` | 68KB | Multi-channel content generation (email/SMS/LI/voice) | outreach_tasks, outreach_flow, content_agent |
| `content_utils.py` | 12KB | Snapshot builders for content tracking | email, sms, linkedin, voice engines |
| `email.py` | 27KB | Email send via Salesforge | outreach_tasks, outreach_flow |
| `icp_scraper.py` | 66KB | Multi-tier website scraping (Apify→Camoufox) | onboarding_flow, icp_discovery_agent |
| `identity_escalation.py` | 31KB | Proxy waterfall identity enrichment | waterfall_verification_worker |
| `linkedin.py` | 42KB | LinkedIn automation via Unipile | outreach_tasks, outreach_flow |
| `mail.py` | 15KB | Physical mail via ClickSend | outreach_tasks |
| `proxy_waterfall.py` | 15KB | Proxy-based data enrichment | ⚠️ **ISOLATED - no external callers** |
| `reporter.py` | 26KB | Campaign metrics aggregation | reports API |
| `scorer.py` | 67KB | Lead scoring with ALS weights | scoring_tasks, enrichment_flow, pool_assignment |
| `scout.py` | 54KB | Multi-source lead enrichment | enrichment_tasks, intelligence_flow, lead_enrichment_flow |
| `smart_prompts.py` | 39KB | Context-aware prompt building | content engine, voice engine |
| `sms.py` | 19KB | SMS via ClickSend | outreach_tasks |
| `timing.py` | 9KB | Business hours + send time optimization | outreach_tasks, outreach_flow |
| `url_validator.py` | 17KB | URL validation + canonicalization | icp_scraper |
| `voice.py` | 48KB | Voice calls via VAPI/Telnyx | outreach_tasks, webhooks |
| `voice_agent_telnyx.py` | 23KB | Telnyx-based voice agent | ⚠️ **TODO: Deepgram STT not implemented** |
| `waterfall_verification_worker.py` | 30KB | Multi-tier identity verification | Called by identity_escalation |
| `__init__.py` | 186B | Only exports `BaseEngine` | - |

### 1.2 Engine Dependency Graph

```
                    ┌─────────────┐
                    │  BaseEngine │ (base.py)
                    └──────┬──────┘
          ┌────────────────┼────────────────┐
          │                │                │
    OutreachEngine    EngineResult    (Standalone)
          │                │                │
    ┌─────┴─────┐    (All engines)    ┌─────┴─────┐
    │           │                     │           │
  EmailEngine SMSEngine           ScoutEngine AllocatorEngine
  LinkedInEngine VoiceEngine      ScorerEngine ReporterEngine
  MailEngine                      ContentEngine CloserEngine
```

### 1.3 TODOs in Engines
- `voice_agent_telnyx.py:565` - "TODO: Implement Deepgram STT"

---

## 2. INTEGRATIONS FOLDER (`src/integrations/`)

### 2.1 File Inventory (30 files)

| File | Size | Purpose | Exported in __init__.py | Actually Used |
|------|------|---------|------------------------|---------------|
| `abn_client.py` | 32KB | Australian Business Number lookup | ✅ Yes | ✅ Yes |
| `anthropic.py` | 10KB | Claude API wrapper | ❌ No | ✅ Yes (12+ files) |
| `apify.py` | 47KB | Web scraping actor runner | ❌ No | ✅ Yes (5 files) |
| `apollo.py` | 27KB | Lead enrichment API | ❌ No | ✅ Yes (pool_population, scout) |
| `camoufox_scraper.py` | 11KB | Anti-detect browser scraper | ❌ No | ✅ Yes (icp_scraper) |
| `clay.py` | 9KB | Clay enrichment fallback | ❌ No | ✅ Yes (icp_scraper, scout) |
| `clicksend.py` | 21KB | SMS/Mail API | ✅ Yes | ✅ Yes (sms, mail engines) |
| `dataforseo.py` | 19KB | SEO metrics enrichment | ❌ No | ⚠️ **PARTIAL** (model fields exist, no flow calls) |
| `dncr.py` | 13KB | Do Not Call Register check | ❌ No | ✅ Yes (dncr_rewash_flow, enrichment, voice) |
| `elevenlabs.py` | 6KB | Text-to-speech API | ✅ Yes | ⚠️ **MINIMAL** (not in flows) |
| `gmb_scraper.py` | 30KB | Google My Business scraper | ❌ No | ⚠️ **STUBBED** in siege_waterfall |
| `heyreach.py` | 14KB | LinkedIn automation (DEPRECATED) | ❌ No | ⚠️ Only in reply_tasks |
| `infraforge.py` | 3KB | Domain provisioning | ❌ No | ✅ Yes (infra_provisioning_flow) |
| `kaspr.py` | 22KB | Contact enrichment waterfall | ✅ Yes | ⚠️ Only via siege_waterfall |
| `postmark.py` | 10KB | Transactional email | ❌ No | ✅ Yes (reply_tasks, reply_recovery) |
| `redis.py` | 15KB | Cache + rate limiting | ❌ No | ✅ Yes (12+ files) |
| `resend.py` | 6KB | Transactional email alt | ❌ No | ❌ **UNUSED** |
| `salesforge.py` | 13KB | Cold email infrastructure | ❌ No | ✅ Yes (email engine) |
| `sdk_brain.py` | 22KB | AI agent orchestration | ❌ No | ✅ Yes (8 SDK agents) |
| `sentry_utils.py` | 4KB | Error tracking utilities | ❌ No | ❌ **UNUSED** (Sentry in main.py) |
| `serper.py` | 11KB | Google search API | ✅ Yes | ✅ Yes (industry_researcher skill) |
| `siege_waterfall.py` | 37KB | Multi-tier contact enrichment | ❌ No | ⚠️ Has stubs, not wired to flows |
| `supabase.py` | 7KB | Database session factory | ❌ No | ✅ Yes (ALL flows) |
| `twilio.py` | 8KB | SMS/Voice telephony | ❌ No | ✅ Yes (reply_tasks, reply_recovery) |
| `unipile.py` | 25KB | LinkedIn API wrapper | ❌ No | ✅ Yes (linkedin engine, services) |
| `vapi.py` | 22KB | Voice AI orchestration | ✅ Yes | ✅ Yes (voice engine, webhooks) |
| `warmforge.py` | 5KB | Domain warmup monitoring | ❌ No | ✅ Yes (warmup_monitor_flow) |
| `__init__.py` | 1KB | Exports 6 clients only | - | - |

### 2.2 Integration Wiring Issues

**Exported but Rarely Used:**
- `ElevenLabsClient` - Not called in any flow
- `KasprClient` - Only via SiegeWaterfall (which isn't wired)

**Used Everywhere but Not Exported:**
- `get_db_session` (supabase) - 25+ direct imports
- `get_anthropic_client` - 12+ direct imports
- `rate_limiter` (redis) - 5+ direct imports

**Dead/Stub Code:**
1. `siege_waterfall.py` contains 3 stub classes:
   - `GMBScraperStub` (line 221) - "TODO: Implement in gmb_scraper.py"
   - `HunterClientStub` (line 249) - "TODO: Implement in hunter.py"
   - `ProxyCurlStub` (line 283) - "TODO: Implement in proxycurl.py"

2. `resend.py` - Complete client, zero imports
3. `sentry_utils.py` - Utilities exist but Sentry configured in main.py

### 2.3 TODOs in Integrations
- `siege_waterfall.py:225` - Implement GMB scraper
- `siege_waterfall.py:253` - Implement Hunter client
- `siege_waterfall.py:290` - Implement ProxyCurl client

---

## 3. API FOLDER (`src/api/`)

### 3.1 File Inventory

| File | Purpose | Mounted in main.py |
|------|---------|-------------------|
| `main.py` | FastAPI app, middleware, exception handlers | - (entrypoint) |
| `dependencies.py` | Auth, rate limiting, client context | ✅ Used |
| **routes/** | | |
| `admin.py` | Admin operations, AI usage tracking | ✅ Mounted |
| `campaign_generation.py` | ICP → Campaign wizard API | ✅ Mounted |
| `campaigns.py` | Campaign CRUD, suggestions | ✅ Mounted |
| `crm.py` | HubSpot/Pipedrive/Close OAuth | ✅ Mounted |
| `customers.py` | Customer import for suppression | ✅ Mounted |
| `digest.py` | Daily digest endpoints | ✅ Mounted |
| `health.py` | Health check + readiness | ✅ Mounted |
| `leads.py` | Lead CRUD, enrichment triggers | ✅ Mounted |
| `linkedin.py` | LinkedIn seat management | ✅ Mounted |
| `meetings.py` | Meeting CRUD | ✅ Mounted |
| `onboarding.py` | ICP discovery flow trigger | ✅ Mounted |
| `patterns.py` | Conversion Intelligence patterns | ✅ Mounted |
| `pool.py` | Lead pool management | ✅ Mounted |
| `replies.py` | Reply handling endpoints | ✅ Mounted |
| `reports.py` | Campaign/client metrics | ✅ Mounted |
| `webhooks.py` | Inbound webhooks (Postmark/Twilio/etc) | ✅ Mounted |
| `webhooks_outbound.py` | Outbound webhook config | ✅ Mounted |

### 3.2 TODOs in API Routes
- `dependencies.py:397` - "TODO: Implement API-level rate limiting"
- `leads.py:693` - "TODO: Integrate with Prefect enrichment flow"
- `leads.py:751` - "TODO: Integrate with Prefect enrichment flow"
- `crm.py:371` - "TODO: Make frontend_url configurable"
- `webhooks.py:81` - "TODO: Implement custom signature verification"
- `webhooks.py:321` - "TODO: Log to Sentry in production"
- `admin.py:752` - "TODO: Implement ai_usage_logs table"
- `admin.py:786` - "TODO: Implement ai_usage_logs table"
- `admin.py:818` - "TODO: Implement Redis historical tracking"

---

## 4. SERVICES FOLDER (`src/services/`)

### 4.1 File Inventory (35 files)

| File | Purpose | Used By |
|------|---------|---------|
| `buyer_signal_service.py` | Platform buyer signals for scoring | scorer |
| `content_qa_service.py` | Pre-send content validation | outreach_flow |
| `conversation_analytics_service.py` | Reply thread analytics | CIS flows |
| `crm_push_service.py` | Push to HubSpot/Pipedrive/Close | crm_sync_flow |
| `customer_import_service.py` | CRM/CSV customer import | customers API |
| `deal_service.py` | Deal pipeline management | crm routes |
| `digest_service.py` | Daily digest generation | daily_digest_flow |
| `domain_capacity_service.py` | Domain send capacity | allocator |
| `domain_health_service.py` | Bounce/complaint monitoring | domain capacity |
| `domain_provisioning_service.py` | InfraForge domain setup | infra_provisioning_flow |
| `email_events_service.py` | Email engagement tracking | webhooks |
| `email_signature_service.py` | Email signature generation | email engine |
| `jit_validator.py` | Just-in-time lead validation | pool_assignment_flow |
| `lead_allocator_service.py` | Lead distribution to clients | pool flows |
| `lead_pool_service.py` | Central lead pool CRUD | pool flows |
| `linkedin_connection_service.py` | LinkedIn connection sync | linkedin_health_flow |
| `linkedin_health_service.py` | LinkedIn seat health | linkedin_health_flow |
| `linkedin_warmup_service.py` | LinkedIn warmup tracking | linkedin_health_flow |
| `meeting_service.py` | Meeting scheduling | meetings API |
| `persona_service.py` | Persona buffer management | persona_buffer_flow |
| `phone_provisioning_service.py` | Twilio number setup | voice engine |
| `recording_cleanup_service.py` | 90-day recording retention | recording_cleanup_flow |
| `reply_analyzer.py` | AI reply classification | reply_tasks |
| `resource_assignment_service.py` | Resource pool allocation | resource flows |
| `response_timing_service.py` | Response delay calculation | reply_tasks |
| `sdk_usage_service.py` | SDK brain usage logging | sdk agents |
| `send_limiter.py` | Test mode send limits | outreach |
| `sequence_generator_service.py` | Auto-generate sequences | campaign creation |
| `suppression_service.py` | Suppression list management | enrichment |
| `thread_service.py` | Conversation thread tracking | reply handling |
| `timezone_service.py` | Australian timezone lookup | outreach |
| `voice_retry_service.py` | Voice call retry scheduling | voice engine |
| `who_refinement_service.py` | ICP refinement from CIS | pattern learning |
| `__init__.py` | Comprehensive exports | ✅ All services exported |

### 4.2 Services __init__.py Assessment
**Status:** ✅ WELL MAINTAINED - All 35 services properly exported with clear phase annotations

---

## 5. ORCHESTRATION FOLDER (`src/orchestration/`)

### 5.1 Flows Inventory (27 flows)

| Flow File | Exported in __init__ | Scheduled | Called By |
|-----------|---------------------|-----------|-----------|
| `campaign_activation_flow.py` | ✅ | ❌ | onboarding API |
| `campaign_evolution_flow.py` | ❌ | Triggered | pattern_learning |
| `campaign_flow.py` | ✅ | ❌ | API trigger |
| `credit_reset_flow.py` | ❌ | ✅ Hourly | Cron |
| `crm_sync_flow.py` | ❌ | ✅ 6h | Cron |
| `daily_digest_flow.py` | ✅ | ✅ 7AM | Cron |
| `daily_pacing_flow.py` | ❌ | ✅ 7AM | Cron |
| `dncr_rewash_flow.py` | ❌ | ✅ Quarterly | Cron |
| `enrichment_flow.py` | ✅ | ✅ 2AM | Cron |
| `infra_provisioning_flow.py` | ❌ | ❌ | onboarding |
| `intelligence_flow.py` | ❌ | ❌ | onboarding |
| `lead_enrichment_flow.py` | ❌ | ❌ | API trigger |
| `linkedin_health_flow.py` | ❌ | ✅ 6AM | Cron |
| `monthly_replenishment_flow.py` | ❌ | Triggered | credit_reset |
| `onboarding_flow.py` | ❌ | ❌ | onboarding API |
| `outreach_flow.py` | ✅ | ✅ Hourly 8-18 | Cron |
| `pattern_backfill_flow.py` | ✅ | ✅ 4AM | Cron |
| `pattern_learning_flow.py` | ✅ | ✅ Sun 3AM | Cron |
| `persona_buffer_flow.py` | ✅ | ❌ | warmup_monitor |
| `pool_assignment_flow.py` | ✅ | ❌ | daily allocation |
| `pool_population_flow.py` | ❌ | ❌ | replenishment |
| `post_onboarding_flow.py` | ❌ | ❌ | onboarding |
| `recording_cleanup_flow.py` | ❌ | ✅ 3AM | Cron |
| `reply_recovery_flow.py` | ✅ | ✅ 6h | Cron |
| `stale_lead_refresh_flow.py` | ✅ | ❌ | daily_outreach_prep |
| `warmup_monitor_flow.py` | ✅ | ✅ 6AM | Cron |
| `__init__.py` | - | - | 16 flows exported |

### 5.2 Tasks Inventory

| Task File | Purpose | Used By |
|-----------|---------|---------|
| `enrichment_tasks.py` | Batch enrichment, Clay limits | enrichment flows |
| `outreach_tasks.py` | Send email/SMS/LI/voice/mail | outreach flows |
| `reply_tasks.py` | Process inbound replies | reply flows |
| `scoring_tasks.py` | Lead scoring with ALS | scoring flows |

### 5.3 Schedules
**File:** `scheduled_jobs.py`
**Status:** ✅ COMPREHENSIVE - 16 scheduled jobs covering all operational needs

---

## 6. ADDITIONAL FOLDERS

### 6.1 Agents (`src/agents/`)

| Subfolder/File | Purpose | Status |
|----------------|---------|--------|
| `base_agent.py` | Abstract agent base | ✅ Used |
| `cmo_agent.py` | Marketing orchestration AI | ✅ Exported |
| `content_agent.py` | Content generation AI | ✅ Exported |
| `icp_discovery_agent.py` | ICP extraction from website | ✅ Exported |
| `campaign_generation_agent.py` | Campaign wizard AI | ✅ Exported |
| `reply_agent.py` | Reply intent classification | ✅ Exported |
| **skills/** | 17 modular AI skills | ✅ Used by agents |
| **sdk_agents/** | 6 SDK brain agents | ✅ Used |
| **campaign_evolution/** | 4 CIS analyzer agents | ✅ Used |

### 6.2 Detectors (`src/detectors/`)
**Status:** ✅ ALL WIRED
- `WhoDetector` - Conversion pattern detection
- `WhatDetector` - Message pattern detection
- `WhenDetector` - Timing pattern detection
- `HowDetector` - Channel pattern detection
- `FunnelDetector` - Funnel stage detection
- `WeightOptimizer` - ALS weight optimization

### 6.3 Intelligence (`src/intelligence/`)
**Status:** ✅ USED
- `platform_priors.py` - Default scoring weights

### 6.4 Models (`src/models/`)
**Status:** ✅ 26 models, all SQLAlchemy ORM

---

## 7. DEPENDENCY ANALYSIS

### 7.1 Import Graph (Simplified)

```
LAYER 5 (API/Agents)
   │
   ├── api/routes/* → engines, services, models
   └── agents/* → engines, integrations, models
       │
LAYER 4 (Orchestration)
   │
   └── orchestration/flows/* → engines, services, integrations, models
       │
LAYER 3 (Engines/Services)
   │
   ├── engines/* → integrations, models
   └── services/* → integrations, models
       │
LAYER 2 (Integrations)
   │
   └── integrations/* → models, exceptions
       │
LAYER 1 (Models/Exceptions)
   │
   └── models/* → SQLAlchemy base only
```

### 7.2 Circular Import Risks
**None detected** - Layer boundaries are respected.

---

## 8. DEAD/UNUSED CODE SUMMARY

### 8.1 Completely Unused Files
| File | Reason |
|------|--------|
| `integrations/resend.py` | Zero imports anywhere |
| `integrations/sentry_utils.py` | Sentry configured directly in main.py |

### 8.2 Partially Used / Stub Code
| File | Issue |
|------|-------|
| `integrations/siege_waterfall.py` | Has 3 stubs, not wired to any flow |
| `engines/proxy_waterfall.py` | Only used internally, no flow integration |
| `integrations/elevenlabs.py` | Exported but not used in flows |
| `integrations/dataforseo.py` | Model fields exist but no flow calls DataForSEO |

### 8.3 Deprecated Code
| File | Reason |
|------|--------|
| `integrations/heyreach.py` | Only in reply_tasks, marked deprecated in TOOLS.md |

---

## 9. TODO/FIXME SUMMARY (13 Active Items)

| Location | Priority | Description |
|----------|----------|-------------|
| `engines/voice_agent_telnyx.py:565` | P2 | Implement Deepgram STT |
| `api/routes/leads.py:693,751` | P2 | Integrate with Prefect enrichment flow |
| `api/routes/admin.py:752,786,818` | P3 | Implement ai_usage_logs table |
| `api/routes/crm.py:371` | P4 | Make frontend_url configurable |
| `api/routes/webhooks.py:81` | P3 | Custom signature verification |
| `api/routes/webhooks.py:321` | P4 | Log to Sentry in production |
| `api/dependencies.py:397` | P3 | API-level rate limiting |
| `integrations/siege_waterfall.py:225` | P2 | Implement GMB scraper |
| `integrations/siege_waterfall.py:253` | P3 | Implement Hunter client |
| `integrations/siege_waterfall.py:290` | P3 | Implement ProxyCurl client |

---

## 10. RECOMMENDATIONS

### 10.1 Immediate Actions
1. **Clean up `integrations/__init__.py`** - Either export commonly-used clients (anthropic, redis, supabase) or document the direct-import pattern
2. **Wire or remove siege_waterfall.py** - It has 1100+ lines of code with stubs, no active use
3. **Remove resend.py and sentry_utils.py** - Dead code

### 10.2 Technical Debt
1. **DataForSEO Integration** - Model fields exist but enrichment flow doesn't call it
2. **HeyReach Deprecation** - Only used in reply_tasks, should be migrated to Unipile
3. **AI Usage Logging** - 3 TODOs reference missing `ai_usage_logs` table

### 10.3 Architecture Notes
- ✅ Layer boundaries well-maintained
- ✅ Services comprehensively exported
- ✅ Orchestration schedules complete
- ⚠️ Engines __init__.py only exports BaseEngine (intentional for direct imports)
- ⚠️ Integrations __init__.py inconsistent (6 exported, 24 used directly)

---

*Audit completed by RESEARCHER-CODE subagent*
