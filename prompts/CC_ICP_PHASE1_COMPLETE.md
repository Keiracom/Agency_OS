# CC Prompt: ICP Phase 1 - Portfolio Fix + Social Enrichment

## Context

The ICP extraction pipeline is broken. When scraping `dilate.com.au`:
- ✅ 11 pages scraped (401KB HTML)
- ✅ Services extracted correctly
- ❌ Portfolio companies NOT extracted (company names lost in summarization)
- ❌ ICP fields empty (Target Industries, Sizes, Locations)

**Root Cause:** `PortfolioExtractorSkill` only sees summarized `PageContent`, not the raw HTML containing actual client names (Vermeer, Kustom Timber, APM, etc.)

## Task

Implement two fixes:

### Fix A: Pass Raw HTML to Portfolio Extractor
Make the portfolio extractor see the raw HTML so it can extract actual company names from testimonials and case studies.

### Fix B: Add Social Media Enrichment
Extract social links from website, then scrape LinkedIn/Instagram/Facebook/Google Business for additional data.

---

## Files to Modify

### 1. `src/agents/skills/website_parser.py`

Add `social_links` field to `PageContent` model:

```python
class PageContent(BaseModel):
    # ... existing fields ...
    
    social_links: dict[str, str] = Field(
        default_factory=dict,
        description="Social media URLs found: {linkedin: url, instagram: url, facebook: url, twitter: url}"
    )
```

Update the system prompt to extract social links from header/footer.

### 2. `src/agents/skills/portfolio_extractor.py`

Add `raw_html` input field:

```python
class Input(BaseModel):
    pages: list[PageContent] = Field(...)
    company_name: str = Field(default="")
    raw_html: str = Field(
        default="",
        description="Raw HTML for direct company name extraction"
    )
```

Update `build_prompt()` to include raw HTML excerpts when available:

```python
def build_prompt(self, input_data: Input) -> str:
    # ... existing code ...
    
    # Add raw HTML section for testimonial/case study extraction
    if input_data.raw_html and len(input_data.raw_html) > 100:
        # Extract testimonial and case study sections
        html_excerpt = self._extract_relevant_sections(input_data.raw_html)
        prompt += f"\n\nRAW HTML (testimonials/case studies sections):\n{html_excerpt}"
    
    return prompt

def _extract_relevant_sections(self, html: str, max_chars: int = 15000) -> str:
    """Extract testimonial and case study sections from raw HTML."""
    import re
    
    sections = []
    
    # Find testimonial sections
    testimonial_patterns = [
        r'(?i)class=["\'][^"\']*testimonial[^"\']*["\'][^>]*>(.{500,3000}?)</div>',
        r'(?i)<blockquote[^>]*>(.{100,1000}?)</blockquote>',
        r'(?i)(?:said|says|testified|commented)[^<]{50,500}',
    ]
    
    # Find case study sections
    case_study_patterns = [
        r'(?i)class=["\'][^"\']*case.?stud[^"\']*["\'][^>]*>(.{500,3000}?)</div>',
        r'(?i)class=["\'][^"\']*portfolio[^"\']*["\'][^>]*>(.{500,3000}?)</div>',
        r'(?i)class=["\'][^"\']*client[^"\']*["\'][^>]*>(.{500,3000}?)</div>',
    ]
    
    # Find "trusted by" / client logo sections
    client_patterns = [
        r'(?i)(?:trusted by|our clients|we work with|partnered with)[^<]{50,500}',
        r'(?i)alt=["\']([^"\']{3,50}?)["\']',  # Image alt text for logos
    ]
    
    for pattern in testimonial_patterns + case_study_patterns + client_patterns:
        matches = re.findall(pattern, html)
        sections.extend(matches[:10])  # Limit matches per pattern
    
    combined = "\n---\n".join(sections)
    return combined[:max_chars]
```

Update the system prompt to emphasize extracting company names:

```python
system_prompt = """You are a portfolio analyst extracting client information from agency websites.

CRITICAL: Extract ALL company names mentioned in:
- Testimonial quotes (look for "— Name, Company" or "from Company")
- Case study sections (client names, results achieved)
- Client logo sections (alt text, image descriptions)
- "Trusted by" or "Our Clients" sections

EXTRACTION GUIDELINES:
...existing guidelines...
"""
```

### 3. `src/integrations/apify.py`

Add social media scraping methods:

```python
# Actor IDs for social scraping
LINKEDIN_COMPANY_SCRAPER = "curious_coder/linkedin-company-scraper"
INSTAGRAM_SCRAPER = "apify/instagram-profile-scraper"
FACEBOOK_SCRAPER = "apify/facebook-pages-scraper"
GOOGLE_MAPS_SCRAPER = "apify/google-maps-scraper"

async def scrape_linkedin_company(self, linkedin_url: str) -> dict[str, Any]:
    """
    Scrape LinkedIn company page.
    
    Returns:
        {
            "name": str,
            "url": str,
            "followers": int,
            "employee_count": str,  # "11-50", "51-200", etc.
            "specialties": list[str],
            "description": str,
            "website": str,
            "industry": str,
            "headquarters": str,
        }
    """
    actor = self._get_actor(self.LINKEDIN_COMPANY_SCRAPER)
    
    run_input = {
        "startUrls": [{"url": linkedin_url}],
        "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
    }
    
    try:
        run = actor.call(run_input=run_input)
        dataset = self._client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())
        
        if items:
            item = items[0]
            return {
                "name": item.get("name"),
                "url": linkedin_url,
                "followers": item.get("followerCount"),
                "employee_count": item.get("employeeCountRange"),
                "specialties": item.get("specialities", []),
                "description": item.get("description"),
                "website": item.get("website"),
                "industry": item.get("industry"),
                "headquarters": item.get("headquarter", {}).get("city"),
            }
        return {}
    except Exception as e:
        raise APIError(
            service="apify",
            status_code=500,
            message=f"LinkedIn company scrape failed: {str(e)}",
        )

async def scrape_instagram_profile(self, instagram_url: str) -> dict[str, Any]:
    """
    Scrape Instagram profile.
    
    Returns:
        {
            "username": str,
            "url": str,
            "followers": int,
            "following": int,
            "posts_count": int,
            "bio": str,
            "is_verified": bool,
        }
    """
    actor = self._get_actor(self.INSTAGRAM_SCRAPER)
    
    # Extract username from URL
    username = instagram_url.rstrip("/").split("/")[-1]
    
    run_input = {
        "usernames": [username],
        "resultsLimit": 1,
    }
    
    try:
        run = actor.call(run_input=run_input)
        dataset = self._client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())
        
        if items:
            item = items[0]
            return {
                "username": item.get("username"),
                "url": instagram_url,
                "followers": item.get("followersCount"),
                "following": item.get("followsCount"),
                "posts_count": item.get("postsCount"),
                "bio": item.get("biography"),
                "is_verified": item.get("verified", False),
            }
        return {}
    except Exception as e:
        raise APIError(
            service="apify",
            status_code=500,
            message=f"Instagram scrape failed: {str(e)}",
        )

async def scrape_facebook_page(self, facebook_url: str) -> dict[str, Any]:
    """
    Scrape Facebook page.
    
    Returns:
        {
            "name": str,
            "url": str,
            "likes": int,
            "followers": int,
            "category": str,
            "about": str,
            "rating": float,
            "review_count": int,
        }
    """
    actor = self._get_actor(self.FACEBOOK_SCRAPER)
    
    run_input = {
        "startUrls": [{"url": facebook_url}],
        "maxPosts": 0,  # Don't need posts
    }
    
    try:
        run = actor.call(run_input=run_input)
        dataset = self._client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())
        
        if items:
            item = items[0]
            return {
                "name": item.get("name"),
                "url": facebook_url,
                "likes": item.get("likes"),
                "followers": item.get("followers"),
                "category": item.get("categories", [None])[0] if item.get("categories") else None,
                "about": item.get("about"),
                "rating": item.get("overallStarRating"),
                "review_count": item.get("reviewCount"),
            }
        return {}
    except Exception as e:
        raise APIError(
            service="apify",
            status_code=500,
            message=f"Facebook page scrape failed: {str(e)}",
        )

async def scrape_google_business(self, business_name: str, location: str = "Australia") -> dict[str, Any]:
    """
    Scrape Google Business listing.
    
    Returns:
        {
            "name": str,
            "rating": float,
            "review_count": int,
            "address": str,
            "phone": str,
            "website": str,
            "place_id": str,
        }
    """
    actor = self._get_actor(self.GOOGLE_MAPS_SCRAPER)
    
    run_input = {
        "searchStringsArray": [f"{business_name} {location}"],
        "maxCrawledPlacesPerSearch": 1,
        "language": "en",
        "includeReviews": False,
    }
    
    try:
        run = actor.call(run_input=run_input)
        dataset = self._client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())
        
        if items:
            item = items[0]
            return {
                "name": item.get("title"),
                "rating": item.get("totalScore"),
                "review_count": item.get("reviewsCount"),
                "address": item.get("address"),
                "phone": item.get("phone"),
                "website": item.get("website"),
                "place_id": item.get("placeId"),
            }
        return {}
    except Exception as e:
        raise APIError(
            service="apify",
            status_code=500,
            message=f"Google Business scrape failed: {str(e)}",
        )
```

### 4. `src/models/social_profile.py` (NEW FILE)

Create model for social data:

```python
"""
FILE: src/models/social_profile.py
PURPOSE: Models for social media profile data
PHASE: 18-B (ICP Enrichment)
"""

from pydantic import BaseModel, Field
from typing import Optional


class LinkedInCompanyProfile(BaseModel):
    """LinkedIn company page data."""
    url: str
    name: Optional[str] = None
    followers: Optional[int] = None
    employee_count: Optional[str] = None
    specialties: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    industry: Optional[str] = None
    headquarters: Optional[str] = None


class InstagramProfile(BaseModel):
    """Instagram profile data."""
    url: str
    username: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    posts_count: Optional[int] = None
    bio: Optional[str] = None
    is_verified: bool = False


class FacebookPageProfile(BaseModel):
    """Facebook page data."""
    url: str
    name: Optional[str] = None
    likes: Optional[int] = None
    followers: Optional[int] = None
    category: Optional[str] = None
    about: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None


class GoogleBusinessProfile(BaseModel):
    """Google Business listing data."""
    name: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    place_id: Optional[str] = None


class SocialProfiles(BaseModel):
    """Aggregated social profiles for a company."""
    linkedin: Optional[LinkedInCompanyProfile] = None
    instagram: Optional[InstagramProfile] = None
    facebook: Optional[FacebookPageProfile] = None
    google_business: Optional[GoogleBusinessProfile] = None
    
    @property
    def total_social_followers(self) -> int:
        """Total followers across platforms."""
        total = 0
        if self.linkedin and self.linkedin.followers:
            total += self.linkedin.followers
        if self.instagram and self.instagram.followers:
            total += self.instagram.followers
        if self.facebook and self.facebook.followers:
            total += self.facebook.followers
        return total
```

### 5. `src/agents/icp_discovery_agent.py`

Update to:
1. Pass `raw_html` to portfolio extractor
2. Extract social links from parsed pages
3. Scrape social profiles
4. Include social data in ICPProfile

```python
# Add import
from src.models.social_profile import SocialProfiles, LinkedInCompanyProfile, InstagramProfile, FacebookPageProfile, GoogleBusinessProfile

# Update ICPProfile model - add after existing fields:
class ICPProfile(BaseModel):
    # ... existing fields ...
    
    # Social profiles (NEW)
    social_profiles: Optional[SocialProfiles] = Field(
        default=None,
        description="Social media profiles data"
    )
    social_links: dict[str, str] = Field(
        default_factory=dict,
        description="Social media URLs"
    )

# In extract_icp method, update portfolio extraction call:
portfolio_task = self.use_skill(
    "extract_portfolio",
    pages=[p.model_dump() for p in parsed.pages],
    company_name=parsed.company_name,
    raw_html=scraped.raw_html,  # ADD THIS LINE
)

# After Step 3 (parallel extraction), add Step 3.5 - Social Media Scraping:
# Step 3.5: Extract and scrape social profiles
social_links = {}
for page in parsed.pages:
    if hasattr(page, 'social_links') and page.social_links:
        social_links.update(page.social_links)

social_profiles = None
if social_links:
    social_profiles = await self._scrape_social_profiles(social_links, parsed.company_name)

# Add helper method to class:
async def _scrape_social_profiles(
    self,
    social_links: dict[str, str],
    company_name: str,
) -> SocialProfiles:
    """
    Scrape all available social profiles.
    
    Args:
        social_links: Dict of platform -> URL
        company_name: Company name for Google Business search
        
    Returns:
        SocialProfiles with all available data
    """
    from src.integrations.apify import get_apify_client
    import logging
    
    logger = logging.getLogger(__name__)
    apify = get_apify_client()
    
    profiles = SocialProfiles()
    
    # LinkedIn
    if linkedin_url := social_links.get("linkedin"):
        try:
            logger.info(f"Scraping LinkedIn: {linkedin_url}")
            data = await apify.scrape_linkedin_company(linkedin_url)
            if data:
                profiles.linkedin = LinkedInCompanyProfile(url=linkedin_url, **data)
        except Exception as e:
            logger.warning(f"LinkedIn scrape failed: {e}")
    
    # Instagram
    if instagram_url := social_links.get("instagram"):
        try:
            logger.info(f"Scraping Instagram: {instagram_url}")
            data = await apify.scrape_instagram_profile(instagram_url)
            if data:
                profiles.instagram = InstagramProfile(url=instagram_url, **data)
        except Exception as e:
            logger.warning(f"Instagram scrape failed: {e}")
    
    # Facebook
    if facebook_url := social_links.get("facebook"):
        try:
            logger.info(f"Scraping Facebook: {facebook_url}")
            data = await apify.scrape_facebook_page(facebook_url)
            if data:
                profiles.facebook = FacebookPageProfile(url=facebook_url, **data)
        except Exception as e:
            logger.warning(f"Facebook scrape failed: {e}")
    
    # Google Business (search by company name)
    try:
        logger.info(f"Searching Google Business: {company_name}")
        data = await apify.scrape_google_business(company_name, "Australia")
        if data:
            profiles.google_business = GoogleBusinessProfile(**data)
    except Exception as e:
        logger.warning(f"Google Business search failed: {e}")
    
    return profiles

# Update profile building at the end:
profile = ICPProfile(
    # ... existing fields ...
    social_profiles=social_profiles,
    social_links=social_links,
)
```

### 6. Update `src/agents/skills/website_parser.py` System Prompt

Add to the system prompt:

```python
SOCIAL MEDIA EXTRACTION:
Look in the header and footer for social media links:
- LinkedIn: linkedin.com/company/...
- Instagram: instagram.com/...
- Facebook: facebook.com/...
- Twitter/X: twitter.com/... or x.com/...

Return in social_links field:
{
    "linkedin": "https://linkedin.com/company/example",
    "instagram": "https://instagram.com/example",
    "facebook": "https://facebook.com/example",
    "twitter": "https://twitter.com/example"
}
```

---

## Testing

After implementation, test with:

```python
# Test URL
url = "https://www.dilate.com.au"

# Expected results:
# - Portfolio companies: Vermeer, Kustom Timber, APM, Spinifex Sheds, Pure Running, etc.
# - Social links extracted
# - LinkedIn company data populated
# - Google Business rating populated
# - ICP industries populated (not empty)
# - ICP company sizes populated (not empty)
# - Confidence > 70%
```

---

## Success Criteria

- [ ] `portfolio_companies` list contains actual client names (not empty)
- [ ] `social_profiles.linkedin` populated with follower count, employee range
- [ ] `social_profiles.google_business` populated with rating, reviews
- [ ] `icp_industries` populated (Mining, Construction, Healthcare, etc.)
- [ ] `icp_company_sizes` populated (50-200, 200-500, etc.)
- [ ] `icp_locations` populated (Perth, Western Australia, etc.)
- [ ] `confidence` > 0.70 (was 0.50)

---

## Estimated Cost Impact

| Operation | Cost per Agency |
|-----------|-----------------|
| Website scrape (existing) | ~$0.01 |
| LinkedIn Company | ~$0.50 |
| Instagram | ~$0.02 |
| Facebook | ~$0.02 |
| Google Business | ~$0.02 |
| Apollo enrichment (existing) | ~$0.31 |
| **Total** | **~$0.88** |

For 100 founding customers: ~$88 total enrichment cost
