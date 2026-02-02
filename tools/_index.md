# Tools Index

Quick reference for available Python tools. Run with `python3 tools/<name>.py`.

## Core Tools

| Tool | Purpose | Usage |
|------|---------|-------|
| `memory_master` | Semantic memory search/save | `search "<query>"`, `save "<content>" --type <type>`, `stats`, `audit` |
| `autonomous_browser` | Stealth web scraping (215k proxies) | `fetch "<url>"` |
| `proxy_manager` | Manage proxy rotation | `sync`, `verify`, `test` |

## Domain Masters

| Tool | Purpose |
|------|---------|
| `agency_master` | Agency OS operations |
| `content_master` | YouTube, RSS, arXiv content |
| `database_master` | Supabase/Postgres, Redis |
| `enrichment_master` | Apollo leads, Apify scraping |
| `infra_master` | Prefect workflows, Railway |
| `social_master` | Twitter, Reddit, HN, Dev.to |

## Utilities

| Tool | Purpose |
|------|---------|
| `behavior_cache` | Cache API/browser behaviors |
| `embed_memories` | Generate embeddings for memories |
| `ingest_all` | Bulk ingest files to memory |
| `query_memory` | Simple memory queries |

## When to Use What

- **Need to remember something?** → `memory_master save`
- **Need to recall something?** → `memory_master search`
- **Need web data?** → `autonomous_browser` (NEVER raw requests)
- **Need lead data?** → `enrichment_master` (costs money - ask first)
- **Need social signals?** → `social_master`
