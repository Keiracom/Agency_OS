# Agent auto-start systemd services (KEI-43)

**Owner:** Atlas (build) · **Linear:** [KEI-43](https://linear.app/keiracom/issue/KEI-43) · **bd:** Agency_OS-idt

## What this gives you

Six `systemd --user` units — one per agent — that automatically spawn each
agent's tmux session + `claude` resume on boot. A server reboot brings all 6
agents back within ~2 minutes with **zero operator intervention**.

| Service                | Callsign | tmux session | Worktree                                 |
|------------------------|----------|--------------|------------------------------------------|
| `elliot-agent.service` | elliot   | `elliottbot` | `/home/elliotbot/clawd/Agency_OS`        |
| `aiden-agent.service`  | aiden    | `aiden`      | `/home/elliotbot/clawd/Agency_OS-aiden`  |
| `max-agent.service`    | max      | `maxbot`     | `/home/elliotbot/clawd/Agency_OS-max`    |
| `atlas-agent.service`  | atlas    | `atlas`      | `/home/elliotbot/clawd/Agency_OS-atlas`  |
| `orion-agent.service`  | orion    | `orion`      | `/home/elliotbot/clawd/Agency_OS-orion`  |
| `scout-agent.service`  | scout    | `scout`      | `/home/elliotbot/clawd/Agency_OS-scout`  |

Map source-of-truth: `scripts/orchestrator/elliot_polling_loop.py CALLSIGN_TO_TMUX`.

## Install (one-time, post-merge)

```bash
# 1. Make sure every worktree has the supervisor wrapper (it ships under main).
for wt in /home/elliotbot/clawd/Agency_OS /home/elliotbot/clawd/Agency_OS-aiden \
          /home/elliotbot/clawd/Agency_OS-max /home/elliotbot/clawd/Agency_OS-atlas \
          /home/elliotbot/clawd/Agency_OS-orion /home/elliotbot/clawd/Agency_OS-scout; do
    test -x "$wt/scripts/systemd_agent_supervisor.sh" \
        || echo "MISSING: $wt — run 'git -C $wt pull' before continuing"
done

# 1b. CRITICAL: user services need linger enabled or they won't auto-start at boot.
loginctl show-user elliotbot --property=Linger 2>/dev/null | grep -q "Linger=yes" \
    || echo "WARN: linger OFF — services will NOT auto-start at boot. Fix: sudo loginctl enable-linger elliotbot"

# 2. Copy unit files into the user systemd dir.
install -D -m 0644 -t /home/elliotbot/.config/systemd/user/ \
    /home/elliotbot/clawd/Agency_OS/infra/systemd/agents/*.service

# 3. Make sure the log dir exists.
mkdir -p /home/elliotbot/clawd/logs

# 4. Reload + enable + start each unit.
systemctl --user daemon-reload
for svc in elliot-agent aiden-agent max-agent atlas-agent orion-agent scout-agent; do
    systemctl --user enable --now "${svc}.service"
done

# 5. Verify all six are active.
systemctl --user --type=service --state=active | grep -E "^(elliot|aiden|max|atlas|orion|scout)-agent"
```

## "How do I recover from a server reboot?"

You don't. It auto-recovers.

After a reboot, all 6 agent services start automatically via `WantedBy=default.target`,
spawn their tmux sessions inside their canonical worktrees, and invoke
`scripts/agent_session_launcher.sh <callsign>` which resumes the most recent
watchdog-fresh `session_uuid` from Supabase (PR-C session resumption).

Expected timeline after `reboot`:

1. `t+0` — host comes back online.
2. `t+0..30s` — `default.target` reached, `*-agent.service` units fire.
3. `t+30s..2min` — each unit's supervisor spawns its tmux session and invokes
   `agent_session_launcher.sh`, which `claude --resume <uuid>` reloads each
   agent's prior session.
4. `t≈2min` — all 6 agents online; inbox watchers (separate services) pick up
   pending dispatches.

If something is missing after ~3 minutes, see **Troubleshooting**.

## How a crashed agent recovers

Each service runs `scripts/systemd_agent_supervisor.sh <callsign> <tmux> <worktree>`,
which polls the tmux session and exits non-zero when the session terminates.
That triggers `Restart=on-failure` with `RestartSec=10`, so the agent is back
within ~10 seconds of a crash. `StartLimitBurst=5` / `StartLimitIntervalSec=300`
caps runaway restart loops (5 restarts in 5 minutes → systemd holds it failed).

## Verify auto-restart without rebooting

```bash
# Pick one — the watcher should exit non-zero and systemd restart within ~10s.
systemctl --user status atlas-agent.service                  # confirm Active=running
tmux kill-session -t atlas                                   # kill the underlying session
sleep 15
systemctl --user status atlas-agent.service                  # should show ↻ Active=running (restarted)
tmux has-session -t atlas && echo "OK — atlas tmux session is back"
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `systemctl --user status <svc>` shows `code=exited, status=2` | Worktree path missing OR `agent_session_launcher.sh` missing/non-exec | `git -C <worktree> pull && chmod +x scripts/agent_session_launcher.sh` |
| Service flaps (start-limit-hit) | Persistent crash inside `claude` / `agent_session_launcher.sh` | `journalctl --user -u <svc> --since=-5min` and inspect; reset with `systemctl --user reset-failed <svc>` |
| Two tmux sessions with the same name | Manual `tmux new-session -s atlas` while service is up | The supervisor is idempotent — kill the duplicate manually; service keeps the canonical one alive |
| Service is `inactive`/`disabled` after reboot | `systemctl --user enable` was skipped | Re-run step 4 of the install procedure |
| `lingering` not enabled — services don't auto-start at boot | User services need linger | `sudo loginctl enable-linger elliotbot` |

## Why these files live in the repo

Operator runbook + unit files are checked into the repo so:

- The map between callsign / tmux name / worktree stays version-controlled.
- A fresh server install just needs `git clone` + the install commands above.
- PR review can catch drift if the canonical map in
  `scripts/orchestrator/elliot_polling_loop.py` changes without these files
  changing in lockstep.

## Layer 3 idle enforcement (KEI-45)

In addition to the 6 boot services above, KEI-45 adds a single master daemon —
`agent-idle-enforcer.service` — that runs every 5 minutes and mechanically
injects unclaimed `bd ready` work into idle agents' tmux sessions. This closes
the "agent is alive but stopped pulling new work" failure mode (which is
distinct from the KEI-43 boot-side cold-start and the KEI-35 detection-based
restart).

### What it does, per 5-min cycle, per agent

1. Captures the tail of the agent's tmux pane (20 lines).
2. **Weekly-cap detection** — matches the Anthropic "You've used X% of your
   weekly limit · resets <date>" banner → posts to `#ceo` once, suppresses
   retries until reset (state written to `ceo:boot_state_current`).
3. **Transient throttle detection** — reuses the existing `THROTTLE_RE`
   (`429` / `retry-after` / `Brewed for`) → exponential-backoff state, no
   escalation.
4. **BUSY-guard** — if the pane shows a recent `[BUSY:<callsign>:<task>]`
   tag, skip (the agent is mid-task; don't double-dispatch).
5. **Idle derivation** — `HEARTBEAT.md` file mtime in each worktree.
6. **Idle ≥10 min + unclaimed `bd ready --assignee=<callsign>` work + not
   rate-limited + not BUSY** → `tmux send-keys -t <session>:0 "<brief>" Enter`.
   This is Layer 3 mechanical: cannot be bypassed by agent reasoning.
7. **Idle ≥30 min with work still pending** → escalate to `#ceo`
   (deduped to 60 min per callsign so we don't spam Dave).
8. Upserts the per-agent snapshot to `public.ceo_memory key ceo:boot_state_current`
   (jsonb), schema documented in the script docstring.

### Install (one-time, post-merge)

```bash
install -D -m 0644 /home/elliotbot/clawd/Agency_OS/infra/systemd/agents/agent-idle-enforcer.service \
    /home/elliotbot/.config/systemd/user/agent-idle-enforcer.service
systemctl --user daemon-reload
systemctl --user enable --now agent-idle-enforcer.service
systemctl --user status agent-idle-enforcer.service   # confirm Active=running
```

### Verify a real injection (one-shot smoke)

```bash
# From the Agency_OS worktree (the WorkingDirectory of the unit):
python3 scripts/idle_enforcer.py --once
# Then in Supabase:
#   SELECT jsonb_pretty(value) FROM public.ceo_memory WHERE key='ceo:boot_state_current';
```

### Related

- KEI-35 — detection-based session recovery (already shipped); complementary to
  this boot-side path. KEI-35 catches a *running* agent that has gone dead;
  KEI-43 catches the post-reboot cold-start.
- KEI-45 — Layer 3 idle enforcement (this file's §Layer 3 idle enforcement).
- KEI-44 — Cognee 3GB memory cap (Orion, parallel work — limits the OOM that
  triggered the original 2026-05-13 incident).
- `openclaw.service` — `/home/elliotbot/.config/systemd/user/openclaw.service`
  was the reference pattern for the unit shape.
