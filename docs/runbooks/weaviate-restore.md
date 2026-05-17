# Weaviate restore procedure

KEI-60 — companion to `scripts/orchestrator/weaviate_backup.sh` daily snapshots.

## When to run

- Disk corruption or accidental deletion in `WEAVIATE_DATA_DIR`.
- Schema mistake that needs rollback to yesterday's state.
- Migrating to a new host.

The daily backup timer (`weaviate-backup.timer`) keeps 7 days of `.tar.gz`
archives at `/home/elliotbot/clawd/backups/weaviate/weaviate-YYYY-MM-DD.tar.gz`.

## Procedure

```bash
# 1. Identify the backup you want.
ls -la /home/elliotbot/clawd/backups/weaviate/
# weaviate-2026-05-13.tar.gz
# weaviate-2026-05-14.tar.gz   <-- example: restore from yesterday

# 2. Stop the Weaviate service so the restore writes to an idle data dir.
systemctl --user stop weaviate.service

# 3. Move the current data dir aside (do NOT delete — keep the broken state
#    in case the backup is also bad).
mv /home/elliotbot/clawd/weaviate-data \
   /home/elliotbot/clawd/weaviate-data.broken.$(date -u +%Y%m%dT%H%M%SZ)

# 4. Extract the chosen archive into the parent of the data dir.
#    Tar paths are relative to weaviate-data/ so this recreates the dir.
tar -xzf /home/elliotbot/clawd/backups/weaviate/weaviate-2026-05-13.tar.gz \
    -C /home/elliotbot/clawd/

# 5. Verify the data dir contents look right.
ls /home/elliotbot/clawd/weaviate-data/
du -sh /home/elliotbot/clawd/weaviate-data/

# 6. Start Weaviate.
systemctl --user start weaviate.service

# 7. Smoke probe — readiness + arbitrary collection query.
curl -s http://localhost:8090/v1/.well-known/ready
curl -s 'http://localhost:8090/v1/objects?limit=1' | python3 -m json.tool | head -20

# 8. If restore looks bad, the `.broken.<ts>` dir is still on disk for forensics.
#    To roll back to the broken state:
#    systemctl --user stop weaviate.service
#    mv /home/elliotbot/clawd/weaviate-data /home/elliotbot/clawd/weaviate-data.failed-restore
#    mv /home/elliotbot/clawd/weaviate-data.broken.<ts> /home/elliotbot/clawd/weaviate-data
#    systemctl --user start weaviate.service
```

## Acceptance test (KEI-60 verbatim)

> Weaviate container restarts. Data from before restart is still queryable.

Empirical probe pattern (used in PR #882 KEI-60 verification):

```bash
# Before restart — insert a unique sentinel object using Atlas's schema.
TEST_UUID=$(uuidgen)
curl -s -XPOST http://localhost:8090/v1/objects -H "Content-Type: application/json" \
    -d "{\"class\":\"AgentMessage\",\"id\":\"$TEST_UUID\",\"properties\":{\"content\":\"KEI-60 persistence probe\"}}"

# Restart.
systemctl --user restart weaviate.service
sleep 5
curl -s http://localhost:8090/v1/.well-known/ready

# Query — same UUID still returns the object.
curl -s "http://localhost:8090/v1/objects/$TEST_UUID"
```

If the GET returns the object, persistence works. If it returns 404, the
data dir was wiped (probably misconfigured `WEAVIATE_DATA_DIR` in
`weaviate_capped.sh` or a non-persistent volume).

## Caveats

- **No remote/offsite backup yet.** A full host-loss event loses all
  Weaviate data. Pre-revenue right-sizing per Dave directive — upgrade path
  when revenue funds offsite storage.
- **Backup runs against a live data dir** by default. Brief inconsistency
  window — acceptable for current scale, would need a quiesce-stop-snapshot
  loop at prod-scale.
- **7-day retention is conservative.** Lengthen via `AGENCY_OS_BACKUP_RETENTION_DAYS`
  in `/home/elliotbot/.config/agency-os/.env`.
