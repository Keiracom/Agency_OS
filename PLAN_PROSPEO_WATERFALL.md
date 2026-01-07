# Plan: Add Prospeo to Enrichment Waterfall + Verify Prefect Integration

**Created:** 2026-01-07
**Status:** PLANNING

---

## Current State Analysis

### Enrichment Waterfall (Current)
```
Tier 0: Cache (Redis) ─────────────────────── FREE
    ↓ miss
Tier 1: Apollo + Apify ────────────────────── ~$0.03-0.05/lead
    ↓ fail (confidence < 0.70)
Tier 2: Clay (max 15%) ────────────────────── ~$0.25-0.50/lead
```

### Target State
```
Tier 0: Cache (Redis) ─────────────────────── FREE
    ↓ miss
Tier 1: Apollo ────────────────────────────── ~$0.03/lead
    ↓ no email / low confidence
Tier 1.5: Prospeo (NEW) ───────────────────── ~$0.03-0.06/lead
    ↓ fail
Tier 2: Clay (max 15%) ────────────────────── ~$0.25-0.50/lead
```

### Prefect Status
| Component | Status | Notes |
|-----------|--------|-------|
| prefect.yaml configured | ✅ | 4 deployments defined |
| Scout used in flows | ✅ | enrichment_flow, pool_population_flow |
| Prefect worker running | ❓ | Need to verify on Railway |
| Work pool exists | ❓ | Need `prefect work-pool ls` |
| Deployments registered | ❓ | Need `prefect deployment ls` |

### Missing Components
| Component | Status | Required Action |
|-----------|--------|-----------------|
| `src/integrations/prospeo.py` | ❌ Missing | Create new file |
| `docs/specs/integrations/PROSPEO.md` | ❌ Missing | Create spec |
| Prospeo in Scout waterfall | ❌ Not integrated | Modify scout.py |
| `PROSPEO_API_KEY` env var | ❓ Unknown | Add to Railway |

---

## Task Breakdown

### Phase 1: Create Prospeo Integration (INT-010)

**File:** `src/integrations/prospeo.py`

**Prospeo API Endpoints to Implement:**
| Method | Endpoint | Cost | Purpose |
|--------|----------|------|---------|
| `find_email()` | `/email-finder` | 1 credit | Find email by name + domain |
| `verify_email()` | `/email-verifier` | 0.5 credits | Verify email validity |
| `enrich_linkedin()` | `/social-url-enrichment` | 2 credits | Enrich from LinkedIn URL |

**Implementation:**
```python
class ProspeoClient:
    BASE_URL = "https://api.prospeo.io"

    async def find_email(self, first_name, last_name, domain) -> dict
    async def verify_email(self, email) -> dict
    async def enrich_from_linkedin(self, linkedin_url) -> dict
```

### Phase 2: Add Prospeo to Scout Waterfall (ENG-010)

**File:** `src/engines/scout.py`

**Changes:**
1. Import ProspeoClient
2. Add `_enrich_tier1_5()` method for Prospeo fallback
3. Modify `_enrich_tier1()` to return partial data if Apollo has no email
4. Update waterfall flow in `enrich_lead()` and `_enrich_single()`

**New Waterfall Logic:**
```python
async def enrich_lead():
    # Tier 0: Cache
    if cached: return cached

    # Tier 1: Apollo
    apollo_result = await _enrich_tier1(lead, domain)
    if apollo_result and self._validate_enrichment(apollo_result):
        return apollo_result

    # Tier 1.5: Prospeo (NEW) - if Apollo found person but no email
    if apollo_result and not apollo_result.get("email"):
        prospeo_result = await _enrich_tier1_5(lead, domain, apollo_result)
        if prospeo_result and self._validate_enrichment(prospeo_result):
            return prospeo_result

    # Tier 2: Clay (existing)
    clay_result = await _enrich_tier2(lead, domain)
    ...
```

### Phase 3: Verify Prefect Connection

**Checks to Perform:**
1. Verify `PREFECT_API_URL` is set in Railway
2. Check if work pool `agency-os-pool` exists
3. Check if deployments are registered
4. Test flow execution manually

**Verification Commands:**
```bash
# On Railway or local with PREFECT_API_URL set
prefect work-pool ls
prefect deployment ls
prefect flow-run ls --limit 10
```

**If Not Working:**
```bash
# Create work pool
prefect work-pool create agency-os-pool --type process

# Deploy flows
prefect deploy --all

# Start worker
prefect worker start --pool agency-os-pool
```

### Phase 4: Add Environment Variable

**Railway Config:**
```
PROSPEO_API_KEY=<api_key>
```

**Settings Update:**
```python
# src/config/settings.py
prospeo_api_key: str = Field(default="", env="PROSPEO_API_KEY")
```

---

## Files to Create/Modify

| Action | File | Description |
|--------|------|-------------|
| CREATE | `src/integrations/prospeo.py` | Prospeo API client |
| CREATE | `docs/specs/integrations/PROSPEO.md` | Integration spec |
| MODIFY | `src/engines/scout.py` | Add Tier 1.5 waterfall |
| MODIFY | `src/config/settings.py` | Add PROSPEO_API_KEY |
| MODIFY | `config/.env.example` | Add PROSPEO_API_KEY example |

---

## Execution Order

```
1. Create src/integrations/prospeo.py
2. Update src/config/settings.py with prospeo_api_key
3. Modify src/engines/scout.py to add Tier 1.5
4. Test locally with pytest
5. Verify Prefect status on Railway
6. Deploy and test end-to-end
```

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Prospeo API changes | Use tenacity retry with exponential backoff |
| Rate limiting | Implement rate limiter in client |
| Cost overrun | Add usage tracking/limits |
| Prefect not running | Deploy worker to Railway |

---

## Estimated Effort

| Task | Time |
|------|------|
| Create Prospeo integration | 1-2 hours |
| Modify Scout waterfall | 1 hour |
| Verify/fix Prefect | 30 min - 2 hours |
| Testing | 1 hour |
| **Total** | **3.5 - 6 hours** |
