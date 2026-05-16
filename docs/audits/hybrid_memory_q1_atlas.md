# Hybrid Memory Audit — Q1 Atlas Deep Dive
**Vultr filesystem inventory of agent-written data sources Dave cannot see**

- Author: ATLAS
- Date: 2026-05-16
- Dispatch: Elliot CEO Research Mandate, Q1-deeper
- Scope: this host (`agency-os.keiracom.com`) filesystem only. Out-of-scope: Supabase (Aiden Q2), Weaviate object content (Max Q4), staleness (Orion Q3).
- Status: research artefact — no data moves until ingestion plan ratified.

---

## TL;DR — material data sources outside Dave's view

| Location | Size | Category | Ingest-worthy for hybrid memory? |
|---|---|---|---|
| `/home/elliotbot/.claude/projects/.../*.jsonl` (Claude session transcripts) | **170MB+ across ~35 sessions** | canonical reasoning chains | YES — highest-signal corpus; but raw → too noisy without distillation |
| `/home/elliotbot/.claude/projects/.../memory/*.md` (84 feedback/reference notes) | 368KB, 2008 lines | canonical agent learnings | YES — already canonicalised; should be Tier-1 ingest |
| `/home/elliotbot/clawd/cognee_data/cognee_db` (SQLite, ~215MB) | 215MB | partial knowledge graph (KEI-44 era) | PARTIAL — likely overlap with Weaviate; check before ingest |
| `/home/elliotbot/clawd/weaviate-data/` | 1.1MB | target system | N/A — this IS the destination |
| `/home/elliotbot/clawd/.beads/issues.jsonl` (across 6 worktrees) | 26MB main + ~220KB clones | canonical task graph | YES for closed/Done issues; NO for ephemeral state |
| `/home/elliotbot/clawd/logs/*` | **248MB** | ephemeral operational logs | NO — telegram/slack chatter, telemetry, costs. Pure noise for code agent. |
| `/tmp/telegram-relay-*/` (7802 files) | ~6MB | ephemeral relay state | NO — inbox/outbox already-consumed dispatch envelopes |
| `/home/elliotbot/clawd/Agency_OS-*/docs/` | varies per worktree | canonical project docs | YES for `governance/`, `architecture/`, `audits/`; SAMPLE for older audits |
| `/home/elliotbot/clawd/skills/` (26 skills + SKILL_INDEX.md) | varies | canonical skill specs | YES — Tier-1 ingest, agents read these before external calls (LAW VI) |
| `/home/elliotbot/clawd/Agency_OS-*/.claude/{agents,modules,skills,commands}/` | varies | canonical Claude-Code per-worktree config | YES for `modules/` (auto-loaded); agents/* are sub-agent specs |

---

## 1. Claude Code session state (highest signal, currently invisible)

### `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/`

- 35+ UUID-named session pairs (`.jsonl` transcript + per-session subdir).
- Largest sessions (raw transcript bytes):
  - `4cc9d4d3-...jsonl` — **43MB**
  - `1561a09a-...jsonl` — **22MB**
  - `e8133640-...jsonl` — 9.3MB
  - `f85e338e-...jsonl` — 12MB
  - `3546b03e-...jsonl` — 12MB
- Total project transcript bytes: ~170MB across all sessions
- Content: full Claude Code conversation logs (user prompts, assistant turns, tool calls, results). Includes raw stdout from `bd ready`, `git diff`, `pytest`, every Step 0 RESTATE, every dispatch, every failure and recovery.

**Implication for hybrid memory:**
This is the single richest unstructured signal we have about *how* agents work, *what* fails, *what* gets fixed. But ingesting raw will swamp Weaviate with noise (TodoWrite reminders, repeated `bd ready` polls, env-load chatter). Needs distillation pass before Weaviate ingest — e.g. extract every assistant turn that contains a `[FINAL]`, `[CONCUR]`, `[FAIL]`, `Step 0 RESTATE`, or `discovery_log` marker.

### `/home/elliotbot/.claude/projects/.../memory/` — already-distilled feedback corpus

- 84 `.md` files (each ~10-50 lines, one durable lesson per file)
- Index file `MEMORY.md` is 77 lines — covers ~75 entries → **9 unindexed memory files (drift)**
- Categories observable from filename prefix:
  - `feedback_*.md` (66 files) — corrections/confirmations from Dave or peers
  - `reference_*.md` (10 files) — pointers to systems Dave told us to remember
  - `research_*.md`, `project_*.md`, `user_*.md`, `api_*.md` — fewer
- This corpus already follows the discovery-log v2 spec in spirit (rule + Why + How-to-apply).

**Recommendation:** ingest the entire `memory/` dir as Tier-1 in Weaviate `Decisions` class. Backfill index drift first.

### `/home/elliotbot/.claude/{history.jsonl, paste-cache, file-history, plugins}` (global, not project-scoped)

- `history.jsonl` 8.3MB — prompt history
- `paste-cache` 31MB — pasted content cache
- `file-history` 50MB — file diff history
- `plugins` 5.3MB — installed plugins

Largely ephemeral. SKIP for ingest.

---

## 2. Local databases (knowledge stores agents wrote to)

### `/home/elliotbot/clawd/cognee_data/cognee_db` (SQLite, 215MB)

- Single SQLite file, last written 2026-05-13 21:27
- Pre-Weaviate knowledge graph attempt (KEI-44 era — Max's 3GB cgroup work).
- Schema unreadable from Atlas tier (no `sqlite3` binary on host) — Max should probe this; he shipped KEI-44 ingest.
- Companion file: `cognee_data/postgres` (412KB — likely metadata or vector dump).

**Decision needed:** Is cognee corpus the *source* for Weaviate seed, or has it been superseded? If superseded, archive and skip. If still valuable, Max extracts → distils → ingests.

### `/home/elliotbot/clawd/weaviate-data/` (1.1MB — destination, near-empty)

- Schema confirmed via `127.0.0.1:8090/v1/schema`:
  - Classes: **`Codebase`, `ToolCalls`, `Keis`, `Discoveries`, `Decisions`, `Sessions`**
- Object counts (verified via `/v1/graphql Aggregate.{cls}.meta.count`):
  - `Discoveries: 1` (KEI-49 smoke test object — "raspberries are aggregate fruits" probe)
  - `Codebase: 0`
  - `Decisions: 0`
  - `Keis: 0`
- Disk layout: classifications.db, modules.db, schema.db, raft/raft.db, plus per-class folders.
- Status: schema scaffolded, **empty**. This is what Dave's mandate is about.

### `/home/elliotbot/clawd/.beads/` (Dolt-backed task graph)

- Per-worktree:
  - `Agency_OS` (main): **26MB**, 99 issues — canonical Dolt DB
  - `aiden`, `max`, `scout`: ~220KB each, 99 issues (slim mirrors)
  - `atlas`: 216KB, 97 issues
  - `orion`: **60KB, 14 issues** — significantly out-of-sync (likely stale clone-pull)
- Contains: KEI history, claim/close timestamps, agent assignments, dependency graph, design decisions in `--design`/`--notes`/`--acceptance` fields.

**Recommendation:** ingest **closed issues only** with their final state (status=closed, resolution, design notes). Open/active issues should not be ingested (rapidly changing — query Beads live).

---

## 3. Per-worktree identity & instruction divergence

| Worktree | CLAUDE.md hash | IDENTITY.md hash | MEMORY.md present? |
|---|---|---|---|
| `Agency_OS` (main) | `7ac439be...` | unique | no |
| `Agency_OS-aiden` | `7ac439be...` (same) | unique | no |
| `Agency_OS-atlas` | `7ac439be...` (same) | unique | no |
| `Agency_OS-max` | `7ac439be...` (same) | unique | no |
| `Agency_OS-orion` | **`6d4f6e6e...` (DIVERGENT)** | unique | no |
| `Agency_OS-scout` | `7ac439be...` (same) | unique | no |

- **Finding:** Orion's `CLAUDE.md` is one line behind (missing `@.claude/modules/_discovery_log.md` import at line 48). Single-line drift; KEI-55 work likely branched from before that module landed.
- **No `MEMORY.md` file exists in any worktree.** The MEMORY.md referenced in CLAUDE.md (line 78 user instructions context) is at `/home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/MEMORY.md` (the global index) — not per-worktree.
- All `IDENTITY.md` hashes differ (correct — each callsign).

---

## 4. Per-worktree `.claude/` config (auto-loaded knowledge)

`/home/elliotbot/clawd/Agency_OS-atlas/.claude/` contains:
- `agents/` — **35 sub-agent specs** (audit-*, fix-p0/p2/p3/p5/*, architect-0, build-2/3, devops-6, research-1, review-5, test-4, fix-master) — these are Claude Code Task() sub-agent definitions
- `modules/` — **15 governance modules** auto-loaded by CLAUDE.md (`_law_step0.md`, `_orchestrator.md`, `_governance_rules.md`, `_discovery_log.md`, etc)
- `skills/` — 7 skill mirrors (callback-poller, drive-manual, mcp-bridge, leadmagic, pr-tool, decomposer, dataforseo)
- `commands/` — `kill.md`, `e2e.md` (slash command defs)
- `settings.json`, `settings.local.json`, `scheduled_tasks.lock`

**Recommendation:** ingest `modules/` (governance SSOT) and `agents/` (sub-agent specs) into `Decisions` and `Modules`-equivalent classes. These are read every session start — high recall value.

---

## 5. Top-level repo knowledge files (Atlas worktree)

- `ARCHITECTURE.md`, `MANUAL.md` (docs/), `DEFINITION_OF_DONE.md`, `HEARTBEAT.md`, `docs/governance/CONSOLIDATED_RULES.md`, `docs/governance/SOP_ARCHITECTURE_SSOT.md`, `docs/governance/agent_pairs_ratify_2026-05-14.md`, `docs/governance/deprecated/{r1_concur_before_summary,r5_shared_file_claim,r7_clone_direct_post}.md`
- `docs/audits/` — 24 audit reports (memory_audit_2026-05-12, demo_archaeology, drevon_port, etc)
- `docs/architecture/` — 13 architecture docs (MAX_COO_ARCHITECTURE.md, ARCHITECTURE_INDEX.md, discovery_vs_verification.md, distribution/, foundation/, flows/, frontend/, business/, etc)
- `docs/`: ~150 files at top level (A6_AUTH_AUDIT, B1_SIDEBAR_CONSOLIDATION, B2_*, agent_audit_anthropic.md, agent_sops.md, ENV_CHECKLIST.md, FIXED_COSTS_BREAKDOWN.md, etc)

**Recommendation:** Tier-1 ingest `docs/governance/*` (ratified rules) and `docs/architecture/*` (current). Deprecated/ → archive class, not main. Older audits (pre-2026-05) → sample, not full ingest.

---

## 6. Skills corpus

`/home/elliotbot/clawd/skills/` — 26 skill dirs + `SKILL_INDEX.md` (244 lines, "Last Updated Feb 17 2026" — **stale date stamp**) + `DEPRECATED.md`

Skills: agents, archive, callback-poller, campaign, conversion, crm, dataforseo, decomposer, drive-manual, email, enrichment, frontend, leadmagic, linkedin, mcp-bridge, pr-tool, slack-file-upload, superpowers, testing, three-store-save (top-level) + asic-new-co, austender, cognee-recall (in Agency_OS/skills/).

**Recommendation:** Tier-1 ingest all `SKILL.md` files. Per LAW VI, these are the canonical interface to external services — every agent reads them. Index drift (SKILL_INDEX.md last updated Feb 17) should be flagged to Elliot.

---

## 7. Operational logs (NOISE — exclude from ingest)

`/home/elliotbot/clawd/logs/` — 248MB total:

| File | Size | Type |
|---|---|---|
| `telegram-chat-bot.log` | 65MB | ephemeral chat traffic |
| `telegram-chat-bot-aiden.log` | 53MB | ephemeral chat traffic |
| `telegram-chat-bot-elliot.log` | 44MB | ephemeral chat traffic |
| `aiden-telegram.log` | 27MB | ephemeral |
| `listener-telemetry.jsonl` | 24MB (7886 lines) | listener health pings |
| `aiden-slack-mirror.log` | 16MB | slack dispatch echo |
| `telegram-chat-bot-max.log` | 13MB | ephemeral |
| `openai-cost.jsonl` | 5.7MB (29300 lines) | cost telemetry |
| Other (relay-watcher-*, cognee.log, evo-callback-poller, hook-failure-monitor, service-health-monitor, slack-central-listener, elliot-polling-loop, etc) | <2MB each | operational |

**Recommendation:** explicit **exclusion list** for Weaviate ingest. These would poison retrieval — agent asks "what did we decide about X" → get back a telegram heartbeat.

`/tmp/telegram-relay-*/` (7802 files, ~6MB) — same. Ephemeral dispatch envelopes already consumed.

---

## 8. Per-callsign environment files (`.config`)

`/home/elliotbot/.config/agency-os/`:
- `.env` (11.6KB — main credentials)
- `.env.aiden`, `.env.atlas`, `.env.elliot`, `.env.enforcer`, `.env.max`, `.env.orion`, `.env.scout` — per-callsign overrides (mostly TELEGRAM_BOT_TOKEN, CALLSIGN)
- `hooks/`, `modules/` (auto-load modules)
- `youtube_tokens.json`, `oauth_state_personal.json` — third-party OAuth state

**Recommendation:** NEVER ingest into Weaviate (contains secrets). Treat as out-of-scope.

---

## 9. Systemd user services (operational — not data sources)

- 20 services loaded (15 active, 5 FAILED).
- Active: agency-os-opa, agency-os-slack-central-listener, cognee, atlas-clone, atlas-inbox-watcher, atlas-relay-watcher, aiden/orion/scout/max-* inbox+relay watchers, dbus.
- **FAILED:** agency-os-hook-failure-monitor, agency-os-skill-pr-staleness-monitor, keiracom-poll-replies, openai-cost-daily, weaviate-backup.

**Flag to Elliot:** `weaviate-backup.service` failed. If we ingest into Weaviate without backup running, data loss risk.

---

## What's NOT ingest-worthy (Q3 hand-off to Orion)

Stale/superseded content that should NOT enter Weaviate:
- `/home/elliotbot/clawd/Agency_OS-atlas/docs/governance/deprecated/` (3 files: r1, r5, r7 — pre-7-rule consolidation)
- `/home/elliotbot/clawd/skills/DEPRECATED.md` and any skill marked deprecated
- `docs/audits/` older than 2026-04-01 — pre-pipeline-v2.1, likely contradicts current
- ARCHITECTURE.md SECTION 3 (Dead References) — explicit deprecation list, ingest only as exclusion signal
- Pre-role-swap (Elliot=CTO → COO) content where role assignment matters
- Anything in `/home/elliotbot/clawd/Agency_OS-orion/` that diverges from main (Orion CLAUDE.md is one line behind)

---

## Recommendations to Elliot (for consolidation post)

1. **Tier-1 ingest (small, high-signal, already-distilled):**
   - `~/.claude/projects/.../memory/*.md` (84 files, 368KB) → `Decisions` class. Fix 9-entry MEMORY.md drift first.
   - `clawd/skills/*/SKILL.md` (~26 files) → new `Skills` class. Update SKILL_INDEX stale date.
   - `Agency_OS-main/.claude/modules/*.md` (15 modules) → `Modules` class.
   - `docs/governance/CONSOLIDATED_RULES.md` + ratified governance → `Decisions`.

2. **Tier-2 ingest (medium, requires distillation):**
   - Beads closed issues (filter status=closed, status=done) → `Keis` class.
   - `docs/architecture/*` → `Codebase` class.

3. **Tier-3 ingest (large, needs aggressive distillation pass):**
   - Claude session transcripts — extract only assistant turns containing `[FINAL]`, `[CONCUR]`, `[FAIL]`, `Step 0 RESTATE`, or `discovery_log` markers. Drop everything else (TodoWrite noise, env loads, repeated polls).

4. **NEVER ingest:**
   - `/home/elliotbot/clawd/logs/*` (248MB chat/telemetry noise)
   - `/tmp/telegram-relay-*` (consumed envelopes)
   - `~/.config/agency-os/.env*` (secrets)
   - `.beads/` open/active issues (rapidly changing — query live)
   - `cognee_data/cognee_db` until Max confirms it's the source we want — likely superseded by KEI-48 Weaviate path.

5. **Fix before ingestion run:**
   - `weaviate-backup.service` FAILED — restore before populating.
   - MEMORY.md index drift (9 unindexed feedback files).
   - SKILL_INDEX.md last-updated stamp (Feb 17 vs reality May 16).
   - Orion CLAUDE.md one line behind main (missing `_discovery_log.md` import).

6. **Open question for Dave:**
   - Sensitivity of Claude session transcripts. They contain Dave-direct quotes, ratification language, business decisions, occasional credentials redacted as `***`. Approve ingestion + distillation pipeline, or hold?

---

## Verification — commands run

```
# Worktree enumeration
ls /home/elliotbot/clawd/ | grep Agency_OS  # → 6 worktrees

# Per-worktree CLAUDE.md/IDENTITY.md hash compare
sha256sum /home/elliotbot/clawd/Agency_OS*/CLAUDE.md  # → 1 divergent (Orion)
sha256sum /home/elliotbot/clawd/Agency_OS*/IDENTITY.md  # → 6 unique (correct)

# Weaviate schema + object counts
curl -s 127.0.0.1:8090/v1/schema  # → 6 classes
curl -s 127.0.0.1:8090/v1/graphql -d '{"query":"{ Aggregate { Discoveries { meta { count } } } }"}'  # → 1

# Beads sizes
du -sh /home/elliotbot/clawd/Agency_OS*/.beads  # → 26M main, ~220K clones, 60K orion
wc -l /home/elliotbot/clawd/Agency_OS*/.beads/issues.jsonl  # → 99/99/99/99/14/99

# Memory dir
ls /home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory | wc -l  # → 84 files
wc -l /home/elliotbot/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/MEMORY.md  # → 77 (drift)

# Logs
du -sh /home/elliotbot/clawd/logs  # → 248M

# Systemd
systemctl --user list-units --type=service --no-pager  # → 20 loaded, 5 failed
```

No data was moved. Read-only walk. Inventory complete.
