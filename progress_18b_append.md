
---

## PHASE 18-B: ICP Enrichment Pipeline Fix (NEW)

**Purpose:** Fix empty ICP fields despite successful scraping + add social media enrichment
**Created:** January 5, 2026
**Diagnosis:** Railway logs confirmed portfolio data loss in summarization stage
**Priority:** 🔴 CRITICAL - Blocks M1 (Onboarding)
**Full Spec:** `docs/progress/PHASE_18B_ICP_FIX.md`

### Problem Summary

Pipeline loses portfolio company names during website parsing. Raw HTML contains Vermeer, Kustom Timber, APM etc. but they're lost in summarization before PortfolioExtractor sees them.

### Task Summary

| Sub-Phase | Description | Tasks | Status |
|-----------|-------------|-------|--------|
| 18-B-A | Fix Portfolio Data Loss | 5 | 🔴 |
| 18-B-B | Social Media Enrichment | 6 | 🔴 |
| 18-B-C | Enhanced Data Points | 6 | 🔴 |
| 18-B-D | ICP Display Enhancement | 6 | 🔴 |
| **TOTAL** | | **23** | 🔴 |

### Critical Path (Phase 1)

| Task | Description | Status |
|------|-------------|--------|
| ICP-FIX-001 | Add raw_html input to PortfolioExtractor | 🔴 |
| ICP-FIX-002 | Update prompt to extract names from HTML | 🔴 |
| ICP-FIX-003 | Pass raw_html from agent to skill | 🔴 |
| ICP-FIX-004 | Add logging for company extraction | 🔴 |
| ICP-FIX-005 | Test with dilate.com.au | 🔴 |

### New Data Sources (Phase 2)

| Source | Data Points | Actor |
|--------|-------------|-------|
| LinkedIn | Size, specialties, posts | curious_coder/linkedin-company-scraper |
| Instagram | Followers, engagement | apify/instagram-profile-scraper |
| Facebook | Likes, reviews | apify/facebook-pages-scraper |
| Google Business | Rating, reviews | apify/google-maps-scraper |

### Success Criteria

- [ ] Target Industries populated (not empty)
- [ ] Target Company Sizes populated (not empty)
- [ ] Confidence > 70% (currently 50%)
- [ ] Portfolio companies extracted from testimonials

---

