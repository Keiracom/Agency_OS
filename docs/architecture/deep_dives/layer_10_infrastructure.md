# Layer 10 — Infrastructure (Vultr + Docker + Vault + Cloudflare)

**Owner:** orion
**Status:** PARTIAL — Vultr fleet host + Vault running; Docker conventions live; Cloudflare CDN DEFERRED to V1.1 per Cat 16
**Directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500

## Notes — canonical evidence pasted per audit-dispatch checklist

Inventory Cat 16 (Operability + Infrastructure) verbatim row excerpts:

- `infra.observability` — "Better Stack (already in fleet env vars) + per-layer /health checks" — LOOSE V1-required
- `infra.secrets_management` — "HashiCorp Vault self-hosted on Vultr (single node V1) with Transit engine for BYOK envelope encryption" — LOOSE-BLOCKER (now BUILT per PR #1146, this session)
- `infra.rate_limiting` — "request throttling at LiteLLM virtual key + token spend hard-stop via Temporal middleware" — LOOSE V1-required
- `infra.cdn` — "Cloudflare free tier. DEFERRED until ICP includes non-local customers" — DEFERRED
- `infra.backup_dr` — "MOVED FROM V1 HARD GATE TO V1.x FEATURE per Dave directive 2026-05-25 ~1779738300" — LOOSE (V1.x)
- `infra.cicd` — "GitHub Actions (partially exists today; gap audit needed)" — LOOSE V1-required
- `infra.iac` — "Pulumi (Python SDK) over Terraform for V1. V1 narrow scope: tenant provisioning automation triggered by Temporal workflow" — LOOSE V1-required

`ceo:keiracom_build_priority.phase_a_build_unblockers` — A2 (Vault) DONE, A4 (Go Sidecar) PENDING.

## §1 Designed

Five infrastructure substrates:

1. **Vultr** — primary cloud (Sydney region for AEST locality). Already in use for fleet host (`vc2-6c-16gb` 149.28.182.216) + Vault host (`vc2-1c-1gb` 45.77.51.184, this session).
2. **Docker** — runtime convention (containers for Hindsight, Weaviate, TEI, Vault, etc.). docker-compose for local-dev + service-config.
3. **Vault** — Phase A2 substrate; per-tenant BYOK envelope; Transit engine. Shamir 5/3 unseal V1; GCP KMS upgrade as `Agency_OS-hpst` follow-up.
4. **Cloudflare** — CDN tier, DEFERRED to V1.1 per Cat 16 row `infra.cdn`. Not built; not deployed; spec is "free tier when ICP geography expands".
5. **Pulumi** — IaC choice over Terraform (Cat 16 `infra.iac`). Python SDK fits team-language continuity. V1 scope is narrow: tenant provisioning via Temporal workflow.

Tying these together is `infra.observability` (Better Stack + per-layer /health) — already wired into fleet env (BETTERSTACK_* env vars present per earlier session work).

## §2 Built

| Component | Status | Evidence |
|---|---|---|
| Vultr fleet host | RUNNING | `vc2-6c-16gb` Sydney, 149.28.182.216, hosts Hindsight container + Weaviate + Cognee + 51 systemd services |
| Vultr Vault host | RUNNING | `vc2-1c-1gb` Sydney, 45.77.51.184, Vault 2.0.1 unsealed + Transit configured (this session, Phase A2) |
| Docker (fleet) | RUNNING | docker daemon + 16GB memory pressure (5GB swap used per session diagnostic); local-dev pattern at `keiracom_system/dev/{hindsight,vault}/` |
| Vault | RUNNING | Shamir 5/3 unsealed; Transit engine; `keiracom-tenant-extension` policy; service token TTL 24h; UFW :8200 ALLOW from fleet only |
| Vault Python client | MERGED | PR #1146 `src/keiracom_system/vault/vault_decryptor.py` (this session) |
| Cloudflare | NOT DEPLOYED | DEFERRED V1.1 per `infra.cdn` |
| Pulumi | NOT DEPLOYED | DESIGNED only; Cat 16 `infra.iac` LOOSE V1-required |
| Better Stack | PARTIAL | env vars present; per-layer /health checks per-service status unknown |
| systemd unit conventions | RUNNING | KEI-48 / KEI-44 patterns (memory-capped via `systemd-run --user --scope -p MemoryMax=...`) — established |
| UFW firewall posture | RUNNING (Vault host) | Vault host: default DROP + :22 ALLOW + :8200 ALLOW FROM 149.28.182.216 only |

Empirical scan:
```
ls /home/elliotbot/clawd/keiracom_system/dev/ → hindsight/ vault/ (the two local-dev rehearsals I built)
ls /home/elliotbot/clawd/Agency_OS-orion/scripts/orchestrator/ → weaviate_capped.sh, cognee_capped.sh, weaviate_backup.sh, weaviate_capped.sh (memory-capped service launchers)
```

## §3 Measured

Production data WHERE IT EXISTS (this session's empirical work):

| Metric | Value | Source |
|---|---|---|
| Fleet host RAM total | 15Gi | `free -h` |
| Fleet host RAM used | 9.0Gi | `free -h` |
| Fleet host swap used | 5.0Gi of 5.3Gi | `free -h` — under pressure |
| Top RSS consumers | weaviate 3.2GB, hindsight-api 1.4GB | `ps -eo rss,comm --sort=-rss` |
| Vault host RAM available | 1GB total (vc2-1c-1gb) | Vultr plan spec |
| Vault host Vault process RSS | ~100MB at idle | typical for single-node Vault, not yet sampled live |
| Vault unseal time after restart | NOT MEASURED — requires deliberate restart test | n/a |
| Vault encrypt latency (LAN) | ~50-100ms per call | informal smoke (criteria #3 verification, this session) |
| Vault host UFW: :8200 blocked from non-fleet IPs | VERIFIED | tested via `timeout 5 bash -c '</dev/tcp/...'` from fleet pre + post UFW rule |
| Hindsight container memory cap | 3GB | `weaviate_capped.sh` pattern (Weaviate) — Hindsight runs unbounded currently |
| Vultr account balance | $0 | Vultr API at session start |
| Vultr pending charges | $52.98 + $5/mo Vault = ~$58/mo current burn rate | Vultr API account endpoint |

What is NOT measured:
- Better Stack alert latency / coverage
- Disk usage trajectory (fleet host SSD)
- Per-service uptime (51 systemd services — no central dashboard)
- Network egress bytes (CDN need would surface here)
- Vultr Object Storage usage (file system — `infra.iac` references it but no use yet)

## §4 Token budget / cost behaviour

**Infrastructure itself consumes zero LLM tokens.** Cost shape at this layer:

| Category | Per month |
|---|---|
| Fleet host (vc2-6c-16gb Sydney) | ~$48 USD pending charges suggests current spend |
| Vault host (vc2-1c-1gb Sydney) | $5 USD ($7.75 AUD) — new this session |
| Cloudflare (DEFERRED) | $0 (free tier when activated) |
| Better Stack | Unknown — env vars present; tier TBD |
| Pulumi state storage (Vultr Object Storage) | <$1 USD typical |
| **Total Vultr current** | **~$53 USD/mo (~$82 AUD/mo)** |

Infrastructure cost is LINEAR with tenant count for per-tenant infra (Topology A enterprise tier — per-tenant VPC). Shared infra (Topology B) is per-host fixed cost amortised over N tenants — sublinear scaling.

`infra.iac` Pulumi tenant-provisioning workflow is the cost-control surface for V1: provisioning is automatic per signup, deprovisioning is automatic per churn — no human in the loop = bounded ops cost.

## §5 Cache strategy applicable

Infrastructure layer is BENEATH the cache strategy — caches run AT this layer (Valkey at Layer 11 needs a host, Hindsight pgvector at Layer 6 needs Postgres, Anthropic prompt cache is the provider's concern).

What Layer 10 contributes to caching:
- **Valkey deployment** — Cat 4 `cost.semantic_cache_valkey` RATIFIED-DM "Valkey running today". Layer 10 owns the host + healthcheck. Not yet capacity-planned per-tenant.
- **Vault Transit caching** — Vault Transit has internal LRU cache for active keys; not Keiracom-tunable. At scale (N tenants × frequent decrypt), the in-Vault cache hit rate determines decrypt latency.
- **Object Storage cache headers** — for V1 file uploads + Cloudflare-when-activated, cache TTL is set at Layer 10 storage config.

## §6 LOOSE items / open questions

1. **Fleet host memory pressure** — 5GB swap used of 5.3GB. Adding more services to this host risks OOM. Hindsight (1.4GB) is dev-only; can be torn down. Weaviate (3.2GB) is critical until memory-cutover Phase A3 retires it.
2. **Better Stack coverage** — env vars present but per-layer health-check map is not documented. Layer 12 deep-dive (Scout+Atlas) addresses observability; Layer 10 needs to surface "what hosts are monitored".
3. **Pulumi tenant-provisioning workflow** — `infra.iac` LOOSE V1-required. Depends on Temporal (Layer 5) which is DESIGNED NEVER DEPLOYED. Sequencing: Temporal deploy → Pulumi workflow → first tenant provisioned.
4. **CI/CD gap audit** — `infra.cicd` LOOSE: "tests yes, deploys via Railway, rollouts via Vercel, rollbacks UNKNOWN — Phase 2 sub-item". Rollback procedure is the hard gap (Phase B3 `Rollback procedure + Vercel CI-gating`).
5. **Cloudflare ICP-trigger** — `infra.cdn` DEFERRED until ICP geography expands. No defined trigger condition (which customer or which signup geo activates it?).
6. **Vault HA tripwire** — Cat 16 `infra.secrets_management` sub-item (c): "3-node cluster at what threshold — probably mem.tenancy_tripwire 20-30 tenants". Naming `infra.vault_ha_tripwire` as own concept would clarify.
7. **Composio per-tenant OAuth segregation** — Cat 16 sub-item (d) "HARD-GATE-WITHIN-HARD-GATE". Covered in Layer 8 deep-dive but the infra fault domain (one Composio account = one HTTP origin = one rate-limit pool per tenant) is Layer 10-shaped.
8. **Backup-DR for Vault** — V1.x scope per `infra.backup_dr` reframe; Vault data dir + Shamir share rotation backup not yet defined. PR #1146 docs the recovery procedure but doesn't ship the backup mechanism.

## §7 Per-tier behaviour variation

| Tier | Infra topology | Host model |
|---|---|---|
| Sandbox | Topology B (shared fleet host) | No dedicated resources; 10 tasks/day rate limit at LiteLLM (Phase E e2) |
| Solo | Topology B | Shared host, schema-per-tenant; minimal per-tenant overhead |
| Pro | Topology B | Shared host, schema-per-tenant; multi-thread workflows allowed |
| Team | Topology B | Shared host, schema-per-tenant; per-user accounting |
| Enterprise | **Topology A** per-tenant VPC | Per-tenant Vultr instance (region of customer choice for compliance); per-tenant Hindsight + Vault + LiteLLM; per-tenant Composio account |

Phase A `infra.iac` Pulumi automation handles Topology B provisioning (schema in shared Postgres). Topology A (Enterprise) requires `infra.iac` "Vultr VPC provisioning per tenant (Scale-tier only, re-introduce on first Scale-tier customer)" which is DEFERRED.

## §8 Per-agent-type variation

Infrastructure is largely agent-type-agnostic, BUT some specifics:

| Agent type | Infra concern |
|---|---|
| Chat agent (Keira) | Customer-facing; latency-critical → benefits from Cloudflare CDN when activated for the dashboard + chat endpoints |
| Deliberators | Internal-only → no CDN need; sit on fleet host's internal LAN to LiteLLM internal-Gemini route |
| Worker agents | Long-running; need persistent host or workflow-engine durability (Temporal) — Layer 10 hosts the worker pool runtime |
| Sidecar processes (TEI, Go Sidecar) | Per-tenant or per-instance; container resource cap conventions apply per `weaviate_capped.sh` pattern |

## Cross-cutting concerns

- **Multi-tenancy enforcement** — Vault Transit per-tenant key naming (`keiracom-tenant-{tenant_id}`) makes the cross-tenant decrypt attempt structurally impossible (verified PR #1146 + this session smoke). Topology A per-tenant VPC adds isolation at the infra level for Enterprise tier.
- **Security (BYOK + secret mgmt)** — Vault is THE primary surface (Phase A2 done). Three secret categories per `infra.secrets_management`: customer BYOK keys (Vault Transit envelope, in Postgres), internal service credentials (Vault store, V1.x to wire), Composio OAuth tokens (per-tenant Composio account = customer-owned, not in Keiracom Vault).
- **CI/CD + rollback** — `infra.cicd` LOOSE; Phase B3 has rollback gap. SonarCloud → CodeQL migration (PR #1138, `op.codeql_migration` RATIFIED-CEO) is one CI improvement; orchestrator-merge-after-NATS-concur pattern is the deploy-gate.
- **Backup-DR (V1.x)** — Vault data dir backup not yet shipped; Hindsight per-tenant export is V1.x per Dave reframe; Postgres backup via Supabase PITR ($39/mo Pro tier mentioned in `infra.backup_dr`).
- **Customer file system** — Vultr Object Storage as backend per `infra.iac`. Layer 10 owns the bucket + access policies; Layer 7 governance owns the per-tenant ACL.
- **Reasoning trace + audit trail** — emitted by services in Layers 5/7/12; Layer 10 provides the storage substrate. Postgres for active; Hindsight for historical (post-active-window per cache framework).
- **Compliance gates** — `tier.enterprise` compliance certifications (SOC 2 / HIPAA per `tier.enterprise` row) drive Layer 10 hardening: Topology A per-tenant VPC, separate Vault instance per regulated customer, region-locking.

## Sources

- `ceo:keiracom_architecture_v2_locked` (queried 2026-05-25)
- `ceo:keiracom_build_priority` Phase A + B + Cat 16
- Inventory Cat 16 (7 rows) + Cat 20 line 524
- PR #1133 — TEI sidecar (running)
- PR #1146 — Vault decryptor (this session)
- bd `Agency_OS-31bk` — Phase A2 Vault parent
- bd `Agency_OS-hpst` — Shamir → GCP KMS upgrade follow-up
- `scripts/orchestrator/weaviate_capped.sh` — systemd memory-cap pattern (KEI-44 / KEI-48)
- `/home/elliotbot/clawd/keiracom_system/dev/vault/PRODUCTION_DEPLOYMENT.md` — Shamir recovery procedure
