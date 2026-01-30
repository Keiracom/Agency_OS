---
name: knowledge-inject
description: "Auto-injects relevant tools and knowledge before every session based on context"
metadata: {"clawdbot":{"emoji":"🧠","events":["agent:bootstrap"]}}
---

# Knowledge Inject Hook

Automatically queries the knowledge system and injects relevant tools/capabilities before Elliot processes any message.

## What It Does

1. Fires on `agent:bootstrap` (before context injection)
2. Reads recent conversation context
3. Queries Supabase `elliot_knowledge` for relevant tools
4. Injects matching tools into `context.bootstrapFiles`

## Why This Exists

Elliot has a tendency to forget learned tools mid-session. This hook enforces checking the knowledge base automatically — no self-discipline required.

## Requirements

- Supabase credentials in environment
- `elliot_knowledge` table populated
