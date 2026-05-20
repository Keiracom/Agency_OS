# HMAC Secret Rotation — `INBOX_HMAC_SECRET`

KEI-138 runbook. Rotate the shared HMAC secret without dropping any in-flight inbox dispatch.

## When to rotate

- Routine: every 90 days
- Suspected leak (env file accessed by unfamiliar process, secret pasted in a chat, host taken offline)
- After any contributor with `.env` read access leaves the project

## Pre-conditions

- Migration `20260518_kei138_dispatch_audit.sql` applied (table `public.dispatch_audit` + view `public.dispatch_signature_metrics` present).
- Audit emission wired in `scripts/sign_dispatch.py` and `src/relay/relay_consumer.py` (this is now baseline — KEI-138 merged).
- You have shell access to every host running an `inbox-watcher` or `relay-consumer` systemd unit.

## Step-by-step

### 1. Generate the new secret

```bash
new_secret="$(openssl rand -hex 32)"
echo "$new_secret"  # copy now — only visible once
```

### 2. Note the old fingerprint (before you change anything)

```bash
python3 -c "
import hashlib, os
old=os.environ.get('INBOX_HMAC_SECRET','')
print('old fingerprint:', hashlib.sha256(old.encode()).hexdigest()[:12])
"
```

Record this — you'll use it to confirm rotation completion in step 6.

### 3. Open the rotation window — set BOTH secrets

Update `~/.config/agency-os/.env` on every host:

```bash
INBOX_HMAC_SECRET="<new secret from step 1>"
INBOX_HMAC_SECRET_PREVIOUS="<the old secret>"
```

Order matters: `INBOX_HMAC_SECRET` becomes the **new** value; `INBOX_HMAC_SECRET_PREVIOUS` holds the **old** one. `verify()` and `relay_consumer._hmac_verify_dict` automatically accept payloads signed with either during the window.

### 4. Restart all consumers and signers

```bash
systemctl --user restart \
  elliot-inbox-watcher.service \
  aiden-inbox-watcher.service \
  scout-inbox-watcher.service \
  max-inbox-watcher.service \
  atlas-inbox-watcher.service \
  orion-inbox-watcher.service \
  relay-consumer.service
```

All new dispatches will now sign with the new secret. In-flight dispatches still on disk or in Redis (signed with the old secret) will verify cleanly via the `_PREVIOUS` fallback.

### 5. Drain the old-fingerprint window

Wait until you are confident every in-flight dispatch has been consumed. Typical window:

- File queues drain on the order of seconds
- Redis dispatch queues drain within minutes of restart
- 30 minutes is a conservative ceiling unless a tmux session is stuck (check `bd ready` / `tmux ls`)

### 6. Verify rotation completion via `dispatch_signature_metrics`

Query the audit view, scoped to the last 30 minutes and the OLD fingerprint:

```sql
SELECT hour, target, result, secret_fingerprint, dispatches
  FROM public.dispatch_signature_metrics
 WHERE secret_fingerprint = '<old fp from step 2>'
   AND hour >= NOW() - INTERVAL '30 minutes';
```

**Expected:** `0 rows`. If any rows appear, a consumer is still using the old secret — identify the `target`, restart that unit, wait, re-query.

### 7. Close the rotation window — remove `INBOX_HMAC_SECRET_PREVIOUS`

Once step 6 returns empty, edit `~/.config/agency-os/.env` on every host:

- Delete the `INBOX_HMAC_SECRET_PREVIOUS=…` line.

Restart consumers + signers one more time:

```bash
systemctl --user restart \
  '*-inbox-watcher.service' \
  relay-consumer.service
```

From this point any dispatch signed with the old secret will be REJECTED (logged at WARNING + audit row with `result='mismatch'`).

### 8. Capture rotation completion in `dispatch_audit`

For the post-incident report, the rotation event itself is reconstructable from the `dispatch_audit` table — the `secret_fingerprint` column transitions cleanly from old → new at the timestamp of the step-4 restart. No separate event log is needed.

## Rollback

If anything misbehaves between steps 3 and 7:

1. Swap `INBOX_HMAC_SECRET` and `INBOX_HMAC_SECRET_PREVIOUS` values in `.env` (the OLD secret becomes current again, the NEW one becomes the fallback).
2. Restart all consumers + signers.
3. The old secret regains primary status; the new one is the rotation companion.
4. Investigate the failure, then restart the rotation from step 1.

The dual-key window means rotation is reversible without dropping any dispatch.

## Observability snippets

Live verify outcomes by signature posture (last hour):

```sql
SELECT result, secret_fingerprint, COUNT(*)
  FROM public.dispatch_audit
 WHERE action = 'verify' AND ts >= NOW() - INTERVAL '1 hour'
 GROUP BY result, secret_fingerprint
 ORDER BY COUNT(*) DESC;
```

Unsigned-dispatch alerting (any non-zero count is suspicious):

```sql
SELECT COUNT(*)
  FROM public.dispatch_audit
 WHERE action = 'verify' AND result = 'unsigned'
   AND ts >= NOW() - INTERVAL '15 minutes';
```

Per-target signer breakdown (catch a misconfigured signer that's never been migrated):

```sql
SELECT target, actor, secret_fingerprint, COUNT(*)
  FROM public.dispatch_audit
 WHERE action = 'sign' AND ts >= NOW() - INTERVAL '24 hours'
 GROUP BY target, actor, secret_fingerprint
 ORDER BY target, actor;
```
