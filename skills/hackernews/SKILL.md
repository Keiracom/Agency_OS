---
name: hackernews
description: Use when scraping HackerNews via Algolia API. Search stories, comments, Show HN, Ask HN by keyword or author. Filter by points, date, comments. Triggers on "hackernews", "hn", "what's trending tech", "show hn", tech discussions.
metadata: {"clawdbot":{"emoji":"🔶"}}
---

# HackerNews Algolia API

## Overview

The Algolia HN Search API provides programmatic access to all Hacker News content since 2006. No authentication required.

**Base URL:** `https://hn.algolia.com/api/v1/`

> ⚠️ **MUST use HTTPS** - HTTP requests return 301 redirects and fail.

---

## Endpoints

### Search by Relevance

```
GET /search
```

Returns results sorted by relevance (popularity + recency).

### Search by Date

```
GET /search_by_date
```

Returns results sorted by creation date (newest first).

### Get Item

```
GET /items/{id}
```

Returns a single item (story, comment, poll) with nested children.

### Get User

```
GET /users/{username}
```

Returns user profile with karma and about text.

---

## Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Full-text search query |
| `tags` | string | Filter by tags (see Tags section) |
| `numericFilters` | string | Filter by numeric fields (see below) |
| `page` | int | Page number (0-indexed, max 500 pages) |
| `hitsPerPage` | int | Results per page (default 20, max 1000) |

---

## Tags

Filter content by type using the `tags` parameter.

### Content Types
| Tag | Description |
|-----|-------------|
| `story` | Stories (articles, links) |
| `comment` | Comments on stories |
| `poll` | Polls |
| `show_hn` | "Show HN" posts |
| `ask_hn` | "Ask HN" posts |
| `front_page` | Items currently on front page |

### Tag Logic

- **AND (default):** Comma-separated tags are ANDed  
  `tags=story,show_hn` → Stories that are Show HN posts

- **OR:** Parentheses create OR groups  
  `tags=(story,poll)` → Stories OR polls

- **Combined:**  
  `tags=(story,poll),show_hn` → (Stories OR polls) AND Show HN

### Author Tag
Filter by author: `tags=author_username`

```
tags=story,author_pg
```

---

## Numeric Filters

Filter by numeric fields using comparison operators.

### Available Fields

| Field | Description |
|-------|-------------|
| `points` | Upvotes/points |
| `num_comments` | Comment count |
| `created_at_i` | Unix timestamp |

### Operators

- `>` greater than
- `>=` greater than or equal
- `<` less than
- `<=` less than or equal
- `=` equal

### Examples

```
# Stories with 100+ points
numericFilters=points>100

# Multiple filters (comma = AND)
numericFilters=points>100,num_comments>50

# Created after specific timestamp
numericFilters=created_at_i>1704067200
```

---

## Response Format

### Search Response

```json
{
  "hits": [...],
  "nbHits": 1692534,
  "page": 0,
  "nbPages": 500,
  "hitsPerPage": 20,
  "processingTimeMS": 4,
  "query": "AI"
}
```

### Hit Object (Story)

```json
{
  "objectID": "39526057",
  "title": "Airfoil",
  "url": "https://example.com/article",
  "author": "username",
  "points": 2544,
  "num_comments": 296,
  "created_at": "2024-02-27T16:32:49Z",
  "created_at_i": 1709051569,
  "_tags": ["story", "author_username", "story_39526057"]
}
```

### Hit Object (Comment)

```json
{
  "objectID": "12345",
  "comment_text": "This is the comment...",
  "author": "username",
  "points": null,
  "story_id": 39526057,
  "story_title": "Parent Story Title",
  "story_url": "https://example.com/article",
  "parent_id": 39526057,
  "created_at": "2024-02-27T17:00:00Z",
  "created_at_i": 1709053200,
  "_tags": ["comment", "author_username", "story_39526057"]
}
```

### Item Response (with children)

```json
{
  "id": 1,
  "type": "story",
  "title": "Y Combinator",
  "url": "http://ycombinator.com",
  "author": "pg",
  "points": 57,
  "created_at": "2006-10-09T18:21:51.000Z",
  "children": [
    {
      "id": 15,
      "type": "comment",
      "text": "Comment text here...",
      "author": "sama",
      "parent_id": 1,
      "children": [...]
    }
  ]
}
```

### User Response

```json
{
  "username": "pg",
  "karma": 157316,
  "about": "Bug fixer."
}
```

---

## Example Queries

### Search Stories About AI with 50+ Points

```bash
curl "https://hn.algolia.com/api/v1/search?query=AI+agents&tags=story&numericFilters=points>50"
```

### Show HN Posts from Last Week

```bash
curl "https://hn.algolia.com/api/v1/search_by_date?tags=show_hn&numericFilters=created_at_i>$(date -d '7 days ago' +%s)"
```

### Top Comments by Specific User

```bash
curl "https://hn.algolia.com/api/v1/search?tags=comment,author_pg&numericFilters=points>10"
```

### Ask HN Posts with 100+ Comments

```bash
curl "https://hn.algolia.com/api/v1/search?tags=ask_hn&numericFilters=num_comments>100"
```

### Stories from Last 24 Hours

```bash
curl "https://hn.algolia.com/api/v1/search_by_date?tags=story&numericFilters=created_at_i>$(date -d '24 hours ago' +%s)"
```

### Front Page Items Right Now

```bash
curl "https://hn.algolia.com/api/v1/search?tags=front_page"
```

### Pagination Example

```bash
# Page 0 (first 20 results)
curl "https://hn.algolia.com/api/v1/search?query=rust&page=0&hitsPerPage=20"

# Page 1 (results 21-40)
curl "https://hn.algolia.com/api/v1/search?query=rust&page=1&hitsPerPage=20"
```

---

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests per hour | 10,000 |
| Recommended rate | 1 request/second |
| Max pages | 500 |
| Max hitsPerPage | 1,000 |

---

## Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| 301 redirect | Using `http://` | Always use `https://` |
| Empty results | Invalid tag combo | Check tag syntax |
| Truncated results | Page limit reached | Max 500 pages × hitsPerPage |
| Old data | Caching | Add cache-busting param |

---

## Quick Reference

```bash
# Base patterns
SEARCH="https://hn.algolia.com/api/v1/search"
SEARCH_DATE="https://hn.algolia.com/api/v1/search_by_date"
ITEM="https://hn.algolia.com/api/v1/items"
USER="https://hn.algolia.com/api/v1/users"

# Unix timestamp helpers
NOW=$(date +%s)
WEEK_AGO=$(date -d '7 days ago' +%s)
MONTH_AGO=$(date -d '30 days ago' +%s)

# Practical examples
# Hot AI stories this week
curl "$SEARCH?query=AI&tags=story&numericFilters=points>100,created_at_i>$WEEK_AGO"

# Get story with all comments
curl "$ITEM/39526057" | jq '.children'

# User karma lookup
curl "$USER/pg" | jq '.karma'
```

---

## Integration Tips

1. **Use `search_by_date` for monitoring** - Guarantees chronological order
2. **Cache aggressively** - Data doesn't change often
3. **Parse `created_at_i`** - Unix timestamp is easier than ISO date
4. **Check `_tags` array** - Contains useful metadata like author and story type
5. **Handle null `url`** - Ask HN posts don't have URLs (text-only)
