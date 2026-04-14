# Discovery vs Verification Principle

## Core Principle

Discovery layers find candidates. Verification layers confirm facts. Never auto-trust discovery results.

## Pattern

1. **Discovery** (SERP, Gemini grounding, public index search): Returns candidate data — URLs, names, identifiers. These are hypotheses, not facts.
2. **Verification** (profile scraper, ABR registry, direct API): Scrapes or queries the authoritative source to confirm the candidate is correct.
3. **Post-filter** (fuzzy match, field comparison): Compares verified data against known facts (F3a business_name, DM name) to accept or reject.

## Applications

### ABN Resolution (F4)
- Discovery: DFS SERP query `"{business_name}" ABN site:abr.business.gov.au`
- Verification: ABR snippet contains 11-digit ABN pattern
- Source of truth: ABR registry

### DM LinkedIn Identity (F5 L2)
- Discovery: DFS SERP query `site:linkedin.com/in {dm_name} {business_name}` → candidate URL
- Verification: `harvestapi/linkedin-profile-scraper` scrapes candidate URL → returns experience[], headline
- Post-filter: experience[].company fuzzy match vs F3a business_name (>=85% direct, >=75% related)
- Source of truth: LinkedIn profile data

### Company LinkedIn URL (F4)
- Discovery: DFS SERP query `site:linkedin.com/company "{business_name}"`
- Verification: First `/company/` URL in top 3 results accepted (SERP is authoritative for URL existence)
- Source of truth: Google index of LinkedIn

### GMB Data (future)
- Discovery: DFS Maps SERP
- Verification: Direct GMB data fields
- Source of truth: Google Maps listing

## Anti-pattern: Auto-trust

Never assign `match_type=direct_match` or persist a URL as verified based solely on discovery results. The SERP query `site:linkedin.com/in David Fitzgerald Taxopia` returns Claire Arnold (landscape designer, Hobart) and David Fitzgerald (Factor1, not Taxopia) — both wrong-person matches that look plausible at discovery but fail at verification.

## Ratified

2026-04-14, F-CONTAMINATION-01. Both false-positive cases (Factor1 David, Hobart landscape designer) confirmed and rejected by verification layer.
