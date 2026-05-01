# Max COO Proxy — Build Roadmap
Ratified: 2026-05-01. Dave directive: "Build now. Create roadmap and architecture specs."

## Overview
Max (@MaxCOO_Bot) becomes Dave's proxy in the Agency OS supergroup. Dave exits group, communicates through Max via DM only. Max reads group in real-time, relays to Dave, posts to group on Dave's behalf, and (at higher Tiers) interjects independently.

## Phase A — Foundation (serial, ~2hr)

### A1. Architecture Spec
- File: docs/architecture/MAX_COO_ARCHITECTURE.md
- Owner: Aiden (architect-0 dispatch)
- Deliverable: component contracts, Tier model, CLI subprocess spec, file ownership map

### A2. Opus CLI Subprocess Wrapper
- File: src/coo_bot/opus_client.py (new)
- Owner: Elliot
- Deliverable: async wrapper around `claude -p` subprocess, timeout handling, error capture
- Test: smoke test parallel calls, verify 5-15s response, no queue
- Replaces: openai.AsyncOpenAI client in bot.py

### A3. Group Message Handler
- File: src/coo_bot/group_handler.py (new)
- Owner: Aiden
- Deliverable: reads supergroup messages via python-telegram-bot, updates working state buffer, decides flag-to-DM
- Test: mock group messages, verify state buffer updates

### A4. DM Bidirectional Handler
- File: src/coo_bot/dm_handler.py (new)
- Owner: Elliot
- Deliverable: receives Dave DMs, loads memory context, calls Opus, responds. Receives /post commands, routes to group writer.
- Test: mock DM conversation, verify context loading + response

## Phase B — Parallel Components (clone dispatch, ~1hr)

### B1. Tier Framework + Kill Switch
- File: src/coo_bot/tier_framework.py (new)
- Owner: ORION (Aiden's clone)
- Deliverable: COO_APPROVAL_TIER env var (0/1/2/3), permission checks per action type, STOP MAX keyword detection
- Test: unit tests for each tier gate

### B2. Memory Retrieval Layer
- File: src/coo_bot/memory_retriever.py (new)
- Owner: ATLAS (Elliot's clone)
- Deliverable: load relevant agent_memories for a query (semantic + tag filter), format as context for Opus prompt
- Test: mock Supabase, verify context formatting

### B3. Group Post Writer
- File: src/coo_bot/group_writer.py (new)
- Owner: Aiden
- Deliverable: posts to group with [MAX] prefix when authorised by Tier check
- Test: mock Telegram sendMessage, verify prefix + Tier gate

### B4. Persona Prompt
- File: src/coo_bot/persona.py (new)
- Owner: Elliot
- Deliverable: system prompt for Max's COO voice, loaded from Dave's historical post patterns
- Test: prompt renders correctly with context injection

## Phase C — Integration (sequential, ~1hr)

### C1. Wire bot.py
- Owner: Elliot (bot.py is his file)
- Deliverable: register group_handler + dm_handler + group_writer in Application, wire Opus client
- Test: full integration — mock group msg → DM arrives; mock Dave DM /post → group post fires

### C2. Smoke Test
- Owner: Both (joint verification)
- Deliverable: real Telegram test — group message → Max DMs Dave; Dave DMs Max → Max posts to group
- Gate: parallel subprocess calls work without blocking

## Success Criteria
1. Max reads group messages in real-time → DMs Dave summaries/flags
2. Dave DMs Max instructions → Max posts to group with [MAX] prefix
3. Tier 0: Max NEVER auto-posts to group without Dave's DM instruction
4. STOP MAX keyword → Max drops to relay-only immediately
5. Opus subprocess calls complete in <15s, parallel without blocking
6. All components have pytest coverage

## Timeline
- Phase A: ~2hr (serial, foundation)
- Phase B: ~1hr (parallel clone dispatch)
- Phase C: ~1hr (integration + smoke)
- Total: ~4hr wall-clock

## Deferred (not in this build)
- Tier 1+ auto-post categories
- Event-driven flagging (replace time-based digest)
- Dave-voice persona training from historical posts
- Anthropic SDK migration (if subprocess bottlenecks)
