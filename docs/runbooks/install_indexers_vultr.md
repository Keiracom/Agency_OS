# Install the 5 Weaviate auto-indexers on Vultr Sydney

**Dispatcher:** Elliot 2026-05-18 — install 4 indexers on Vultr. This PR ships the 5th install script (`tool_call_log` was missing one) + a one-shot wrapper that deploys the full set.

**Indexer fleet** (5 units):

| Indexer | Service unit | Source → Weaviate |
|---|---|---|
| ceo-memory | `ceo-memory-indexer.service` | `public.ceo_memory` → Weaviate `CeoMemory` |
| elliot-memories | `elliot-memories-indexer.service` | `elliot_internal.memories` → Weaviate `AgentMemories` |
| git-commits | `git-commits-indexer.service` | `git log` → Weaviate `GitCommits` |
| linear-state | `linear-state-indexer.service` | Linear API → Weaviate `LinearKEIs` |
| tool-call-log | `tool-call-log-indexer.service` | `public.tool_call_log` → Weaviate `ToolCallLog` |

## Prerequisite

Vultr Sydney host has the repo checked out at `/home/elliotbot/clawd/Agency_OS` + the venv at `/home/elliotbot/clawd/venv`. (Both seeded by KEI-48 / KEI-73 / KEI-74 / KEI-75 / KEI-179 — already done.)

`/home/elliotbot/.config/agency-os/.env` carries:
- `SUPABASE_DB_URL` (psycopg DSN — `postgres://` not `postgresql+asyncpg://`)
- `WEAVIATE_URL`, `WEAVIATE_API_KEY`
- `LINEAR_API_KEY` (linear-state-indexer only)

## Deploy

```bash
ssh vultr-sydney
cd /home/elliotbot/clawd/Agency_OS
git pull
bash scripts/install_all_indexers.sh
```

The orchestrator runs each per-unit installer, calls `systemctl --user daemon-reload + enable --now`, then verifies all 5 report `is-active = active`. Non-zero exit + named failures on any miss.

## Verify (one-liner)

```bash
for u in ceo-memory elliot-memories git-commits linear-state tool-call-log; do
    systemctl --user is-active "${u}-indexer.service" || echo "FAIL: ${u}"
done
```

Expect 5 `active` lines, no `FAIL` lines.

## Per-unit install (if installing one at a time)

```bash
scripts/install_ceo_memory_indexer.sh
scripts/install_elliot_memories_indexer.sh
scripts/install_git_commits_indexer.sh
scripts/install_linear_state_indexer.sh
scripts/install_tool_call_log_indexer.sh   # new in this PR
```

Each wraps `scripts/orchestrator/install_indexer.sh <unit>` so the KEI-108 grep-gate finds the literal `.service` unit name in `scripts/install*`.

## Rollback

```bash
for u in ceo-memory elliot-memories git-commits linear-state tool-call-log; do
    systemctl --user disable --now "${u}-indexer.service" || true
    rm -f "${HOME}/.config/systemd/user/${u}-indexer.service"
done
systemctl --user daemon-reload
```

## What this PR does NOT do

- Does **not** SSH to Vultr (atlas clone doesn't hold `vultr-sydney` SSH credentials). The install must be run by Dave or a callsign that does (Elliot worktree or devops).
- Does **not** seed `agency-os/.env` — that's a per-host operator step.
- Does **not** install Weaviate or LiteLLM — those are KEI-48 / KEI-73.
- Does **not** add monitoring — see KEI-141 (systemd service health monitoring) for that follow-up.

## What this PR adds

1. `scripts/install_tool_call_log_indexer.sh` — missing 5th install script (sibling to the existing 4 — closes a KEI-108 gap where the `.service` was shipped without a per-unit installer wrapper).
2. `scripts/install_all_indexers.sh` — one-shot orchestrator with verify + named-failure exit codes.
3. `docs/runbooks/install_indexers_vultr.md` — this runbook.
