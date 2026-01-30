# ArXiv API Skill

Search and retrieve academic papers from ArXiv's open-access repository.

## Endpoint

```
GET http://export.arxiv.org/api/query
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_query` | string | None | Search query string |
| `id_list` | comma-delimited | None | Specific arXiv IDs to retrieve |
| `start` | int | 0 | Index of first result (0-based) |
| `max_results` | int | 10 | Number of results (max 2000 per request, 30000 total) |
| `sortBy` | string | relevance | `relevance`, `lastUpdatedDate`, `submittedDate` |
| `sortOrder` | string | descending | `ascending`, `descending` |

## Search Query Syntax

### Field Prefixes

| Prefix | Field | Example |
|--------|-------|---------|
| `all:` | All fields | `all:transformer` |
| `ti:` | Title | `ti:attention mechanism` |
| `abs:` | Abstract | `abs:multi-agent` |
| `au:` | Author | `au:bengio` |
| `cat:` | Category | `cat:cs.AI` |
| `co:` | Comment | `co:accepted` |
| `jr:` | Journal ref | `jr:nature` |
| `rn:` | Report number | `rn:CERN` |

### Boolean Operators

- `AND` - Both terms required
- `OR` - Either term
- `ANDNOT` - Exclude term

**URL encoding:** Spaces → `+`, operators stay uppercase

### Examples

```bash
# LLM papers in AI category, newest first
search_query=all:LLM+AND+cat:cs.AI&sortBy=submittedDate&sortOrder=descending

# Multi-agent papers excluding robotics
search_query=all:multi-agent+ANDNOT+all:robotics

# Papers by specific author on transformers
search_query=au:vaswani+AND+ti:transformer

# Combine multiple categories
search_query=(cat:cs.AI+OR+cat:cs.CL)+AND+all:agents
```

## Relevant Categories

| Category | Name | Use For |
|----------|------|---------|
| `cs.AI` | Artificial Intelligence | AI agents, reasoning, planning |
| `cs.CL` | Computation and Language | NLP, LLMs, text generation |
| `cs.LG` | Machine Learning | ML methods, neural networks |
| `cs.MA` | Multi-Agent Systems | Agent coordination, swarms |
| `cs.HC` | Human-Computer Interaction | Interfaces, UX |
| `cs.SE` | Software Engineering | Code generation, dev tools |

## Response Format (Atom XML)

```xml
<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <opensearch:totalResults>1000</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>10</opensearch:itemsPerPage>
  
  <entry>
    <id>http://arxiv.org/abs/2401.12345v1</id>
    <title>Paper Title Here</title>
    <summary>Abstract text...</summary>
    <published>2024-01-15T00:00:00Z</published>
    <updated>2024-01-16T00:00:00Z</updated>
    <author><name>Author Name</name></author>
    <author><name>Second Author</name></author>
    <link href="http://arxiv.org/abs/2401.12345v1" rel="alternate"/>
    <link href="http://arxiv.org/pdf/2401.12345v1" rel="related" title="pdf"/>
    <arxiv:primary_category term="cs.AI"/>
    <category term="cs.AI"/>
    <category term="cs.CL"/>
  </entry>
</feed>
```

### Key Entry Fields

| Field | Description |
|-------|-------------|
| `entry.id` | ArXiv URL (extract ID: remove `http://arxiv.org/abs/`) |
| `entry.title` | Paper title |
| `entry.summary` | Abstract |
| `entry.published` | First submission date |
| `entry.updated` | Latest version date |
| `entry.author.name` | Author names (multiple) |
| `entry.link[@rel='alternate']` | Abstract page URL |
| `entry.link[@title='pdf']` | PDF URL |
| `arxiv:primary_category` | Main category |

## Rate Limits

⚠️ **IMPORTANT: 1 request per 3 seconds minimum**

- Be a good citizen - ArXiv is a free academic resource
- Cache results - they only update once daily at midnight
- Max 2000 results per request, 30000 total per query
- Large requests (>1000 results) strain the server

## Code Examples

### Python (feedparser)

```python
import feedparser
import time

def search_arxiv(query, max_results=50, sort_by="submittedDate"):
    """Search ArXiv and return parsed entries."""
    base_url = "http://export.arxiv.org/api/query"
    url = f"{base_url}?search_query={query}&max_results={max_results}&sortBy={sort_by}&sortOrder=descending"
    
    feed = feedparser.parse(url)
    
    papers = []
    for entry in feed.entries:
        papers.append({
            "id": entry.id.split("/abs/")[-1],
            "title": entry.title.replace("\n", " "),
            "summary": entry.summary.replace("\n", " "),
            "authors": [a.name for a in entry.authors],
            "published": entry.published,
            "pdf_url": f"http://arxiv.org/pdf/{entry.id.split('/abs/')[-1]}.pdf",
            "categories": [t.term for t in entry.tags],
        })
    
    return papers

# Search for LLM agent papers
papers = search_arxiv("all:LLM+agent+AND+cat:cs.AI", max_results=20)
for p in papers:
    print(f"{p['title']}\n  {p['pdf_url']}\n")
```

### Python (with paging)

```python
import feedparser
import time

def search_arxiv_all(query, max_total=100):
    """Fetch all results with paging and rate limiting."""
    base_url = "http://export.arxiv.org/api/query"
    results = []
    start = 0
    chunk_size = 100
    
    while start < max_total:
        url = f"{base_url}?search_query={query}&start={start}&max_results={chunk_size}"
        feed = feedparser.parse(url)
        
        if not feed.entries:
            break
            
        results.extend(feed.entries)
        start += chunk_size
        
        # Respect rate limit
        time.sleep(3)
    
    return results[:max_total]
```

### Bash (curl + quick parse)

```bash
# Fetch latest AI agent papers
curl -s "http://export.arxiv.org/api/query?search_query=all:AI+agent+AND+cat:cs.AI&max_results=10&sortBy=submittedDate&sortOrder=descending" \
  | grep -oP '(?<=<title>).*?(?=</title>)' \
  | tail -n +2  # Skip feed title

# Get PDF links
curl -s "http://export.arxiv.org/api/query?search_query=ti:transformer&max_results=5" \
  | grep -oP 'http://arxiv.org/pdf/[^"<]+'
```

## Common Queries for Our Use Cases

```bash
# AI Agents & Autonomous Systems
search_query=all:AI+agent+AND+(cat:cs.AI+OR+cat:cs.MA)

# LLM-based Agents
search_query=(all:LLM+agent+OR+all:language+model+agent)+AND+cat:cs.CL

# Tool Use / Function Calling
search_query=all:tool+use+AND+all:language+model

# Memory in AI Systems
search_query=(ti:memory+OR+abs:memory)+AND+all:agent+AND+cat:cs.AI

# Multi-Agent Coordination
search_query=all:multi-agent+AND+(all:coordination+OR+all:collaboration)

# Code Generation
search_query=all:code+generation+AND+cat:cs.SE

# Retrieval-Augmented Generation
search_query=all:RAG+OR+all:retrieval+augmented+generation
```

## Retrieving Specific Papers

Use `id_list` to fetch known papers:

```bash
# Single paper
http://export.arxiv.org/api/query?id_list=2401.12345

# Multiple papers
http://export.arxiv.org/api/query?id_list=2401.12345,2401.67890,2312.11111

# Filter specific IDs by search
http://export.arxiv.org/api/query?search_query=cat:cs.AI&id_list=2401.12345,2401.67890
```

## Notes

- Results update daily at midnight (ET) - no need to poll more frequently
- Version suffix (v1, v2) in ID indicates paper version
- Primary category in `arxiv:primary_category`, all categories in `category` tags
- Abstract pages: `http://arxiv.org/abs/{id}`
- PDF direct: `http://arxiv.org/pdf/{id}.pdf`
