# KEI-39 Design — Pre-execution claim protocol (4-step)

**Author:** Aiden (design only — per Dave verbatim ts ~1778665450)
**Implementer:** Elliot (post-compact ratification + execute)
**Beads:** Agency_OS-mwwmq0 — P0 URGENT
**Linear:** [KEI-39](https://linear.app/keiracom/issue/KEI-39)

## Problem

Agents update Beads + Linear when starting a NEW KEI but not when transitioning between subtasks WITHIN a KEI. Today's duplicate-dispatch incident: Max's ingest script auto-rolled from Stream 2 → Streams 3+4 with no claim signal; CEO saw no owner + dispatched Aiden; near-collision averted by Resolution A.

## The 4-step protocol (mandatory before ANY task / subtask transition)

```
1. bd claim [task-id]
2. Linear: set assignee field + add comment "Starting [subtask] now"
3. #execution post: [STARTING] [task description] — owned by [callsign]
4. THEN execute
```

### When it applies

- Starting a new KEI from `Todo` status.
- Starting the next stream / phase / subtask within a running KEI.
- Resuming a task after a crash, restart, or context compaction.
- Picking up a `[PROPOSE:callsign]` self-assigned item (treat as task-start).

### When it does NOT apply

- Single-shot informational posts (status, concur, release).
- Sub-step granularity within an already-claimed atomic task (e.g. editing one file vs another within the same PR).
- Reviewing a peer's PR (review is not execution-claim; concur tags handle that lane).

## Step-by-step machine-readable contract

### Step 1: `bd claim [task-id]`

- CLI: `bd update <bead-id> --claim` OR `bd update <bead-id> --assignee=<callsign>`.
- Acceptance: `bd show <bead-id>` returns `Status: IN_PROGRESS` and `Assignee: <callsign>`.
- Failure mode: bead already claimed by another callsign → DO NOT proceed. Surface as `[BLOCK:<existing-owner>]` in #execution + escalate to Elliot for resolution.

### Step 2: Linear assignee + comment

- API: Linear MCP `linear-server` — `mcp__linear-server__update_issue` with `assignee` field set + `mcp__linear-server__add_comment` with body `"Starting <subtask> now"`.
- Acceptance: Linear shows the assignee + comment within 60s.
- Failure mode: Linear MCP unavailable → degrade to step 1 + step 3 only. Log governance debt as `LAW_KEI39_LINEAR_SKIP` with reason.

### Step 3: `#execution` post

- Format: `[STARTING] <task description> — owned by <callsign>`.
- Channel: `#execution` (Slack `C0B3QB0K1GQ`).
- Tooling: `python3 scripts/slack_relay.py "[STARTING] ... — owned by aiden"` (callsign auto-resolved from `IDENTITY.md` — pending KEI-22 fix for cross-worktree resolution).
- Acceptance: Slack post visible to peers + CEO within 30s.
- Failure mode: slack_relay errors → DO NOT proceed. Investigate before execute; another agent may be silently doing the same work.

### Step 4: Execute

- Only after steps 1-3 confirm.
- During execution: standard concur protocol applies for any decision points.
- On completion: `bd close <bead-id>` + Linear status update + `[TASK-COMPLETE]` post.

## CEO dispatch safety check

Before any CEO dispatch, the new check sequence:

1. **Does Linear show an assignee on this task?**
   - Yes → task is owned. Do NOT dispatch.
   - No → continue to (2).
2. **Is there a recent `[STARTING]` post for this task in `#execution`?**
   - Yes → task is owned (Linear may be stale per KEI-22). Do NOT dispatch.
   - No → task is unowned. Safe to dispatch.

This is exactly the gap KEI-22 documents (Linear↔Beads sync). KEI-39 is the human-protocol mitigation; KEI-22 is the machine mitigation. Both ship.

## GOVERNANCE.md additions

Append to GOVERNANCE.md under a new section `## PROTOCOL — Pre-execution claim (KEI-39)`:

```markdown
## PROTOCOL — Pre-execution claim (KEI-39, ratified 2026-05-13)

Before executing ANY task or subtask transition, every agent MUST:

1. `bd claim <task-id>` — claim Beads ownership.
2. Linear: set assignee field + comment "Starting <subtask> now".
3. `#execution`: post `[STARTING] <description> — owned by <callsign>`.
4. THEN execute.

Applies to: new KEI start, next stream/phase/subtask within a running KEI, post-crash/post-compact resume, picking up a [PROPOSE:callsign] self-assigned item.

Does NOT apply to: status/concur/release posts, sub-step granularity within an already-claimed atomic task, PR review (use concur tags).

Violation = governance debt entry of type `LAW_KEI39_CLAIM_SKIPPED`.
```

## Beads task-start template

Modify the `bd create` default template to include a checklist reminder:

```
## Pre-execution claim (KEI-39 — mandatory)

- [ ] bd claim <task-id> — claimed by <callsign>
- [ ] Linear assignee set + "Starting <subtask> now" comment posted
- [ ] #execution `[STARTING] <description> — owned by <callsign>` post sent
- [ ] All 3 confirmations verified before execute
```

The template is rendered into the issue description on create. Agents check off as they progress.

## Acceptance criteria

- GOVERNANCE.md updated with §PROTOCOL — Pre-execution claim.
- `bd create` template includes the 4-item checklist.
- All 6 agents (aiden, max, elliot, atlas, orion, scout) acknowledge in #execution within 24h of ratification.
- First test case: Aiden's next task transition uses the protocol verbatim. Confirms in #execution. Beads + Linear + Slack all show ownership before execute.

## Failure modes + mitigations

- **Linear MCP outage**: degrade to step 1 + 3 only. Log governance debt. Re-sync Linear post-restore.
- **Slack relay outage**: DO NOT execute. Investigate cross-agent collision risk first (another agent may have stepped in).
- **Agent forgets the protocol**: Enforcer hook fires `[ENFORCER]: KEI-39 violation` when an agent reports `[TASK-COMPLETE]` without a prior `[STARTING]` for the same task-id. Adds to detection coverage.

## Implementation handoff for Elliot

Files to touch:

1. `GOVERNANCE.md` — append the §PROTOCOL section.
2. Beads `bd create` template — add the 4-item checklist (path: wherever bd templates live; likely `~/.bd/templates/` or in-repo `.beads/templates/`).
3. (Optional) Enforcer hook — extend `scripts/enforcer/enforcer_check.py` (or equivalent) with a `KEI-39` rule that fires on `[TASK-COMPLETE]` without prior `[STARTING]`.

Estimated: ~30 LoC governance text + ~10 LoC template + ~25 LoC enforcer rule (optional).

## Rollback

GOVERNANCE.md revert via `git revert` if the protocol creates more friction than the duplicate-dispatch risk it prevents. Pragmatic — first 2 weeks watch closely; if false-friction (e.g. agents posting [STARTING] before every micro-edit) eats more time than it saves, narrow the scope.
