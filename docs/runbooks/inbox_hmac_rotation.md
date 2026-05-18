# Inbox HMAC Secret Rotation — KEI-138

End-to-end SOP for rotating `INBOX_HMAC_SECRET` without dropping in-flight dispatches.

## When to run

- Quarterly hygiene rotation.
- Immediately on any suspected compromise of `~/.config/agency-os/.env` or the relay host.
- After offboarding any operator who had host access.

## Threat model recap (per `src/security/inbox_hmac.py` docstring)

> Tamper detection against corrupted or accidentally-written files, NOT authentication against a malicious insider with shell access. Anyone who can read the shared secret can also sign. Per-writer keys in Supabase Vault is the follow-up.

This runbook does NOT defend against an attacker with shell access on the relay host — they have the secret regardless. It rotates the shared symmetric key to limit blast radius if `.env` leaks.

## Dual-secret window

`src/security/inbox_hmac.verify_dict()` accepts payloads signed with **either** `INBOX_HMAC_SECRET` (slot 0) or `INBOX_HMAC_SECRET_PREV` (slot 1). During the rotation window:

- Producers (e.g. `scripts/sign_dispatch.py`) sign with the new secret as soon as it lands in env.
- Consumer (`src/relay/relay_consumer.py`) accepts both — `public.dispatch_audit_log.secret_index` records which one was used.
- After all observed traffic has `secret_index = 0` for >24h, `INBOX_HMAC_SECRET_PREV` is unset.

## Procedure

### 1. Generate new secret

```bash
openssl rand -hex 32 > /tmp/inbox_hmac_new.secret
chmod 600 /tmp/inbox_hmac_new.secret
```

Treat `/tmp/inbox_hmac_new.secret` as secret-equivalent to `TELEGRAM_BOT_TOKEN`. Do not commit, do not paste in chat, do not leave on disk longer than needed.

### 2. Promote current → previous in env

Open `~/.config/agency-os/.env`:

```bash
# Before
INBOX_HMAC_SECRET=<OLD_VALUE>

# After
INBOX_HMAC_SECRET=<NEW_VALUE_FROM_STEP_1>
INBOX_HMAC_SECRET_PREV=<OLD_VALUE>
```

Order matters: the new value goes in the primary slot, the old goes to PREV.

### 3. Restart relay consumer

`src/relay/relay_consumer.py` reads env on startup; no hot reload. Restart the systemd service:

```bash
systemctl --user restart relay-consumer.service
journalctl --user -u relay-consumer.service -f -n 50
```

Watch for:

```
[relay-consumer] ... INFO Consumer started: dispatch:atlas → atlas:0.0
[relay-consumer] ... INFO Consumer started: dispatch:orion → orion:0.0
```

### 4. Restart signers

Any process that signs dispatches must read the new env. In practice that's:

- Orchestrator agents (Elliot, Max) — call `bash scripts/restart_<agent>.sh` per agent.
- Any operator running `scripts/sign_dispatch.py --target <clone>` from a fresh shell automatically uses the new env.

### 5. Validate end-to-end via audit log

Run a synthetic dispatch through `scripts/sign_dispatch.py`, then query:

```sql
SELECT created_at, queue, hmac_status, secret_index, reason
  FROM public.dispatch_audit_log
 WHERE created_at >= NOW() - INTERVAL '5 minutes'
 ORDER BY created_at DESC
 LIMIT 20;
```

Expected:

- New synthetic dispatch: `hmac_status='signed_verified'`, `secret_index=0`.
- Any in-flight dispatch from before the restart still verifies — but with `secret_index=1` (signed with PREV).

### 6. Signed-vs-unsigned ratio check

```sql
SELECT hmac_status, secret_index, COUNT(*) AS n
  FROM public.dispatch_audit_log
 WHERE created_at >= NOW() - INTERVAL '1 hour'
 GROUP BY hmac_status, secret_index
 ORDER BY n DESC;
```

Healthy ratio: `signed_verified / secret_index=0` dominates; `unsigned` and `signed_invalid` should be 0. Any non-zero `signed_invalid` is the alert signal — investigate.

### 7. Close the rotation window

Re-run the query from step 5 every few hours. When you see **>24 hours of zero rows with `secret_index=1`**:

```bash
# Remove the PREV line from ~/.config/agency-os/.env
sed -i '/^INBOX_HMAC_SECRET_PREV=/d' ~/.config/agency-os/.env

systemctl --user restart relay-consumer.service
```

Confirm via `verify_dict` that PREV is empty:

```bash
INBOX_HMAC_SECRET_PREV= python3 -c "from src.security.inbox_hmac import _rotation_secrets; print(_rotation_secrets(None))"
# Should print [primary] — one element only.
```

## Rollback (if step 5 shows signed_invalid spikes)

`signed_invalid` on the first dispatch after rotation means the signer didn't pick up the new env. Two options:

**Fast revert:**

```bash
# Swap PRIMARY and PREV in ~/.config/agency-os/.env, then:
systemctl --user restart relay-consumer.service
```

This makes the OLD secret primary again. Producers signing with the new secret still verify (slot=1). Investigate why the signer didn't re-read env, then retry from step 1.

**Forensic mode:**

```sql
SELECT queue, target, reason, payload_hash, created_at
  FROM public.dispatch_audit_log
 WHERE hmac_status = 'signed_invalid'
   AND created_at >= NOW() - INTERVAL '30 minutes'
 ORDER BY created_at DESC;
```

Cross-reference `payload_hash` with `scripts/sign_dispatch.py` output to identify the misconfigured signer.

## Cleanup

```bash
shred -u /tmp/inbox_hmac_new.secret  # zero the on-disk copy of the new secret
```

## Verification commands cheat sheet

```bash
# Pre-rotation: confirm current secret is in env
[ -n "$INBOX_HMAC_SECRET" ] && echo "primary set"

# Mid-rotation: confirm both slots populated
[ -n "$INBOX_HMAC_SECRET" ] && [ -n "$INBOX_HMAC_SECRET_PREV" ] && echo "rotation window active"

# Post-rotation: confirm PREV cleared
[ -n "$INBOX_HMAC_SECRET" ] && [ -z "$INBOX_HMAC_SECRET_PREV" ] && echo "rotation closed"
```

## References

- `src/security/inbox_hmac.py` — `sign()`, `verify()`, `verify_dict()`, `canonical_hash()`, `_rotation_secrets()`.
- `src/security/dispatch_audit.py` — fail-open writer for `public.dispatch_audit_log`.
- `src/relay/relay_consumer.py` — calls `_classify_dispatch()` + `_audit_async()` on every dispatch pop.
- `supabase/migrations/20260518_kei138_dispatch_audit_log.sql` — schema + indexes.
- KEI-138 Linear: <https://linear.app/keiracom/issue/KEI-138>
