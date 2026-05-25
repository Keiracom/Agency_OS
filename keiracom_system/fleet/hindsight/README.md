# keiracom_system/fleet/hindsight — fleet Hindsight engine (Phase A1)

**bd:** Agency_OS-njhl (Phase A1 — Hindsight fleet deployment + wired wrappers + fleet tenant in control-plane)
**Anchor:** `ceo:keiracom_build_priority.phase_a_build_unblockers.a1`
**Sibling:** `keiracom_system/dev/hindsight/` (Orion's dev variant; coexists on same host, port 8888 vs 8889)

## Acceptance status (Phase A1 dispatch)

| Criterion | Status | Evidence |
|---|---|---|
| Hindsight container running on fleet infra with health check passing | ✅ | `keiracom-fleet-hindsight` Up + health: starting/passing; port 8889 → 8888 internal |
| All 4 wrappers connected (smoke: write Decision/Artifact/TaskContext/AntiPattern, read back) | ✅ | `python3 smoke_wrappers.py` — 4/4 writes OK, 8 read-back rows |
| Fleet tenant_id row in keiracom_tenants | ✅ | `00000000-0000-0000-0000-000000000001` (tier=pro, topology=B_shared_schema, status=active) |
| Monitoring + health checks configured | ✅ | docker healthcheck (10s interval, /health probe); systemd unit script provided |

## Canonical key notes (per audit-dispatch checklist)

`ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation` includes:
`mem.engine_hindsight`, `mem.topology_tier_keyed`, `mem.tempr_cara`, `mem.cognee_retired`,
`mem.llamaindex_pinned`, `mem.weaviate_coldstart`. This deploy ships against those locked
positions — does not redeliberate.

## Impl-feasibility decisions

**Vultr (this host) via systemd-managed docker-compose** chosen over Railway. Reasoning:
- Mirrors the existing cognee.service pattern on the fleet Vultr host (zero new infra to provision).
- Orion's dev variant already proves the image + compose recipe end-to-end on this host.
- Railway adds a separate deploy surface for one container with no horizontal-scale need at V1.
- Fleet Hindsight is single-instance (V1); horizontal scale is a post-V1 problem.

**Port 8889 (NOT 8888)** so the fleet variant coexists with Orion's dev variant on the same host without conflict. Dev stays available for ongoing spike work.

**Tenant_id is a deterministic UUID** (`00000000-0000-0000-0000-000000000001`) because the schema uses UUID PK. The "tenant_id=1" framing from the V2.0 inventory's `tenant.single_supabase` row is conceptual; the actual PK is this canonical UUID, documented in `provision_fleet_tenant.py`.

## Layout

| File | Purpose |
|---|---|
| `docker-compose.yml` | Fleet container definition (image + ports + volume + healthcheck). Distinct compose project `keiracom-fleet-hindsight` so it coexists with the dev variant. |
| `provision_fleet_tenant.py` | Idempotent: inserts/returns the fleet tenant row in `public.keiracom_tenants` via Atlas's `provision_tenant` from PR #1131. Uses placeholder `llm_api_key_encrypted` until `infra.secrets_management` Vault substrate lands (Phase A1 boundary). |
| `smoke_wrappers.py` | Wires the 4 wrappers from PR #1134 against the deployed instance. Acceptance test for criterion 2. |
| `install_systemd_unit.sh` | Idempotent host-side install of `~/.config/systemd/user/keiracom-fleet-hindsight.service`. Wraps `docker compose up -d` via `sg docker`. |

## Operator runbook

```bash
# 0. Pre-req: keiracom_tenants migration applied to Supabase (done once,
#    Phase A1 via apply_migration MCP call 2026-05-25)

# 1. Create .env with OPENAI_API_KEY (sourced from /home/elliotbot/.config/agency-os/.env)
cd /home/elliotbot/clawd/Agency_OS/keiracom_system/fleet/hindsight
echo "OPENAI_API_KEY=$(grep ^OPENAI_API_KEY= /home/elliotbot/.config/agency-os/.env | cut -d= -f2-)" > .env

# 2. Bring up the container (one-shot bootstrap; systemd takes over thereafter)
sg docker -c "docker compose up -d"

# 3. Verify health
curl -sS http://localhost:8889/health  # {"status":"healthy","database":"connected"}

# 4. Provision fleet tenant (idempotent — re-runs return existing row)
set -a; source /home/elliotbot/.config/agency-os/.env; set +a
python3 provision_fleet_tenant.py

# 5. Smoke test all 4 wrappers
python3 smoke_wrappers.py  # expects 4/4 writes + non-zero read-back

# 6. Install + enable systemd unit (host-side; survives reboot)
bash install_systemd_unit.sh
systemctl --user daemon-reload
systemctl --user enable --now keiracom-fleet-hindsight.service
systemctl --user status keiracom-fleet-hindsight.service
```

## Monitoring + health checks

- **Container-level:** docker healthcheck runs every 10s; probes `GET /health` and expects HTTP 200 with `{"status":"healthy","database":"connected"}`. `docker ps` shows the health state.
- **Systemd-level:** unit is `Type=oneshot RemainAfterExit=yes`. State visible via `systemctl --user status keiracom-fleet-hindsight`. Failure-to-start surfaces in journal: `journalctl --user -u keiracom-fleet-hindsight`.
- **Application-level monitoring:** PR #1130 spike confirmed Hindsight emits Prometheus metrics at `/metrics` + OTel distributed tracing per `monitoring.md`. Hooking into BetterStack (already wired for fleet per Cat 16 `infra.observability`) is a Phase A2 follow-up — fleet Hindsight currently observable via container healthcheck + manual `/metrics` curl.

## Endpoints

- API: `http://localhost:8889`
  - `/health` — liveness probe
  - `/docs` — Swagger UI
  - `/openapi.json` — authoritative API spec
  - `/v1/default/banks/*` — bank ops (verified working via smoke_wrappers.py)
- UI: `http://localhost:10000` — Hindsight dashboard (operator-only)

## Phase A1 → A3 handoff

This deploy is the prerequisite for Phase A3 (memory cutover steps 4+5). When A3 starts:
- Indexers point at this instance (`http://localhost:8889`)
- 7 pipeline-fed Weaviate classes re-ingest into the same bank set
- 3 hand-migration classes (Sessions, Global_governance_patterns, Discoveries) preserve content from `/backups/memory_pre_hindsight_migration_20260525/`
- LlamaIndex retired (PR #1142 pin lifts at cutover step 5-B)

Post READY-FOR-A3 to elliot's inbox when this PR merges + the systemd unit is enabled on the fleet host.
