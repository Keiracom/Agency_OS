---
name: content-tool
description: Unified content scraping - YouTube, RSS feeds, arXiv papers. Search videos, fetch feeds, find research papers.
metadata:
  clawdbot:
    emoji: "📚"
schema:
  type: object
  required: ["action", "source"]
  properties:
    action:
      type: string
      enum: ["search", "fetch", "transcript"]
    source:
      type: string
      enum: ["youtube", "rss", "arxiv"]
    query:
      type: string
    url:
      type: string
      description: "RSS feed URL (for fetch action)"
    category:
      type: string
      description: "arXiv category (e.g., cs.AI)"
---

# Content Tool 📚

Unified interface for content scraping.

## Usage

```bash
python3 tools/content_master.py <action> <source> [query] [options]
```

## Examples

```bash
# Search YouTube
python3 tools/content_master.py search youtube "AI agents tutorial"

# Fetch RSS feed
python3 tools/content_master.py fetch rss --url "https://blog.example.com/feed"

# Search arXiv
python3 tools/content_master.py search arxiv "transformer architecture" --category cs.AI
```

## Replaces

- youtube, youtube-transcript, rss-feeds, arxiv
