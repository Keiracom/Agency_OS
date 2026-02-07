# GAP AUDIT: Agency OS Documentation vs Code

**Generated:** 2026-02-06  
**Auditor:** RESEARCHER-GAPS (Claude Subagent)  
**Sources Analyzed:**
- `PROJECT_BLUEPRINT.md`
- `AGENCY_OS_STRATEGY.md`
- `docs/phases/PHASE_INDEX.md`
- `src/` directory (180+ Python files)
- `docs/specs/` directory (70+ spec files)

---

## Executive Summary

| Category | Count |
|----------|-------|
| **Documented but NOT Built** | 17 items |
| **Built but NOT Documented** | 14 items |
| **Partially Complete** | 8 items |

**Critical Gaps:** Siege Waterfall missing 2 of 5 tier clients (Hunter.io, Proxycurl)

---

## 1. DOCUMENTED BUT NOT BUILT

### 1.1 Missing Integration Clients (Critical)

| Integration | Documented In | Expected File | Status |
|-------------|---------------|---------------|--------|
| **Hunter.io** | AGENCY_OS_STRATEGY.md (Tier 3) | `src/integrations/hunter.py` | ❌ Missing |
| **Proxycurl** | AGENCY_OS_STRATEGY.md (Tier 4) | `src/integrations/proxycurl.py` | ❌ Missing |
| **Lusha** | identity_escalation.py comment | `src/integrations/lusha.py` | ❌ Missing (Kaspr fallback) |

**Impact:** Siege Waterfall Tiers 3-4 cannot execute without these clients.

### 1.2 Phase 22: Marketing Automation (Planned)

| Item | Description | Expected File |
|------|-------------|---------------|
| HeyGen Integration | AI video generation | `src/integrations/heygen.py` |
| Buffer Integration | Social media scheduling | `src/integrations/buffer.py` |
| Marketing Flow | Prefect automation | `src/orchestration/flows/marketing_automation_flow.py` |

**Status:** 📋 Planned post-launch

### 1.3 Phase 23: Platform Intelligence (Planned)

| Item | Description | Expected File |
|------|-------------|---------------|
| Platform Patterns Table | Cross-client learning | Migration `023_platform_intelligence.sql` |
| Platform Learning Engine | Weight aggregation | `src/engines/platform_learning.py` |
| 18 total tasks | See PHASE_23_PLATFORM_INTEL.md | — |

**Status:** 📋 Planned (requires 10+ clients with data)

### 1.4 Missing Integration Specs

| Integration | Code Exists | Spec Exists |
|-------------|-------------|-------------|
| Hunter.io | ❌ | ❌ |
| Proxycurl | ❌ | ❌ |
| Kaspr | ✅ `src/integrations/kaspr.py` | ❌ |
| Unipile | ✅ `src/integrations/unipile.py` | ❌ |
| Salesforge | ✅ `src/integrations/salesforge.py` | ❌ |
| Warmforge | ✅ `src/integrations/warmforge.py` | ❌ |

### 1.5 Infrastructure Items (Action Items from AGENCY_OS_STRATEGY.md)

| Item | Description | Status |
|------|-------------|--------|
| Migration 055 | Waterfall enrichment architecture | ❓ Not executed in Supabase |
| SMS Alpha Tags | Twilio Trust Hub registration | ❌ Due July 2026 |
| DNCR SOAP API | Full SOAP integration | ❌ Partial (REST wrapper only) |
| ABN Bulk Extract | data.gov.au ingestion pipeline | ❌ Not complete |
| Prefect Spot Instances | AWS bulk processing | 📋 Planned |

### 1.6 Maya Digital Employee UI

| Item | Documented In | Status |
|------|---------------|--------|
| Hologram UI component | PROJECT_BLUEPRINT.md | ❌ Not built |
| Pre-rendered onboarding video | PROJECT_BLUEPRINT.md | ❌ Not produced |
| Daily update TTS | PROJECT_BLUEPRINT.md | ❌ Not wired |

**Note:** Maya exists as voice personality in `voice_agent_telnyx.py` but no dashboard UI.

---

## 2. BUILT BUT NOT DOCUMENTED

### 2.1 Undocumented Engines

| File | Purpose | In ENGINE_INDEX.md? |
|------|---------|---------------------|
| `src/engines/campaign_suggester.py` | AI campaign suggestions | ❌ |
| `src/engines/client_intelligence.py` | Client learning system | ❌ |
| `src/engines/timing.py` | Send time optimization | ❌ |
| `src/engines/proxy_waterfall.py` | Datacenter→ISP→Residential | ❌ |
| `src/engines/voice_agent_telnyx.py` | Telnyx voice implementation | ❌ |

### 2.2 Undocumented Integrations

| File | Purpose | In INTEGRATION_INDEX.md? |
|------|---------|--------------------------|
| `src/integrations/kaspr.py` | Tier 5 mobile enrichment | ❌ |
| `src/integrations/siege_waterfall.py` | Orchestrates 5-tier pipeline | ❌ |
| `src/integrations/salesforge.py` | Cold email sending | ❌ (mentioned but no spec) |
| `src/integrations/warmforge.py` | Email warmup | ❌ (mentioned but no spec) |
| `src/integrations/unipile.py` | LinkedIn automation | ❌ |
| `src/integrations/abn_client.py` | ABN Bulk Extract API | ❌ |
| `src/integrations/gmb_scraper.py` | Google Maps business data | ❌ |

### 2.3 Undocumented Services Layer

**No documentation index exists for 35+ service files:**

| Sample Services | Purpose |
|-----------------|---------|
| `lead_pool_service.py` | Lead pool operations |
| `domain_health_service.py` | Email domain monitoring |
| `jit_validator.py` | Just-in-time validation |
| `crm_push_service.py` | CRM synchronization |
| `customer_import_service.py` | Customer data import |
| `linkedin_connection_service.py` | LinkedIn operations |
| ... | (30+ more) |

**Recommendation:** Create `docs/specs/services/SERVICE_INDEX.md`

### 2.4 Undocumented Detectors

| File | Purpose |
|------|---------|
| `src/detectors/who_detector.py` | Contact targeting |
| `src/detectors/what_detector.py` | Offer optimization |
| `src/detectors/when_detector.py` | Timing patterns |
| `src/detectors/how_detector.py` | Channel selection |
| `src/detectors/funnel_detector.py` | Funnel stage detection |
| `src/detectors/weight_optimizer.py` | ALS weight learning |

**Note:** These are Phase 16 Conversion Intelligence, mentioned in specs but no dedicated index.

---

## 3. PARTIALLY COMPLETE

### 3.1 Siege Waterfall Pipeline

| Tier | Name | Client Code | Documentation |
|------|------|-------------|---------------|
| 1 | ABN Bulk | ✅ `abn_client.py` | ✅ AGENCY_OS_STRATEGY.md |
| 2 | GMB/Ads Signals | ✅ `gmb_scraper.py` | ✅ |
| 3 | Hunter.io | ❌ **MISSING** | ✅ |
| 4 | LinkedIn Pulse | ❌ **MISSING** (Proxycurl) | ✅ |
| 5 | Identity Gold | ✅ `kaspr.py` | ✅ |

**Orchestration:** `siege_waterfall.py` + `waterfall_verification_worker.py` exist but cannot call Tiers 3-4.

### 3.2 E2E Testing (Phase 21)

| Journey | Status |
|---------|--------|
| J0: Infrastructure | 🟡 In Progress |
| J1: Onboarding | 🟡 In Progress |
| J2: Campaign | 🟡 In Progress |
| J3-J10 | Various states |

**Docs exist:** `docs/e2e/sources_ref/J*.md`

### 3.3 Frontend Components

| Location | Status |
|----------|--------|
| `frontend/design/prototype/components/` | ✅ 50+ TSX files exist |
| Wiring to backend | 🟡 Phase 20 incomplete |
| Production deployment | ❌ Still prototype |

### 3.4 Voice AI Implementation

| Component | Documented | Built |
|-----------|------------|-------|
| Vapi orchestration | ✅ | ✅ `vapi.py` |
| Telnyx telephony | ✅ | ✅ `twilio.py` (but also `voice_agent_telnyx.py`) |
| Cartesia TTS | ✅ | ❓ Via Vapi |
| Voice personality | ✅ | ✅ In `voice_agent_telnyx.py` |

**Confusion:** Docs mention Telnyx, code has both Twilio and Telnyx implementations.

### 3.5 DNCR Integration

| Component | Status |
|-----------|--------|
| REST client | ✅ `dncr.py` exists |
| SOAP API integration | ❌ Action item incomplete |
| Redis caching | ✅ Implemented |
| 30-day rewash flow | ✅ `dncr_rewash_flow.py` exists |

---

## 4. FILE NAMING ISSUES

| Issue | Current | Expected |
|-------|---------|----------|
| Phase 20 spec | `PHASE_21_UI_OVERHAUL.md` | `PHASE_20_UI_WIRING.md` |
| Phase 18/19 confusion | Two PHASE_18 files exist | Consolidate |

---

## 5. PRIORITY RECOMMENDATIONS

### Critical (Blocks Launch)
1. **Build Hunter.io client** - Required for Siege Waterfall Tier 3
2. **Build Proxycurl client** - Required for Siege Waterfall Tier 4
3. **Execute Migration 055** - Waterfall architecture DB changes

### High Priority (Technical Debt)
4. Create integration specs for: Kaspr, Unipile, Salesforge, Warmforge
5. Create SERVICE_INDEX.md documenting 35+ services
6. Update ENGINE_INDEX.md with 5 missing engines

### Medium Priority (Post-Launch)
7. Maya UI components
8. Phase 22 Marketing Automation
9. Rename misnamed phase files

### Low Priority (Future)
10. Phase 23 Platform Intelligence (requires client data)
11. Lusha fallback integration

---

## 6. METRICS

| Category | Files |
|----------|-------|
| Total src/*.py files | 180+ |
| Documented engines | 12 |
| Actual engines | 17 |
| Documented integrations | 16 |
| Actual integrations | 28 |
| Services (undocumented) | 35 |
| Detectors (undocumented) | 6 |

---

*Generated by RESEARCHER-GAPS subagent*
