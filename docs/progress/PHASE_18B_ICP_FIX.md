
---

## PHASE 18-B: ICP Enrichment Fix + Social Media (NEW)

**Purpose:** Fix empty portfolio extraction + add social media enrichment
**Created:** January 5, 2026
**Spec:** `docs/progress/PHASE_18B_ICP_FIX.md`
**Discovered:** During M1 testing - ICP extraction returns empty target fields

### Problem

ICP extraction succeeds but returns empty data:
- ✅ Website scraped (11 pages, 401KB HTML)
- ✅ Services extracted correctly
- ❌ Portfolio companies empty (company names lost in summarization)
- ❌ Target Industries empty
- ❌ Target Company Sizes empty
- ❌ Target Locations empty
- ❌ Confidence only 50%

**Root Cause:** `PortfolioExtractorSkill` only sees summarized `PageContent`, not raw HTML. Company names from testimonials (Vermeer, APM, Kustom Timber) are lost during summarization.

### Solution: Two-Part Fix

**Part A - Portfolio Data Loss Fix:**
- Pass `raw_html` to portfolio extractor
- Extract testimonial/case study sections for company name mining
- Update prompts to emphasize name extraction

**Part B - Social Media Enrichment:**
- Extract social links from website header/footer
- Add Apify scrapers for LinkedIn Company, Instagram, Facebook, Google Business
- Include social data in ICP profile

### Tasks

#### 18-B-A: Fix Portfolio Data Loss (5 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| ICP-FIX-001 | Add `raw_html` field to PortfolioExtractorSkill.Input | 🔴 | `src/agents/skills/portfolio_extractor.py` |
| ICP-FIX-002 | Update build_prompt to extract testimonial sections | 🔴 | `src/agents/skills/portfolio_extractor.py` |
| ICP-FIX-003 | Update system prompt for company name extraction | 🔴 | `src/agents/skills/portfolio_extractor.py` |
| ICP-FIX-004 | Pass raw_html from ICPDiscoveryAgent | 🔴 | `src/agents/icp_discovery_agent.py` |
| ICP-FIX-005 | Test with dilate.com.au | 🔴 | — |

#### 18-B-B: Social Media Enrichment (6 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| SOC-001 | Add social_links field to PageContent | 🔴 | `src/agents/skills/website_parser.py` |
| SOC-002 | Add scrape_linkedin_company method | 🔴 | `src/integrations/apify.py` |
| SOC-003 | Add scrape_instagram_profile method | 🔴 | `src/integrations/apify.py` |
| SOC-004 | Add scrape_facebook_page method | 🔴 | `src/integrations/apify.py` |
| SOC-005 | Add scrape_google_business method | 🔴 | `src/integrations/apify.py` |
| SOC-006 | Create SocialProfiles model | 🔴 | `src/models/social_profile.py` |

#### 18-B-C: Integration (3 tasks)

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| INT-B-001 | Add _scrape_social_profiles helper | 🔴 | `src/agents/icp_discovery_agent.py` |
| INT-B-002 | Add social_profiles to ICPProfile | 🔴 | `src/agents/icp_discovery_agent.py` |
| INT-B-003 | Update profile building section | 🔴 | `src/agents/icp_discovery_agent.py` |

### CC Prompts Created

| Prompt | Purpose | File |
|--------|---------|------|
| Phase 1A | Backend: Portfolio fix + Social enrichment | `prompts/CC_PHASE1A_BACKEND_ICP_FIX.md` |
| Phase 1B | Frontend: Async UX (redirect to dashboard) | `prompts/CC_PHASE1B_FRONTEND_ASYNC_UX.md` |

### Cost Impact

| Operation | Cost per Agency |
|-----------|-----------------|
| Website scrape (existing) | ~$0.01 |
| LinkedIn Company | ~$0.50 |
| Instagram | ~$0.02 |
| Facebook | ~$0.02 |
| Google Business | ~$0.02 |
| Apollo enrichment (existing) | ~$0.31 |
| **Total** | **~$0.88** |

For 100 founding customers: ~$88 total enrichment cost

### Success Criteria

- [ ] Portfolio companies extracted (Vermeer, APM, etc.)
- [ ] Social links extracted from website
- [ ] LinkedIn company data populated
- [ ] Google Business rating populated
- [ ] ICP industries populated (not empty)
- [ ] ICP company sizes populated (not empty)
- [ ] Confidence > 70%

### Expected Output After Fix

```json
{
  "portfolio_companies": ["Vermeer", "Kustom Timber", "APM", ...],
  "social_profiles": {
    "linkedin": {"followers": 2847, "employee_count": "11-50"},
    "google_business": {"rating": 4.8, "review_count": 47}
  },
  "icp_industries": ["Mining", "Construction", "Healthcare"],
  "icp_company_sizes": ["50-200", "200-500"],
  "confidence": 0.85
}
```

---

## PHASE 18-B-FE: Async Onboarding UX (NEW)

**Purpose:** Don't make users wait 2-3 minutes staring at loading screen
**Created:** January 5, 2026
**Depends On:** Phase 18-B (backend)

### Current UX (Bad)

```
1. User enters URL → waits 2-3 min on "Analyzing" screen → sees ICP → confirms → dashboard
```

### New UX (Good)

```
1. User enters URL → immediately redirected to dashboard (<1 sec)
2. Dashboard shows progress banner
3. User explores dashboard while waiting
4. Banner updates to "✅ ICP Ready" when complete
5. User clicks → review modal → confirm
```

### Tasks

| Task | Description | Status | Files |
|------|-------------|--------|-------|
| FE-B-001 | Update onboarding to redirect immediately | 🔴 | `frontend/app/onboarding/page.tsx` |
| FE-B-002 | Create ICP progress banner component | 🔴 | `frontend/components/icp-progress-banner.tsx` |
| FE-B-003 | Create ICP review modal | 🔴 | `frontend/components/icp-review-modal.tsx` |
| FE-B-004 | Add polling to dashboard | 🔴 | `frontend/app/dashboard/page.tsx` |
| FE-B-005 | Persist job_id to localStorage | 🔴 | `frontend/app/dashboard/page.tsx` |

### Existing Infrastructure (No Backend Changes Needed)

- ✅ `BackgroundTasks` in FastAPI
- ✅ `icp_extraction_jobs` table with status tracking
- ✅ `GET /onboarding/status/{job_id}` endpoint
- ✅ `GET /onboarding/result/{job_id}` endpoint
- ✅ 2-second polling already implemented in onboarding page
