# Cutover Requirements V1 — Full List

**Author:** Viktor (compiled from Dave's Cutover Readiness Gate directive 2026-05-27)
**Status:** RATIFIED-CEO — canonical reference for ephemeral cutover work
**Anchor:** Dave directive #ceo 2026-05-27 ts approx 1779853990

> The list is complete. Nothing on it is optional.

## AGENT-SIDE

- **Identity as system prompt template** — Agent identity portable and not session-resident; survives fresh spawn without accumulated context
- **Persona context-independence** — Persona definition works correctly from cold start; no reliance on what the agent "remembers" from prior session
- **Memory fully externalised** — All memory dependencies out of agent process; agent never relies on session memory across spawns
- **Tool access via MCP only** — No direct SDK or API calls from agents; all tool access gated through MCP
- **Done-criteria per task type** — Every task type has an unambiguous, mechanical definition of "done" before dispatch
- **Hard token + time ceiling per spawn** — Each spawned agent has an enforced token limit and wall-clock kill timer at the dispatcher level

## INFRASTRUCTURE-SIDE

- **Temporal workflows for full agent lifecycle** — Spawn, execute, recover, and die workflows defined and running in Temporal for every agent role
- **Dispatcher workflow-driven** — Dispatcher refactored off tmux-driven model; fully workflow-driven dispatch in production
- **Tmux session manager retired** — Not deferred. Fully retired from production
- **Keepalive fresh-context default** — ✅ Done (PR 1201 merged 2026-05-27 — first gate item green)
- **Wake hook scheduler retired** — Wake hook replaced by event-triggered spawn; old scheduler not running
- **Inbox watcher + send-keys relay retired** — Replaced by direct API call; relay pattern fully decommissioned
- **Context window budget per role enforced at dispatch** — Each role has a defined context ceiling; dispatcher mechanically enforces it before spawn

## STATE SEPARATION

- **Ephemeral persistence boundary spec written** — Document defining exactly what state is ephemeral (dies with spawn) vs durable; no ambiguity at the boundary
- **Durable state → Temporal + Postgres** — All durable state stored there, not in agent process
- **Knowledge state → pgvector** — Atomized memory live and retrievable
- **Configuration state → versioned config** — Governance policy in versioned config, not hardcoded
- **Cold archive → explicit recall API only** — No passive bleed of archive state into agent context

## COST TELEMETRY (all red — hard gates)

- **Per-spawn token logging** — Input / output / cache-read / cache-write tracked per spawn, stored, queryable
- **Spawn attribution** — Each token cost attributed to the specific spawn that incurred it
- **Per-task-type cost attribution** — Costs broken down by task type so you can see what's expensive
- **Daily cost rollup to #ceo** — Automated daily summary of spend posted here (PR 1202 in flight)
- **Real-time dashboard** — Live cost visibility for Dave without waiting for Anthropic bill
- **Budget ceiling enforcement firing** — When spend hits ceiling, spawn is mechanically stopped — not logged, *stopped* (PR 1203 in flight)
- **Cache hit-rate observability** — Cache performance visible; can verify TTL is working as intended

## MODEL ROUTING

- **Tiered model routing live** — Tasks routed to appropriate model tier (Flash / Sonnet / Opus) based on complexity; not everything hitting the expensive model
- **Cache TTL set to 5-minute default** — Prompt caching TTL configured; cache actually being used and measurable

## TASK QUEUE INTEGRITY

- **Idempotency keys on task queue** — Tasks have idempotency keys so duplicate dispatches don't cause double-execution or cost double spend
- **Explicit policy at budget ceiling** — Clear defined behaviour (not just a crash) when a spawn hits its ceiling: what happens to the task, what gets logged, what alerts

## GOVERNANCE ENFORCEMENT

- **Domain-to-tool mappings in versioned config** — Which agent role can call which tools is locked in config, not ad hoc
- **Go Sidecar denying cross-domain calls in production** — Mechanical enforcement of tool scope at runtime; not just policy
- **MCP tools/list filtered per role** — Each agent only sees the tools it's authorised for
- **Tenant isolation at atom-store layer** — Retrieval and write isolation enforced at the store, not just provenance tagging

## QUALITY PRESERVATION

- **Atomization pilot validated end-to-end** — Skills atomized, retrieval working, composer functioning at human endpoints
- **Task decomposition discipline documented** — Clear rules for when to decompose vs keep whole
- **Externalisation triggers defined** — Documented policy for when to fork to subprocess vs spawn LLM
- **Verification pass operational** — Fabrication verifier and claim-verification layer active in production (already shipped)

## PRE-FLIGHT SMOKE TESTS (run immediately before declaring go)

- **Bounded ephemeral spawn end-to-end on API** — One real spawn on Gemini Flash (or equivalent), cost measured, spawn dies cleanly
- **Migration spike — 5 real production tasks** — Not synthetic. Five actual workloads run end-to-end through ephemeral dispatcher on subscription. Cost measured per task. No bug spirals. All five clean = gate green
- **Task decomposition quality test** — One task decomposed end-to-end; confirm output quality matches persistent-session baseline
- **Adversarial input test** — One adversarial input run against a fresh-context spawn; confirm governance holds without persistent context
- **Keepalive respawn test** — Confirm fresh context on respawn, no state carryover (PR 1201 covers, will revalidate at smoke pass)

## CURRENT SCORE (2026-05-27)

- ✅ Green: 5 (bounded-spawn validated, keepalive fresh-context, ephemeral substrate foundation 6/7, atomization pilot, Temporal engine live)
- 🔴 Red: 17+ (everything in cost telemetry, model routing, task queue, governance enforcement, and all smoke tests)

## CONCUR-GATE RULE

Every architecture deliberation opens with: *"Does this satisfy the cutover gate, or violate it?"*

- Proposals that build a gate item → concur eligible
- Proposals that defer gate items → require explicit Dave override
- Proposals that would land work post-cutover with gate items still red → REJECTED at the deliberation tier
