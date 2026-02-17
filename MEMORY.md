# MEMORY.md — Agency OS Long-Term Memory

*Curated decisions, lessons, and persistent context.*

---

## Enrichment Infrastructure

### Tier 2 GMB: DIY Scraper DEPRECATED
**As of:** CEO Directive #031 (2026-02-17)

The DIY GMB scraper (`src/integrations/gmb_scraper.py`) has been **DEPRECATED**.

**Replaced by:** Bright Data Google Maps SERP at $0.0015/request.

**Validation:** Directive #020a (2026-02-16)

**New skill:** `skills/enrichment/brightdata-gmb/`

**Why deprecated:**
- Missing dependencies: `tools/autonomous_browser.py`, `tools/proxy_manager.py` never restored
- Cost: $0.006/lead (DIY) vs $0.0015/request (Bright Data) = 75% savings
- Quality: Bright Data returns email, phone, website, social media, reviews
- Reliability: Professional API vs brittle browser automation

The `tools/` directory (autonomous_browser.py, proxy_manager.py) is **no longer needed**.

---

## Credential Locations

**Primary .env:** `/home/elliotbot/.config/agency-os/.env`  
**Symlink:** `/home/elliotbot/clawd/.env` → primary

**Critical credentials (verified 2026-02-17):**
- `ABN_LOOKUP_GUID` — Tier 1 ABN Lookup (FREE)
- `BRIGHTDATA_API_KEY` — Tiers 1.5, 2 (LinkedIn, GMB)
- `HUNTER_API_KEY` — Tier 3 (email discovery)

---

## Enrichment Skills Created

**Location:** `skills/enrichment/`  
**Created:** CEO Directive #031 (2026-02-17)

| Skill | Tier | Cost | Status |
|-------|------|------|--------|
| abn-lookup | 1 | FREE | ✅ |
| brightdata-linkedin | 1.5 | ~$0.01 | ✅ |
| brightdata-gmb | 2 | $0.0015 | ✅ |
| hunter-verify | 3 | $0.15 | ✅ |

---

*Last Updated: 2026-02-17*
