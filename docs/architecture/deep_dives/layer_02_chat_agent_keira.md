# Layer 2 Deep-Dive — Chat Agent Keira

**Owner:** Aiden (architecture/governance lens — behaviour boundaries) + Viktor (persona spec)
**Per directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500
**Status:** WORKING DRAFT — open for Viktor positioning lens + Dave persona final review

## Notes — Canonical-key gate evidence (audit-dispatch checklist)

Queried `ceo:keiracom_architecture_v2_locked` (15 sub-keys); persona spec is at `persona.chat_agent_identity` line 196 RATIFIED-CEO (Dave sign-off 2026-05-25 ~1779742100 + Viktor 3-part deliberation + my "competent-peer" concern resolved via worked examples). The assembled v3 prompt is at `cust.chat_prompt_v3` line 178 LOOSE pending Dave final review of assembled file at `/home/elliotbot/clawd/Agency_OS/keiracom_system/personas/keira/system_prompt_v3.md`. `ceo:cache_framework_canonical.layer_2_uncached` confirms Layer 2 is uncached band (per-call dynamic content, 1.0× multiplier).

## §1 Designed

**Name = Keira.** Voice: direct + smart + helpful + curious-that-opens-conversation. Action-verb-first for task confirms ("Dispatching now" / "On it"); "I" for conversation. **Praise:** brief acknowledgment + redirect. **Hostility:** own if she erred, pivot to action; no performative apology. **Humor:** dry-wry only; customer sets tone first. **No cultural variants V1** — one Keira, different volumes. **Voice across surfaces:** same core, formality varies (chat full, dashboard terse, push notifications verb-first).

**Behaviour rules (RATIFIED-CEO):**
- **Handoff transparency rule:** *"This needs X. Routing to Y. Back to you in N."* — never silent handoffs, never opaque "I'll get on that."
- **Factual-correction rule:** correct gently with reasoning; don't patronize; don't capitulate; pivot to underlying problem.

**System prompt v3** assembles Viktor's 8 resolved answers + handoff transparency rule + 6 worked examples + Dave's factual-correction example. Pending Dave's final sign-off of the assembled file before LOOSE→RATIFIED-CEO promotion.

**Conversation framing per Cat 19:** chat agent v3 is calibrated for technical-builders / solo-founders ICP per `cust.icp_segmentation` Viktor narrow-to-1 recommendation. Chat reads as "competent peer who's going to help me get unblocked" NOT "AI assistant who wants to be helpful." That's the persona-depth dimension I flagged in `feedback_viktor_cross_check_gaps_2026-05-25`.

## §2 Built

**Persona spec file present** at `keiracom_system/personas/keira/system_prompt_v3.md` per `cust.chat_prompt_v3` row. Pending Dave final review of assembled prompt before ship.

**Inference substrate:** LiteLLM governance router (`gov.litellm_router` RATIFIED-RUNNING) routes Keira calls to customer BYOK provider key. Per `gov.customer_byok` line 162: Anthropic Haiku / OpenAI gpt-4o-mini / Gemini Flash / Azure depending on customer tier choice.

**Not yet built:**
- **Pre-filled first-chat prompt by project type** — onboarding step 5 per my Cat 19 §2.5 (Research/Build/Writing/Empty templates). Drop-off-prevention mechanism for blank-canvas paralysis.
- **Persona-volume modulation per surface** — full-voice in chat, terse on dashboard, verb-first on push notifications. Implementation pattern TBD — likely prompt-suffix layer keyed off `surface_context` parameter.
- **No-cultural-variants enforcement** — V1 design says "one Keira"; cross-locale customers see same voice. V1.x deliberation: do we add cultural variants (e.g. Australian-vs-US tone calibration)? Currently DEFERRED per `persona.behavioral_design`.

## §3 Measured

**No production data yet.** Pre-revenue per `feedback_pre_revenue_reality`. First-10-customer cohort produces the calibration signal for whether Keira's persona reads as "competent peer" or drifts toward "generic AI assistant trope."

**Honest measurement gap:** Viktor's coherence-check criterion 2 (per `feedback_viktor_coherence_check_and_persona_framing_2026-05-25`) is the empirical test — observer asks *"does this feel like one machine or three components?"* Until N>0 customers have run a real task through Keira and we can observe the outcome, we have NO behavioural-fit data. The persona is design-validated (Viktor + Dave + Aiden concurred), not customer-validated.

## §4 Token budget / cost behaviour at this layer

Layer 2 is **the primary LLM-cost layer for V1** — every customer chat turn fires a token call through Keira. Per `gov.customer_byok`: token cost lands on customer's BYOK provider account (we don't pay; we route).

**Keiracom-controlled cost surface:** governance overhead (Temporal interception layer adds latency + small token cost for inline gates — see Layer 7); metering pipeline read cost (PR #1137 captures per-tenant LLM metering for dashboard display); cache hit-rate (degraded cache → higher absolute cost on customer's BYOK).

**Cost behaviour pattern at Layer 2:**
- **Stable system prompt content** → Anthropic prompt cache 0.10× (cross-turn within 5-min TTL)
- **Per-turn user input** → uncached 1.0× (always fresh)
- **Recall context from Hindsight** → bounded by active window size + cache hit-rate on semantic Valkey cache (`cost.semantic_cache_valkey` line 78)
- **Reasoning trace emission** → stored to Hindsight (Layer 6) at write time; trace doesn't add live cost during chat turn

## §5 Cache strategy

Per `ceo:cache_framework_canonical.layer_2_uncached.multiplier = 1.0×` — Layer 2 is the UNCACHED BAND for per-call dynamic content (the customer turn itself). But Keira's framing wraps cached components:

**Cached at Layer 2:**
- **Keira system prompt v3** (Anthropic prompt cache 0.10× — stable per-domain content). System prompt v3 is well over the Anthropic cache eligibility threshold; will benefit from caching.
- **Memory Recall context** (Valkey semantic cache for repeated lookups within session per `cost.semantic_cache_valkey`).

**Uncached at Layer 2:**
- Customer user turn (always fresh)
- Conversation history beyond active window (per `ceo:cache_framework_canonical.history_beyond_active_window` — stored in Hindsight Layer 6 for queryable recall, NOT held in active context)
- Tool call results (per-call dynamic)

**Strategic implication:** Keira-prompt-cache discipline determines V1 economics. If cache hits hold near upper-bound (e.g. 70-80% on repeat-customer sessions), Keira's effective cost is much lower than naive 1.0× would suggest. If cache invalidates often (e.g. prompt edits cascade through TTL boundary), economics tighten. Phase 2 must measure cache hit-rate against first-10-customer telemetry.

## §6 LOOSE items / open questions

- **`cust.chat_prompt_v3` LOOSE pending Dave final review** — assembled v3 prompt at canonical file path needs final-sign-off. RATIFICATION blocker.
- **Pre-filled first-chat prompts by project type** — design exists (my Cat 19 §2.5), implementation pending.
- **Persona-volume modulation across surfaces** — implementation pattern TBD (prompt-suffix vs persona-microservice).
- **Multi-thread chat behaviour boundaries** — Pro multi-thread unlocks per Cat 17; how does Keira handle context-switching between topic chats within a project? Cross-thread memory boundaries: shared or per-thread? Worth pre-launch decision.
- **Voice input behaviour** — V3 surface per Cat 19 §2.7. When voice lands, Keira's "I'll dispatch that" verbal cadence needs voice-tuning (different prosody than text).
- **Error-handling persona** — when LLM rate-limits or Vault is sealed, Keira surfaces an error. Persona spec doesn't yet name the failure-mode voice (apologetic? matter-of-fact? actionable?). V1-required.
- **Push notification phrasing patterns** — "verb-first" framing per persona spec; concrete examples TBD.

## §7 Per-tier behaviour variation

Per `ceo:cache_framework_canonical.per_tier_multipliers_proposal`:

| Tier | Layer 2 multiplier | Keira behaviour delta |
|---|---:|---|
| Sandbox | 0.5× | Smaller context window; truncates history aggressively; single chat slot only |
| Solo | 1.0× | Baseline Keira; full system prompt v3; single-thread per project |
| Pro | 1.5× | Multi-thread chat unlocked; richer Memory Inspector recall context per turn |
| Team | 2.0× | Per-user chat slots; cross-user context boundaries enforced; user-mention disambiguation |
| Enterprise | custom | Compliance-vertical persona overlays (legal/health/accounting language calibration); per-VPC deployment |

**Architectural note (pressure-test):** the multiplier is COST-RELATIVE — Pro at 1.5× burns ~50% more tokens per chat session than Solo because (a) richer recall context per turn, (b) multi-thread context-switching overhead, (c) cross-thread memory awareness. Team 2× because per-user context multiplies linearly with active users in the project. Sandbox 0.5× because aggressive context truncation + rate-limit. **Honest gap:** these are PROPOSALS — not measured. Phase 2 first-10-customer cohort produces the calibration; multipliers may shift ±50% on real usage.

## §8 Per-agent-type variation

Keira is the ONLY customer-facing agent type at V1. Internal fleet agents (Aiden / Atlas / Max / Orion / Scout / Nova) are NEVER surfaced to customer per `ux.no_agent_language` lock — they live at Layer 3 (deliberators) and Layer 11 (cost optimization) operating beneath Keira's surface.

**Trust-theatre option** (Cat 19 §6C optional V2 differentiator): Pro+ outputs could carry "Reviewed by 2 specialists" badge — a sanitised surfacing of dual-CONCUR mechanism at Layer 3. NOT "Aiden + Max concurred" — just "dual-review verified" framing. Optional; pending Dave + Viktor positioning decision.

## Cross-cutting concerns touched

- **Multi-tenancy enforcement:** Keira's recall calls are tenant-scoped via Hindsight TenantExtension (PR #1132). Customer A's Keira NEVER sees customer B's memory. Enforcement at API layer (TenantExtension), not at chat-history-display.
- **Security (BYOK + secret leak):** Keira's responses go through Go Sidecar `ScanResponse` for secret-pattern detection before reaching customer LLM context (per `infra.secrets_management` integration line 208).
- **Reasoning trace + audit trail:** every Keira turn emits a reasoning trace via Temporal middleware (Layer 7) → stored in Hindsight (Layer 6). Customer can surface trace via `ux.diff.reasoning_trace_viewer` (Cat 19).
- **Compliance gates (V1.x for regulated verticals):** legal/health/accounting customers get audit-trail surface as feature; current ICP narrow-to-1 to technical-builders defers regulated-vertical persona overlays to V1.x post-Vault.

## Connects to

`[[layer_01_customer_surface]]`, `[[layer_03_deliberators]]`, `[[layer_06_memory]]`, `[[layer_07_governance]]`, `persona.chat_agent_identity`, `cust.chat_prompt_v3`, `ceo:cache_framework_canonical.layer_2_uncached`.
