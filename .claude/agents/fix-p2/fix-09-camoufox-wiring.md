---
name: Fix 09 - Camoufox Scraper Wiring
description: Wires Camoufox into scraper waterfall as Tier 3
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 09: Camoufox Scraper Not Wired

## Gap Reference
- **TODO.md Item:** #9
- **Priority:** P2 High
- **Location:** `src/engines/scout.py` or scraper waterfall
- **Issue:** Tier 3 code exists, not called in waterfall

## Pre-Flight Checks

1. Find Camoufox code:
   ```bash
   grep -rn "camoufox\|Camoufox" src/
   find src/ -name "*camoufox*"
   ```

2. Find scraper waterfall logic:
   ```bash
   grep -rn "waterfall\|tier.*3\|fallback" src/engines/scout.py
   ```

3. Read SCRAPER_WATERFALL.md to understand expected flow:
   ```bash
   cat docs/architecture/distribution/SCRAPER_WATERFALL.md
   ```

## Implementation Steps

1. **Understand the waterfall structure:**
   - Tier 1: Primary scraper (fastest/cheapest)
   - Tier 2: Secondary scraper (backup)
   - Tier 3: Camoufox (anti-detection, last resort)

2. **Locate scraping function** in scout.py or equivalent

3. **Add Camoufox as Tier 3 fallback:**
   ```python
   from src.integrations.camoufox import CamoufoxScraper

   async def scrape_profile(url: str, ...) -> Dict:
       # Tier 1: Primary
       result = await primary_scraper.scrape(url)
       if result:
           return result

       # Tier 2: Secondary
       result = await secondary_scraper.scrape(url)
       if result:
           return result

       # Tier 3: Camoufox (anti-detection)
       result = await camoufox_scraper.scrape(url)
       if result:
           return result

       raise ScrapingFailedError(f"All tiers failed for {url}")
   ```

4. **Add appropriate error handling** and logging

5. **Respect rate limits** for Camoufox (likely slower/more expensive)

## Acceptance Criteria

- [ ] Camoufox imported in scraper module
- [ ] Camoufox called as Tier 3 fallback
- [ ] Only called when Tier 1 and 2 fail
- [ ] Proper error handling
- [ ] Logging when Camoufox is invoked
- [ ] Rate limiting respected

## Validation

```bash
# Check Camoufox is imported
grep -n "camoufox\|Camoufox" src/engines/scout.py

# Check waterfall has 3 tiers
grep -n "tier\|fallback" src/engines/scout.py

# Verify no syntax errors
python -m py_compile src/engines/scout.py

# Type check
mypy src/engines/scout.py --ignore-missing-imports
```

## Post-Fix

1. Update TODO.md — delete gap row #9
2. Report: "Fixed #9. Camoufox now wired as Tier 3 in scraper waterfall."
