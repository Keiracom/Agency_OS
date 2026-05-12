# Polling Loop Bug Diagnosis (Agency_OS-yvz)

Source: `scripts/orchestrator/elliot_polling_loop.py` (read fresh 2026-05-12, commit on `main`). Live evidence reproduced from `/home/elliotbot/clawd/logs/elliot-polling-loop.log`.

## Bug (a) — `bd_ready=0`

**Repro:**
```
$ tail /home/elliotbot/clawd/logs/elliot-polling-loop.log | grep "bd ready"
WARNING: bd ready failed: [Errno 2] No such file or directory: 'bd'

$ bd ready --json | python3 -c "import json,sys; print(len(json.load(sys.stdin)))"
8
```

**Root cause:** `poll_bd_ready()` at `elliot_polling_loop.py:109-118`. Line 111 calls `subprocess.run(["bd", "ready", "--json"], ...)` — bare command name. `bd` is installed at `/home/elliotbot/.local/bin/bd` (verified: `which bd`). The systemd service `elliot-polling-loop.service` inherits a restricted PATH that does **not** include `~/.local/bin/`. `FileNotFoundError` → `except` clause at line 116 logs and returns `[]`.

**Suggested fix:** absolute path. Replace line 111 with:
```python
subprocess.run([os.path.expanduser("~/.local/bin/bd"), "ready", "--json"], ...)
```
OR add `Environment="PATH=/home/elliotbot/.local/bin:/usr/bin:/bin"` to the `.service` unit. Path-in-code is more robust against PATH drift across hosts; PATH-in-unit is more idiomatic. Either works.

## Bug (b) — `idle=0`

**Repro:**
```
$ tail /home/elliotbot/clawd/logs/elliot-polling-loop.log | grep -A2 "idle-agent"
WARNING: idle-agent query failed: prepared statement "__asyncpg_stmt_1__" already exists
HINT:
NOTE: pgbouncer with pool_mode set to "transaction" or "statement" does not support prepared statements properly.
```

**Root cause:** `poll_idle_agents()` at `elliot_polling_loop.py:148-190`. Line 177 calls `asyncpg.connect(...)` with default arguments. The DSN routes through Supabase's pgbouncer in transaction pool mode, which does not preserve prepared-statement state across pool re-uses. `asyncpg` aggressively prepares + caches every statement and collides with itself on the second cycle. Postgres returns the pgbouncer error verbatim. The `except` at line 188 logs and returns `[]` — so the idle check never produces a signal even when outboxes (e.g. atlas at `Apr 22 20:59`, orion at `Apr 26 00:23` per `ls -la /tmp/telegram-relay-{atlas,orion}/outbox/`) are clearly stale.

**Suggested fix:** disable asyncpg's statement cache (Supabase's documented pattern). Line 177 becomes:
```python
conn = await asyncpg.connect(
    dsn.replace("postgresql+asyncpg://", "postgresql://"),
    statement_cache_size=0,
)
```
Single-keyword change. No schema or call-site impact.

## Bug (c) — Prefect 404

**Repro:**
```
$ tail /home/elliotbot/clawd/logs/elliot-polling-loop.log | grep "Prefect"
WARNING: Prefect failure query failed: HTTP Error 404: Not Found

$ env_url=$(grep '^PREFECT_API_URL=' /home/elliotbot/.config/agency-os/.env | cut -d= -f2-)
$ echo "$env_url"
https://prefect-server-production-f9b1.up.railway.app/api

$ curl -s "https://prefect-server-production-f9b1.up.railway.app/"
{"service":"Agency OS API","version":"3.0.0","status":"running",...}
```

**Root cause:** `poll_prefect_failures()` at `elliot_polling_loop.py:193-218`. The URL construction at line 213 (`f"{api_url}/flow_runs/filter"`) is **correct** — that's the canonical Prefect REST filter endpoint. The bug is **not in the code**: the Railway service at the URL stored in `PREFECT_API_URL` has been repurposed and now serves "Agency OS API v3.0.0" instead of Prefect. So every Prefect endpoint returns 404 because there is no Prefect server at that hostname.

**Suggested fix:** infrastructure/env change, not code change.
1. Find the live Prefect server URL (check Railway dashboard for the actual Prefect deployment).
2. Update `PREFECT_API_URL` in `/home/elliotbot/.config/agency-os/.env` to the real URL.
3. If self-hosted Prefect is decommissioned: short-circuit `poll_prefect_failures()` to return `[]` early (`if not api_url: return []` is already there — just unset the env var) OR remove the poll entirely from `collect_signals` at line 224.

## Sequence for Aiden's PR

(b) is the smallest diff (one keyword arg). (a) is similarly small (one command path). (c) is mostly an env-config change with optional code short-circuit. Bundle (a)+(b) into one PR; (c) is a separate env/infra concern.
