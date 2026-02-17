# Long-Term Memory

This file contains curated memories and learnings from daily operations.

## CEO Directives

### Directive #031 - Enrichment Skills + GMB Replacement (2026-02-17)

Tier 2 GMB: DIY scraper (gmb_scraper.py) DEPRECATED as of Directive #031. Replaced by Bright Data Google Maps SERP at $0.0015/request. Validated in Directive #020a. Skill: skills/enrichment/brightdata-gmb/. The tools/ directory (autonomous_browser.py, proxy_manager.py) is no longer needed.

**Key Changes:**
- Created four enrichment skills in skills/enrichment/
- Deprecated src/integrations/gmb_scraper.py
- Cost reduction: $0.006/lead → $0.0015/request (75% savings)
- Improved data quality and reliability

**Skills Created:**
1. **ABN Lookup** - Australian Business Number lookups via ABR Web Services
2. **Bright Data LinkedIn** - LinkedIn profile extraction via dataset gd_l1vikfnt1wgvvqz95w  
3. **Bright Data GMB** - Google Maps business search replacing DIY scraper
4. **Hunter Verify** - Email verification via Hunter.io (free plan, 50/cycle)

## Technical Architecture

### Siege Waterfall Tiers
- **Tier 1:** ABN lookups (working)
- **Tier 1.5:** Enhanced ABN data (working)  
- **Tier 2:** GMB search - NOW USING Bright Data instead of DIY scraper
- **Tier 3:** Additional enrichment (working)

### Integration Patterns
- Skills wrap existing src/integrations/ code or call APIs directly
- No refactoring of src/integrations/ - skills are additive
- Standard skill structure: SKILL.md, run.py, test.py, .env.example

## Lessons Learned

### API Integration
- Always implement proper error handling for external APIs
- Include rate limiting and quota awareness
- Provide clear deprecation warnings when replacing components

### Cost Optimization
- Bright Data GMB: 75% cost reduction vs DIY scraping
- Free/freemium APIs (ABN, Hunter free plan) provide good baseline capability
- External services more reliable than DIY scraping solutions

### Skill Development
- Follow established patterns for consistency
- Include comprehensive test cases
- Document API limits and costs clearly