# Relay tmpfs → durable migration

**KEI-142** / `Agency_OS-jhdf25`. Operator runbook for moving per-callsign relay state from `/tmp/telegram-relay-<callsign>` (tmpfs — wiped on reboot, in-flight messages lost) to `/var/lib/agency-os/relay-<callsign>` (persistent disk).

The migration preserves the `/tmp/telegram-relay-<callsign>` path as a **symlink** to the durable directory, so the ~18 in-tree call sites that hardcode the tmpfs path keep working without code change. The symlinks are re-established on every boot by `systemd-tmpfiles` reading `/etc/tmpfiles.d/agency-os-relay.conf`.

---

## When to run

- One-time per host, during a maintenance window.
- After any host re-provision before agents start writing relay state.

## Who runs it

Operator with `sudo`. Atlas in normal deploys; Dave for emergencies.

## Prereqs

- Repo cloned at `/home/elliotbot/clawd/Agency_OS` (or any worktree).
- All inbox-watcher + relay-watcher systemd units stopped so nothing is writing to `/tmp/telegram-relay-*` mid-rsync.

---

## Steps

### 1. Stop the relay services

```bash
for cs in elliot aiden max orion atlas scout nova; do
    systemctl --user stop "${cs}-inbox-watcher.service" 2>/dev/null || true
    systemctl --user stop "${cs}-relay-watcher.service" 2>/dev/null || true
done
```

Verify all stopped:

```bash
systemctl --user list-units --state=running | grep -E '(inbox|relay)-watcher' || echo "all stopped"
```

### 2. Create the durable base directory (sudo, one-shot)

```bash
sudo install -d -m 755 -o elliotbot -g elliotbot /var/lib/agency-os
```

### 3. Install the tmpfiles config (sudo, one-shot)

```bash
sudo install -m 644 \
    infra/tmpfiles.d/agency-os-relay.conf \
    /etc/tmpfiles.d/agency-os-relay.conf
```

If the agent UID differs from `elliotbot:elliotbot` on this host, edit `/etc/tmpfiles.d/agency-os-relay.conf` to match before running step 4.

### 4. Run the migration

```bash
bash scripts/migrate_relay_tmpfs_to_durable.sh --all
```

Expected output (one line per callsign):

```
  elliot: copied data -> /var/lib/agency-os/relay-elliot; tmpfs dir parked at /tmp/telegram-relay-elliot.premigrate.<epoch>
  elliot: /tmp/telegram-relay-elliot -> /var/lib/agency-os/relay-elliot (symlinked)
  aiden: ...
  ...
migration: done.
```

Re-running on already-migrated callsigns is a no-op — the script reports `already migrated` and exits 0.

### 5. Verify

```bash
for cs in elliot aiden max orion atlas scout nova; do
    target=$(readlink -f "/tmp/telegram-relay-${cs}")
    expected="/var/lib/agency-os/relay-${cs}"
    if [[ "$target" == "$expected" ]]; then
        echo "  ${cs}: ✓ ${target}"
    else
        echo "  ${cs}: ✗ resolves to ${target} (expected ${expected})"
    fi
done
```

All 7 should show `✓`.

### 6. Restart the relay services

```bash
for cs in elliot aiden max orion atlas scout nova; do
    systemctl --user start "${cs}-inbox-watcher.service" 2>/dev/null || true
    systemctl --user start "${cs}-relay-watcher.service" 2>/dev/null || true
done
```

### 7. Reboot test (gated — schedule with Dave)

```bash
sudo reboot
# ... wait for host to come back ...

# Then on return:
for cs in elliot aiden max orion atlas scout nova; do
    test -L "/tmp/telegram-relay-${cs}" && echo "  ${cs}: symlink survived reboot ✓" \
        || echo "  ${cs}: symlink LOST ✗"
done
```

If any callsign shows `LOST`, `systemd-tmpfiles --create /etc/tmpfiles.d/agency-os-relay.conf` did not run — check `journalctl -b -u systemd-tmpfiles-setup.service` for the failure.

---

## Rollback

If a callsign needs to go back to plain-tmpfs (debugging):

```bash
rm /tmp/telegram-relay-<callsign>            # delete the symlink
mkdir -p /tmp/telegram-relay-<callsign>/{inbox,outbox,processed}
# Restore from the `.premigrate.<epoch>` backup if needed:
cp -a /tmp/telegram-relay-<callsign>.premigrate.<epoch>/* /tmp/telegram-relay-<callsign>/
```

To prevent the next boot's `systemd-tmpfiles` run from re-creating the symlink, comment the relevant `L+ /tmp/telegram-relay-<callsign>` line in `/etc/tmpfiles.d/agency-os-relay.conf`.

---

## Failure modes seen

| Symptom | Cause | Fix |
|---------|-------|-----|
| `FATAL: /var/lib/agency-os does not exist` | Step 2 skipped | Run step 2 |
| `FATAL: /var/lib/agency-os is not writable by elliotbot` | Wrong owner from step 2 | `sudo chown -R elliotbot:elliotbot /var/lib/agency-os` |
| Symlink not recreated after reboot | tmpfiles config missing or malformed | Re-run step 3, then `sudo systemd-tmpfiles --create /etc/tmpfiles.d/agency-os-relay.conf` |
| Service writes to a real `/tmp` dir instead of the symlink target | Service started before `systemd-tmpfiles-setup.service` ran (rare; default unit ordering avoids this) | Stop service, remove the bogus real dir, restart |
