# KEI-37 Design — CEO session boot state (single ceo_memory key)

**Author:** Aiden (design only — per Dave verbatim ts ~1778665450)
**Implementer:** Elliot (post-compact ratification + execute)
**Beads:** Agency_OS-qxsrht — P0
**Linear:** [KEI-37](https://linear.app/keiracom/issue/KEI-37)

## Problem

CEO session boot today fans out to 5+ stale sources (claude.ai memory edits, project knowledge, Drive Manual, 30+ fragmented ceo_memory keys, Linear board). Today's real failure: stale Linear/Beads state caused Dave to dispatch Aiden to Streams 3+4 while Max was already running them — Resolution A coordination thrash, two PRs of state-mismatch work (KEI-22 + KEI-39) to close the gap.

## Solution

One ceo_memory key, `ceo:boot_state_current`, that a new CEO session can query in ONE call and get a complete, current picture.

## Schema

```json
{
  "written_at": "2026-05-13T08:30:00Z",
  "written_by": "elliot",
  "build_phase": "Stream 3+4 ingest in flight; Track 1 close gated on VQ4",
  "active_keis": [
    {
      "id": "KEI-23",
      "title": "Cognee Lance writer-conflict",
      "status": "Done",
      "owner": "aiden",
      "blocking": false,
      "merged_pr": 826
    },
    {
      "id": "KEI-34",
      "title": "Orchestrator-discipline polling-loop",
      "status": "Done",
      "owner": "aiden",
      "blocking": false,
      "merged_pr": 824
    }
  ],
  "restart_gate": {
    "track_1_stream_2": "done",
    "track_1_stream_3": "in_progress",
    "track_1_stream_4": "in_progress",
    "track_2": "done",
    "track_3": "done",
    "atlas_test_restart": "pending",
    "dave_auth": "pending"
  },
  "needs_dave": [
    "Stream 3+4 completion notification",
    "VQ4 cross-stream pass ratification",
    "Atlas test-restart authorisation"
  ],
  "ratified_decisions": {
    "model_assignment": "ceo_memory:orchestration:model_assignment",
    "stage7_locked": "ceo_memory:ceo:stage7_locked",
    "concur_gate_release_pattern": "ceo_memory:ceo:concur_gate_release"
  },
  "drive_manual_id": "1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho",
  "supabase_project": "jatzvazlbusedwsnqxzr",
  "session_uuid_last": "0ee6d2f4-02b0-4a78-b183-3a4a4abddc3a"
}
```

### Design rationale on field shape

- `active_keis` is a list-of-dicts (not a map) — preserves insertion order which encodes priority sequencing.
- `restart_gate` is flat key-value with `track_1_stream_N` split — captures sub-track granularity (Stream 2 done while Stream 3+4 in flight) without nesting.
- `needs_dave` is a list of human-readable strings — CEO reads top-down + actions.
- `ratified_decisions` is a pointer map (ceo_memory:keys, not inlined values) — keeps boot_state small + forces explicit follow-up read for any decision the CEO is acting on (auditable).
- `session_uuid_last` enables KEI-31 (session UUID resume) cross-reference without a second query.

## Write triggers

Four write paths, ranked by frequency expectation:

1. **Hourly cron during peak hours (21:00–11:00 UTC ≈ 07:00–21:00 AEST)** — Elliot orchestrator polling-loop already runs minutely; add a once-per-hour write-fresh-snapshot side-effect when `now.minute == 0`. Implementation: extend `scripts/orchestrator/elliot_polling_loop.py` with a `_write_boot_state_snapshot()` function called from the cycle-top dispatch.
2. **On PR merge to main** — `.github/workflows/post-merge-update.yml` (new) triggers on `pull_request.closed && merged == true`; runs a small Python script that updates the snapshot. Or simpler: piggy-back on the post-merge auto-pull-main script already running on the host.
3. **On session end** — each agent session-end hook (`.claude/hooks/session_end.*`) updates the snapshot before the agent exits.
4. **On Dave directive completion** — after every ratified decision (LAW XV four-store completion), the boot-state snapshot is refreshed in the same pass.

### Write contention

Multiple writers (cron + merge hook + session end + directive completion) all targeting the same key. Per ceo_memory implementation (Supabase row upsert), last-write-wins. Acceptable because each writer constructs the FULL snapshot from authoritative sources (bd ready + linear + recent merge commits + Drive Manual), not partial diffs. No partial state propagation.

## Query pattern (new CEO boot path)

```sql
SELECT value
FROM public.ceo_memory
WHERE key = 'ceo:boot_state_current';
```

CEO session start:

1. **Read** the boot state in one call.
2. **Branch on `needs_dave`**: if non-empty, address each item before any build dispatch.
3. **Read Drive Manual** only for narrative context when boot_state references something unfamiliar (not as primary boot).
4. **Query specific ratified-decision keys** from `ratified_decisions` map as the CEO acts on them.

Old path (replaced): read Drive Manual first → query 30+ keys → reconstruct state manually.

## Acceptance criteria

- `ceo:boot_state_current` exists in `public.ceo_memory`.
- Never more than 60 minutes stale during peak hours (07:00–21:00 AEST).
- A new CEO session can read this one key and immediately know: what's in progress, what's blocking, what needs Dave, where the restart gate stands.
- claude.ai memory edits + project-knowledge files become supplementary only — not primary boot path.
- Atomic upsert (no partial-state propagation).

## Failure modes + mitigations

- **Stale (>60min)**: hourly cron missed. Mitigation — write also fires on every merge to main (10+ PRs/day current rate); even without cron, freshness stays under 2h on active days.
- **Conflict on multi-writer**: last-write-wins on upsert. Each writer constructs the full snapshot from authoritative sources → no partial-state divergence.
- **Schema drift**: introduce a `schema_version` integer field (default 1); CEO reader logs a warning if version > known.

## Implementation handoff for Elliot

Files to touch:

1. `scripts/orchestrator/elliot_polling_loop.py` — add `_write_boot_state_snapshot()` + hourly cycle-top call.
2. `scripts/post_merge_update_boot_state.py` (new) — single-file Python script invoked by `auto_pull_main.sh` or a GitHub workflow.
3. `.claude/hooks/session_end.sh` (per-callsign) — append boot-state-write call.
4. New ceo_memory key `ceo:boot_state_current` (schema seeded by first write).

Estimated: ~120 LoC + ~6 tests + 1 migration-style ceo_memory key seed.
