# HANDOFF.md — Session Continuity Document
## Agency OS Current State

**Last Updated:** 2026-02-05 09:03 UTC
**Last Session:** FCO-002 + FCO-003 Ratified, Migration 055 Complete, SDK Deprecated

---

## 🔴 CRITICAL CONTEXT

### The Siege Waterfall is Now Doctrine
Agency OS has pivoted from "Renting Data" (Apollo SPOF) to "Manufacturing Intel" via the 5-Tier Siege Waterfall:

| Tier | Source | Cost (AUD) | Gate |
|------|--------|------------|------|
| 1 | ABN Bulk | FREE | Always |
| 2 | GMB/Ads | $0.006 | Always |
| 3 | Hunter.io | $0.012 | Email needed |
| 4 | LinkedIn Pulse | $0.024 | Warm+ leads |
| 5 | Identity Gold | $0.45 | **ALS ≥ 85 ONLY** |

**Key files:**
- `AGENCY_OS_STRATEGY.md` — Master strategy document
- `src/engines/waterfall_verification_worker.py` — Tiers 1-4
- `src/engines/identity_escalation.py` — Tier 5 + Director Hunt

---

## 📊 IGNITION TIER ECONOMICS (Post FCO-002)

| Metric | Current | Post FCO-001+002 |
|--------|---------|------------------|
| Leads/month | 1,250 | 1,250 |
| Revenue | $2,500 AUD | $2,500 AUD |
| Fixed costs | $722/mo | $575/mo |
| Variable costs | $567/mo | $173/mo |
| **Net Profit** | **$1,211/mo** | **$1,752/mo** |
| **Margin** | **48%** | **70%** ✅ |

**Key change:** SDK costs dropped from $400/mo to $6/mo (Smart Prompts replaces SDK)

**Full analysis:** `docs/IGNITION_FULL_COST_ANALYSIS.md`, `memory/2026-02-05-fco-002-decision.md`

---

## ✅ COMPLETED THIS SESSION

### FCO-002: SDK Deprecation (RATIFIED)
- [x] **Decision:** Smart Prompts replaces SDK for content generation
- [x] **SDK Enrichment:** DEPRECATED — Siege Waterfall provides data
- [x] **SDK Email/Voice KB:** DEPRECATED — Smart Prompts handles
- [x] **SDK Objection Handling:** KEPT — 10% Claude routing
- [x] **Margin Impact:** 48% → 70% (Ignition tier)
- [x] **Cost Savings:** ~$385/mo

### Infrastructure
- [x] Siege Waterfall engines (waterfall_verification_worker.py, identity_escalation.py)
- [x] Proxy Waterfall engine (proxy_waterfall.py) — 60% scraping cost reduction
- [x] Voice AI Raw Stack (voice_agent_telnyx.py) — $0.09/min vs $2.00/min
- [x] Australian Personality Prompt (VOICE_AI_PERSONALITY.md)

### Documentation
- [x] AGENCY_OS_STRATEGY.md — Siege Waterfall doctrine
- [x] NATIONWIDE_ROLLOUT.md — AU expansion strategy
- [x] FIXED_COSTS_BREAKDOWN.md — Monthly infrastructure costs
- [x] IGNITION_FULL_COST_ANALYSIS.md — Code-verified cost audit
- [x] PREFECT_SPOT_MIGRATION.md — Bulk flow migration plan
- [x] COLD_EMAIL_INFRASTRUCTURE_FINAL_REPORT.md — Forge Stack validation

### Research
- [x] Lusha/Kaspr evaluation — Kaspr wins for AU mobiles
- [x] ACMA compliance — DNCR, calling hours, SMS alpha tags

---

## ⏳ PENDING (Dave to Execute)

### SQL Migrations
```bash
# In Supabase SQL Editor:
# 1. Run migration 055_waterfall_enrichment_architecture.sql
# 2. Run audit log INSERT statements (6 pending from session)
```

### External Actions
- [ ] Register SMS alpha tags with Twilio Trust Hub (deadline: July 2026)
- [ ] Create Telnyx account with Sydney PoP
- [ ] Test Kaspr free tier for AU mobile accuracy

---

## 🔧 NEXT SESSION PRIORITIES

### FCO-002: SDK Deprecation (RATIFIED 2026-02-05)
**Target: 70% margin**

1. **Remove SDK Enrichment calls** — Scout engine uses Siege Waterfall data only
2. **Update content.py** — Smart Prompts for ALL leads (not just non-Hot)
3. **Update voice.py** — SMART_VOICE_KB_PROMPT replaces SDK voice KB
4. **Deprecate SDK agents:**
   - `sdk_agents/enrichment_agent.py`
   - `sdk_agents/email_agent.py`
   - `sdk_agents/voice_kb_agent.py`
5. **Keep SDK objection handling** — 10% Claude routing for complex objections

### FCO-001: Infrastructure Optimization
- Tag Prefect flows with `tier: bulk` / `tier: realtime`
- Provision AWS Spot instance for bulk processing

### Build Missing Integrations
1. `src/integrations/gmb_scraper.py` — DIY Google Maps scraper (replaces Apify) ⭐ NEW
2. `src/integrations/hunter.py` — Email verification client
3. `src/integrations/proxycurl.py` — LinkedIn enrichment client
4. `src/integrations/kaspr.py` — Mobile enrichment client
5. `src/integrations/abn.py` — ABN Bulk Extract ingestion

### Merge Pending Branches
- `feature/heygen-integration` — Maya video generation

---

## 🚫 REJECTED INFRASTRUCTURE (Do Not Revisit)

| Proposal | Reason |
|----------|--------|
| SMTP Pinging | Sender reputation risk > $3/mo savings |
| Self-hosted Postal | Deliverability is existential |
| Vapi | $1,910/1000min markup eliminated |
| Titan/Neo Email | Forge Stack validated as optimal (comprehensive research 2026-02-05) |
| Smartlead/Instantly | More expensive than Forge when including infrastructure |
| DIY Warmup | No open-source warmup tools exist; Gmail pattern detection too sophisticated |

## ✅ VALIDATED INFRASTRUCTURE (Do Not Change)

| Component | Tool | Reason |
|-----------|------|--------|
| Email Domains | InfraForge | Automated DNS, DKIM/SPF/DMARC |
| Email Warmup | WarmForge | 200K+ account warmup network |
| Email Sending | Salesforge | Native integration, no hidden costs |
| Email Trust | Custom domains (Infraforge) | Branded domains > shared for high-ticket B2B |

**Research:** `research/COLD_EMAIL_INFRASTRUCTURE_FINAL_REPORT.md` (8 agents, 15 competitors analyzed)

---

## 📁 KEY FILES REFERENCE

### Strategy
- `AGENCY_OS_STRATEGY.md` — Master strategy (Siege Waterfall + FCO)
- `MEMORY.md` — Operational memory

### Engines (src/engines/)
- `waterfall_verification_worker.py` — ABN+GMB+Hunter+ZeroBounce
- `identity_escalation.py` — Director Hunt + Mobile enrichment
- `proxy_waterfall.py` — Datacenter→ISP→Residential
- `voice_agent_telnyx.py` — Raw Voice AI stack

### Docs
- `docs/IGNITION_FULL_COST_ANALYSIS.md` — Cost audit
- `docs/VOICE_AI_PERSONALITY.md` — Aussie vernacular
- `docs/NATIONWIDE_ROLLOUT.md` — AU expansion
- `docs/FIXED_COSTS_BREAKDOWN.md` — Infrastructure costs

---

## 🎯 SUCCESS METRICS

| Metric | Target | Current |
|--------|--------|---------|
| First paying client | 1 | 0 |
| MRR | $8K (quit job) | $0 |
| Ignition margin | >60% | 64.2% ✅ |
| Voice AI latency | <200ms | Designed ✅ |
| DNCR compliance | 100% | Pending |

---

## ⚠️ CONTEXT FOR NEW SESSION

If starting a new session, read:
1. This file (HANDOFF.md)
2. `AGENCY_OS_STRATEGY.md` — Full doctrine
3. `memory/daily/2026-02-05.md` — Detailed session log

**Do not assume Apollo workflow.** Siege Waterfall is doctrine.

---

*Handoff prepared: 2026-02-05 01:58 UTC | Elliot (CTO)*
