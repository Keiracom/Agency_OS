# J2B: Lead Enrichment & LinkedIn Scraping Journey

**Status:** 🟢 Ready for Testing
**Priority:** P1 — Critical for hyper-personalization and ALS accuracy
**Depends On:** J2 Campaign (Lead Pool Population)
**Last Updated:** January 11, 2026
**Sub-Tasks:** 8 groups, 36 individual checks

---

## Overview

Tests the complete lead enrichment waterfall including LinkedIn data scraping, Claude analysis for personalization, and ALS scoring with LinkedIn boost signals.

**Why This Journey Exists:**
The enrichment flow is a critical pipeline that transforms basic Apollo lead data into hyper-personalized, high-scoring leads. Without enrichment testing, we risk:
- Stale/incomplete lead data
- Missing personalization angles
- Inaccurate ALS scores (missing up to 10 points from LinkedIn boost)

**Enrichment Waterfall (5 Stages):**
```
Stage 1: Apollo Data (from pool population)
    ↓
Stage 2: Apify LinkedIn Person Scrape (profile + posts)
    ↓
Stage 3: Apify LinkedIn Company Scrape (profile + posts)
    ↓
Stage 4: Claude Analysis (pain points, personalization, hooks)
    ↓
Stage 5: ALS Scoring with Enhanced Signals
```

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Enrichment Flow | `src/orchestration/flows/lead_enrichment_flow.py` | 505 | ✅ VERIFIED |
| Scorer Engine | `src/engines/scorer.py` | 1428 | ✅ VERIFIED |
| Scout Engine | `src/engines/scout.py` | 500+ | ✅ VERIFIED |
| Apify Integration | `src/integrations/apify.py` | 400+ | ✅ VERIFIED |
| Research Skills | `src/agents/skills/research_skills.py` | 200+ | ✅ VERIFIED |
| Lead Assignments | `lead_assignments` table | - | Has LinkedIn fields |

---

## Sub-Tasks

### J2B.1 — Enrichment Flow Trigger
**Purpose:** Verify enrichment flow triggers correctly for assigned leads.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.1.1 | Read `lead_enrichment_flow.py` — verify flow definition | Check Prefect deployment |
| J2B.1.2 | Verify flow accepts `assignment_id` parameter | N/A |
| J2B.1.3 | Verify `get_assignment_for_enrichment_task` loads all needed data | Check returned fields |
| J2B.1.4 | Verify enrichment_status updates to 'in_progress' | Trigger flow, check DB |
| J2B.1.5 | Verify batch flow `batch_lead_enrichment_flow` exists | Check batch support |

**Enrichment Status Transitions:**
```
pending → in_progress → linkedin_scraped → analysis_complete → completed
                    ↘ failed (on error)
```

**Pass Criteria:**
- [ ] Flow runs via Prefect
- [ ] Assignment data loaded correctly
- [ ] Status transitions properly tracked
- [ ] Batch enrichment supported

<!-- E2E_SESSION_BREAK: J2B.1 complete. Next: J2B.2 LinkedIn Person Scraping -->

---

### J2B.2 — LinkedIn Person Scraping (Stage 2)
**Purpose:** Verify Apify scrapes LinkedIn person profiles and posts.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.2.1 | Read `scrape_linkedin_data_task` in enrichment flow | N/A |
| J2B.2.2 | Read `src/engines/scout.py` — verify `enrich_linkedin_for_assignment` | N/A |
| J2B.2.3 | Read `src/integrations/apify.py` — verify LinkedIn person actor | Check actor ID |
| J2B.2.4 | Verify profile fields captured: headline, about, connections | Check data structure |
| J2B.2.5 | Verify posts scraped with engagement metrics | Check posts array |
| J2B.2.6 | Verify data stored in `linkedin_person_data` JSONB field | Query assignment |

**LinkedIn Person Data Fields:**
```json
{
  "headline": "VP of Marketing at TechCorp",
  "about": "15 years in B2B marketing...",
  "connections": 1247,
  "posts": [
    {
      "text": "Excited to announce...",
      "posted_date": "2026-01-05",
      "likes": 45,
      "comments": 12
    }
  ]
}
```

**Pass Criteria:**
- [ ] Apify actor runs successfully
- [ ] Profile data captured (headline, about, connections)
- [ ] Posts scraped with dates and engagement
- [ ] Data stored in assignment record

<!-- E2E_SESSION_BREAK: J2B.2 complete. Next: J2B.3 LinkedIn Company Scraping -->

---

### J2B.3 — LinkedIn Company Scraping (Stage 3)
**Purpose:** Verify Apify scrapes LinkedIn company profiles and posts.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.3.1 | Verify company LinkedIn URL used from lead_pool | Check URL source |
| J2B.3.2 | Read `apify.py` — verify LinkedIn company actor | Check actor ID |
| J2B.3.3 | Verify company fields captured: description, specialties, followers | Check data structure |
| J2B.3.4 | Verify company posts scraped | Check posts array |
| J2B.3.5 | Verify data stored in `linkedin_company_data` JSONB field | Query assignment |

**LinkedIn Company Data Fields:**
```json
{
  "description": "TechCorp is a leading provider of...",
  "specialties": ["SaaS", "B2B", "Marketing Tech"],
  "followers": 5420,
  "posts": [
    {
      "text": "We're hiring! Join our team...",
      "posted_date": "2026-01-08",
      "likes": 89
    }
  ]
}
```

**Pass Criteria:**
- [ ] Company profile scraped
- [ ] Specialties array captured
- [ ] Company posts with dates/engagement
- [ ] Data stored in assignment record

<!-- E2E_SESSION_BREAK: J2B.3 complete. Next: J2B.4 Claude Personalization Analysis -->

---

### J2B.4 — Claude Personalization Analysis (Stage 4)
**Purpose:** Verify Claude analyzes data and generates personalization insights.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.4.1 | Read `analyze_for_personalization_task` in enrichment flow | N/A |
| J2B.4.2 | Read `src/agents/skills/research_skills.py` — verify `PersonalizationAnalysisSkill` | Check Input/Output |
| J2B.4.3 | Verify skill input includes: person posts, company posts, agency services | Check input construction |
| J2B.4.4 | Verify pain_points generated (array of strings) | Check output |
| J2B.4.5 | Verify icebreaker_hooks generated | Check output |
| J2B.4.6 | Verify best_channel recommended | Check output |
| J2B.4.7 | Verify AI cost tracked (tokens_used, cost_aud) | Check metadata |

**Claude Analysis Output:**
```json
{
  "pain_points": [
    "Struggling with lead quality from current sources",
    "Marketing team stretched thin for content creation"
  ],
  "personalization_angles": [
    "Recent post about team growth shows scaling challenges",
    "Company hiring for 3 marketing roles - likely need support"
  ],
  "icebreaker_hooks": [
    "Saw your post about the new product launch - impressive results!",
    "Noticed you're hiring marketing specialists - exciting growth phase!"
  ],
  "best_channel": "linkedin",
  "confidence": 0.85,
  "topics_to_avoid": ["competitor X merger"],
  "best_timing": "Tuesday-Thursday mornings"
}
```

**Pass Criteria:**
- [ ] Claude analysis runs successfully
- [ ] Pain points identified from LinkedIn data
- [ ] Icebreaker hooks generated
- [ ] Best channel recommended
- [ ] AI spend tracked

<!-- E2E_SESSION_BREAK: J2B.4 complete. Next: J2B.5 ALS LinkedIn Boost -->

---

### J2B.5 — ALS LinkedIn Boost (Stage 5)
**Purpose:** Verify ALS scoring includes LinkedIn engagement boost (up to 10 points).

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.5.1 | Read `scorer.py` — verify `_get_linkedin_boost` method | N/A |
| J2B.5.2 | Verify MAX_LINKEDIN_BOOST = 10 | Check constant |
| J2B.5.3 | Verify person posts boost (+3) | Check LINKEDIN_PERSON_POSTS_BOOST |
| J2B.5.4 | Verify company posts boost (+2) | Check LINKEDIN_COMPANY_POSTS_BOOST |
| J2B.5.5 | Verify high connections boost (+2 for 500+) | Check LINKEDIN_HIGH_CONNECTIONS_BOOST |
| J2B.5.6 | Verify high followers boost (+2 for 1000+) | Check LINKEDIN_HIGH_FOLLOWERS_BOOST |
| J2B.5.7 | Verify recent activity boost (+1 for 30 days) | Check LINKEDIN_RECENT_ACTIVITY_BOOST |
| J2B.5.8 | Verify boost applied in `score_pool_lead` when assignment_id provided | Check score calculation |

**LinkedIn Boost Breakdown (VERIFIED from scorer.py lines 108-114):**
| Signal | Points | Condition |
|--------|--------|-----------|
| Person has posts | +3 | posts array not empty |
| Company has posts | +2 | company posts not empty |
| High connections | +2 | 500+ connections |
| High followers | +2 | 1000+ company followers |
| Recent activity | +1 | Posted in last 30 days |
| **MAX TOTAL** | **10** | Capped |

**Pass Criteria:**
- [ ] LinkedIn boost calculated from enrichment data
- [ ] All 5 signal types checked
- [ ] Boost capped at 10 points max
- [ ] Boost added to final ALS score
- [ ] Signals logged for transparency

<!-- E2E_SESSION_BREAK: J2B.5 complete. Next: J2B.6 Assignment Data Storage -->

---

### J2B.6 — Assignment Data Storage
**Purpose:** Verify all enrichment data stored correctly in lead_assignments.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.6.1 | Verify `linkedin_person_data` JSONB column exists | Check schema |
| J2B.6.2 | Verify `linkedin_company_data` JSONB column exists | Check schema |
| J2B.6.3 | Verify `linkedin_person_scraped_at` timestamp stored | Check timestamp |
| J2B.6.4 | Verify `linkedin_company_scraped_at` timestamp stored | Check timestamp |
| J2B.6.5 | Verify `personalization_data` JSONB stored | Check field |
| J2B.6.6 | Verify `pain_points` array stored | Check field |
| J2B.6.7 | Verify `icebreaker_hooks` JSONB stored | Check field |
| J2B.6.8 | Verify `best_channel` stored | Check field |
| J2B.6.9 | Verify `als_score`, `als_tier`, `als_components` stored | Check score fields |
| J2B.6.10 | Verify `enrichment_completed_at` timestamp set | Check timestamp |

**Key Assignment Fields for Enrichment:**
```sql
-- LinkedIn Data
linkedin_person_data JSONB,
linkedin_company_data JSONB,
linkedin_person_scraped_at TIMESTAMP,
linkedin_company_scraped_at TIMESTAMP,

-- Claude Analysis
personalization_data JSONB,
pain_points TEXT[],
icebreaker_hooks JSONB,
best_channel VARCHAR,
personalization_confidence FLOAT,
personalization_analyzed_at TIMESTAMP,

-- ALS Scoring
als_score INTEGER,
als_tier VARCHAR,
als_components JSONB,
scored_at TIMESTAMP,

-- Status Tracking
enrichment_status VARCHAR,
enrichment_started_at TIMESTAMP,
enrichment_completed_at TIMESTAMP
```

**Pass Criteria:**
- [ ] All LinkedIn data stored in JSONB
- [ ] All analysis results stored
- [ ] ALS score with components stored
- [ ] Timestamps track enrichment progress

<!-- E2E_SESSION_BREAK: J2B.6 complete. Next: J2B.7 Error Handling -->

---

### J2B.7 — Error Handling
**Purpose:** Verify graceful handling of enrichment failures.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.7.1 | Verify LinkedIn scrape failures don't crash flow | Test with invalid URL |
| J2B.7.2 | Verify analysis continues without LinkedIn data | Skip scrape, run analysis |
| J2B.7.3 | Verify ALS scoring works without LinkedIn boost | Score without enrichment |
| J2B.7.4 | Verify enrichment_status set to 'failed' on error | Check status update |
| J2B.7.5 | Verify batch continues on individual failures | Run batch with bad data |

**Error Recovery Strategy:**
```
LinkedIn Scrape Fails → Continue to analysis (use Apollo data only)
Claude Analysis Fails → Continue to scoring (use basic ALS)
Scoring Fails → Log error, mark assignment failed
```

**Pass Criteria:**
- [ ] Individual failures don't crash batch
- [ ] Partial enrichment still useful
- [ ] Error states properly tracked
- [ ] Retries configured (2x with 10s delay)

<!-- E2E_SESSION_BREAK: J2B.7 complete. Next: J2B.8 Enrichment API Endpoints -->

---

### J2B.8 — Enrichment API Endpoints
**Purpose:** Verify manual enrichment triggers via API.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J2B.8.1 | Verify `/api/v1/leads/{id}/research` endpoint exists | Check leads.py |
| J2B.8.2 | Verify endpoint triggers enrichment flow | Test endpoint |
| J2B.8.3 | Verify response includes enrichment status | Check response |
| J2B.8.4 | Verify batch enrichment endpoint exists | Check endpoint |

**Pass Criteria:**
- [ ] Manual enrichment can be triggered via API
- [ ] Enrichment status returned in response
- [ ] Both single and batch supported

<!-- E2E_SESSION_BREAK: J2B JOURNEY COMPLETE. Next: J3 Email Outreach -->

---

## Completion Criteria

All checks must pass:

- [ ] **J2B.1** Enrichment flow triggers and tracks status
- [ ] **J2B.2** LinkedIn person profile + posts scraped
- [ ] **J2B.3** LinkedIn company profile + posts scraped
- [ ] **J2B.4** Claude analysis generates personalization insights
- [ ] **J2B.5** ALS LinkedIn boost calculated correctly (up to +10)
- [ ] **J2B.6** All enrichment data stored in assignments
- [ ] **J2B.7** Errors handled gracefully
- [ ] **J2B.8** API endpoints work

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Enrichment waterfall fully implemented (5 stages)
2. ✅ LinkedIn scraping via Apify actors configured
3. ✅ Claude PersonalizationAnalysisSkill generates quality insights
4. ✅ ALS LinkedIn boost correctly implemented (max 10 points)
5. ✅ All data stored in lead_assignments table
6. ✅ Batch processing supported
7. ✅ Error handling with retries (2x, 10s delay)

**LinkedIn Boost Impact:**
A lead with active LinkedIn presence can gain up to 10 additional ALS points:
- This can push a Warm lead (84) into Hot territory (94)
- Ensures engaged prospects get priority outreach
- Signals like "posted in last 30 days" indicate receptive timing

**Apify Cost Estimate:**
- LinkedIn Person Scrape: ~$0.01-0.05 per profile
- LinkedIn Company Scrape: ~$0.01-0.05 per company
- Budget consideration: Enrich only assigned leads (not full pool)

---

## Notes

**Why Enrich After Assignment:**
Enrichment runs AFTER lead assignment (not during pool population) to:
1. Save costs (only enrich leads that will be used)
2. Get fresh LinkedIn data (not stale cached data)
3. Tailor analysis to specific client's services

**Integration with Content Engine:**
The personalization data from enrichment directly feeds the content engine:
- `pain_points` → Email body messaging
- `icebreaker_hooks` → Opening lines
- `best_channel` → Channel prioritization in orchestrator
- `topics_to_avoid` → Negative keywords for AI

**ALS Score Example with LinkedIn Boost:**
```
Base Score (without enrichment): 78 (Warm)
  - Data Quality: 18/20
  - Authority: 22/25 (VP title)
  - Company Fit: 20/25
  - Timing: 8/15
  - Risk: 10/15

LinkedIn Boost: +8
  - Person has posts: +3
  - 500+ connections: +2
  - Recent activity: +1
  - Company has posts: +2

Final Score: 86 (Hot)
  - Now eligible for SMS, Voice, Direct Mail
```
