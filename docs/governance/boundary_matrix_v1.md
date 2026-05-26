# Boundary Matrix V1

**Status:** RATIFIED-CEO
**Version:** 1
**Ratified:** 2026-05-26T08:30:00Z
**Ratified by:** CONCUR-Full (Aiden + Max + Viktor) on Dave directive KEI-CEO-BOUNDARY-MATRIX-V1
**Canonical source:** Supabase `ceo_memory` key `ceo:boundary_matrix_v1`
**Directive:** #10028
**Filed under:** Agency_OS-9cgr

This document is a faithful mirror of the canonical key. The canonical key is the single source of truth; this file exists so reviewers and contributors can read the matrix without a Supabase round-trip. On any conflict, the canonical key wins — query it with `SELECT value FROM ceo_memory WHERE key = 'ceo:boundary_matrix_v1';`.

---

## 1. What this matrix does

It draws hard ownership lines between the eight architectural layers of Keiracom, declares the seven boundary violations CI must police, and sets the four-week kill criterion under which the NATS layer is removed if it earns its keep. Every CI guard in `scripts/ci/check_no_*.sh` traces back to a row in §3 or §4.

## 2. Decision rules — when does data go where

| Rule | When it applies |
|---|---|
| **Supabase only** | Final outcomes + audit log + cross-workflow historical queries + spend records. |
| **NATS exception only** | Fan-out broadcast + real-time heartbeats + empirically-validated <100 ms channels. |
| **Temporal Signal default** | Workflow-to-workflow + wait-for-event + durability/replay matters. |

Default to Temporal Signal. Choose NATS only if a sub-100 ms requirement is concretely benchmarked, not theoretical (per Viktor NIT 3 tightening).

## 3. Layer ownership contracts

| Layer | Owns |
|---|---|
| `mal` | All memory reads/writes (Memory Abstraction Layer). |
| `mcp` | Tool authorization + per-tenant allowed set. |
| `nats` | Real-time messaging fan-out (<100 ms latency requirement); observability fan-out (heartbeats, health pings) is categorically distinct from workflow state transport per Viktor NIT 2. |
| `valkey` | Rate limiting + KV cache only. |
| `sidecar` | Code execution sandbox. |
| `supabase` | Durable state + audit + cross-workflow queries. |
| `temporal` | Workflow execution + signals. |
| `dispatcher` | Tool routing only. |

## 4. Boundary violations to police

CI must fail the build on any of these:

1. Temporal must NOT serve as event bus.
2. NATS must NOT carry workflow state. (Workflow state = in-flight branching decisions; observability fan-out is NOT workflow state per Viktor NIT 2 disambiguation.)
3. Dispatcher must NOT do tool authorization.
4. Cognee / Hindsight must NOT store governance policy. (Policy-vs-memory test per Aiden + Viktor NIT 1: would this content read the same way for ANY tenant? Yes = Policy = Supabase; tenant-specific = Memory = Hindsight.)
5. Agents must NEVER bypass MCP for convenience tool calls.
6. Supabase must NOT be queried for in-flight workflow state.
7. Memory writes that bypass MAL wrappers must fail in CI.

## 5. Policy-vs-memory test

> Would this content read the same way for ANY tenant?
>
> - **Yes →** Policy. Lives in Supabase `ceo_memory` keys, governance laws, orchestrator runbook.
> - **No (tenant-specific) →** Memory. Lives in `mem.wrap.*` per-tenant via Hindsight `TenantExtension`.

This test is the canonical disambiguation surfaced by Aiden + Viktor NIT 1. Use it whenever a contributor is unsure whether a write belongs in `ceo_memory` or in Hindsight.

## 6. NATS kill criterion (4-week window)

| Field | Value |
|---|---|
| Window | 4 weeks of production-shape load (Dave dogfooding daily). |
| Scope | Measured against V1 production-shape load only (Aiden NIT 3). |
| Trigger to remove | No NATS channel requires sub-100 ms that Temporal Signal cannot meet. |
| Irreversibility note | NATS removal is reversible-via-redeploy in principle but operationally one-way once code dependencies are cleaned out. |
| Re-deliberation trigger | CONCRETELY BENCHMARKED sub-100 ms requirement (not theoretical) emerging in V1.x+ collaborative features (e.g. multi-thread chat cursor sync; real-time chip streaming) triggers re-deliberation BEFORE NATS removal commits (Viktor NIT 3 tightening). |

## 7. V1 documented exception

**`approval_gate_v1`** — A text-based approval gate (chat-message ConfirmYN response) for irreversible actions is a V1-acceptable substitute for the Temporal pause-pattern. V3 ships push-based approval workflow via the Temporal pause-resume primitive. Documented as a V1 mitigation, **not** a permanent exception (Aiden NIT 4).

## 8. CI guards (the four scaffolded for V1)

| # | Guard | Script | Polices |
|---|---|---|---|
| (a) | NATS forbidden in Temporal workflow files | `scripts/ci/check_no_nats_in_temporal_workflow_files.sh` | Violation #2 |
| (b) | Direct DB drivers forbidden outside MAL + `control_plane` | `scripts/ci/check_no_direct_db_outside_mal.sh` | Violation #7 |
| (c) | Composio imports forbidden outside MCP layer | `scripts/ci/check_no_direct_composio_outside_mcp.sh` | Violation #5 |
| (d) | Governance policy keys (`ceo:*`) forbidden in Hindsight wrappers | `scripts/ci/check_no_governance_policy_in_hindsight.sh` | Violation #4 |

Wired into `.github/workflows/ci.yml` as the `boundary-matrix-guards` job, sequenced `needs: backend-lint`. Each guard is a separate step so the failing one is obvious from the workflow log; `set -e` + non-zero exit fails the job. All four guards run on every push/PR.

**Scope note for guards (b) and (c):** these scan `src/keiracom_system/` only. Legacy Agency_OS BDR surface in `src/pipeline/` + `src/orchestration/flows/` is out of scope until the 3-repo split per `ceo:agency_os_keiracom_separation_v1` hands enforcement to the Keiracom-side repo. The Keiracom repo inherits these guards against its full `src/` at split-time.

**Guard (b) exempt path note:** `src/keiracom_system/control_plane/` is listed as an exempt path for raw asyncpg/psycopg usage alongside `src/keiracom_system/memory/`. `memory/` is the canonical MAL owner per §3; `control_plane/` is the to-be-built supabase-layer interface that owns `ceo_memory` and governance-audit writes. Listing a not-yet-existent path in the allowlist is harmless — it activates when the directory lands.

## 9. Deliberation provenance

| Reviewer | Verdict |
|---|---|
| Max | `REVIEW:approve:max` with 5 NITs (2 reinforcing Aiden, 3 distinct). |
| Aiden | `REVIEW:approve:aiden` with 4 NITs (policy-vs-memory boundary, NATS dual-publish framing, kill-criterion scope, V1 text-based approval exception). |
| Viktor | `CONCUR-Full` with 3 NIT responses (all APPROVE; one tightening on kill-criterion to require concrete benchmarked sub-100 ms, not theoretical). |

## 10. Cross-reference

- Canonical key: `ceo:boundary_matrix_v1`
- Completion marker: `ceo:directive_10028_complete`
- Drive Manual: Agency OS Manual §13 entry referencing #10028
- `cis_directive_metrics` row: `directive_id = 10028`
- Related canonical keys: `ceo:memory_abstraction_layer_v1`, `ceo:comm_architecture`, `ceo:agency_os_keiracom_separation_v1`
- bd issue (this scaffold PR): Agency_OS-9cgr
