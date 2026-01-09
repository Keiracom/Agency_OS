# Lead Enrichment Waterfall Specification

**Phase:** 24A+ (Enhanced Lead Enrichment)
**Status:** Draft
**Last Updated:** 2026-01-09

---

## Overview

Full lead enrichment waterfall that captures ALL available data for hyper-personalization across 5 channels (Email, SMS, LinkedIn, Voice, Direct Mail).

---

## Waterfall Stages

### Stage 1: Apollo (Contact + Company Firmographics)
**Trigger:** Pool population
**Cost:** ~$0.03-0.10 per lead

**Data Captured:**
- Email (verified status)
- Phone number
- LinkedIn URL
- Job title, seniority
- Company name, domain, industry
- Company size, revenue, location
- Hiring signals, funding data
- Tech stack, keywords

---

### Stage 2: Apify LinkedIn Person Scrape
**Trigger:** After lead assignment to client
**Cost:** ~$0.03 per profile

**Data Captured:**
```
Profile:
- Headline (how they position themselves)
- About/Summary (their story)
- Current role start date
- Full experience history
- Skills & endorsements
- Certifications
- Education

Activity:
- Last 5 posts (content, date, engagement)
- Post topics/themes
- Engagement style (posts vs comments)
- Articles/publications
```

---

### Stage 3: Apify LinkedIn Company Scrape
**Trigger:** After lead assignment (parallel with Stage 2)
**Cost:** ~$0.03 per company

**Data Captured:**
```
Company Profile:
- Description
- Specialties
- Employee count
- Follower count
- Headquarters

Activity:
- Last 5 company posts (content, date)
- Recent announcements
- Hiring activity
- Awards/recognition
```

---

### Stage 4: Claude Analysis (Pain Points + Personalization)
**Trigger:** After Stages 2 & 3 complete
**Cost:** ~$0.01-0.02 per lead

**Input:** All LinkedIn data from person + company

**Output:**
```json
{
  "pain_points": [
    "Scaling marketing team while maintaining quality",
    "Transitioning from founder-led sales"
  ],
  "personalization_angles": [
    "Recent post about hiring challenges",
    "Company just raised Series A"
  ],
  "icebreaker_hooks": {
    "email": "Your post about scaling teams resonated...",
    "linkedin": "Saw your take on founder-led sales...",
    "sms": "Quick q about your hiring push...",
    "voice": "Calling about your recent funding...",
    "direct_mail": "Congrats on the Series A..."
  },
  "common_ground": [
    "Both in B2B SaaS",
    "Similar company size challenges"
  ],
  "topics_to_avoid": [
    "Competitor mentioned positively in posts"
  ],
  "best_channel": "linkedin",
  "best_time": "Tuesday-Thursday, morning",
  "confidence": 0.85
}
```

---

### Stage 5: Clay Fallback (Optional)
**Trigger:** Only if Apollo + Apify fail validation
**Cost:** ~$0.15-0.50 per lead
**Limit:** Max 15% of batch

---

## Cost Summary

| Stage | Cost | When |
|-------|------|------|
| Apollo | ~$0.05 | Pool population |
| Apify Person | ~$0.03 | After assignment |
| Apify Company | ~$0.03 | After assignment |
| Claude Analysis | ~$0.02 | After scraping |
| **Total** | **~$0.13** | |

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ POOL POPULATION (Platform-wide)                                 │
│ └─ Apollo search → 50 fields                                    │
│ └─ Store in lead_pool (status: available)                       │
│ └─ NO LinkedIn scraping yet (save costs)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ POOL ASSIGNMENT (Client-specific)                               │
│ └─ Match lead to client ICP                                     │
│ └─ Create lead_assignments record                               │
│ └─ Trigger enrichment waterfall ──────────────────────┐         │
└─────────────────────────────────────────────────────────────────┘
                              ↓                         ↓
┌──────────────────────────────────┐  ┌──────────────────────────────────┐
│ APIFY: Person LinkedIn           │  │ APIFY: Company LinkedIn          │
│ └─ Profile + About               │  │ └─ Description + Specialties     │
│ └─ Last 5 posts                  │  │ └─ Last 5 company posts          │
│ └─ Experience history            │  │ └─ Hiring/announcements          │
└──────────────────────────────────┘  └──────────────────────────────────┘
                              ↓                         ↓
                              └───────────┬─────────────┘
                                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ CLAUDE ANALYSIS                                                 │
│ └─ Identify pain points from posts                              │
│ └─ Find personalization angles                                  │
│ └─ Generate icebreaker hooks (all 5 channels)                   │
│ └─ Detect topics to avoid                                       │
│ └─ Recommend best channel + timing                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ ALS SCORING (Enhanced)                                          │
│ └─ Apollo data (existing signals)                               │
│ └─ + LinkedIn engagement (post frequency, connections)          │
│ └─ + Company signals (growth, hiring, funding)                  │
│ └─ + Claude confidence score                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ OUTREACH READY                                                  │
│ └─ Personalized hooks for all 5 channels                        │
│ └─ Pain points identified                                       │
│ └─ Best channel + timing recommended                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Claude Analysis Prompt

```
You are analyzing a lead for sales outreach personalization.

## Lead Profile
Name: {first_name} {last_name}
Title: {title}
Company: {company_name}
Industry: {industry}

## Their LinkedIn Activity
Headline: {headline}
About: {about}

Recent Posts:
{posts}

## Their Company's LinkedIn Activity
Company Description: {company_description}
Recent Company Posts:
{company_posts}

## Your Task
Analyze this person and their company to identify:

1. **Pain Points**: What challenges are they likely facing based on their posts, role, and company stage?

2. **Personalization Angles**: What specific things from their posts/profile can we reference to show we've done our research?

3. **Icebreaker Hooks**: Write a 1-sentence opener for each channel:
   - Email (can be slightly longer)
   - LinkedIn (connection request limit)
   - SMS (very short, casual)
   - Voice (conversational opener)
   - Direct Mail (headline for letter)

4. **Topics to Avoid**: Anything that could backfire (competitor praise, sensitive topics)

5. **Best Channel**: Which channel is likely to get the best response from this person?

6. **Confidence**: How confident are you in this analysis (0-1)?

Return JSON format.
```

---

## Database Changes

### New Fields in `lead_assignments`

```sql
-- LinkedIn enrichment data
linkedin_scraped_at TIMESTAMPTZ,
linkedin_person_data JSONB,      -- Full person profile + posts
linkedin_company_data JSONB,     -- Full company profile + posts

-- Claude analysis output
personalization_data JSONB,      -- Pain points, angles, hooks
pain_points TEXT[],              -- Extracted for easy querying
icebreaker_hooks JSONB,          -- Per-channel hooks
best_channel channel_type,
analysis_confidence FLOAT,
analyzed_at TIMESTAMPTZ
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/orchestration/flows/pool_assignment_flow.py` | Trigger enrichment after assignment |
| `src/engines/scout.py` | Add company LinkedIn scraping |
| `src/engines/scorer.py` | Add LinkedIn signals to ALS |
| `src/agents/skills/research_skills.py` | Add company scraping + Claude analysis |
| `supabase/migrations/xxx_enrichment_fields.sql` | Add new fields |

---

## Success Criteria

- [ ] All assigned leads have LinkedIn person data
- [ ] All assigned leads have LinkedIn company data
- [ ] Claude generates pain points for 90%+ of leads
- [ ] Icebreaker hooks generated for all 5 channels
- [ ] Cost per fully enriched lead < $0.15
- [ ] Enrichment completes within 30 seconds per lead
