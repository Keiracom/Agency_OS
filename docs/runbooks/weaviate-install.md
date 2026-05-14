# Weaviate install on Vultr Sydney (KEI-48)

**Linear:** [KEI-48](https://linear.app/keiracom/issue/KEI-48) · **Author:** Atlas · **Driver:** Dave verbatim 2026-05-14 06:39 AEST

Foundation of the entire memory system. 12 downstream KEIs cannot start until
Weaviate is installed. This runbook documents the **native-binary** install
chosen because Docker is not installed on the Vultr Sydney host (per Elliot
ts ~1778742500 pick of option (b)).

## Acceptance criteria (all verified empirically at install time)

| Criterion | How verified | Evidence |
|---|---|---|
| Weaviate process running | `systemctl --user list-units --type=scope` | `weaviate-<PID>.scope loaded active running` |
| Cgroup MemoryMax=2.5G enforced | `systemctl --user show <scope>.scope --property=MemoryMax` | `MemoryMax=2684354560` (= 2.5 GiB) |
| `/v1/meta` returns version | `curl http://127.0.0.1:8090/v1/meta` | `{"version":"1.37.3", ...}` |
| 5 collections present | `curl http://127.0.0.1:8090/v1/schema` | `Codebase, Decisions, Discoveries, Keis, Sessions` |
| Mandatory properties on every class | `infra/weaviate/smoke_test.py` step [2/5] | All 5 classes have `raw_text/environment_hash/created_at/agent/kei` |
| Probe insert+retrieve+delete | `infra/weaviate/smoke_test.py` steps [3-5/5] | UUID round-trip verified |
| Persistent volume mount | `ls -la /home/elliotbot/clawd/weaviate-data` | `classifications.db` + per-collection dirs created post-startup |

## One-time install

### Prerequisites

- `loginctl show-user elliotbot --property=Linger` → `Linger=yes` (required for
  `systemctl --user enable` to persist across reboots)
- Port 8090 free (`ss -ltn | grep :8090` returns empty) — 8080 is held by crowdsec
- `/home/elliotbot/clawd/Agency_OS/` worktree on `main` with the KEI-48 PR merged

### Steps

```bash
# 1. Create directories.
mkdir -p /home/elliotbot/clawd/weaviate-bin /home/elliotbot/clawd/weaviate-data

# 2. Download Weaviate v1.37.3 linux-amd64 + verify SHA-256.
cd /home/elliotbot/clawd/weaviate-bin
curl -L -o weaviate-v1.37.3-linux-amd64.tar.gz \
    https://github.com/weaviate/weaviate/releases/download/v1.37.3/weaviate-v1.37.3-linux-amd64.tar.gz
curl -L -o weaviate-v1.37.3-linux-amd64.tar.gz.sha256 \
    https://github.com/weaviate/weaviate/releases/download/v1.37.3/weaviate-v1.37.3-linux-amd64.tar.gz.sha256
sha256sum -c weaviate-v1.37.3-linux-amd64.tar.gz.sha256
# Expected: cbdefcd2205fef65cbc206e45194afac7a1965d1420e0baf711c20370c7747bf

# 3. Extract binary.
tar xzf weaviate-v1.37.3-linux-amd64.tar.gz
chmod +x weaviate

# 4. Install systemd-user unit (from the merged PR).
install -D -m 0644 \
    /home/elliotbot/clawd/Agency_OS/infra/systemd/agents/weaviate.service \
    /home/elliotbot/.config/systemd/user/weaviate.service
mkdir -p /home/elliotbot/clawd/logs

# 5. Reload + enable + start.
systemctl --user daemon-reload
systemctl --user enable --now weaviate.service
sleep 8   # Raft single-node bootstrap takes 4-6s on a warm host

# 6. Verify readiness.
curl -s -o /dev/null -w 'ready=%{http_code}\n' http://127.0.0.1:8090/v1/.well-known/ready   # expect ready=200
curl -s http://127.0.0.1:8090/v1/meta | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])"   # expect 1.37.3

# 7. Apply schema (idempotent — re-runs only add missing collections).
cd /home/elliotbot/clawd/Agency_OS
python3 infra/weaviate/schema.py --host 127.0.0.1 --port 8090

# 8. Run smoke test.
python3 infra/weaviate/smoke_test.py --host 127.0.0.1 --port 8090
# Expect: "KEI-48 SMOKE PASSED — Weaviate 1.37.3 reachable, schema valid, round-trip OK."
```

## Why native binary, not Docker

Empirical env check on Vultr Sydney 2026-05-14 found:

- **`docker: command not found`** — no docker/podman/containerd/runc on PATH;
  no `docker.service` unit; no `dpkg -l docker*` entries. Docker is not installed.
- **Port 8080 held by `crowdsec` (pid 1632)** — Weaviate's default port is
  unavailable; runbook uses **8090** instead.
- **Memory pressure baseline** — 7.7G total, 4.2G used + 3.9G swap in use.
  Cgroup hard ceiling at 2.5G via `systemd-run --user --scope -p MemoryMax=2.5G`
  prevents Weaviate from OOM-killing the host (Cognee OOM precedent KEI-44).

Native binary install:
- Avoids the install-Docker yak-shave.
- Cleaner cgroup integration — `systemd-run --user --scope` wraps the binary
  directly, exactly as `cognee_capped.sh` (KEI-44) wraps `cognee_ingest.py`.
- Smaller attack surface, faster start, smaller disk footprint.

The wrapper is `scripts/orchestrator/weaviate_capped.sh`; the unit is
`infra/systemd/agents/weaviate.service`; both mirror the KEI-44 + KEI-43 patterns.

## Configuration env vars

| Env | Default | Purpose |
|---|---|---|
| `WEAVIATE_BIN` | `/home/elliotbot/clawd/weaviate-bin/weaviate` | Path to extracted binary |
| `WEAVIATE_HOST` | `127.0.0.1` | Loopback-only bind (reverse-proxy if exposing) |
| `WEAVIATE_PORT` | `8090` | crowdsec holds 8080; 8090 free |
| `WEAVIATE_DATA_DIR` | `/home/elliotbot/clawd/weaviate-data` | Persistent volume mount target |
| `AGENCY_OS_WEAVIATE_MAX_MEM` | `2.5G` | Cgroup ceiling — KEI-56 pre-condition |
| `CLUSTER_HOSTNAME` | `node1` | Single-node Raft cluster name |
| `CLUSTER_ADVERTISE_ADDR` | `127.0.0.1` | Single-node Raft advertise (Vultr has no private IP) |
| `RAFT_JOIN` | `node1` | Self-join for single-node bootstrap |
| `DEFAULT_VECTORIZER_MODULE` | `none` | Schema doc convention: explicit vectors only |
| `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED` | `true` | Loopback-only host; auth at reverse-proxy layer |

## Schema convention (per `docs/schema/weaviate-schema-requirements.md`)

Every collection has these 5 properties (4 mandatory + 1 optional):

```json
{"name": "raw_text",         "dataType": ["text"]}   // mandatory — re-embedding insurance
{"name": "environment_hash", "dataType": ["text"]}   // mandatory — reproducible re-embedding (KEI-60)
{"name": "created_at",       "dataType": ["date"]}   // mandatory — ISO-8601 UTC
{"name": "agent",            "dataType": ["text"]}   // mandatory — callsign or 'system'
{"name": "kei",              "dataType": ["text"]}   // optional — KEI ID that triggered the write
```

`vectorizer=none` — agents write vectors directly using the
`AGENCY_OS_EMBEDDING_MODEL`-pinned model (`gemini-embedding-001` by default).
Server-side vectorization is deliberately disabled to keep model pinning explicit
across the corpus.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `systemctl status weaviate.service` shows `code=exited` | Binary or data dir missing | Re-run install steps 1-3 |
| `503 Service Unavailable` on `/v1/.well-known/ready` | Raft still bootstrapping (4-6s after start) | Wait 8s, retry |
| `failed to get final advertise address: no private IP` | Cluster env vars missing | Verify `CLUSTER_ADVERTISE_ADDR=127.0.0.1` exported (already in `weaviate_capped.sh`) |
| `address already in use :8090` | Old scope unit stuck | `systemctl --user stop 'weaviate-*.scope'` then restart |
| Cgroup cap not enforced | Wrapper bypassed | Ensure unit's `ExecStart` points at `weaviate_capped.sh`, not at the bare binary |

## Verification snapshot (install-time, 2026-05-14)

```
$ systemctl --user show weaviate-922166.scope --property=MemoryMax,MemoryAccounting,MemoryCurrent
MemoryCurrent=45776896
MemoryAccounting=yes
MemoryMax=2684354560

$ python3 infra/weaviate/smoke_test.py --host 127.0.0.1 --port 8090
[1/5] GET http://127.0.0.1:8090/v1/meta
      version=1.37.3
[2/5] GET http://127.0.0.1:8090/v1/schema — expect classes=['Codebase', 'Decisions', 'Discoveries', 'Keis', 'Sessions']
      OK: all 5 classes present
[3/5] POST http://127.0.0.1:8090/v1/objects (id=137aac2b-..., class=Discoveries)
      OK: insert response id=137aac2b-...
[4/5] GET  http://127.0.0.1:8090/v1/objects/Discoveries/137aac2b-...
      OK: round-trip raw_text contains obj_id
[5/5] DELETE http://127.0.0.1:8090/v1/objects/Discoveries/137aac2b-...
      OK: probe cleaned up
KEI-48 SMOKE PASSED — Weaviate 1.37.3 reachable, schema valid, round-trip OK.
```

## Related

- KEI-43 — agent auto-start systemd services (merged `afdb692a`); same systemd-user pattern as this unit.
- KEI-44 — Cognee 3GB memory cap (merged `3b133132`); `cognee_capped.sh` is the wrapper pattern this runbook copies.
- KEI-56 — memory-cap policy (this is one of its pre-conditions).
- KEI-60 — embedding-model-independence + re_embed_corpus.py; the schema convention above implements the property contract.
- 12 downstream KEIs blocked on this install (per Dave verbatim ts ~1778742300).
