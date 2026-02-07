# SYNC ALIGNMENT: Docs ↔ Code ↔ Decisions

**Generated:** 2026-02-06 01:45 UTC
**Purpose:** Everything that's out of sync and needs fixing
**Source:** 5 research agent audits

---

## CRITICAL MISALIGNMENTS (Fix Immediately)

### 1. Siege Waterfall Not Wired

| Issue | Current State | Required State |
|-------|---------------|----------------|
| siege_waterfall.py exists | 1100 lines of code | Wire to flows |
| scout.py uses Apollo | `from src.integrations.apollo import` | Use siege_waterfall |
| icp_scraper.py uses Apollo | `from src.integrations.apollo import` | Use siege_waterfall |
| client_intelligence.py uses Apify | `from src.integrations.apify import` | Use gmb_scraper |

**Files to Update:**
- [ ] `src/engines/scout.py` — Replace Apollo with SiegeWaterfall
- [ ] `src/engines/icp_scraper.py` — Replace Apollo with SiegeWaterfall
- [ ] `src/engines/client_intelligence.py` — Replace Apify with GMBScraper
- [ ] `src/orchestration/flows/lead_enrichment_flow.py` — Use SiegeWaterfall
- [ ] `src/orchestration/flows/intelligence_flow.py` — Use GMBScraper

### 2. Missing Integration Clients

| Client | Required For | Status |
|--------|--------------|--------|
| `hunter.py` | Siege Tier 3 (email finding) | ❌ Create |
| `proxycurl.py` | Siege Tier 4 (LinkedIn enrichment) | ❌ Create |

**Files to Create:**
- [ ] `src/integrations/hunter.py` — Hunter.io email finder
- [ ] `src/integrations/proxycurl.py` — LinkedIn profile enrichment

### 3. Migration 055 Not Applied

| Issue | Action |
|-------|--------|
| `055_waterfall_enrichment_architecture.sql` exists | Apply to production Supabase |

### 4. Finance Docs Outdated

| Document | Issue | Fix |
|----------|-------|-----|
| `SDK_FINAL_PL_MODEL.md` | Shows 31.8% Dominance margin | Update with post-Siege/FCO-002 margins |
| `FINANCE_AUDIT_COMPLETE.md` | References old SDK costs | Add note about MARGIN_RECALCULATION_POST_SIEGE.md |
| All SDK_OPTION_*.md files | SDK now deprecated | Add deprecation header |

**Files to Update:**
- [ ] `docs/finance/SDK_FINAL_PL_MODEL.md` — Add deprecation notice, reference new margins
- [ ] `docs/finance/SDK_OPTION_A_TIER_CAPS.md` — Add deprecation notice
- [ ] `docs/finance/SDK_OPTION_C_SELECTIVE_USAGE.md` — Add deprecation notice
- [ ] `docs/finance/SDK_OPTION_D_SERVICE_TIERS.md` — Add deprecation notice
- [ ] `docs/finance/SDK_MARGIN_ANALYSIS_EXECUTIVE_SUMMARY.md` — Add deprecation notice

---

## HIGH PRIORITY MISALIGNMENTS

### 5. Infrastructure Issues

| Issue | Current State | Fix |
|-------|---------------|-----|
| Railway token expired | MCP returns "Not Authorized" | Refresh Railway_Token in .env |
| Prefect worker offline | `local-pool` is OFFLINE | Restart worker |
| 3 crashed flows | daily-learning-scrape | Investigate and fix |
| 10 paused deployments | Various Prefect flows | Review and unpause needed ones |

### 6. Dead/Deprecated Code Still Active

| File | Status | Action |
|------|--------|--------|
| `src/integrations/apollo.py` | Still active, should be deprecated | Add deprecation warning, phase out |
| `src/integrations/apify.py` | Still active, should be deprecated | Add deprecation warning, phase out |
| `src/integrations/heyreach.py` | Deprecated but used in reply_tasks | Remove from reply_tasks |
| `src/integrations/resend.py` | Zero imports | Delete or document why kept |
| `src/integrations/sentry_utils.py` | Zero imports | Delete (Sentry in main.py) |

### 7. Unipile 401 Error

| Issue | Impact | Fix |
|-------|--------|-----|
| Unipile returning 401 | LinkedIn outreach broken | Fix auth or replace provider |

---

## DOCUMENTATION GAPS

### 8. Built But Not Documented

| Item | File Exists | Needs Doc |
|------|-------------|-----------|
| Kaspr integration | `src/integrations/kaspr.py` | Create spec |
| Siege Waterfall | `src/integrations/siege_waterfall.py` | Create spec |
| ABN Client | `src/integrations/abn_client.py` | Create spec |
| GMB Scraper | `src/integrations/gmb_scraper.py` | Create spec |
| Unipile | `src/integrations/unipile.py` | Create spec |
| Salesforge | `src/integrations/salesforge.py` | Create spec |
| Warmforge | `src/integrations/warmforge.py` | Create spec |

**Files to Create:**
- [ ] `docs/specs/integrations/SIEGE_WATERFALL.md`
- [ ] `docs/specs/integrations/KASPR.md`
- [ ] `docs/specs/integrations/ABN_CLIENT.md`
- [ ] `docs/specs/integrations/GMB_SCRAPER.md`
- [ ] `docs/specs/integrations/UNIPILE.md`
- [ ] `docs/specs/integrations/SALESFORGE.md`
- [ ] `docs/specs/integrations/WARMFORGE.md`

### 9. Missing Service Documentation

| Issue | Action |
|-------|--------|
| 35 services exist, no SERVICE_INDEX.md | Create docs/specs/services/SERVICE_INDEX.md |

### 10. Missing Engine Documentation

| Engine | In ENGINE_INDEX.md? |
|--------|---------------------|
| campaign_suggester.py | ❌ Add |
| client_intelligence.py | ❌ Add |
| timing.py | ❌ Add |
| proxy_waterfall.py | ❌ Add |
| voice_agent_telnyx.py | ❌ Add |

---

## CODEBASE ALIGNMENT

### 11. Integration Exports

| Issue | Fix |
|-------|-----|
| Only 6 integrations exported in `__init__.py` | Export all used integrations |
| anthropic, redis, supabase used everywhere but not exported | Add to exports |

**File to Update:**
- [ ] `src/integrations/__init__.py` — Export all actively used integrations

### 12. Engine Exports

| Issue | Fix |
|-------|-----|
| Only `BaseEngine` exported | Export all engines used by flows |

**File to Update:**
- [ ] `src/engines/__init__.py` — Export all engines

### 13. Active TODOs in Code

| Location | TODO |
|----------|------|
| `voice_agent_telnyx.py:565` | Implement Deepgram STT |
| `siege_waterfall.py:225` | GMB scraper stub |
| `siege_waterfall.py:253` | Hunter client stub |
| `siege_waterfall.py:290` | ProxyCurl client stub |

---

## BUFFER/WARMUP GAPS

### 14. Email Infrastructure Buffer

| Resource | Required | Current | Gap |
|----------|----------|---------|-----|
| Warmed domains | 10+ | 0 | 10 |
| Warmed mailboxes | 30+ | ~3 | 27+ |
| AU phone numbers | 10 | 0 | 10 |

**Actions Required:**
- [ ] Purchase 10+ domains via InfraForge
- [ ] Start warmup via WarmForge
- [ ] Provision AU phone numbers via Telnyx

---

## PRICING/TIER INCONSISTENCIES

### 15. Velocity Tier Price

| Document | Price |
|----------|-------|
| Some buyer guides | $4,000/mo |
| Other docs | $5,000/mo |
| PROJECT_BLUEPRINT | $5,000/mo |

**Decision Resolved (Feb 2026):** Velocity price confirmed at $4,000/mo

---

## SUMMARY: TOTAL TASKS

| Category | Count |
|----------|-------|
| Critical code changes | 7 files |
| Files to create (integrations) | 2 files |
| Migration to apply | 1 |
| Deprecated code to clean | 5 files |
| Docs to create | 8 files |
| Docs to update | 5 files |
| Infrastructure fixes | 4 items |
| Buffer seeding | 3 items |
| **TOTAL TASKS** | **~35 tasks** |

---

## EXECUTION ORDER

1. **Fix Infrastructure** (15 min)
   - Refresh Railway token
   - Restart Prefect worker

2. **Apply Migration 055** (5 min)

3. **Create Missing Integrations** (4 hours)
   - hunter.py
   - proxycurl.py

4. **Wire Siege Waterfall** (4 hours)
   - Update scout.py
   - Update icp_scraper.py
   - Update client_intelligence.py
   - Update flows

5. **Deprecate Old Code** (1 hour)
   - Add warnings to apollo.py, apify.py
   - Remove heyreach from reply_tasks
   - Delete dead code

6. **Update Finance Docs** (30 min)
   - Add deprecation notices
   - Reference new margin calculation

7. **Create Missing Docs** (2 hours)
   - Integration specs
   - SERVICE_INDEX.md
   - ENGINE_INDEX updates

8. **Fix Unipile 401** (1 hour)
   - Debug or replace

9. **Seed Buffers** (Ongoing)
   - Purchase domains
   - Start warmup
   - Provision phones

---

*This document supersedes individual audit files for action planning.*
*All items traced back to: DOCS_AUDIT, CODE_AUDIT, GAP_AUDIT, INFRA_AUDIT, FINANCE_AUDIT*
