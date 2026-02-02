---
name: social-tool
description: Unified social media scraping - Twitter, Reddit, HackerNews, Dev.to. Search posts, get trending topics, find top content across platforms.
metadata:
  clawdbot:
    emoji: "📱"
    always: false
    requires:
      bins: ["python3"]
schema:
  type: object
  required: ["action", "platform"]
  properties:
    action:
      type: string
      enum: ["search", "trending", "top"]
      description: "Action to perform"
    platform:
      type: string
      enum: ["twitter", "reddit", "hn", "devto"]
      description: "Platform to query"
    query:
      type: string
      description: "Search query (required for action=search)"
    subreddit:
      type: string
      description: "Subreddit name for Reddit queries"
    tag:
      type: string
      description: "Tag for Dev.to filtering"
    limit:
      type: integer
      default: 20
      description: "Number of results"
---

# Social Tool 📱

Unified interface for social media scraping across multiple platforms.

## Platforms

| Platform | Actions | No Auth Required |
|----------|---------|------------------|
| `twitter` | search, trending | ✅ (via snscrape) |
| `reddit` | search, top | ✅ (old.reddit.com) |
| `hn` | search, trending | ✅ (Algolia API) |
| `devto` | search, top | ✅ (Public API) |

## Usage

```bash
python3 tools/social_master.py <action> <platform> [query] [options]
```

## Examples

### Search
```bash
# Search Twitter for AI discussions
python3 tools/social_master.py search twitter "AI agents"

# Search Reddit in specific subreddit
python3 tools/social_master.py search reddit "automation" --subreddit=python

# Search HackerNews
python3 tools/social_master.py search hn "vector database"

# Search Dev.to by tag
python3 tools/social_master.py search devto --tag=ai
```

### Trending / Top
```bash
# Get HN front page
python3 tools/social_master.py trending hn

# Get top posts from subreddit
python3 tools/social_master.py top reddit --subreddit=LocalLLaMA --timeframe=week

# Get top Dev.to articles
python3 tools/social_master.py top devto --tag=webdev
```

## Options

| Option | Description |
|--------|-------------|
| `--limit N` | Number of results (default: 20) |
| `--subreddit NAME` | Reddit subreddit |
| `--tag NAME` | Dev.to tag |
| `--timeframe` | day/week/month/year/all |
| `--json` | Output raw JSON |

## Output Format

Returns formatted results with:
- Title/content preview
- Engagement metrics (likes, comments, points)
- URLs

## Replaces

This tool consolidates:
- `skills/twitter/`
- `skills/x-trends/`
- `skills/reddit/`
- `skills/hackernews/`
- `skills/devto/`
