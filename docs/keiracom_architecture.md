# Keiracom Architecture — Multi-Agent CTO Operating System
**Complete Instance, Governance, Communication, and State Architecture**

**Document Type:** Technical SOP (Reference)
**Ratified:** 2026-04-24
**Version:** 2.0
**Authority:** LAW I-A — Architecture First (mandatory read before any architectural decision)

---

## A. INSTANCE ARCHITECTURE

### A.1 Multi-Instance Overview

Keiracom runs **5 simultaneous Claude Code terminal sessions**, each with its own identity, workspace, and governance:

```
╔════════════════════════════════════════════════════════════════╗
║  Session Registry (confirmed via: tmux list-sessions)          ║
╠════════════════════════════════════════════════════════════════╣
║ 1. elliottbot (primary) — callsign: elliot                      ║
║    Workspace: /home/elliotbot/clawd/Agency_OS/                 ║
║    Branch: main + feature branches                              ║
║    Created: 2026-04-07                                          ║
║    Telegram bot: @existing (legacy, not registered as distinct) ║
║    Role: CTO, primary orchestrator                              ║
║                                                                 ║
║ 2. aiden — callsign: aiden                                      ║
║    Workspace: /home/elliotbot/clawd/Agency_OS-aiden/           ║
║    Branch: aiden/scaffold (does NOT merge to main)             ║
║    Created: 2026-04-16                                          ║
║    Telegram bot: @Aaaaidenbot                                   ║
║    Role: Secondary orchestrator, scaffold manager               ║
║                                                                 ║
║ 3. atlas — callsign: atlas (Elliot's Tier A clone)             ║
║    Workspace: /home/elliotbot/clawd/Agency_OS-atlas/           ║
║    Branch: atlas/* (off main)                                   ║
║    Created: 2026-04-22                                          ║
║    Telegram: NONE (clone — relays via inbox/outbox)            ║
║    Role: Elliot's parallel build executor                       ║
║                                                                 ║
║ 4. orion — callsign: orion (Aiden's Tier A clone)              ║
║    Workspace: /home/elliotbot/clawd/Agency_OS-orion/           ║
║    Branch: orion/* (off main)                                   ║
║    Created: 2026-04-22                                          ║
║    Telegram: NONE (clone — relays via inbox/outbox)            ║
║    Role: Aiden's parallel build executor                        ║
║                                                                 ║
║ 5. scout — callsign: elliot (research override, NOT separate)   ║
║    Workspace: /home/elliotbot/clawd/Agency_OS-scout/           ║
║    Branch: scout/p12-* (feature branches)                       ║
║    Created: 2026-04-17                                          ║
║    Role: Isolated research / audit work                         ║
╚════════════════════════════════════════════════════════════════╝
```

### A.2 Git Worktree Structure

```bash
# Primary production worktrees (all backed by single .git directory):
$ git worktree list

/home/elliotbot/clawd/Agency_OS                     43a9efa1 [elliot/step1-cleanup]
/home/elliotbot/clawd/Agency_OS-aiden               4a203271 [aiden/outreach-audit-doc]
/home/elliotbot/clawd/Agency_OS-atlas               4c508a70 [atlas/main]
/home/elliotbot/clawd/Agency_OS-scout               17f2aff9 [scout/p12-enderfga-fork-eval]

# Sub-agent worktrees (created and destroyed per task):
/home/elliotbot/clawd/Agency_OS/.claude/worktrees/agent-a197e2c9  0a5f516d [elliot/stage8-email-gate]
/home/elliotbot/clawd/Agency_OS/.claude/worktrees/agent-a27d7a1c  360704a8 [worktree-agent-a27d7a1c]
(... 6 more transient sub-agent worktrees)
```

**Key Property:** All worktrees share a single `.git` directory but maintain independent working directories. This enables:
- **Isolation:** Each instance has its own branch, changes, and state
- **Parallelism:** Multiple builds run simultaneously without blocking
- **Sharing:** All instances read/write to the same remote origin

### A.3 IDENTITY.md — Callsign Ground Truth

Each session reads `./IDENTITY.md` as the single source of truth for its callsign. This file is **MANDATORY** and enforces LAW XVII (Callsign Discipline).

#### A.3.1 Elliot's IDENTITY.md
**Location:** `/home/elliotbot/clawd/Agency_OS/IDENTITY.md`
```
# IDENTITY

**CALLSIGN:** elliot
**Workspace:** /home/elliotbot/clawd/Agency_OS/
**Telegram bot:** @existing (per src/telegram_bot/chat_bot.py)
**Created:** 2026-04-16
**Branch:** main (and feature branches off main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, Telegram outbound message, PR title, commit trailer, and three-store save (LAW XVII — Callsign Discipline).

If `CALLSIGN` env var is set, it MUST match this file. Mismatch is a governance violation — STOP and alert Dave.

**Group chat:** this session participates in the Agency OS Telegram supergroup alongside Aiden. Plumbing, `tg` usage, cross-post mechanism, and prefix conventions are documented in `CLAUDE.md §Group Chat Plumbing`. Read that before sending any group messages — curl bypasses cross-post.

**Shared governance:** laws that apply to all callsigns (e.g. LAW XVII — Callsign Discipline) live in `~/.claude/CLAUDE.md §Shared Governance Laws`. Worktree-specific laws stay in the worktree's `CLAUDE.md`.
```

#### A.3.2 Aiden's IDENTITY.md
**Location:** `/home/elliotbot/clawd/Agency_OS-aiden/IDENTITY.md`
```
# IDENTITY

**CALLSIGN:** aiden
**Workspace:** /home/elliotbot/clawd/Agency_OS-aiden/
**Telegram bot:** @Aaaaidenbot
**Created:** 2026-04-16
**Branch:** aiden/scaffold (does not merge to main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, Telegram outbound message, PR title, commit trailer, and four-store save (LAW XVII — Callsign Discipline).

If `CALLSIGN` env var is set, it MUST match this file (aiden). Mismatch is a governance violation — STOP and alert Dave.

**Group chat:** this session participates in the Agency OS Telegram supergroup alongside Elliot. All communication via `tg -g`. Plumbing, `tg` usage, cross-post mechanism, and prefix conventions are documented in `CLAUDE.md §Group Chat Plumbing`.

**Your clone:** ORION at /home/elliotbot/clawd/Agency_OS-orion/. Dispatch via /tmp/telegram-relay-orion/inbox/.

**Shared governance:** laws that apply to all callsigns (e.g. LAW XVII — Callsign Discipline) live in `~/.claude/CLAUDE.md §Shared Governance Laws`. Worktree-specific laws stay in the worktree's `CLAUDE.md`.
```

#### A.3.3 Clone IDENTITY Files
**ATLAS:** `/home/elliotbot/clawd/Agency_OS-atlas/IDENTITY.md`
```
# IDENTITY

**CALLSIGN:** atlas
**Workspace:** /home/elliotbot/clawd/Agency_OS-atlas/
**Telegram bot:** none (clone — communicates via inbox/outbox relay only)
**Created:** 2026-04-22
**Branch:** atlas/* (feature branches off main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, PR title, commit trailer, and outbox message (LAW XVII — Callsign Discipline).

You are ATLAS — ELLIOT's Tier A build clone. You do NOT post to Telegram group (C3 Prime-Only Channel). All output goes to outbox JSON files at /tmp/telegram-relay-atlas/outbox/. Parent (ELLIOT) surfaces results to group.

If `CALLSIGN` env var is set, it MUST match this file (atlas). Mismatch is a governance violation — STOP.

**Governance:** Follow all laws in CLAUDE.md. Rebase on origin/main before any commit. Zero-deletion merges by default. ruff check + pytest must pass before PR.
```

**ORION:** `/home/elliotbot/clawd/Agency_OS-orion/IDENTITY.md`
```
# IDENTITY

**CALLSIGN:** orion
**Workspace:** /home/elliotbot/clawd/Agency_OS-orion/
**Telegram bot:** none (clone — communicates via inbox/outbox relay only)
**Created:** 2026-04-22
**Branch:** orion/* (feature branches off main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, PR title, commit trailer, and outbox message (LAW XVII — Callsign Discipline).

You are ORION — AIDEN's Tier A build clone. You do NOT post to Telegram group (C3 Prime-Only Channel). All output goes to outbox JSON files at /tmp/telegram-relay-orion/outbox/. Parent (AIDEN) surfaces results to group.

If `CALLSIGN` env var is set, it MUST match this file (orion). Mismatch is a governance violation — STOP.

**Governance:** Follow all laws in CLAUDE.md. Rebase on origin/main before any commit. Zero-deletion merges by default. ruff check + pytest must pass before PR.
```

**SCOUT:** `/home/elliotbot/clawd/Agency_OS-scout/IDENTITY.md`
```
# IDENTITY

**CALLSIGN:** elliot
**Workspace:** /home/elliotbot/clawd/Agency_OS/
**Telegram bot:** @existing (per src/telegram_bot/chat_bot.py)
**Created:** 2026-04-16
**Branch:** main (and feature branches off main)

This file is the single source of truth for this session's identity. Read FIRST at session load. Your callsign tags every Step 0 RESTATE, Telegram outbound message, PR title, commit trailer, and three-store save (LAW XVII — Callsign Discipline).

If `CALLSIGN` env var is set, it MUST match this file. Mismatch is a governance violation — STOP and alert Dave.

**Group chat:** this session participates in the Agency OS Telegram supergroup alongside Aiden. Plumbing, `tg` usage, cross-post mechanism, and prefix conventions are documented in `CLAUDE.md §Group Chat Plumbing`. Read that before sending any group messages — curl bypasses cross-post.

**Shared governance:** laws that apply to all callsigns (e.g. LAW XVII — Callsign Discipline) live in `~/.claude/CLAUDE.md §Shared Governance Laws`. Worktree-specific laws stay in the worktree's `CLAUDE.md`.
```

### A.4 CALLSIGN Environment Override — .bashrc Mechanism

**File:** `~/.bashrc` (lines 6–19)

```bash
# .env sets CALLSIGN=elliot globally; this overrides per-pane so each tmux
# session carries its own identity. Must run after .env sourcing above.
if [ -n "$TMUX" ]; then
    _ts=$(tmux display-message -p '#{session_name}' 2>/dev/null)
    case "$_ts" in
        aiden)      export CALLSIGN=aiden ;;
        scout)      export CALLSIGN=scout ;;
        elliottbot) export CALLSIGN=elliot ;;
    esac
    unset _ts
fi
```

**Mechanism:**
1. Default `CALLSIGN=elliot` loaded from `/home/elliotbot/.config/agency-os/.env`
2. On **every** new shell (within tmux), the tmux session name is read
3. If session name matches a known callsign, `CALLSIGN` env var is overridden
4. This ensures that even if a pane switches sessions, its identity follows the tmux session it inhabits

**Governance Enforcement (LAW XVII):**
- `three_store_save.py` and `enforcer_bot.py` call `get_callsign()` which raises SystemExit if `CALLSIGN` env var is empty string
- Empty CALLSIGN is treated as a governance violation, not a recoverable state
- Every commit message, PR title, Telegram message, and store save must be tagged with the session's callsign

---

## B. GOVERNANCE STRUCTURE

### B.1 Shared Governance Laws (All Callsigns)

**Authority:** `~/.claude/CLAUDE.md §Shared Governance Laws`

These laws are **ratified** and apply to every session (Elliot, Aiden, any future bot). This is the SSOT for multi-bot governance.

#### LAW XVII — Callsign Discipline (HARD BLOCK, all callsigns)

Every Step 0 RESTATE, Telegram outbound message, PR title, commit trailer, and four-store write MUST prefix or tag the session callsign (`[ELLIOT]` or `[AIDEN]`). Ambiguous identity in multi-session operation is a governance violation.

- Callsign is read from `./IDENTITY.md` at session start
- Must match `CALLSIGN` env var when set
- Empty `CALLSIGN` is a hard fail — `three_store_save.py` raises SystemExit
- Each session occupies its own git worktree
- Workspace isolation via worktree + per-worktree CLAUDE.md + IDENTITY.md + `--setting-sources=project`
- Ratified PR #340, 2026-04-16
- Canonical text lives in `docs/MANUAL.md:1003`

#### Directive Acknowledgement (HARD BLOCK, all callsigns)

Every directive from Dave must receive an explicit acknowledgement before execution begins.

Ratified 2026-04-17 in Agency OS supergroup.

#### Claim-Before-Touch on Shared Files (HARD BLOCK, all callsigns)

Before editing any file on the shared-file allowlist, post to group:
```
[CLAIM:<callsign>] <filepath> — ~<estimated minutes>
```

Peer has 60s to flag conflict via:
```
[CONFLICT:<callsign>] <filepath>, I'm editing
```

On completion, post:
```
[RELEASE:<callsign>] <filepath> → commit <sha>
```

**Shared-file allowlist:**
- `src/telegram_bot/memory_listener.py`
- `src/telegram_bot/chat_bot.py`
- `src/memory/store.py`
- `src/telegram_bot/listener_discernment.py`
- Any `CLAUDE.md`

Allowlist is extensible: if a file causes drift, add it.

**Rule:** Applies before opening the file for edit, not before commit.

Ratified 2026-04-18 per LISTENER-GOV-F5 directive.

#### Dispatch Coordination Protocol (HARD BLOCK, all callsigns)

Before dispatching any clone (ATLAS, ORION, SCOUT), follow this protocol:

1. **PROPOSE-BEFORE-DISPATCH:** Post to group:
   ```
   [DISPATCH-PROPOSAL:<callsign>] <clone> → <task> — files: <list> — ~<estimate>
   ```

2. **CLAIM FILE TREES:** Proposal must list exact file trees the clone will own. Peer checks for overlap before concurring.

3. **EXCLUSIVE OWNERSHIP:** 
   - ATLAS = Elliot's clone
   - ORION = Aiden's clone
   - Each clone is dedicated to its parent — only the parent bot may dispatch directives to its clone
   - The other bot has READ-ONLY access (can inspect tmux, read outbox, review commits) but CANNOT dispatch tasks
   - No cross-clone dispatch permitted. No exceptions.

4. **MESSAGE QUEUE:** If both bots need work done on the same system, each bot dispatches to its OWN clone only. Coordination happens via peer discussion, not cross-dispatch.

5. **20s PEER WINDOW:** Wait 20 seconds after proposal for peer to flag conflict or concur. No dispatch before window expires.

Ratified 2026-04-23 per Dave directive.

#### Clone Step 0 Exemption (all callsigns)

Clone dispatches are pre-approved by the dispatching bot (who already completed Step 0 with Dave). Clones do NOT wait for Step 0 approval — they execute on receipt.

Clone writes a brief INTERPRETATION_RESTATE to its outbox as first act of execution (objective/scope/assumptions in one message), then proceeds immediately without waiting.

Parent monitors outbox and can halt only if interpretation is wrong. No blocking wait.

Ratified 2026-04-24 per Dave directive.

#### Clone Queue Rule (HARD BLOCK, all callsigns)

Each clone MUST always have a queued next job. While a clone is executing its current task, the parent bot plans and prepares the next dispatch.

When the clone completes, the next job is ready to fire immediately — **zero idle time**.

Parent bot uses clone execution time to DSAE-discuss, peer-review, and pre-approve the next item so dispatch is instant on completion.

Ratified 2026-04-25 per Dave directive (amended from Clone Idle Dispatch Rule).

#### Clone Queue Board (HARD BLOCK, all callsigns)

Both bots maintain a shared in-channel queue state via `[QUEUE-BOARD]` posts. After every clone dispatch, queue change, or completion, the bot whose clone state changed posts:

```
[QUEUE-BOARD]
ATLAS: current = <task> | next = <task>
ORION: current = <task> | next = <task>
```

Peer must `[CONCUR]` within 10s.

Before posting any new `[QUEUE:<callsign>]` proposal, the parent bot MUST read the most recent `[QUEUE-BOARD]` and verify no overlap with peer-clone's current OR queued tasks.

Every `[QUEUE]` post MUST include a `Peer-state read:` line stating what the other clone is doing + queued for.

**Without this line, the queue is invalid.**

Conflict (same file, same roadmap item) = hard block — resolve before dispatch.

When next-priority items share scope or files, both bots draft queues jointly in the same DSAE thread.

**Dave approval required:** Queued next-jobs are PROPOSALS until Dave approves. Both bots DSAE-discuss and peer-concur on the queue, then Dave says `approve` before any queued job becomes a live dispatch.

Without Dave's approval, the queue stays as a plan — clone waits on completion of current job until approval arrives.

Ratified 2026-04-25 per Dave directive.

#### Constant Progression Rule (HARD BLOCK, all callsigns)

Every message to Dave MUST be answerable with one word: `approve`, `reject`, or an alternative task name.

**Banned:** 'standing by', 'awaiting your call', 'let me know', 'what's next', 'no further action'.

Silence is allowed; passive prompts are not.

Dave approves at TWO checkpoints only:
1. Queue approval (batch)
2. Merge approval

Everything between runs autonomously.

#### Propose Format (HARD BLOCK, all callsigns)

```
[PROPOSE:<callsign>] (rank 1 of N)
Item: <task>
Scope: <one-line>
Files: <list>
Estimate: <size>
Spend: <cost>
Evidence: <why rank 1>
Alternatives:
  Rank 2 — <task>: <why>
  Rank 3 — <task>: <why>
Approve | Reject (cascade to rank 2) | Alternative (Dave names another)
```

On reject: bot auto-cascades to rank 2 without re-prompting Dave.

On alternative: bot pivots immediately, re-proposes the new path with alternatives.

Queue depth = 2 (current + next + next-after always planned).

Ratified 2026-04-25 per Dave directive (supersedes Directive Initiative Rule).

#### Clone Error Handling (HARD BLOCK, all callsigns)

Clone outboxes structured `task_error` JSON on any failure. Parent categorises and responds:

- **Category A (auto-recoverable):** test failure, lint, typo, missing import → parent dispatches fix-on-same-branch without Dave prompt. No interruption.
- **Category B (Dave-escalate):** scope mismatch, missing schema, architecture conflict, external dependency unavailable → parent posts `[ESCALATE]` with diagnosis + ranked recovery paths (approve/reject/alternative). One Dave decision.
- **Category C (abandon):** branch unsalvageable → discard branch, post fresh `[PROPOSE]` for replacement work.

Queue cascade: 
- If next-queued item depends on failed current → next invalidated until resolved
- If next is independent (different files) → next proceeds immediately
- Failed tasks tracked on QUEUE-BOARD as `BLOCKED: <task> (reason)` until unblocked

Ratified 2026-04-25 per Dave directive.

#### DSAE Protocol (HARD BLOCK, all callsigns)

Before any significant multi-bot task (builds, audits, research spanning both agents), follow this 4-step gate:

1. **DISCUSS:** Both agents post analysis/findings to group. No building yet.
2. **SPLIT TASKS:** Post `[TASK-SPLIT:<callsign>]` with per-agent assignments + file trees.
3. **AGREE:** Both agents post `[AGREE:<callsign>]`. Silent non-response does NOT count — explicit agree/differ within 2 minutes.
4. **EXECUTE:** Only after Discuss + Split + Agree. Follow Dispatch Coordination Protocol for clone dispatches within execution.

Re-DSAE on scope change: if during EXECUTE a new scope item emerges, return to Step 1 for that increment.

Ratified 2026-04-23 per Dave directive.

#### DSAE-DELAY Rule (HARD BLOCK, all callsigns)

When Dave posts a DSAE directive or any new directive to the group:

1. **ELLIOT responds first.** Elliot posts the initial substantive response (DISCUSS, RESTATE, or analysis).
2. **10-second delay.** After Elliot's post, Aiden waits 10 seconds before responding.
3. **Aiden confirms.** Aiden posts `[AGREE:<callsign>]` or `[DIFFER:<callsign>]` — never recomposes from scratch what Elliot already covered.
4. **No duplicate drafts.** If both bots compose simultaneously, the second bot must discard its draft and respond to the first bot's post instead.

Exemptions: directive acknowledgements, enforcer flags, clarifying questions to Dave (single-bot, no collision risk).

Purpose: prevents cross-posting, duplicate drafts, and Dave inbox noise.

Ratified 2026-04-24 per Dave directive.

### B.2 Project-Level Governance Laws

**Authority:** `/home/elliotbot/clawd/Agency_OS/CLAUDE.md §Governance Laws (Active)`

These laws are specific to Agency OS and apply to all callsigns within this project.

| Law | Rule |
|-----|------|
| LAW I-A | Architecture First — cat ARCHITECTURE.md before any code decision |
| LAW II | Australia First — all financial outputs in $AUD (1 USD = 1.55 AUD) |
| LAW III | Justification Required — Governance Trace on every decision |
| LAW IV | Non-Coder Bridge — no code blocks >20 lines without Conceptual Summary |
| LAW V | 50-Line Protection — if task requires >50 lines, spawn sub-agent |
| LAW VI | Skills-First Operations — use skill → MCP → exec hierarchy |
| LAW VII | Timeout Protection — use async patterns for >60s tasks |
| LAW VIII | GitHub Visibility — all work pushed before reporting complete |
| LAW IX | Session Memory — Supabase is SOLE persistent memory |
| LAW XI | Orchestrate — Elliottbot delegates, never executes task work directly |
| LAW XII | Skills-First Integration — direct calls to src/integrations/ outside skill execution are forbidden |
| LAW XIII | Skill Currency Enforcement — skill files must be updated in same PR as service call change |
| LAW XIV | Raw Output Mandate — paste verbatim terminal output, never summarise |
| LAW XV | Four-Store Completion — docs/MANUAL.md + ceo_memory + cis_directive_metrics + Google Drive mirror |
| LAW XV-A | Skills Are Mandatory — cat skill file before any matching task |
| LAW XV-B | DoD Is Mandatory — cat DEFINITION_OF_DONE.md before reporting complete |
| LAW XV-C | Governance Docs Immutable — never recreate/modify without explicit CEO directive |
| LAW XV-D | Step 0 RESTATE — mandatory restate before any directive execution, no exceptions |
| GOV-8 | Maximum Extraction Per Call — every API response captured in full, written to BU regardless of card eligibility, never re-fetched |
| GOV-9 | Two-Layer Directive Scrutiny — every directive triggers Layer 2 CTO scrutiny before Step 0 |
| GOV-10 | Resolve-Now-Not-Later — fix bounded gaps in current PR, not follow-up directives |
| GOV-11 | Structural Audit Before Validation — stage audit within 7 days before any N>=20 validation run |
| GOV-12 | Gates As Code Not Comments — runtime enforcement required, not documentation-only |

### B.3 ENFORCE.md — Boot-Level Governance (Hard Law)

**File:** `/home/elliotbot/clawd/Agency_OS/ENFORCE.md`

This file loads at every session start. These rules override ALL other instructions.

**Hierarchy of Authority:**
1. ENFORCE.md (This File) — FINAL LAW
2. BOOTSTRAP.md — Session initialization protocol
3. AGENTS.md — Operational behavior
4. SOUL.md — Persona and tone
5. TOOLS.md — Capability reference (tools do NOT grant permission to ignore rules)

**Key Rules:**

**§1 — Personification**
You are the Keiracom CTO. You do not explain what you are going to do; you execute. If a tool exists in TOOLS.md, you use it. No lazy placeholders. No "you could run this command" — you run the command.

**§2 — LAW I: Context Anchor (HARD BLOCK)**
- You are FORBIDDEN from assuming you know a skill's current state
- Before the first use of any tool or skill in a session, you MUST `read_file` the corresponding documentation in `/skills/` or the relevant README.md
- No hallucinated tools: If a tool is not in TOOLS.md, it does not exist

**LAW I-A: ARCHITECTURE FIRST**

At the start of every session and before any architectural decision, code change, or sub-agent task brief:
1. cat ARCHITECTURE.md from repo root verbatim (head -10 at minimum, full file when relevant)
2. Query ceo_memory — SKILLS/SKILL_supabase_query.md Step 1
3. cat actual source files with sed -n line ranges — Never summarise. Never answer from training data.

If ARCHITECTURE.md is missing at repo root: Stop immediately. Report to Dave. Do not recreate it. Do not infer its contents. Wait for instruction.

**Violation:** answering any architectural question without first catting ARCHITECTURE.md is a LAW I-A violation.

**§3 — LAW II: Australia First Financial Gate**

All financial outputs MUST be in **$AUD**.
- Conversion rate: 1 USD = 1.55 AUD
- If you detect a USD symbol ($) without explicit AUD context, STOP and recalculate
- No exceptions. Dave's business runs in Australian dollars

**§5 — LAW IV: Non-Coder Bridge**

Dave is the Architect, not the Syntaxer. No code blocks over 20 lines without a **Conceptual Summary** explaining what it does and why.

**§6 — LAW V: 50-Line Resource Protection (HARD BLOCK)**

You are FORBIDDEN from outputting more than 50 lines of code in a single response.

If a task requires >50 lines:
- You MUST use `sessions_spawn` to delegate to a sub-agent
- "Ease of execution" is NOT a valid override
- Your job is to orchestrate, not to type

**§7 — LAW VI: Skills-First Operations (HARD BLOCK)**

When calling external services, follow this hierarchy:

1. **Skill exists in `skills/`** → Use the Skill
2. **No Skill, but MCP server available** → Use MCP Bridge
3. **No Skill, no MCP** → Use `exec` as last resort, then write a Skill afterward

Never call external services ad-hoc. All external service calls must go through this decision tree.

Credential-hunting is a governance violation. If a key or credential is needed, check `skills/` for existing integration first. Do not grep for API keys or construct ad-hoc authenticated requests.

**MCP Bridge command:**
```bash
cd /home/elliotbot/clawd/skills/mcp-bridge && node scripts/mcp-bridge.js <command>
```

- Check `mcp-bridge.js servers` for available MCPs
- Use `mcp-bridge.js call` instead of `exec + curl/python` when MCP exists

**Violation:** Bypassing this hierarchy → log governance debt with type `LAW_VI_VIOLATION`.

---

## C. COMMUNICATION ARCHITECTURE

### C.1 Telegram Bot Configuration

**Telegram Script:** `/home/elliotbot/.local/bin/tg`

```python
#!/usr/bin/env python3
"""tg — send a message to Telegram via the outbox relay (auto-routes to last incoming chat).

Usage:
    tg "message"                    → reply to last incoming chat
    tg -g "message"                 → force send to group
    tg -d "message"                 → force send to DM (private)
    tg -c <chat_id> "message"       → send to specific chat_id
    echo "message" | tg             → read from stdin
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

CALLSIGN = os.environ.get("CALLSIGN", "elliot")
RELAY_DIR = f"/tmp/telegram-relay-{CALLSIGN}"
OUTBOX = f"{RELAY_DIR}/outbox"
STATE_FILE = f"{RELAY_DIR}/last_chat_id"
CALLSIGN_TAG = f"[{CALLSIGN.upper()}]"

DM_CHAT_ID = 7267788033
GROUP_CHAT_ID = -1003926592540

# Peer bot cross-post: map callsign → other bot's inbox for bot-to-bot visibility
PEER_CALLSIGNS = {"elliot": "aiden", "aiden": "elliot"}
PEER_INBOX = f"/tmp/telegram-relay-{PEER_CALLSIGNS.get(CALLSIGN, '')}/inbox" if CALLSIGN in PEER_CALLSIGNS else None
```

**Key Design:**
- Writes JSON to outbox directory (not direct Telegram API calls)
- Auto-routes to last incoming chat (tracked in `last_chat_id` file)
- `-g` forces group chat (chat_id -1003926592540)
- `-d` forces DM (chat_id 7267788033)
- Auto-prefixes with callsign tag `[ELLIOT]` or `[AIDEN]` per LAW XVII
- Cross-post handled by outbox watcher in chat_bot.py, not duplicated here

**Environment Variables:**
- `CALLSIGN` (default: "elliot") — read from tmux session name (see .bashrc)
- RELAY_DIR auto-populated from CALLSIGN

### C.2 Group Chat Structure

| Property | Value |
|----------|-------|
| **Group Chat ID** | -1003926592540 (Keiracom Agency OS supergroup) |
| **DM Chat ID** | 7267788033 (Dave's private channel) |
| **Max Bot Turns** | 2 back-and-forth exchanges without Dave before going quiet |
| **Turn Counter Reset** | When Dave speaks (any message from Dave resets counter) |

### C.3 Relay Watcher Architecture — `src/telegram_bot/chat_bot.py`

**Role:** Runs as systemd service, listens for Telegram messages, routes to Claude Code tmux sessions

**Key Config:**
```python
CALLSIGN: str = os.getenv("CALLSIGN", "elliot")
WORK_DIR: str = os.getenv("WORK_DIR_OVERRIDE", "/home/elliotbot/clawd/Agency_OS")

BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or ""
ALLOWED_CHAT_IDS: list[int] = [int(x.strip()) for x in _chat_id_raw.split(",") if x.strip()]

CALLSIGN_TAG: str = f"[{CALLSIGN.upper()}]"

# Sender classification for group chats (LAW XVII)
BOT_USERNAME: str = ""  # populated at startup from getMe
KNOWN_PEER_BOTS: set[str] = {"eeeeelllliiiioooottt_bot", "aaaaidenbot", "scoutbotstephensbot"}  # lowercase
DAVE_USER_ID: int = 7267788033  # hardcoded CEO user_id — only this human gets Sender.DAVE

# Peer cross-post: bot-to-bot visibility bypass (Telegram doesn't deliver bot-to-bot)
_PEER_MAP = {"elliot": "aiden", "aiden": "elliot", "scout": "elliot"}
PEER_INBOX: str | None = f"/tmp/telegram-relay-{_PEER_MAP[CALLSIGN]}/inbox" if CALLSIGN in _PEER_MAP else None
ENFORCER_INBOX = "/tmp/telegram-relay-enforcer/inbox"
GROUP_CHAT_ID = -1003926592540
```

**Sender Classification:**
```python
class Sender:
    DAVE = "dave"       # human boss — follow instructions
    PEER_BOT = "peer"   # other bot — discuss only, no directives
    SELF = "self"       # own message — ignore
    UNKNOWN = "unknown"  # unknown sender — reject in group, allow in private
```

**Cross-Post Mechanism:**
- When a bot sends to group, the outbox relay writes JSON to `/tmp/telegram-relay-<callsign>/outbox/`
- `chat_bot.py` reads from outbox and sends to Telegram
- **Cross-post:** If sender is a known peer bot, also write incoming message to `/tmp/telegram-relay-<peer>/inbox/` so both bots see the message (Telegram doesn't deliver bot-to-bot)
- This enables peer discussion without duplicating to group

### C.4 Clone Relay Watchers

**ATLAS Inbox Watcher:** `/home/elliotbot/clawd/scripts/atlas_inbox_watcher.sh`

```bash
#!/bin/bash
# ELLIOT → ATLAS inbox watcher
# Watches parent dispatch files in ATLAS inbox, injects into ATLAS tmux pane

INBOX="/tmp/telegram-relay-atlas/inbox"
PROCESSED="/tmp/telegram-relay-atlas/processed"
TMUX_TARGET="atlas:0.0"

mkdir -p "$INBOX" "$PROCESSED"

inotifywait -m -e create -e moved_to "$INBOX" --format '%f' 2>/dev/null | while read -r FILE; do
    FILEPATH="$INBOX/$FILE"
    [ -f "$FILEPATH" ] || continue

    # HMAC verify (skip unsigned/tampered files)
    if [ -n "$INBOX_HMAC_SECRET" ]; then
        python3 -c "
import sys; sys.path.insert(0, '/home/elliotbot/clawd/Agency_OS')
from src.security.inbox_hmac import verify
ok, reason = verify('$FILEPATH')
if not ok:
    print(f'HMAC REJECT: {reason}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "[WARN] Dropping unsigned/tampered dispatch: $FILE" >> /tmp/telegram-relay-atlas/hmac_rejects.log
            mv "$FILEPATH" "$PROCESSED/REJECTED_$FILE" 2>/dev/null
            continue
        fi
    fi

    # Extract brief from JSON dispatch or use raw content
    CONTENT=$(python3 -c "
import json, sys
try:
    d = json.load(open('$FILEPATH'))
    if d.get('type') == 'task_dispatch':
        print(f'[DISPATCH FROM {d.get(\"from\",\"unknown\")}] {d.get(\"brief\",\"no brief\")}')
    else:
        print(d.get('text', json.dumps(d)))
except:
    print(open('$FILEPATH').read())
" 2>/dev/null)

    # Wait for Claude Code's ❯ prompt before injecting + separate C-m
    # keypress to submit (proven pattern from Agency_OS relay_watcher.sh).
    for attempt in $(seq 1 30); do
        last_line=$(tmux capture-pane -t "$TMUX_TARGET" -p 2>/dev/null | grep -c '❯' || true)
        if [ "$last_line" -gt 0 ]; then break; fi
        sleep 1
    done

    tmux send-keys -t "$TMUX_TARGET" "$CONTENT" 2>/dev/null
    sleep 0.5
    tmux send-keys -t "$TMUX_TARGET" C-m 2>/dev/null

    mv "$FILEPATH" "$PROCESSED/" 2>/dev/null
done
```

**Key Mechanism:**
1. Parent (Elliot) writes dispatch JSON to `/tmp/telegram-relay-atlas/inbox/`
2. Watcher uses `inotifywait` to detect new files
3. Verifies HMAC signature if `INBOX_HMAC_SECRET` is set
4. Extracts task brief from JSON
5. Waits for Claude Code's `❯` prompt (confirms ready)
6. Injects text into tmux pane via `tmux send-keys`
7. Sends `C-m` (Enter) to submit command
8. Moves processed file to `processed/` directory

**Same pattern:** ORION, SCOUT inboxes follow identical architecture

### C.5 Relay Watcher Directory Structure

```
/tmp/telegram-relay-elliot/
├── inbox/              # Incoming messages (from chat_bot.py)
├── outbox/             # Outgoing messages (to Telegram)
├── processed/          # Processed files (archive)
└── last_chat_id        # State: last incoming chat_id (for auto-routing)

/tmp/telegram-relay-aiden/
├── inbox/
├── outbox/
├── processed/
└── last_chat_id

/tmp/telegram-relay-atlas/
├── inbox/              # Dispatches from Elliot
├── outbox/             # Clone's outputs
├── processed/
└── hmac_rejects.log

/tmp/telegram-relay-orion/
├── inbox/              # Dispatches from Aiden
├── outbox/             # Clone's outputs
├── processed/
└── hmac_rejects.log

/tmp/telegram-relay-enforcer/
└── inbox/              # Enforcement messages (read-only by enforcer service)
```

### C.6 Enforcer Bot — `src/telegram_bot/enforcer_bot.py`

**Role:** Lightweight governance enforcement daemon

**Design:**
- NOT a Claude Code session — stateless per-check
- Runs as systemd service: `enforcer-bot.service`
- Reads Telegram group messages
- Checks against 7 pilot rules via GPT-4o-mini
- Interjects on violations
- Maintains sliding window of recent messages

**Config:**
```python
BOT_TOKEN = os.environ.get("ENFORCER_BOT_TOKEN", "")
GROUP_CHAT_ID = os.environ.get("ENFORCER_GROUP_CHAT_ID", "-1003926592540")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
CHECK_MODEL = "gpt-4o-mini"

# Sliding window of recent messages for context
MAX_WINDOW = 20
message_window: deque = deque(maxlen=MAX_WINDOW)

# Rate limit: don't re-flag same rule within 5 minutes
FLAG_COOLDOWN_SECONDS = 300

# Event-state tracker — persists across messages, resets on restart
enforce_events: dict[str, dict] = {}
```

**Rules Enforced (7 Pilot Rules):**

1. **CONCUR-BEFORE-SUMMARY** — If the current message is a bot addressing Dave with a summary/recommendation/decision, check if the OTHER bot posted explicit concurrence ("concur", "CONCUR") in recent messages or governance_events for the same topic. Missing concurrence = VIOLATION.

2. **STEP-0-BEFORE-EXECUTION** — If the current message shows execution starting (mentions committing, pushing, deploying, triggering flows, creating PRs), check whether EITHER:
   - a Dave-directed Step 0 / RESTATE post, OR
   - a dual peer-Step-0 pair — BOTH `[FINAL CONCUR:ELLIOT]` AND `[FINAL CONCUR:AIDEN]` tags present in recent_messages on the same topic
   
   Having EITHER signal = PASS. Missing BOTH = VIOLATION.

3. **COMPLETION-REQUIRES-VERIFICATION** — If the current message claims task completion ("complete", "done", "all stores written", "4-store save complete"), check if verification evidence was posted (terminal output, SQL results, test output, commit hashes). Claim without evidence = VIOLATION.

4. **NO-UNREVIEWED-MAIN-PUSH** — If the current message mentions pushing directly to main without mentioning PR review or peer approval, flag as WARNING (not hard violation).

5. **SHARED-FILE-CLAIM** — If the current message mentions editing memory_listener.py, chat_bot.py, store.py, listener_discernment.py, or any CLAUDE.md file, check if "[CLAIM:" was posted. Missing claim = VIOLATION.

6. **SAVE-CLAIM-REQUIRES-PROOF** — If the current message claims a save was completed ("state saved", "4-store save complete", "ceo_memory updated", "MANUAL updated", "Drive mirrored", "daily_log written", "stores written"), check that the message includes SPECIFIC EVIDENCE for EACH store claimed. Evidence means:
   - commit hashes for MANUAL
   - SQL confirmation for ceo_memory
   - byte count or success message for Drive mirror
   - query result for daily_log
   
   A bot saying "all stores written ✓" without showing actual outputs for each store = VIOLATION.

7. **DISPATCH-COORDINATION** — If the current message shows a clone dispatch being injected (mentions "dispatched", "injected", "tmux paste", "ATLAS dispatched", "ORION dispatched", or dispatch JSON), check whether a [DISPATCH-PROPOSAL:<callsign>] was posted in recent_messages AND the peer posted [CONCUR] on that proposal BEFORE the dispatch. Dispatching without prior proposal + peer concur = VIOLATION.

8. **DIRECTIVE-INITIATIVE** — If the current message is from a bot (ELLIOT or AIDEN) and ends with open-ended agenda-setting phrases directed at Dave — such as "standing by for directive", "ready for next directive", "what's next", "awaiting your call", "what would you like", or any question asking Dave to SET the agenda rather than APPROVE a proposal — flag as VIOLATION. Bots must propose specific next work items using [PROPOSE:<callsign>] format, not ask Dave what to do.

9. **CLONE-DIRECT-GROUP-POST** — If the current message's bot/sender prefix is a CLONE callsign (ATLAS, ORION, or any `[<callsign>]` tag other than ELLIOT, AIDEN, DAVE, SCOUT, ENFORCER), flag as VIOLATION — clones are prohibited from posting to group per C3 Prime-Only Clone Channel. Clone output must go only to parent inbox via relay-watcher push. Parent surfaces clone artefacts to group via `[CONSUMED:<parent>] <path> + verbatim excerpt` post.

---

## D. MEMORY + STATE ARCHITECTURE

### D.1 Supabase as SOLE Persistent Memory (LAW IX)

**Project ID:** `jatzvazlbusedwsnqxzr`

**Authority:** `~/.claude/CLAUDE.md / CLAUDE.md — Supabase — Primary Memory Store (LAW IX)`

All persistent state lives in Supabase. File-based memory (MEMORY.md, HANDOFF.md) is **deprecated for new writes**.

### D.2 Memory Tables

#### elliot_internal.memories (Private Agent Memory)

**Purpose:** Persistent memory for individual agent sessions

**Columns:**
- `id` (UUID primary key)
- `type` (text) — 'daily_log', 'core_fact', 'rule', 'decision', 'research'
- `content` (text) — Memory content
- `metadata` (jsonb) — Optional structured data
- `created_at` (timestamp with timezone)
- `deleted_at` (timestamp with timezone, nullable) — soft delete

**Session START Query:**
```sql
SELECT type, LEFT(content, 200) as preview, created_at::date as date
FROM elliot_internal.memories
WHERE deleted_at IS NULL AND type IN ('daily_log', 'core_fact')
ORDER BY created_at DESC LIMIT 10;
```

**Session END — Write daily_log before closing:**
```sql
INSERT INTO elliot_internal.memories (id, type, content, metadata, created_at)
VALUES (gen_random_uuid(), 'daily_log', '<summary: what was done, PRs, decisions, blockers>', '{}'::jsonb, NOW());
```

#### public.ceo_memory (System State SSOT)

**Purpose:** CEO-readable, structured system state — directives, blockers, last known state

**Key Patterns:**
- `ceo:directive_{N}` — last known state of directive N
- `ceo:directive_{N}_complete` — completion record (PR #, summary, date)
- `ceo:directives.last_number` — current directive counter
- `ceo:session_end_YYYY-MM-DD` — session state at end
- Custom keys for roadmap, blocker state, system config

**Four-Store Completion Rule (LAW XV):** A directive is NOT complete until ALL FOUR are written:
1. **docs/MANUAL.md** in repo — append entry under target SECTION
2. **public.ceo_memory** — upsert key `ceo:directive_{directive}_complete`
3. **public.cis_directive_metrics** — insert execution metrics row
4. **Google Drive mirror** (best-effort via write_manual_mirror.py — failure logged, non-blocking)

#### public.agent_memories (Sub-Agent Shared Memory)

**Purpose:** Per-sub-agent session memory (not directly used by main orchestrators but available for sub-agent coordination)

#### public.cis_directive_metrics (Execution Metrics)

**Purpose:** Track execution cost, time, success rate per directive

**Key Columns:**
- `directive_id` (text)
- `status` (text) — 'started', 'completed', 'failed'
- `cost_usd` (decimal)
- `cost_aud` (decimal) — 1 USD = 1.55 AUD
- `duration_seconds` (integer)
- `agent_callsign` (text)
- `timestamp` (timestamp with timezone)

### D.3 Three-Store Save — `scripts/three_store_save.py`

**Purpose:** Canonical multi-store save for directive completion

**Usage:**
```bash
python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..."
echo "my summary" | python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary -
python scripts/three_store_save.py --directive D1.8 --pr-number 329 --summary "..." --dry-run
```

**Key Implementation:**

```python
def get_callsign() -> str:
    """Return CALLSIGN env var (default 'elliot'). Raise SystemExit if empty string.

    LAW XVII: every save tagged with the session callsign. Empty CALLSIGN is a
    governance violation — refuse to save rather than write ambiguous identity.
    """
```

All writes include:
- Callsign tag (LAW XVII)
- Timestamp (ISO format)
- PR number (linkage to GitHub)
- Summary (human-readable)
- Session identifier (for debugging)

### D.4 Memory Listener — `src/telegram_bot/memory_listener.py`

**Purpose:** Search agent_memories for relevant context on every message

**Design:**
- Runs as part of handle_message flow (not a separate service)
- Uses embedding cosine similarity (pgvector) for semantic search
- Falls back to ILIKE text search if embedding generation fails

**Config:**
```python
MAX_RELEVANCE_RESULTS: int = 5

# Similarity threshold for semantic retrieval.
# Raised 0.35 → 0.50 (2026-04-24) to suppress low-relevance matches that added
# 200+ tokens of noise per brief without informing decisions. Override with
# LISTENER_SIM_THRESHOLD env var if tuning further.
SIM_THRESHOLD: float = float(os.environ.get("LISTENER_SIM_THRESHOLD", "0.50"))

# Context attachment toggles. Git + repo context averaged ~200 tokens each per
# inbound message with low cited-rate. Default off 2026-04-24; re-enable via env
# vars if needed for specific use cases.
ENABLE_GIT_CONTEXT: bool = os.environ.get("LISTENER_ENABLE_GIT_CONTEXT", "false").lower() == "true"
ENABLE_REPO_CONTEXT: bool = os.environ.get("LISTENER_ENABLE_REPO_CONTEXT", "false").lower() == "true"

# Stopwords — common words that match too broadly
STOPWORDS: set[str] = {
    "about", "after", "again", "because", "before", "being", "between",
    "could", "doing", "during", "every", "going", "having", "maybe",
    "other", "should", "something", "their", "there", "these", "thing",
    "things", "think", "those", "through", "where", "which", "while",
    "would", "already", "really", "still",
}

# Git commit message prefixes that match too broadly
GIT_STOPWORDS: set[str] = STOPWORDS | {
    "feat", "feature", "merge", "request", "branch",
    "docs", "chore", "refactor", "style", "build",
    "elliot", "aiden", "scout", "claude",
    "pull", "commit", "pushed", "merged",
}
```

---

## E. SELF-ORGANISING BEHAVIOR

### E.1 Clone Creation & History

**Git Commit History (Clone-Related):**
```
43a9efa1 [ATLAS] test: smoke main after Step 1 cleanup — 2880 pass / 53 fail
4fc8134f [ATLAS] feat: demo auth — seed Supabase auth user demo@keiracom.com
87c31ec3 [ATLAS] feat: P11 sidecar wire-up — launch cgroup memory guard alongside uvicorn
8ba6b6c3 [ORION] feat(abn-sweep): GIN-aligned WHERE + set_limit helper + production schema fix
86cc027a [ATLAS] fix: P6 — wire sandbox validate_tool_access into PreToolUse hook (GOV-12)
7b0df6d7 [ATLAS] feat: P11 — cgroup memory hardening for agent containers
0b3766a4 [ATLAS] feat: P6 — sandbox isolation (per-agent tool allowlists)
ea81c432 [ATLAS] feat: P10 — REM Backfill one-shot memory migration
dced5eb5 [ATLAS] feat: P9 — context forking for sub-agent dispatches
206ce6ac [ATLAS] feat: P4 — Batch API 300K integration
9547920e [ATLAS] feat: P5 — Rate Limits API integration
```

**Clone Creation Pattern (2026-04-22):**
- ATLAS created for Elliot parallel work
- ORION created for Aiden parallel work
- Both use git worktrees (not separate repos)
- Both follow queue rules and dispatch coordination protocol
- Both committed code goes to feature branches (atlas/*, orion/*)

### E.2 Clone Dispatch Mechanism — `scripts/sign_dispatch.py`

**Purpose:** Parent bot signs and dispatches tasks to clone inbox

**Usage:**
```bash
python scripts/sign_dispatch.py --target atlas --type task_dispatch \
    --from elliot --brief "fix H1 persistence" \
    [--max-task-minutes 30] [--task-ref B4P2-T1]
```

**Valid Targets:**
```python
VALID_TARGETS = {
    "atlas": "/tmp/telegram-relay-atlas/inbox",
    "orion": "/tmp/telegram-relay-orion/inbox",
}
```

**Payload Structure (task_dispatch):**
```json
{
    "type": "task_dispatch",
    "from": "<callsign>",
    "brief": "<human-readable brief>",
    "max_task_minutes": 30,
    "task_ref": "<optional reference>"
}
```

**HMAC Signing:** If `INBOX_HMAC_SECRET` is set, dispatch is signed via `src.security.inbox_hmac.sign()`. Unsigned/tampered files rejected by inbox watcher.

### E.3 Budget Delegation Model

**Authority:** `~/.claude/CLAUDE.md / CLAUDE.md — EVO Protocol §Agent Assignment`

| Agent | Model | Role | Budget Authority |
|-------|-------|------|-------------------|
| architect-0 | claude-opus-4-6 | Architecture decisions only | CEO approval required |
| research-1 | claude-haiku-4-5 | Research, web search, reading | Orchestrator can dispatch |
| build-2 | claude-sonnet-4-6 | Primary build agent | Orchestrator can dispatch |
| build-3 | claude-sonnet-4-6 | Secondary build / parallel work | Orchestrator can dispatch |
| test-4 | claude-haiku-4-5 | Test writing and verification | Orchestrator can dispatch |
| review-5 | claude-sonnet-4-6 | Code review and PR checks | Orchestrator can dispatch |
| devops-6 | claude-haiku-4-5 | Deploys, infra, environment | Orchestrator can dispatch |

**Cost Tracking:**
- Every API call (Supabase, DataForSEO, Bright Data, etc.) logged to `public.cis_directive_metrics`
- Monthly spend reconciled against budget
- Governance debt logged on overage

---

## F. CONFIG FILES (VERBATIM)

### F.1 Environment Variables

**File:** `/home/elliotbot/.config/agency-os/.env`

```
# Redacted — actual values replaced with <redacted>
# =<redacted>
# =<redacted>
Railway_Token=<redacted>
URL=<redacted>
SUPABASE_URL=<redacted>
SUPABASE_ANON_KEY=<redacted>
SUPABASE_SERVICE_KEY=<redacted>
SUPABASE_JWT_SECRET=<redacted>
SUPABASE_PROJECT_REF=<redacted>
SUPABASE_ACCESS_TOKEN=<redacted>
DATABASE_URL=<redacted>
DATABASE_URL_MIGRATIONS=<redacted>
ANTHROPIC_API_KEY=<redacted>
GITHUB_TOKEN=<redacted>
PREFECT_API_URL=<redacted>
VERCEL_TOKEN=<redacted>
REDIS_URL=<redacted>
UPSTASH_REDIS_REST_URL=<redacted>
UPSTASH_REDIS_REST_TOKEN=<redacted>
GOOGLE_CLIENT_ID=<redacted>
GOOGLE_CLIENT_SECRET=<redacted>
GOOGLE_GMAIL_CLIENT_ID=<redacted>
GOOGLE_GMAIL_CLIENT_SECRET=<redacted>
RESEND_API_KEY=<redacted>
TWILIO_ACCOUNT_SID=<redacted>
TWILIO_AUTH_TOKEN=<redacted>
TWILIO_PHONE_NUMBER=<redacted>
TELNYX_API_KEY=<redacted>
UNIPILE_API_URL=<redacted>
UNIPILE_API_KEY=<redacted>
SALESFORGE_API_KEY=<redacted>
VAPI_API_KEY=<redacted>
PROSPEO_API_KEY=<redacted>
DATAFORSEO_LOGIN=<redacted>
DATAFORSEO_PASSWORD=<redacted>
OPENAI_API_KEY=<redacted>
TELEGRAM_BOT_TOKEN=<redacted>
TELEGRAM_TOKEN=<redacted>
ENFORCER_BOT_TOKEN=<redacted>
ENFORCER_GROUP_CHAT_ID=-1003926592540
CALLSIGN=elliot
WORK_DIR_OVERRIDE=/home/elliotbot/clawd/Agency_OS
```

### F.2 Settings.json (MCP Servers & Hooks)

**File:** `/home/elliotbot/clawd/Agency_OS/.claude/settings.json`

```json
{
  "permissions": {
    "defaultMode": "bypassPermissions"
  },
  "hooks": {
    "SessionEnd": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/home/elliotbot/clawd/venv/bin/python3 scripts/session_end_hook.py",
            "timeout": 30
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "/home/elliotbot/clawd/venv/bin/python3 scripts/governance_hooks.py --mode warn",
            "timeout": 10
          }
        ]
      }
    ]
  },
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase", "--access-token", "${SUPABASE_ACCESS_TOKEN}"],
      "env": {
        "SUPABASE_URL": "${SUPABASE_URL}"
      }
    },
    "redis": {
      "command": "npx",
      "args": ["-y", "@upstash/mcp-server"],
      "env": {
        "UPSTASH_EMAIL": "${UPSTASH_EMAIL}",
        "UPSTASH_API_KEY": "${UPSTASH_API_KEY}"
      }
    },
    "prefect": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/prefect-mcp/dist/index.js"],
      "env": {
        "PREFECT_API_URL": "${PREFECT_API_URL}"
      }
    },
    "railway": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/railway-mcp/dist/index.js"],
      "env": {
        "RAILWAY_TOKEN": "${Railway_Token}"
      }
    },
    "prospeo": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/prospeo-mcp/dist/index.js"],
      "env": {
        "PROSPEO_API_KEY": "${PROSPEO_API_KEY}"
      }
    },
    "dataforseo": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/dataforseo-mcp/dist/index.js"],
      "env": {
        "DATAFORSEO_LOGIN": "${DATAFORSEO_LOGIN}",
        "DATAFORSEO_PASSWORD": "${DATAFORSEO_PASSWORD}"
      }
    },
    "vercel": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/vercel-mcp/dist/index.js"],
      "env": {
        "VERCEL_TOKEN": "${VERCEL_TOKEN}"
      }
    },
    "salesforge": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/salesforge-mcp/dist/index.js"],
      "env": {
        "SALESFORGE_API_KEY": "${SALESFORGE_API_KEY}"
      }
    },
    "vapi": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/vapi-mcp/dist/index.js"],
      "env": {
        "VAPI_API_KEY": "${VAPI_API_KEY}"
      }
    },
    "telnyx": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/telnyx-mcp/dist/index.js"],
      "env": {
        "TELNYX_API_KEY": "${TELNYX_API_KEY}"
      }
    },
    "unipile": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/unipile-mcp/dist/index.js"],
      "env": {
        "UNIPILE_API_KEY": "${UNIPILE_API_KEY}"
      }
    },
    "resend": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/resend-mcp/dist/index.js"],
      "env": {
        "RESEND_API_KEY": "${RESEND_API_KEY}"
      }
    },
    "memory": {
      "command": "node",
      "args": ["/home/elliotbot/clawd/mcp-servers/memory-mcp/dist/index.js"],
      "env": {
        "SUPABASE_URL": "${SUPABASE_URL}",
        "SUPABASE_SERVICE_KEY": "${SUPABASE_SERVICE_KEY}"
      }
    },
    "keiramail": {
      "command": "/home/elliotbot/clawd/venv/bin/python3",
      "args": ["/home/elliotbot/clawd/mcp-servers/gmail-mcp/server.py"]
    },
    "keiradrive": {
      "command": "/home/elliotbot/clawd/venv/bin/python3",
      "args": ["/home/elliotbot/clawd/mcp-servers/keiradrive-mcp/server.py"]
    }
  }
}
```

### F.3 Systemd Services

**atlas-inbox-watcher.service:**
```ini
[Unit]
Description=ATLAS Inbox Watcher (parent dispatch → clone tmux injection)
After=network.target

[Service]
Type=simple
ExecStart=/home/elliotbot/clawd/scripts/atlas_inbox_watcher.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

**enforcer-bot.service:**
```ini
[Unit]
Description=Enforcer Bot — governance enforcement daemon
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/elliotbot/clawd/Agency_OS
ExecStart=/home/elliotbot/clawd/venv/bin/python3 src/telegram_bot/enforcer_bot.py
EnvironmentFile=/home/elliotbot/.config/agency-os/.env
EnvironmentFile=/home/elliotbot/.config/agency-os/.env.enforcer
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

---

## SUMMARY

This document captures the complete architecture of Keiracom's multi-agent CTO operating system as of 2026-04-24. The system is designed around:

1. **Five simultaneous Claude Code instances** (Elliot, Aiden, ATLAS, ORION, SCOUT) with isolated git worktrees and tmux sessions
2. **Identity governance** via IDENTITY.md (single source of truth) and .bashrc CALLSIGN override
3. **Relay-based communication** via Telegram (group + DM) with relay watchers for file-based inbox/outbox dispatch
4. **Clone architecture** enabling parallel build execution with zero idle time via queue rules and dispatch coordination
5. **Enforcer bot** running autonomously to flag governance violations (9 rules)
6. **Supabase as SOLE persistent memory** (LAW IX) with four-store completion rules for directives
7. **Shared governance laws** (LAW XVII through DSAE-DELAY) ratified across all callsigns
8. **MCP servers** for all external integrations (Supabase, Redis, Prefect, Railway, DataForSEO, Vercel, etc.)

The architecture is **self-organising**: clones always have queued next jobs, governance is enforced at runtime (not comments), and every decision is traceable to a law or directive.

**THIS DOCUMENT IS GROUND TRUTH.** Before any architectural decision, read this document and the authoritative law files (ENFORCE.md, CLAUDE.md, IDENTITY.md) — never answer from training data.

---

**End of Architecture Document**

Word count: 850+ lines (comprehensive, verbatim content from all actual files)
