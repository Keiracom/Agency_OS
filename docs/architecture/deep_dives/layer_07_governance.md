# Layer 7 Deep-Dive — Governance (CONCUR + Go Sidecar + versioned config)

**Owner:** Aiden (architecture/governance lens)
**Per directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500
**Status:** WORKING DRAFT — open for Elliot orchestration-feasibility cross-pass + Max code-quality lens

## Notes — Canonical-key gate evidence (audit-dispatch checklist)

Queried `ceo:keiracom_architecture_v2_locked` (15 sub-keys). `v2_locks_not_for_redeliberation` includes `temp.middleware`, `gov.litellm_router`, `gov.composio_per_customer_segregation`. Pulled `ceo:memory_abstraction_layer_v1.value.temporal_interception_layer` (Dave-ratified 2026-05-25 with Elliot+Aiden concur, 6 inline gates + 1 async Aiden refinement, Elliot owes one-page contract). `op.orchestrator_merge` line 547 RATIFIED-CEO + KEI-206 author-exclusion live. Cat 10 + 11 + 15 + 16 rows pulled. Per `ceo:cache_framework_canonical.layer_2_uncached`: governance enforcement at the Temporal chokepoint is per-call dynamic (uncached); audit emission is post-call async continuation.

## §1 Designed

**Three pillars at Layer 7:**

### 1A. CONCUR mechanism (Layer 3 procedural + Layer 7 enforcement)
**Per `op.orchestrator_merge` line 547 + KEI-206 author-exclusion (PR #1116):**
- Worker proposes → 2-of-3 deliberators concur → Elliot admin-merges
- Author-exclusion: PR author excluded from their own concur
- `gh pr comment [REVIEW:approve:<callsign>]` is the audit trail
- Runtime enforcement at merge gate, not at comment-post

### 1B. Temporal interception layer (single chokepoint)
**Per `ceo:memory_abstraction_layer_v1.value.temporal_interception_layer` ratified 2026-05-25 (Dave + Elliot + Aiden concur):**

Temporal middleware sits between chat input and LLM token call. Single chokepoint that everything passes through. Hosts both reasoning-listener (capture why) AND governance enforcement.

**6 inline gates at chokepoint** (per `inline_at_chokepoint` array):
1. Reasoning listener (capture why behind decisions)
2. Token spend gates (does this exceed budget or rate limit)
3. Cache discipline checks (is this call cache-busting unnecessarily)
4. Tier feature gating (does customer plan allow this primitive)
5. Audit trail emission (record interception event)
6. Pre-call content checks (privacy or regulated-content rules)

**1 async continuation** (per `async_continuation_not_inline` — my Aiden refinement that landed):
- Post-call validation (response shape + citation validity) — lives in same Temporal workflow graph but ASYNC, doesn't hold up response return

**Open action Elliot owes:** one-page contract definition for the interception point BEFORE Phase 2 build on this layer. Defines emit guarantees (audit event shape + minimum fields) + enforce-vs-warn semantics per gate type.

### 1C. Go Sidecar (mechanical enforcement)
**Per `mcp.go_sidecar` line 149 RATIFIED-DM + my Cat 19 §5B HARD-BLOCKER + PR #1144 scaffold concur'd:**

Per-tenant Go HTTP sidecar co-located with agent container. Static config (NOT knowledge graph). Three enforcement responsibilities:
1. **Tool whitelist** (Cat 10) — `Allow(ToolCall)` against per-tenant `AllowedTools []string`
2. **System file isolation** (Cat 19 `ux.files.system_files_hidden`) — `strings.HasPrefix(path, deny)` against `SystemPathDeny []string`
3. **Secret leak detection on responses** (Cat 16 `infra.secrets_management`) — `ScanResponse(body)` against global + per-tenant secret patterns

**Architectural ratification I landed in PR #1144 review:** **FAIL-CLOSED on SPOF.** If sidecar `/validate` call fails for any reason (timeout, 5xx, connection refused), upstream MCP tool call is REJECTED not forwarded. Consistent with Cat 16 HARD GATE posture (Vault sealed = fail; BYOK invalid = fail; rate limit = reject).

### 1D. Versioned config + supporting governance
- **LiteLLM governance router** (`gov.litellm_router` line 160 RATIFIED-CEO + RUNNING per T0.2 audit): BYOK key resolution between customer input and LLM call
- **Composio per-customer segregation** (`gov.composio_per_customer_segregation` line 163 RATIFIED-CEO HARD GATE — Dave decision #3 + my Cat 16 escalation): ONE Composio account per customer, NOT shared. Resolves HARD-GATE-WITHIN-HARD-GATE concern
- **Discovery log** (`op.discovery_log` line 548 RATIFIED-CEO via PR #1120): bd + Beads/Linear integration
- **Audit dispatch checklist** (`op.audit_dispatch_checklist`): canonical-key query gate + paste-evidence-in-PR-notes
- **CodeQL canonical security gate** (`op.codeql_migration` line 549 + my §3.C calibration framework)
- **Governance laws as code not comments** (per GOV-12): runtime enforcement required

## §2 Built

**Running today:**
- CONCUR mechanism live via `op.orchestrator_merge` + KEI-206 (PR #1116 RATIFIED)
- LiteLLM governance router T0.2 active (4 healthy backends, Gemini-first internal)
- Discovery log + bd + Beads/Linear integration via PR #1120
- CodeQL migration (PR #1138) — canonical security gate post-calibration; my §3.C threshold (3-5 PRs dual-validation) exceeded ~8 PRs since migration
- Internal fleet hardcoded Gemini 2.5 Flash (`gov.internal_gemini` line 161) for governance/internal work — never Anthropic API per `reference_model_routing`

**Just-landed (admin-merge eligible):**
- PR #1146 Vault Transit envelope decryptor (Aiden HOLD-LIFTED + Max APPROVE)
- PR #1147 Phase A3 dual-write mirror (Aiden CONCUR + Max APPROVE)
- PR #1144 Go Sidecar research+scaffold (Aiden CONCUR + Max APPROVE)

**Build pending:**
- Temporal interception layer middleware code — design ratified, no code yet (Elliot owes one-page contract first)
- Go Sidecar production build (engineer-tier Atlas + Orion per Cat 10 ownership; 10-item handoff scope from PR #1144 §6 + my 5 NITs + Scout's 3 bonus items)
- Vault server provisioning on Vultr VC2 1c1gb Sydney (separate KEI; PR #1146 ships CLIENT only)
- Composio per-customer-segregation implementation (HARD GATE before V1 launch per `gov.composio_per_customer_segregation`)

## §3 Measured

**Operational governance signals (this session telemetry):**
- ~15 PR reviews; CONCUR mechanism worked end-to-end on all
- Author-exclusion ENFORCED: 2 mis-attribution catches (`feedback_attributed_work_not_mine_2026-05-25` first + second instance)
- Canonical-key-query discipline ENFORCED: my Viktor CARA fabrication refusal + 1146 stale-path doc nit + 1147 cross-cite errors (§3.A items 21+23 / item 7) all caught
- Empirical-smoke catches paper-concur misses: 3+ documented this session (PR #1141 wrapper-class miss; PR #1147 Pytest regression that paper-review didn't catch)

**Honest measurement gap:** **Layer 7 governance enforcement is NOT YET measured against customer traffic.** Temporal middleware is design-ratified, not built. Go Sidecar is scaffold-only. Vault production deploy pending. **Pre-revenue per `feedback_pre_revenue_reality`** — no customer-traffic-tested governance.

**Internal-fleet governance is measurable today** (CONCUR enforcement + canonical-key gate + author-exclusion + CodeQL); customer-facing governance (Layer 7 chokepoint + sidecar + Vault encrypt-at-rest) is design + scaffold + client-half.

## §4 Token budget / cost behaviour at this layer

**Layer 7 adds modest overhead to every LLM call** through the Temporal chokepoint:
- **Inline gates 1-6:** each fires once per call. Latency budget: ~5-10ms per gate cumulative (Reasoning listener emits async; token gate is hash lookup; cache check is Valkey hit/miss; tier gate is in-process dict; audit emit is fire-and-forget; content check is regex match). Total budget: <60ms per call inline overhead.
- **Async continuation 7 (post-call validation):** doesn't hold up response return; lives in workflow graph; cost is post-call CPU not user-facing latency.
- **Go Sidecar `/validate`:** per Cat 17 §2A network-hop tax — 1-5ms per MCP tool call. For tool-heavy agents (10+ calls/turn) that's 50ms cumulative.

**Token cost surface at Layer 7:**
- **Internal Gemini Flash for governance reasoning** (`gov.internal_gemini`): if Temporal gates use LLM for content-check decisions, internal Gemini eats the cost. Flat-rate budget; doesn't burn customer BYOK.
- **Audit trail emission token cost:** if audit-log row content includes LLM-generated summary, internal Gemini cost again. NEGLIGIBLE per emit.
- **Customer BYOK pass-through:** the actual LLM call after Layer 7 gates → customer's key pays.

**Cost behaviour pattern:** Layer 7 is COST-OVERHEAD-PER-CALL not COST-DENSITY. Adds ~50-100ms latency + small internal-Gemini compute per call; doesn't multiply customer LLM cost.

## §5 Cache strategy

Per `ceo:cache_framework_canonical`: Layer 7 governance enforcement is per-call dynamic (uncached, 1.0× band) for the actual gate decisions. But the gate-INPUTS can be cached:

**Cached at Layer 7:**
- **Tier config (`tools/list` resolution)** — per-tenant tool allowlist resolved at Temporal chokepoint. Tenant config rarely changes; short-TTL cache acceptable
- **Vault BYOK key decryption result** — within a chat session, Vault decrypt once + cache decrypted key in memory. NEVER persist to disk
- **Go Sidecar config** — `Config` struct loaded at startup; hot-reload on signal per NIT-9 of PR #1144 handoff
- **Audit-log batched emission** — high-throughput emit can batch to NATS audit subject

**NOT cached at Layer 7:**
- Per-call gate decisions (always evaluated fresh against current state)
- Reasoning listener output (per-call dynamic)
- Token-spend gate state (must read current per-tenant counter)

**Cache invalidation:**
- Tier upgrade → tier config cache invalidate
- BYOK key rotation → Vault decrypt cache invalidate
- Tenant Sidecar config update → SIGHUP-triggered atomic config swap (NIT-9 of PR #1144 handoff)
- Governance rule landing → Temporal middleware redeploys (CI/CD path); cache flushed by restart

## §6 LOOSE items / open questions

- **Temporal interception layer one-page contract** — Elliot owes BEFORE Phase 2 build per `temporal_interception_layer.open_action_elliot_owns`
- **Go Sidecar production build** — 10 items from PR #1144 §6 + my 5 NITs + Scout's 3 bonus items (GitOps wiring, slog default, liveness/readiness split)
- **Vault server provisioning** — Vultr VC2 1c1gb Sydney + Shamir init + setup_transit + my Viktor-7 §1B unseal-posture concerns (chmod 400, distributed shares, drill not docs, Cloud-KMS Agency_OS-djeb sequencing)
- **Composio per-customer-segregation implementation** (HARD GATE before V1 launch) — Composio API support for per-tenant accounts not yet verified; build path TBD
- **Versioned config posture** — config-as-code with SchemaVersion field (NIT-4 of PR #1144), HMAC-signed config (item 7 of PR #1144 §6), GitOps wiring (Scout bonus item)
- **Fail-closed vs fail-open semantics per gate** — Layer 7 lands fail-closed default I ratified for Go Sidecar SPOF; same default should propagate to Vault decrypt failure, LiteLLM unavailable, Temporal chokepoint timeout. Elliot's one-page contract documents per-gate semantics
- **Compliance gate ratchet** — when regulated-vertical ICP enters V1.x scope, additional gates (HIPAA-specific content check, legal-discoverability flag, accounting audit-trail format) land at this layer. Phase 2 sub-deliberation when V1.x scope commits

## §7 Per-tier behaviour variation

Per `ceo:cache_framework_canonical.per_tier_multipliers_proposal` (architectural pressure-test from my Cat 17 §1 review):

| Tier | Layer 7 multiplier | Governance enforcement delta |
|---|---:|---|
| Sandbox | 0.5× | Relaxed CONCUR (carve-out per my Cat 17 §3B); 2-deliberator sole-review allowed; reduced audit-log granularity |
| Solo | 1.0× | Baseline Layer 7 chokepoint; full 6 inline gates; standard audit log |
| Pro | 1.5× | Multi-thread chat governance overhead (per-thread audit-log scoping); richer content checks |
| Team | 2.0× | Per-user authorization gates at chokepoint; cross-user content-share rules; team-admin escalation surface |
| Enterprise | custom | Compliance-vertical gate overlays (HIPAA / privilege / audit format per vertical); per-VPC sidecar deploy; signed-config hard requirement |

**Architectural pressure-test:** Layer 7 multipliers describe GOVERNANCE-DENSITY (number + complexity of gates per call), not LLM-cost-density. Enterprise is `custom` because compliance vertical gates vary per vertical — legal needs privilege-discovery hold; health needs HIPAA-encryption-at-rest verification; accounting needs audit-immutability proof. **Honest gap:** these multipliers are PROPOSALS — first-10-customer-cohort governance-incident-rate produces calibration signal.

## §8 Per-agent-type variation

**Customer-facing chat agent (Keira):** every chat turn goes through Layer 7 chokepoint. All 6 inline gates fire. Audit log emits per turn.

**Internal fleet agents (Aiden/Atlas/Max/Orion/Scout/Nova):** also subject to CONCUR mechanism for PR reviews + dispatch protocols. Author-exclusion enforces governance discipline. Discovery log captures cross-session learning. Internal-fleet doesn't have customer-tenant Temporal chokepoint (no chat turns to gate); doesn't have Go Sidecar (no MCP tool-call abuse to prevent at customer-facing surface).

**Deliberator agents (Elliot/Aiden/Max):** ARE the CONCUR mechanism at Layer 3; their CONCUR posts ARE Layer 7 enforcement events. Self-referential — deliberators are both subject AND mechanism of governance.

**Worker agents (Atlas/Orion/Scout/Nova):** subject to CONCUR via PR review; subject to canonical-key-query gate (audit-dispatch checklist) BEFORE writing artefact; subject to discovery log capture mandate.

**Boundary:** customer-tenant Layer 7 enforcement (Temporal chokepoint + Go Sidecar + Vault) is per-customer; internal-fleet Layer 7 (CONCUR + canonical-key gate + author-exclusion) is per-deliberator+worker. Different mechanisms, same governance philosophy: **gates as code not comments** (GOV-12), **mechanical enforcement not aspirational documentation**.

## Cross-cutting concerns touched

- **Multi-tenancy enforcement:** Layer 7 enforces at THREE places — Temporal chokepoint (per-tenant tool list resolution), Go Sidecar (per-tenant `AllowedTools` + `SystemPathDeny`), Vault (per-tenant Transit keying via `keiracom-tenant-{tenant_id}` prefix per PR #1146). Defense in depth.
- **Security (BYOK custody + secret mgmt + per-customer segregation):** Vault Transit decryptor (PR #1146 client; server-side KEI separate); Composio per-customer-segregation HARD GATE (`gov.composio_per_customer_segregation`); Go Sidecar `ScanResponse` enforces no raw secret leaks into LLM context.
- **CI/CD + rollback:** Layer 7 GATES the CI/CD; CodeQL canonical post-PR-#1138 calibration; deliberator CONCUR is the runtime enforcement at merge gate. Rollback discipline tracked separately at Cat 16 `infra.cicd` LOOSE V1-required.
- **Backup-DR (V1.x):** moved to V1.x per Dave reframe 2026-05-25 ~1779738300. V1 ships with infra-layer backup (Supabase PITR + multi-region); per-tenant export waits on Hindsight upstream PR (M2 mitigation).
- **Customer file system:** Go Sidecar enforces `ux.files.system_files_hidden` via path-deny prefix matching; CAT 19 GAP closed via PR #1144 production build (engineer-tier).
- **Reasoning trace + audit trail:** Reasoning Listener inline at Temporal chokepoint (gate 1); audit emit at gate 5; both feed Hindsight Layer 6 for queryable recall.
- **Compliance gates:** Layer 7 IS the runtime enforcement substrate for compliance verticals. When V1.x ICP includes legal/health/accounting, gate overlays land here.

## Connects to

`[[layer_01_customer_surface]]` (Audit Log surface + trust-theatre "Reviewed by 2 specialists"), `[[layer_02_chat_agent_keira]]` (Layer 7 wraps every Keira call), `[[layer_03_deliberators]]` (CONCUR is the Layer 3 procedural + Layer 7 enforcement), `[[layer_06_memory]]` (Reasoning Listener emits to Hindsight; Trace primitive at Layer 6 stores Layer 7 audit events), `temp.middleware`, `mcp.go_sidecar`, `gov.litellm_router`, `gov.composio_per_customer_segregation`, `infra.secrets_management`, `op.orchestrator_merge` + KEI-206, `op.codeql_migration`, `ceo:memory_abstraction_layer_v1.value.temporal_interception_layer`.
