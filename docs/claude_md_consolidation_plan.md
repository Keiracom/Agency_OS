# CLAUDE.md Consolidation Plan
# Created: 2026-04-16 | Author: build-2 (elliot/memory-save-consolidation)
# Status: PLAN ONLY — execution requires Dave review and explicit approval

## Context

Two CLAUDE.md files currently carry overlapping governance content:
- `~/.claude/CLAUDE.md` — global, all-callsign (Elliot + Aiden + future bots)
- `/home/elliotbot/clawd/Agency_OS/CLAUDE.md` — Elliot worktree, project-specific

Goal: eliminate duplication, make the boundary explicit, and reduce maintenance surface.
The global file becomes the SSOT for cross-callsign laws. The worktree file owns
project-specific config only.

---

## Section-by-Section Audit of Worktree CLAUDE.md

Each section from `/home/elliotbot/clawd/Agency_OS/CLAUDE.md` is classified below.

### 1. Project header ("Project: Agency OS")
**Lines 1–9**
Content: project name, stack, repo path, env file location.
**WORKSPACE-SPECIFIC** — stays in worktree CLAUDE.md.
Reason: stack, repo path, and env path are Elliot-worktree specific. Aiden's worktree
would have different values.

---

### 2. MANDATORY STEP 0 RESTATE (LAW XV-D)
**Lines 11–22**
Content: Step 0 format + hard block declaration.
**DUPLICATE — SHARED** — already present in `~/.claude/CLAUDE.md` (lines 24–35).
Action: remove from worktree CLAUDE.md. Reference: "See ~/.claude/CLAUDE.md §MANDATORY STEP 0 RESTATE."
Risk: LOW — identical text in both; removing from worktree removes the duplication.

---

### 3. Session Start — Read the Manual First
**Lines 24–33**
Content: IDENTITY.md read, Drive manual read, staleness guard.
**SHARED** — applies to both Elliot and Aiden sessions.
Currently lives ONLY in worktree CLAUDE.md. Global file has a similar but older version
(lines 39–44) that lacks the IDENTITY.md step (LAW XVII) and the Drive-first override.
Action: move the WORKTREE version (more current, includes LAW XVII) to `~/.claude/CLAUDE.md`,
replacing the older global "Session Startup" section. Worktree keeps a one-liner:
"See ~/.claude/CLAUDE.md §Session Start."

---

### 4. Clean Working Tree (LAW XVI)
**Lines 35–37**
Content: git status before new directive, stash/commit unknown changes.
**SHARED** — applies to all callsigns operating git worktrees.
Action: move to `~/.claude/CLAUDE.md §Shared Governance Laws`. Remove from worktree.

---

### 5. Architecture First (LAW I-A)
**Lines 39–46**
Content: read ARCHITECTURE.md before any code change.
**WORKSPACE-SPECIFIC** — the ARCHITECTURE.md path and project context are worktree-bound.
Stays in worktree CLAUDE.md.
Note: The rule itself is universal but the operationalisation (which file to read, MCP bridge
endpoint) is project-specific.

---

### 6. MCP Bridge
**Lines 48–63**
Content: bridge invocation, available servers, LAW VI decision tree.
**WORKSPACE-SPECIFIC** — bridge path, server list, and LAW VI hierarchy are Agency OS
specific (Aiden may have a different bridge path or server set in future).
Stays in worktree CLAUDE.md.

---

### 7. Supabase — Primary Memory Store (LAW IX)
**Lines 65–81**
Content: project ID, session start/end SQL queries.
**WORKSPACE-SPECIFIC** — project ID `jatzvazlbusedwsnqxzr` and schema (`elliot_internal`)
are Elliot-worktree specific.
Stays in worktree CLAUDE.md.
Note: The principle (Supabase is SOLE persistent memory) is shared, but the SQL and
project ID are not.

---

### 8. Governance Laws table
**Lines 83–112**
Content: LAW I-A through GOV-12 reference table + shared governance pointer.
**PARTIALLY SHARED / PARTIALLY WORKSPACE-SPECIFIC**

Sub-classification:
- LAW I-A, II, III, IV, V, VI, VII, VIII, IX, XI, XIV: SHARED — apply to all callsigns.
  Currently duplicated (global file has these). Action: global file is SSOT; worktree
  table becomes a condensed reference with a pointer to global.
- LAW XII, XIII: SHARED — skills-first rules apply to all callsigns.
- LAW XV: NOTE — global file says "Four-Store" (4 stores); worktree says "Four-Store"
  too. BOTH need to match. Currently consistent — keep in both files as it is
  operationally critical and must be visible in worktree context.
- LAW XV-A, XV-B, XV-C, XV-D: SHARED — apply to all callsigns.
- GOV-8 through GOV-12: WORKSPACE-SPECIFIC — these are Agency OS pipeline governance
  rules (stage audits, gate-as-code, extraction protocol). Stays in worktree.

Action: restructure worktree governance table into two sections:
  (a) "Cross-callsign laws — see ~/.claude/CLAUDE.md for canonical text" (condensed list)
  (b) "Agency OS pipeline governance (GOV-8 through GOV-12)" (full text, stays here)

---

### 9. Group Chat Plumbing
**Lines 113–147**
Content: Telegram supergroup chat_id, `tg` script usage, relay dirs, prefix conventions.
**SHARED** — both Elliot and Aiden use the same group chat, same `tg` script, same
cross-post mechanism.
Action: move to `~/.claude/CLAUDE.md`. Worktree keeps a one-liner reference.
Note: relay dir paths include `{callsign}` substitution so they're already callsign-agnostic.

---

### 10. Directive + Validation Governance (GOV-9, GOV-11, GOV-12 prose)
**Lines 148–160**
Content: GOV-9 directive scrutiny, GOV-11 structural audit, GOV-12 gates-as-code — detailed text.
**WORKSPACE-SPECIFIC** — pipeline validation governance is Agency OS specific.
Stays in worktree CLAUDE.md.

---

### 11. Dead References table
**Lines 162–174**
Content: deprecated APIs + replacements, active exceptions.
**WORKSPACE-SPECIFIC** — enrichment vendor choices are Agency OS specific.
Stays in worktree CLAUDE.md.

---

### 12. Active Enrichment Path
**Lines 176–182**
Content: waterfall tier sequence, ALS gates, cost per tier.
**WORKSPACE-SPECIFIC** — pipeline architecture.
Stays in worktree CLAUDE.md.

---

### 13. Directive Format
**Lines 184–191**
Content: `Directive #NNN` template.
**SHARED** — format applies to all callsigns.
Action: move to `~/.claude/CLAUDE.md §EVO Protocol` or new §Directive Format.
Worktree keeps a one-liner reference.

---

### 14. Session End Protocol
**Lines 193–202**
Content: 4-store check script, ceo_memory writes, daily_log, context thresholds.
**PARTIALLY SHARED**
- Context thresholds (40%/50%/60%) and the principle of session-end writes: SHARED.
- The specific script (`python scripts/session_end_check.py`) and ceo_memory key format:
  WORKSPACE-SPECIFIC (Elliot worktree script path).
Action: move thresholds + principle to global; keep script invocation in worktree.

---

## Summary Table

| Section | Classification | Action |
|---------|---------------|--------|
| Project header | WORKSPACE-SPECIFIC | Stay |
| Step 0 RESTATE | SHARED (duplicate) | Remove from worktree, pointer only |
| Session Start (LAW XVII incl.) | SHARED (worktree more current) | Move to global, update global |
| Clean Working Tree (LAW XVI) | SHARED | Move to global §Shared Governance |
| Architecture First (LAW I-A) | WORKSPACE-SPECIFIC | Stay |
| MCP Bridge | WORKSPACE-SPECIFIC | Stay |
| Supabase memory store | WORKSPACE-SPECIFIC | Stay |
| Governance laws table (cross-callsign) | SHARED (duplicate) | Condense in worktree, global is SSOT |
| Governance laws table (GOV-8–12) | WORKSPACE-SPECIFIC | Stay |
| Group Chat Plumbing | SHARED | Move to global |
| GOV-9/11/12 prose | WORKSPACE-SPECIFIC | Stay |
| Dead References | WORKSPACE-SPECIFIC | Stay |
| Active Enrichment Path | WORKSPACE-SPECIFIC | Stay |
| Directive Format | SHARED | Move to global |
| Session End (script + thresholds) | PARTIALLY SHARED | Split: principle→global, script→worktree |

---

## Conflicts Identified

1. **LAW XV store count mismatch (RESOLVED in both files):** Global file says "Four-Store"
   (4 stores incl. Google Drive). Worktree also says "Four-Store" as of the current read.
   Both are consistent. No action needed.

2. **Session Startup in global is stale:** Global `~/.claude/CLAUDE.md` "Session Startup"
   (lines 37–44) predates LAW XVII and lacks the IDENTITY.md read step. The worktree
   "Session Start" (lines 24–33) is more current. When migrating, the WORKTREE version
   should win and replace the global version.

3. **Step 0 RESTATE appears in both files identically:** Pure duplication. Safe to
   remove from worktree; pointer added.

4. **EVO Protocol lives only in global:** Worktree has no EVO Protocol section. No
   conflict — global is already authoritative here.

---

## Proposed Worktree CLAUDE.md Structure Post-Migration

```
# CLAUDE.md — Agency OS Project Config (Elliot Worktree)

## Project: Agency OS
[stack, paths, env — WORKSPACE-SPECIFIC]

## Cross-Callsign Governance
See ~/.claude/CLAUDE.md for: Step 0 RESTATE, EVO Protocol, Session Start,
Clean Working Tree (LAW XVI), Agent Assignment, Completion Alerts, /kill,
Directive Format, Group Chat Plumbing, LAW XVII.

## Architecture First (LAW I-A — HARD BLOCK)
[WORKSPACE-SPECIFIC — unchanged]

## MCP Bridge
[WORKSPACE-SPECIFIC — unchanged]

## Supabase — Primary Memory Store (LAW IX)
[WORKSPACE-SPECIFIC — unchanged]

## Governance Laws
### Cross-callsign laws (condensed reference)
See ~/.claude/CLAUDE.md for canonical text: LAW I-A, II, III, IV, V, VI, VII,
VIII, IX, XI, XII, XIII, XIV, XV, XV-A, XV-B, XV-C, XV-D, XVI, XVII.

### Agency OS pipeline governance
[GOV-8 through GOV-12 — full text — WORKSPACE-SPECIFIC]

## Directive + Validation Governance (GOV-9, GOV-11, GOV-12 prose)
[WORKSPACE-SPECIFIC — unchanged]

## Dead References
[WORKSPACE-SPECIFIC — unchanged]

## Active Enrichment Path
[WORKSPACE-SPECIFIC — unchanged]

## Session End Protocol
Script: python scripts/session_end_check.py
[See ~/.claude/CLAUDE.md for context thresholds and principle]
```

---

## Execution Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Global CLAUDE.md edit breaks Aiden session | HIGH | Aiden reads global — any change must be reviewed and coordinated |
| Stale pointer in worktree causes missed governance | MEDIUM | Keep pointer explicit with section name + line ref |
| Session Startup version conflict | MEDIUM | Worktree version wins; update global carefully |
| Lost content during move | LOW | PR diff provides full audit trail |

---

## Recommended Execution Sequence (when Dave approves)

1. Dave reviews this plan and approves specific sections to move.
2. Build-2 creates PR branch `elliot/claude-md-migration`.
3. Update global `~/.claude/CLAUDE.md` first (additive — add moved sections).
4. Trim worktree `CLAUDE.md` second (remove duplicates, add pointers).
5. Both bots (Elliot + Aiden) restart sessions to reload updated global.
6. Dave confirms both bots correctly reference the new structure.

**This plan file must not be deleted after execution — it documents the migration
rationale for governance audit purposes.**
