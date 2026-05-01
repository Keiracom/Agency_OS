# CLAUDE.md — Agency OS Project Config

## Project: Agency OS

Keiracom's outbound sales automation platform. Discovers Australian SMBs via Google Maps, enriches contact data through a multi-tier waterfall, scores leads with a Competitive Intelligence Score (CIS), and executes personalised outreach campaigns.

**Repo:** /home/elliotbot/clawd/Agency_OS
**Stack:** Python (FastAPI), Next.js (frontend), Supabase (Postgres + auth), Railway (compute), Prefect (orchestration), Redis (queue)
**Env:** /home/elliotbot/.config/agency-os/.env

## MANDATORY STEP 0 RESTATE ON EVERY DIRECTIVE (LAW XV-D — HARD BLOCK)

Before any tool call, before any planning, before any execution, output Step 0 RESTATE in this format:

- **Objective:** [one line — what we're doing]
- **Scope:** [what's in, what's out]
- **Success criteria:** [how we know it worked]
- **Assumptions:** [what you are assuming]

Wait for Dave to confirm. Then proceed with Decompose → Present → Execute → Verify → Report.

Skipping Step 0 is a governance violation. No exceptions, no shortcuts, no jumping ahead because the task seems simple. Every directive, every time.

## Session Start — Read the Manual First (HARD BLOCK)

On every new session, your FIRST action before any directive, query, or build work:

0. Read `./IDENTITY.md` first — your callsign is the single source of truth for this session (LAW XVII). Verify CALLSIGN env var matches if set.
1. Read the Agency OS Manual from Google Drive (Doc ID: `1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho`). This is the CEO SSOT — current state, active directives, blockers, and system status.
2. Do not work from memory. Do not work from stale docs. Read the Manual before any directive.
3. If the Manual is unreachable, alert Dave and STOP. Do not proceed from cached knowledge.
4. **Telegram verification (HARD BLOCK):** Read the §Group Chat Plumbing section below. Verify `tg -g "test"` works. Your FIRST outbound message to Dave MUST go via `tg -g`, not terminal output. If `tg` fails, fix it before proceeding — Dave reads Telegram, not your terminal. All communication with Dave and peers happens via the Telegram group (chat_id `-1003926592540`), never terminal-only.
5. **READ RECENT GROUP CHAT ON RESET (HARD BLOCK):** Pull the last ~30 messages or last 24 hours of the Telegram supergroup before acting on any directive. The Manual + ceo_memory capture ratified state but miss in-flight conversation — Dave approvals given in the last 10 minutes, peer corrections, dispatch announcements may NOT be in ceo_memory yet. Read from the listener log at `/tmp/telegram-relay-<callsign>/` or via Telegram getUpdates API. If the most recent messages reference a pending decision or approval, that state is ACTIVE — do NOT re-ask Dave for something visible in recent chat history.
6. **CLONE AWARENESS (HARD BLOCK):** Check for active clone sessions (ATLAS, ORION, SCOUT) via `tmux list-sessions` and inbox/outbox watchers. Clones may have in-flight work dispatched before your reset. Read any pending outbox messages from clones before proceeding. You are not working alone — your clone assistant may already be executing directives.

This overrides all other startup steps. The Manual is ground truth.

## Clean Working Tree (LAW XVI — HARD BLOCK)

Before any new directive work, run `git status`. If the working tree has uncommitted modifications from a previous session, STOP and report them to Dave. Do not include them in new commits via `git add -A`. Either commit them as their own atomic change (after Dave confirms what they are) or stash them. Never sweep unknown changes into unrelated PRs.

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
SELECT source_type AS type, LEFT(content, 200) AS preview, created_at::date AS date
FROM public.agent_memories
WHERE callsign = 'elliot' AND state != 'archived'
  AND source_type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

Session END — write daily_log before closing:
```sql
INSERT INTO public.agent_memories (id, callsign, source_type, content, typed_metadata, created_at, valid_from, state)
VALUES (gen_random_uuid(), 'elliot', 'daily_log', '<summary: what was done, PRs, decisions, blockers>', '{}'::jsonb, NOW(), NOW(), 'confirmed');
```

## Governance — 7 Consolidated Rules (Ratified 2026-05-01)

**Canonical document:** `docs/governance/CONSOLIDATED_RULES.md`

| # | Rule | Principle |
|---|------|-----------|
| 1 | VERIFY | Truth over speed — run verification before claiming done |
| 2 | COORDINATE | No overlap, no surprise — claim before touch, peer before dispatch |
| 3 | APPROVE | Two checkpoints only — queue approval + merge approval |
| 4 | ORCHESTRATE | Delegate, don't execute — sub-agents build, bots verify |
| 5 | COMMUNICATE | Right channel, right density — TG group, concise, always propose |
| 6 | GOVERN | Rules are code, not comments — runtime enforcement required |
| 7 | BUSINESS | Australia-first, pre-revenue honest — $AUD, no fake social proof |

> **Full rule text** (triggers, satisfied-by, violations, absorbs): read `docs/governance/CONSOLIDATED_RULES.md`.
> **Shared governance** (all callsigns): `~/.claude/CLAUDE.md §Shared Governance Laws`.
> **Infrastructure procedures:** separate operational doc (not governance).
> **Dead References:** see ARCHITECTURE.md.

## Dead References (Do Not Use)

| Dead | Replacement |
|------|-------------|
| Proxycurl | Bright Data LinkedIn Profile (gd_l1viktl72bvl7bjuj0) |
| Apollo (enrichment) | Waterfall Tiers 1-5 |
| Apify (GMB scraping) | Bright Data GMB Web Scraper (gd_m8ebnr0q2qlklc02fz). EXCEPTION: Apify harvestapi/linkedin-profile-scraper active in Pipeline F v2.1 for L2 LinkedIn verification. Apify facebook-posts-scraper active for Stage 9 social. |
| SDK agents (enrichment/email/voice_kb) | Smart Prompts + sdk_brain.py |
| MEMORY.md (new writes) | Supabase elliot_internal.memories |
| HANDOFF.md (new writes) | Supabase elliot_internal.memories |
| HunterIO (email verify) | Leadmagic ($0.015/email). EXCEPTION: Hunter email-finder active in Pipeline F v2.1 as L2 email fallback (score >= 70). |
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
1. Run session-end 3-store check: `python scripts/session_end_check.py` — fix any gaps before proceeding
2. Write CEO Memory Update to public.ceo_memory (key: ceo:session_end_YYYY-MM-DD)
3. Update directive counter in public.ceo_memory (ceo:directives.last_number)
4. Write daily_log to elliot_internal.memories
5. Report completion with directive number and PR links

**Context thresholds:** 40% -> self-alert | 50% -> alert Dave | 60% -> execute session end protocol
