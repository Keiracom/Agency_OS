---
name: twitter
description: Use when scraping Twitter/X without API key. Search tweets, get user timelines, filter by likes/RTs/date. Uses snscrape + Nitter fallback. Triggers on "tweets about", "twitter search", "x posts", "scrape twitter", social monitoring.
metadata: {"clawdbot":{"emoji":"🐦"}}
---

# Twitter/X Scraping (Native, No API Key)

## 1. Overview
- Native Python Twitter scraping without API key ($0 cost)
- Primary: snscrape library
- Fallback: Nitter RSS feeds

## 2. Installation
```bash
pip install snscrape
```

## 3. Search Tweets with snscrape
```python
import snscrape.modules.twitter as sntwitter

# Search by keyword
query = "AI agents lang:en"
scraper = sntwitter.TwitterSearchScraper(query)

for i, tweet in enumerate(scraper.get_items()):
    if i >= 100:
        break
    print(tweet.rawContent)
    print(f"Likes: {tweet.likeCount}, RTs: {tweet.retweetCount}")
```

## 4. Search Operators
| Operator | Description |
|----------|-------------|
| `keyword` | basic search |
| `from:username` | tweets from user |
| `to:username` | replies to user |
| `@username` | mentions |
| `#hashtag` | hashtag |
| `lang:en` | language filter |
| `since:2024-01-01` | date filter |
| `until:2024-06-01` | end date |
| `filter:verified` | only verified |
| `filter:media` | has media |
| `min_faves:100` | minimum likes |
| `min_retweets:50` | minimum RTs |
| `-filter:retweets` | exclude RTs |

**Combine operators:** `AI agents from:elikiara lang:en since:2024-01-01 min_faves:10`

## 5. Get User Tweets
```python
# All tweets from a user
scraper = sntwitter.TwitterUserScraper("username")
for tweet in scraper.get_items():
    print(tweet.rawContent)
```

## 6. Tweet Object Structure
```python
tweet.id            # Tweet ID
tweet.url           # Full URL
tweet.rawContent    # Tweet text
tweet.date          # datetime
tweet.user.username # @handle
tweet.user.displayname
tweet.user.followersCount
tweet.user.verified
tweet.likeCount
tweet.retweetCount
tweet.replyCount
tweet.quoteCount
tweet.media         # List of media
tweet.hashtags      # List of hashtags
tweet.mentionedUsers
```

## 7. Nitter Fallback (RSS)
If snscrape breaks (Twitter changes often):
```python
import feedparser

# Public nitter instances
NITTER_INSTANCES = [
    "nitter.net",
    "nitter.cz",
    "nitter.poast.org"
]

def get_user_feed(username: str):
    for instance in NITTER_INSTANCES:
        try:
            url = f"https://{instance}/{username}/rss"
            feed = feedparser.parse(url)
            if feed.entries:
                return feed.entries
        except:
            continue
    return []
```

## 8. Rate Limits
- snscrape: No official limits, but be respectful
- Recommend: 1 second between requests
- Heavy scraping may get IP blocked
- Consider rotating proxies for scale

## 9. Common Issues
| Issue | Mitigation |
|-------|------------|
| snscrape breaks after Twitter changes | Use Nitter fallback, check for library updates |
| Nitter instances go down | Rotate through multiple instances |
| Tweets unavailable | Handle exceptions, skip deleted/private tweets |
| Rate limiting | Add delays, use proxies for scale |

## 10. Full Example
```python
import snscrape.modules.twitter as sntwitter
import time

def search_tweets(query: str, limit: int = 50):
    results = []
    scraper = sntwitter.TwitterSearchScraper(f"{query} lang:en")
    
    for i, tweet in enumerate(scraper.get_items()):
        if i >= limit:
            break
        results.append({
            'text': tweet.rawContent,
            'author': tweet.user.username,
            'likes': tweet.likeCount,
            'date': tweet.date.isoformat(),
            'url': tweet.url
        })
    
    return results

def get_user_tweets(username: str, limit: int = 50):
    results = []
    scraper = sntwitter.TwitterUserScraper(username)
    
    for i, tweet in enumerate(scraper.get_items()):
        if i >= limit:
            break
        results.append({
            'text': tweet.rawContent,
            'likes': tweet.likeCount,
            'retweets': tweet.retweetCount,
            'date': tweet.date.isoformat(),
            'url': tweet.url
        })
    
    return results

# Usage
tweets = search_tweets("AI agents", limit=20)
user_tweets = get_user_tweets("elikiara", limit=10)
```

## 11. Important Notes
- **Cost:** $0 - no API key required
- **Reliability:** snscrape depends on Twitter's public web interface; may break with site changes
- **Legal:** Respect Twitter's ToS; use for research/personal purposes
- **Updates:** Check `pip install --upgrade snscrape` periodically
