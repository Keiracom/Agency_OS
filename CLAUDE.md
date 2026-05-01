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
| LAW XII | Skills-First Integration — direct calls to src/integrations/ outside skill execution are forbidden |
| LAW XIII | Skill Currency Enforcement — skill files must be updated in the same PR as any service call change; update noted in Manual |
| LAW XIV | Raw Output Mandate — paste verbatim terminal output, never summarise |
| LAW XV | Four-Store Completion — docs/MANUAL.md + ceo_memory + cis_directive_metrics + Google Drive mirror |
| LAW XV-A | Skills Are Mandatory — cat skill file before any matching task |
| LAW XV-B | DoD Is Mandatory — cat DEFINITION_OF_DONE.md before reporting complete |
| LAW XV-C | Governance Docs Immutable — never recreate/modify without explicit CEO directive |
| LAW XV-D | Step 0 RESTATE — mandatory restate before any directive execution, no exceptions |
| GOV-8 | Maximum Extraction Per Call — every API response captured in full, written to BU regardless of card eligibility, never re-fetched if prior stage received it |
| GOV-9 | Two-Layer Directive Scrutiny — every directive triggers Layer 2 CTO scrutiny before Step 0. Report DIRECTIVE SCRUTINY — N GAPS FOUND or CLEAR before any execution |
| GOV-10 | Resolve-Now-Not-Later — fix bounded gaps in current PR, not follow-up directives |
| GOV-11 | Structural Audit Before Validation — stage audit within 7 days before any N>=20 validation run |

> **Shared governance:** laws that apply to every callsign (e.g. LAW XVII — Callsign Discipline, Directive Acknowledgement, Claim-Before-Touch on Shared Files) live in `~/.claude/CLAUDE.md §Shared Governance Laws`. Treat that as authoritative for all-callsign rules; worktree laws above are Agency_OS-main specific.
| GOV-12 | Gates As Code Not Comments — runtime enforcement required, not documentation-only |

## Directive + Validation Governance

### GOV-9 — Directive Scrutiny (MANDATORY)

Every directive received triggers Layer 2 scrutiny pass before Step 0. Scrutinise for: missing capabilities, missing config, missing instrumentation, contradicted assumptions, recently-merged code that changes the path. Report gaps as `DIRECTIVE SCRUTINY — N GAPS FOUND` with gap list, or `DIRECTIVE SCRUTINY — CLEAR` before proceeding to Step 0 RESTATE. This is mandatory regardless of how thorough the CEO's Layer 1 drafting was.

### GOV-11 — Structural Audit Before Validation (MANDATORY)

Before any cohort run intended to validate pipeline behavior at scale (N>=20 domains, intended to inform ship/no-ship decision), a structural stage audit must complete in the prior 7 days. Audit covers: data flow gaps, GOV-8 violations, dead code paths, gate enforcement vs documentation, unfilled template tokens, cascade failure risk per stage. No validation run without recent audit on file.

### GOV-12 — Gates As Code (MANDATORY)

Any gate specified in a directive must be runtime enforcement. Reports of "gate added" require evidence of executable conditional, not comment block. Gates as comments create false confidence.

> **Shared governance:** laws that apply to every callsign (e.g. LAW XVII — Callsign Discipline, Directive Acknowledgement, Claim-Before-Touch on Shared Files) live in `~/.claude/CLAUDE.md §Shared Governance Laws`. Treat that as authoritative for all-callsign rules.

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
