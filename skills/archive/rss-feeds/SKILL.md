---
name: rss-feeds
description: Use when fetching RSS/Atom feeds or monitoring newsletters. Parse Substack, blogs, company feeds. Get latest posts from feeds. Triggers on "rss", "feed", "substack", "newsletter", "blog updates", content syndication.
metadata: {"clawdbot":{"emoji":"📰"}}
---

# RSS & Substack Feed Scraping

## Overview

RSS (Really Simple Syndication) is a standardized XML format for syndicating content. Most blogs, newsletters, and news sites expose RSS feeds for programmatic consumption.

## Library

```bash
pip install feedparser
```

**feedparser** handles RSS, Atom, and various feed formats automatically.

---

## Finding RSS Feeds

### Substack Newsletters
Pattern: `https://{newsletter}.substack.com/feed`

### Generic Blogs
Check these common paths:
- `/feed`
- `/rss`
- `/feed.xml`
- `/rss.xml`
- `/atom.xml`
- `/index.xml`

### Discovery Tips
1. View page source, search for `application/rss+xml` or `application/atom+xml`
2. Check `<link rel="alternate" type="application/rss+xml">`
3. Append common paths to domain

---

## Key Newsletter Feeds

| Newsletter | Feed URL |
|------------|----------|
| Lenny's Newsletter | `https://www.lennysnewsletter.com/feed` |
| Latent Space | `https://www.latent.space/feed` |
| One Useful Thing | `https://www.oneusefulthing.org/feed` |
| Pragmatic Engineer | `https://newsletter.pragmaticengineer.com/feed` |
| Simon Willison | `https://simonwillison.net/atom/everything/` |

---

## AI Company Blogs

| Company | Feed URL | Notes |
|---------|----------|-------|
| OpenAI | `https://openai.com/blog/rss.xml` | Official RSS |
| LangChain | `https://blog.langchain.dev/rss/` | Official RSS |
| Hugging Face | `https://huggingface.co/blog/feed.xml` | Official RSS |
| Anthropic | N/A | No public RSS - scrape HTML or check news page |

---

## Python Usage

### Basic Example

```python
import feedparser

feed = feedparser.parse("https://www.latent.space/feed")

for entry in feed.entries[:10]:
    print(entry.title, entry.link, entry.published)
```

### Full Parsing

```python
import feedparser
from datetime import datetime

def fetch_feed(url: str) -> list[dict]:
    """Fetch and parse an RSS/Atom feed."""
    feed = feedparser.parse(url)
    
    if feed.bozo:  # Parse error occurred
        print(f"Warning: {feed.bozo_exception}")
    
    entries = []
    for entry in feed.entries:
        entries.append({
            "title": entry.get("title"),
            "link": entry.get("link"),
            "summary": entry.get("summary"),
            "published": entry.get("published"),
            "author": entry.get("author"),
            "content": entry.get("content", [{}])[0].get("value") if entry.get("content") else None,
        })
    
    return entries
```

### Batch Fetching with Rate Limiting

```python
import feedparser
import time
from collections import defaultdict

class FeedFetcher:
    def __init__(self, cache_ttl: int = 300):
        self.cache = {}
        self.cache_ttl = cache_ttl  # seconds
        self.last_fetch = defaultdict(float)
    
    def fetch(self, url: str, delay: float = 2.0) -> dict:
        """Fetch feed with caching and rate limiting."""
        now = time.time()
        
        # Check cache
        if url in self.cache:
            cached_time, cached_data = self.cache[url]
            if now - cached_time < self.cache_ttl:
                return cached_data
        
        # Rate limit per domain
        domain = url.split("/")[2]
        elapsed = now - self.last_fetch[domain]
        if elapsed < delay:
            time.sleep(delay - elapsed)
        
        # Fetch
        feed = feedparser.parse(url)
        self.last_fetch[domain] = time.time()
        self.cache[url] = (time.time(), feed)
        
        return feed

# Usage
fetcher = FeedFetcher(cache_ttl=600)  # 10 min cache
feed = fetcher.fetch("https://www.latent.space/feed")
```

---

## Response Structure

Each `feed.entries[]` item typically contains:

| Field | Description |
|-------|-------------|
| `title` | Article title |
| `link` | URL to full article |
| `summary` | Short description or excerpt |
| `published` | Publication date string |
| `author` | Author name |
| `content` | Full content (if provided) |
| `tags` | List of category/tag objects |

Feed metadata in `feed.feed`:
- `feed.feed.title` - Feed name
- `feed.feed.link` - Site URL
- `feed.feed.description` - Feed description

---

## Rate Limiting Best Practices

1. **Per-domain delays:** 2-5 seconds between requests to same domain
2. **Cache aggressively:** Most feeds update at most hourly
3. **Respect headers:** Check `Cache-Control` and `ETag` if available
4. **Batch wisely:** Fetch all feeds once, then wait before next cycle

```python
# Recommended delays
RATE_LIMITS = {
    "substack.com": 3.0,      # Be extra polite
    "simonwillison.net": 5.0, # Personal blog
    "openai.com": 2.0,
    "default": 2.0
}
```

---

## Common Issues & Solutions

### Partial Content
Many feeds only include summaries. Solutions:
1. Check `entry.content` for full content
2. Fetch the `entry.link` URL separately with `web_fetch`

### Date Parsing
```python
from email.utils import parsedate_to_datetime

# feedparser normalizes to time.struct_time
import time
published_struct = entry.published_parsed
if published_struct:
    timestamp = time.mktime(published_struct)
    dt = datetime.fromtimestamp(timestamp)
```

### Feed Errors
```python
feed = feedparser.parse(url)
if feed.bozo:
    # Parse error - feed may still have partial data
    print(f"Parse warning: {feed.bozo_exception}")
if not feed.entries:
    print("No entries found - check URL")
```

### Missing Fields
Always use `.get()` for optional fields:
```python
author = entry.get("author", "Unknown")
summary = entry.get("summary", "")[:500]  # Truncate
```

---

## Quick Reference

```python
import feedparser

FEEDS = {
    "latent_space": "https://www.latent.space/feed",
    "lenny": "https://www.lennysnewsletter.com/feed",
    "pragmatic": "https://newsletter.pragmaticengineer.com/feed",
    "one_useful": "https://www.oneusefulthing.org/feed",
    "simon": "https://simonwillison.net/atom/everything/",
    "openai": "https://openai.com/blog/rss.xml",
    "langchain": "https://blog.langchain.dev/rss/",
    "huggingface": "https://huggingface.co/blog/feed.xml",
}

def get_latest(feed_name: str, count: int = 5) -> list[dict]:
    url = FEEDS.get(feed_name)
    if not url:
        return []
    
    feed = feedparser.parse(url)
    return [
        {"title": e.title, "link": e.link, "published": e.get("published")}
        for e in feed.entries[:count]
    ]
```
