# Clone Architecture — Agency OS

**Status:** Ratified 2026-04-22
**Authors:** ORION (drafted on dispatch from AIDEN)
**Audience:** Every callsign (orchestrators and clones) operating in the Agency OS multi-worktree environment.
**Scope:** Authoritative reference for the clone topology, the C1–C6 communication rules, activation, the DIRECT-BUILD exception, the exit-gate pattern, and known failure modes.

Related:
- `~/.claude/CLAUDE.md §Shared Governance Laws` — LAW XVII callsign discipline, Claim-Before-Touch, Directive Acknowledgement.
- `./CLAUDE.md` — worktree project governance.
- `./IDENTITY.md` — per-session callsign (SSOT for this session).
- `docs/clones/CLONE_LEARNINGS.template.md` — per-clone working journal template.

---

## 1. Purpose + Team Topology

### Purpose

The clone architecture separates **orchestration** from **execution**. Orchestrators decide *what* and *why*; clones execute *how*. Each role runs in its own git worktree with its own CLAUDE.md, IDENTITY.md, callsign, and Telegram plumbing, so concurrent sessions cannot collide on identity or branch state.

Goals:
- Keep the orchestrator context clean — delegate long-running build work to clones.
- Guarantee Dave never has to copy-paste between sessions.
- Enforce workspace isolation so governance violations are attributable to a single callsign.
- Make dispatch auditable — every clone task is a JSON file on disk with HMAC attestation.

### Team Diagram

```
                                     +--------+
                                     |  DAVE  |   big-things approver
                                     +---+----+
                                         |
                   Step 0 RESTATE (big things only) / ratification
                                         |
                  +----------------------+----------------------+
                  |                                             |
             +----+-----+                                 +-----+----+
             |  ELLIOT  |<-- peer concur / dual -------->|   AIDEN  |
             |  (CTO)   |    [FINAL CONCUR] tags         |  (peer)  |
             +----+-----+                                 +-----+----+
                  | dispatch (inbox.json)                       | dispatch
                  v                                             v
             +----+-----+                                 +-----+----+
             |  ATLAS   |                                 |   ORION  |
             | build-   |                                 |  build-  |
             | clone    |                                 |  clone   |
             +----------+                                 +----------+
                                         |
                                   (outbox -> parent only, never group)
                                         |
                                   +-----+-----+
                                   |   SCOUT   |  research clone
                                   +-----------+
```

Roles:

| Callsign | Role | Worktree | Talks to |
|----------|------|----------|----------|
| **Dave** | CEO, big-things approver. Ratifies laws, approves new directives, gets Step 0 RESTATE for big things. | — | Telegram group |
| **Elliot** | CTO orchestrator. Holds `main` worktree, runs `docs/MANUAL.md`, four-store saves, peer of Aiden. | `/home/elliotbot/clawd/Agency_OS` | Dave, Aiden, ATLAS (inbox), group |
| **Aiden** | Peer orchestrator. Dispatches to ORION. Peer concur on standard work. | `/home/elliotbot/clawd/Agency_OS-aiden` | Dave, Elliot, ORION (inbox), group |
| **ATLAS** | Build clone of Elliot. Executes Tier A code tasks dispatched to inbox. No group posts. | `/home/elliotbot/clawd/Agency_OS-atlas` | Elliot (outbox only) |
| **ORION** | Build clone of Aiden. Executes Tier A code tasks dispatched to inbox. No group posts. | `/home/elliotbot/clawd/Agency_OS-orion` | Aiden (outbox only) |
| **Scout** | Research clone. Read-heavy, MCP-heavy, no code commits. Returns artefacts to its parent. | `/home/elliotbot/clawd/Agency_OS-scout` | Parent (outbox only) |

Orchestrators communicate in the Telegram supergroup (chat_id `-1003926592540`). Clones **never** post to the group — their channel is parent inbox/outbox only.

---

## 2. Communication Rules C1–C6

The following rules were ratified in session on 2026-04-22. They apply to every orchestrator-clone relationship and every peer-concur exchange in the group.

### C1 — Mandatory Delegation + Runtime Gate

For any Tier A build task (multi-file, >50 lines, or touching shared-allowlist files), the orchestrator MUST dispatch to its build-clone rather than execute directly. A runtime gate in the dispatch pipeline rejects orchestrator-authored commits on a task branch that has an active inbox dispatch — the gate prevents the orchestrator from "helping" inside a clone's scope. Exception path: the DIRECT-BUILD tag (see §4) when clones are unavailable or the task is sub-tier.

### C2 — Consumption + Verbatim Proof (10 min, 200 chars)

Within **10 minutes** of a peer's Step 0 RESTATE or ratification message, the receiving callsign must post a consumption proof: a **≥200 character** verbatim quote from the source message, prefixed `[CONSUMED:<callsign>]`. The verbatim quote is evidence that the message was read, not just acknowledged. Failure to post within 10 min is a governance violation — the peer may re-dispatch or escalate to Dave. This rule exists because acknowledgements without proof degraded into reflexive "ack" replies that masked non-consumption.

### C3 — Prime-Only Clone Channel (push via relay-watcher)

Clones are reachable **only** through their parent's inbox (`/tmp/telegram-relay-<clone>/inbox/`). No Telegram DMs to clones, no group messages to clones, no tmux injection from anyone but the parent's `<clone>-inbox-watcher.service`. The inbox-watcher uses `inotifywait -m -e create` to detect new dispatch files and injects them into the clone's tmux pane via `tmux send-keys`. Outbound from clone goes through `<clone>-relay-watcher.service` which tails the clone's outbox and injects into the parent's tmux pane prefixed `[<CLONE>]`. This keeps the clone channel authenticated (only parent can write to inbox) and directional (clone replies only to parent).

### C4 — Self-Timeout (event-driven stall signal)

Every dispatch carries `max_task_minutes`. On exceedance, the clone self-injects `[STALLED:<callsign>]` into the parent's tmux via the outbox and exits the task. The stall signal is **event-driven**, not polled — the clone emits it at the moment of detection so the parent can redispatch, escalate, or cancel without waiting for a heartbeat interval. The parent's inbox-watcher surfaces the stall immediately. Clones MUST NOT silently exceed timeout — silence is treated as the worst case (deadlock) and escalated to Dave.

### C5 — Scope Lock

The clone executes **exactly** the dispatched task. No self-directed scope expansion, no "while I'm in here" refactors, no opportunistic fixes to unrelated code. If the clone discovers an unrelated issue, it returns it as a **finding** in the outbox completion payload — the parent decides whether to open a follow-up dispatch. Scope creep in a clone is attributed to the clone's callsign in blame and counts as a governance violation under LAW XVII. This rule prevents clones from producing sprawling PRs that the peer reviewer cannot cleanly evaluate.

### C6 — Clone Branch Isolation

Clones commit **only** to their own branch (`<callsign>/<task-ref>`), never to `main` and never to any PR branch owned by another callsign. The clone opens the PR against `main`; the parent (or parent's peer) reviews and merges. Clones MUST NOT push to `main` even with a clean merge — the merge is the orchestrator's act, not the clone's. This keeps the final merge decision attributable to an orchestrator callsign and keeps review-before-merge enforceable.

---

## 3. Activation Procedure

Bringing a clone online is a 5-step procedure. Step 3 is the one we missed live today — Claude Code presents a trust-folder prompt on first invocation in a worktree, and without pressing Enter the session sits idle and no inbox dispatch ever fires.

1. **Create / attach tmux session** with the callsign as the session name:

   ```bash
   tmux new-session -d -s <callsign> -c /home/elliotbot/clawd/Agency_OS-<callsign>
   ```

2. **Boot Claude Code with CALLSIGN env var** in the clone's pane. CALLSIGN MUST be set — `three_store_save.py` raises `SystemExit` on empty CALLSIGN (LAW XVII):

   ```bash
   tmux send-keys -t <callsign>:0.0 \
     "cd /home/elliotbot/clawd/Agency_OS-<callsign> && CALLSIGN=<callsign> claude --setting-sources=project" Enter
   ```

3. **Press Enter for the trust-folder prompt.** Claude Code, on first invocation inside a fresh worktree, prompts *"Do you trust the files in this directory?"* and blocks until the user confirms. The inbox-watcher cannot answer this prompt for you. If you skip this step, dispatches will accumulate in the inbox and never inject. Manually attach to the pane (`tmux attach -t <callsign>`) and press **Enter** to accept trust. Then detach (`Ctrl-b d`).

4. **Start the inbox-watcher** so parent dispatches can reach the clone:

   ```bash
   sudo systemctl start <callsign>-inbox-watcher.service
   sudo systemctl start <callsign>-relay-watcher.service
   ```

5. **Verify activation** — from the parent pane, drop a ping dispatch into `/tmp/telegram-relay-<clone>/inbox/` and confirm the clone's tmux pane receives the injection within ~2 seconds. If nothing appears, check `journalctl -u <callsign>-inbox-watcher.service` and confirm the trust-folder prompt was actually answered.

---

## 4. DIRECT-BUILD Tag Convention

Clones are the default path (C1). But clones can be unavailable — watcher down, trust-folder not yet accepted, HMAC secret mismatch, or the task is sub-Tier-A and delegation is overhead without benefit. When the orchestrator builds directly, the commit and group message must carry the DIRECT-BUILD tag so the governance trail stays honest.

Convention:

1. **Group post before starting:**
   ```
   [DIRECT-BUILD:<callsign>] <filepath or task-ref> — <reason: clone unavailable / sub-tier>
   ```
   Reason is mandatory. "Faster this way" is not an acceptable reason if clones are available.

2. **Commit message trailer:**
   ```
   DIRECT-BUILD: <callsign>
   Reason: <clone-unavailable | sub-tier | blocked-<details>>
   Governance-debt: LAW-XVII-DIRECT-BUILD
   ```

3. **Governance debt log:** record the DIRECT-BUILD incident in `elliot_internal.memories` as `type=governance_debt` with the tag `LAW_XVII_DIRECT_BUILD` and a one-line rationale. The debt entry lets us audit how often clones are bypassed and why — a rising rate signals an infrastructure problem, not just individual judgment calls.

The tag does not *excuse* the direct build; it *declares* it. Peer reviewer treats DIRECT-BUILD commits with extra scrutiny because they bypass C1 by design.

---

## 5. Exit Gate Pattern — Detect → Dispatch → Clone-Fix → Peer-Review → Merge

The exit gate is the end-to-end flow from "peer spots a problem" to "merge to main" with zero Dave copy-paste. Every step is observable and every handoff is a file on disk or a tmux injection — no human courier.

```
   [Elliot]        [Aiden]        [ORION clone]     [Elliot peer]      [main]
      |              |                  |                  |              |
   1. DETECT ------->|                  |                  |              |
      "Rule 2 firing |                  |                  |              |
       on peer work" |                  |                  |              |
      |              |                  |                  |              |
      |          2. DISPATCH ---------->|                  |              |
      |          inbox.json {task_ref,  |                  |              |
      |          brief, max_minutes}    |                  |              |
      |              |                  |                  |              |
      |              |              3. CLONE-FIX           |              |
      |              |              - read CLAUDE.md       |              |
      |              |              - branch orion/<task>  |              |
      |              |              - commit + push        |              |
      |              |              - open PR              |              |
      |              |                  |                  |              |
      |              |              4. OUTBOX ------------>|              |
      |              |              [COMPLETE:ORION]       |              |
      |              |              PR link + SHA          |              |
      |              |                  |                  |              |
      |<--- 5. PEER-REVIEW --------------------------------+              |
      |    (Elliot reviews Aiden-dispatched clone PR,                     |
      |     since Aiden is too close to the dispatch)                     |
      |              |                  |                  |              |
      +---------- 6. MERGE ------------------------------------------------>
         (orchestrator merges; clone never pushes to main)
```

Gate checks:
- **After step 3:** commit SHA appears in `git log orion/<task-ref>` on the clone's remote branch. No SHA = dispatch silently failed.
- **After step 4:** outbox file exists in `/tmp/telegram-relay-<clone>/processed/` (relay-watcher moves it post-injection) and parent's tmux received `[<CLONE>] [COMPLETE:...]`.
- **Before step 6:** PR has `[FINAL CONCUR:<peer>]` from a non-dispatching orchestrator. Dispatching parent cannot be the final approver on its own clone's work.

Dave sees one message: the final merge announcement. No copy-paste, no forwarded dispatches, no relay of intermediate state.

---

## 6. Known Failure Modes

### 6.1 Claude Code trust-folder prompt blocks activation

**Symptom:** Dispatches pile up in `/tmp/telegram-relay-<clone>/inbox/` but never inject into the clone tmux. `journalctl -u <clone>-inbox-watcher.service` shows the service is running and seeing the files but `tmux send-keys` appears to have no effect.

**Cause:** On first invocation in a freshly-cloned worktree, Claude Code blocks on a *"Do you trust the files in this directory?"* interactive prompt. `tmux send-keys` delivers the dispatch text to the pane, but the Claude Code process is waiting on the trust prompt and discards subsequent input until confirmed.

**Fix:** Attach to the clone tmux session (`tmux attach -t <callsign>`), press Enter to accept the trust prompt, then detach. See activation procedure step 3.

**Prevention:** Automate the trust prompt by pre-seeding `.claude/settings.json` with `"autoTrust": true` (only in trusted infrastructure worktrees), or add a manual "Enter the trust prompt" checklist item to any clone activation runbook.

---

### 6.2 Dispatch routed to wrong clone → duplicate work

**Symptom:** Two clones produce near-identical PRs for the same task-ref. One clone wasted 20+ minutes on work already completed by the other; peer reviewer must now triage two PRs and reject one.

**Cause (live incident, 2026-04-22):** The enforcer Rule 2 fix was dispatched to **both** ATLAS (via Elliot) and ORION (via Aiden) because the peer-concur exchange didn't specify which clone owned the task. Both clones ran C1 correctly in isolation; the collision happened at the orchestrator layer.

**Fix:** On dual peer-concur for a build task, the dispatching orchestrator MUST post a `[DISPATCHING:<parent> → <clone>]` claim before dropping the inbox file. 60-second peer-conflict window mirrors Claim-Before-Touch. If the other orchestrator was already dispatching to its clone, they post `[CONFLICT:<peer>] already dispatched to <their-clone>` and one side aborts.

**Prevention:** Enforcer bot rule: detect simultaneous inbox writes to two clones on the same `task_ref` within 60 seconds and flag both. Dispatch JSON already carries `task_ref` — the duplicate detection is cheap.

---

### 6.3 Unsigned dispatches rejected by HMAC when `INBOX_HMAC_SECRET` set

**Symptom:** Dispatch file appears in `/tmp/telegram-relay-<clone>/processed/` prefixed `REJECTED_`, and `/tmp/telegram-relay-<clone>/hmac_rejects.log` shows a HMAC REJECT reason. The clone tmux never receives the dispatch.

**Cause:** Inbox-watcher checks `src/security/inbox_hmac.verify()` when `INBOX_HMAC_SECRET` is set in the environment. Dispatches written without the HMAC signature field (or with a mismatched signature because the writer used a different secret) are rejected as unsigned or tampered.

**Fix:** The dispatching orchestrator must use the HMAC-signing helper to produce the dispatch JSON. Hand-written JSON drops into inbox without signature and will be rejected. If the secret was rotated, both sides must pick up the new value — check `/home/elliotbot/.config/agency-os/.env` and restart the inbox-watcher service.

**Prevention:** Wrap dispatch authoring in a single helper (`dispatch_to_clone.py` or equivalent) that always signs. Never `cat > inbox.json`. Add a healthcheck that dispatches a synthetic signed ping every hour and alerts if the signature check fails — catches secret drift before a real task is lost.

---

## Appendix — Callsign Quick Reference

| Callsign | Env var | Worktree dir | Branch prefix | Tmux session | Inbox | Outbox |
|----------|---------|--------------|---------------|--------------|-------|--------|
| elliot | `CALLSIGN=elliot` | `Agency_OS/` | `main` / `feat/*` | `elliot` | — (orchestrator) | — |
| aiden | `CALLSIGN=aiden` | `Agency_OS-aiden/` | `aiden/*` | `aiden` | — (orchestrator) | — |
| atlas | `CALLSIGN=atlas` | `Agency_OS-atlas/` | `atlas/*` | `atlas` | `/tmp/telegram-relay-atlas/inbox/` | `/tmp/telegram-relay-atlas/outbox/` |
| orion | `CALLSIGN=orion` | `Agency_OS-orion/` | `orion/*` | `orion` | `/tmp/telegram-relay-orion/inbox/` | `/tmp/telegram-relay-orion/outbox/` |
| scout | `CALLSIGN=scout` | `Agency_OS-scout/` | `scout/*` | `scout` | `/tmp/telegram-relay-scout/inbox/` | `/tmp/telegram-relay-scout/outbox/` |

All clones inherit governance from `~/.claude/CLAUDE.md §Shared Governance Laws` plus their worktree `./CLAUDE.md`. Per-clone operational state lives in `./IDENTITY.md` (callsign SSOT) and `./CLONE_LEARNINGS.md` (working journal that persists across `/clear`).
