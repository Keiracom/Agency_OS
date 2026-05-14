# Cognee 3 GB Memory Cap (KEI-44)

Owner: orion · Status: shipped · Linear: [KEI-44](https://linear.app/keiracom/issue/KEI-44/kei-44-cognee-subprocess-3gb-memory-cap-cgroupulimit) · Beads: Agency_OS-ely

## Why this exists

2026-05-13 OOM crash: uncapped `cognee_ingest.py` + `uvicorn cognee.api.client`
ran for 4+ hours, consumed all 6 GB of server RAM, killed six agent tmux
sessions. Required manual Dave intervention to recover.

The cap is **containment, not a fix**. Cognee memory growth is its own
problem — this runbook just bounds the blast radius so it never takes the
host down again.

## What the cap does

`scripts/orchestrator/cognee_capped.sh` wraps the launch under
`systemd-run --user --scope -p MemoryMax=3G`. The kernel cgroup memcg
hard-kills the child when RSS hits the cap. The host stays up. The
neighbouring agent tmux sessions stay up. The cognee process dies with
exit code 137 (SIGKILL) and a journal entry.

## Always launch via the wrapper

```bash
# Stream-1 batch ingest
scripts/orchestrator/cognee_capped.sh ingest -- --include-aux-skills

# Uvicorn server on :8000
scripts/orchestrator/cognee_capped.sh server

# Anything else cognee-shaped
scripts/orchestrator/cognee_capped.sh exec -- /usr/bin/env python -m mymodule
```

`exec` mode is the escape hatch for one-off scripts that touch cognee but
aren't `cognee_ingest.py` or the uvicorn server.

## Knobs

| Flag / env                          | Default | Meaning                                                     |
|-------------------------------------|---------|-------------------------------------------------------------|
| `--max-mem=3G`                      | 3G      | Cap value (anything systemd accepts: `3G`, `1500M`, etc.)   |
| `AGENCY_OS_COGNEE_CAP_MAX_MEM`      | 3G      | Same, via env (the wrapper picks `--max-mem` over env)      |
| `--no-cap`                          | off     | Run direct, no systemd-run wrapper. Local dev only.         |
| `AGENCY_OS_COGNEE_CAP_PYTHON`       | python3 | Override the python binary used for `ingest`/`server` modes |
| `AGENCY_OS_SYSTEMD_RUN`             | systemd-run | Path to the systemd-run binary                          |

## Verifying the cap is live

```bash
# Launch
scripts/orchestrator/cognee_capped.sh ingest -- --dry-run &
sleep 2

# Find the scope and its cgroup
systemctl --user list-units --type=scope | grep cognee-

# Look at the kernel-level cap (truth)
CG=$(systemctl --user show cognee-ingest-<PID>.scope -p ControlGroup --value)
cat /sys/fs/cgroup${CG}/memory.max   # → 3221225472 (= 3 GB)
```

**Heads-up:** `systemctl --user show <scope> -p MemoryMax` returns
`infinity` for transient scopes. That's a systemd display quirk — it does
not mean the cap is missing. The cgroup `memory.max` file is the source
of truth.

## Acceptance test (10-chunk synthetic batch)

```bash
scripts/orchestrator/cognee_cap_acceptance_test.sh           # default --cap 1G
scripts/orchestrator/cognee_cap_acceptance_test.sh --cap 3G  # real cap
```

The script allocates 10 × 400 MB chunks under the wrapper and verifies
the child is SIGKILL'd by the cgroup OOM killer (rc=137) before completing
all chunks. Default cap is 1 GB to keep dev workstation pressure low;
the enforcement mechanism is identical at 3 GB.

Verified 2026-05-13 (PR landing this runbook):

```
==> Wrapper exit code: 137
==> Last log lines: chunk 1..5 allocated (~2000 MB virt)
PASS: child SIGKILL'd by cgroup OOM (rc=137) at cap=1G
```

Kernel dmesg confirms scope-local memcg constraint:
```
oom-kill:constraint=CONSTRAINT_MEMCG,...
oom_memcg=/user.slice/.../cognee-exec-<pid>.scope
Memory cgroup out of memory: Killed process <pid> (python) anon-rss:1042304kB
```

## Resuming Streams 3+4 after the OOM freeze

1. Confirm cognee freeze still in effect: no active `cognee_ingest.py` or
   `uvicorn cognee.api.client` PIDs (`pgrep -f cognee_`).
2. Restart the server under the cap:
   ```bash
   scripts/orchestrator/cognee_capped.sh server </dev/null >/tmp/cognee-server.log 2>&1 &
   ```
3. Re-run the ingest under the cap:
   ```bash
   scripts/orchestrator/cognee_capped.sh ingest -- --include-aux-skills
   ```
4. If the cap fires, the process exits 137 cleanly. Don't auto-retry — a
   cap-hit means cognee's memory profile changed; investigate before
   re-launching.

## Failure modes

| Symptom                                | Diagnosis                                                                 | Action                                                                  |
|----------------------------------------|---------------------------------------------------------------------------|-------------------------------------------------------------------------|
| Wrapper exits 3 with "not available"   | `systemd-run` missing or wrong path                                       | Set `AGENCY_OS_SYSTEMD_RUN=/usr/bin/systemd-run` or `--no-cap` for local |
| Cognee process exits 137 unexpectedly  | Hit the 3 GB cap — workload grew past containment envelope                | Investigate chunking strategy / batch size. Don't widen the cap.        |
| `memory.max` shows `max` (no number)   | Memory controller not delegated to user slice                             | `systemctl edit --force --full user-1001.slice` → add `MemoryAccounting=yes`; or contact infra |
| Scope unit lingers after child exit    | Wrapper crashed mid-launch                                                | `systemctl --user reset-failed <unit>`                                  |

## Related

- KEI-43 (agent auto-start systemd services) — separate work; Atlas owns.
- PR #790 (`install_systemd_units.sh`) — installer pattern this wrapper
  doesn't use (no .service file ships; cap is applied per-invocation).
