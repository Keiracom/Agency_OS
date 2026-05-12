# Memory Audit — 2026-05-12 (Phase 1, Inventory + Findings Only)

**Status:** Synthesis complete. **PAUSED for Dave review** per directive ts ~1778557082. No Phase 2 work (redesign, retirements, fixes) starts without explicit go-ahead.

**Owners:** Aiden (Supabase), Max (Drevon-port audit-trail tables), Orion (filesystem + Drive), Atlas (mem0 cloud), Elliot (synthesis + claude.ai instructions + cross-store).

**Inputs:** four section docs in this folder —
- `memory_audit_2026-05-12_aiden_section.md` (9 Supabase tables, 3 schemas)
- `memory_audit_2026-05-12_max_section.md` (5 Drevon-port tables — sessions/turns/turn_logs/turn_files/messages)
- `memory_audit_2026-05-12_orion_section.md` (6 worktrees × CLAUDE/IDENTITY/modules/HEARTBEAT/settings/MEMORY + Drive Manual + auto-memory pins; PR #758)
- `memory_audit_2026-05-12_atlas_section.md` (mem0 cloud + 4 wired call sites + JSONL log; PR #760)

**Methodology (common attribute set, agreed before dispatch):**
name / purpose / **authority** (5-cat: SSOT / DERIVED / ARCHIVE / DEPRECATED / ORPHAN) / size / **freshness** (MAX created_at|updated_at|mtime) / **churn** (Postgres n_live/n_dead or git commits 7d) / **readers** (grep src/+scripts/+skills/+.claude/hooks/) / **writers** (same) / **last-access proxy** (idx_scan+seq_scan for Postgres, atime for filesystem, JSONL log for mem0) / **surprises**.

Each owner ran the same attribute schema against their store, flagged a "Surprises" section, and avoided redesign recommendations. This synthesis layers cross-cutting findings on top.

---

## Executive Summary — Plain English

We have 27 named memory stores spread across 5 mediums (Supabase, Drevon-port tables, filesystem-per-worktree, Google Drive, mem0 cloud) and 6 codebases (one per agent). Roughly half of the 27 stores are healthy SSOTs that are being read and written as designed. The other half breaks down into three patterns:

1. **Partial migrations that never closed the old read path** — same shape, three times: `elliot_internal.memories` (no writers, ad-hoc readers continue), the Drevon `messages` table (no writers ever wired, but `skill_gen/extractor.py` reads it on every compression run and silently gets zero rows), and mem0 cloud (one-shot backfill wrote 82 memories under `user_id="system"`, but recall code filters by per-agent callsign — every search returns zero by construction).

2. **Orphan stores with active infrastructure** — Postgres tables that nothing writes but still have attached triggers, embeddings, indexes, or scoring functions (`elliot_knowledge` with 2 triggers, `ceo_memory_archive`, `elliot_signoff_queue`, `turn_files` with zero idx_scan, the deprecated repo-local `MEMORY.md` committed in all 6 worktrees).

3. **SSOT label contradictions** — at least three places where two stores both claim to be the canonical source for the same content: Drive Doc vs `docs/MANUAL.md`, global vs per-worktree CLAUDE.md session-start pointer (`elliot_internal.memories` vs `public.agent_memories`), and `ceo:mem0_decision_2026-05-01` ratified state vs empirical mem0 state.

The biggest single waste of dollars or time isn't disk or compute — it's silent zero-result reads. `skill_gen` compresses without user-message context. Mem0 recall returns empty arrays on every production search. The `elliot_knowledge` scoring pipeline is wired end-to-end and never invoked.

The biggest single piece of new-agent drift is **Scout** — running on the pre-2026-05-11 monolithic CLAUDE.md, missing the shared `.claude/modules/` folder, missing recent governance hooks, on the old heartbeat template, and its identity file still says Elliot is CTO.

**Recommendation:** none — this is Phase 1. Phase 2 candidates are listed at the bottom, but no work starts until Dave directs.

---

## Cross-Store Inventory Matrix

27 stores total, grouped by medium. Per-store detail in section docs; this is the consolidated map.

| # | Store | Medium | Authority | Owner | Live data | Surprise count |
|---|---|---|---|---|---|---|
| 1 | `public.ceo_memory` | Supabase | SSOT | Aiden | 575 rows / 616 kB | — |
| 2 | `public.agent_memories` | Supabase | SSOT | Aiden | 6,311 rows / 31 MB | — |
| 3 | `public.governance_events` | Supabase | SSOT | Aiden | 25,617 rows / 7.3 MB | — |
| 4 | `public.cis_directive_metrics` | Supabase | SSOT | Aiden | 195 rows / 176 kB | 1 (no ON CONFLICT — re-runs duplicate) |
| 5 | `keiracom_admin.task_queue` | Supabase | SSOT | Aiden | 91 rows / 128 kB | — |
| 6 | `elliot_internal.memories` | Supabase | DEPRECATED | Aiden | 1,665 rows / 30 MB | 2 (read path not closed; global CLAUDE.md still points here) |
| 7 | `public.ceo_memory_archive` | Supabase | ORPHAN | Aiden | 14 rows / 64 kB | 1 (no archival writer) |
| 8 | `public.elliot_knowledge` | Supabase | ORPHAN | Aiden | 659 rows / 2.6 MB + embeddings | 1 (2 triggers still attached) |
| 9 | `public.elliot_signoff_queue` | Supabase | ORPHAN | Aiden | 52 rows / 168 kB | — |
| 10 | `public.sessions` | Drevon-port | SSOT | Max | 137 rows / 144 kB | 1 (`extra` jsonb undocumented + unused) |
| 11 | `public.turns` | Drevon-port | SSOT | Max | 125 rows / 128 kB | 1 (37% seq-scan ratio) |
| 12 | `public.turn_logs` | Drevon-port | SSOT | Max | 1,663 rows / 1.6 MB | — |
| 13 | `public.turn_files` | Drevon-port | DERIVED | Max | 321 rows / 248 kB | 1 (zero idx_scan; recorder always passes empty `files=[]`) |
| 14 | `public.messages` | Drevon-port | ORPHAN | Max | 0 rows | 1 (live reader in skill_gen gets [] silently — REAL BUG) |
| 15 | `CLAUDE.md` (per-worktree) | Filesystem | SSOT-per-tree | Orion | 1244 b × 5 worktrees + 9258 b Scout | 1 (Scout forked) |
| 16 | `IDENTITY.md` (per-worktree) | Filesystem | SSOT-per-tree | Orion | 372–2300 b | 2 (Orion 11-line minimal; Scout role stale) |
| 17 | `.claude/modules/*.md` | Filesystem | DERIVED | Orion | 13 modules × ~7 KB each | 1 (Scout has no modules dir) |
| 18 | `.claude/settings.json` | Filesystem | SSOT-per-tree | Orion | 3115–6363 b | 1 (4 distinct shapes across 6 worktrees) |
| 19 | `MEMORY.md` (repo-local) | Filesystem | DEPRECATED | Orion | 4495 b × 6 (identical) | 1 (still committed; easily confused with auto-memory MEMORY.md) |
| 20 | `HEARTBEAT.md` (per-worktree) | Filesystem | SSOT-per-tree | Orion | 1170 b × 5 + 367 b Scout | 1 (Scout pre-#751) |
| 21 | Drive Manual (Doc `1p9F…e9ho`) | Drive | SSOT (claimed) | Orion | 56,539 b | 1 (Dave hasn't opened in 3 weeks) |
| 22 | `docs/MANUAL.md` | Filesystem | SSOT (self-claimed) | Orion | 109,808 b / 1395 LOC | 1 (contradicts Drive SSOT label — actually IS primary per write order) |
| 23 | `~/.claude/projects/…/MEMORY.md` (auto-memory index) | Filesystem | SSOT | Orion | 4611 b | 1 (same filename as #19) |
| 24 | `~/.claude/projects/…/feedback_*.md` + `project_*.md` (pins) | Filesystem | SSOT-each | Orion | 33 files / 34,866 b | 1 (30 pins — no retirement step) |
| 25 | mem0 cloud (api.mem0.ai) | External | INACTIVE | Atlas | 82 memories (all `system` callsign) | 8 (callsign deadlock, dual-write gate off, consumer service inactive, ceo_memory drift, SDK 2.x v3-endpoint drift, free-tier cliff at 140 days, etc.) |
| 26 | `src/governance/mem0_adapter.py` + 3 call sites | Code | WIRED, IDLE | Atlas | 4 files, gated off | (subsumed in #25) |
| 27 | `logs/mem0-usage.jsonl` | Filesystem | ARCHIVE | Atlas | 60 entries / 5421 b | 1 (frozen since 2026-05-02, 10 days silent) |

**Total surprises flagged across all 4 sections:** ~25. Three cross-cutting patterns emerge.

---

## Cross-Cutting Findings

### Pattern A — Unclosed read paths during partial migrations

The same shape of bug shows up in three independent stores, owned by three different agents, found independently:

| Store | Migration | What didn't close | Reader symptom |
|---|---|---|---|
| `elliot_internal.memories` (#6) | → `public.agent_memories` | Global CLAUDE.md session-start block + ad-hoc psql still read old store | 2,858 seq_scan reads continue on dead table |
| `public.messages` (#14) | Schema + `record_message()` writer shipped; no hook wired | `skill_gen/extractor.py::_fetch_user_messages` reads it on every compression | Silent `[]` return; SKILL.md generated without user-prompt chronology |
| mem0 cloud (#25) | Backfill on 2026-05-01 wrote 82 rows; per-agent callsign filter on read | `recall_via_mem0` searches under `aiden`/`elliot`/etc.; rows are under `system` | Every production search returns `[]`; hybrid recall becomes Supabase-only with extra latency |
| `MEMORY.md` (repo-local, #19) | Marked deprecated in seed script; still committed | None active — but `Read` tool surfaces it; agents may treat it as live | Confusion source, not active bug |

**Common root cause:** writer-side migration shipped without an audit + close of the read-side. The author moved on assuming the old path was dead; it wasn't.

**Phase 2 implication (not a recommendation — just an observation):** any future memory-store migration plan should include an explicit step: "grep for readers of the old path; replace OR delete them in the same PR; CI gate on zero residual references." Aiden noted this exact pattern in her section's Surprise #3.

### Pattern B — Orphan stores with attached infrastructure

| Store | Attached infra | Why it's still there |
|---|---|---|
| `elliot_knowledge` (#8) | 2 INSERT/UPDATE triggers (`trg_score_knowledge_insert`, `trg_score_knowledge_update`) + 2.6 MB of embeddings | Built end-to-end then never invoked from src/ |
| `ceo_memory_archive` (#7) | None — clean orphan | Was likely populated by a script that no longer exists |
| `elliot_signoff_queue` (#9) | None — clean orphan | Human-in-the-loop gate; pattern obsoleted by Telegram concur flow |
| `turn_files` (#13) | FK index on `turn_log_id`; recorder code path passes through | Recorder always passes `files=[]` from the hook layer — table is reachable but unwritten in practice |
| `public.messages` (#14) | Schema + `record_message()` writer + extractor reader | Writer never wired into any hook |
| `MEMORY.md` repo-local (#19) | Committed in all 6 worktrees | Seed script flags deprecated but doesn't remove |
| `~/.claude/projects/…/memory/` pins (#24) | 30 feedback pins, no retirement step | Pins accumulate; contradictory feedback never explicitly retired |

**Common shape:** infrastructure was built before utility was proven, or built then orphaned by a strategy shift. None of these is actively breaking; all are surface area we maintain for zero value.

### Pattern C — SSOT label contradictions

| Subject | Claim A | Claim B | Actual behaviour |
|---|---|---|---|
| The Manual | Global `~/.claude/CLAUDE.md` §0: "Read the Agency OS Manual from Google Drive… This is the CEO SSOT" | `docs/MANUAL.md` line 7: "Primary store. This file is the CEO SSOT. Google Doc is an auto-generated mirror" | `docs/MANUAL.md` writes first (02:47:42 UTC), Drive mirror updates ~4 min later (02:51:17) — repo is primary. Global CLAUDE.md pointer stale. |
| Session-start memory store | Global CLAUDE.md: query `elliot_internal.memories` | Per-worktree `CLAUDE.md` + `.claude/modules/_session_start.md`: query `public.agent_memories` | Per-worktree wins in practice (newer modular config). Global still loads first per Claude Code session-start order. Drift unrectified. |
| mem0 status | `ceo:mem0_decision_2026-05-01`: "BUILT + OPERATIONAL 80%" | Empirical: dual-write gate off, callsign deadlock, consumer service `inactive + disabled`, 10-day silent JSONL | Ratified state contradicts running state. ceo_memory key needs supersession regardless of disposition outcome. |

Aiden's section flagged the first two; Atlas's flagged the third. Same shape, three places.

---

## Section 5 — Claude.ai Project Instructions + Auto-Memory + Cross-Store (Elliot)

Brief contribution since most cross-store content is now woven into the synthesis above.

**claude.ai project instructions** (visible at session top under `# claudeMd`): aggregate of `~/.claude/CLAUDE.md` (global) + `/home/elliotbot/clawd/CLAUDE.md` (parent dir) + `/home/elliotbot/clawd/Agency_OS/CLAUDE.md` (project) + `.claude/modules/*.md` (transitively via `@import`). Total ~7 KB of instructions auto-loaded every session. Authority: SSOT. Last update: 2026-05-12 (modules churn 3 commits last 7d). No drift between worktrees on the modular layer (orion confirmed 5/6 identical, Scout the outlier).

**Auto-memory (`~/.claude/projects/-home-elliotbot-clawd-Agency-OS/memory/`):** 33 files / ~35 KB / 30 feedback pins + 3 project pins. Authority: SSOT each. Auto-loaded transitively via the `MEMORY.md` index in the same folder. Writer: Claude Code harness on user feedback. No retirement step. **Surprise:** the 30 feedback pin count itself is the concerning number — pin contradictions accumulate without an explicit "which still applies" review. (Covered as Pattern B above.)

**Cross-store relationships:**
- `agent_memories` table writes pre-2026-05-01 mirror to mem0 cloud (now gated off). Mem0 cloud is the only true "external duplicate" of an internal SSOT.
- `docs/MANUAL.md` → Drive Doc (one-direction mirror, `skills/drive-manual/write_manual.py`). Repo is primary per write order.
- `ceo_memory` key `ceo:directives.last_number` is the authoritative directive counter, but the same counter is also written to `docs/MANUAL.md` (directive log section) and to `cis_directive_metrics` (one row per directive). Three sources of truth that must remain consistent. The LAW XV mechanical gate (PR #752) is the first runtime check that forces them to be.
- `governance_events` is the SSOT audit trail; `phoenix_export_loop.py` is the only reader that exports it outward.

**No new stores to flag** beyond what the other 4 sections covered.

---

## Phase 2 Candidates (listed, not recommended)

Listing inventory of plausible Phase 2 work for Dave to direct on. These are NOT proposals — they are the result of "if we were to act on what this audit found, the work items would be…":

1. **Retire mem0** (Atlas section recommendation, RETIRE disposition with 6-step staged plan)
2. **Close `elliot_internal.memories` reader path** (Aiden surprise #3 — drop global CLAUDE.md session-start block, update to public.agent_memories, drop ad-hoc psql usage)
3. **Wire `record_message` into a UserPromptSubmit hook OR remove `_fetch_user_messages`** (Max surprise #1 — the orphan `messages` table with a live broken reader)
4. **Drop 3 Supabase orphan tables** (Aiden — `ceo_memory_archive`, `elliot_knowledge` w/ triggers, `elliot_signoff_queue`)
5. **Bring Scout up to current** (Orion drift 1 — propagate modules dir, settings.json, HEARTBEAT.md, fix IDENTITY.md role staleness)
6. **Thicken Orion's IDENTITY.md** (Orion drift 2 — match Aiden/Atlas template)
7. **Reconcile `.claude/settings.json` shape** across 6 worktrees (Orion drift 3)
8. **Remove deprecated repo-local `MEMORY.md`** from all 6 worktrees (Orion drift 4)
9. **Resolve SSOT label contradiction** for the Manual (Orion drift 5 — pick one, update the other to "mirror")
10. **Fix `cis_directive_metrics` ON CONFLICT bug** in `scripts/three_store_save.py` (Aiden surprise #4)
11. **Persist Drive mirror exit code** to ceo_memory / cis_directive_metrics (Aiden surprise #5)
12. **Memory pin retirement step** — process to review the 30 pins and explicitly mark superseded ones (Orion table #10)
13. **CI gate on memory-migration completeness** — fail PR if a writer is removed without grep showing zero residual readers (cross-cutting Pattern A)

13 items, no priorities, no order. Dave's call.

---

## Pause Notice

Per directive ts ~1778557082 ("Pause after synthesise doc") — Phase 1 is complete. All Phase 2-derivative work stops. The team waits for Dave's review and direction on which subset (if any) of the 13 candidates above to schedule, and in what order.

Non-audit-derived work (existing PRs, separate roadmap items) continues to completion per the no-closing pin. Specifically: PR #759 (clone fan-out fix) merges, PR #761 (LLM wiki) merges, central listener restarts to activate Option B. None of those depend on Dave's audit review.

— Elliot (synthesis)
