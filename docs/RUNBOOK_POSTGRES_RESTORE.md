# Postgres Restore Runbook (KEI-126)

**Purpose:** Restore the Supabase production DB from a nightly snapshot in Vultr Object Store. Quarterly drill recovery target: **<10 minutes from snapshot URL to verified DB**.

**KEI:** [KEI-126](https://linear.app/keiracom/issue/KEI-126) — Nightly pg_dump to S3 + restore runbook.

---

## When to use this

- Catastrophic data loss in production (DROP TABLE without WHERE, schema migration that lost rows, etc.).
- Quarterly restore-to-staging drill (verifies the backup chain is alive).
- Forensics: spin up a snapshot in isolation to investigate a historical state.

---

## Prerequisites

You need access to:
- Vultr Object Store credentials (same `AWS_*` vars as the backup script).
- A target Postgres instance to restore INTO (staging branch, NOT production unless you're doing intentional rollback).
- `pg_restore` + `aws` CLI on your workstation.

The backup script ships snapshots at:
```
s3://${AWS_S3_BUCKET}/postgres/YYYY-MM-DDTHH-MM-SSZ.dump
```

---

## Restore procedure

### 1. List available snapshots

```bash
aws s3 ls "s3://${AWS_S3_BUCKET}/postgres/" \
    --endpoint-url "${AWS_S3_ENDPOINT}"
```

Pick the snapshot you want to restore. Retention is 7 days — older snapshots are pruned automatically.

### 2. Download the snapshot

```bash
SNAPSHOT_KEY="postgres/2026-05-18T01-00-00Z.dump"   # replace with actual key
aws s3 cp "s3://${AWS_S3_BUCKET}/${SNAPSHOT_KEY}" \
    "/tmp/postgres-restore.dump" \
    --endpoint-url "${AWS_S3_ENDPOINT}" \
    --only-show-errors

ls -lh /tmp/postgres-restore.dump   # sanity-check non-zero size
```

### 3. Create restore target

**STRONGLY RECOMMENDED:** restore into a Supabase branch DB, not the live prod project. Branch via:

```bash
# Via Supabase MCP (preferred):
mcp__supabase__create_branch --name "restore-drill-$(date -u +%Y%m%d)"

# OR via CLI:
supabase branches create "restore-drill-$(date -u +%Y%m%d)"
```

Capture the branch's DSN — that's your `RESTORE_DSN` below.

### 4. Restore

```bash
# Strip +asyncpg suffix if present.
RESTORE_DSN="${RESTORE_DSN/+asyncpg/}"

pg_restore \
    --dbname="${RESTORE_DSN}" \
    --no-owner \
    --no-acl \
    --clean \
    --if-exists \
    --jobs=4 \
    /tmp/postgres-restore.dump
```

`--jobs=4` parallel-restores 4 tables at a time — the dump is `-Fc` custom format which supports this.

### 5. Verify

```bash
psql "${RESTORE_DSN}" -c "
    SELECT
        (SELECT COUNT(*) FROM public.tasks) AS tasks_count,
        (SELECT COUNT(*) FROM public.customer_subscriptions) AS subs_count,
        (SELECT COUNT(*) FROM public.agent_memories) AS memories_count,
        (SELECT MAX(created_at) FROM public.agent_memories) AS most_recent_memory;
"
```

Expected: row counts in the same order of magnitude as production at snapshot time. `most_recent_memory` should equal roughly the snapshot timestamp (01:00 UTC on the snapshot date).

### 6. Cleanup (if you restored to a branch for drill)

```bash
mcp__supabase__delete_branch --branch_id <id>
# OR
supabase branches delete restore-drill-<date>

rm /tmp/postgres-restore.dump
```

---

## Quarterly drill checklist

Run the following every 90 days. File as `KEI-126-drill-YYYYMM` in Linear with the verified output.

- [ ] List snapshots — confirm 7 days present (no gaps)
- [ ] Download yesterday's snapshot — confirm download <5min
- [ ] Restore to fresh Supabase branch — record wall-clock time
- [ ] Verify row counts match expected magnitude
- [ ] Verify `most_recent_memory` timestamp matches snapshot
- [ ] **Total wall-clock <10 minutes** — acceptance criterion
- [ ] Delete drill branch
- [ ] Post drill outcome to #ceo (Dave's audit signal)

If wall-clock exceeds 10 minutes, file a sibling KEI to investigate (snapshot size growth, network throughput, parallelism tuning).

---

## Failure modes + responses

### "no snapshots in bucket"

- Check that `postgres-backup.timer` is enabled: `systemctl --user list-timers postgres-backup.timer`
- Check the latest run: `journalctl --user -u postgres-backup.service --since today`
- Most common cause: missing `AWS_*` env in `.env`; reinstall via `bash scripts/install_postgres_backup.sh`.

### "pg_restore fails with role/owner errors"

- The `--no-owner --no-acl` flags should prevent this. If still failing:
- Verify the dump was created with `--no-owner --no-acl` (check `backup_postgres.sh`).
- Try restoring with `--role=postgres` if a specific role is referenced.

### "restore wall-clock >10 minutes"

- Check parallelism — `--jobs=4` may need bump.
- Check network throughput from your workstation to the restore target.
- Snapshot size may have grown; if >5GB, consider partial-restore by schema:
  ```bash
  pg_restore --schema=public --dbname=... snapshot.dump
  ```
- File `KEI-126` follow-up for restore-target right-sizing.

---

## Files

| Path | Purpose |
|---|---|
| `scripts/backup_postgres.sh` | Daily `pg_dump` + S3 upload + 7d retention prune |
| `scripts/install_postgres_backup.sh` | KEI-108-compliant install wrapper |
| `infra/systemd/agents/postgres-backup.service` | `Type=oneshot` unit run by the timer |
| `infra/systemd/agents/postgres-backup.timer` | `OnCalendar=*-*-* 01:00:00 UTC` daily timer |
| `docs/RUNBOOK_POSTGRES_RESTORE.md` | This runbook |
