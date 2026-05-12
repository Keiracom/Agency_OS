# KEI-17 Pre-Research — Polling Loop Design

## Existing 1-min cadence pattern in production

Only one current service polls at 60s — `evo-callback-poller` — and it's the canonical template Aiden should copy. Verbatim:

`/home/elliotbot/.config/systemd/user/evo-callback-poller.timer`:
```ini
[Unit]
Description=EVO Callback Poller Timer (every 60s)
[Timer]
OnBootSec=30
OnUnitActiveSec=60
AccuracySec=5
[Install]
WantedBy=timers.target
```

`/home/elliotbot/.config/systemd/user/evo-callback-poller.service`:
```ini
[Unit]
Description=EVO Callback Poller (one-shot)
After=network.target
[Service]
Type=oneshot
WorkingDirectory=/home/elliotbot/clawd/Agency_OS
Environment="PYTHONPATH=/home/elliotbot/clawd/Agency_OS"
EnvironmentFile=/home/elliotbot/.config/agency-os/.env
ExecStart=/usr/bin/python3 -B /home/elliotbot/clawd/Agency_OS/src/evo/callback_poller.py
StandardOutput=append:/home/elliotbot/clawd/logs/evo-callback-poller.log
StandardError=append:/home/elliotbot/clawd/logs/evo-callback-poller.log
```

Type=oneshot + timer-driven is the right shape for Haiku-cadence polling: no long-running daemon to leak memory, no in-process scheduler to drift, restart semantics are free.

## Other 15-min poller worth referencing

`keiracom-agent-status.timer` (`OnUnitActiveSec=15min`) drives `collect_agent_status.py` which already aggregates the "what is each callsign doing" signal Aiden's loop needs for idle-detection. It writes to `keiracom_admin.agent_status_observations` — that's the table Aiden should read, not re-derive in the polling loop.

## Reuse-vs-fresh-build trade-off

**Reuse `keiracom_admin.agent_status_observations`** for idle-agent detection (don't re-implement tmux poking, gh PR queries, agent_memories scans). The 15-min collector is good enough for "agent has been idle ≥30 min" thresholds. If Aiden needs sub-minute idle detection, that's a separate change to the collector cadence, not new code in the polling loop.

**Build fresh** for the four orchestrator-specific checks (bd ready, Linear stale, Prefect failures, dispatch). These don't have existing observability layers writing to a queryable store.

## Recommended file layout

| Artefact | Path |
|---|---|
| Polling script | `/home/elliotbot/clawd/Agency_OS/scripts/orchestrator/elliot_polling_loop.py` |
| Helper modules | `/home/elliotbot/clawd/Agency_OS/scripts/orchestrator/checks/` (one file per check: `bd_ready.py`, `linear_stale.py`, `idle_agents.py`, `prefect_failures.py`) |
| Systemd timer | `/home/elliotbot/.config/systemd/user/elliot-polling-loop.timer` |
| Systemd service | `/home/elliotbot/.config/systemd/user/elliot-polling-loop.service` |
| Log file | `/home/elliotbot/clawd/logs/elliot-polling-loop.log` |
| State file (last-seen IDs for dedup) | `/home/elliotbot/.local/state/elliot-polling-loop.json` |

**Worktree binding:** services read from main worktree per `feedback_systemd_worktree_main.md`. Path `/home/elliotbot/clawd/Agency_OS` is correct; do not point at any callsign worktree.

## Two gotchas to surface up-front

1. **Overlap protection.** `Type=oneshot` does not prevent a slow run from overlapping its next tick. Add `RuntimeMaxSec=55` to the service so any run >55s gets killed before the next 60s tick fires.
2. **Quiet first 30s of boot.** `OnBootSec=30` matches the evo-callback-poller defaults — gives the network stack and EnvironmentFile a moment to be ready. Don't shorten it.

Net: copy evo-callback-poller's two unit files, swap names + ExecStart, add `RuntimeMaxSec=55`, ship.
