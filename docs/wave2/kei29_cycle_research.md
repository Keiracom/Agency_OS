# KEI-29 — Weekly Linear cycle from bd ready (research phase)

KEI-29 verbatim (Linear GraphQL): *"Weekly, Elliot auto-populates a Linear cycle from `bd ready` output. Shows a week's planned work at a glance. Runs every Monday 07:00 AEST via systemd timer."*

## Linear Cycle API — empirically probed

`__type(CycleCreateInput)` fields (introspected `api.linear.app/graphql`):

| Field | Type | Required |
|---|---|---|
| `id` | UUID v4 | optional (server-generated) |
| `name` | String | optional |
| `description` | String | optional |
| `teamId` | String | **REQUIRED** |
| `startsAt` | DateTime | **REQUIRED** |
| `endsAt` | DateTime | **REQUIRED** |
| `completedAt` | DateTime | optional |

Available cycle mutations: `cycleCreate`, `cycleUpdate`, `cycleArchive`, `cycleShiftAll`, `cycleStartUpcomingCycleToday`, `teamCyclesDelete`.

Adding an issue to a cycle: there is **no dedicated `cycleAddIssue` mutation**. Use `issueUpdate(id: $issueId, input: {cycleId: $cycleUUID})` per issue. One mutation per issue (N round-trips per cycle population) — acceptable for the small N our weekly cycle will hold.

KEI team UUID (verified): `4686528f-ce77-4c2f-968b-3dc76b34d6fe`.

## bd ready --json shape — re-verified

Fields present per issue (verified 2026-05-13): `id, title, description, status, priority, issue_type, created_at, updated_at, started_at, external_ref, metadata, dependency_count, dependent_count, comment_count`.

The **`external_ref`** field holds `https://linear.app/keiracom/issue/KEI-N` — that's the human identifier, **not** the Linear UUID needed for `issueUpdate`. Resolution path: GraphQL `query { issues(filter: {team: {key: {eq: "KEI"}}, number: {eq: $N}}) { nodes { id } } }` to translate `KEI-N → UUID`. One extra round-trip per bd item.

## Cadence + idempotency

- **Trigger:** systemd user-timer `OnCalendar=Sun *-*-* 21:00:00` (Monday 07:00 AEST = Sunday 21:00 UTC + AEST=UTC+10). Pair `.service` with `Type=oneshot`, ExecStart at the new script.
- **Cycle window:** `startsAt = next Monday 07:00 AEST`, `endsAt = following Monday 07:00 AEST` (7-day cycle).
- **Idempotency:** before `cycleCreate`, query `team(id: $kei).cycles(filter: {startsAt: {eq: $monday}})` — if a cycle exists with the target `startsAt`, skip create and re-use its UUID to top-up issues. Prevents duplicate cycle on cron-double-fire or operator re-run.
- **Operator override:** allow `--force-now` flag for manual mid-week runs (creates an "ad-hoc" cycle outside the Monday cadence).

## Selection policy — open question

KEI-29 says "auto-populated from `bd ready`" but doesn't specify selection. Three options:
1. **All `bd ready` items** at trigger time. Simple; risks 30-item cycles.
2. **Top-N by `priority`** (N=10 default, env-overridable). Bounded; needs tiebreaker (suggest `priority ASC, updated_at DESC`).
3. **Top-N filtered to `bd_ready ∧ has_external_ref`** — skip bd-only items that aren't yet Linear-tracked. Recommended, since cycles are a Linear-side concept.

Recommend option 3 with N=10 default.

## Existing wiring to lean on

- `scripts/linear_to_bd.py` — Linear → bd direction (read). Pattern to mirror for auth + GraphQL POST.
- `scripts/betterstack_to_linear.py` — BS → Linear issue create. Has the LINEAR_API_KEY + GraphQL writer pattern.
- No existing cycle-writer in repo (grep `cycleCreate` = zero hits).

## Open questions for Dave green-light before build

1. **Selection policy** — Option 3 (top-10 by priority, has-external-ref) or override?
2. **Cycle name template** — `"KEI Week of YYYY-MM-DD"` or shorter?
3. **What to do with last week's incomplete cycle items** — auto-roll into new cycle, or leave as-is?
4. **Mid-week new-ready items** — top up the current cycle on subsequent timer fires (idempotent re-fill), or only populate on Monday?

Recommend defaults: name `KEI Week of <Mon date>`, no roll-over (let prior cycle archive naturally), no mid-week top-up (Monday is the cadence; deviation = operator manual trigger).

## Proposed build shape (~150–200 LoC)

- `scripts/orchestrator/weekly_cycle_from_bd.py` (script).
- `systemd/user/weekly-cycle-from-bd.{timer,service}` (timer unit).
- `tests/scripts/test_weekly_cycle_from_bd.py` covering: cycle-create happy path, idempotent skip on existing cycle, empty `bd ready` (no cycle created — no-op log), bd-item-without-external-ref (skipped), Linear API error (logged, no partial state).

Awaiting Dave green-light on the 4 open questions before build phase.
