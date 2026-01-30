---
name: mid-session-check
description: "Injects checkpoint reminder before every message is processed"
metadata: {"clawdbot":{"emoji":"🔄","events":["message_received"]}}
---

# Mid-Session Check Hook

Fires before EVERY message is processed, not just session start.
Injects a tiny checkpoint (~20 tokens) to keep Elliot on track.

## What It Does

1. Fires on `message_received` event
2. Injects minimal checkpoint reminder
3. Keeps token cost flat (~20 tokens per message)

## Why This Exists

Elliot forgets SOUL principles mid-session. This hook enforces checking before every response.
