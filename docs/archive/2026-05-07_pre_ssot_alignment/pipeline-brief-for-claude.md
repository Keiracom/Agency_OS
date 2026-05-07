# AGENCY OS — NEW DISCOVERY & ENRICHMENT PIPELINE
## Full Technical Brief — For Implementation

---

## WHY WE MADE THESE DECISIONS

### The core problem we discovered today

We ran tests on the current `MapsFirstDiscovery` pipeline. It uses BD GMB SERP to find leads by searching Google Maps — e.g. "plumber sydney". Each query returns 20 results. After the waterfall filters (ICP filter → ALS gate → email find rate → DM find rate), only ~14% of raw leads become complete profiles. That means:

- To get 600 complete profiles, you need ~4,300 raw leads
- To get 4,300 raw leads at 20/query = 215 BD SERP queries
- At $0.0015/query + enrichment costs = ~$315 per campaign
- But the real problem: 215 queries × 20 results = only 4,300 raw leads IF you have 215 distinct search queries to run. In practice the system was running far fewer queries, yielding ~140 complete profiles max.

The system wasn't broken. It just wasn't designed for volume.

### Why Yellow Pages AU + Jina

We tested multiple sources today to find something that could provide volume at low cost:

| Source | Tested? | Result |
|--------|---------|--------|
| BD GMB SERP (current) | ✅ | 20 results/query, $0.0015/query, works |
| BD Datasets Marketplace (GMaps Full Info) | ✅ | Requires web login for samples, API endpoints 404 |
| BD LinkedIn People dataset | ✅ | No email/phone fields in schema — marketing claim not in data |
| GitHub sample CSVs (luminati-io) | ✅ | 1,000 records, US-heavy, no AU |
| Jina + Google Maps | ✅ | Only sponsored listings parse cleanly (~2-3/search) |
| **Jina + Yellow Pages AU** | ✅ | **30 leads/page, 88% phone rate, clean structured data, $0** |

Yellow Pages AU won because:
1. It's AU-native — every listing is an Australian local business. No filtering needed.
2. It's structured — Jina renders it as clean markdown that parses reliably
3. The `is_advertiser` signal is unique — a business paying for a YP listing in 2026 is already in "I pay for customer acquisition" mode. That's our buyer.
4. It's free — no API keys, no rate limits that matter at our volume
5. It scales — 200 categories × 10 cities × 3 pages = 18,000 raw leads per run

We confirmed it works with live tests: sydney-nsw/plumbers returned 30 leads with 88% phone fill rate, 70% address fill rate, ratings, years in business, hours.

### Why the marketing gap scorer

The previous outreach tests (referenced by Dave) had poor conversion. The data wasn't the problem — the *message* was. Generic cold outreach like "I help businesses get more leads" fails because:
- Every agency sends it
- It gives the prospect no reason to believe you know their business
- It has no specific hook

The gap scorer changes what the message IS. Instead of "I help plumbers", the outreach says: "Your competitor Metro Plumbing has 180 Google reviews vs your 23 and ranks #1 for 'plumber sydney' — they're capturing most local search traffic."

That's factual, specific, and impossible to dismiss. It proves you looked at them. The DataForSEO SEO analysis and BD GMB comparison generate exactly these numbers automatically per lead.

### Why we still use BD SERP (moved to stage 7, not discovery)

BD SERP is still valuable — it gives us the GMB comparison data (maps rank + review delta vs #1 competitor). But we demote it from T0 discovery to T7 enrichment. It only runs on ~1,260 leads (those that passed the free signal gate) rather than being the source of all raw leads. This alone saves 70% of current BD SERP spend.

### Why the DM pipeline matters more than the business data

The previous system enriched businesses (name, address, phone, website). That's not enough to book a meeting. You need:
- The owner's name (not the receptionist)
- Their direct email (not info@)
- Their LinkedIn (to understand what they care about before you write to them)
- Their social handles (for multi-channel sequencing)

A message to "the business" gets ignored. A message to "John Smith, Owner, Smith & Sons Plumbing" that references something John posted on LinkedIn last week gets opened.

### Why LinkedIn activity specifically

The BD LinkedIn People dataset includes a `posts` field with the DM's last N posts. This is the most underused signal in cold outreach. If John posted "slow week, hoping the weather improves" — that's the perfect opening. "Saw you mentioned it's been quiet — we've helped three Sydney plumbers add 15 leads/month from the same slow season using retargeting." That's a conversation, not a pitch.

### Why Claude Haiku for personalisation (not GPT-4 or Sonnet)

We're generating an opening line per lead. At 630 leads per campaign:
- Claude Opus/Sonnet: ~$0.015-0.075/lead = $9-47 just for personalisation
- Claude Haiku: ~$0.003/lead = $1.89 total
- GPT-3.5: similar to Haiku

The task is constrained (one sentence, specific format, specific inputs) — it doesn't need a frontier model. Haiku handles it well at 15x lower cost.

### Why the gate at stage 8 (score ≥ 60)

Without a gate, we'd run Leadmagic email enrichment on all 2,520 leads that made it through the website audit. At $0.015/lead that's $37.80. With the gate, only ~630 get enriched = $9.45. The gate uses real signals (SEO gap + GMB comparison + YP score) to ensure we're only spending money on leads with a genuine marketing gap AND affordability signal. This is where the cost savings compound.

---

**Context:** You are being asked to implement a new lead discovery and enrichment pipeline for Agency OS. This replaces the current `MapsFirstDiscovery` system which is hitting a hard ceiling of ~140 complete lead profiles per campaign. We need 600. Read the existing codebase first, then implement.

**Codebase:** `/home/elliotbot/clawd`

**Read these first:**
- `src/pipeline/campaign_trigger.py` — active pipeline entry point
- `src/pipeline/discovery_modes.py` — current MapsFirstDiscovery
- `src/pipeline/query_translator.py` — discovery orchestration
- `src/pipeline/waterfall_v2.py` — enrichment waterfall
- `src/integrations/bright_data_client.py` — BD SERP client
- `src/integrations/leadmagic.py` — email/mobile enrichment
- `src/integrations/abn_client.py` — ABN lookup

---

## THE PROBLEM WITH THE CURRENT SYSTEM

```
Current MapsFirstDiscovery funnel:
  BD SERP query       → 20 results
  × ICP filter (50%)  → 10
  × ALS gate (30%)    → 3
  × Email found (60%) → 1.8
  × DM found (40%)    → 0.7 complete profiles per query

To get 140 profiles = 200 queries
To get 600 profiles = 857 queries = impossible without massive spend
```

Cost: ~$315 for 140 complete profiles ($2.25/profile).

---

## THE NEW PIPELINE

**18,000 raw leads → ~390 complete profiles → $60.19 total**

```
STAGE  SOURCE                    COST        IN        OUT
  1    Jina + Yellow Pages AU    $0          —         18,000
  2    ICP Filter (rules)        $0          18,000     9,000
  3    Free Signal Score         $0           9,000     3,150
  4    Website Audit             $0           3,150     2,520
  5    ABN Lookup                $0           2,520     2,520
  6    DataForSEO SEO Gap        $12.60       2,520     2,520  ← enrichment only
  7    BD GMB Comparison         $1.89        1,260     1,260
  8    Full Gap Score + Gate     $0           1,260       630  ← qualified leads
  9    LinkedIn DM Name          $3.46          346       277
 10    LinkedIn DM Profile       $6.65          554       443
 11    Leadmagic Email           $9.45          630       410
 12    Leadmagic Mobile          $24.25         315       126
 13    Social Scrape             $0             630       630
 14    AI Personalisation        $1.89          630       630
                                ────────
                                $60.19
```

---

## STAGE 1: DISCOVERY — Jina + Yellow Pages AU
**File to create:** `src/integrations/yp_scraper.py`
**Cost: $0**

Yellow Pages AU is Australia's largest business directory. We scrape it via the Jina reader API which renders JS pages to clean markdown.

**URL pattern:**
```
https://r.jina.ai/https://www.yellowpages.com.au/{suburb-state}/{category}
```

**Confirmed working examples (tested today):**
```
https://r.jina.ai/https://www.yellowpages.com.au/sydney-nsw/plumbers         → 30 leads, 88% phone
https://r.jina.ai/https://www.yellowpages.com.au/melbourne-vic/electricians  → 34 leads
https://r.jina.ai/https://www.yellowpages.com.au/brisbane-qld/dentists       → 32 leads
https://r.jina.ai/https://www.yellowpages.com.au/perth-wa/accountants        → 34 leads
```

**What the Jina markdown looks like:**
```markdown
## [A to Z Plumbing & Drainage Services](https://www.yellowpages.com.au/sydney-nsw/bpp/a-to-z-580279355)

[Plumbers & Gasfitters](https://www.yellowpages.com.au/australia/plumbers-gasfitters)

5.0(23)

**36 Years** in Business

0480 023 046

Serving Sydney, NSW

OPEN until 10:00 pm

[Website](https://www.atozplumbing.com.au)

Ad
```

The first ~5 listings on each page are **paid advertisers** — these are our warmest leads because they already have a "pay for customer acquisition" mindset.

**Scale calculation:**
- 200 AU trade/professional/health/beauty categories
- 10 city/suburb combinations
- 30 results per page × 3 pages = 90 per category/city
- Total: 18,000 raw leads
- Rate limit: 1 request/second (Jina free tier)
- Pagination: `?page=2`, `?page=3`

**Output dataclass:**
```python
from dataclasses import dataclass, field

@dataclass
class YPLead:
    """A raw lead scraped from Yellow Pages AU."""
    name: str
    yp_url: str
    category: str
    phone: str | None = None
    address: str | None = None          # "Suburb, STATE XXXX"
    service_area: str | None = None     # "Serving Sydney, NSW"
    rating: float | None = None
    review_count: int | None = None
    years_in_business: int | None = None
    hours: str | None = None
    is_advertiser: bool = False          # Paid YP listing = STRONGEST signal
    has_website: bool = False
    website_url: str | None = None
    source: str = "yellowpages_au"
```

**Full implementation:**
```python
"""
FILE: src/integrations/yp_scraper.py
PURPOSE: Discover Australian businesses via Yellow Pages AU + Jina reader API
COST: $0 (free)
RATE LIMIT: 1 req/sec (Jina free tier)
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field

import httpx
import structlog

logger = structlog.get_logger()

JINA_BASE = "https://r.jina.ai/"
YP_BASE = "https://www.yellowpages.com.au"

# Agency OS ICP categories → YP URL slugs
ICP_CATEGORY_MAP = {
    # Trades
    "plumber": "plumbers",
    "electrician": "electricians",
    "builder": "builders",
    "air_conditioning": "air-conditioning",
    "tiler": "tilers",
    "painter": "painters-decorators",
    "landscaper": "landscapers",
    "cleaner": "cleaning-services",
    # Professional services
    "accountant": "accountants",
    "lawyer": "lawyers",
    "financial_planner": "financial-planners",
    "mortgage_broker": "mortgage-brokers",
    # Health
    "dentist": "dentists",
    "physiotherapist": "physiotherapists",
    "chiropractor": "chiropractors",
    "optometrist": "optometrists",
    "gp": "general-practitioners",
    # Beauty
    "hair_salon": "hair-salons",
    "beauty_salon": "beauty-salons",
    "barber": "barbers",
    "nail_salon": "nail-salons",
    # Real estate
    "real_estate_agent": "real-estate-agents",
}

# Location slugs for major AU cities
AU_LOCATIONS = [
    "sydney-nsw", "melbourne-vic", "brisbane-qld", "perth-wa",
    "adelaide-sa", "gold-coast-qld", "newcastle-nsw", "canberra-act",
    "wollongong-nsw", "geelong-vic",
]


@dataclass
class YPLead:
    """A raw lead scraped from Yellow Pages AU."""
    name: str
    yp_url: str
    category: str
    phone: str | None = None
    address: str | None = None
    service_area: str | None = None
    rating: float | None = None
    review_count: int | None = None
    years_in_business: int | None = None
    hours: str | None = None
    is_advertiser: bool = False
    has_website: bool = False
    website_url: str | None = None
    source: str = "yellowpages_au"


# Phone number patterns for Australia
AU_PHONE_RE = re.compile(
    r'(\(0\d\)\s*\d{4}\s*\d{4}'   # (02) 9xxx xxxx
    r'|1[38]\d{2}\s*\d{3}\s*\d{3}'  # 1300/1800 xxx xxx
    r'|04\d{2}\s*\d{3}\s*\d{3}'     # 04xx xxx xxx
    r'|\+61\s*\d[\s\d]{8,})'         # +61 ...
)

ADDRESS_RE = re.compile(
    r'(.+,\s+(?:NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\s+\d{4})'
)

RATING_RE = re.compile(r'(\d\.\d)\(?(\d+)\)?')
YEARS_RE = re.compile(r'(\d+)\s+Years?\s+in\s+Business', re.IGNORECASE)
WEBSITE_RE = re.compile(r'\[Website\]\((https?://[^)]+)\)')
CATEGORY_RE = re.compile(r'\[([A-Z][^\]]{3,})\]\(https://www\.yellowpages\.com\.au/australia/')


async def scrape_yp_category(
    category_slug: str,
    location_slug: str,
    pages: int = 3,
) -> list[YPLead]:
    """
    Scrape Yellow Pages AU for a category+location combo via Jina.

    Args:
        category_slug: YP URL slug e.g. "plumbers", "electricians"
        location_slug: YP location slug e.g. "sydney-nsw", "melbourne-vic"
        pages: Number of pages to scrape (30 results/page)

    Returns:
        List of YPLead objects

    Cost: $0 (Jina free tier)
    Rate limit: 1 req/sec
    """
    leads = []
    log = logger.bind(category=category_slug, location=location_slug)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for page in range(1, pages + 1):
            url = f"{YP_BASE}/{location_slug}/{category_slug}"
            if page > 1:
                url += f"?page={page}"

            jina_url = f"{JINA_BASE}{url}"

            try:
                resp = await client.get(jina_url)
                if resp.status_code != 200:
                    log.warning("yp_scraper.non_200", page=page, status=resp.status_code)
                    break

                page_leads = _parse_yp_markdown(resp.text, page_num=page)
                leads.extend(page_leads)
                log.info("yp_scraper.page_scraped", page=page, leads_found=len(page_leads))

                if len(page_leads) < 10:  # End of results
                    break

            except httpx.TimeoutException:
                log.warning("yp_scraper.timeout", page=page)
                break
            except Exception as e:
                log.error("yp_scraper.error", page=page, error=str(e))
                break

            await asyncio.sleep(1.0)  # Jina rate limit

    return leads


def _parse_yp_markdown(content: str, page_num: int = 1) -> list[YPLead]:
    """
    Parse Jina-rendered Yellow Pages markdown into structured YPLead objects.

    Business entries follow this pattern in the markdown:
    ## [Business Name](yp_url)
    [Category](category_url)
    4.8(52)
    **12 Years** in Business
    (02) 9123 4567
    123 Main Street, Sydney, NSW 2000
    OPEN until 6:00 pm
    [Website](https://example.com.au)
    """
    leads = []
    lines = content.split('\n')
    in_ad_section = (page_num == 1)  # First listings on page 1 = paid ads

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect transition from ad section to organic results
        if 'sort:' in line.lower() or 'default' in line.lower():
            in_ad_section = False

        # Business name: ## [Name](url) pattern
        if line.startswith('## [') and 'yellowpages.com.au' in line:
            name_match = re.match(r'^## \[([^\]]+)\]\(([^)]+)\)', line)
            if not name_match:
                i += 1
                continue

            biz = YPLead(
                name=name_match.group(1).strip(),
                yp_url=name_match.group(2).strip(),
                category="",
                is_advertiser=in_ad_section,
            )

            # Scan the next 16 lines for field data
            for j in range(i + 1, min(i + 17, len(lines))):
                l = lines[j].strip()
                if not l:
                    continue
                # Stop at next business entry
                if lines[j].strip().startswith('## ['):
                    break

                # Rating + review count: "4.8(52)" or "5.0 (23)"
                rating_match = RATING_RE.search(l)
                if rating_match and biz.rating is None:
                    biz.rating = float(rating_match.group(1))
                    biz.review_count = int(rating_match.group(2))

                # Australian phone number
                phone_match = AU_PHONE_RE.search(l)
                if phone_match and biz.phone is None:
                    biz.phone = phone_match.group(0).strip()

                # Address: "Suburb, STATE XXXX"
                addr_match = ADDRESS_RE.search(l)
                if addr_match and biz.address is None:
                    biz.address = addr_match.group(1).strip()

                # Service area: "Serving Sydney, NSW"
                if 'Serving' in l and biz.service_area is None:
                    biz.service_area = l

                # Business hours
                if ('OPEN' in l or 'CLOSED' in l) and biz.hours is None:
                    biz.hours = l

                # Years in business: "36 Years in Business"
                yib_match = YEARS_RE.search(l)
                if yib_match and biz.years_in_business is None:
                    biz.years_in_business = int(yib_match.group(1))

                # Website link: [Website](https://...)
                website_match = WEBSITE_RE.search(l)
                if website_match:
                    biz.has_website = True
                    biz.website_url = website_match.group(1).strip()

                # Category: [Plumbers & Gasfitters](https://www.yellowpages.com.au/australia/...)
                cat_match = CATEGORY_RE.search(l)
                if cat_match and not biz.category:
                    biz.category = cat_match.group(1).strip()

            # Only keep businesses with a name (sanity check)
            if biz.name and len(biz.name) > 2:
                leads.append(biz)

        i += 1

    return leads


async def bulk_discover(
    categories: list[str],
    locations: list[str],
    pages_per_combo: int = 3,
) -> list[YPLead]:
    """
    Run YP discovery across multiple category+location combos.

    Args:
        categories: List of YP category slugs
        locations: List of YP location slugs
        pages_per_combo: Pages per category/location (30 results each)

    Returns:
        Deduplicated list of YPLead objects

    Example:
        leads = await bulk_discover(
            categories=["plumbers", "electricians", "dentists"],
            locations=["sydney-nsw", "melbourne-vic", "brisbane-qld"],
        )
        # Returns up to 810 leads (3 cats × 3 locs × 3 pages × 30/page)
    """
    all_leads: list[YPLead] = []
    seen_names: set[str] = set()

    for category in categories:
        for location in locations:
            leads = await scrape_yp_category(category, location, pages_per_combo)
            for lead in leads:
                # Deduplicate by name+location
                key = f"{lead.name.lower()}:{location}"
                if key not in seen_names:
                    seen_names.add(key)
                    all_leads.append(lead)

    logger.info("yp_scraper.bulk_complete",
                total_leads=len(all_leads),
                categories=len(categories),
                locations=len(locations))

    return all_leads
```

---

## STAGE 2: ICP FILTER
**Cost: $0 — Pure rules, no API**

```python
def apply_icp_filter(lead: YPLead) -> tuple[bool, str | None]:
    """
    Filter out leads that are clearly not Agency OS prospects.
    Returns: (passes, reason_if_rejected)
    """
    # Must have a phone number to be reachable
    if not lead.phone:
        return False, "no_phone"

    # "Serving Australia" = national chain, not local SMB owner
    if lead.service_area and "serving australia" in lead.service_area.lower():
        return False, "national_chain"

    # Must have some location signal
    if not lead.address and not lead.service_area:
        return False, "no_location"

    return True, None
```

Volume: 18,000 → ~9,000

---

## STAGE 3: FREE SIGNAL SCORE
**Cost: $0 — Uses only YP data already collected**

```python
def score_free_signals(lead: YPLead) -> tuple[int, dict]:
    """
    Score 0-100 using only free YP signals.
    Higher score = more likely to need marketing help AND have budget.

    Key insight: is_advertiser (+25) is the strongest single signal.
    A business paying Yellow Pages for a listing in 2026 is already
    in "I pay for customer acquisition" mode. That's our buyer.
    """
    score = 0
    signals = {}

    # Review count sweet spot: 5-80
    # Too few = brand new (no budget)
    # Too many = market leader (has a marketing team)
    if lead.review_count is not None:
        if 5 <= lead.review_count <= 80:
            score += 20
            signals["review_sweet_spot"] = lead.review_count
        elif lead.review_count < 5:
            score += 5
        elif lead.review_count > 200:
            score -= 15
            signals["too_established"] = True

    # Rating: 3.8-4.6 = room to improve but not broken
    # >4.8 = might be complacent
    # <3.5 = might be defensive
    if lead.rating is not None:
        if 3.8 <= lead.rating <= 4.6:
            score += 15
        elif lead.rating < 3.5:
            score += 5
        elif lead.rating > 4.8:
            score += 8

    # Years in business: 2-8 = established but still scaling, owner still hands-on
    if lead.years_in_business is not None:
        if 2 <= lead.years_in_business <= 8:
            score += 20
            signals["years_sweet_spot"] = lead.years_in_business
        elif lead.years_in_business > 15:
            score -= 10
            signals["too_established"] = True
        elif lead.years_in_business < 2:
            score += 5

    # STRONGEST SIGNAL: Already paying for marketing
    if lead.is_advertiser:
        score += 25
        signals["yp_advertiser"] = True

    # Digital awareness
    if lead.has_website:
        score += 10
        signals["has_website"] = True

    # Active business
    if lead.hours:
        score += 5

    return score, signals

STAGE_3_GATE = 35  # Minimum to proceed
```

Volume: 9,000 → ~3,150

---

## STAGE 4: WEBSITE AUDIT
**File to create:** `src/integrations/website_auditor.py`
**Cost: $0 — Direct HTTP fetch**

```python
"""
FILE: src/integrations/website_auditor.py
PURPOSE: Audit business websites for marketing signals and owner identity
COST: $0 (direct HTTP, no API)
"""

from __future__ import annotations

import re

import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()

# Marketing pixel patterns — absence = gap we can fill
PIXEL_PATTERNS: dict[str, str] = {
    "facebook_pixel": r"fbq\(|facebook\.com/tr\?|connect\.facebook\.net",
    "google_analytics": r"gtag\(|G-[A-Z0-9]+|UA-\d+",
    "google_ads": r"googleadservices\.com|AW-\d+",
    "hotjar": r"hotjar\.com",
    "hubspot": r"hs-scripts\.com",
    "mailchimp": r"mailchimp\.com",
}

# Patterns to find owner name on About/Team pages
OWNER_PATTERNS: list[str] = [
    r"(?:founded|owned|established)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    r"(?:owner|director|principal|founder|ceo|managing\s+director)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
    r"([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*(?:owner|director|founder|principal))",
    r"(?:my name is|I'm|I am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})",
]

BOOKING_SIGNALS = [
    "book now", "book online", "book an appointment",
    "schedule", "make a booking", "request a quote",
]

PERSONAL_EMAIL_EXCLUDE = ["info@", "admin@", "hello@", "contact@", "support@",
                          "noreply@", "enquiries@", "reception@"]

PAGES_TO_CHECK = ["", "/about", "/about-us", "/team", "/our-team",
                  "/contact", "/contact-us"]


@dataclass
class WebsiteAudit:
    """Results of a business website audit."""
    pixels: dict[str, bool] = field(default_factory=dict)  # pixel_name → found
    has_booking: bool = False
    owner_name: str | None = None
    social_links: dict[str, str] = field(default_factory=dict)  # platform → url
    personal_emails: list[str] = field(default_factory=list)
    is_mobile_responsive: bool = False
    pages_checked: int = 0
    error: str | None = None


async def audit_website(website_url: str, max_pages: int = 3) -> WebsiteAudit:
    """
    Audit a business website for marketing signals and owner identity.

    Checks: tracking pixels, booking system, owner name, social links,
    personal email addresses, mobile responsiveness.

    Args:
        website_url: The business website URL
        max_pages: Max pages to fetch (homepage + about + contact)

    Returns:
        WebsiteAudit with all signals extracted

    Cost: $0 (direct HTTP)
    """
    audit = WebsiteAudit()

    async with httpx.AsyncClient(
        timeout=15,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; AgencyOS/1.0)"}
    ) as client:

        for path in PAGES_TO_CHECK[:max_pages]:
            url = f"{website_url.rstrip('/')}{path}"
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue

                audit.pages_checked += 1
                html = resp.text
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator=" ")
                text_lower = text.lower()

                # 1. Tracking pixel detection
                for pixel_name, pattern in PIXEL_PATTERNS.items():
                    if not audit.pixels.get(pixel_name):
                        if re.search(pattern, html, re.IGNORECASE):
                            audit.pixels[pixel_name] = True

                # 2. Booking system
                if not audit.has_booking:
                    if any(signal in text_lower for signal in BOOKING_SIGNALS):
                        audit.has_booking = True

                # 3. Owner name extraction (prioritise About pages)
                if not audit.owner_name:
                    for pattern in OWNER_PATTERNS:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            candidate = match.group(1).strip()
                            # Basic validation: 2 words, looks like a name
                            if len(candidate.split()) >= 2:
                                audit.owner_name = candidate
                                break

                # 4. Social links from anchor tags
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "linkedin.com/in/" in href and "linkedin_personal" not in audit.social_links:
                        audit.social_links["linkedin_personal"] = href
                    elif "linkedin.com/company/" in href and "linkedin_company" not in audit.social_links:
                        audit.social_links["linkedin_company"] = href
                    elif "facebook.com/" in href and "facebook.com/sharer" not in href and "facebook" not in audit.social_links:
                        audit.social_links["facebook"] = href
                    elif ("twitter.com/" in href or "x.com/" in href) and "twitter" not in audit.social_links:
                        audit.social_links["twitter"] = href
                    elif "instagram.com/" in href and "instagram" not in audit.social_links:
                        audit.social_links["instagram"] = href

                # 5. Personal email addresses on page
                emails = re.findall(
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    html
                )
                for email in emails:
                    email_lower = email.lower()
                    is_personal = not any(exc in email_lower for exc in PERSONAL_EMAIL_EXCLUDE)
                    is_new = email_lower not in [e.lower() for e in audit.personal_emails]
                    if is_personal and is_new:
                        audit.personal_emails.append(email)
                        if len(audit.personal_emails) >= 3:
                            break

                # 6. Mobile responsiveness
                if not audit.is_mobile_responsive:
                    if "viewport" in html.lower() and "width=device-width" in html.lower():
                        audit.is_mobile_responsive = True

            except (httpx.TimeoutException, httpx.ConnectError):
                continue
            except Exception as e:
                audit.error = str(e)
                break

    return audit
```

---

## STAGE 5: ABN LOOKUP
**Uses existing `src/integrations/abn_client.py` — Cost: $0**

Key insight: If `entity_type == "IND"` (Individual), the business is a sole trader and `legalName` IS the owner's name. This gives us the DM name for ~40% of AU businesses.

```python
async def enrich_abn(business_name: str, state: str, abn_client: ABNClient) -> dict:
    result = await abn_client.search_by_name(business_name, state)
    if not result:
        return {}
    return {
        "abn": result.get("abn"),
        "entity_type": result.get("entityType"),  # "IND" = sole trader = owner IS ABN holder
        "registration_date": result.get("registrationDate"),
        "gst_registered": result.get("gstRegistered"),
        # If sole trader: legalName = "John Smith" = owner name
        "owner_name_from_abn": (
            result.get("legalName")
            if result.get("entityType") == "IND"
            else None
        ),
        "business_confirmed_active": result.get("status") == "Active",
    }
```

After stages 4 + 5: **~60% of leads have DM name identified for free.**

---

## STAGE 6: SEO GAP ANALYSIS
**File to create:** `src/integrations/dataforseo_seo.py`
**Cost: ~$0.005/domain → $12.60 for 2,520 leads**

Credentials already in `.env`:
```
DATAFORSEO_LOGIN=david.stephens@keiracom.com
DATAFORSEO_PASSWORD=9cb373dab8a0eff1
```

**Two API calls per domain:**

**Call 1: Domain Overview** — organic traffic, keyword count
```
POST https://api.dataforseo.com/v3/dataforseo_labs/google/domain_overview/live
Auth: Basic base64(LOGIN:PASSWORD)
Body: [{"target": "smithsonsplumbing.com.au", "location_name": "Australia", "language_name": "English"}]

Response path: tasks[0].result[0].metrics.organic
  → etv: monthly estimated traffic
  → count: number of ranking keywords
```

**Call 2: SERP Check** — where do they rank for their primary keyword?
```
POST https://api.dataforseo.com/v3/serp/google/organic/live/advanced
Auth: Basic base64(LOGIN:PASSWORD)
Body: [{"keyword": "plumber sydney", "location_name": "Australia", "language_name": "English", "depth": 20}]

Response path: tasks[0].result[0].items[]
  → rank_absolute: position (1 = top)
  → url: result URL
  → title: page title
```

**Logic:**
```python
# Find their position
rank_position = next(
    (item["rank_absolute"] for item in items if domain in item.get("url", "")),
    None  # Not in top 20 = invisible
)

# Find who's #1
top_competitor = next(
    (item["title"] for item in items if item["rank_absolute"] == 1),
    None
)

# The hook for outreach:
if rank_position is None:
    gap_detail = f"Not ranking at all for '{keyword}' — completely invisible to local searchers"
elif rank_position > 10:
    gap_detail = f"Ranking #{rank_position} for '{keyword}' while {top_competitor} is #1 — they get 90% of the clicks"
elif rank_position > 5:
    gap_detail = f"Ranking #{rank_position} for '{keyword}' — page 1 but below the fold, missing 60% of clicks"
else:
    gap_detail = f"Ranking #{rank_position} for '{keyword}' — solid position"
    # No gap here, don't use SEO as the angle
```

**Full implementation:**
```python
"""
FILE: src/integrations/dataforseo_seo.py
PURPOSE: SEO gap analysis for Agency OS lead qualification
COST: ~$0.005/domain (2 API calls: domain overview + SERP check)
"""

from __future__ import annotations

import base64
import os

import httpx
import structlog

logger = structlog.get_logger()

def _get_auth() -> str:
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    return base64.b64encode(f"{login}:{password}".encode()).decode()


@dataclass
class SEOSignals:
    domain: str
    organic_traffic_monthly: int = 0
    ranking_keywords: int = 0
    rank_for_main_keyword: int | None = None  # None = not ranking
    main_keyword: str = ""
    top_competitor: str | None = None
    seo_gap: bool = True
    gap_detail: str = ""
    cost_aud: float = 0.005


async def get_seo_signals(domain: str, category: str, location: str) -> SEOSignals:
    """
    Pull SEO metrics and rank position for a business domain.

    Args:
        domain: Business domain e.g. "smithsonsplumbing.com.au"
        category: Business category e.g. "plumber"
        location: City e.g. "Sydney"

    Returns:
        SEOSignals with gap analysis

    Cost: ~$0.005 AUD (2 DataForSEO API calls)
    """
    auth = _get_auth()
    keyword = f"{category} {location}"
    signals = SEOSignals(domain=domain, main_keyword=keyword)

    async with httpx.AsyncClient(timeout=30) as client:

        # Call 1: Domain overview
        try:
            resp = await client.post(
                "https://api.dataforseo.com/v3/dataforseo_labs/google/domain_overview/live",
                headers={"Authorization": f"Basic {auth}"},
                json=[{
                    "target": domain,
                    "location_name": "Australia",
                    "language_name": "English"
                }]
            )
            data = resp.json()
            result = data.get("tasks", [{}])[0].get("result", [{}])[0]
            organic = result.get("metrics", {}).get("organic", {})
            signals.organic_traffic_monthly = int(organic.get("etv", 0))
            signals.ranking_keywords = int(organic.get("count", 0))
        except Exception as e:
            logger.warning("dataforseo_seo.domain_overview_failed", domain=domain, error=str(e))

        # Call 2: SERP rank check for primary keyword
        try:
            resp = await client.post(
                "https://api.dataforseo.com/v3/serp/google/organic/live/advanced",
                headers={"Authorization": f"Basic {auth}"},
                json=[{
                    "keyword": keyword,
                    "location_name": "Australia",
                    "language_name": "English",
                    "depth": 20
                }]
            )
            data = resp.json()
            items = data.get("tasks", [{}])[0].get("result", [{}])[0].get("items", [])

            for item in items:
                item_url = item.get("url", "").lower()
                rank = item.get("rank_absolute")

                # Find their position
                if domain.lower().replace("www.", "") in item_url.replace("www.", ""):
                    signals.rank_for_main_keyword = rank

                # Find who's #1
                if rank == 1 and not signals.top_competitor:
                    signals.top_competitor = item.get("title", "a competitor")

        except Exception as e:
            logger.warning("dataforseo_seo.serp_failed", domain=domain, error=str(e))

    # Build the gap detail string (used as outreach hook)
    rank = signals.rank_for_main_keyword
    competitor = signals.top_competitor or "a competitor"

    if rank is None:
        signals.gap_detail = (
            f"Not ranking at all for '{keyword}' — completely invisible to local searchers"
        )
        signals.seo_gap = True
    elif rank > 10:
        signals.gap_detail = (
            f"Ranking #{rank} for '{keyword}' while {competitor} is #1 — "
            f"they capture ~90% of search clicks"
        )
        signals.seo_gap = True
    elif rank > 5:
        signals.gap_detail = (
            f"Ranking #{rank} for '{keyword}' — page 1 but below the fold, "
            f"missing ~60% of available clicks"
        )
        signals.seo_gap = True
    else:
        signals.gap_detail = f"Ranking #{rank} for '{keyword}' — solid position"
        signals.seo_gap = False

    logger.info("dataforseo_seo.complete",
                domain=domain, keyword=keyword,
                rank=rank, seo_gap=signals.seo_gap,
                cost_aud=signals.cost_aud)

    return signals
```

---

## STAGE 7: GMB COMPARISON
**Uses existing `BrightDataClient` — Cost: $0.0015/query**
**API Key:** `BRIGHTDATA_API_KEY=636a81d7-4f89-4fb5-904b-f1e195ec20d2`
**Zone:** `serp_api1`

```python
async def get_gmb_comparison(
    business_name: str,
    category: str,
    location: str,
    bright_data_client: BrightDataClient,
) -> dict:
    """
    Check Maps rank position and compare review count to #1 competitor.
    Uses existing BD SERP client (search_google_maps method).
    Cost: $0.0015 AUD
    """
    query = f"{category} {location}"
    results = await bright_data_client.search_google_maps(query)

    our_position = None
    our_reviews = None
    top_reviews = None
    is_claimed = False

    for i, result in enumerate(results.get("local_results", []), 1):
        title = result.get("title", "").lower()
        business_lower = business_name.lower()

        # Fuzzy match on first 10 chars of business name
        if business_lower[:10] in title or title[:10] in business_lower:
            our_position = i
            our_reviews = result.get("reviews", 0)
            is_claimed = result.get("claimed", False)

        if i == 1:
            top_reviews = result.get("reviews", 0)

    review_gap = (top_reviews or 0) - (our_reviews or 0)
    maps_gap = our_position is None or our_position > 5

    maps_gap_detail = (
        f"Not appearing in Google Maps top 20 for '{query}'"
        if our_position is None
        else f"#{our_position} on Maps, {review_gap} fewer reviews than the #1 listing"
        if our_position > 3
        else f"#{our_position} on Maps — strong local position"
    )

    return {
        "maps_rank_position": our_position,
        "our_review_count": our_reviews,
        "top_competitor_reviews": top_reviews,
        "review_gap": review_gap,
        "is_claimed": is_claimed,
        "maps_gap": maps_gap,
        "maps_gap_detail": maps_gap_detail,
        "cost_aud": 0.0015,
    }
```

---

## STAGE 8: FULL GAP SCORE + GATE
**Cost: $0**

```python
GAP_GATE_THRESHOLD = 60

def compute_final_gap_score(
    yp_score: int,
    website_audit: WebsiteAudit,
    seo_signals: SEOSignals,
    gmb_comparison: dict,
) -> tuple[int, list[str], str]:
    """
    Combine all signals into final gap score.
    Returns: (score, gap_bullets, recommended_angle)

    gap_bullets = specific facts for outreach personalisation
    recommended_angle = the primary hook to lead with
    """
    score = yp_score
    gap_bullets: list[str] = []

    # SEO gap
    if seo_signals.seo_gap:
        score += 20
        gap_bullets.append(seo_signals.gap_detail)

    # Maps/GMB gap
    if gmb_comparison.get("maps_gap"):
        score += 15
        gap_bullets.append(gmb_comparison["maps_gap_detail"])

    # Large review gap
    if gmb_comparison.get("review_gap", 0) > 50:
        score += 10
        gap_bullets.append(
            f"Competitor has {gmb_comparison['review_gap']} more Google reviews"
        )

    # Not running retargeting ads
    has_retargeting = (
        website_audit.pixels.get("facebook_pixel")
        or website_audit.pixels.get("google_ads")
    )
    if not has_retargeting:
        score += 10
        gap_bullets.append(
            "No retargeting pixels — losing warm website visitors who don't convert first visit"
        )

    # No online booking
    if not website_audit.has_booking:
        score += 5
        gap_bullets.append(
            "No online booking — adding friction to conversion, competitors with booking forms win"
        )

    return (
        min(score, 100),
        gap_bullets,
        gap_bullets[0] if gap_bullets else "general marketing improvement",
    )
```

---

## STAGE 9: DM NAME (remaining ~40% without name)
**Cost: $0.01/company**
**BD LinkedIn Company dataset:** `gd_l1vikfnt1wgvvqz95w`

```python
DM_TITLES = [
    "owner", "director", "founder", "principal", "ceo",
    "managing director", "proprietor", "co-founder", "partner",
]

async def find_dm_via_linkedin_company(
    business_name: str,
    bright_data_client: BrightDataClient,
) -> dict | None:
    """
    Search LinkedIn for company, find Owner/Director in employee list.
    Cost: $0.01 AUD
    """
    result = await bright_data_client.trigger_dataset(
        dataset_id="gd_l1vikfnt1wgvvqz95w",
        inputs=[{"url": f"https://www.linkedin.com/search/results/companies/?keywords={business_name}"}]
    )
    if not result:
        return None

    for employee in result.get("employees", []):
        title = employee.get("title", "").lower()
        if any(t in title for t in DM_TITLES):
            return {
                "dm_name": employee.get("name"),
                "dm_title": employee.get("title"),
                "dm_linkedin_url": employee.get("profile_url"),
                "linkedin_company_url": result.get("url"),
                "cost_aud": 0.01,
            }
    return None
```

After stage 9: **~88% of 630 qualified leads have DM name (554 leads)**

---

## STAGE 10: LINKEDIN DM PROFILE
**Cost: $0.012/profile**
**BD LinkedIn People dataset:** `gd_l1viktl72bvl7bjuj0`

```python
async def enrich_dm_linkedin_profile(
    linkedin_profile_url: str,
    bright_data_client: BrightDataClient,
) -> dict:
    """
    Pull full LinkedIn profile for decision maker.
    Key fields: about, posts (last 5), activity, position.
    Cost: $0.012 AUD

    The last 5 posts are GOLD for personalisation.
    If they posted "quiet week, anyone need a plumber?" we lead with that.
    """
    result = await bright_data_client.trigger_dataset(
        dataset_id="gd_l1viktl72bvl7bjuj0",
        inputs=[{"url": linkedin_profile_url}]
    )
    if not result:
        return {}

    recent_posts = result.get("posts", [])[:5]
    post_texts = [p.get("text", "")[:150] for p in recent_posts]
    activity_summary = _classify_activity(recent_posts)

    return {
        "dm_bio": result.get("about", "")[:300],
        "dm_current_position": result.get("position"),
        "dm_followers": result.get("followers"),
        "dm_connections": result.get("connections"),
        "dm_recent_posts": post_texts,
        "dm_activity_summary": activity_summary,
        "cost_aud": 0.012,
    }


def _classify_activity(posts: list[dict]) -> str:
    """Classify DM's LinkedIn activity for personalisation targeting."""
    if not posts:
        return "no_recent_activity"
    texts = " ".join(p.get("text", "") for p in posts).lower()
    if any(w in texts for w in ["slow", "quiet", "not many", "struggling"]):
        return "mentions_slow_business"   # Perfect opening
    if any(w in texts for w in ["hiring", "we're growing", "new team member"]):
        return "growing_actively"          # Scaling = has budget
    if any(w in texts for w in ["award", "proud", "thrilled", "excited"]):
        return "celebrating_wins"          # Good mood = receptive
    return "general_activity"
```

---

## STAGE 11: EMAIL ENRICHMENT
**Uses existing `src/integrations/leadmagic.py` — Cost: $0.015/lead**
**Success rate: ~65% → ~410 leads with verified email**

```python
# Uses existing LeadmagicClient.find_email()
result = await leadmagic.find_email(
    first_name=dm_first_name,
    last_name=dm_last_name,
    company_domain=domain,  # e.g. "smithsonsplumbing.com.au"
)
# Returns: {"email": "john@smithsonsplumbing.com.au", "confidence": 0.92, "status": "valid"}
```

---

## STAGE 12: MOBILE
**Uses existing `src/integrations/leadmagic.py` — Cost: $0.077/lead**
**Only run for leads with gap_score >= 80 (top 50% = 315 leads)**
**Success rate: ~40% → ~126 with mobile**

```python
# Uses existing LeadmagicClient.find_mobile()
result = await leadmagic.find_mobile(
    name=dm_full_name,
    company=business_name,
)
# Returns: {"mobile": "0412 345 678"}
```

---

## STAGE 13: SOCIAL ENRICHMENT
**Cost: $0 — Derived from website audit**

```python
def extract_final_socials(website_audit: WebsiteAudit) -> dict:
    return {
        "linkedin_personal": website_audit.social_links.get("linkedin_personal"),
        "linkedin_company": website_audit.social_links.get("linkedin_company"),
        "facebook": website_audit.social_links.get("facebook"),
        "twitter": website_audit.social_links.get("twitter"),
        "instagram": website_audit.social_links.get("instagram"),
    }
# Twitter fallback: BD SERP search "{name} twitter" ($0.0015) for top leads only
```

---

## STAGE 14: PERSONALISATION
**File to create:** `src/integrations/personalisation_engine.py`
**Cost: $0.003/lead (Claude Haiku) — $1.89 for 630**

```python
"""
FILE: src/integrations/personalisation_engine.py
PURPOSE: Generate personalised outreach opening lines using gap signals + DM activity
COST: ~$0.003 AUD per lead (Claude Haiku)
"""

import anthropic
import structlog

logger = structlog.get_logger()

CLAUDE_CLIENT = anthropic.Anthropic()

PERSONALISATION_PROMPT = """\
You are writing the opening line of a cold outreach email from a marketing agency to a small business owner.

Business: {business_name}
Category: {category}
Decision Maker: {dm_name}, {dm_title}
Their recent LinkedIn activity: {dm_activity}

Top marketing gaps identified:
{gap_bullets}

Write ONE sentence (maximum 25 words) that:
1. References ONE specific gap — use the competitor name or numbers if available
2. Is factual and specific, not vague
3. Does NOT use generic phrases like "I help businesses grow" or "take your business to the next level"
4. Creates mild urgency without being pushy or salesy
5. Sounds like a human who actually looked at their business

Output ONLY the sentence. No greeting. No sign-off. Just the hook.

Good example: "Your competitor Metro Plumbing has 180 Google reviews vs your 23 and ranks #1 for 'plumber sydney' — they're capturing most local search traffic."
Bad example: "I help plumbing businesses get more customers online."
"""


async def generate_opening_line(
    business_name: str,
    category: str,
    dm_name: str,
    dm_title: str,
    dm_activity_summary: str,
    gap_bullets: list[str],
) -> str:
    """
    Generate a personalised cold outreach opening line.

    Uses the specific marketing gaps identified in earlier pipeline stages
    combined with the DM's LinkedIn activity to create a hook that
    references their actual business situation.

    Cost: ~$0.003 AUD (Claude Haiku, ~100 tokens in/out)
    """
    bullets_text = "\n".join(f"- {b}" for b in gap_bullets[:3])
    if not bullets_text:
        bullets_text = "- General marketing improvement opportunity identified"

    try:
        message = CLAUDE_CLIENT.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": PERSONALISATION_PROMPT.format(
                    business_name=business_name,
                    category=category,
                    dm_name=dm_name or "the owner",
                    dm_title=dm_title or "Owner",
                    dm_activity=dm_activity_summary or "no recent activity",
                    gap_bullets=bullets_text,
                )
            }]
        )
        opening_line = message.content[0].text.strip()
        logger.info("personalisation_engine.generated",
                    business=business_name, chars=len(opening_line))
        return opening_line

    except Exception as e:
        logger.error("personalisation_engine.error", business=business_name, error=str(e))
        # Fallback: use first gap bullet directly
        return gap_bullets[0] if gap_bullets else f"I noticed some marketing gaps for {business_name}."
```

---

## FINAL OUTPUT DATACLASS
**File to create:** `src/models/campaign_ready_lead.py`

```python
"""
FILE: src/models/campaign_ready_lead.py
PURPOSE: Unified output schema for a campaign-ready lead
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CampaignReadyLead:
    """
    A fully enriched, scored, and personalised lead ready for outreach.

    Produced by the 14-stage discovery + enrichment pipeline.
    Replaces the raw LeadRecord used in waterfall_v2.py.
    """

    # ── Business ─────────────────────────────────────────────────────
    business_name: str
    category: str
    phone: str | None = None
    address: str | None = None
    website: str | None = None
    abn: str | None = None
    years_in_business: int | None = None

    # ── Qualification Scores ─────────────────────────────────────────
    icp_score: int = 0           # Stage 3: free signal score (0-100)
    gap_score: int = 0           # Stage 8: combined gap score (0-100)
    gap_bullets: list[str] = field(default_factory=list)  # Specific gaps found
    recommended_angle: str = ""  # Primary hook for outreach

    # ── Decision Maker ───────────────────────────────────────────────
    dm_name: str | None = None
    dm_title: str | None = None
    dm_email: str | None = None
    dm_mobile: str | None = None
    dm_linkedin_url: str | None = None
    dm_bio: str | None = None
    dm_recent_posts: list[str] = field(default_factory=list)
    dm_activity_summary: str | None = None  # "mentions_slow_business" etc.

    # ── Social Profiles ──────────────────────────────────────────────
    linkedin_company_url: str | None = None
    facebook_page: str | None = None
    twitter_handle: str | None = None
    instagram_url: str | None = None

    # ── Personalised Outreach ────────────────────────────────────────
    personalised_opening_line: str = ""
    outreach_channels: list[str] = field(default_factory=list)
    # Derived: ["email"] if dm_email found, ["linkedin"] if LI found,
    #          ["phone","sms"] if dm_mobile found

    # ── Pipeline Metadata ────────────────────────────────────────────
    enrichment_cost_aud: float = 0.0
    pipeline_stage_reached: int = 0
    source: str = "yellowpages_au"

    def __post_init__(self) -> None:
        """Derive outreach channels from available contact data."""
        channels = []
        if self.dm_email:
            channels.append("email")
        if self.dm_linkedin_url:
            channels.append("linkedin")
        if self.dm_mobile:
            channels.extend(["phone", "sms"])
        elif self.phone:
            channels.append("phone")
        self.outreach_channels = channels
```

---

## HOW IT WIRES INTO THE EXISTING CODEBASE

### New class in `discovery_modes.py`

```python
class YPFirstDiscovery:
    """
    Discovers Australian businesses via Yellow Pages AU + Jina reader.
    Replaces MapsFirstDiscovery as the primary T0 discovery source.

    Cost: $0 (free)
    Volume: 18,000 raw leads per full run
    """

    def __init__(self, categories: list[str], locations: list[str]):
        self.categories = categories
        self.locations = locations

    async def discover(self, campaign_config: CampaignConfig) -> list[DiscoveryResult]:
        # 1. Scrape YP
        raw_leads = await bulk_discover(self.categories, self.locations)

        # 2. ICP filter
        filtered = [(l, *apply_icp_filter(l)) for l in raw_leads]
        filtered = [(l, reason) for l, passes, reason in filtered if passes]

        # 3. Score
        scored = [(l, *score_free_signals(l)) for l, _ in filtered]
        qualified = [(l, score, sigs) for l, score, sigs in scored if score >= STAGE_3_GATE]

        # Convert to DiscoveryResult format (matches existing interface)
        return [
            DiscoveryResult(
                abn=None,
                business_name=lead.name,
                trading_name=None,
                source="yellowpages_au",
                raw_data={
                    "phone": lead.phone,
                    "address": lead.address,
                    "rating": lead.rating,
                    "review_count": lead.review_count,
                    "years_in_business": lead.years_in_business,
                    "is_advertiser": lead.is_advertiser,
                    "website": lead.website_url,
                    "icp_score": score,
                    "icp_signals": signals,
                    "yp_url": lead.yp_url,
                },
                dedup_hash=hashlib.md5(
                    f"{lead.name}:{lead.phone}".encode()
                ).hexdigest(),
            )
            for lead, score, signals in qualified
        ]
```

### Modification in `campaign_trigger.py`

In the `_enrich_lead` method, add gap scoring before the existing T0 GMB step:

```python
async def _enrich_lead(self, lead: LeadRecord) -> LeadRecord:
    # ── NEW: Website audit + SEO gap (runs before expensive enrichment) ──
    if lead.website:
        website_audit = await audit_website(lead.website)
        lead.raw_data["website_audit"] = asdict(website_audit)

        # Owner name from website (free)
        if website_audit.owner_name and not lead.decision_makers:
            lead.decision_makers = [{"name": website_audit.owner_name, "source": "website_audit"}]

        # SEO gap analysis
        seo_signals = await get_seo_signals(
            domain=urlparse(lead.website).netloc,
            category=lead.category or "",
            location=lead.state or "",
        )
        lead.raw_data["seo_signals"] = asdict(seo_signals)

    # ── EXISTING: T0 GMB → T1 ABN → T1.5a SERP → ... ──
    # (unchanged — GMB now acts as enrichment rather than discovery)
    ...
```

---

## SUMMARY TABLE

| Stage | File | Cost | Leads In | Leads Out |
|-------|------|------|----------|-----------|
| 1 Discovery | yp_scraper.py (NEW) | $0 | — | 18,000 |
| 2 ICP Filter | discovery_modes.py | $0 | 18,000 | 9,000 |
| 3 Signal Score | discovery_modes.py | $0 | 9,000 | 3,150 |
| 4 Website Audit | website_auditor.py (NEW) | $0 | 3,150 | 2,520 |
| 5 ABN Lookup | abn_client.py (existing) | $0 | 2,520 | 2,520 |
| 6 SEO Gap | dataforseo_seo.py (NEW) | $12.60 | 2,520 | 2,520 |
| 7 GMB Compare | bright_data_client.py (existing) | $1.89 | 1,260 | 1,260 |
| 8 Gap Gate | campaign_trigger.py | $0 | 1,260 | 630 |
| 9 LI DM Name | bright_data_client.py (existing) | $3.46 | 346 | 277 |
| 10 LI DM Profile | bright_data_client.py (existing) | $6.65 | 554 | 443 |
| 11 Email | leadmagic.py (existing) | $9.45 | 630 | 410 |
| 12 Mobile | leadmagic.py (existing) | $24.25 | 315 | 126 |
| 13 Social | website_auditor.py (NEW) | $0 | 630 | 630 |
| 14 Personalisation | personalisation_engine.py (NEW) | $1.89 | 630 | 630 |
| **TOTAL** | | **$60.19** | | **~390 complete** |

---

## NEW FILES TO CREATE

1. `src/integrations/yp_scraper.py` — Yellow Pages AU discovery
2. `src/integrations/website_auditor.py` — Website pixel/owner/social audit
3. `src/integrations/dataforseo_seo.py` — SEO gap analysis
4. `src/integrations/personalisation_engine.py` — AI outreach personalisation
5. `src/models/campaign_ready_lead.py` — Unified output dataclass

## FILES TO MODIFY

6. `src/pipeline/discovery_modes.py` — Add `YPFirstDiscovery` class
7. `src/pipeline/campaign_trigger.py` — Wire YP as T0, add gap scoring pre-step
8. `src/pipeline/waterfall_v2.py` — Add stages 6-14 to the pipeline

---

## CONVENTIONS TO FOLLOW

- All costs tracked in AUD in structlog events: `cost_aud=0.015`
- Async/await throughout
- structlog for all logging: `logger.bind(...)`, `logger.info(...)`, `logger.warning(...)`
- Full type hints
- Full docstrings with Args/Returns/Cost
- LAW compliance (read LAW files in codebase)
- Do NOT break existing tests
- Add unit tests for all new modules
