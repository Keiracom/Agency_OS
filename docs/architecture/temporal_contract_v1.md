# Temporal Interception Layer — Per-Gate Contract V1

**Owner:** Elliot
**Status:** DRAFT pending Aiden + Max concur
**Anchor:** ceo:keiracom_architecture_v2_locked Cat 5 temp.middleware + 6 inline gates + 1 async continuation; temp.contract_doc LOOSE row (BLOCKER for A6 first-workflow-migrated step)
**Directive:** KEI-DAVE-MIGRATION-PATH Phase A6 (Orion's Temporal deploy blocks on this contract)
**Date:** 2026-05-25

---

## Purpose

Temporal middleware is the single chokepoint between chat input and the LLM token call. Six gates run INLINE (must complete before the LLM call returns); one runs ASYNC (continuation after the LLM call returns).

This contract defines per-gate:
1. **Emit guarantee** — what event the gate writes to the audit trail
2. **Enforce-vs-warn semantics** — does failure BLOCK the LLM call or just LOG?
3. **Failure mode** — what happens when the gate itself errors

The contract is referenced by engineer-tier build dispatches when wiring each gate. Changes to this contract require Aiden + Max + Elliot concur (architecture/governance touches every gate).

## Cross-cutting principles

- **Fail-closed default.** Per Cat 16 HARD GATE posture + Aiden architectural ratification on Go Sidecar (PR #1144 § "fail-closed for SPOF"). If a gate errors, the LLM call is REJECTED. The customer sees a sanitised denial. Operator surfaces it via the audit log
- **Audit emission is mandatory.** Every gate emits a single audit event with a fixed schema. No "silent pass" — even a successful gate writes the pass event
- **Tier-aware enforcement vs warn.** Some gates degrade to warn-mode on Sandbox tier (evaluation safety); paid tiers enforce strictly
- **No timing predictions in emit shape.** Per Keira-rule fleet-wide, gate events report observed elapsed time only after-the-fact, never predictions

## Common audit event schema

Every gate emits an event with this shape:

```
{
  "gate": "temp.inline.<name>",
  "workflow_id": "<temporal_workflow_id>",
  "activity_id": "<temporal_activity_id>",
  "tenant_id": "<uuid>",
  "agent_id": "<callsign or ephemeral spawn id>",
  "agent_type": "chat | worker | deliberator | reasoning_listener",
  "tier": "sandbox | solo | pro | team | enterprise",
  "outcome": "pass | block | warn | error",
  "elapsed_ms": <observed>,
  "reason": "<machine-readable>",
  "detail": "<human-readable, sanitised; no raw secrets, no customer payload>",
  "timestamp": "<ISO-8601 UTC>"
}
```

Events stream to:
1. Temporal workflow event history (for replay + debugging)
2. Layer 12 observability sink (`mem.wrap.trace` composition per PR #1134)
3. Customer-visible audit log if tier >= Pro (Cat 19 ux.surface.audit_log)

---

## Gate 1 — temp.inline.listener (Reasoning Listener)

**Purpose:** Capture the "why" behind decisions. Inline because reasoning must be recorded BEFORE the LLM call returns its rationale (otherwise the rationale gets lost on activity completion).

**Emit guarantee:**
- Always emits one `reasoning_capture` event per LLM call
- Event includes the upstream context shape (which agent triggered, what task_id, what input summary) but NOT the raw input text (PII discipline)
- Captures the LLM's reasoning-tag content (if Anthropic with `<reasoning>` tags enabled) post-call as a follow-up event

**Enforce vs warn:**
- WARN-ONLY: this gate is observational, not enforcement. Failure to capture reasoning does NOT block the LLM call (would create a chicken-egg: agent can't operate if reasoning capture is down)
- If listener errors, audit event records the failure; LLM call proceeds
- Exception: if listener errors >5 times in 60s for a single tenant, escalate to Layer 12 alert (fleet-wide reasoning capture degraded)

**Failure mode:** transient HTTP error to Hindsight → warn + continue. Hindsight unavailable >30s → emit `degraded` event; fleet-supervisor notified; LLM calls still proceed

---

## Gate 2 — temp.inline.token_gate (Token Spend Hard-Stop)

**Purpose:** Per-call cap + tier-scaled pool + dispatcher-enforced + model-cost-calibrated (Viktor's 4-component model in `cost.token_budget`).

**Emit guarantee:**
- Pre-call check event with `pool_remaining`, `call_estimated_cost_aud`, `cap_remaining`
- Post-call event with `actual_cost_aud` reconciled against estimate
- If cap breached, emit `block` event with `cap_kind` (per-call vs per-pool) and `denied_cost_aud`

**Enforce vs warn:**
- ENFORCE on all paid tiers (Solo / Pro / Team / Enterprise)
- WARN-ONLY on Sandbox tier (eval users still see the warning but the call proceeds; gives them visibility into what would happen at paid tier without blocking eval workflow)
- If token-gate itself errors → fail-closed (block the LLM call). Better to drop a call than spend uncontrolled

**Failure mode:** rate-limit-resolution service unavailable → block + escalate. Pool state stale (Redis/Valkey down) → block + alert; per `cost.semantic_cache_valkey` row, Valkey down is V1.x degraded posture but production blocks calls

---

## Gate 3 — temp.inline.cache_check (Cache Strategy Dispatch)

**Purpose:** Decide which cache layer applies per call. Three checks in sequence — Anthropic prompt cache eligibility / Valkey semantic similarity / Hindsight recall for beyond-window content. Routes to the cheapest applicable strategy.

**Emit guarantee:**
- One `cache_decision` event per call with `routes_to` enum: `prompt_cache | valkey_hit | hindsight_recall | uncached`
- For prompt_cache route: `cache_breakpoint_token_index`
- For valkey_hit route: `similarity_score` + `valkey_key`
- For hindsight_recall route: `recall_query_hash` + `result_count`
- For uncached route: `reason_for_uncached`

**Enforce vs warn:**
- WARN-ONLY: cache misses are not failures. Gate emits the decision for cost attribution + observability
- If cache lookup itself errors → fall through to uncached. LLM call proceeds. Warn event emitted

**Failure mode:** Valkey unavailable → fall to uncached + warn (per `cost.semantic_cache_valkey` V1.x degraded posture). Hindsight unavailable → fall to uncached + warn

---

## Gate 4 — temp.inline.tier_gate (Tier Feature Gating)

**Purpose:** Enforce per-tier capacity allocation (4-6-8-14 curve per Cat 17) + per-tier tool whitelisting (MCP per-tier `tools/list`) + per-tier model access (BYOK key resolves to tier-allowed providers).

**Emit guarantee:**
- One `tier_check` event per call with `tier`, `capacity_used`, `capacity_limit`, `tool_in_allowed_set` (bool)
- On block, `reason` enum: `capacity_exceeded | tool_not_in_tier | model_not_in_tier`
- Customer dashboard receives the block via `ux.workflow.upgrade_prompt` pattern (Cat 17 `tier.capacity_behaviour`)

**Enforce vs warn:**
- ENFORCE on all tiers (including Sandbox — eval IS the enforcement)
- Sandbox 10-tasks/day rate-limit is enforced here (decremented per workflow start)
- If tier-gate itself errors → fail-closed (block). Tier metadata is the security boundary

**Failure mode:** tenant control-plane unavailable (Supabase down on `keiracom_tenants`) → block + escalate. Cannot determine tier safely → cannot grant access

---

## Gate 5 — temp.inline.audit (Audit Trail Emission)

**Purpose:** Compose the audit event per `mem.wrap.trace` (OTel + tenant log + Reflect citations) → write to audit trail surface visible to customer per Cat 19 `ux.surface.audit_log`. Compliance-grade emission for regulated verticals.

**Emit guarantee:**
- One `audit_record` event per LLM call. This gate is the AUDIT EVENT — the others emit auxiliary events
- Includes: workflow_id, activity_id, tenant_id, agent_id, agent_type, tier, input_summary_hash (NOT raw), output_summary_hash (NOT raw), gate_outcomes_summary (which gates passed/blocked), tool_calls_count, citations_count
- HIPAA/legal/accounting downstream verticals (V1.x audience) receive the full structured audit per `mem.wrap.trace` Cat 6 row

**Enforce vs warn:**
- ENFORCE: audit emission is mandatory. If audit-write fails, the LLM call is BLOCKED. No compliance vertical can accept un-audited outputs
- Exception: Sandbox tier may warn-only (eval users get the call through with audit-degraded marker; eval is not a compliance surface)

**Failure mode:** audit-trail sink (Hindsight + Layer 12) unavailable → block + escalate. Audit emission is the integrity surface for V1.x regulated verticals — better to drop a call than ship un-audited output

---

## Gate 6 — temp.inline.content_check (Pre-Call Privacy / Regulated Content)

**Purpose:** Block LLM calls that would leak PII / PHI / financial data / regulated content into the prompt. Mechanical pattern check before the call hits the LLM provider. Cross-cuts with Go Sidecar `ScanResponse` (Go Sidecar is the egress equivalent; this is the ingress equivalent for the LLM prompt itself).

**Emit guarantee:**
- One `content_scan` event per call
- On block, `reason` enum: `pii_detected | phi_detected | financial_detected | secret_detected | jailbreak_pattern_detected`
- On pass, `patterns_checked` count for audit completeness

**Enforce vs warn:**
- ENFORCE on Enterprise tier (regulated vertical posture)
- ENFORCE on Team tier if customer enables compliance mode
- WARN-ONLY on Solo / Pro / Sandbox (warn the user; let them proceed; honest framing of what was detected)
- If scanner itself errors → fail-closed on regulated tiers; warn on others

**Failure mode:** pattern catalogue (likely a YAML file in Vault per `infra.secrets_management`) unavailable → fail-closed on regulated tiers; warn on others

---

## Gate 7 (Async) — temp.async.post_validation (Response Shape + Citation Validity)

**Purpose:** Aiden refinement to keep slow checks off the critical path. After the LLM responds, validate response shape (JSON well-formed if expected, schema-conformant if a structured-output workflow) + citation validity (per Hindsight reflect citation-validation pattern surfaced by Atlas in PR #1153 review — "FREE on reflect path").

**Emit guarantee:**
- One `post_validation` event per LLM call
- Includes `shape_valid` (bool), `citations_total` (int), `citations_valid` (int), `citations_invalid_ids` (list, sanitised)
- On invalid citations, customer is notified via dashboard surface (Cat 19 ux.workflow.decision_traces) AFTER the LLM response has already been delivered

**Enforce vs warn:**
- WARN-ONLY by design (async continuation cannot block a response that already returned to the customer)
- Invalid citations are surfaced to the customer as "this output references X memories; Y of those are no longer in the index" — honest framing
- Invalid-shape responses trigger a follow-up activity that regenerates with stricter constraints (`continue-as-new` Temporal pattern)

**Failure mode:** validator unavailable → emit `validation_skipped` event with reason; LLM response already returned to customer; integrity claim is degraded for this call. Operator sees the gap in dashboard

---

## Sequencing rules

1. **Pre-call (in order):** tier_gate → content_check → cache_check → token_gate. If ANY blocks, LLM call rejected; emit `block` audit event; sanitised denial returned to customer
2. **The LLM call itself** (if all 4 pre-call gates pass)
3. **Inline post-call (in order):** listener (capture reasoning if available) → audit (compose full record) → cache_check post-emit (record actual hit/miss)
4. **Async continuation:** post_validation fires as a separate Temporal activity after the customer-facing response has shipped

## Tier-aware enforcement matrix

| Gate | Sandbox | Solo | Pro | Team | Enterprise |
|---|---|---|---|---|---|
| listener | warn | warn | warn | warn | warn |
| token_gate | warn | ENFORCE | ENFORCE | ENFORCE | ENFORCE |
| cache_check | warn | warn | warn | warn | warn |
| tier_gate | ENFORCE | ENFORCE | ENFORCE | ENFORCE | ENFORCE |
| audit | warn-degraded | ENFORCE | ENFORCE | ENFORCE | ENFORCE |
| content_check | warn | warn | warn | optional ENFORCE | ENFORCE |
| post_validation | warn | warn | warn | warn | warn |

## Cross-references

- ceo:keiracom_architecture_v2_locked Cat 5 (10 rows) — all 7 gates referenced
- ceo:cache_framework_canonical — feeds cache_check
- ceo:dave_decisions_2026_05_26 decision_5 — Temporal on separate Vultr (Option C 4GB Sydney)
- PR #1134 mem.wrap.trace — audit composition
- PR #1144 Go Sidecar ScanResponse — content_check egress parallel
- PR #1146 Vault decryptor — secret access at gate execution
- KEI-206 author-exclusion — applies to deliberator workflows but not chat workflows

## What this contract does NOT specify

- Concrete cost-cap numbers per tier (those land per-tier in Phase 2)
- Pattern catalogue specifics (Vault YAML; engineer-tier owns)
- Customer-visible error message copy (Cat 19 UX owns; cross-cite Keira persona for tone)
- Workflow-versioning strategy for gate logic upgrades (Temporal sub-spike — Orion's Phase A6 build dispatch)

## Concur required before build commit

- Aiden architecture/governance lens — does this match the V2.0 spec intent?
- Max quality/coverage lens — are the emit events sufficient for observability + compliance audit?
- Elliot impl-feasibility — this doc IS my impl-feasibility statement
- Orion build dispatch — when this contract concurs, A6 first-workflow-migrated step unblocks

## Phase 2 amendments (folded from Aiden CONCUR observations 2026-05-25)

Non-blocking; track for Phase 2 implementation discipline:

1. **Schema extension for V1.x regulated verticals.** Add to common audit event schema:
   - `session_id` / `chat_thread_id` — multi-call correlation within a customer session (HIPAA episode tracking, legal-privilege grouping)
   - `event_id` + `trace_id` — distributed-trace correlation across audit-sink pipeline (Temporal → mem.wrap.trace → Layer 12)
   - `signature` / `audit_hmac` — tamper-resistance for compliance verticals; HMAC-keyed via Vault Transit (`infra.secrets_management`); pairs with Atlas Go Sidecar NIT-7 HMAC-signed-config
   - Explicit PHI policy on `detail` field: `phi_filtered: bool` flag confirming strip pass ran (HIPAA is broader than "secrets" or "payload")

2. **Sandbox token_gate calibration — abuse vector closure.** Current warn-only on Sandbox is unbounded fleet-cost risk (10K tokens/task × 10 tasks/day × N tenants). Suggested:
   - ENFORCE with generous-cap (e.g., 50K tokens/day total per Sandbox tenant)
   - WARN below 50% of cap (visibility into paid-tier behaviour)
   - ENFORCE at 100%
   Calibration tune in Phase 2 with actual Sandbox usage data; communicate cap honestly in Sandbox onboarding flow

3. **Cache-hit short-circuit in pre-call sequencing.** When `cache_check` returns `valkey_hit` (no LLM call needed), `token_gate` firing afterward is wasteful. Suggested re-ordering:
   - tier_gate (always)
   - content_check (always)
   - cache_check
     - if HIT: SHORT-CIRCUIT (skip token_gate; emit cache-hit-pass; return cached response)
     - if MISS: continue
   - token_gate (only on cache MISS)
   - LLM call
   - Inline post-call: listener → audit
   - Async: post_validation
   Cleaner cost-flow + better audit signal
