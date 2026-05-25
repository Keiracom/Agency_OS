# Layer 8 — Integration (MCP + Composio + LiteLLM)

**Owner:** Orion (MCP + Composio sidecar wiring) + Atlas (joint)
**Status:** PARTIAL — MCP tier-aware server merged (PR #1136); Composio per-tenant POC OPEN (`Agency_OS-aynv`); LiteLLM running per Cat 11 RATIFIED-CEO
**Directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500

## Notes — canonical evidence pasted per audit-dispatch checklist

Inventory Cat 10 (MCP) verbatim:

- `mcp.abstraction` (RATIFIED-CEO, PR #1136) — "All tools exposed via MCP servers; tools/list resolves per-tenant allowed set"
- `mcp.composio` (RATIFIED-DM, Viktor verbatim 2026-05-25 + Aiden anchor MAL §11) — "Composio as integration library beneath MCP (implementation choice; not architectural constraint)"
- `mcp.go_sidecar` (RATIFIED-DM, BUILD pending) — "Go sidecar — security interceptor + tool-call validator; static config not knowledge graph; mechanical enforcement"
- `mcp.tei_sidecar` (RATIFIED-CEO, running, PR #1133) — "TEI sidecar serving BAAI/bge-small-en-v1.5"

Inventory Cat 11 (LiteLLM + BYOK) verbatim:
- `gov.litellm_router` (RATIFIED-CEO, running) — "LiteLLM as governance router with BYOK key resolution — RATIFIED AND RUNNING (T0.2 audit)"

`ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation` includes `gov.litellm_router` + `gov.composio_per_customer_segregation`.

`ceo:keiracom_build_priority.phase_b_v1_hard_gates.b2` verbatim: "Composio per-customer segregation (uses Agency_OS-aynv POC verification first)"

## §1 Designed

Three integration substrates, three roles:

1. **MCP (Model Context Protocol)** — `mcp.abstraction`. All tool access goes through MCP servers. Per-tenant `tools/list` resolves the allowed set (tier-aware feature gating).
2. **Composio** — `mcp.composio`. Sits BENEATH MCP as the integration library that wraps the 250+ underlying APIs (Salesforce, HubSpot, Slack, GitHub, etc.). Per Dave directive 2026-05-25 decision #3 + `gov.composio_per_customer_segregation` lock: **one Composio account per customer** (account-per-tenant model).
3. **LiteLLM** — `gov.litellm_router`. Governance router that resolves BYOK keys at LLM-call time + applies rate limiting (per Phase E e2). Running today; pre-dates this audit.

Plus two sidecars (Cat 10):
4. **Go Sidecar** (`mcp.go_sidecar`) — security interceptor that intercepts MCP tool calls + validates against static-config domain whitelist. Mechanical enforcement, not knowledge graph. BUILD pending (Phase A4 `phase_a_build_unblockers.a4`).
5. **TEI Sidecar** (`mcp.tei_sidecar`) — embedding service for Hindsight. RUNNING (PR #1133, my work).

The layer's job: present a clean tool-call surface to agents (via MCP) while hiding the integration plumbing (Composio + LiteLLM) AND enforcing per-tenant access + security.

## §2 Built

| Component | Status | Evidence |
|---|---|---|
| `mcp.abstraction` (tier-aware MCP server) | MERGED | PR #1136 (Atlas) — `src/keiracom_system/mcp/` |
| `mcp.tei_sidecar` | RUNNING | PR #1133 + dev container `keiracom-dev-hindsight` consumes via `http://embed:80`; production deploy via Phase A1 (Hindsight fleet) |
| `gov.litellm_router` | RUNNING | T0.2 audit — pre-dates this work. No PR in this session's window. |
| `mcp.composio` (architectural commitment) | DESIGNED | `gov.composio_per_customer_segregation` locked; `skills/composio-oauth/SKILL.md` is the integration skill stub |
| `mcp.composio` (per-tenant segregation actually working) | POC OPEN | `Agency_OS-aynv` — Atlas spot-check HOLD anchor; verification not yet run |
| `mcp.go_sidecar` | NOT BUILT | Phase A4 `phase_a_build_unblockers.a4`; "binary skeleton + domain whitelist + GitOps config" |

Empirical scan:
```
ls src/keiracom_system/ → embeddings/ mcp/ memory/ metering/ tenant/ vault/
grep -rli composio src/ skills/ → skills/composio-oauth/SKILL.md only (skill stub)
```

## §3 Measured

**No production-scale data.** Layer 8 has shipped runtime components (MCP server merged, TEI running, LiteLLM running) but multi-tenant production traffic doesn't exist yet (pre-revenue).

What is measurable today against the dev Hindsight container (per my il34 spike runs):
- TEI sidecar embed call: ~0.7s for 100 fixtures via `retain` (which routes embedding via TEI internally; see PR #1137 §benchmark)
- Hindsight ingest rate: 3.05 items/sec at n=100, 2.02 items/sec at n=1000 — slowing at scale (likely consolidation overhead, not TEI overhead)

What is NOT measured:
- MCP `tools/list` resolution latency per tenant
- Composio API call latency / failure modes (no account provisioned yet)
- LiteLLM routing decision overhead
- Go Sidecar interception latency (not built)

## §4 Token budget / cost behaviour

**Tool calls themselves consume LLM tokens** (the model's "tool_use" + "tool_result" content blocks). Per Anthropic pricing, tool definitions count as input tokens (cacheable per Layer 11 strategy if structurally stable).

Cost shape per integration substrate:
- **MCP `tools/list`** — definition catalog; structurally stable per tenant tier; **Layer 1 prompt cache target** (0.10× input cost). Definitions can be 1-10K tokens depending on tool count. Cache lifetime ≥ tier-config TTL.
- **Composio** — adds per-call cost (Composio API pricing) ON TOP of LLM token cost. Pricing model needs verification in `Agency_OS-aynv` POC (account-per-tenant means N customers = N Composio accounts = N billing relationships).
- **LiteLLM** — passthrough cost (it's a proxy not an LLM); the routing decision itself is sub-millisecond. Rate-limiting may DROP calls (rejected before LLM cost incurred — net cost savings).
- **TEI sidecar** — zero LLM cost (embeddings are local BGE-small inference). Cost = sidecar host time (~$0 marginal at fleet scale).
- **Go Sidecar** — zero LLM cost (mechanical validation). Cost = latency added to every tool call.

The metering pipeline (PR #1137 — my work) captures token spend per LLM call but does NOT yet attribute tool-call overhead separately. Layer 11 cost dashboard ought to show "tool overhead" as a distinct line if we want to monitor it.

## §5 Cache strategy applicable

Per `ceo:cache_framework_canonical`:

| Cache layer | Layer 8 application |
|---|---|
| **Layer 1 — Anthropic prompt cache (0.10× input)** | MCP `tools/list` catalog (structurally stable per tier). Tier-config TTL determines re-cache cadence. |
| **Layer 2 — uncached (1.0×)** | Each tool's parameters + return value (dynamic per call) |
| **Valkey semantic cache** | Repetitive tool calls with identical args + recent recency (e.g., "fetch HubSpot company by domain X" — same X within N seconds returns cached result without hitting HubSpot). Cache key = canonical tool-call hash. |
| **Hindsight beyond active window** | Tool-call audit trail beyond active context — recall via Hindsight for compliance / debugging. NOT a perf cache; an observability store. |

Layer 8 routing decision: at MCP tool-call dispatch, check Valkey first (cache hit short-circuits the Composio call); on miss, hit Composio; on success, populate Valkey. Cache invalidation is per-tool: data-fetch tools have short TTL (~60s); definition fetches have long TTL (~24hr).

**Post-ephemeral cache-validity question** (`cost.cache_post_ephemeral_validity` Aiden §3.C nit): when chat agents are ephemeral (spawn-execute-die per `eph.scoping`), each spawn loses local cache locality. Valkey is shared so cache hits survive across spawns; but the LLM prompt-cache only sticks within Anthropic's 5-min window per cache breakpoint. New ephemeral spawn = new connection = new prompt cache miss on first call.

## §6 LOOSE items / open questions

1. **`Agency_OS-aynv` Composio POC** — gates Phase B2. Needs to verify: (a) per-tenant OAuth segregation actually isolates data, (b) per-customer Composio account pricing model fits the unit economics, (c) onboarding flow when customer adds an integration (do they create their own Composio account, or do we create one on their behalf?).
2. **`mcp.go_sidecar` build** — Phase A4 unblocker. Aiden Phase 1 §3.A item 7 spec'd it; no implementation yet. Domain whitelist source-of-truth + GitOps config flow needs naming.
3. **MCP `tools/list` tier-resolution** — Atlas PR #1136 implements tier-aware filtering; needs deliberator-cross-check that the per-tier tool sets are correctly carved (Sandbox = view-only; Solo = read; Pro = write; Team/Enterprise = admin).
4. **LiteLLM virtual-key per-tenant** — currently virtual keys exist; per-tenant assignment + rotation flow not yet defined as a runbook.
5. **Composio cost ceiling** — if each tenant = 1 Composio account, what's the OPEX at N tenants? Cat 16 `infra.secrets_management` sub-item (d) flagged this as "HARD-GATE-WITHIN-HARD-GATE" — `Agency_OS-aynv` must answer.
6. **Tool-overhead metering** — PR #1137 attributes LLM tokens but not tool-call overhead. Layer 11 dashboard column for "% of cost from tool calls vs raw LLM" is a useful visibility add (LOOSE).
7. **Cache invalidation on Composio webhook** — Composio offers webhooks for data changes (e.g., HubSpot company updated). Spec doesn't yet say whether webhooks fan in to Valkey cache invalidation.

## §7 Per-tier behaviour variation

| Tier | MCP tool set | Composio | LiteLLM rate limit | Go Sidecar policy |
|---|---|---|---|---|
| Sandbox | View-only subset; 10 tasks/day rate limit | Disabled (no real tool calls in eval) | Aggressive (free tier protection) | Strictest whitelist (no external write tools) |
| Solo | Read-mostly; one project | Standard | Per-tenant cap | Standard whitelist |
| Pro | Read+write; multi-thread | Standard | Looser cap | Standard whitelist + Pro-only tools |
| Team | Full + admin actions | Standard + multi-user attribution | Per-user cap | Per-user policy |
| Enterprise | Custom — per-tenant whitelist | Per-tenant Composio account (already the default per `gov.composio_per_customer_segregation`); for Enterprise, may be per-instance | Per-tenant SLA | Customer-customisable whitelist + compliance attestation |

Per Phase E e3 `Multi-tenant isolation enforcement at API layer` — Layer 8 is one of the enforcement surfaces. MCP `tools/list` per-tier filtering is mechanical; Go Sidecar domain whitelist is mechanical. Both fail-closed on tier-config mismatch.

## §8 Per-agent-type variation

| Agent type | MCP tool surface | Composio usage | LiteLLM routing | Go Sidecar exposure |
|---|---|---|---|---|
| Chat agent (Keira, Tier 1) | Read tools + customer-facing actions (within tier set) | Per-tenant account | Customer's BYOK key | Yes — every tool call validated |
| Deliberators (Tier 2) | Governance read tools (Linear, GitHub PR lookup) | Internal-only (Keiracom-owned Composio account, not per-tenant) | Internal Gemini routing per `reference_model_routing.md` | No — internal-only, sidecar not in path |
| Worker agents (Tier 3) | Domain-specific tool subset (e.g., HubSpot worker has HubSpot tools only) | Per-tenant account | Customer's BYOK key | Yes — every tool call validated |

Worker agents are domain-scoped at the MCP `tools/list` level — a HubSpot worker can't see Salesforce tools even if the tenant has both integrations enabled. This is part of `mcp.go_sidecar` enforcement spec.

## Cross-cutting concerns

- **Multi-tenancy enforcement** — Composio per-tenant accounts (architectural lock) + MCP per-tenant `tools/list` + Go Sidecar per-tenant whitelist. THREE mechanical layers; if any one drifts, cross-tenant leakage risk. `Agency_OS-aynv` POC is the integration-test surface for this.
- **Security (BYOK + per-customer segregation)** — Vault Transit (PR #1146) gives BYOK envelope; LiteLLM looks up the right tenant key at call time; Go Sidecar prevents the decrypted key leaking into LLM prompt (separate from `VaultDecryptor` — that's the read side; Go Sidecar is the egress side).
- **CI/CD + rollback** — MCP server + Composio config + Go Sidecar config should ALL be GitOps-managed per `mcp.go_sidecar` "GitOps config" verbatim. PR-as-config-change with deliberator concur.
- **Backup-DR (V1.x)** — Composio data is in customer's own Composio account; ergo backup-DR for integration data is OUTSIDE Keiracom's scope (we never hold it). LiteLLM virtual keys + MCP per-tenant config need backup.
- **Customer file system** — file uploads via MCP file tool; sidecar validates allowed file types per tier. Storage is Vultr Object Storage (V1) per `infra.iac`.
- **Reasoning trace + audit trail** — every MCP tool call emits an event consumed by Layer 12 observability. `Cat 19 ux.surface.reasoning_trace` is the customer-visible view.
- **Compliance gates** — Go Sidecar is the runtime check; static config maps allowed tool → allowed tier → allowed customer (for regulated verticals). Compliance attestation per Enterprise tier (`tier.enterprise`).

## Sources

- `ceo:keiracom_architecture_v2_locked` (queried 2026-05-25)
- `ceo:keiracom_build_priority` Phase A4 + B2 + E
- Inventory Cat 10 (4 rows) + Cat 11 (2 rows of relevance) + Cat 20 line 522
- PR #1136 — Atlas tier-aware MCP server
- PR #1133 — Orion TEI sidecar (this layer's running embedding component)
- PR #1146 — Orion Vault decryptor (cross-layer; called by LiteLLM at routing time)
- bd `Agency_OS-aynv` — Composio per-tenant POC (Aiden owner)
- `skills/composio-oauth/SKILL.md` — Composio integration skill stub
- `reference_model_routing.md` — internal Gemini routing memo
