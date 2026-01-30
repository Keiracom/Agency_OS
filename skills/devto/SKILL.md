# Dev.to Scraping Skill

Fetch and analyze articles from Dev.to using the Forem API v1.

## Base URL

```
https://dev.to/api
```

## Endpoints

### 1. Articles Listing

```bash
GET https://dev.to/api/articles
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tag` | string | Filter by tag. Multiple: `tag=ai,machinelearning` |
| `username` | string | Filter by author username |
| `state` | string | `fresh`, `rising`, `all` (default: `all`) |
| `per_page` | int | Results per page (default: 30, max: 1000) |
| `page` | int | Pagination (1-indexed) |
| `top` | int | Top articles by timeframe: `1` (day), `7` (week), `30` (month), `365` (year), `infinity` |
| `collection_id` | int | Filter by article series |

### 2. Single Article

```bash
GET https://dev.to/api/articles/{id}
# Returns full body_html and body_markdown
```

### 3. Article by Path

```bash
GET https://dev.to/api/articles/{username}/{slug}
```

## Common Queries

```bash
# Top AI articles this week
curl "https://dev.to/api/articles?tag=ai&top=7&per_page=30"

# Top AI articles this month
curl "https://dev.to/api/articles?tag=ai&top=30&per_page=30"

# Multiple tags (OR logic)
curl "https://dev.to/api/articles?tag=ai,machinelearning&per_page=50"

# Articles by username
curl "https://dev.to/api/articles?username=bengreenberg&per_page=20"

# Rising articles in a tag
curl "https://dev.to/api/articles?tag=llm&state=rising"

# Fresh articles (newest first)
curl "https://dev.to/api/articles?tag=python&state=fresh&per_page=25"
```

## Response Schema

Articles endpoint returns array:

```json
[
  {
    "type_of": "article",
    "id": 12345,
    "title": "Article Title",
    "description": "Short description...",
    "readable_publish_date": "Jan 30",
    "slug": "article-title-abc1",
    "path": "/username/article-title-abc1",
    "url": "https://dev.to/username/article-title-abc1",
    "comments_count": 42,
    "public_reactions_count": 156,
    "positive_reactions_count": 156,
    "published_timestamp": "2026-01-30T12:00:00Z",
    "published_at": "2026-01-30T12:00:00Z",
    "reading_time_minutes": 5,
    "tag_list": ["ai", "python", "machinelearning"],
    "tags": "ai, python, machinelearning",
    "user": {
      "name": "Author Name",
      "username": "authorhandle",
      "twitter_username": "twitter_handle",
      "github_username": "github_handle",
      "profile_image": "https://..."
    }
  }
]
```

### Key Fields to Extract

```
[].{
  id,
  title,
  description,
  url,
  tags,
  positive_reactions_count,
  comments_count,
  published_at,
  reading_time_minutes,
  user.username
}
```

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests/minute | 30 |
| Recommended delay | 2 seconds between requests |
| Auth required | No (public endpoints) |

**Headers for identification (optional but recommended):**
```bash
-H "User-Agent: AgencyOS/1.0"
```

## Useful Tags

| Category | Tags |
|----------|------|
| AI/ML | `ai`, `machinelearning`, `llm`, `openai`, `langchain`, `rag` |
| Automation | `automation`, `devops`, `cicd`, `github-actions` |
| Languages | `python`, `javascript`, `typescript`, `go`, `rust` |
| Business | `saas`, `startup`, `productivity`, `career` |
| Agents | `agents`, `chatgpt`, `claude`, `copilot` |

## Pagination Pattern

```bash
# Page through all results
page=1
while true; do
  response=$(curl -s "https://dev.to/api/articles?tag=ai&per_page=100&page=$page")
  count=$(echo "$response" | jq length)
  [ "$count" -eq 0 ] && break
  echo "$response" >> all_articles.json
  ((page++))
  sleep 2
done
```

## jq Parsing Examples

```bash
# Extract titles and URLs
curl -s "https://dev.to/api/articles?tag=ai&top=7" | \
  jq -r '.[] | "\(.title) - \(.url)"'

# Top 10 by reactions
curl -s "https://dev.to/api/articles?tag=ai&top=30&per_page=100" | \
  jq -r 'sort_by(-.positive_reactions_count) | .[0:10] | .[] | "\(.positive_reactions_count) - \(.title)"'

# Extract for CSV
curl -s "https://dev.to/api/articles?tag=llm&per_page=50" | \
  jq -r '.[] | [.id, .title, .url, .positive_reactions_count, .comments_count, .published_at, .user.username] | @csv'
```

## Error Handling

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 404 | Article/User not found |
| 429 | Rate limited (wait and retry) |
| 500 | Server error (retry with backoff) |

## Notes

- No authentication required for read operations
- `top` parameter filters by most popular in timeframe
- Multiple tags use OR logic (matches any tag)
- Response includes `url` field with full article link
- `body_html` and `body_markdown` only on single-article endpoint
