# Apify Untapped Capabilities — Implementation Plan

*Research completed: 2026-01-30*

---

## Executive Summary

**TOP 2 PICKS FOR THIS WEEK:**
1. **LinkedIn Jobs Scraper** — Hiring signals = growth timing
2. **Google News Scraper** — PR moments = personalized outreach

**Estimated cost impact:** +$1.50–2.50 per 1,000 leads enriched

---

## Actor Research Matrix

| Actor | Store URL | Pricing | Users | Rating | CU/1K Leads |
|-------|-----------|---------|-------|--------|-------------|
| **Google News Scraper** | [epctex/google-news-scraper](https://apify.com/epctex/google-news-scraper) | ~0.01-0.03 CU/100 items | 2K+ | ★★★★ | ~$0.30 |
| **LinkedIn Jobs Scraper** | [bebity/linkedin-jobs-scraper](https://apify.com/bebity/linkedin-jobs-scraper) | CU-based | 21K | 3.9★ | ~$1.00 |
| **Tweet Scraper V2** | [apidojo/tweet-scraper](https://apify.com/apidojo/tweet-scraper) | $0.40/1K tweets | 34K | 4.4★ | ~$2.00 |
| **Crunchbase Scraper** | [curious_coder/crunchbase-scraper](https://apify.com/curious_coder/crunchbase-scraper) | ~$0.73/1K records | 15K+ | ★★★★ | ~$0.73 |
| **YouTube Scraper** | [streamers/youtube-scraper](https://apify.com/streamers/youtube-scraper) | CU-based | 51K | 4.7★ | ~$1.50 |
| **Reddit Scraper** | [trudax/reddit-scraper](https://apify.com/trudax/reddit-scraper) | ~$4/1K results | 30K+ | ★★★★ | ~$4.00 |
| **Indeed Scraper** | [misceres/indeed-scraper](https://apify.com/misceres/indeed-scraper) | CU-based | 20K+ | ★★★★ | ~$1.20 |

---

## Value Ranking for Agency OS

### Tier 1: HIGH LEVERAGE (Implement This Week)

#### 🥇 #1: LinkedIn Jobs Scraper
**WHY:** Hiring = growth signal = budget exists = perfect outreach timing

- **Signal value:** Company hiring for marketing roles → actively investing in growth
- **Detector integration:** WHEN Detector (timing signals)
- **ALS impact:** +5-10 points for active hiring
- **ROI case:** 3x response rate on leads with active job postings (industry benchmark)

**Data fields we want:**
- Company name (match to lead)
- Job titles (marketing/growth/sales roles)
- Posted date (recency = urgency)
- Job count (velocity = scale of growth)

#### 🥈 #2: Google News Scraper  
**WHY:** Recent news = conversation starter + timing signal

- **Signal value:** Funding news, expansion, awards, new hires = outreach hooks
- **Detector integration:** WHEN Detector + personalization engine
- **ALS impact:** +3-5 points for recent positive coverage
- **ROI case:** Personalized icebreakers get 2x open rates

**Data fields we want:**
- Headlines mentioning company
- Source and date
- Article URL (for linking in outreach)
- Sentiment (expansion/funding = positive)

### Tier 2: MEDIUM VALUE (Phase 2)

#### #3: Crunchbase Scraper
**Issue:** Apollo already provides funding data. Only add if Apollo coverage gaps exist.
**Best for:** Deeper company intel (acquisitions, investor network)

#### #4: Indeed Scraper
**Issue:** Overlaps with LinkedIn Jobs. Only add for non-LinkedIn-present companies.

### Tier 3: LOW PRIORITY (Skip for Now)

#### #5: Twitter/X Scraper
- Expensive ($0.40/1K tweets)
- Australian B2B agencies aren't Twitter-heavy
- Pain point discovery requires NLP layer we don't have yet

#### #6: Reddit Scraper
- Great for market research, poor for individual lead enrichment
- High cost ($4/1K)
- Better suited for ICP research, not lead scoring

#### #7: YouTube Scraper
- Podcast guest discovery is niche
- Requires video-to-company matching logic
- Low hit rate for SMB agencies

---

## Implementation Spec: Top 2 Actors

### Integration Architecture

```
leads table
    ↓
Prefect: enrich_leads_tier2_apify
    ├── existing: LinkedIn Profile → company intel
    ├── existing: Website Crawler → tech stack
    ├── NEW: LinkedIn Jobs → hiring_signals
    └── NEW: Google News → news_mentions
    ↓
Supabase: leads.enrichment_data (JSONB)
    ↓
WHEN Detector → timing_score adjustment
    ↓
ALS recalculation
```

### Database Schema Changes

```sql
-- Add to leads.enrichment_data JSONB structure:
{
  "hiring_signals": {
    "job_count": 5,
    "marketing_roles": 2,
    "last_posting_date": "2026-01-28",
    "growth_velocity": "high",  -- high/medium/low
    "scraped_at": "2026-01-30T04:00:00Z"
  },
  "news_mentions": {
    "articles": [
      {
        "title": "Agency X raises $5M Series A",
        "source": "SmartCompany",
        "date": "2026-01-25",
        "url": "https://...",
        "sentiment": "positive"
      }
    ],
    "mention_count_30d": 3,
    "scraped_at": "2026-01-30T04:00:00Z"
  }
}
```

### Prefect Flow: `enrich_leads_jobs_news.py`

```python
from prefect import flow, task
from apify_client import ApifyClient
import os

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN")
client = ApifyClient(APIFY_TOKEN)

@task(retries=2, retry_delay_seconds=30)
async def scrape_linkedin_jobs(company_name: str) -> dict:
    """
    Scrape LinkedIn Jobs for hiring signals.
    Actor: bebity/linkedin-jobs-scraper
    Cost: ~0.001 CU per company
    """
    run_input = {
        "searchQueries": [company_name],
        "location": "Australia",
        "maxResults": 25,
    }
    
    run = client.actor("bebity/linkedin-jobs-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    # Process for hiring signals
    marketing_roles = [j for j in items if any(
        kw in j.get("title", "").lower() 
        for kw in ["marketing", "growth", "brand", "digital", "content"]
    )]
    
    return {
        "job_count": len(items),
        "marketing_roles": len(marketing_roles),
        "last_posting_date": items[0].get("postedAt") if items else None,
        "growth_velocity": "high" if len(items) > 10 else "medium" if len(items) > 3 else "low",
        "raw_jobs": items[:5],  # Keep top 5 for context
    }

@task(retries=2, retry_delay_seconds=30)
async def scrape_google_news(company_name: str) -> dict:
    """
    Scrape Google News for recent mentions.
    Actor: epctex/google-news-scraper
    Cost: ~0.0003 CU per company
    """
    run_input = {
        "search": company_name,
        "maxItems": 10,
        "date": "7d",  # Last 7 days
        "decodeArticleUrls": True,
        "proxy": {"useApifyProxy": True},
    }
    
    run = client.actor("epctex/google-news-scraper").call(run_input=run_input)
    items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    
    # Basic sentiment classification
    positive_keywords = ["funding", "raised", "growth", "expansion", "award", "launch"]
    
    articles = []
    for item in items:
        title = item.get("title", "").lower()
        sentiment = "positive" if any(kw in title for kw in positive_keywords) else "neutral"
        articles.append({
            "title": item.get("title"),
            "source": item.get("source"),
            "date": item.get("publishedAt"),
            "url": item.get("decodedArticleUrl") or item.get("articleUrl"),
            "sentiment": sentiment,
        })
    
    return {
        "articles": articles,
        "mention_count_30d": len(articles),
    }

@flow(name="enrich_leads_tier2_apify_extended")
async def enrich_leads_with_jobs_news(lead_ids: list[str]):
    """
    Enrich leads with hiring signals and news mentions.
    Run after Apollo enrichment, before ALS calculation.
    """
    from src.integrations.supabase_client import get_lead, update_lead_enrichment
    
    for lead_id in lead_ids:
        lead = await get_lead(lead_id)
        company_name = lead.get("company_name")
        
        if not company_name:
            continue
        
        # Parallel scraping
        jobs_future = scrape_linkedin_jobs.submit(company_name)
        news_future = scrape_google_news.submit(company_name)
        
        hiring_signals = await jobs_future.result()
        news_mentions = await news_future.result()
        
        # Update enrichment data
        enrichment_update = {
            "hiring_signals": hiring_signals,
            "news_mentions": news_mentions,
        }
        
        await update_lead_enrichment(lead_id, enrichment_update)
```

### WHEN Detector Integration

```python
# Add to src/detectors/when_detector.py

def calculate_hiring_signal_score(hiring_signals: dict) -> float:
    """
    Score based on hiring activity.
    High hiring = actively investing = better timing.
    """
    if not hiring_signals:
        return 0.0
    
    base_score = 0.0
    
    # Job count scoring
    job_count = hiring_signals.get("job_count", 0)
    if job_count > 10:
        base_score += 8
    elif job_count > 5:
        base_score += 5
    elif job_count > 0:
        base_score += 3
    
    # Marketing role bonus
    marketing_roles = hiring_signals.get("marketing_roles", 0)
    if marketing_roles > 0:
        base_score += min(marketing_roles * 2, 5)
    
    # Velocity bonus
    if hiring_signals.get("growth_velocity") == "high":
        base_score += 3
    
    return min(base_score, 15)  # Cap at 15 points

def calculate_news_signal_score(news_mentions: dict) -> float:
    """
    Score based on news recency and sentiment.
    Recent positive news = perfect outreach timing.
    """
    if not news_mentions:
        return 0.0
    
    articles = news_mentions.get("articles", [])
    if not articles:
        return 0.0
    
    positive_count = sum(1 for a in articles if a.get("sentiment") == "positive")
    
    base_score = 0.0
    
    # Any mention = engaged company
    if len(articles) > 0:
        base_score += 2
    
    # Positive coverage bonus
    base_score += min(positive_count * 3, 8)
    
    return min(base_score, 10)  # Cap at 10 points
```

### ALS Impact

| Signal | Max Points | Trigger |
|--------|------------|---------|
| Hiring activity | +15 | Any job postings |
| Marketing roles | +5 | Marketing/growth roles open |
| Positive news | +10 | Funding, expansion, awards |
| News recency | +3 | Coverage in last 7 days |

**Max potential ALS boost: +33 points**

---

## Cost Estimation

### Per 1,000 Leads Enriched

| Actor | Calls | Cost/Call | Total |
|-------|-------|-----------|-------|
| LinkedIn Jobs | 1,000 | ~$0.001 | ~$1.00 |
| Google News | 1,000 | ~$0.0003 | ~$0.30 |
| **Total new cost** | | | **~$1.30** |

### Monthly Projection (10K leads/month)

| Current Tier 2 Cost | + New Actors | New Total |
|---------------------|--------------|-----------|
| ~$50 | +$13 | ~$63 |

**Cost increase: ~26% for 2x data points**

---

## Deployment Checklist

### Week 1: LinkedIn Jobs Scraper
- [ ] Add `bebity/linkedin-jobs-scraper` to Apify workspace
- [ ] Create `scrape_linkedin_jobs` task in enrichment flow
- [ ] Add `hiring_signals` to enrichment JSONB schema
- [ ] Update WHEN Detector with `calculate_hiring_signal_score`
- [ ] Add ALS weight for hiring signals
- [ ] Test on 100 leads
- [ ] Monitor CU consumption

### Week 2: Google News Scraper
- [ ] Add `epctex/google-news-scraper` to Apify workspace
- [ ] Create `scrape_google_news` task
- [ ] Add `news_mentions` to enrichment schema
- [ ] Update WHEN Detector with `calculate_news_signal_score`
- [ ] Build personalization template using news hooks
- [ ] Test on 100 leads
- [ ] Monitor CU consumption

### Week 3: Optimization
- [ ] Analyze signal quality (which leads converted?)
- [ ] Tune ALS weights based on outcomes
- [ ] Set up caching (news doesn't change daily)
- [ ] Implement batch processing for cost efficiency

---

## Success Metrics

| Metric | Baseline | Target (30 days) |
|--------|----------|------------------|
| Response rate on hot leads | 8% | 12% |
| ALS accuracy (converted vs score) | Unknown | 70% correlation |
| Enrichment coverage | 60% | 80% |
| Cost per enriched lead | $0.05 | $0.07 |

---

## Rejected Alternatives (With Reasoning)

| Actor | Reason for Rejection |
|-------|---------------------|
| Twitter Scraper | High cost ($0.40/1K), low AU B2B usage |
| Reddit Scraper | Market research tool, not lead enrichment |
| YouTube Scraper | Complex matching, low hit rate |
| Crunchbase | Apollo overlap, add only if gaps found |
| Indeed | LinkedIn Jobs covers same signal |

---

*Prepared for Agency OS enrichment pipeline expansion*
