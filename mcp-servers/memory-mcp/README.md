# Memory MCP Server

MCP server wrapping the Agency OS memory system (Supabase + pgvector) for semantic memory search.

## Overview

This MCP server provides tools to:
- **Semantic search** over memories using OpenAI embeddings
- **Save** new memories with auto-generated embeddings
- **List, filter, and manage** memories by tags, source, or time

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   Memory MCP    │────▶│    Supabase     │
│   (Claude)      │     │    Server       │     │   (pgvector)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │  OpenAI API     │
                        │  (embeddings)   │
                        └─────────────────┘
```

## Installation

```bash
cd /home/elliotbot/clawd/mcp-servers/memory-mcp

# With uv (if available)
uv sync

# Or with pip + venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Environment Variables

Required in `~/.config/agency-os/.env`:

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `DATABASE_URL_MIGRATIONS` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key for embeddings |

## Tools

### `search`
Semantic search over memories using vector similarity.

**Parameters:**
- `query` (required): Search query text
- `limit` (default: 10): Maximum results
- `min_score` (default: 0.25): Minimum similarity score (0-1)

**Example:**
```json
{"query": "how to deploy to railway", "limit": 5}
```

### `save`
Save a new memory with auto-generated embedding.

**Parameters:**
- `content` (required): Memory content
- `tags` (optional): Array of tags
- `source` (optional): Source identifier
- `metadata` (optional): Additional JSON metadata

**Example:**
```json
{
  "content": "Railway deployments use git push to deploy",
  "tags": ["railway", "deployment"],
  "source": "documentation"
}
```

### `list_recent`
List recently created memories.

**Parameters:**
- `hours` (default: 24): Look back period
- `limit` (default: 10): Maximum results

### `get_by_id`
Get a specific memory by UUID.

**Parameters:**
- `memory_id` (required): Memory UUID

### `delete`
Delete a memory by UUID.

**Parameters:**
- `memory_id` (required): Memory UUID

### `get_stats`
Get memory statistics including counts by tag, source, and recent activity.

**Parameters:** None

### `search_by_tag`
Find memories with a specific tag.

**Parameters:**
- `tag` (required): Tag to search for
- `limit` (default: 10): Maximum results

### `bulk_save`
Batch save multiple memories.

**Parameters:**
- `memories` (required): Array of memory objects with `content`, optional `tags`, `source`, `metadata`

**Example:**
```json
{
  "memories": [
    {"content": "First memory", "tags": ["test"]},
    {"content": "Second memory", "source": "import"}
  ]
}
```

## Database Schema

```sql
CREATE TABLE elliot_internal.memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  tags TEXT[],
  source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB
);

-- Vector similarity index
CREATE INDEX ON elliot_internal.memories 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

## Running

### Standalone test
```bash
cd /home/elliotbot/clawd/mcp-servers/memory-mcp
uv run python server.py
```

### MCP Configuration
Add to your MCP config:

```json
{
  "mcpServers": {
    "memory": {
      "command": "/home/elliotbot/clawd/mcp-servers/memory-mcp/.venv/bin/python",
      "args": ["/home/elliotbot/clawd/mcp-servers/memory-mcp/server.py"]
    }
  }
}
```

Or with uv:
```json
{
  "mcpServers": {
    "memory": {
      "command": "uv",
      "args": ["run", "--directory", "/home/elliotbot/clawd/mcp-servers/memory-mcp", "python", "server.py"]
    }
  }
}
```

## Technical Notes

- **Embedding model:** `text-embedding-3-small` (1536 dimensions)
- **Vector similarity:** Cosine distance via pgvector `<=>` operator
- **Default threshold:** 0.25 (25% similarity minimum)
- **Connection:** Direct PostgreSQL via psycopg2 (not Supabase REST)

## Reference

Based on existing tool: `/home/elliotbot/clawd/tools/memory_master.py`
