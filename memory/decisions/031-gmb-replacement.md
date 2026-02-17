# Decision: GMB Scraper Replacement

**Decision ID:** 031  
**Date:** 2026-02-17  
**Directive Chain:** #020 → #020a → #031  
**Status:** IMPLEMENTED

---

## What Was Replaced

**Old system:** `src/integrations/gmb_scraper.py`
- DIY Google Maps scraper using Playwright + Webshare proxies
- Dependencies: `tools/autonomous_browser.py`, `tools/proxy_manager.py`
- Location: src/integrations/gmb_scraper.py

**New system:** Bright Data Google Maps SERP API
- Professional SERP API service
- No browser automation needed
- Skill: `skills/enrichment/brightdata-gmb/`

---

## Why Replaced

### 1. Missing Infrastructure
The `tools/` directory containing `autonomous_browser.py` and `proxy_manager.py` was never restored after repo restructuring. Without these files, the DIY scraper cannot function.

### 2. Cost Reduction (75% savings)
| System | Cost | Basis |
|--------|------|-------|
| DIY Scraper | $0.006/lead | Proxy cost + compute |
| Bright Data SERP | $0.0015/request | API pricing |
| **Savings** | **75%** | |

### 3. Data Quality Improvement
| Field | DIY Scraper | Bright Data |
|-------|-------------|-------------|
| Phone | ✅ | ✅ |
| Website | ✅ | ✅ |
| Address | ✅ | ✅ |
| Hours | ✅ | ✅ |
| Rating | ✅ | ✅ |
| Reviews | ❌ | ✅ |
| Email | ❌ | ✅ |
| Social Media | ❌ | ✅ |

### 4. Reliability
- DIY: Brittle browser automation, CAPTCHA issues, proxy blocks
- Bright Data: Professional service with SLA, consistent results

---

## Validation

**Directive #020a (2026-02-16):** Tested Bright Data Google Maps SERP endpoint with query "marketing agency Melbourne". Returned structured JSON with business data.

**Directive #030b (2026-02-17):** Confirmed all Siege Waterfall tiers operational (except Tier 2 DIY which was blocked). This decision removes the blocker by replacing Tier 2.

---

## Implementation

1. ✅ Marked `src/integrations/gmb_scraper.py` as DEPRECATED (header comment)
2. ✅ Created `skills/enrichment/brightdata-gmb/` skill
3. ✅ Updated MEMORY.md with deprecation notice
4. ✅ Updated SKILL_INDEX.md with new skill
5. ⏳ Supabase ceo_memory table update (pending)
6. ❌ File deletion deferred to future cleanup (Dave decision)

---

## Governance Trace

- **#020:** Bright Data platform audit
- **#020a:** Google Maps SERP validation
- **#031:** Formal deprecation and skill creation

---

*Decision documented by Elliot, 2026-02-17*
