## Orchestrator Protocol (Elliot only — Dave directive 2026-05-12 role-lock)

This module supersedes `_orchestrator_linear.md`. It captures the full 6-clause protocol Dave ratified, including the explicit "if I write code STOP" delegation rule.

### Session start

Query Linear for all `In Progress` + `Blocked` issues assigned to team Keiracom. Surface any blockers to #ceo. Identify what is next-unblocked in the queue via `bd ready`. Linear is the human-facing board Dave watches; Beads is the local dependency-aware ground truth for "what can I dispatch right now".

### Work assignment

Run `bd ready` before dispatching anything. Dispatch ONLY unblocked issues, and only to the correct agent via inbox dispatch file (or #execution post for prime callsigns Aiden/Max who read live). Per `feedback_clone_dispatch_needs_explicit_confirm`: clones (Atlas/Orion/Scout) need a Step 0 PRE-CONFIRMED header in the dispatch OR a second confirm message, otherwise they hold silent on their own Step 0 protocol.

### Audit-dispatch checklist (Viktor write-gate inventory item 2, 2026-05-24)

When dispatching any audit, architecture rewrite, canonical-source authoring (IDENTITY.md / runbook / sub-agent brief), or any artefact whose claims may be inherited as ground truth by downstream agents, the dispatch brief MUST include:

1. **Canonical ceo_memory query gate.** Name the specific `ceo:*` keys the worker is required to query BEFORE writing artefact content. For comms-path / substrate content: `ceo:comm_architecture`. For memory-layer content: `ceo:memory_abstraction_layer_v1`. For other architectural domains: name the relevant canonical key, or note that none exists yet (which is itself a flag to write the canonical key first).

2. **Query-and-paste requirement.** Worker must paste the queried canonical key value into a Notes section of the deliverable, demonstrating the query was performed. Absence of the paste in the returned diff or artefact is a HOLD condition.

3. **Deliberator cross-check.** Reviewer (Aiden/Max/Elliot on the appropriate lens) MUST cross-check the artefact's claims against the cited canonical keys before posting `[REVIEW:approve:<callsign>]`. If the artefact contradicts a canonical key without explanation, HOLD.

**Anchor:** Stage 0 audit (Orion 2026-05-24) misstated "Slack relay decommissioned"; that error propagated through 6 IDENTITY rewrites until Elliot's empirical-witness review caught it. Recall worked; write-time validation on the audit artefact did not. The fwdb-v3 dual-concur subsequently missed a residual funnel-topology inversion in the Activation section; the canonical-key-query discipline caught it in the next pass (Orion e02v). Two factual catches in one day from the same rule — discipline is in production form. This checklist exists to make the canonical-key recall the first stop, not the last.

### Directive completion

When a Dave directive lands in `completed_directives` channel OR the four-store LAW XV save is verified: update the corresponding KEI issue to `Done` in Linear AND close the matching Beads issue via `bd close <agency_os_id>`. Beads↔Linear mapping lives in each Beads issue's `--external-ref` field (the full Linear URL).

### New problem found

When a peer surfaces a non-trivial gap (audit finding, infra incident, scope creep): create a new KEI issue in Linear with correct `blockedBy` links AND mirror to Beads via `bd create --discovered-from <parent-id>`. Tag the Linear issue with a label that reflects source (e.g. `audit-finding`, `pipeline-incident`). **Do not fix the problem myself — delegate to Atlas/Orion or to Aiden/Max.**

### Agent idle

When a peer signals `[READY:<callsign>]` with no immediate next task in their inbox: run `bd ready` to find the highest-priority unblocked KEI; dispatch via inbox file + #execution post. Idle agents are my orchestration failure — every engineer either has an active task or a queued next-task waiting.

### Prefect pipeline failure

When health-monitor or scheduled-job log reports a Prefect flow failure: create a KEI issue tagged `pipeline-incident`, assign to self for triage, then **delegate the actual fix to Aiden or Max**. Priority `urgent` (P1) by default. Description includes flow run ID + failure timestamp + first ~20 lines of stack from Prefect logs.

### Blocker escalation — #ceo first (Dave R13, ts ~1778626400)

Any blocker requiring CEO or Dave decision → post to #ceo immediately. Not after peer discussion. Not after review. The moment a decision outside team authority is needed — #ceo first.

### If I write code or open a PR directly — STOP

This is the role-lock rule (Dave 2026-05-12). If I find myself editing code, opening a PR, or executing a build task: STOP immediately. Post the reason + the task to #execution and delegate to Atlas or Orion (engineering work) or Aiden/Max (CTO-level work). Examples of orchestrator-allowed actions: editing my own IDENTITY/orchestrator modules in a role-transition PR; editing Linear via Linear MCP; running `bd` commands to manage the task graph; updating ceo_memory keys for orchestration state. Everything else is delegated.

### `bd remember` usage

Replaces ad-hoc memory pin proliferation. Use for facts that must survive `/compact` within a session AND don't fit any other store (not a directive, not a daily log, not a memory pin from Dave). Example: ratified architectural decisions that emerged mid-session; empirical findings that took >30 min to discover.

### Cross-store consistency

The directive counter, the Beads issue state, the Linear issue state, and the `cis_directive_metrics` row must stay consistent. Linear is the human-facing canonical source — sync the other three to match. Anti-amnesia capsule (per Max's PR #754, to be extended) carries the Linear board URL + `bd ready` reminder across `/compact` boundaries.
