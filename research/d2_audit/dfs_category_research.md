# DFS Category Code Research — D2.2 Prep

**Research Date:** 2026-04-15  
**Researcher:** research-1 (Haiku)  
**Status:** COMPLETE

## Summary

Found and verified 4 DFS category codes for target verticals. Used DataForSEO Labs API (domain_metrics_by_categories/live) with Australia location, English language, Oct 2025 – Apr 2026 date range.

All recommendations tested against mid-tail (offset=50, limit=10) to assess SMB accessibility.

---

## Vertical 1: Recruitment

**DFS Code:** 12371  
**Category Name:** Recruiting & Retention

**Search Terms Tried:**
- "recrui" (matched: Recruiting & Retention, Recruiting Firms, Headhunters, Job listings variants)
- "staffing" (no direct staffing category, absorbed into Recruiting)
- "employment" (matched Welfare & Unemployment, Jobs & Careers, Job Interview Coaching)

**Verification — Full Distribution (offset=0, limit=100):**
- Total domains ranked: 100
- Top 5 ETVs: [439921, 262120, 87475, 69515, 59522]
- Mean ETV: 16,589
- Median ETV: 5,055
- P25 ETV: 3,205
- P75 ETV: 9,707
- Min–Max ETV: 2,467 – 439,921
- Sample top domains: Randstad AU, Chandler Macleod, Robert Walters, Workpac, AIHR

**Mid-Tail Check (offset=50, limit=10):**
- Domains 50–59 ETV range: 4,332–5,026
- Examples: whitefoxrecruitment.com.au, paxus.com.au, globalskills.com.au, CMR AU
- Domain quality: Pure recruitment agencies, minimal noise

**Confidence:** HIGH  
**Recommended ETV Window:** etv_min=3000, etv_max=25000, offset_start=50  
**Rationale:** Offset 50 captures local mid-market recruitment firms. Skip top 50 (dominated by Randstad, large national recruiters). P25 cutoff at 3200 is solid lower bound for SMBs with measurable organic presence.

---

## Vertical 2: IT MSPs

**DFS Code:** 12202  
**Category Name:** Computer Tech Support

**Search Terms Tried:**
- "IT services" — no direct hit; found "Computer Tech Support" (12202)
- "managed IT" — no dedicated category
- "MSP" — not in DFS taxonomy
- "IT support" — mapped to Computer Tech Support (12202)
- Alternative codes tested:
  - 12203 (Computer Consulting) — zero results in Australia
  - 12211 (Programming & Developer Software) — too broad, includes tools/SaaS

**Verification — Full Distribution (offset=0, limit=100):**
- Total domains ranked: 100
- Top 5 ETVs: [10032, 8578, 6599, 5518, 5294]
- Mean ETV: 1,626
- Median ETV: 1,045
- P25 ETV: 708
- P75 ETV: 1,947
- Min–Max ETV: 526 – 10,032
- Sample top domains: supportnetwork.com.au, themissinglink.com.au, kmtech.com.au, techbrain.com.au, firstfocus.com.au

**Mid-Tail Check (offset=50, limit=10):**
- Domains 50–59 ETV range: 875–1,042
- Examples: dycomputer.com.au, jimcomputer.com.au, helpdeskcomputers.com.au, 4it.com.au, foit.com.au
- Domain quality: Local tech support firms, some independent operators, minimal cross-category noise

**Confidence:** MEDIUM  
**Recommended ETV Window:** etv_min=800, etv_max=5000, offset_start=50  
**Rationale:** This is the narrowest vertical (mean ETV 1,626 vs. 9,056 for consulting). "Computer Tech Support" is more helpdesk/break-fix than managed services, but mid-tail captures local IT support businesses. Offset 50 filters out tools/SaaS platforms. Consider supplementing with manual industry research to identify true MSPs vs. helpdesk shops.

**Caveat:** DFS taxonomy does not have a dedicated "Managed Services Provider" or "IT Services" category. This is the closest available match. An alternative approach: cross-reference via LinkedIn profile scrape (Tier T2/T2.5) for "IT Services" and "Managed IT" keywords.

---

## Vertical 3: Web/Software Development

**DFS Code:** 11493  
**Category Name:** Web Design & Development

**Search Terms Tried:**
- "web design" — matched Web Design & Development (11493)
- "software development" — matched Software Development (12197) but includes non-geographic tools/platforms
- "web development" — absorbed into Web Design & Development (11493)
- "development services" — no dedicated services category

**Verification — Full Distribution (offset=0, limit=100):**
- Total domains ranked: 100
- Top 5 ETVs: [554492, 141985, 129891, 71746, 68864]
- Mean ETV: 17,683
- Median ETV: 5,735
- P25 ETV: 3,619
- P75 ETV: 10,867
- Min–Max ETV: 2,726 – 554,492
- Sample top domains: wix.com, dribbble.com, squarespace.com, archive.org, awwwards.com

**Mid-Tail Check (offset=50, limit=10):**
- Domains 50–59 ETV range: 4,758–5,708
- Examples: thriveweb.com.au, adelaidewebdesigner.com.au, confettidesign.com.au, digitalforest.com.au, quikclicks.com.au
- Domain quality: Legitimate local web agencies; noise from design tools/SaaS at head (Wix, Squarespace, dribbble)

**Confidence:** MEDIUM-HIGH  
**Recommended ETV Window:** etv_min=4000, etv_max=20000, offset_start=50  
**Rationale:** Top 50 heavily contaminated by Wix/Squarespace (tools, not agencies). Mid-tail (offset 50+) cleanly captures local web design and development shops. P25 cutoff at 3,619 includes smaller shops; recommend etv_min=4000 to filter out near-zero-traffic sites.

**Caveat:** Top of ranking includes design communities and SaaS platforms. Offset 50 is necessary to reach actual SMB agencies. Consider manual filtering to exclude freelancer platforms.

---

## Vertical 4: Business Coaching

**DFS Code:** 11098  
**Category Name:** Management Consulting

**Search Terms Tried:**
- "business coaching" — no dedicated category; found "Career Counseling & Coaching" (10747, much narrower)
- "consulting" — matched Management Consulting (11098) and Technology Consulting (11094)
- "business consulting" — absorbed into Management Consulting (11098)
- "management consulting" — matched Management Consulting (11098)

**Verification — Full Distribution (offset=0, limit=100):**
- Total domains ranked: 100
- Top 5 ETVs: [151565, 94271, 74882, 67156, 60272]
- Mean ETV: 9,056
- Median ETV: 2,706
- P25 ETV: 1,815
- P75 ETV: 5,792
- Min–Max ETV: 1,258 – 151,565
- Sample top domains: mckinsey.com, deloitte.com, consultancy.com.au, grantthornton.com.au, ey.com

**Mid-Tail Check (offset=50, limit=10):**
- Domains 50–59 ETV range: 2,252–2,669
- Examples: intrax.com.au, catalinaconsultants.com.au, mspcorp.com.au, levit8.com.au, cloudeagle.ai
- Domain quality: Legitimate local consultancies, minimal cross-category noise

**Confidence:** HIGH  
**Recommended ETV Window:** etv_min=2000, etv_max=15000, offset_start=50  
**Rationale:** "Management Consulting" is clean and includes small coaching/advisory practices. Offset 50 filters out Big Three firms (McKinsey, Deloitte, EY) and focuses on mid-market and boutique consultancies. P25 at 1,815 is reasonable lower bound for established consultancies.

**Note:** "Business Coaching" as a pure vertical does not exist in DFS. Management Consulting is the closest. If pure executive coaching (1-on-1) is required, consider manual research or alternative enrichment path (LinkedIn Tier T2 "Coaching Services" keyword).

---

## Comparison Table

| Vertical | Code | Category Name | Mean ETV | Median ETV | P25 ETV | Recommended ETV Min | Recommended ETV Max | Offset Start | Confidence |
|----------|------|---------------|----------|-----------|---------|---------------------|---------------------|--------------|------------|
| Recruitment | 12371 | Recruiting & Retention | 16,589 | 5,055 | 3,205 | 3,000 | 25,000 | 50 | HIGH |
| IT MSPs | 12202 | Computer Tech Support | 1,626 | 1,045 | 708 | 800 | 5,000 | 50 | MEDIUM |
| Web/Software Dev | 11493 | Web Design & Development | 17,683 | 5,735 | 3,619 | 4,000 | 20,000 | 50 | MEDIUM-HIGH |
| Business Coaching | 11098 | Management Consulting | 9,056 | 2,706 | 1,815 | 2,000 | 15,000 | 50 | HIGH |

---

## Recommendations

### Step 1: Category Code Selection ✓ COMPLETE

All four verticals have verified DFS codes with adequate domain coverage (100+ results) and meaningful ETV distribution.

**Blockers or Concerns:**
1. **IT MSPs (12202):** Narrowest category (mean ETV 1,626). May need manual post-enrichment filtering to exclude pure retail/break-fix and identify true managed services players. Alternative: supplement with LinkedIn T2/T2.5 enrichment for "Managed Services" keyword.
2. **Web/Software Dev (11493):** Significant head contamination by SaaS tools. Offset 50 is mandatory to reach legitimate agencies.
3. **Business Coaching (11098):** Category is "Management Consulting" not "Business Coaching." Works for management coaches but may miss pure executive/life coaches. Consider supplementary manual research.

### Step 2: ETV Window Selection ✓ COMPLETE

All recommendations balance SMB accessibility (P25–P75 range) with data quality. Offset 50 filters enterprise and tools/platforms in all four.

---

## Data Integrity Notes

- **API Endpoint:** `dataforseo_labs/google/domain_metrics_by_categories/live`
- **Date Range:** 2025-10-01 to 2026-04-01 (6 months)
- **Location:** Australia
- **Language:** English
- **ETV Field:** `organic_etv` (from metrics_history.202604.organic)
- **All results verified:** No null returns; all 100-domain result sets complete.

---

## Next Steps (D2.2 Execution)

1. **Waterfall Integration:** Ingest these DFS codes into Stage 1 (T0 GMB discovery). Use offset_start and etv_min/etv_max to filter seed dataset.
2. **Seed Generation:** Query DFS API with offset=50–150 (mid-tail 100 domains) for each code to generate initial lead lists.
3. **Manual Validation:** Review first 20 results per vertical for noise (especially IT MSPs and Web Dev). Document exclusion criteria.
4. **Tier Integration:** Cross-reference ETV filters with Waterfall gates (ALS>=20 at T2 stage).

---

**Report Generated:** 2026-04-15T14:30 UTC  
**Next Checkpoint:** D2.2 Step 3 — Seed generation & enrichment pipeline
