# CLAUDE.md — Agency OS Project Config

## Project: Agency OS

Keiracom's outbound sales automation platform. Discovers Australian SMBs via Google Maps, enriches contact data through a multi-tier waterfall, scores leads with a Competitive Intelligence Score (CIS), and executes personalised outreach campaigns.

**Repo:** /home/elliotbot/clawd/Agency_OS
**Stack:** Python (FastAPI), Next.js (frontend), Supabase (Postgres + auth), Railway (compute), Prefect (orchestration), Redis (queue)
**Env:** /home/elliotbot/.config/agency-os/.env

## Architecture First (LAW I-A — HARD BLOCK)

Before ANY architectural decision, code change, or sub-agent task brief:
1. cat ARCHITECTURE.md from repo root (head -10 minimum, full file when relevant)
2. Query ceo_memory via MCP bridge for current system state
3. Never answer architectural questions from training data

If ARCHITECTURE.md is missing: STOP. Report to Dave. Do not recreate it. Wait.

## MCP Bridge

All external service calls go through MCP bridge:

```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js call <server> <tool> [args_json]
```

Available servers: supabase, redis, prefect, railway, prospeo, dataforseo, vercel, salesforge, vapi, telnyx, unipile, resend, memory

**Decision tree (LAW VI):**
1. Skill exists in skills/ -> use the skill
2. No skill, MCP available -> use MCP bridge
3. No skill, no MCP -> use exec as last resort, then write a skill

Never call external services ad-hoc. No credential hunting.

## Supabase — Primary Memory Store (LAW IX)

**Project ID:** jatzvazlbusedwsnqxzr

Session START query:
```sql
SELECT type, LEFT(content, 200) as preview, created_at::date as date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

Session END — write daily_log before closing:
```sql
INSERT INTO elliot_internal.memories (id, type, content, metadata, created_at)
VALUES (gen_random_uuid(), 'daily_log', '<summary: what was done, PRs, decisions, blockers>', '{}'::jsonb, NOW());
```

## Governance Laws (Active)

| Law | Rule |
|-----|------|
| LAW I-A | Architecture First — cat ARCHITECTURE.md before any code decision |
| LAW II | Australia First — all financial outputs in $AUD (1 USD = 1.55 AUD) |
| LAW III | Justification Required — Governance Trace on every decision |
| LAW IV | Non-Coder Bridge — no code blocks >20 lines without Conceptual Summary |
| LAW V | 50-Line Protection — if task requires >50 lines, spawn sub-agent |
| LAW VI | Skills-First Operations — use skill -> MCP -> exec hierarchy |
| LAW VII | Timeout Protection — use async patterns for >60s tasks |
| LAW VIII | GitHub Visibility — all work pushed before reporting complete |
| LAW IX | Session Memory — Supabase is SOLE persistent memory |
| LAW XI | Orchestrate — Elliottbot delegates, never executes task work directly |
| LAW XIV | Raw Output Mandate — paste verbatim terminal output, never summarise |
| LAW XV | Three-Store Completion — docs/MANUAL.md + ceo_memory + cis_directive_metrics |
| LAW XV-A | Skills Are Mandatory — cat skill file before any matching task |
| LAW XV-B | DoD Is Mandatory — cat DEFINITION_OF_DONE.md before reporting complete |
| LAW XV-C | Governance Docs Immutable — never recreate/modify without explicit CEO directive |

## Dead References (Do Not Use)

| Dead | Replacement |
|------|-------------|
| Proxycurl | Bright Data LinkedIn Profile (gd_l1viktl72bvl7bjuj0) |
| Apollo (enrichment) | Waterfall Tiers 1-5 |
| Apify | Bright Data GMB Web Scraper (gd_m8ebnr0q2qlklc02fz) |
| SDK agents (enrichment/email/voice_kb) | Smart Prompts + sdk_brain.py |
| MEMORY.md (new writes) | Supabase elliot_internal.memories |
| HANDOFF.md (new writes) | Supabase elliot_internal.memories |
| HunterIO (email verify) | Leadmagic ($0.015/email) |
| Kaspr | Leadmagic mobile ($0.077) |
| ABNFirstDiscovery | MapsFirstDiscovery (Waterfall v3) |

## Active Enrichment Path

T0 GMB -> T1 ABN -> T1.5a SERP Maps -> T1.5b SERP LinkedIn -> T2 LinkedIn Company -> ALS gate (>=20) -> T2.5 LinkedIn People -> T3 Leadmagic Email -> T5 Leadmagic Mobile

**Decision-maker path:** T-DM0 DataForSEO ($0.0465) -> T-DM1 BD Profile ($0.0015) -> T-DM2/2b/3/4 (Propensity >=70)

**ALS gates:** PRE_ALS_GATE = 20 | HOT_THRESHOLD = 85

## Directive Format

```
Directive #NNN — [Title]
Scope: [files/systems]
Success: [criteria]
Agent: [which agent]
```

## Session End Protocol

Before context exhaustion or /reset:
1. Write CEO Memory Update to ceo_memory (key: ceo:session_end_YYYY-MM-DD)
2. Update directive counter (ceo:directives.last_number)
3. Write daily_log to elliot_internal.memories
4. Report completion with directive number and PR links

**Context thresholds:** 40% -> self-alert | 50% -> alert Dave | 60% -> execute session end protocol
