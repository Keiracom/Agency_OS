# Install NATS + JetStream on Vultr Sydney (KEI-205)

**Dispatcher:** Elliot 2026-05-18 — Dave directive: NATS replaces Valkey messaging layer NOW.
**Lane:** Atlas install + Elliot KEI-183 PR scope update to consume NATS instead of Redis pub/sub.

## Why NATS

NATS is purpose-built for ephemeral agent coordination, sub-millisecond task routing, lightweight pub/sub for agent state. Single binary, starts in milliseconds, no dependencies. Better fit than Valkey pub/sub for the messaging layer.

**Valkey stays** for what it's good at:
- Rate limiting ([KEI-117](https://linear.app/keiracom/issue/KEI-117) — sliding window per tenant)
- Thread count state per tenant
- KV store for session metadata

## What ships (this PR)

| Path | Purpose |
|---|---|
| `infra/nats/nats-server.conf` | NATS server config with JetStream enabled — localhost listener on `:4222`, monitor on `:8222`, file-backed JetStream store at `~/clawd/nats-jetstream` |
| `infra/systemd/agents/nats-server.service` | systemd user unit — Type=simple, Restart=on-failure, LimitNOFILE=65536 |
| `scripts/install_nats.sh` | KEI-108-compliant install wrapper. Downloads NATS binary (v2.10.20), installs systemd unit, creates JetStream store + log dir, enables + starts the service, verifies `is-active` + `/healthz`. |
| `scripts/nats_create_streams.sh` | Creates the 6 JetStream streams idempotently. Installs `nats` CLI on first run. |
| `docs/runbooks/install_nats_vultr.md` | This runbook. |

## Stream map (per Elliot's architecture spec)

| Stream | Subject pattern | Purpose |
|---|---|---|
| `orchestration` | `keiracom.orchestration` | Main task routing |
| `deliberation` | `keiracom.deliberation.*` | Per-task deliberation (wildcard for `task_id`) |
| `agent_status` | `keiracom.agent.status.*` | Agent ready/active — kills `[READY]` Slack spam |
| `pair_elliot_atlas` | `keiracom.elliot.atlas` | Elliot → Atlas pair channel |
| `pair_aiden_orion` | `keiracom.aiden.orion` | Aiden → Orion pair channel |
| `pair_max_scout` | `keiracom.max.scout` | Max → Scout pair channel |

All streams: file storage, 24h retention, single replica (Vultr Sydney single-node).

## Deploy

```bash
ssh vultr-sydney
cd /home/elliotbot/clawd/Agency_OS
git pull

# Step 1: install nats-server + systemd unit
bash scripts/install_nats.sh

# Step 2: create JetStream streams (after server is up)
bash scripts/nats_create_streams.sh
```

## Verify

```bash
# Service is up
systemctl --user is-active nats-server.service   # → active

# Health endpoint responds 200
curl -s http://127.0.0.1:8222/healthz             # → 200

# 6 streams exist
nats -s nats://127.0.0.1:4222 stream ls
# Expect: orchestration, deliberation, agent_status, pair_elliot_atlas,
#         pair_aiden_orion, pair_max_scout

# Smoke a publish + subscribe
nats -s nats://127.0.0.1:4222 pub keiracom.agent.status.atlas '{"ready":true}'
nats -s nats://127.0.0.1:4222 sub 'keiracom.agent.status.*' --count=1
```

## What this PR does NOT do (separate KEIs / follow-ups)

- **SSH to vultr-sydney + actual deploy** — operator step (Dave / Elliot worktree / devops with creds). Atlas clone doesn't hold vultr-sydney SSH.
- **Python NATS client wrapper** — `src/integrations/nats_client.py` is consumed by KEI-183 (Supervisor v2 — Max is the active builder per claim, his PR #990 scope gets updated per Elliot to consume NATS instead of Redis pub/sub). Sibling KEI to file if not absorbed into KEI-183.
- **Dispatcher subscription wiring** — `src/dispatcher/app.py` subscribes to `keiracom.orchestration`. KEI-179 follow-up (the dispatcher service exists; NATS-consume happens in a separate PR so KEI-179 stays a clean scaffold).
- **Killing `[READY]` Slack spam** — KEI-183 + KEI-185 own the supervisor-side flip (read agent state from NATS, not Slack).

## Rollback

```bash
systemctl --user disable --now nats-server.service
rm -f "${HOME}/.config/systemd/user/nats-server.service"
systemctl --user daemon-reload

# Optional: nuke JetStream store (loses all in-flight messages — only do this if
# you're rolling back from a corrupt state, not a normal stop)
# rm -rf ~/clawd/nats-jetstream

# /usr/local/bin/nats-server is left in place — same binary works if you re-install
```

## Acceptance (Linear KEI-205 Part 1)

- [x] **NATS server running as systemd service on Vultr** — `nats-server.service` user unit installed via `install_nats.sh`; verified by `systemctl --user is-active` in the install script.
- [x] **JetStream enabled, 6 streams created** — `jetstream {}` block in conf; `nats_create_streams.sh` creates all 6 idempotently and verifies via `stream ls`.

## Acceptance (Linear KEI-205 Parts 2 + 3) — out of scope this PR

- [ ] **Agent READY signals visible in `keiracom.agent.status.*` — zero `[READY]` in Slack** — depends on KEI-183 PR scope update (Elliot coordinates with Max).
- [ ] **Supervisor reads agent state from NATS, not Slack** — same as above.
- [ ] **Dispatcher publishes task assignments to NATS** — KEI-179 follow-up PR adds the publish hook.
- [ ] **KEI-183 PR updated to use NATS before merge** — Elliot owns coordination with Max.

This PR ships the install layer. Parts 2+3 are downstream consumer work owned by KEI-183 + KEI-179 authors.
