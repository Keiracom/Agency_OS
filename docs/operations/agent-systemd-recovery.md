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

## OpenClaw relay dependency (KEI-95)

Every `*-agent.service` unit declares `Requires=openclaw.service` +
`After=network-online.target openclaw.service`. On a fresh boot the agent
unit will NOT start until OpenClaw is up — preventing the silent-deaf
agent failure mode where Claude Code initialises before the relay is ready
and MCP/Slack inbound never reconnects.

Two operator conditions must hold on a fresh host or after a reinstall:

```bash
# 1. Linger must be on (services need to start without a login session).
sudo loginctl enable-linger elliotbot

# 2. openclaw.service must be installed under ~/.config/systemd/user/
#    and enabled. Source lives outside this repo; if it's missing,
#    install_*_agent.sh exits and the dependency fails.
systemctl --user is-enabled openclaw.service   # expect: enabled
systemctl --user is-active  openclaw.service   # expect: active
```

If OpenClaw is unhealthy on boot, agent units stay in `inactive (waiting)`
until OpenClaw becomes active — they will NOT crash-loop. Once OpenClaw
comes up, agents follow within seconds.

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

---

## KEI-63 — Idle-agent auto-dispatch (bd completion hook + OpenClaw idle fallback)

**Linear:** [KEI-66](https://linear.app/keiracom/issue/KEI-66)
**bd:** Agency_OS-3nri4k

### What ships

Two small extensions to existing infrastructure that eliminate idle gaps:

**1. Completion hook — `scripts/orchestrator/bd_complete_hook.sh`**

Agents call this instead of `bd close` directly. It:

1. Runs `bd close "$@"` (marks the task done — bd's own logic, unmodified).
2. On success: runs `bd ready --claim --json` to atomically claim the next available task.
3. If a task is claimed: injects `bd claim <id>` into the agent's canonical tmux pane via `tmux send-keys`. Agent transitions directly to new work. Zero idle gap.
4. If no task: logs `idle:no_work` to `/home/elliotbot/clawd/logs/kei63-completion-hook.log`.
5. Always exits 0 — hook failure never blocks `bd close` from completing.

Callsign resolution (first wins): `$CALLSIGN` env var → `IDENTITY.md` in worktree → `git config user.name`.

**2. OpenClaw idle fallback — `poll_kei63_idle_inject` in `elliot_polling_loop.py`**

Every polling cycle (1 min peak, 60 min overnight), for each agent:

- Checks if pane is idle > 5 min (pane ends with a shell prompt AND HEARTBEAT.md is stale).
- If idle + work available: injects `bd ready` into the tmux pane so the agent sees the queue.
- If idle > 30 min + NO work: posts a `#ceo` alert (deduped per 30-min window per callsign).

### How to verify it is working

```bash
# Check the completion hook log for injection events.
tail -f /home/elliotbot/clawd/logs/kei63-completion-hook.log

# Run the acceptance test directly.
bash /home/elliotbot/clawd/Agency_OS/scripts/kei63_acceptance_test.sh

# Run pytest for the unit tests.
python -m pytest tests/scripts/test_bd_complete_hook.py tests/scripts/test_elliot_polling_loop_kei63.py -v
```

### How to disable for debugging

```bash
# Disable injection in the completion hook (skip the post-close step):
AGENCY_OS_BD_HOOK_LOG=/dev/null CALLSIGN="" bash scripts/orchestrator/bd_complete_hook.sh <issue-id>

# Disable the idle fallback poller: comment out poll_kei63_idle_inject() in run_cycle()
# (no env-var gate by design — the poller is lightweight and always-on).
```

### CALLSIGN_TO_TMUX map

Both the hook and the poller use the same canonical map (defined in `elliot_polling_loop.py`):

| Callsign | tmux session |
|----------|--------------|
| elliot   | elliottbot   |
| aiden    | aiden        |
| max      | maxbot       |
| atlas    | atlas        |
| orion    | orion        |
| scout    | scout        |

If a callsign is added or a tmux session renamed: update `CALLSIGN_TO_TMUX` in `elliot_polling_loop.py` AND the `declare -A CALLSIGN_TO_TMUX` in `bd_complete_hook.sh` in the same PR.

## Related

- KEI-35 — detection-based session recovery (already shipped); complementary to
  this boot-side path. KEI-35 catches a *running* agent that has gone dead;
  KEI-43 catches the post-reboot cold-start.
- KEI-44 — Cognee 3GB memory cap (Orion, parallel work — limits the OOM that
  triggered the original 2026-05-13 incident).
- `openclaw.service` — `/home/elliotbot/.config/systemd/user/openclaw.service`
  was the reference pattern for the unit shape.
