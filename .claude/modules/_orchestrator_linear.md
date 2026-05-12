## Orchestrator — Linear + Beads Hooks (Elliot only)

Per Dave directive 2026-05-12. Elliot is the only callsign that runs these hooks; clones + CTOs report state, Elliot updates the board.

### Trigger hooks

1. **Directive completion** — when a Dave directive lands in `completed_directives` channel OR the four-store LAW XV save is verified: update the corresponding KEI issue to `Done` in Linear AND close the matching Beads issue via `bd close <agency_os_id>`.

2. **New problem discovered** — when a peer surfaces a non-trivial gap (audit finding, infra incident, scope creep): create a new KEI issue in Linear with correct `blockedBy` links AND mirror to Beads via `bd create --discovered-from <parent-id>`. Tag the Linear issue with a label that reflects source (e.g. `audit-finding`, `pipeline-incident`).

3. **Agent idle** — when a peer signals `[READY:<callsign>]` with no immediate next task in their inbox: run `bd ready` to find the highest-priority unblocked KEI; dispatch via inbox file + #execution post.

4. **Prefect pipeline failure** — when health-monitor or scheduled-job log reports a Prefect flow failure: create a KEI issue tagged `pipeline-incident`, assignee Elliot, priority `urgent` (P1), description includes the flow run ID + failure timestamp + first ~20 lines of stack from the Prefect logs.

### Beads ID ↔ Linear ID mapping

The Beads issues use prefix `Agency_OS-<hash>`. Linear identifiers use `KEI-<n>`. Mapping lives in each Beads issue's `--external-ref` field as the full Linear URL. To look up a Beads ID from a Linear KEI-N, query Beads with `bd list --json | jq` and filter by `external_ref` substring, OR query Linear via the API for the URL stored on the KEI.

### `bd remember` usage

Replaces ad-hoc memory pin proliferation. Use for facts that must survive `/compact` within a session AND don't fit any other store (not a directive, not a daily log, not a memory pin from Dave). Example: ratified architectural decisions that emerged mid-session; empirical findings that took >30 min to discover.

### Cross-store consistency

The directive counter, the Beads issue state, the Linear issue state, and the `cis_directive_metrics` row must stay consistent. Three sources of truth means every state change touches all three. If they diverge, Linear is the human-facing canonical source — sync the other two to match.
