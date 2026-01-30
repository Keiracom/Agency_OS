# Reddit Scraping Skill

Public JSON endpoints for scraping Reddit without authentication.

## ⚠️ Critical: Use old.reddit.com

**ALWAYS** use `old.reddit.com` - new Reddit blocks bots/scrapers.

## Endpoints

### Browse Posts
```
https://old.reddit.com/r/{subreddit}/hot.json
https://old.reddit.com/r/{subreddit}/new.json
https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}
https://old.reddit.com/r/{subreddit}/rising.json
```

### Search Within Subreddit
```
https://old.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=on
```

### Search All Reddit
```
https://old.reddit.com/search.json?q={query}
```

### Get Post Comments
```
https://old.reddit.com/r/{subreddit}/comments/{post_id}.json
```

---

## Required Headers

```bash
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

Without a browser-like User-Agent, you'll get 403 Forbidden.

---

## Search Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `q` | string | Search query (URL encode spaces as `+`) |
| `sort` | `relevance`, `hot`, `top`, `new`, `comments` | Sort order |
| `t` | `hour`, `day`, `week`, `month`, `year`, `all` | Time filter (for top/relevance) |
| `limit` | 1-100 | Results per request (max 100) |
| `restrict_sr` | `on` | Restrict to subreddit (required for subreddit search) |
| `after` | `t3_xxxxx` | Pagination cursor (fullname of last post) |

---

## Example Queries

### Search r/SaaS for AI agents
```bash
curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://old.reddit.com/r/SaaS/search.json?q=AI+agents&sort=relevance&t=all&limit=50&restrict_sr=on"
```

### Get top posts from r/startups this month
```bash
curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://old.reddit.com/r/startups/top.json?t=month&limit=25"
```

### Search for outbound sales pain points
```bash
curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://old.reddit.com/r/sales/search.json?q=outbound+cold+email&sort=top&t=year&limit=100&restrict_sr=on"
```

---

## Response Structure

```json
{
  "kind": "Listing",
  "data": {
    "after": "t3_abc123",  // Pagination cursor
    "children": [
      {
        "kind": "t3",
        "data": {
          "title": "Post title",
          "selftext": "Post body (for text posts)",
          "url": "https://...",
          "score": 142,
          "author": "username",
          "created_utc": 1704067200,
          "num_comments": 47,
          "permalink": "/r/SaaS/comments/abc123/post_title/",
          "subreddit": "SaaS",
          "is_self": true,
          "link_flair_text": "Question"
        }
      }
    ]
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `title` | Post title |
| `selftext` | Body text (empty for link posts) |
| `url` | Link URL or self post URL |
| `score` | Upvotes minus downvotes |
| `author` | Username (may be `[deleted]`) |
| `created_utc` | Unix timestamp |
| `num_comments` | Comment count |
| `permalink` | Relative URL to post |
| `is_self` | true = text post, false = link post |

---

## Rate Limits

- **No official limit** for public JSON endpoints
- **Recommend:** 2 second delay between requests
- **Reality:** Reddit WILL block aggressive scrapers (429 or shadow-block)
- **Best practice:** Cache results, don't re-scrape unnecessarily

---

## Pagination

Use `after` parameter with the `name` (fullname) of the last post:

```bash
# First page
curl "https://old.reddit.com/r/SaaS/top.json?t=all&limit=100"
# Response includes: "after": "t3_xyz789"

# Next page
curl "https://old.reddit.com/r/SaaS/top.json?t=all&limit=100&after=t3_xyz789"
```

---

## Relevant Subreddits

### SaaS & Business
- r/SaaS - SaaS founders and operators
- r/Entrepreneur - General entrepreneurship
- r/startups - Startup advice and stories
- r/sales - Sales professionals
- r/marketing - Marketing discussion
- r/growmybusiness - Growth tactics

### AI & Tech
- r/LocalLLaMA - Self-hosted LLMs
- r/ClaudeAI - Claude users
- r/ChatGPT - ChatGPT users
- r/artificial - AI discussion
- r/MachineLearning - ML research

### Outreach & Lead Gen
- r/Emailmarketing - Email marketing
- r/coldemail - Cold email tactics
- r/b2bmarketing - B2B marketing

---

## Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| 403 Forbidden | Wrong User-Agent | Use browser-like UA string |
| 403 Forbidden | Using www.reddit.com | Switch to old.reddit.com |
| 429 Too Many Requests | Rate limited | Add delays, reduce frequency |
| Empty results | Query too specific | Broaden search terms |
| `[deleted]` author | User deleted account | Normal, ignore |

---

## Quick Reference

```bash
# Template
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Search subreddit
curl -s -H "User-Agent: $UA" \
  "https://old.reddit.com/r/SUBREDDIT/search.json?q=QUERY&sort=relevance&t=all&limit=100&restrict_sr=on"

# Top posts
curl -s -H "User-Agent: $UA" \
  "https://old.reddit.com/r/SUBREDDIT/top.json?t=month&limit=100"

# Parse with jq
curl -s -H "User-Agent: $UA" "URL" | jq '.data.children[].data | {title, score, url, author}'
```
