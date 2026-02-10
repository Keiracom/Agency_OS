# System Overhaul: SIEGE

**Created:** 2026-02-05
**Status:** PLANNED — Awaiting Dave's Sign-Off
**Reference:** `Agency_OS/INTEGRATION_MASTER_PLAN.md` (full details)

---

## Mission

Replace "Rented Data" architecture with "Manufacturing Intel" — removing Apollo, Apify, and SDK dependencies in favor of the Siege Waterfall + Autonomous Browser + Smart Prompts stack.

---

## What We're REMOVING

| System | Monthly Cost | Files | Replacement |
|--------|--------------|-------|-------------|
| Apollo | ~$150 | 12 | Siege Waterfall (5-Tier) |
| Apify | ~$15-50 | 15 | Autonomous Stealth Browser |
| SDK Enrichment | ~$150 | 3 agents | Siege Waterfall data |
| SDK Email | ~$85 | content.py | Smart Prompts |
| SDK Voice KB | ~$150 | voice.py | Smart Prompts |
| Twilio Voice | Variable | voice.py | Telnyx + Groq/Claude |
| **Total Savings** | **~$550/mo** | **21 files** | |

---

## What We're BUILDING

### New Integrations
| File | Purpose | Tier |
|------|---------|------|
| `siege_waterfall.py` | Unified 5-tier enrichment interface | All |
| `abn_client.py` | data.gov.au (3.5M AU businesses) | 1 |
| `gmb_scraper.py` | Google Maps scraping (FCO-003) | 2 |
| `kaspr.py` | Mobile enrichment (ALS 85+) | 5 |
| `telnyx.py` | AU mobile voice | Voice |
| `cartesia.py` | TTS (10x cheaper than ElevenLabs) | Voice |

### Siege Waterfall Tiers
| Tier | Name | Source | Cost/Lead |
|------|------|--------|-----------|
| 1 | ABN Bulk | data.gov.au | FREE |
| 2 | GMB/Ads Signals | Google Maps + Meta | $0.006 |
| 3 | Email Verification | Hunter.io | $0.012 |
| 4 | LinkedIn Pulse | Proxycurl | $0.024 |
| 5 | Identity Gold | Kaspr/Lusha | $0.45 (ALS 85+ only) |

**Weighted Average:** $0.105/lead (vs Apollo $0.50+)

---

## Files to Modify (21 Total)

### Apollo Touchpoints (12)
| File | Effort | Change |
|------|--------|--------|
| `src/integrations/apollo.py` | L | Deprecate → Siege facade |
| `src/engines/scout.py` | M | Replace enrichment calls |
| `src/engines/icp_scraper.py` | M | Replace company lookup |
| `src/orchestration/flows/pool_population_flow.py` | L | Switch to ABN seeding |
| `src/orchestration/flows/post_onboarding_flow.py` | L | Switch to Siege |
| `src/orchestration/tasks/enrichment_tasks.py` | M | Update to waterfall |
| `src/services/lead_pool_service.py` | S | Update ID references |
| `src/agents/icp_discovery_agent.py` | S | Passes through |
| `src/agents/skills/portfolio_fallback.py` | S | Remove Apollo refs |
| `src/config/settings.py` | S | Remove apollo_api_key |
| `tests/test_engines/test_scout.py` | M | Update mocks |
| `tests/test_e2e/test_full_flow.py` | M | Update integration |

### Apify Touchpoints (15)
| File | Effort | Change |
|------|--------|--------|
| `src/integrations/apify.py` | L | Deprecate → Autonomous Browser |
| `src/engines/scout.py` | M | Replace LinkedIn scraping |
| `src/engines/icp_scraper.py` | L | Replace website waterfall |
| `src/engines/client_intelligence.py` | L | Replace all social scraping |
| `src/orchestration/flows/stale_lead_refresh_flow.py` | M | Use Proxycurl |
| `src/agents/icp_discovery_agent.py` | S | Passes through |
| `src/agents/skills/social_enricher.py` | M | Autonomous Browser |
| `src/agents/skills/social_profile_discovery.py` | M | Brave Search API |
| `src/agents/skills/research_skills.py` | M | Autonomous Browser |
| `src/agents/sdk_agents/sdk_tools.py` | S | Remove Apify refs |
| `src/config/settings.py` | S | Remove apify_api_key |
| `tests/live/config.py` | S | Update validation |
| `tests/test_engines/test_scout.py` | M | Update mocks |
| `tests/test_engines/test_scraper_waterfall.py` | M | Update tests |
| `scripts/check_env.py` | S | Update validation |

### SDK Deprecation (FCO-002)
| File | Change |
|------|--------|
| `src/engines/content.py` | Route to Smart Prompts only |
| `src/engines/voice.py` | Use Smart Prompts for KB |
| `src/agents/sdk_agents/enrichment_agent.py` | DELETE |
| `src/agents/sdk_agents/email_agent.py` | DELETE |
| `src/agents/sdk_agents/voice_kb_agent.py` | DELETE |
| `src/agents/sdk_agents/sdk_eligibility.py` | KEEP (objection routing) |

---

## Timeline (6 Weeks)

| Week | Phase | Focus |
|------|-------|-------|
| 1 | Foundation | Migrations, new integrations (siege_waterfall.py, gmb_scraper.py, kaspr.py) |
| 2 | Enrichment | Apollo → Siege Waterfall (scout.py, pool flows) |
| 2-3 | Scraping | Apify → Autonomous Browser (icp_scraper.py, client_intelligence.py) |
| 3 | SDK | Smart Prompts replaces SDK (content.py, voice.py) |
| 3-4 | Voice | Telnyx + Groq/Claude hybrid |
| 4-5 | Frontend | Onboarding, Maya, Campaign allocation |
| 5-6 | Cleanup | Remove old systems, validate, E2E test |

---

## Margin Impact

**Ignition Tier ($2,500/mo):**
| Metric | Before | After |
|--------|--------|-------|
| Total Burn | $1,289 | $748 |
| Net Profit | $1,211 | $1,752 |
| Margin | 48% | **70%** |

---

## 3-Agent Execution System

Every task in SIEGE runs through this pipeline:

### Agent Roles

| Agent | Role | Output |
|-------|------|--------|
| **BUILDER** | Writes the code/migration | PR or file changes |
| **AUDITOR** | Reviews for correctness, governance, edge cases | Pass/Fail + issues list |
| **FIXER** | Addresses issues found by Auditor | Fixed PR |

### Workflow

```
Task Assignment
      ↓
  [BUILDER]
   Creates implementation
      ↓
  [AUDITOR]  
   Reviews output
      ↓
   Pass? ──→ ✅ Merge-ready
      │
      No
      ↓
  [FIXER]
   Addresses issues
      ↓
  [AUDITOR] (re-review)
      ↓
   Pass? ──→ ✅ Merge-ready
```

### Agent Spawn Commands

```bash
# Builder: Creates new integration
sessions_spawn task="BUILDER: Create src/integrations/siege_waterfall.py..." label="siege-builder"

# Auditor: Reviews builder output
sessions_spawn task="AUDITOR: Review siege_waterfall.py for..." label="siege-auditor"

# Fixer: Addresses audit findings
sessions_spawn task="FIXER: Address issues [1,2,3] in siege_waterfall.py..." label="siege-fixer"
```

### Quality Gates (Auditor Checklist)

- [ ] LAW I: Read relevant skill/doc before implementation
- [ ] LAW II: All costs in $AUD
- [ ] LAW IV: Code >20 lines has conceptual summary
- [ ] LAW VI: MCP-first for external services
- [ ] Tests pass
- [ ] No hardcoded credentials
- [ ] Error handling with retries
- [ ] Type hints + docstrings
- [ ] Matches Siege Waterfall tier spec

### Example: Building GMB Scraper (FCO-003)

**Round 1:**
1. BUILDER creates `src/integrations/gmb_scraper.py`
2. AUDITOR reviews → finds: missing retry logic, no $AUD cost tracking
3. FIXER adds retry + cost tracking
4. AUDITOR re-reviews → ✅ Pass

**Round 2:**
1. BUILDER updates `src/engines/icp_scraper.py` to use GMB scraper
2. AUDITOR reviews → finds: old Apify import still present
3. FIXER removes Apify import
4. AUDITOR re-reviews → ✅ Pass

---

## Blockers Before Start

1. **Dave:** Create Telnyx account + ID verification
2. **Dave:** Run migration 055 in Supabase
3. **Dave:** Sign off on master plan

---

## Governance Events

| Event | Description | Status |
|-------|-------------|--------|
| FCO-001 | Fixed-Cost Fortress Phase 1 | ✅ $34/mo saved |
| FCO-002 | SDK Deprecation + Smart Prompts | ✅ RATIFIED |
| FCO-003 | Apify Replacement (GMB Scraper) | ✅ RATIFIED |
| **SIEGE** | System Overhaul (this plan) | 📋 PLANNED |

---

*Last Updated: 2026-02-05 23:44 UTC*
