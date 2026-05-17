# Valkey — Real-time coordination bus

Linear KEI-75 / bd KEI-101. Localhost-bound Valkey 7.x on the Vultr Sydney host,
replacing Slack as the machine coordination layer for agent dispatch.

## Architecture

- Single-node Valkey on `127.0.0.1:6379`.
- Localhost bind is the security boundary (no AUTH, no TLS).
- 2GB ceiling via `systemd` cgroup (`MemoryMax`); RDB snapshots only (`appendonly no`).
- Six initial streams/channels per spec — see `scripts/valkey/init_streams.py`.

## Install

```bash
bash scripts/valkey/install.sh
```

Idempotent. Run on the Vultr Sydney host (or any future replica). Requires
`sudo`. Pulls `valkey-server` + `valkey-tools` from `noble-updates/universe`,
applies the RDB save policy in `/etc/valkey/valkey.conf`, installs the
`MemoryMax=2G` Drop-In, enables + starts the service, and seeds the six
streams/channels.

## Stream / channel inventory

| Name                              | Type    | Purpose                                  |
| --------------------------------- | ------- | ---------------------------------------- |
| `orchestration`                   | stream  | Dispatcher → containers task feed        |
| `deliberation_thread_{task_id}`   | stream  | Per-task agent deliberation              |
| `keiracom:agent:status:{callsign}`| hash    | Fleet status board                       |
| `keiracom:tasks:available`        | pub/sub | New available-task fan-out               |
| `keiracom:tasks:completed:{id}`   | pub/sub | Per-task completion fan-out              |
| `keiracom:ceo:escalation`         | pub/sub | Direct CEO escalation channel            |

## Verify

```bash
systemctl status valkey-server
valkey-cli ping
python3 scripts/valkey/smoke_pubsub.py   # publish→receive < 5ms
```
