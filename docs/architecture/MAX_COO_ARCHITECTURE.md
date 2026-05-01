# Max COO Proxy — Architecture Spec

**Status:** APPROVED build, in flight 2026-05-01.
**Authors:** Aiden + Elliot peer-corrected via DSAE.
**Authority:** Dave directive 2026-05-01 — "Build now. Create roadmap and architecture specs. Save both then execute."

---

## Purpose

Max becomes Dave's COO **proxy** in the Agency OS supergroup. Dave exits the group; Max stands in his place. Max also runs a private DM channel with Dave for free strategic discussion. Same brain, two channels, no group-tempo lag.

This is not a digest bot. Max reads everything, relays to Dave, can speak in group as Dave's voice (under tier-gated authority), and answers Dave's DMs with full context loaded from Supabase + recent group buffer.

---

## Architecture summary

- **Single Python service** — extension of existing `agency-os-coo.service` systemd unit.
- **Two Telegram channels** — group (`-1003926592540`) and Dave's DM (`7267788033`). Single bot token (`COO_BOT_TOKEN` for `@MaxCOO_Bot`).
- **One LLM provider** — Claude Opus via `claude -p` subprocess on Dave's Anthropic Max plan (`~/.claude/credentials.json` OAuth). Cost folded into the $200/mo subscription, not per-call.
- **Shared state** — Supabase `agent_memories` (long-term), `governance_events` (real-time), `ceo_memory` (CEO state), new `coo_session_state` (Max's working memory: last-seen group msg id, recent-buffer, in-flight tasks).
- **Async parallel** — `asyncio` lets Max handle group + DM concurrently. Each `claude -p` is short-lived; smoke-test will verify parallel subprocesses don't serialise on the Max plan.

---

## Components

### 1. Group handler (`src/coo_bot/group_handler.py`)

Reads supergroup messages via `python-telegram-bot` `Application` polling. For each new message:
- Skip enforcer alerts, duplicate concurs, claim/release noise (sim-threshold filter — same pattern as `memory_listener.py`).
- Update `coo_session_state.recent_buffer` (last 50 messages).
- Decide via Opus call: `flag-to-DM` / `silent` / `auto-action-Tier-1+`.
- If flag-to-DM: DM Dave a one-line summary + verbatim quote.
- Never write to group autonomously at Tier 0.

### 2. DM handler (`src/coo_bot/dm_handler.py`)

Reads Dave's DM messages. For each:
- Load context: recent group buffer + relevant `agent_memories` (semantic + tag retrieval, hybrid Supabase+Mem0) + active directives from `ceo_memory`.
- Branch:
  - Conversational ("what's happening?", "why did Aiden do X?") → Opus call → DM reply.
  - Instruction ("post X to group", "merge PR Y") → format-check → execute (subject to Tier).
  - Kill switch ("STOP MAX") → drop Tier to 0, no group writes, ack DM.

### 3. Group writer (`src/coo_bot/group_writer.py`)

Writes to supergroup with `[MAX]` prefix when Dave instructs (Tier 0) or when pre-approved category triggers (Tier 1+). Posts have a `dave_authorized_via_dm_id` audit field written to `governance_events` so every Max group post is traceable to a Dave DM.

### 4. Tier framework (`src/coo_bot/tier_framework.py`)

- `COO_APPROVAL_TIER` env var (0-3, default 0).
- Permission gate before any group write: `can_post(action_type, current_tier) -> bool`.
- Categories at each tier:
  - Tier 0: nothing autonomous — only Dave-instructed posts.
  - Tier 1: pre-approved low-risk categories (acknowledge clone dispatch, surface gov violation flags).
  - Tier 2: routine ops (merge cleanup PRs, restart hung services).
  - Tier 3: full proxy authority (months out, criteria-gated).
- STOP MAX state file at `/home/elliotbot/clawd/state/coo_tier_override` — when present, forces Tier 0 regardless of env var.

### 5. Opus CLI subprocess wrapper (`src/coo_bot/opus_client.py`)

Replaces `openai.AsyncOpenAI` calls with:
```python
proc = await asyncio.create_subprocess_exec(
    "claude", "-p", prompt,
    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
)
stdout, stderr = await proc.communicate()
return stdout.decode()
```
- Uses Dave's existing Max plan OAuth (no API key).
- Smoke test in first hour: fire 5 parallel `claude -p` calls — measure if they serialise or run concurrently. If serialise, fall back to `claude_agent_sdk` with API key.
- Wrapped — failures return empty string, never raise.

### 6. Memory retriever (`src/coo_bot/memory_retriever.py`)

Loads relevant context for a Max query:
- `agent_memories` semantic search (Mem0 hybrid mode) — top-K=5.
- `agent_memories` tag filter — high-value types: pattern, decision, dave_confirmed, verified_fact.
- `ceo_memory` keys related to active directives.
- Recent group buffer (last 50 messages from `coo_session_state`).
Returns one assembled context block injected into the Opus prompt.

### 7. Persona (`src/coo_bot/persona.py`)

System prompt for Opus calls. Two variants:
- DM persona: "You are Max, COO of Agency OS. Reply to Dave directly. Be terse, surface specifics, propose options not consensus."
- Group post persona: "You are Max speaking on Dave's behalf. Match Dave's voice (terse, direct, decisive). Tag every post with `[MAX]` prefix."

### 8. Bidirectional relay (in `bot.py` wiring)

The orchestration that ties group handler + DM handler + group writer together. After all components land, `bot.py` is the integration point. One PR; touched last in the build sequence (avoid merge conflicts during parallel component work).

---

## File ownership map

| File | Owner | Purpose |
|------|-------|---------|
| `docs/architecture/MAX_COO_ARCHITECTURE.md` | Aiden | This doc |
| `docs/roadmap/MAX_COO_ROADMAP.md` | Elliot | Build plan |
| `src/coo_bot/opus_client.py` | Elliot direct | Subprocess wrapper |
| `src/coo_bot/group_handler.py` | ATLAS (Elliot's clone) | Group reader |
| `src/coo_bot/group_writer.py` | ATLAS | Group post on Dave's instruction |
| `src/coo_bot/dm_handler.py` | ORION (Aiden's clone) | DM listener |
| `src/coo_bot/tier_framework.py` | ORION | Tier gates + STOP MAX |
| `src/coo_bot/memory_retriever.py` | ORION | Context loader |
| `src/coo_bot/persona.py` | Aiden direct | System prompts |
| `src/coo_bot/bot.py` | Aiden direct (wiring) | Integration last |
| `tests/coo_bot/*` | Each component owner | pytest per module |
| Supabase migration `coo_session_state` | Aiden direct | new table |

---

## Tier-0 starting authority (locked at build time)

- `COO_APPROVAL_TIER=0` in `.env`.
- Max reads everything (group + ceo_memory + agent_memories + governance_events).
- Max DMs Dave proactively when `flag-to-DM` decision triggers.
- Max responds to Dave's DMs with full context.
- Max writes to group ONLY when Dave's DM contains an explicit `/post <text>` instruction (Tier 0 group writes are 1:1 dictation; Max does not paraphrase Dave's posts at Tier 0).
- STOP MAX kill switch in DM forces Tier 0 even if env var is higher.

---

## Smoke tests (must all pass before declaring complete)

- T1. `claude -p "ping"` returns within 30s (Opus reachable on Max plan).
- T2. 5 parallel `claude -p` calls — measure concurrency. PASS if all 5 finish within 2x single-call latency.
- T3. Bot reads a group test message, DM-flags Dave with verbatim quote.
- T4. Dave DM `/post "test"` → group sees `[MAX] test`. `governance_events` row records `dave_authorized_via_dm_id`.
- T5. Dave DM `STOP MAX` → state file written → next Tier-1 attempt blocked → ack DM sent.
- T6. `agent_memories` retrieval — DM "what did we decide about Mem0?" returns the relevant decision row in the response context.

---

## Non-goals (explicit OUT scope for v1)

- Phase 3 authority tiers (Tier 2/3). Long-horizon, criteria-gated.
- Anthropic API key fallback (Dave provides separately if Max plan ever rate-limits).
- Voice mimicry (matching Dave's writing style at high fidelity). Persona is good enough for v1; calibration is a follow-up.
- Auto-pickup latency below 60s polling. Polling is fine for now.
- Multi-user DMs (only Dave).

---

## Risk register

| ID | Risk | Mitigation |
|----|------|------------|
| R1 | Relay fidelity loss | Verbatim quotes in DM summaries; not paraphrased. |
| R2 | Voice impersonation drift | Tier 0 = 1:1 dictation only; persona calibration follow-up. |
| R3 | Loss of Dave's correction window | "Raw mode" DM thread option — opt-in via Dave DM `/raw on`. |
| R4 | Max goes off-rails | STOP MAX keyword → forces Tier 0 instantly. |
| R5 | Authority chain ambiguity | Every group post audit-logged with `dave_authorized_via_dm_id`. |
| R6 | Context window exhaustion | Sim-threshold filter on group reads (skip noise); recent buffer capped at 50. |
| R7 | Subprocess parallelism unverified | T2 smoke test gates declaring "parallel works." Fallback: `claude_agent_sdk` + Anthropic API key. |
