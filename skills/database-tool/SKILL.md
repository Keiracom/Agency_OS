---
name: database-tool
description: Unified database interface - Supabase/Postgres queries, Redis cache operations.
metadata:
  clawdbot:
    emoji: "🗄️"
schema:
  type: object
  required: ["action", "target"]
  properties:
    action:
      type: string
      enum: ["query", "tables", "describe", "get", "set", "keys"]
    target:
      type: string
      enum: ["supabase", "postgres", "redis"]
---

# Database Tool 🗄️

Unified database interface.

## Usage

```bash
python3 tools/database_master.py <action> <target> [options]
```

## Examples

```bash
# List tables
python3 tools/database_master.py tables supabase

# Describe table
python3 tools/database_master.py describe supabase --table "public.users"

# Run query
python3 tools/database_master.py query postgres --sql "SELECT COUNT(*) FROM users"

# Redis get/set
python3 tools/database_master.py get redis --key "session:123"
python3 tools/database_master.py set redis --key "cache:data" --value '{"foo":"bar"}'
```

## Replaces

- supabase, postgres, redis
