---
name: github-search
description: Use when searching GitHub for repos, code, or users. Find repos by stars, language, topic. Search code patterns across GitHub. Triggers on "find repos", "github search", "code search", "popular libraries", open source discovery.
metadata: {"clawdbot":{"emoji":"🔍"}}
---

# GitHub Search API Skill

Search GitHub repositories, code, issues, and users via REST API.

## Endpoint

```
GET https://api.github.com/search/repositories
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | **Required.** Search query with keywords + qualifiers |
| `sort` | string | Sort by: `stars`, `forks`, `help-wanted-issues`, `updated` |
| `order` | string | `desc` (default) or `asc` |
| `per_page` | int | Results per page (max 100, default 30) |
| `page` | int | Page number for pagination |

## Query Syntax

### Keywords
Simple text search across name, description, topics, README:
```
ai agents
```

### Qualifiers

| Qualifier | Example | Description |
|-----------|---------|-------------|
| `stars:>N` | `stars:>1000` | Minimum star count |
| `stars:N..M` | `stars:100..500` | Star range |
| `language:X` | `language:python` | Primary language |
| `topic:X` | `topic:llm` | Repository topic |
| `pushed:>DATE` | `pushed:>2024-01-01` | Recently updated |
| `created:>DATE` | `created:>2023-01-01` | Created after date |
| `forks:>N` | `forks:>100` | Minimum forks |
| `user:X` | `user:openai` | Owner username |
| `org:X` | `org:langchain-ai` | Organization owner |
| `in:name` | `agent in:name` | Search in repo name |
| `in:description` | `llm in:description` | Search in description |
| `in:readme` | `agent in:readme` | Search in README |
| `license:X` | `license:mit` | License type |
| `is:public` | `is:public` | Public repos only |
| `fork:true` | `fork:true` | Include forks |
| `archived:false` | `archived:false` | Exclude archived |

### Combining Qualifiers
```
ai agents language:python stars:>100 pushed:>2024-01-01
```

## Authentication

### Without Token
- **Rate limit:** 10 requests/minute
- Good for quick one-off searches

### With Token (Recommended)
- **Rate limit:** 30 requests/minute
- Header: `Authorization: Bearer $GITHUB_TOKEN`

### Rate Limit Headers
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1706616000
```

## Example Requests

### Basic Search
```bash
curl -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=ai+agents&sort=stars&order=desc&per_page=10"
```

### Authenticated Search
```bash
curl -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/repositories?q=ai+agents+stars:>100&sort=stars&order=desc&per_page=30"
```

### Complex Query
```bash
# AI agent repos in Python with 100+ stars, updated in 2024
curl -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=ai+agents+language:python+stars:>100+pushed:>2024-01-01&sort=stars&order=desc"
```

### Topic-Based Search
```bash
curl -H "Accept: application/vnd.github+json" \
  "https://api.github.com/search/repositories?q=topic:ai-agents&sort=stars&order=desc&per_page=50"
```

## Response Structure

```json
{
  "total_count": 1234,
  "incomplete_results": false,
  "items": [
    {
      "full_name": "owner/repo-name",
      "description": "Repository description",
      "html_url": "https://github.com/owner/repo-name",
      "stargazers_count": 5000,
      "forks_count": 500,
      "language": "Python",
      "topics": ["ai", "agents", "llm"],
      "pushed_at": "2024-01-15T10:30:00Z",
      "created_at": "2023-06-01T08:00:00Z",
      "license": {
        "key": "mit",
        "name": "MIT License"
      },
      "open_issues_count": 25,
      "default_branch": "main"
    }
  ]
}
```

### Key Response Fields

| Field | Description |
|-------|-------------|
| `full_name` | `owner/repo` format |
| `description` | Repo description |
| `html_url` | GitHub web URL |
| `stargazers_count` | Star count |
| `forks_count` | Fork count |
| `language` | Primary language |
| `topics` | Array of topic tags |
| `pushed_at` | Last push timestamp |
| `created_at` | Creation timestamp |
| `license.key` | License identifier |
| `open_issues_count` | Open issues |

## Rate Limits & Constraints

| Limit | Value |
|-------|-------|
| Unauthenticated | 10 req/min |
| Authenticated | 30 req/min |
| Max results | 1,000 total |
| Max per_page | 100 |
| Query length | 256 chars (excluding operators) |
| Max operators | 5 AND/OR/NOT |

## Useful Searches for Agency OS

### AI & Automation
```bash
# AI agent frameworks
q=topic:ai-agents+stars:>100

# LLM memory systems
q=topic:llm-memory+stars:>50

# AI workflow automation
q=ai+workflow+automation+language:python+stars:>100
```

### Sales & Outreach
```bash
# Cold email tools
q=cold+email+automation+stars:>50

# Sales automation
q=sales+automation+stars:>100

# Lead generation
q=lead+generation+stars:>100
```

### Infrastructure
```bash
# Email infrastructure
q=email+warmup+OR+email+deliverability+stars:>50

# Web scraping
q=web+scraping+language:python+stars:>500
```

## Code Search Endpoint

For searching code within repos (10 req/min, auth required):

```
GET https://api.github.com/search/code?q=QUERY
```

```bash
curl -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/search/code?q=langchain+agent+in:file+language:python"
```

## Error Handling

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 304 | Not modified (cache) |
| 403 | Rate limited |
| 422 | Invalid query / validation failed |
| 503 | Service unavailable |

### Rate Limit Recovery
Check `X-RateLimit-Reset` header for Unix timestamp when limit resets.
Implement exponential backoff on 403.

## CLI One-Liner (jq)

```bash
# Get top 10 repos with name, stars, URL
curl -s "https://api.github.com/search/repositories?q=ai+agents+stars:>100&sort=stars&per_page=10" | \
  jq -r '.items[] | "\(.stargazers_count) ⭐ \(.full_name) - \(.html_url)"'
```

## Notes

- Results sorted by "best match" by default
- Only default branch searched for code
- Use `+` or `%20` for spaces in URL
- Date format: `YYYY-MM-DD` (ISO 8601)
- Topics are lowercase, hyphens for spaces
