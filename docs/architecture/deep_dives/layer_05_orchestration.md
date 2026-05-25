# Layer 5 — Orchestration (Temporal workflow engine)

**Owner:** orion
**Status:** **HARD GAP — DESIGNED, NEVER DEPLOYED** (per Cat 20 inventory line 519)
**Directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500

## Notes — canonical evidence pasted per audit-dispatch checklist

- `ceo:keiracom_architecture_v2_locked` — listed `temp.middleware` in `v2_locks_not_for_redeliberation`
- `ceo:keiracom_build_priority.phase_e_capacity_abuse.e2` verbatim: "Rate limiting at LiteLLM + token spend hard-stop via Temporal middleware (already proposed)"
- `ceo:keiracom_build_priority.phase_a_build_unblockers` — Temporal NOT in Phase A (no A1-A4 row deploys it)
- Inventory Cat 5 row source attribution: `temporal_interception_layer 2026-05-25 (Elliot+Aiden concur)` — design ratified, no deployment record
- Inventory Cat 20 verbatim (line 519): "Orchestration (Temporal workflow engine — designed, NEVER deployed) — Orion / LOOSE (deep-dive pending; HARD GAP)"
- `ceo:cache_framework_canonical` — Layer 11 produces implementation spec; Layer 5 hosts the cache-check INLINE gate

## §1 Designed

Yes. Spec is locked across 10 inventory rows in Cat 5:

| Row | Status | Role |
|---|---|---|
| `temp.middleware` | RATIFIED-CEO | Single chokepoint between chat input and LLM token call |
| `temp.inline.listener` | RATIFIED-CEO | Reasoning Listener — capture "why" behind decisions |
| `temp.inline.token_gate` | RATIFIED-CEO | Token spend hard-stop per call |
| `temp.inline.cache_check` | RATIFIED-CEO | Layer 11 cache-strategy dispatch (prompt cache / Valkey / Hindsight) |
| `temp.inline.tier_gate` | RATIFIED-CEO | Tier feature gating (Sandbox/Solo/Pro/Team/Enterprise) |
| `temp.inline.audit` | RATIFIED-CEO | Audit trail emission to `dashboard` |
| `temp.inline.content_check` | RATIFIED-CEO | Pre-call privacy/regulated-content checks |
| `temp.async.post_validation` | RATIFIED-CEO | Async continuation — response shape + citation validity (Aiden refinement) |
| `temp.contract_doc` | LOOSE (BLOCKER for build) | One-page per-gate contract: emit guarantees + enforce-vs-warn semantics. **ELLIOT OWES BEFORE BUILD.** |
| `temp.dispatcher` | RATIFIED-CEO | Temporal as workflow engine for dispatcher (replaces NATS-loop/tmux-pane-injection per `v1_completion_criteria` criterion 1; ephemeral scoping PR #1140) |

Design pattern: **6 inline gates + 1 async continuation, single chokepoint at temp.middleware.** Per Aiden refinement, inline gates fail-fast on policy violation; async continuation handles post-call validation that doesn't block user response.

## §2 Built

**Nothing.** Empirical scan:
```
grep -rliE 'temporal\.io|@temporalio|workflow.*temporal' src/  →  0 files
grep -rliE 'temporal' .claude/  →  0 files
ls /home/elliotbot/clawd/Agency_OS-orion/src/keiracom_system/temporal/  →  does not exist
```

Confirms Cat 20 dispatch attribution. Phase A (Vault + Hindsight deploy + Go Sidecar + memory cutover) does not include Temporal deploy. The dispatcher in `src/dispatcher/main.py` is the NATS-loop/tmux-pane pattern Temporal is meant to replace per `temp.dispatcher` + `v1_completion_criteria` criterion 1.

`temp.contract_doc` is the LOOSE blocker that gates build. Elliot owes it. No build can start until that contract is written + deliberator-concurred.

## §3 Measured

**No production data — Temporal not deployed.** Honest framing per Cat 20 line 519. This section will populate after Phase E2 ("token spend hard-stop via Temporal middleware") deploys.

The closest existing measurement is the metering pipeline (PR #1137) which captures token counts AFTER Hindsight emits a log line — i.e., per-call attribution, not per-workflow attribution. Temporal would add workflow-level attribution (a chat turn that triggers 6 LLM calls would be one workflow with 6 child activities), which the metering pipeline cannot currently produce.

## §4 Token budget / cost behaviour

Temporal IS the layer that enforces token budgets. `temp.inline.token_gate` is the runtime enforcement of the per-call cap + tier-scaled pool described in `cost.token_budget` (Cat 4 LOOSE — Viktor 4-component proposal). Without Temporal deployed:

- Per-call cap: not enforced today (no chokepoint)
- Tier-scaled pool: not enforced today (no dispatcher tracking budgets per tenant)
- Hard-stop: not enforced today (no enforce-vs-warn surface)

Cost behaviour AT this layer: zero direct LLM cost (workflow engine doesn't call LLMs itself). All cost is in the activities Temporal invokes — those activities live in Layers 2/3/4 (chat agent / deliberators / workers).

Operational cost (Temporal Cloud vs self-host): not yet decided. Temporal Cloud is ~$200/mo for low-volume tier; self-host adds ops burden. Recommend deciding at build dispatch.

## §5 Cache strategy applicable

`temp.inline.cache_check` is the dispatch site for Layer 11 cache strategy. Per `ceo:cache_framework_canonical`:

- **Anthropic prompt cache (0.10× input cost)** — applied to structurally stable per-domain content. Temporal middleware decides if the upcoming LLM call qualifies (content shape + tenant tier) and routes to the prompt-cache-enabled provider config.
- **Uncached (1.0×)** — per-call dynamic content. Default fall-through.
- **Valkey semantic cache** — repetitive query hits. Temporal middleware checks Valkey BEFORE the LLM call; cache hit short-circuits to cached response + emits audit event.
- **Hindsight beyond active window** — context not held in active window; Temporal middleware retrieves via Hindsight recall before constructing the LLM prompt.

All four strategies fan in to `temp.inline.cache_check`. Temporal is the integration point — Layer 11 spec is the routing logic.

## §6 LOOSE items / open questions

1. **`temp.contract_doc` (Elliot owes)** — per-gate contract: what's emitted, enforce-vs-warn semantics, error shape. Build blocker.
2. **Temporal Cloud vs self-host** — operational cost trade-off undecided.
3. **NATS coexistence** — Viktor 2026-05-25 verbatim retained NATS as inter-agent messaging fabric (separate from Temporal-as-workflow-engine). Boundary needs concrete naming in build dispatch: which signals stay on NATS, which become Temporal activities/signals.
4. **Migration strategy from `src/dispatcher/main.py`** — current dispatcher is NATS-loop/tmux-pane. PR #1140 (Aiden ephemeral scoping) names this as 8 tmux-coupled subsystems requiring 5-stage migration. Temporal deploy depends on that migration sequencing.
5. **Activity timeout policies** — LLM calls can take 30-120s; deliberator concurs take longer (minutes). Default Temporal activity timeouts may need tier-aware tuning.
6. **Workflow versioning** — Temporal's deterministic-replay requires careful workflow code versioning. No spec yet for Keiracom's versioning approach (event sourcing? blue-green workflow code deploy?).
7. **Where the post-validation async continuation lives** — Aiden refined to ASYNC. Spec doesn't yet name whether it's a separate child workflow or a continue-as-new activity.

## §7 Per-tier behaviour variation

| Tier | Tier multiplier (proposal per `ceo:cache_framework_canonical`) | Per-call cap | Temporal-specific |
|---|---|---|---|
| Sandbox | 0.5× | Smallest cap (free eval; 10 tasks/day per Cat 17) | Aggressive token-gate cut-off; cache-check force-hit prompt cache when available |
| Solo | 1.0× | Baseline cap | Standard gates |
| Pro | 1.5× | Looser cap | Multi-thread chats unlock (Pro+) → multiple parallel workflows per tenant; tier-gate enforces concurrency cap (4-6-8-14 curve) |
| Team | 2.0× | Larger cap | Per-user budget pools (Team has multiple users); tier-gate dispatches per-user attribution |
| Enterprise | custom | Custom | Per-tenant VPC topology A — Temporal cluster may be per-tenant for compliance verticals; tier-gate becomes per-tenant-instance config |

Tier multipliers PROPOSAL — pressure-test in Phase 2 per `ceo:cache_framework_canonical.tier_multipliers_status`.

Sandbox 10-tasks/day rate limit (Cat 17 `tier.sandbox`) is enforced at the dispatcher (Phase E e1 verbatim: "Tier capacity enforcement (4-6-8-14 curve at dispatcher)"); Temporal `tier-gate` is the runtime check on each workflow start.

## §8 Per-agent-type variation

| Agent type | Workflow shape | Temporal-specific |
|---|---|---|
| Chat agent (Keira, Tier 1 ephemeral) | One workflow per chat turn | Activity = LLM call. Inline gates apply per-activity. Async post-validation for citation checks. |
| Deliberators (Tier 2 CONCUR-gated) | One workflow per CONCUR cycle | Activity = each deliberator's review call. tier-gate enforces min 3 deliberators on paid tiers (per `tier.baseline_rule`). |
| Worker agents (Tier 3 domain execution) | Long-running workflow per task | Activities span minutes to hours; activity timeouts must accommodate. Heartbeat protocol mandatory. |

Cross-cutting per agent type: every workflow emits `temp.inline.audit` events for dashboard reasoning-trace view (Cat 19 ux.surface.reasoning_trace). Audit shape needs to be one schema across all agent types so Layer 12 observability can aggregate.

## Cross-cutting concerns

- **Multi-tenancy enforcement** — Temporal namespace per tenant for Topology A (per-VPC); shared namespace + tenant_id metadata for Topology B. `tier-gate` enforces tenant_id == workflow.metadata.tenant_id. Mechanical check at activity-start, not UI.
- **Security (BYOK + secret mgmt)** — `temp.inline.content_check` runs against `mcp.go_sidecar` static config to block raw-secret leakage into LLM context. Vault decryption happens at activity-level (via PR #1146 `VaultDecryptor`), never at workflow-level.
- **CI/CD + rollback** — workflow code versioning unresolved (see §6). Activity code can rollout standard; workflow code needs deterministic-replay-safe deploy. Likely needs a sub-spike before build.
- **Backup-DR** — Temporal event history IS the workflow source of truth. Lost = lost workflows. V1.x backup-DR (`infra.backup_dr`) must include Temporal event history alongside Hindsight + Postgres.
- **Customer file system** — file uploads land in S3-compatible storage (V1 Vultr Object Storage per `infra.iac`); Temporal workflows reference them by URI. No file content in workflow state.
- **Reasoning trace + audit trail** — emitted by `temp.inline.audit`; consumed by Layer 7 governance + Layer 12 observability. Schema TBD in `temp.contract_doc`.
- **Compliance gates** — `temp.inline.content_check` is the runtime enforcement point. Privacy/regulated checks before any LLM call. Per-tier policy.

## Sources

- `ceo:keiracom_architecture_v2_locked` (queried 2026-05-25)
- `ceo:cache_framework_canonical` (queried 2026-05-25)
- `ceo:keiracom_build_priority` Phase E e2 (Temporal token-spend hard-stop)
- Inventory rows Cat 5 (10 rows) + Cat 20 line 519
- PR #1140 — Aiden ephemeral scoping
- PR #1137 — metering pipeline (orthogonal data layer; not Temporal-aware)
- `v1_completion_criteria` criterion 1 (ephemeral agent system replaces tmux)
