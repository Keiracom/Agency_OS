---
name: memory-db
description: Search Elliot's long-term vector memory database for facts, preferences, decisions, and past learnings. Use when you need to recall something from previous sessions.
metadata: {"clawdbot":{"emoji":"🧠","always":false,"requires":{"bins":["python3"],"env":["OPENAI_API_KEY","DATABASE_URL"]}}}
---

# Memory Database Search 🧠

Vector-powered semantic search over Elliot's persistent memory.

## Usage

```bash
python3 tools/query_memory.py "<natural language query>"
```

## Examples

```bash
# Find project focus
python3 tools/query_memory.py "What is the project focus?"

# Recall a decision
python3 tools/query_memory.py "What did we decide about the dashboard?"

# Find user preferences
python3 tools/query_memory.py "What does Dave prefer for communication?"

# Search for learnings
python3 tools/query_memory.py "What lessons about AI agents?"
```

## When to Use

- Recalling facts from previous conversations
- Finding past decisions and their rationale
- Searching for user preferences
- Looking up project context
- Retrieving learned patterns

## Output Format

Returns top 5 matches with:
- Match percentage (similarity score)
- Memory type (core_fact, daily_log, etc.)
- Section/source
- Content preview

## Technical Details

- Model: `text-embedding-3-small` (OpenAI)
- Dimensions: 1536
- Database: `elliot_internal.memories` (Supabase)
- Threshold: 0.25 (low, for recall)
