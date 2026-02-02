---
name: memory-tool
description: "⚠️ CRITICAL - Your brain. Semantic search over long-term memory, save new memories, audit memory health. Uses Supabase vector database."
metadata:
  clawdbot:
    emoji: "🧠"
    always: true
    requires:
      bins: ["python3"]
      env: ["OPENAI_API_KEY", "DATABASE_URL"]
schema:
  type: object
  required: ["action"]
  properties:
    action:
      type: string
      enum: ["search", "save", "list", "stats", "audit"]
    query:
      type: string
      description: "Search query or content to save"
    type:
      type: string
      enum: ["core_fact", "rule", "daily_log", "knowledge_base", "general"]
      description: "Memory type filter"
    limit:
      type: integer
      default: 5
---

# Memory Tool 🧠

⚠️ **CRITICAL TOOL** - This is your brain.

## Usage

```bash
python3 tools/memory_master.py <action> [query] [options]
```

## Actions

| Action | Description |
|--------|-------------|
| `search` | Semantic vector search over memories |
| `save` | Store new memory with embedding |
| `list` | List recent memories by type |
| `stats` | Show memory statistics |
| `audit` | Check memory system health |

## Examples

### Search (Most Common)
```bash
python3 tools/memory_master.py search "project focus"
python3 tools/memory_master.py search "deployment rules" --type rule
python3 tools/memory_master.py search "what did we decide about X"
```

### Save New Memory
```bash
python3 tools/memory_master.py save "Important decision: We chose X because Y" --type core_fact
```

### Stats & Audit
```bash
python3 tools/memory_master.py stats
python3 tools/memory_master.py audit
```

## Memory Types

| Type | Purpose |
|------|---------|
| `core_fact` | Permanent knowledge (from MEMORY.md) |
| `rule` | Operational constraints (from RULES.md) |
| `daily_log` | Session logs |
| `knowledge_base` | Ingested documentation |
| `general` | Default for new memories |

## Database

- Location: `elliot_internal.memories` (Supabase)
- Model: `text-embedding-3-small` (1536 dimensions)
- Threshold: 0.25 similarity

## Replaces

- memory-db, elliot-memory, memory-hygiene, second-brain
