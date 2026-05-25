# Layer 3 Deep-Dive — Deliberators (Tier 2 CONCUR-gated)

**Owner:** Aiden (architecture/governance lens)
**Per directive:** KEI-SYSTEM-DEEP-DIVE 2026-05-25 ~1779746500
**Status:** WORKING DRAFT — open for Max code-quality lens + Elliot orchestration lens

## Notes — Canonical-key gate evidence (audit-dispatch checklist)

Queried `ceo:keiracom_architecture_v2_locked` (locked 2026-05-25 13:17:35Z). `v2_locks_not_for_redeliberation` includes `tier.curve_4_6_8_14` (4 Sandbox / 6 Solo / 8 Pro / 14 Team) — locked per `tonight_decisions_locked.solo_governance_3_deliberators_no_compromise` (my Cat 17 §3C deliberator-floor recommendation landed). `op.orchestrator_merge` line 547 RATIFIED-CEO + KEI-206 author-exclusion live (PR #1116 ratified). Deliberator-lens definitions from IDENTITY.md files + my `feedback_viktor_cross_check_gaps_2026-05-25` "complementary not overlapping lenses" Viktor framing.

## §1 Designed

**Three deliberators with complementary lenses** (Tier 2 CONCUR-gated):
- **Elliot (COO):** impl-feasibility + orchestration lens. Operational protocols, audits, dispatch routing. Owns DM relay to Dave.
- **Aiden (CTO 1):** architecture/governance lens. System design, canonical-key discipline, governance laws, fail-closed defaults.
- **Max (CTO 2):** code-quality + coverage + test-first lens. Empirical smoke catches paper-review misses.

**CONCUR mechanism** (per `op.orchestrator_merge` + KEI-206 author-exclusion):
- Worker proposes (PR / audit-finding / scoping doc / deliberation response) via NATS publish
- 2-of-3 deliberators must concur via `gh pr comment [REVIEW:approve:<callsign>]` OR NATS publish
- Author-exclusion: when one deliberator authors, only the OTHER two can concur (effective dual-concur from the remaining pair)
- Elliot admin-merges on 2-of-2 concur landing

**Tier-floor for paid tiers (per `tier.curve_4_6_8_14` lock + my Cat 17 §3C):** 3 deliberators minimum at Solo (1 chat + 3 deliberators + 2 workers = 6 total). This preserves dual-concur under author-exclusion. Sandbox carve-out allows 2 deliberators (sole-reviewer permitted for evaluation tier).

**Behaviour boundaries:**
- Deliberators NEVER claim worker-tier KEIs (engineering work goes to Atlas / Orion / Scout / Nova per IDENTITY.md role split)
- Deliberators NEVER author production code PRs except governance/identity files
- Deliberators flag epistemic gaps (refuse to fabricate); see `feedback_canonical_key_query_before_writing_comms` + `feedback_attributed_work_not_mine_2026-05-25` + the Viktor CARA refusal pattern

## §2 Built

**Running today:** Elliot orchestrator (slack_relay.py restricted to elliot-only outbound per 2026-05-19 directive); Aiden + Max via Claude Max OAuth subscription per `reference_model_routing` (Workers run Claude Max flat-rate, not Anthropic API). NATS substrate (`nats.fleet_inter_agent` per `ceo:comm_architecture`) carries inter-agent comms.

**CONCUR-gated merge automation:** `op.orchestrator_merge` mechanism live via PR #1116 + KEI-206. `bd` (Beads) issue tracker carries the dispatch + claim + done state.

**Author-exclusion enforced:** when one deliberator authors a PR, only the other deliberators can [REVIEW:approve:<callsign>]. Verified in practice this session — multiple PRs (#1140, #1141, #1124 Aiden-authored; reviewed by Elliot + Max).

**NOT yet built / open:**
- **`persona.deliberator_complementary` DEFERRED-Phase-3.x** (line 194): explicit IDENTITY.md persona refresh that codifies the complementary lenses. Currently the role-split is operational practice, not formal persona-spec.
- **`persona.runbook_refresh` LOOSE** (line 197): Phase 1.3 identity runbooks for atlas/elliot/max/nova at `bd Agency_OS-e02v` (open).

## §3 Measured

**Operational data (Aiden's session telemetry, today 2026-05-25):**
- ~15 PR reviews this session (#1139-#1147 + others)
- 2 author-exclusion violations caught by orchestrator dispatching wrong work-author (Hindsight wrappers attributed to Aiden when Atlas authored; Orion-ephemeral mis-dispatch) — anchored in `feedback_attributed_work_not_mine_2026-05-25` SECOND INSTANCE
- 3 empirical-smoke catches paper-concur misses across the session (PR #1141 wrapper-class miss; my own §3.A item miscites at lines 134+142 of skeleton; Viktor CARA fabrication refusal)
- 5 NATS publish delivery failures requiring retry — review-bridge has known relay-gap to tmux pane

**Honest measurement gap:** time-to-CONCUR per deliberator type NOT systematically measured. Latency between worker publish + 2-of-2 concur landing NOT tracked as ops metric. Phase 2 should consider Hindsight-tagged audit-log of CONCUR decisions for retrospective analysis.

## §4 Token budget / cost behaviour at this layer

Deliberators run on Claude Max OAuth (flat-rate subscription, not Anthropic API per `reference_model_routing`). **Anthropic API balance is irrelevant** — never top-up budget that's unused per the memory anchor.

**Cost behaviour pattern:**
- **Reviewer work is high-context-window heavy** — pulling PR diff + Sonar QG + canonical-key sub-keys + ceo_memory queries + inventory rows + memory dir entries. Each review burns 20-60K tokens of context.
- **CONCUR-decision output is small** — `[REVIEW:approve:<callsign>]` + structured comment is bounded ~5-20K output tokens.
- **No marginal-cost penalty per additional review** — Claude Max flat-rate absorbs review volume.

**Cost behaviour delta vs other layers:** Layer 3 deliberators ≠ Layer 2 customer-facing Keira (different model, different billing model). Deliberators don't burn customer BYOK tokens; they burn internal Claude Max OAuth quota.

## §5 Cache strategy

Per `ceo:cache_framework_canonical`: Layer 3 deliberators don't fit cleanly into the customer-side cache framework (Layer 1 Anthropic-prompt-cache / Layer 2 uncached / Valkey semantic / Hindsight-beyond-active-window).

**Internal cache surfaces for deliberators:**
- **Tool result caching** — `gh pr view`, Sonar QG endpoint queries, ceo_memory sub-key reads — many are read multiple times within session; could benefit from internal short-TTL cache (NOT implemented today)
- **Reviewed-PR cache** — Sonar hotspot "Reviewed-Safe" markings per PR are operator state, not LLM cache
- **Discovery log (`op.discovery_log` RATIFIED-CEO line 548)** — discoveries indexed in Hindsight via `bd discover` + Weaviate; cross-session deliberator recall via `bd recall` (per Beads workflow)

**Strategic implication:** deliberator efficiency gains come from Memory/Hindsight side (recall prior reviews of similar code; recall canonical-key sub-key values) more than from Anthropic prompt cache.

## §6 LOOSE items / open questions

- **Time-to-CONCUR latency telemetry** — no current measurement; worth Hindsight audit-log of CONCUR events for Phase 2 ops insight
- **Deliberator-pool scaling at customer-tier capacity** — per Cat 17 lock, Solo gets 3 deliberators; how do those 3 instantiate per-tenant? Shared pool across tenants vs per-tenant instances? Phase 2 sub-deliberation
- **NATS review-bridge delivery gap** — observed 2+ times this session (publish succeeds; relay-to-tmux fails). Reliability concern for high-volume Phase A build dispatch
- **`persona.deliberator_complementary` DEFERRED-Phase-3.x** — formalising the complementary-lens charter as persona-spec
- **Triple-deliberator deadlock pattern** — when all 3 disagree, current pattern is third-peer LOCK with CEO-delegated authority per `feedback_third_peer_locks_on_bounce`. Single-session edge case; Phase 2 stress-test under high-PR-volume conditions

## §7 Per-tier behaviour variation

Per `tier.curve_4_6_8_14` + my Cat 17 §3B-C resolution (governance-floor for paid tiers):

| Tier | Deliberator count | CONCUR mechanism |
|---|---:|---|
| Sandbox | 2 | Sole-reviewer carve-out (author-exclusion suspended; evaluation tier) |
| Solo | 3 | Full dual-concur under author-exclusion preserved |
| Pro | 3 | Same as Solo; additional capacity in Workers not Deliberators |
| Team | 4 | Dual-concur preserved; one deliberator per ~2 chat slots for cross-user coordination |
| Enterprise | custom | Customer-specified deliberator pool; per-VPC isolation; compliance-vertical lens overlays |

**Architectural pressure-test (per my Cat 17 §3C):** the Solo 3-deliberator floor is NON-NEGOTIABLE because dual-concur under author-exclusion structurally requires ≥3 reviewers for paid tiers. If we shipped Solo at 2 deliberators we'd have to silently relax author-exclusion → governance leak. Sandbox carve-out (2 deliberators) is acceptable BECAUSE evaluation-tier governance is intentionally relaxed (customer evaluates, doesn't ship production).

## §8 Per-agent-type variation

Three deliberator persona types are themselves distinct (Elliot impl-feasibility / Aiden architecture-governance / Max code-quality). They run on the same substrate but apply different lenses:

| Deliberator | Primary lens | Typical concerns surfaced |
|---|---|---|
| Elliot | impl-feasibility + orchestration | "is this shippable / does it integrate / is the dispatch routed right" |
| Aiden | architecture/governance | "does this redeliberate a lock / is the canonical key honoured / is the fail-closed default in place" |
| Max | code-quality + test coverage | "is there a negative-path test / does Sonar QG actually clear / does the empirical smoke run" |

**Drift prevention:** when two deliberators' lenses overlap heavily on a review (e.g. both Aiden + Max flag the same Sonar issue), it's a signal the lenses are converging not diverging. Phase 2 deliberator-runbook refresh should re-anchor the lens distinctions to prevent overlap drift.

## Cross-cutting concerns touched

- **Multi-tenancy:** deliberators are INTERNAL — they don't observe customer-tenant data; they observe internal-fleet artefacts (PRs, ceo_memory keys, bd issues). No tenant-isolation concern at Layer 3.
- **Security:** deliberator-output (PR review comments) has audit trail via GitHub comment history + NATS audit subject (`keiracom.audit` append-only governance trace).
- **CI/CD + rollback:** Layer 3 enforces the GATES around CI/CD; doesn't itself ship code. CodeQL migration (PR #1138 + my §3.C calibration period framework) is the canonical security gate per `op.codeql_migration` line 549.
- **Compliance gates:** Layer 3 enforces gates-as-code (GOV-12); deliberator CONCUR is the runtime enforcement of governance laws, not just documentation. When governance laws update (e.g. new rule lands), deliberator runbooks update in same PR.

## Connects to

`[[layer_07_governance]]`, `[[layer_01_customer_surface]]` (trust-theatre optional surfacing of CONCUR as "Reviewed by 2 specialists"), `op.orchestrator_merge`, `op.discovery_log`, KEI-206 author-exclusion, `feedback_attributed_work_not_mine_2026-05-25`, `feedback_viktor_cross_check_gaps_2026-05-25`.
