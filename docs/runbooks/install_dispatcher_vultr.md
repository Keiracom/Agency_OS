# Install Dispatcher Service on Vultr Sydney (KEI-213)

**Dispatcher:** Atlas 2026-05-18 — Dave directive: wire KEI-209..212 components into a runnable service.

> **Atlas (clone) cannot SSH to vultr-sydney.** This runbook is for the human operator
> (Dave / Elliot worktree / devops with creds). Atlas writes the artifacts; the operator
> runs the steps below. Same boundary documented at L73 of `docs/runbooks/install_nats_vultr.md`.

---

## Prerequisites

- SSH access to `vultr-sydney` as `elliotbot`
- `nats-server.service` already running (KEI-205 runbook)
- Python 3.11+ venv at `/home/elliotbot/clawd/Agency_OS/.venv`
- Env file at `/home/elliotbot/.config/agency-os/.env` with the vars listed below
- Log dir `/home/elliotbot/clawd/logs/` exists (created by atlas-agent install)

---

## Required env vars

Add these to `/home/elliotbot/.config/agency-os/.env` before starting the service.
They are **fail-fast** — the process will not start if any are missing.

```bash
# auth_minter (KEI-209) — no dev fallback, must be set
DISPATCHER_JWT_SECRET=<generate: openssl rand -hex 32>

# spend_tracker (KEI-212) — Supabase pooler DSN
SUPABASE_DB_DSN=postgresql://postgres:<password>@db.jatzvazlbusedwsnqxzr.supabase.co:5432/postgres

# interceptor_proxy (KEI-210) — defaults to 127.0.0.1:4000 if unset
LITELLM_URL=http://127.0.0.1:4000/v1/chat/completions

# Valkey/Redis for rate limiting + spend counters (KEI-117A)
VALKEY_URL=redis://127.0.0.1:6379/0

# Optional: override default port (default 4001)
# DISPATCHER_PORT=4001

# Optional: scope prefix for watchdog+reaper (default "disp-")
# DISPATCHER_TMUX_PREFIX=disp-
# DISPATCHER_CONTAINER_PREFIX=disp-
```

---

## Step 1 — Pull latest code

```bash
ssh vultr-sydney
cd /home/elliotbot/clawd/Agency_OS
git pull --rebase origin main
```

---

## Step 2 — Install Python dependencies

```bash
cd /home/elliotbot/clawd/Agency_OS
.venv/bin/pip install -e ".[dispatcher]" --quiet
# Verify key packages present
.venv/bin/python -c "import fastapi, uvicorn, jwt, httpx; print('OK')"
```

---

## Step 3 — Install systemd unit

```bash
mkdir -p ~/.config/systemd/user
cp /home/elliotbot/clawd/Agency_OS/infra/systemd/agents/dispatcher.service \
   ~/.config/systemd/user/dispatcher.service
systemctl --user daemon-reload
```

---

## Step 4 — Enable and start

```bash
systemctl --user enable --now dispatcher.service
# Wait ~5 seconds for uvicorn to bind
sleep 5
systemctl --user status dispatcher.service
```

Expected output (paste verbatim into KEI-213 PR):
```
● dispatcher.service - Keiracom Dispatcher service (KEI-213) ...
     Loaded: loaded (/home/elliotbot/.config/systemd/user/dispatcher.service; enabled)
     Active: active (running) since ...
```

---

## Step 5 — Health probe

```bash
curl -s http://127.0.0.1:4001/dispatcher/health | python3 -m json.tool
```

Expected (all components green):
```json
{
    "status": "ok",
    "components": {
        "auth_minter": "ok",
        "interceptor_proxy": "ok",
        "spend_tracker": "ok",
        "watchdog": "ok",
        "reaper": "ok"
    }
}
```

Paste verbatim into the KEI-213 PR.

---

## Step 6 — End-to-end smoke test

This exercise verifies the full path: Supabase task → NATS dispatch → Dispatcher intercept → completion.

```bash
# 1. Publish a test dispatch to NATS orchestration stream
nats -s nats://127.0.0.1:4222 pub keiracom.orchestration \
  '{"task_id":"smoke-001","tenant_id":"test","callsign":"atlas","action":"probe"}'

# 2. Verify interceptor_proxy receives and processes a forwarded call
curl -s -X POST http://127.0.0.1:4001/interceptor/forward \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"test","callsign":"atlas","model":"gpt-4o","messages":[]}' \
  | python3 -m json.tool
# Expect: {"decision": "allow"|"deny_*", "reason": "..."}

# 3. Confirm spend_tracker recorded the probe (check Supabase)
#    SELECT * FROM public.infra_spend_metrics ORDER BY created_at DESC LIMIT 1;
```

---

## Rollback

```bash
systemctl --user disable --now dispatcher.service
rm -f ~/.config/systemd/user/dispatcher.service
systemctl --user daemon-reload
```

---

## Acceptance (Linear KEI-213)

Paste both of the following into the KEI-213 PR description:

- [ ] `systemctl --user status dispatcher.service` — shows `active (running)`
- [ ] `curl localhost:4001/dispatcher/health` — returns `{"status":"ok", ...}` with all five components green
