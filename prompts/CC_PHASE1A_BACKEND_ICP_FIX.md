# CC Prompt: ICP Phase 1A - Portfolio Fix + Social Enrichment (Backend)

## Context

You are working on Agency OS, a multi-channel client acquisition SaaS for Australian marketing agencies. The ICP (Ideal Customer Profile) extraction pipeline is broken.

### Current Problem

When a user submits their website URL during onboarding, the system scrapes the site and extracts their ICP. However, testing with `dilate.com.au` shows:

- ✅ Website scraped successfully (11 pages, 401KB HTML)
- ✅ Services extracted correctly (SEO, PPC, Web Design, etc.)
- ❌ Portfolio companies NOT extracted (empty list)
- ❌ Target Industries empty
- ❌ Target Company Sizes empty  
- ❌ Target Locations empty
- ❌ Confidence score only 50%

### Root Cause (Diagnosed)

The `PortfolioExtractorSkill` only receives summarized `PageContent` objects, NOT the raw HTML. The summarization step loses the actual client names that appear in testimonials and case studies.

**Evidence from dilate.com.au raw HTML:**
- Testimonials mention: Vermeer, APM, Kustom Timber, Spinifex Sheds, Pure Running, Creatures of Comfort
- Case studies reference: True North, Arcadia, Australian Fire Control, Advanced Dental Artistry

But `PortfolioExtractorSkill` only sees boolean flags: `has_testimonials: True`, `has_case_studies: True` — the actual company names are lost.

### The ICP Derivation Chain

```
1. Scrape website → raw_html (401KB)
2. Parse website → PageContent[] (summarized, loses names)
3. Extract portfolio → PortfolioCompany[] (currently empty because no names visible)
4. Enrich via Apollo → EnrichedCompany[] (empty because no companies to enrich)
5. Derive ICP → empty target fields (no data to derive from)
```

---

## Reference Files

Read these files to understand the current implementation:

| File | Purpose |
|------|---------|
| `src/agents/icp_discovery_agent.py` | Main orchestrator - calls skills in sequence |
| `src/agents/skills/portfolio_extractor.py` | Extracts portfolio companies from pages |
| `src/agents/skills/website_parser.py` | Parses raw HTML into PageContent objects |
| `src/agents/skills/icp_deriver.py` | Derives ICP from enriched portfolio |
| `src/integrations/apify.py` | Apify client for web scraping |
| `src/engines/icp_scraper.py` | Scraping engine that returns ScrapedWebsite |
| `src/models/` | Existing Pydantic models |

---

## Tasks

### Task 1: Fix Portfolio Data Loss

**Problem:** `PortfolioExtractorSkill.Input` only accepts `pages: list[PageContent]` but needs access to raw HTML to extract company names from testimonials.

**Requirements:**
1. Add `raw_html: str` field to `PortfolioExtractorSkill.Input`
2. Update `build_prompt()` to extract relevant sections from raw HTML (testimonials, case studies, client logos) and include them in the prompt
3. Update the system prompt to emphasize extracting ALL company names from testimonials, case study attributions, and client logo alt text
4. Update `ICPDiscoveryAgent.extract_icp()` to pass `scraped.raw_html` when calling the portfolio extractor skill

### Task 2: Extract Social Links from Website

**Problem:** We don't capture social media URLs from the agency's website.

**Requirements:**
1. Add `social_links: dict[str, str]` field to `PageContent` model in `website_parser.py`
2. Update `WebsiteParserSkill` system prompt to extract LinkedIn, Instagram, Facebook, Twitter URLs from header/footer
3. Expected format: `{"linkedin": "url", "instagram": "url", "facebook": "url", "twitter": "url"}`

### Task 3: Add Social Media Scrapers to Apify Client

**Problem:** We need to enrich ICP with social media data for a more complete profile.

**Requirements:**
1. Add method `scrape_linkedin_company(linkedin_url: str)` using actor `curious_coder/linkedin-company-scraper`
   - Returns: name, followers, employee_count, specialties, description, industry, headquarters
2. Add method `scrape_instagram_profile(instagram_url: str)` using actor `apify/instagram-profile-scraper`
   - Returns: username, followers, following, posts_count, bio, is_verified
3. Add method `scrape_facebook_page(facebook_url: str)` using actor `apify/facebook-pages-scraper`
   - Returns: name, likes, followers, category, about, rating, review_count
4. Add method `scrape_google_business(business_name: str, location: str)` using actor `apify/google-maps-scraper`
   - Returns: name, rating, review_count, address, phone, website

Follow the existing pattern in `apify.py` for actor calls and error handling.

### Task 4: Create Social Profile Models

**Requirements:**
1. Create new file `src/models/social_profile.py`
2. Create Pydantic models for: `LinkedInCompanyProfile`, `InstagramProfile`, `FacebookPageProfile`, `GoogleBusinessProfile`
3. Create aggregate model `SocialProfiles` containing optional instances of each
4. Add `total_social_followers` property that sums followers across platforms

### Task 5: Integrate Social Scraping into ICP Agent

**Requirements:**
1. After website parsing, collect all `social_links` from parsed pages
2. Add helper method `_scrape_social_profiles(social_links, company_name)` that:
   - Scrapes LinkedIn if URL available
   - Scrapes Instagram if URL available
   - Scrapes Facebook if URL available
   - Always searches Google Business by company name + "Australia"
   - Returns `SocialProfiles` object
   - Handles errors gracefully (log warning, continue with other platforms)
3. Add `social_profiles: Optional[SocialProfiles]` and `social_links: dict` fields to `ICPProfile`
4. Populate these fields in the profile building section

---

## Constraints

1. Follow existing code patterns and style in each file
2. Use existing error handling patterns (`APIError`, `IntegrationError`)
3. All Apify actor calls should use `{"useApifyProxy": True}` for proxy
4. Keep token usage reasonable - don't send full 400KB HTML to Claude, extract relevant sections only (testimonials, case studies, client logos)
5. Social scraping should be non-blocking - if one platform fails, continue with others
6. Add appropriate logging at INFO level for scraping actions
7. Maintain type hints on all new methods and fields
8. No hardcoded API keys or credentials

---

## Testing

After implementation, test with:
- URL: `https://www.dilate.com.au`

**Expected Results:**
- `portfolio_companies` contains: Vermeer, Kustom Timber, APM, Spinifex Sheds, Pure Running, etc.
- `social_links` populated with LinkedIn, Instagram, Facebook URLs found on site
- `social_profiles.linkedin` has follower count and employee range
- `social_profiles.google_business` has rating and review count
- `icp_industries` populated (Mining, Construction, Healthcare, Retail from portfolio analysis)
- `icp_company_sizes` populated (derived from enriched portfolio)
- `confidence` > 0.70

---

## Success Criteria

- [ ] Portfolio extractor receives and uses raw HTML
- [ ] Company names extracted from testimonials (Vermeer, APM, etc.)
- [ ] Social links extracted from website header/footer
- [ ] All 4 social scraper methods implemented in Apify client
- [ ] SocialProfiles model created with all platform models
- [ ] ICP agent orchestrates social scraping after website parsing
- [ ] ICPProfile includes social_profiles and social_links
- [ ] Test with dilate.com.au shows populated ICP fields
