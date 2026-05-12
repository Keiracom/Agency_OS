# Wave 2 Research — Drive Mirror Exit Code Persistence

**Source:** `scripts/three_store_save.py:336-347` (read fresh 2026-05-12, commit d9ffd2e3).

## Current state

```python
# L336-347
def run_drive_mirror(dry_run: bool) -> None:
    mirror_script = REPO_ROOT / "scripts" / "write_manual_mirror.py"
    if dry_run:
        print(f"[DRY-RUN][STORE 4/4] Would run: {sys.executable} {mirror_script}")
        return
    result = subprocess.run([sys.executable, str(mirror_script)], capture_output=True, text=True)
    if result.returncode == 0:
        print("[STORE 4/4] Drive mirror: OK")
    else:
        print(f"[STORE 4/4] Drive mirror: WARNING — exit {result.returncode}")
        if result.stderr:
            print(f"  stderr: {result.stderr.strip()[:200]}")
```

`result.returncode` is computed, printed to stdout, then discarded. No DB write, no file write, no return value. Nothing downstream can tell whether the mirror succeeded.

Function signature is `-> None` — even the caller in `main()` can't branch on it.

## Where it should be written

STORE 3 (the `cis_directive_metrics` insert) runs BEFORE STORE 4 (mirror), so we can't simply add a column to that insert — the row is already committed by the time we know the mirror's exit code.

Two viable persistence targets:

### Option A — Add column to `cis_directive_metrics`, write via UPDATE

```sql
ALTER TABLE public.cis_directive_metrics
ADD COLUMN drive_mirror_exit SMALLINT DEFAULT NULL,
ADD COLUMN drive_mirror_at   TIMESTAMPTZ DEFAULT NULL;
```

Then in `run_drive_mirror`:
```python
return result.returncode   # change signature to -> int
```
And in `main()` after `run_drive_mirror` returns, run `UPDATE cis_directive_metrics SET drive_mirror_exit=$1, drive_mirror_at=NOW() WHERE directive_id=$2`.

**Pros:** Co-located with all other directive completion data. Joinable with directive_id. Queryable across history ("how often does the mirror fail per directive?").
**Cons:** Schema migration. Requires another DB round-trip (~50ms). Couples directive metrics row to mirror lifecycle.

### Option B — Write to `ceo_memory` key `ceo:drive_mirror_last_exit`

```python
ceo_memory.upsert("ceo:drive_mirror_last_exit", {
    "exit": result.returncode,
    "stderr_tail": result.stderr[:200] if result.stderr else None,
    "ts": now.isoformat(),
    "directive_ref": directive_ref,
})
```

**Pros:** No migration. Idempotent upsert pattern already used elsewhere. Trivial to query (single key read). Fits the "current system state" mental model of ceo_memory.
**Cons:** Only the *most recent* exit is retained — no history. Per-directive correlation is in the value blob, not joinable. Stale if the key isn't updated on success.

## Recommendation

**Option A** for the Wave 2 fix. Audit Surprise #5 framed this as a metrics gap — drive mirror failures should be queryable historically, not just "did the last run fail?" The column add is cheap, the UPDATE is one extra query, and it preserves the LAW XV four-store narrative ("Drive mirror outcome is part of the directive's permanent record"). Pair it with Option B as a read-cache only if dashboards need sub-second access; otherwise skip B.

Implementation surface for Wave 2:
1. Alembic migration adding two columns.
2. Change `run_drive_mirror` signature to `-> int`.
3. UPDATE query in `main()` after mirror call (use same `directive_id` and asyncpg conn as STORE 3).
4. Backfill: leave NULL for historical rows; document that NULL = "pre-fix".
