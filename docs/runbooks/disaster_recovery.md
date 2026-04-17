# Disaster Recovery Runbook

**Scope:** restoring the Agency OS Supabase database after data loss or project unavailability.

**Owner:** Dave (CEO). Execute personally or direct a bot to assist.

**Last reviewed:** 2026-04-17 (Wave 1 item #4). Re-validate with a drill every 30 days.

---

## Recovery paths (in order of preference)

### Path 1 — Supabase native Point-in-Time Recovery (PITR)

**Use when:** accidental DELETE/UPDATE, data corruption within the last 7 days, Supabase project still accessible.

- Supabase Pro plan automatically retains daily backups + PITR for **7 days**.
- Restore from the Supabase dashboard: Project Settings → Database → Backups → Restore.
- **RTO:** ~30 minutes (Supabase creates a new project/branch with restored state).
- **RPO:** up to ~24 hours, reduced by using PITR to pick a specific point in time.

**Limits:** Only works while the Supabase project exists. Cannot recover from account suspension, project deletion, or billing lockout.

### Path 2 — Offsite pg_dump restore

**Use when:** Supabase project deleted/suspended, older than 7-day PITR window, Supabase-wide outage.

- Backups produced by `scripts/backup_offsite.sh`, stored at `${BACKUP_DESTINATION}` (see env for current value).
- Frequency: manual until Dave enables the weekly schedule in `.github/workflows/backup-offsite.yml`.
- **RTO:** ~1–2 hours (fresh Supabase project + restore + re-wire env vars).
- **RPO:** interval between scheduled runs (target: weekly once enabled).

**Restore procedure:**

```bash
# 1. Download the most recent dump (adjust CLI for b2/gs destinations)
aws s3 ls s3://YOUR-BUCKET/ --recursive | tail -5   # find latest
aws s3 cp s3://YOUR-BUCKET/agency-os-backup-YYYYMMDDTHHMMSSZ.sql.gz ./restore.sql.gz

# 2. Decompress
gunzip restore.sql.gz

# 3. Provision a new Supabase project and capture its postgres URL
#    (Dashboard → New Project → Settings → Database → Connection string)
export NEW_DB_URL="postgresql://postgres:...@db.NEW-PROJECT-REF.supabase.co:5432/postgres"

# 4. Restore
psql "${NEW_DB_URL}" < restore.sql

# 5. Verify key row counts
psql "${NEW_DB_URL}" -c "SELECT 'leads', COUNT(*) FROM leads
                         UNION ALL SELECT 'clients', COUNT(*) FROM clients
                         UNION ALL SELECT 'ceo_memory', COUNT(*) FROM ceo_memory
                         UNION ALL SELECT 'cis_directive_metrics', COUNT(*) FROM cis_directive_metrics;"

# 6. Update application env vars
#    - ~/.config/agency-os/.env: SUPABASE_URL + SUPABASE_SERVICE_KEY
#    - Railway environment variables (same)
#    - Vercel environment variables (same)
#    - GitHub Actions secrets if they reference the old project
```

### Path 3 — Reconstruct from git + Drive Manual

**Use when:** catastrophic loss of both Supabase + all offsite backups.

- Repo on GitHub contains every migration + schema. Re-run migrations on a fresh Supabase project:
  ```bash
  cd supabase && supabase db push  # or: manual psql < each migration file
  ```
- Drive Manual (`docs/MANUAL.md` mirrored to Google Drive) contains current state notes.
- `ceo_memory` and `cis_directive_metrics` will be empty — manually re-seed from Manual + elliot_internal.memories if those Supabase memories survived.
- **RTO:** days. **RPO:** effectively "everything operational is lost; only code + human memory remain."

---

## Pre-requisites (configure before a real incident)

1. **Supabase DB connection string** — set `SUPABASE_DB_URL` in GitHub repo secrets AND in Dave's local `.env`.
2. **Offsite destination** — choose and provision one:
   - S3: create bucket, issue IAM user with `s3:PutObject` + `s3:GetObject` on that bucket only, set secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `BACKUP_DESTINATION=s3://bucket/agency-os/`.
   - Backblaze B2: create bucket + application key; `rclone config` locally to create `b2-remote`; `BACKUP_DESTINATION=b2://bucket/agency-os/`.
   - GCS: create bucket + service account JSON; `BACKUP_DESTINATION=gs://bucket/agency-os/`.
3. **First manual run** — trigger the workflow manually (GitHub Actions → Offsite DB Backup → Run workflow). Confirm the dump arrives at the destination.
4. **First restore drill** — see below. Do NOT enable the schedule until the drill completes.
5. **Enable schedule** — uncomment the `schedule:` block in `.github/workflows/backup-offsite.yml` (weekly Sunday 17:00 UTC default).

---

## Monthly restore drill (target ~30 min each)

1. Pick the most recent offsite backup.
2. Provision a throwaway Supabase project ("agency-os-drill-YYYYMMDD").
3. Execute the Path 2 restore procedure.
4. Verify row counts match the source counts recorded at backup time.
5. Record in `docs/runbooks/restore_drill_log.md`: date, backup used, RTO actual, any issues.
6. Delete the throwaway project.

**Purpose:** drills catch two classes of rot — (a) the backup script silently writing corrupted dumps, and (b) the restore procedure drifting out of sync with schema migrations. A backup you haven't restored is not a backup.

---

## What's NOT covered here

- **Application credentials loss** — if the VPS or Railway account is lost, recover those from password manager. This runbook covers DB only.
- **Supabase account recovery** — outside our control; Supabase support.
- **GitHub loss** — GitHub is effectively an offsite backup of code. If GitHub itself is lost, pull from local clone.

---

## Governance

- LAW XV-B: this runbook satisfies the Dave-visible DoD for Wave 1 item #4. A successful restore drill is the proof artifact.
- LAW XVI: changes to this runbook go through PR review.
- Revision history lives in git.
