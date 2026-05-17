# KEI-122 — Wave 1/2/3 Decomposition Synthesis

**Linear:** [KEI-122](https://linear.app/keiracom/issue/KEI-122)
**Status:** Closing this synthesis = closing KEI-122.
**Authored:** Aiden 2026-05-17 (executing per Dave-direct dispatch).
**Decomp lead:** Elliot. **Ratifications:** Aiden + Max + Elliot (3-of-3 per row, per Dave one-round-concur rule).

## What this doc is

A single canonical closure record for the three-wave architecture decomposition Elliot drove on 2026-05-17. The work itself — filing the 50 sub-KEIs across Wave 1/2/3 into Linear — is **already done**. This doc proves it, captures the ratification trail, and gives engineer-bot claimers a single artifact to read instead of replaying the multi-hour #execution thread.

## Three waves, 50 KEIs filed, 3-of-3 ratified

| Wave | Source | KEIs filed | What it decomposes |
|---|---|---|---|
| **Wave 1a (9)** | Dave's explicit gap list | KEI-123, 124, 125, 126, 127, 128, 129, 130, 131 | Strangler Fig routing, Composio OAuth, systemd watchdog, Docker→Railway, X-Ray, Prometheus SLO, Postgres backup (Max-escalated to P0), README, GTM 1-pager |
| **Wave 1b (4)** | Aiden granularity edits | KEI-132, 133, 134, 135 | Chaos framework split (132/133), persona versioning (Phase-2 bump), OpenAPI on Vercel |
| **Wave 2 (9)** | Pass-2 architecture sweep | KEI-136 thru KEI-144 (137 dropped, 138 folded into KEI-103, 147 dropped post-empirical-check) | Governance hardening + observability + cross-cutting safety nets |
| **Wave 3 (28)** | Part 17 product-layer sub-decomp | KEI-145 thru KEI-172 | Auth (5), Billing (4), Onboarding (4), Dashboard (4), Container lifecycle (5), BYO crypto (3 P0), Rate limit (3) |
| **Post-Wave** | Real-world incident shipping | KEI-173, 174, 175 | drive_manual sink fix, fleet supervisor, fleet supervisor S3776 refactor |

Total Wave 1+2+3 ratified KEIs: **50**. Three drops (KEI-137 Enforcer permadeath, KEI-138 fold into KEI-103, KEI-147 worktree-lifecycle YAGNI confirmed by `git worktree list` empirical). One fold (KEI-138 → KEI-103 SIM_THRESHOLD-drift sub-task).

## Ratification records (verbatim concur chain)

Each wave cleared Dave's "one-round, no token dance" rule with 3-of-3 from {Aiden, Max, Elliot}:

| Wave | Proposer | First concur | Second concur | Filing |
|---|---|---|---|---|
| 1a (9) | Elliot proposal-table | Aiden CONCUR-WITH-EDITS (4 rows tightened) | Max CONCUR + KEI-127 backup-bump P0/0.5 | Elliot filed |
| 1b (4) | Aiden 3 edits (KEI-A/B/C) | Max [CONCUR:max] release token b8c8cba7a1ec | Elliot ratify + file | Elliot filed (4 KEIs because chaos split into A1+A2) |
| 2 (9) | Elliot Pass-2 proposal | Aiden 4 edits + dup-check flag | Max strong-concur + 2 tightenings (KEI-141 critical-5 env / KEI-142 3 critical MCPs) | Elliot filed after dup-check resolved 138→KEI-103 fold + KEI-147 drop |
| 3 (28) | Elliot Part-17 sub-decomp | Aiden 3 P2→P1 bumps + 2 granularity tightenings | Max strong-concur + KEI-116 P0 escalation (DPA-anchored) | Elliot filed 28 children across 7 parents |

The full thread of CONCUR-REQUEST → LOCK → release tokens is in #execution Slack history for the 2026-05-17 window.

## Critical-path observations (engineering-claimer guidance)

These are the load-bearing dep chains a sub-KEI claimer should respect when picking next-unblocked work:

- **KEI-115 Container chain is the longest single track.** 5 children (162→163, 164→165→166). Start KEI-162 (container spawn) as early as Phase-0.5 work permits — it gates first-customer task throughput.
- **KEI-116 BYO crypto chain is P0, not P1.** Max's escalation 2026-05-17: plaintext customer API keys violate AU Privacy Act + GDPR + KEI-118 DPA compliance baseline. The 3 children (167/168/169) must precede any production key handling.
- **KEI-114A (KEI-158) Feed gates the rest of KEI-114.** Cost/Keys/Usage all expect the feed exists for drill-down references. Start 114A first; B/C/D run in parallel once A scaffolds.
- **KEI-141 ENV schema validation has critical-5 scope** (Max's tightening): `DATABASE_URL`, `SUPABASE_DB_URL`, `LINEAR_API_KEY`, `SLACK_BOT_TOKEN`, `LINEAR_WEBHOOK_SECRET` first; full sweep is its own follow-up. Anchored on today's 5h LINEAR_WEBHOOK_SECRET silent-failure incident.
- **KEI-142 MCP resilience has 3-critical scope** (Max's tightening): `supabase`, `linear-server`, `slack`. Full 11-MCP coverage deferred.

## Phase + priority distribution

| Phase | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| 0.5 (governance/infra hardening) | 4 (122 / 124 / 125 / 126) | 3 (140/141/143/144) | 2 (139/142/146) | — |
| 1 (Model B build-out) | 1 (127) | 5 (128/129/130/131/132/133) | 1 (134) | — |
| 2 (docs + launch) | — | 2 (135/136) | 2 (138/138) | — |
| Product Layer (Part 17) | 3 (167/168/169 BYO crypto chain post-Max-escalation) | 17 (Auth+Billing+Onboarding+Dashboard+Container) | 1 (134 persona post-bump) | 3 (170/171/172 rate limit) |

(Counts are approximate per the per-wave ratification deltas above.)

## Wave-1/2/3 status snapshot at synthesis-time

Per session-context tracking ≈ 22:30 UTC 2026-05-17:

- **Shipped + merged to main (this session):** 12+ KEIs from this decomposition reached `main` already — including KEI-103/106/109-children/146/86/91/108/89/97/88/93/150/151/76/85-phaseB/C/140/144 (some pre-decomposition, listed here for completeness).
- **Open PRs awaiting merge (Wave 3 dashboard family):** PRs #957 (KEI-158), #968 (KEI-161), #970 (mine — KEI-160), #971 (KEI-156), #972 (KEI-157), #967 (KEI-159 if not yet merged). All shell-pattern scaffolds with sub-KEI-claimer wiring deferred.
- **In-flight build (this session):** KEI-118 compliance scaffolds shipped (PR #973). KEI-119 keiracom.com landing shipped (PR #965). KEI-174 fleet supervisor merged (PR #963). KEI-175 refactor open (PR #964).
- **Awaiting engineer-bot claim:** the Auth chain (KEI-145..149), Billing chain (KEI-150..153), Container chain (KEI-162..166) — Wave 3 P1 work that hasn't been picked up yet. Sub-KEI claimers should `bd ready` and self-claim per Dave standing order.

## Wave-4 trigger conditions

Per Elliot's standing post: a Wave 4 decomposition pass is needed when:

1. **KEI-118 legal review unblocks a new compliance subsurface** (e.g., DPO appointment, breach-notification SLAs, cross-border data transfer documentation) that wasn't visible at Wave-1 filing time.
2. **Customer onboarding lands** and reveals product-shape gaps the Wave-3 Part-17 decomposition didn't anticipate (e.g., billing-dispute flow, tenant-data-export, support-ticket pipeline).
3. **Model B (the container-dispatcher product layer) hits a real customer task** and surfaces operational gaps (e.g., container-bad-state recovery, cost-overrun circuit-breaker, multi-region failover).
4. **An incident class repeats** (today's webhook-HMAC-missing 5h silent-failure pattern would have justified a Wave-4 entry for ENV-schema-validation if KEI-141 hadn't already covered it).

None of these triggers are active at synthesis-time. Wave 4 is correctly parked.

## Closure

KEI-122 is closed by this doc landing. The 50 filed KEIs are the deliverable. Engineer-bot claimers work the queue per Dave standing order ("if `bd ready` shows it, take it"). Wave 4 fires on the trigger conditions above + Dave-direct dispatch.

— Aiden, 2026-05-17 UTC
