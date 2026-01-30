# Competitor Scan Template

## Purpose
Scrape and analyze a competitor's website to understand their positioning, offerings, and market strategy.

## Input Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `COMPETITOR_URL` | ✅ | Main website URL (e.g., `https://competitor.com`) |
| `COMPETITOR_NAME` | ✅ | Company name |
| `OUR_PRODUCT` | ❌ | Your product for comparison context |
| `FOCUS_AREAS` | ❌ | pricing/features/messaging/all (default: all) |
| `DEPTH` | ❌ | homepage/shallow/deep (default: shallow) |

## Instructions

### Step 1: Scrape Website via Apify
```bash
# Load API key
source ~/.config/agency-os/.env

# Use website content crawler
curl -X POST "https://api.apify.com/v2/acts/apify~website-content-crawler/runs?token=$APIFY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "startUrls": [{"url": "COMPETITOR_URL"}],
    "maxCrawlPages": 20,
    "crawlerType": "cheerio"
  }'
```

Or for simpler extraction:
```bash
# Use web scraper
curl -X POST "https://api.apify.com/v2/acts/apify~web-scraper/run-sync-get-dataset-items?token=$APIFY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "startUrls": [{"url": "COMPETITOR_URL"}],
    "pageFunction": "async function pageFunction(context) { return { url: context.request.url, title: document.title, text: document.body.innerText }; }"
  }'
```

### Step 2: Key Pages to Analyze
- Homepage (hero, value prop)
- Pricing page
- Features/Product page
- About/Team page
- Case Studies/Testimonials
- Blog (recent posts)

### Step 3: Analysis Framework

#### Positioning Analysis
- **Tagline/Hero:** What's their main message?
- **Target Audience:** Who are they speaking to?
- **Unique Value Prop:** What makes them different?
- **Pain Points Addressed:** What problems do they solve?

#### Product Analysis
- **Core Features:** What do they offer?
- **Pricing Model:** How do they charge?
- **Integrations:** What do they connect with?
- **Tech Stack:** Any hints about their infrastructure?

#### Messaging Analysis
- **Tone of Voice:** Professional/casual/technical?
- **Key Phrases:** Repeated language patterns
- **Social Proof:** How do they build trust?
- **CTAs:** What actions do they push?

## Expected Output Format

```markdown
# 🔍 Competitor Scan: [COMPETITOR_NAME]

**URL:** COMPETITOR_URL
**Scanned:** YYYY-MM-DD
**Industry:** [Industry]

## 📍 Positioning

### Tagline
> "[Their main tagline/hero text]"

### Target Audience
- Primary: [Persona 1]
- Secondary: [Persona 2]

### Value Proposition
[What they promise in 1-2 sentences]

## 🛠️ Product

### Core Features
| Feature | Description | Our Comparison |
|---------|-------------|----------------|
| Feature 1 | ... | ✅/❌/🔄 |

### Pricing
| Tier | Price | Includes |
|------|-------|----------|
| Free | $0 | ... |
| Pro | $X/mo | ... |

## 💬 Messaging

### Tone
[Professional/Casual/Technical/Friendly]

### Key Phrases (Repeated)
- "Phrase 1"
- "Phrase 2"

### Social Proof
- X customers
- Notable logos: [Company1, Company2]
- Testimonial themes: [Speed, Support, etc.]

## 📊 SWOT Analysis

| Strengths | Weaknesses |
|-----------|------------|
| - Point 1 | - Point 1 |

| Opportunities | Threats |
|---------------|---------|
| - Point 1 | - Point 1 |

## 🎯 Strategic Insights

### What They Do Well
- Insight 1

### Where They're Vulnerable
- Opportunity 1

### How We Can Differentiate
- Strategy 1

## 🔗 Links Collected
- Pricing: [URL]
- Docs: [URL]
- Blog: [URL]
```

## Example Usage
```
@elliot Run competitor-scan template for https://competitor.com (compare to Agency OS)
```

## Notes
- Respect robots.txt and rate limits
- Re-run quarterly to track changes
- Save historical scans for trend analysis
- Cross-reference with G2/Capterra reviews for customer sentiment
