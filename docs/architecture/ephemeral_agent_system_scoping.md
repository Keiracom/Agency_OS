# Ephemeral Agent System — Architecture Scoping

**V1 completion criterion 1.** Scoping document, not implementation. Per Dave-authorised dispatch 2026-05-25 post-wave-2-close.

**KEI:** Agency_OS-dbwt (P1). **Author:** aiden (deliberator-tier governance doc). **Reviewers per author-exclusion:** Elliot + Max.

---

## 1. Notes — canonical key paste (per audit-dispatch checklist)

`ceo:memory_abstraction_layer_v1` queried 2026-05-25. Criterion 1 verbatim:

> **id:** 1
> **title:** "Ephemeral agent system replaces tmux"
> **description:** "No more persistent tmux sessions. Agents spin up, do work, spin down. The system is the runtime — not a terminal window. Architectural backbone."

Plus the alignment line from `phase_2_build_alignment.does_not_cover`: "criterion 1 (ephemeral migration), criterion 3 (persona redesign), criterion 4 cache-awareness in governance" — Phase 2 wave 2 work does NOT touch criterion 1; this is genuinely new architectural ground.

---

## 2. What "tmux-coupled" means today — subsystem inventory

Every agent currently lives in a long-running tmux session (`elliottbot`, `aiden`, `max`, `orion`, `atlas`, `scout`, `nova`). Eight subsystems depend on that being true:

| # | Subsystem | Where | Tmux dependency |
|---|---|---|---|
| 1 | **Inbox watcher + injector** | `scripts/elliot_inbox_watcher.sh`, `scripts/orchestrator/relay_watcher.sh`, per-callsign equivalents | Inotify-watches per-callsign inbox dir → parses JSON → `tmux send-keys` into the callsign's pane to inject the message |
| 2 | **Capture-pane liveness check** | inbox watchers' "wait for `❯` prompt" loop | `tmux capture-pane -t <target> -p` reads pane content to detect Claude Code's idle prompt before injecting |
| 3 | **Interactive-prompt resolution** | Implicit in all tmux-bound agents | When an agent emits a question, it stays running in tmux awaiting Dave/peer reply on the same pane (no out-of-band channel) |
| 4 | **Per-callsign tmux session bootstrap** | `scripts/install_*_agent.sh`, `scripts/agent_keepalive.sh` | systemd unit launches a `tmux new-session -d -s <callsign>`, then drives Claude Code inside it; keepalive monitors `tmux has-session` |
| 5 | **NATS bridge → tmux pane** | `scripts/orchestrator/nats_to_inbox_bridge.py`, per-callsign `*-nats-*-bridge.service` | NATS subject → JSON file → inbox watcher → tmux pane (same path as #1 but sourced from NATS instead of file write) |
| 6 | **next_work_prompter inject** | `scripts/orchestrator/next_work_prompter.py` (PR #1113) | When stop hook fires + classifier says "agent has next work", `_inject()` calls `tmux send-keys` to wake the agent |
| 7 | **Supervisor wake heartbeat** | `scripts/orchestrator/supervisor_wake_publish.py` (PR #1117) | Publishes wake envelope to NATS → bridge → inbox → tmux (same as #5 + #1 chained) |
| 8 | **Slack relay last-mile** | `scripts/slack_relay.py` (elliot-only outbound) | Reads from Elliot's tmux pane history for context; injects responses via inbox→pane chain |

**Net:** tmux is the **substrate** for both **inbound** (peer/Dave message → agent's eyes) and **continuation** (agent stays alive between turns). Removing tmux requires replacing BOTH paths.

---

## 3. Spawn-with-context — cashing out "context"

The load-bearing concept. An ephemeral agent has NO prior memory of itself — every spawn is a fresh process. "Context" is what the spawner injects at start so the agent doesn't re-derive everything from zero.

Context at spawn-time has five parts, all queryable from outside the agent:

**Part A — initial prompt template.** Per-callsign role brief (current `IDENTITY.md` / runbook content). Source: `docs/runbooks/<callsign>-identity.md` (PR #1116/#fwdb/#e02v). Static across spawns; refreshed when runbook changes.

**Part B — current canonical-key state.** Snapshot of relevant `ceo_memory` keys at spawn time. For most agents: `ceo:comm_architecture` + `ceo:memory_abstraction_layer_v1` + `ceo:agency_os_keiracom_separation_v1`. Queried fresh per spawn (no cache — staleness is the failure mode the canonical-key-query discipline exists to prevent).

**Part C — pending inbox queue.** All unprocessed inbox messages for this callsign at spawn time. Currently `/tmp/telegram-relay-<callsign>/inbox/*.json` files; post-migration: a Hindsight memory bank or a Postgres queue table (decision deferred to implementation dispatch). Agent processes the queue, terminates.

**Part D — recent ceo_memory.** Last ~5 `daily_log` + `core_fact` entries scoped to callsign (the SQL we run at session start today). Plus any `dave_confirmed` entries from the last 7 days. Source: existing `public.agent_memories` + `public.ceo_memory` tables.

**Part E — recent agent_memories.** Last ~10 entries from this callsign's own working memory. Source: existing `public.agent_memories` filtered by callsign. The "what was I in the middle of?" context.

**Composition:** spawn script reads A+B+C+D+E in parallel (one Supabase query batch + one fs read for C), composes them into a single initial prompt, spawns Claude Code with that as the first input. Agent reads, acts, terminates. No persistent state between spawns.

**Open implementation choice (deferred to dispatch):** is the spawn a fresh `claude` process per task, OR a pool of warm processes that pick tasks off a queue? Both work; the second is cheaper at scale but adds pool-management complexity. Recommend fresh-per-task for V1 (simpler; matches the "spin up, spin down" framing); revisit if cold-start latency becomes the constraint.

---

## 4. Per-subsystem ephemeral replacement

Each of the 8 from §2 needs a non-tmux substitute. Most are straightforward; one (#3) is the substantive design choice.

**#1 — Inbox watcher + injector:** REPLACED by a per-callsign **task dispatcher**. Watches the same inbox dir; on new message → spawns a new ephemeral agent with that message as Part C context (see §3) → agent processes → exits. No tmux send-keys involved.

**#2 — Capture-pane liveness check:** OBSOLETE. No persistent pane to check; the agent is spawned WHEN there's work + auto-terminates when done. Liveness = "is there a spawn running for this task?" answered by process management (systemd `ActiveState=active` or container `docker ps`), not pane content.

**#3 — Interactive-prompt resolution:** This is the substantive design — see §5.

**#4 — Per-callsign tmux session bootstrap:** REPLACED by per-callsign **task dispatcher** (same dispatcher as #1). systemd manages the dispatcher, not the agents. Agents are children of the dispatcher; lifecycle is per-task, not per-callsign.

**#5 — NATS bridge → tmux pane:** SIMPLIFIED. Bridge writes to the per-callsign inbox dir (existing behaviour). Dispatcher (#1) sees the new file → spawns. The NATS → inbox path stays the same; only the "inbox → pane" final hop changes to "inbox → dispatcher → ephemeral spawn".

**#6 — next_work_prompter inject:** REPLACED by **task dispatcher poll**. Instead of "inject a wake message into the pane", the prompter writes a JSON to the inbox dir; dispatcher spawns ephemeral agent with that as Part C. The same classifier logic (AUTHOR / REVIEWER / INFRA) from PR #1113 stays; only the delivery mechanism changes from tmux send-keys to inbox-write.

**#7 — Supervisor wake heartbeat:** REPLACED by **scheduled task spawn**. Timer fires → dispatcher spawns ephemeral "supervise check" agent with the right context → agent reads bd ready / inbox / PR queue / takes action / exits. Same systemd timer + Persistent=true behaviour; only the consumer changes from tmux pane to dispatcher-spawn.

**#8 — Slack relay last-mile:** UNCHANGED at the relay layer. Elliot's outbound (`tg -c ceo`) still writes to Slack. The CHANGE is upstream: Elliot's *spawn* receives the Slack message as Part C context (instead of reading it from tmux pane history). Slack relay continues to be elliot-only-outbound per Dave directive 2026-05-19.

---

## 5. Interactive-prompt edge case — when an ephemeral agent needs to pause and ask

Elliot's framing in the dispatch: "agent emits decision-needed event to queue, terminates, new spawn picks up when decision lands". **Verified — this is the right shape.**

Refinement: the queue isn't a generic queue; it's the SAME per-callsign inbox the dispatcher already watches. The protocol:

1. Agent reaches decision-needed state mid-task.
2. Agent writes a `decision_request` envelope to a NEW inbox dir specific to the asking-party — typically `/tmp/telegram-relay-elliot/inbox/` (Dave's relay surface) or `/tmp/telegram-relay-aiden/inbox/` (deliberator). Envelope carries: original task_ref, the decision question, the agent's state-snapshot needed to resume.
3. Agent emits a `paused_pending_decision` event to its OWN inbox with the same task_ref + state-snapshot. Then terminates.
4. Days/hours/minutes later, the decision-giver's spawn processes the `decision_request`, answers via inbox-write to the original-agent's inbox with `decision_response` envelope.
5. Original-agent's dispatcher sees the new file → spawns a fresh agent with: Parts A+B+D+E (standard) PLUS the original `state-snapshot` from step 3 + the `decision_response`. Agent resumes from where it paused.

**This is durable wait by design.** The "agent" between step 3 and step 5 doesn't exist — there's nothing burning tokens or holding a pane. The dispatcher's job is to detect the right input (decision_response with matching task_ref) and spawn a resume agent.

**State-snapshot scope:** the resume agent doesn't need full memory — it needs (a) the original task_ref to link back to bd or NATS subjects, (b) the question it asked, (c) whatever interim work it had completed (file paths, intermediate artifacts). Typically <1KB JSON. Lives in the `paused_pending_decision` event payload + persisted to a `paused_tasks` table (new — see §7 implementation pieces).

**Edge cases handled:**
- Multiple resumes in flight: each carries unique task_ref; dispatcher routes by task_ref match.
- Decision never lands: TTL on the `paused_tasks` row (e.g. 7 days) → automatic cleanup + dead-letter to Elliot.
- Decision answer is "abort": dispatcher spawns a "task aborted" cleanup agent that closes the bd KEI + cleans interim state.

---

## 6. Migration sequencing — parallel-safe vs cutover-required

Five stages. Stages 1-3 are zero-risk parallel work (tmux stays alive). Stage 4 is the destructive cutover. Stage 5 is post-cutover validation.

**Stage 1 — Build the per-callsign dispatcher (parallel-safe).**
- New service `scripts/dispatcher/<callsign>_dispatcher.py` per callsign. Watches the same inbox dir current watchers use.
- On new message: instead of `tmux send-keys`, spawns `claude` subprocess with the composed prompt (Parts A+B+C+D+E).
- Initially: dispatcher and tmux watcher run IN PARALLEL on the same inbox dir, but only ONE consumes each file (file rename to `inbox/processing/<file>` before spawn = atomic claim). For Stage 1: dispatcher writes a no-op log entry instead of actually spawning, just to prove the file-claim race-safety + verify the watcher still works.
- Risk: zero (no behavior change; dispatcher only logs).

**Stage 2 — Implement spawn-with-context end-to-end (parallel-safe).**
- Dispatcher now actually spawns `claude` with composed prompt instead of no-op logging.
- Initial scope: ONE callsign (recommend Atlas — already a clone, smallest blast radius). Dispatcher claims half of Atlas's inbox messages (e.g. odd-numbered file IDs); tmux watcher claims the other half. Both produce real work; compare outputs.
- Run for 3-5 days. Compare: does ephemeral-Atlas complete tasks identically to tmux-Atlas? Same PR shape? Same review outputs?
- Risk: low (Atlas is a clone, work is bd-tracked, outputs are PR-reviewable; bad outputs surface in PR review, not silently corrupted state).

**Stage 3 — Implement the interactive-prompt protocol (parallel-safe).**
- Add `paused_tasks` Postgres table (see §7).
- Add `decision_request` / `decision_response` / `paused_pending_decision` envelope types to inbox JSON schema.
- Dispatcher learns to: (a) detect `decision_response` envelopes and route to resume-spawn, (b) handle `paused_pending_decision` events by writing to `paused_tasks`.
- Test with synthetic decisions on the Atlas dispatcher from Stage 2 (e.g. "ask Aiden whether X" as a synthetic interrupt mid-task).
- Risk: low (still parallel-running with tmux watcher; failure surfaces as Atlas-only behavior change).

**Stage 4 — Cutover (destructive, requires checklist).**
- One callsign at a time. Order: clones first (Atlas, Orion, Scout, Nova — already file-relay based, smallest blast radius), then deliberators (Aiden, Max), then Elliot last (orchestrator, riskiest).
- Per-callsign cutover:
  1. Stop the tmux watcher service for that callsign.
  2. Switch dispatcher from "claim half" to "claim all" inbox messages.
  3. Stop the systemd `tmux new-session` keepalive for that callsign.
  4. Verify next 3 inbox messages spawn correctly + complete.
  5. If broken: restart tmux watcher + tmux keepalive (rollback path is single systemctl).
- Cutover-day checklist: per-callsign checklist file (see §8) listing the specific systemd unit names + verification queries.

**Stage 5 — Post-cutover hardening (parallel-safe).**
- Decommission the `tmux capture-pane` liveness checks in `agent_keepalive.sh` (no longer needed).
- Update `IDENTITY.md`/runbook references to remove tmux mentions.
- Update `feedback_silence_means_silence` and related memories to reflect "agent terminates" instead of "agent goes quiet in pane".
- Archive `scripts/install_*_agent.sh` tmux-launch logic to `scripts/archive/` (preserve for reference; remove from runtime path).
- Risk: zero (cleanup of obsolete code).

---

## 7. Implementation pieces — bd issues to file after concur

Each becomes a separate engineer-tier KEI dispatched post-merge. Not bundling here per `feedback_split_orthogonal_scope`.

1. **`scripts/dispatcher/` package** — per-callsign dispatcher binaries + shared `_spawn.py` composition library. ~400 LoC. P1.
2. **`paused_tasks` Postgres table + migration** — see §5 state-snapshot. ~50 LoC SQL + ~100 LoC accessor. P1.
3. **Inbox JSON schema update** — add `decision_request` / `decision_response` / `paused_pending_decision` envelope types to the existing schema. ~30 LoC + schema doc. P1.
4. **Per-callsign systemd unit templates** — `keiracom-dispatcher@<callsign>.service` template instance unit. ~50 LoC each × 7 callsigns. P2.
5. **Spawn-with-context composer** — the A+B+C+D+E builder library called by every dispatcher. ~150 LoC. P1 (blocks 1).
6. **Cutover-day checklist generator** — per-callsign markdown checklist with current systemd unit names. ~50 LoC. P3 (operational tooling).
7. **Decommission tracking KEI** — post-Stage-4 cleanup of obsolete tmux scripts + identity-doc updates. P3.

Total estimate: ~1,200 LoC + per-callsign systemd templates. ~2-3 weeks of fleet engineering at current cadence.

---

## 8. Risk + rollback (concretely)

**Risk 1 — cold-start latency makes the system feel slow.**

If `claude` cold-start is 5-15 seconds per spawn (likely with full prompt), latency between inbox-message-landing and agent-action grows from sub-second (tmux pane already running) to 5-15s.

*Mitigation:* worth measuring on Stage 2 Atlas. If unacceptable: switch from "fresh spawn per task" to "warm pool of N idle Claude processes per callsign" — same dispatcher logic, pool maintains N pre-warmed processes. Costs more idle tokens but eliminates cold start.

*Rollback if Stage 2 reveals unacceptable latency:* revert Atlas to tmux watcher (`systemctl start atlas-inbox-watcher.service`); dispatcher continues in no-op mode while we measure cost-vs-latency for the warm-pool variant.

**Risk 2 — interactive-prompt resume drops state.**

If the `paused_tasks` state-snapshot is incomplete (agent had in-memory state not captured in the JSON), the resume spawn starts from incomplete context and produces worse output than the original would have.

*Mitigation:* state-snapshot discipline at pause-time. Agent must EXPLICITLY enumerate what state matters (file paths it was editing, intermediate results, task_ref); the schema validates required fields. Tested in Stage 3 with synthetic decisions.

*Rollback:* if a paused task can't resume cleanly, dispatcher spawns a "from-scratch retry" agent with the original task brief instead. Worst case: re-do work that was already done; not silent corruption.

**Risk 3 — file-claim race in the inbox.**

Two dispatcher instances (e.g. running on different worktrees) try to claim the same inbox file simultaneously.

*Mitigation:* atomic `os.rename(inbox/<file>, inbox/processing/<file>)` — Linux guarantees rename atomicity within a single filesystem. First rename wins; second fails. Established pattern in fleet (relay watchers already use this).

*Rollback:* if a file is incorrectly claimed-but-not-processed, manual move from `inbox/processing/` back to `inbox/` re-queues it. Operator runbook entry needed.

**Risk 4 — Elliot's Slack-relay last-mile breaks under ephemeral.**

Elliot today reads Slack history from his tmux pane to compose context-aware replies. Post-cutover: ephemeral-Elliot has no pane history. If the Slack message context doesn't include the relevant thread state, Elliot's reply will be context-poor.

*Mitigation:* Slack relay payload must include the recent thread context as Part C content. Elliot's dispatcher composes Parts A+B+C(=Slack message + thread snapshot)+D+E. The thread snapshot comes from `slack_relay.py` calling `conversations.replies` API at dispatch time.

*Rollback:* Elliot is the LAST callsign cut over per Stage 4 order, specifically because of this risk. If Slack-context handling breaks: revert Elliot to tmux watcher; investigate thread-snapshot quality before re-attempting.

**Risk 5 — runaway spawn loop.**

A misconfigured dispatcher could spawn agents on every inbox message even when they shouldn't (e.g. a relay watcher echo-loop creates a self-feeding inbox).

*Mitigation:* per-callsign spawn rate limit (e.g. max 10 spawns per minute per callsign). Implemented as a counter at dispatcher level; alarms via existing BetterStack integration when rate-cap hit. Plus: dispatcher reads the existing `feedback_no_held_loop` discipline as a built-in classifier — bare `[CALLSIGN]` echo messages do NOT trigger spawn (mirrors the "Holding." pattern Dave killed 2026-05-07).

*Rollback:* kill switch — `systemctl stop keiracom-dispatcher@<callsign>.service` halts spawning instantly; inbox queue stays intact for post-fix replay.

**Risk 6 — supervisor-wake heartbeat misses (no agent to wake).**

Supervisor wake currently injects to the pane; if the pane doesn't exist, the wake message goes nowhere. Post-cutover: the wake IS a spawn-trigger, not an inject — handled naturally. But during Stage 4 cutover, there's a moment when tmux is dying but dispatcher isn't yet handling supervisor-wake messages — wakes get lost.

*Mitigation:* Stage 4 cutover order: stop tmux watcher FIRST (no inbound consumes), start dispatcher SECOND, only THEN stop tmux session. Wakes accumulate in inbox during the gap; dispatcher processes them on start.

*Rollback:* same as Risk 4 — single-systemctl revert per callsign.

---

## 9. What this scoping does NOT decide (intentional deferrals)

- **Process vs container per spawn.** Subprocess `claude` is fastest to ship; container (`docker run claude:latest`) is more isolated but adds 1-2s startup overhead. Recommend subprocess for V1; revisit for first-paying-customer scale.
- **Fresh-per-task vs warm-pool spawn model.** §3 recommends fresh; Risk 1 mitigation is the fallback to pool. Decide on Stage 2 empirical latency data.
- **Whether Slack relay needs its own ephemeral migration.** Slack relay is a thin Python script, not a Claude agent — stays as a long-running process even after tmux dies. Out of scope for criterion 1; addresses naturally if a "no long-running processes" rule emerges later.
- **NATS bridge services' future.** Currently long-running; could be re-architected as serverless triggers later. Out of scope for criterion 1.

---

## 10. Acceptance criteria

- [x] Names every tmux-coupled subsystem (8 subsystems enumerated in §2).
- [x] Per-subsystem ephemeral replacement proposed (§4).
- [x] Spawn-with-context cashed out into 5 parts (§3).
- [x] Migration sequenced into 5 stages with parallel-safe vs cutover-required distinction (§6).
- [x] Interactive-prompt edge case named + refined (§5).
- [x] 6 risks with concrete rollback paths (§8).
- [x] Implementation pieces enumerated for post-concur bd dispatch (§7).
- [x] Canonical key paste verbatim in §1.
- [ ] Elliot impl-feasibility concur.
- [ ] Max code-quality concur (architecture-doc, so quality lens = "is the proposal coherent / are the risks concrete / are the rollbacks reachable?").

---

_End scoping. Per orchestrator-merge-after-NATS-concur + author-exclusion: Aiden authored; eligible reviewers Elliot + Max; 2-of-2 lands admin-merge. Then dispatch the implementation pieces from §7 as separate engineer-tier KEIs._
