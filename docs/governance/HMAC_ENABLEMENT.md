# Inbox HMAC Enablement — 4-Step Rollout

**Status:** design only. Current production state is **unsigned dispatch accepted**: the atlas/orion inbox-watcher services skip HMAC verification when `INBOX_HMAC_SECRET` is unset in their environment. This document records the steps to flip on signed-only dispatch without dropping in-flight work.

**Approved by Dave:** 2026-05-07 (LAW XVIII directive).

**Related files:**
- `scripts/sign_dispatch.py` — already supports `--target {atlas,orion}` and HMAC signing.
- `src/security/inbox_hmac.py` — `sign()` / `verify()` primitives.
- `scripts/dispatch_to_atlas.sh` — currently writes unsigned JSON. Switches to `sign_dispatch.py` after Step 4.

---

## Step 1 — Generate the secret

On the host running watchers (production), generate a 256-bit hex secret:

```bash
openssl rand -hex 32 > /tmp/inbox_hmac_secret.txt
chmod 600 /tmp/inbox_hmac_secret.txt
cat /tmp/inbox_hmac_secret.txt   # copy the value, then shred the file
shred -u /tmp/inbox_hmac_secret.txt
```

Add to `~/.config/agency-os/.env` so `scripts/sign_dispatch.py` auto-loads it on every dispatch:

```
INBOX_HMAC_SECRET=<paste-the-hex>
```

`chmod 600 ~/.config/agency-os/.env` if not already restricted.

---

## Step 2 — Set the secret in watcher service env

Each watcher unit (`atlas-inbox-watcher.service`, `orion-inbox-watcher.service`) must see `INBOX_HMAC_SECRET` at startup. Two equivalent options:

### Option A — drop-in override (preferred)

```bash
sudo systemctl edit atlas-inbox-watcher.service
```

Add:
```
[Service]
Environment="INBOX_HMAC_SECRET=<paste-the-hex>"
```

Repeat for `orion-inbox-watcher.service`. Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart atlas-inbox-watcher.service orion-inbox-watcher.service
```

### Option B — shared EnvironmentFile

```bash
echo "INBOX_HMAC_SECRET=<paste-the-hex>" | sudo tee /etc/agency-os/watcher.env
sudo chmod 600 /etc/agency-os/watcher.env
sudo chown root:root /etc/agency-os/watcher.env
```

In each unit:
```
[Service]
EnvironmentFile=/etc/agency-os/watcher.env
```

Verify the secret reached the process:

```bash
sudo systemctl show atlas-inbox-watcher.service -p Environment | grep -c INBOX_HMAC_SECRET
# expect: 1
```

---

## Step 3 — Audit `sign_dispatch.py` callers

`scripts/sign_dispatch.py` already takes `--target {atlas,orion}` (see line 53). The work in this step is to **audit every caller** so `--target` is set explicitly — never relying on a default — and so dispatch wrappers route to the right inbox.

Callers to audit:

- [ ] `scripts/dispatch_to_atlas.sh` — currently unsigned. After Step 4, switch the JSON-build block to:
  ```bash
  python3 scripts/sign_dispatch.py \
      --target atlas \
      --from "$FROM_CALLSIGN" \
      --brief "$BRIEF" \
      --task-ref "$TASK_REF" \
      --max-task-minutes "$MAX_MINUTES"
  ```
- [ ] Any future `scripts/dispatch_to_orion.sh` — same pattern, `--target orion`.
- [ ] Manual operator commands in `docs/runbooks/` and the Manual — grep for `sign_dispatch.py` and `--target`.
- [ ] CI scripts (if any) that dispatch tasks.

**Do not switch wrappers to signed-only until Step 4's dual-accept window is open** — otherwise existing unsigned dispatches in the inbox will be rejected.

---

## Step 4 — Flip-day rollout (dual-accept → signed-only)

The watcher must accept **both** signed and unsigned dispatches for 24 hours so anything already queued completes without rejection. Then close the window.

### T0 — enable dual-accept

Add an env flag to each watcher unit (drop-in or `EnvironmentFile`):

```
[Service]
Environment="INBOX_HMAC_DUAL_ACCEPT=1"
```

Watcher logic (in the inbox-poll loop):

```python
import os
from src.security.inbox_hmac import verify

dual_accept = os.environ.get("INBOX_HMAC_DUAL_ACCEPT") == "1"

if "_signature" in payload:
    if not verify(payload):
        reject(payload, reason="bad_signature")
        continue
elif dual_accept:
    log.warning("accepting unsigned dispatch during dual-accept window")
else:
    reject(payload, reason="missing_signature")
    continue
```

Restart watchers:
```bash
sudo systemctl daemon-reload
sudo systemctl restart atlas-inbox-watcher.service orion-inbox-watcher.service
journalctl -u atlas-inbox-watcher -f
```

Smoke test both paths:
```bash
# signed
python3 scripts/sign_dispatch.py --target atlas --from elliot \
    --brief "hmac smoke" --task-ref hmac_smoke_$(date +%s)

# unsigned (legacy)
python3 -c 'import json,time; print(json.dumps({"id":"u1","type":"task_dispatch","from":"elliot","target":"atlas","brief":"unsigned smoke","created_at":int(time.time())}))' \
    > /tmp/telegram-relay-atlas/inbox/u1.json
```

Both should be processed; journalctl should record the unsigned one with the `accepting unsigned dispatch` warning.

### T0 + 24h — flip to signed-only

```bash
sudo systemctl edit atlas-inbox-watcher.service
# remove the INBOX_HMAC_DUAL_ACCEPT line
sudo systemctl daemon-reload
sudo systemctl restart atlas-inbox-watcher.service orion-inbox-watcher.service
```

Repeat for orion. Re-run the smoke pair: signed should pass, unsigned should be rejected with `missing_signature`.

### Rollback

If signed-only causes drops, set `INBOX_HMAC_DUAL_ACCEPT=1` again and restart. Diagnose (check `scripts/sign_dispatch.py` output for the rejected dispatch, confirm the secret matches between sender and watcher), then retry the flip.

---

## Audit checklist (post-flip)

- [ ] `journalctl -u atlas-inbox-watcher --since "1h ago" | grep -ic "missing_signature\|bad_signature"` returns the expected reject count and zero unexpected ones.
- [ ] `python3 scripts/sign_dispatch.py --target atlas --from elliot --brief "smoke" --task-ref hmac_smoke_$(date +%s)` exits 0; the file appears in the inbox; the watcher consumes it.
- [ ] An unsigned write into the inbox is rejected with a clear reason in journalctl.
- [ ] `~/.config/agency-os/.env` is `chmod 600`.
- [ ] Watcher units' `Environment=` does not appear in any group-readable log or `git ls-files` output.
