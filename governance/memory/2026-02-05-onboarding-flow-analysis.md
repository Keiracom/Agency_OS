# Agency OS Onboarding Flow Analysis
**Date:** 2026-02-05  
**Author:** Elliot (Subagent Research)  
**Purpose:** Compare architecture/code onboarding with HTML prototype

---

## 1. Architecture/Code Onboarding Flow

The backend implements a **streamlined, AI-first onboarding** that minimizes user input and maximizes automation.

### Step-by-Step Flow:

| Step | Location | What Happens | Data Collected |
|------|----------|--------------|----------------|
| **1. Auth/Signup** | Supabase Auth + `/auth/callback/` | User creates account, client tenant created | Email, password |
| **2. Website Entry** | `/onboarding/page.tsx` | Single input form | `website_url` only |
| **3. ICP Extraction** | `POST /api/v1/onboarding/analyze` → Prefect flow | Background job starts | None (automated) |
| **4. Analysis Progress** | Dashboard polls `/api/v1/onboarding/status/{job_id}` | 8-step Prefect flow runs | None (automated) |
| **5. ICP Review** | Dashboard ICP component | User sees extracted ICP | Optional edits |
| **6. ICP Confirm** | `POST /api/v1/onboarding/confirm` | Saves to client, triggers post-onboarding | Adjustments (optional) |
| **7. LinkedIn Connect** | `/onboarding/linkedin/` (optional) | Unipile hosted auth | LinkedIn OAuth |
| **8. Post-Onboarding** | `post_onboarding_flow.py` (auto) | Campaigns suggested, leads sourced | None (automated) |

### Prefect ICP Extraction Steps (8 total):
1. Scrape website (Apify)
2. Extract portfolio companies
3. Enrich portfolio with industry/size
4. Analyze services offered
5. Generate ICP profile (AI)
6. Calculate ALS weights
7. Assign buffer resources
8. Mark extraction complete

### Data Model (`clients` table - ICP fields):
```
- website_url
- company_description
- services_offered: TEXT[]
- value_proposition
- team_size
- icp_industries: TEXT[]
- icp_company_sizes: TEXT[]
- icp_revenue_range
- icp_locations: TEXT[]
- icp_titles: TEXT[]
- icp_pain_points: TEXT[]
- icp_keywords: TEXT[]
- als_weights: JSONB
```

### Key Architectural Decisions:
- **AI-First:** Minimal manual input; AI extracts everything from website
- **Async Flow:** Prefect orchestration allows background processing
- **Auto-Apply Option:** ICP can be auto-applied without user confirmation
- **Post-Onboarding Automation:** Campaign and lead generation triggers automatically

---

## 2. HTML Prototype Onboarding Flow

The prototype shows a **5-step wizard** with more manual configuration options.

### Step-by-Step Flow:

| Step | Screen | What Happens | Data Collected |
|------|--------|--------------|----------------|
| **1. Your Business** | Form card | User enters business info | `agencyName`, `websiteUrl`, `agencyDescription` |
| **2. Analysis** | Loading → Results | Shows AI analysis progress, then results | None (display only) |
| **3. Target Audience** | ICP Configuration | User refines ICP with pre-filled suggestions | Industries, company size, job titles, geography |
| **4. Channels** | Connection cards | User connects outreach channels | Email provider, LinkedIn, SMS, Voice |
| **5. Launch** | Review summary | User reviews all settings, sees lead estimate | Confirmation |

### Step 3 (ICP) Details:
- **Industries:** 8 checkbox options (Automotive, Healthcare, Real Estate, Professional Services, Retail, Hospitality, Manufacturing, Technology) - AI pre-selects based on analysis
- **Company Size:** Dropdown (1-10, 11-50, 51-200, 201-500, 501+) - AI suggested
- **Job Titles:** Tag input with AI-suggested defaults (CEO/Founder, Marketing Director, Head of Growth)
- **Geography:** Grid with "All Australia" + 8 state options (NSW, VIC, QLD, WA, SA, TAS, ACT, NT)

### Step 4 (Channels) Details:
- **Email:** Google OAuth, Microsoft OAuth, or SMTP manual
- **LinkedIn:** Connect button (shows pending/connected status)
- **SMS:** Shows "Auto-configured" with Twilio
- **Voice:** Shows "Auto-configured" with Vapi

### Step 5 (Launch) Details:
- Review sections for: Business Info, ICP, Channels
- Estimated leads card with gradient background
- "Launch Your First Campaign" button
- Celebration modal with confetti on success

---

## 3. Gap Analysis Table

| Feature | Code/Backend | Prototype | Gap |
|---------|--------------|-----------|-----|
| **Agency Name Input** | ❌ Not collected in onboarding | ✅ Step 1 field | **Missing in code** |
| **Agency Description** | ❌ Not collected (AI generates) | ✅ Step 1 field | **Missing in code** |
| **Website URL** | ✅ Single input | ✅ Step 1 field | ✅ Aligned |
| **Analysis Progress UI** | ✅ Polling via job_id | ✅ Animated spinner + progress items | **UI implementation needed** |
| **Analysis Results Display** | ✅ API returns data | ✅ Rich results card | **UI implementation needed** |
| **ICP Industries (selection)** | ✅ Stored (auto-extracted) | ✅ Checkbox grid + AI pre-select | **UI for manual edit needed** |
| **ICP Company Size** | ✅ Stored as array | ✅ Dropdown selector | **UI for manual edit needed** |
| **ICP Job Titles** | ✅ Stored as array | ✅ Tag input + AI suggestions | **UI for manual edit needed** |
| **ICP Geography** | ✅ Stored in `icp_locations` | ✅ AU state grid | **UI for manual edit needed** |
| **Email Channel Connect** | ⚠️ Separate infrastructure exists | ✅ Step 4 - OAuth + SMTP | **Not in onboarding flow** |
| **LinkedIn Connect** | ✅ Separate page `/onboarding/linkedin` | ✅ Step 4 - inline | **Different UX (separate vs inline)** |
| **SMS Channel** | ⚠️ Backend exists (Twilio) | ✅ Step 4 - auto-configured | **Not in onboarding flow** |
| **Voice Channel** | ⚠️ Backend exists (Vapi) | ✅ Step 4 - auto-configured | **Not in onboarding flow** |
| **Review Step** | ❌ Goes directly to dashboard | ✅ Step 5 - full summary | **Missing in code** |
| **Estimated Leads** | ❌ Not shown | ✅ Step 5 - prominently displayed | **Missing in code** |
| **Launch Button** | ❌ Auto-triggers post-onboarding | ✅ Explicit user action | **Different approach** |
| **Success Celebration** | ❌ Not implemented | ✅ Modal + confetti | **Missing in code** |
| **ICP Pain Points** | ✅ Stored in model | ❌ Not shown in prototype | **Missing in prototype** |
| **ALS Weights** | ✅ Calculated and stored | ❌ Not exposed | OK (backend-only) |
| **Default Offer** | ✅ In model | ❌ Not collected | **Missing in prototype** |

---

## 4. Recommendations

### High Priority (Align Code to Prototype)

1. **Add Agency Name/Description to Step 1**
   - Update `/onboarding/page.tsx` to collect `agencyName` and `agencyDescription`
   - Send to backend in `/api/v1/onboarding/analyze` payload
   - Store in `clients.name` and `clients.company_description`

2. **Build ICP Configuration Step**
   - New page: `/onboarding/icp/page.tsx`
   - Fetch extraction results
   - Display as pre-filled form with:
     - Industry checkboxes (from detected industries)
     - Company size dropdown
     - Job titles tag input
     - Geography state grid
   - Submit to `/api/v1/onboarding/confirm` with adjustments

3. **Consolidate Channel Connections**
   - Either:
     - (A) Keep separate pages but add progress indicator showing all 4 channels
     - (B) Build unified channels step per prototype
   - Note: SMS/Voice are "auto-configured" in prototype - may not need user action

4. **Add Review Step Before Launch**
   - New page: `/onboarding/review/page.tsx`
   - Display summary of all collected data
   - Calculate and show estimated lead count
   - Explicit "Launch" button that triggers post-onboarding flow

### Medium Priority (Enhance Experience)

5. **Analysis Progress UI**
   - Implement the animated progress list from prototype
   - 4 steps: Scanning pages, Extracting portfolio, Identifying industries, Building ICP
   - Can use SSE or polling with step status from backend

6. **Success Celebration**
   - Add modal component with confetti animation
   - Show stats: ICP profile completeness, channels connected, campaigns ready

7. **Estimated Leads Display**
   - Calculate based on ICP criteria (Apollo API preview?)
   - Show prominently in review step

### Low Priority (Nice to Have)

8. **Pain Points Input**
   - Backend supports it, could add to prototype's ICP step
   - Tag input similar to job titles

9. **"Need Help?" Support Link**
   - Add to header per prototype design

---

## 5. Architecture Notes for Implementation

### Data Flow (Recommended):
```
1. /onboarding (Step 1)
   → POST /api/v1/onboarding/analyze
   → Creates icp_extraction_job
   → Triggers Prefect onboarding_flow

2. /onboarding/analysis (Step 2)
   → GET /api/v1/onboarding/status/{job_id} (polling)
   → Shows progress, then results

3. /onboarding/icp (Step 3)
   → GET /api/v1/onboarding/result/{job_id} (pre-fill)
   → User edits
   → [No API call yet - store in local state]

4. /onboarding/channels (Step 4)
   → LinkedIn: GET /api/v1/linkedin/connect
   → Email: Existing infrastructure
   → SMS/Voice: Auto-show as configured

5. /onboarding/review (Step 5)
   → Display all collected data
   → POST /api/v1/onboarding/confirm (with adjustments)
   → Triggers post_onboarding_flow

6. Dashboard (Celebration modal)
   → Show success
   → Redirect to campaign dashboard
```

### State Management:
- Use React Query for API calls
- Use local state or Zustand for multi-step form data
- `job_id` in URL or localStorage for persistence across refreshes

### Backend Changes Needed:
- Extend `AnalyzeWebsiteRequest` to include `agency_name`, `description`
- Add endpoint for estimated lead count: `GET /api/v1/onboarding/estimate/{job_id}`
- Consider adding email connection to onboarding API (currently separate)

---

## Summary

The **code implements ~60% of the prototype flow**, with strong backend capabilities but missing frontend UX polish. The main gaps are:

1. **Input Collection:** Prototype collects more upfront (name, description)
2. **ICP Editing:** Prototype has rich editing UI; code auto-applies
3. **Channel Consolidation:** Prototype shows all 4 channels; code has LinkedIn separate
4. **Review/Launch:** Prototype has explicit review; code auto-triggers

**Recommended approach:** Implement the prototype's Step 1, 3, and 5 UIs while keeping the existing backend flow. The Prefect orchestration and ICP extraction logic are solid - the gap is primarily frontend UX.
