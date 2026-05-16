# KEI-78 — Dependency auto-unblock + mandatory `dependencies[]` rule

Ratified 2026-05-16 by Dave directive after a Scout-coordination gap left a
KEI sitting blocked even though its dep had merged.

## What the trigger does

`public.tasks` has an `AFTER UPDATE OF status` trigger. When any task X
transitions to `status='done'`, `public.fn_unblock_dependents(X.id)` runs:

1. Find every task Y where `X.id = ANY(Y.dependencies)` and `Y.status='blocked'`.
2. For each Y, check **every** element of `Y.dependencies` joins to a
   `tasks.status='done'` row. NULL FK (orphan dep) counts as not-done — safer
   than silently unblocking on a broken reference.
3. Flip qualifying Y's to `status='available'`, bump `updated_at`.

Supabase Realtime (KEI-45) fans the change out; idle agents claim from the
queue without manual dispatch.

The trigger is idempotent. Re-running `fn_unblock_dependents` on the same task
id no-ops once the dependent is already `available`.

## Governance rule (Dave 2026-05-16T11:52Z)

> When filing a task that depends on another agent's work, `dependencies[]`
> array MUST be populated at creation time. Not optional.

All future `INSERT INTO public.tasks` calls without `dependencies` populated
on cross-agent work are governance violations. Use one of:

```sql
INSERT INTO public.tasks (id, title, dependencies, ...)
VALUES ('KEI-XX', '...', ARRAY['KEI-YY','KEI-ZZ'], ...);
```

or

```bash
bd create --title "..." --deps KEI-YY,KEI-ZZ
```

(the `bd create` shim translates `--deps` into the `dependencies` array.)

## Retroactive backfill

`scripts/orchestrator/dependency_unblock_backfill.py` runs the same SQL
function over every currently-blocked task's dep set. Safe to re-run.

```bash
python3 scripts/orchestrator/dependency_unblock_backfill.py --dry-run
python3 scripts/orchestrator/dependency_unblock_backfill.py
```

## Operator overrides

Manual closure via `tasks_cli complete` or direct `UPDATE` still fires the
trigger because the trigger keys off `OF status`, not on the calling code
path. To intentionally hold a task `blocked` past its deps' completion, set
`status='blocked_hold'` (not enumerated; the trigger only fires on
`done`-transitions of the **upstream** task, so a downstream's manual hold
doesn't get auto-flipped).

## Tie to KEI-74

`KEI-74` ships the `completion_sync_queue` for downstream stores (Linear /
ceo_memory / Drive Manual). This trigger handles the upstream side — when
something closes, dependents free up. Both triggers fire on the same status
transition; no contention because each operates on distinct rows.
