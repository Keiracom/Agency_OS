---
name: apify
description: Use when running web scrapers at scale. Apify actors for scraping websites, extracting structured data, handling anti-bot measures. Triggers on "scrape", "crawl", "extract data from site", "apify", bulk web data collection.
metadata: {"clawdbot":{"emoji":"🕷️","os":["darwin","linux"]}}
---

# Apify

Web scraping platform API for running actors (scrapers) and retrieving datasets.

## Config

| Variable | Description |
|----------|-------------|
| `APIFY_TOKEN` | API token from [Apify Console](https://console.apify.com/account#/integrations) |

**Base URL:** `https://api.apify.com/v2`

## Authentication

Two methods (header preferred):

```bash
# Header (recommended)
curl -H "Authorization: Bearer $APIFY_TOKEN" "https://api.apify.com/v2/acts"

# Query param (less secure)
curl "https://api.apify.com/v2/acts?token=$APIFY_TOKEN"
```

## Core Endpoints

### List Actors
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/acts"
```

### Run Actor
```bash
curl -X POST "https://api.apify.com/v2/acts/{actorId}/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {...}}'
```
**Response includes:** `defaultDatasetId`, `id` (run ID), `status`

### Run Actor Synchronously (waits up to 5 min)
```bash
curl -X POST "https://api.apify.com/v2/acts/{actorId}/run-sync?outputRecordKey=OUTPUT" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {...}}'
```

### Get Run Status
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/acts/{actorId}/runs/{runId}"
```
**Status values:** `READY`, `RUNNING`, `SUCCEEDED`, `FAILED`, `ABORTED`, `TIMED-OUT`

### List Runs
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/acts/{actorId}/runs?limit=10&desc=1"
```

### Get Dataset Items
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/datasets/{datasetId}/items?format=json"
```
Formats: `json`, `csv`, `xlsx`, `xml`, `html`, `rss`

### Get User Info & Usage
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/users/me"

curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/users/me/usage/monthly"
```

## Common Actors

### YouTube Scraper
**Actor ID:** `streamers/youtube-scraper` (or `h7sDV53CddomktSi5`)

```bash
# Scrape by URL
curl -X POST "https://api.apify.com/v2/acts/streamers~youtube-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "startUrls": [{"url": "https://www.youtube.com/@ChannelName"}],
    "maxResults": 50
  }'

# Scrape by search term
curl -X POST "https://api.apify.com/v2/acts/streamers~youtube-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "searchKeywords": "machine learning tutorial",
    "maxResults": 20
  }'
```
**Output:** video IDs, titles, URLs, views, likes, duration, channel info, subtitles

### Twitter/X Scraper
**Actor ID:** `apidojo/tweet-scraper` (Tweet Scraper V2)

```bash
curl -X POST "https://api.apify.com/v2/acts/apidojo~tweet-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "searchTerms": ["from:NASA since:2024-01-01"],
    "sort": "Latest",
    "maxItems": 100
  }'
```

**Query Examples:**
- `from:username` - tweets from user
- `@username` - mentions of user
- `#hashtag lang:en` - hashtag + language
- `keyword filter:media` - with media
- `-filter:retweets` - exclude retweets
- `filter:verified` - only verified users
- `since:2024-01-01 until:2024-06-01` - date range

**Pricing:** $0.40 per 1,000 tweets. Min 50 tweets per query.

### Reddit Scraper
**Actor ID:** `trudax/reddit-scraper`

```bash
# Scrape subreddit
curl -X POST "https://api.apify.com/v2/acts/trudax~reddit-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "startUrls": [{"url": "https://www.reddit.com/r/technology/"}],
    "maxItems": 100,
    "sort": "hot"
  }'

# Search by keyword
curl -X POST "https://api.apify.com/v2/acts/trudax~reddit-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "searchTerms": ["artificial intelligence"],
    "maxItems": 50
  }'
```
**Output:** posts, comments, usernames, votes, timestamps, media elements

**Cost:** ~$4 per 1,000 results

## Rate Limits

| Scope | Limit |
|-------|-------|
| Global | 250,000 req/min (per user) |
| Per resource (default) | 60 req/sec |
| Run Actor | 400 req/sec |
| Dataset push | 400 req/sec |
| Key-value CRUD | 200 req/sec |

**429 response:** Implement exponential backoff (start 500ms, double on each retry).

## Typical Workflow

1. **Run actor** → returns `runId` and `defaultDatasetId`
2. **Poll status** → check until `SUCCEEDED` or `FAILED`
3. **Fetch results** → GET dataset items

```bash
# 1. Start run
RUN=$(curl -s -X POST "https://api.apify.com/v2/acts/trudax~reddit-scraper/runs" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"startUrls":[{"url":"https://reddit.com/r/technology"}],"maxItems":10}')

RUN_ID=$(echo $RUN | jq -r '.data.id')
DATASET_ID=$(echo $RUN | jq -r '.data.defaultDatasetId')

# 2. Check status (poll until SUCCEEDED)
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/acts/trudax~reddit-scraper/runs/$RUN_ID" | jq '.data.status'

# 3. Get results
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/datasets/$DATASET_ID/items"
```

## Billing & Usage

- **Free tier:** $5/month in credits
- **Compute units:** Billed by actor runtime (memory × time)
- **Platform fees:** Some actors have per-item pricing (e.g., Tweet Scraper)

Check usage:
```bash
curl -H "Authorization: Bearer $APIFY_TOKEN" \
  "https://api.apify.com/v2/users/me/usage/monthly"
```

## Notes

- Actor IDs can be numeric (`h7sDV53CddomktSi5`) or named (`username~actor-name`, `username/actor-name`)
- Sync runs timeout after 300s (5 min) - use async + polling for longer jobs
- Response data is in `.data` wrapper (except dataset items)
- Use `jq` to parse JSON responses
