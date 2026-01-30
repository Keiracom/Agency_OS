# Scraping Tools

## Apify Actors

We use Apify for managed web scraping. API key in env: `APIFY_TOKEN`

### x-trends (Twitter/X Trending Topics)
- **Actor:** `eunit/x-twitter-trends-scraper`
- **Status:** TRIAL (as of 2026-01-30)
- **Cost:** $0.0005/trend
- **Auth:** None required (no X API key needed)
- **Data:** Hashtags, tweet counts, ranks, 60+ countries/cities
- **Output:** JSON with timeline, tag_cloud, table_data

**Usage:**
```python
from apify_client import ApifyClient
client = ApifyClient(os.environ['APIFY_TOKEN'])

run = client.actor("eunit/x-twitter-trends-scraper").call(
    run_input={"country": "united-states/new-york"}
)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(item)
```

**Limitations:**
- Scrapes trends24.in (not X directly) - may lag real-time
- Actor reliability depends on third-party site stability

---

## Other Apify Actors
(Add as evaluated)

---
*Last updated: 2026-01-30*
