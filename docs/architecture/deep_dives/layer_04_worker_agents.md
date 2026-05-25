# Layer 4 — Worker Agents (Domain Execution)

**Owner:** Atlas (Phase 1 deep-dive author). Directive: KEI-SYSTEM-DEEP-DIVE 2026-05-25.

## Notes — canonical key evidence (per audit-dispatch checklist)

- `ceo:keiracom_architecture_v2_locked.v2_locks_not_for_redeliberation` includes `temp.middleware` (every worker LLM call routes through it) + `tier.curve_4_6_8_14` (capacity ceiling per tier).
- Cat 4 inventory rows (`cost.attribution_wrappers`, `cost.governance_attribution`) are LOOSE pending Layer 11 build.
- Cat 17 `tier.solo` row anchors per-tier worker count (Solo gets 2 workers; Pro 4; Team 8).
- `cust.multi_channel_communication` row anchors customer-side worker spawn channels.

## §1 Designed

Workers are ephemeral spawn-with-context Docker containers (per Aiden PR #1140 ephemeral scoping) executing domain tasks dispatched by the chat agent + deliberators. A worker's lifecycle is: spawn → receive task brief + relevant memory context → execute via available MCP tools → emit results + audit trail → terminate. No long-lived state on the worker itself; state lives in Layer 6 (memory) and Layer 9 (persistence).

V1 worker types in scope: build (code edits, PR opens), research (web/repo crawls + write-ups), audit (review existing artefacts against canonical keys), test (run pytest + report). Domain bundling is loose — a single worker can be repurposed by changing the system prompt + tool allowlist at spawn.

## §2 Built

Today in fleet: 4 worker callsigns (Atlas, Orion, Scout, Nova) running as long-lived tmux sessions on Vultr host. NOT the V1 ephemeral target. The migration to ephemeral spawn-with-context is V1 Criterion 1 (`crit1.ephemeral`) scoped in PR #1140 but not yet implemented. Worker→ephemeral conversion is multi-PR effort gated on Temporal middleware (`temp.middleware`).

What IS built today: per-worker dispatch via NATS inbox files (`/tmp/telegram-relay-<callsign>/inbox/`), worker reads brief, executes against shared codebase, posts outbox JSON, optionally opens PR. Bounded scope per dispatch. Cross-worker coordination via shared bd (beads) task graph.

## §3 Measured

**No production data yet** — fleet is pre-revenue, all worker activity is internal development. Internal-use signal available:
- bd task throughput: trackable via `bd list --status=closed --limit=N` but never aggregated to a metric
- PR per worker per day: trackable via `gh pr list --author=<callsign>` but never aggregated
- Token spend per worker: NOT measured (Layer 11 metering pipeline `cost.metering_pipeline` PR #1137 is the substrate; per-worker attribution lands in PR #1139 Item 1)

Honest gap: I cannot quote a worker-side latency, throughput, or cost number from production data. The shape is empirical (fleet has been running 4+ workers for weeks) but no aggregator captures the numbers.

## §4 Token budget / cost behaviour at this layer

Workers are the largest single token consumer category in the fleet (every code-edit cycle is 5K–50K input tokens of context + 1K–10K output). Per `ceo:cache_framework_canonical`:
- Layer 1 Anthropic prompt cache (0.10x input): applicable to worker SYSTEM PROMPTS + STABLE TOOL DEFINITIONS. Per `feedback_socket_mode_single_connection` shape — repeated calls within 5-minute window hit the cache. Worker batches that fire ≥2 calls in a 5-min window get the discount; one-shot tasks do not.
- Layer 2 uncached (1.0x): dynamic per-task content — code under edit, KEI text, recent memory recalls.

Per-tier token budget gating happens at the Temporal middleware (`temp.inline.token_gate`) BEFORE the worker call lands. Workers themselves are not aware of the budget — the middleware short-circuits with an error response if exceeded.

## §5 Cache strategy applicable

- **Layer 1 (Anthropic prompt cache, 0.10x):** YES — worker system prompts + role-locked tool definitions are the canonical use case. Discipline doc (PR #1139 Item 3a) should explicitly call out worker prompt prefix stability as the dominant cache-hit lever.
- **Layer 2 (uncached, 1.0x):** YES — per-task dynamic context (file contents, KEI text). Cache miss is correct here.
- **Valkey semantic cache:** PARTIAL — if a worker task is semantically near a recent prior task (e.g. "fix lint in scripts/X" twice in 10 min), the Valkey layer can short-circuit before the LLM call. Lower hit rate at the worker layer than at the chat layer because workers execute mutation tasks (idempotency rare).
- **Hindsight beyond active window:** YES — recall pattern. Workers query Hindsight for prior decisions/artifacts via the MCP tools from PR #1136 instead of holding full history in context.

## §6 LOOSE items / open questions

- **L1:** Worker→ephemeral conversion sequence — depends on `temp.middleware` ratifying enforcement contract (Elliot owes per `temp.contract_doc`).
- **L2:** Per-worker domain bundling — is a single Atlas-class worker sufficient for V1, or do customers see "build / research / audit" as separate worker types with separate pricing?
- **L3:** Per-tier worker concurrency enforcement happens at the dispatcher (per Cat 17), but the dispatcher today is tmux-based — needs `temp.middleware` to enforce the 4/6/8/14 curve.
- **L4:** Worker output validation — `temp.async.post_validation` (response shape + citation validity) is RATIFIED but not built. Without it, worker outputs reach customers without correctness checks.

## §7 Per-tier behaviour variation

Per `tier.curve_4_6_8_14`:

| Tier | Worker concurrency | Cache framework multiplier proposal |
| --- | --- | --- |
| Sandbox | 1 worker | 0.5x (trial-grade priority; cache hits but no Valkey warm-up budget) |
| Solo | 2 workers | 1.0x (baseline) |
| Pro | 4 workers | 1.5x (Valkey warm-up + dedicated cache namespace) |
| Team | 8 workers | 2.0x (multi-user → larger Valkey footprint + shared cache pool) |
| Enterprise | custom | custom (per-tenant VPC + dedicated Valkey + dedicated TEI sidecar) |

Multipliers are PROPOSAL per `ceo:cache_framework_canonical.tier_multipliers_status` — pressure-test against actual customer mix in Phase 2.

## §8 Per-agent-type variation

| Worker type | System prompt cache target | Tool surface | Notes |
| --- | --- | --- | --- |
| Build | High stability (code conventions, lint rules, governance laws) — strong L1 cache fit | Edit/Read/Write + Bash + grep | Highest token consumer; biggest cache savings opportunity |
| Research | Medium stability (research methodology + citation format) — moderate L1 fit | WebFetch + Read + grep | Lower per-task token volume; cache savings smaller |
| Audit | Very high stability (canonical-key paste, governance contracts) — best L1 fit | Read + grep + canonical-key MCP | Predictable structure; ideal for L1 cache |
| Test | High stability (pytest invocation, ruff invocation) — strong L1 fit | Bash + Read | Smallest token tail; cache savings on overhead only |

Across all types: per-tenant boundary enforced at API layer (Layer 7), NOT at the worker layer. Workers never see another tenant's data.
