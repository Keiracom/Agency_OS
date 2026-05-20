# Keiracom Productisation Deliberation — Working Positions

Dave directive 2026-05-20. Deliberators: Elliot (synthesis + implementation-feasibility),
Aiden (architecture + competitive), Max (cost + quality). Brief at Supabase
`ceo:deliberation:keiracom_product_brief`. Final concurred doc → `ceo:deliberation:keiracom_product_output`.

This file collects each deliberator's raw position before synthesis. Working artifact.

---

## MAX — cost + quality lens (received 2026-05-20)

**Per-thread cost floor (reasoned):** thread = 1 Docker container; BYO API keys mean
COGS is PURE INFRASTRUCTURE, zero token volatility. Vultr 4vCPU/8GB ≈$74/mo; 8-12
threads/host → $6.20-9.30/thread compute. Shared services (Cognee+Weaviate ≈$149,
Supabase Pro ≈$39, storage/bw ≈$20) ≈$208/mo. Amortised effective per-thread:
pre-scale (≤20 threads) ~$18-22; modest (50-100) ~$12-15; at-scale (200+) ~$8-10.

**Tier margin check:** Solo $79/2thr ($39.50) ~49% GM pre-scale — holds. Pro $249/6thr
($41.50) ~53% — holds. Team $649/20thr ($32.45) — thinnest, ~38-44% GM pre-scale.
Distributor $15/thread is BELOW the pre-scale floor — only defensible if "dedicated
infra" means distributor runs own hosts and $15 is a licence fee.

**Recommendations:** P1 confirm Distributor = licence-only model (else raise to $18-20).
P2 per-thread price non-monotonic (Pro $41.50 > Solo $39.50) — drop Pro to ~$229 or
market Pro's premium as "3 seats". P3 fair-use Face-spawn rate cap per thread is
NON-NEGOTIABLE (cost lens) — flat per-thread price has unbounded COGS without it;
tie to the rate-limiter (PRs #962/#966). P4 add annual pricing (~2 months free).
Blended GM ~50-55% pre-scale → 65-70% modest scale.

**Tiers:** thread = right unit ONLY if paired with the Face-spawn cap. 2/6/20 spacing
fine. Gap between Solo $79 and Pro $249 — add per-thread add-on ($35-40/thr/mo) so
Solo customers grow without a forced 3x jump.

**Self-hosted:** should exist (shifts 100% COGS to customer). PAID LICENCE not
open-source (dispatcher is the product; open-sourcing hands a competitor a reskin).
Licence mandates max-version-lag clause + bundled update channel. Price high floor
(≥$2,000/mo) so it never cannibalises Team/Distributor. For security/compliance buyers.

**Market:** first payers = technical founders on OpenClaw. Highest-margin early =
distributors/agencies IF $15/thread is licence-only. Missed segment: small dev teams
wanting 3-6 threads but balking at $249 — the Solo add-on captures them.

**UX/dashboard — 4 must-haves:** (a) live thread utilisation vs ceiling; (b) per-thread
/per-Face spend (wire spend_tracker.py — "I can see what it cost me" = #1 renewal
driver); (c) Face activity log; (d) health (container health, last error, uptime).

**Language:** "thread" acceptable for technical target, ambiguous for non-technical —
fallback "lane"/"worker". "Face" NOT clear — sounds like a UI avatar; keep out of
customer-facing pricing copy. One-sentence pitch: "Keiracom runs your AI workforce —
buy concurrent threads, bring your own model key, and see every action and every
dollar in one dashboard."

**Max's divergence flags:** P1 (Distributor infra model) — genuine Dave-intent
question. P3 (rate-cap tied to pricing) — Max holds non-negotiable from cost lens.

---

## AIDEN — architecture + competitive lens (received 2026-05-20)

**Tiers:** thread-as-unit architecturally correct (maps 1:1 to the cost object —
container + tmux + Valkey slice + Weaviate/Cognee load). Seat/thread decoupling right.
"No feature gates" is architecturally strong (one codebase, GOV-12 friendly) but removes
the upsell lever — differentiation is purely capacity. **Tier gap: between Team ($649/20)
and Distributor ($775, a reseller product) there's no home for a non-reseller org
needing 30-80 threads** — add Team overage ($/thread above 20) or an Enterprise tier.
Distributor = a real operational fork (dedicated infra = per-distributor hosts + isolated
NATS + isolated Weaviate, a separate deployment topology).

**Self-hosted (Aiden lead):** a self-hoster receives the ENTIRE moat in one tarball —
Dispatcher, NATS fabric, governance engine, agent defs, Weaviate/Cognee memory. Repo has
NO LICENSE file today. Open-sourcing the core is **existential risk to the Distributor
business** (competitor forks + reskins + resells). Recommendation: self-hosted SHOULD
exist as a **PAID source-available licence** (BSL-style or Keiracom EULA — run it, can't
resell it as a competing service). Price as annual licence + support, NOT per-thread
(can't meter someone else's infra). **Open-core hedge:** open-source the periphery (skill
SDK, integration shims, BYO-key adapters) for ecosystem, keep Dispatcher + governance +
coordination fabric proprietary. "Single highest-leverage IP decision in the deliberation."

**Market (Aiden lead):** first dollar = technical solo founder already on agent CLIs
(Claude Code/OpenClaw) feeling orchestration toil — converts on Solo $79. Competitors:
frameworks (LangGraph/CrewAI/Autogen — different category, libraries not running fleets);
managed agent products (Devin/Factory/Lindy — mostly single-agent); **the real competitor
is DIY "Claude Code + tmux + scripts."** The moat is the coordination layer (governance-
as-code, NATS fabric, shared memory, fleet dashboard) — NOT the agents (agents are Claude,
which is why BYO-key is correct). Risk: DIY is free and improving. Missed segments:
agencies running client work (= Distributor ICP), regulated enterprise (= self-host buyer).

**UX/dashboard:** (1) live fleet activity — "I can see it working"; (2) real-time
per-thread + total spend (spend_tracker.py meters it); (3) outcomes/audit trail — "I can
point at value" = renewal; (4) failure surfacing (watchdog/reaper data). dashboard = admin
panel is correct.

**Language:** "thread" ok for technical ICP, not the marketing lead-line; A/B "lane"/
"worker". "Face" — do NOT expose to customers, it's an internal detail. Pitch: "Keiracom
runs a governed fleet of AI agents that coordinate, remember, and ship real work — so you
operate a team, not a pile of scripts."

---

## ELLIOT — implementation-feasibility lens (2026-05-20)

**What actually exists vs speculation — the load-bearing reality check:**

- **Thread provisioning IS built.** The Dispatcher (container_lifecycle, interceptor_proxy,
  auth_minter, watchdog, reaper, spend_tracker) is substantially complete and the service
  runs. Thread-as-unit is feasible *now* — concur with Aiden + Max.
- **The rate-limiter Max's P3 depends on IS built** (per-tenant sliding-window, PRs
  #962/#966 merged this session). So tying price to a Face-spawn cap is implementable
  today — P3 is not aspirational.
- **spend_tracker exists** — the per-thread spend dashboard tile is wireable now.
- **THE BIG GAP — the dashboard is mostly stubs.** Orion's gap-hunt found the admin pages
  (revenue, system, queues) render mock data with zero API calls, and the dispatcher
  dashboard pages (feed, costs, usage) are placeholder stubs. "Dashboard is the admin
  panel" cannot be *sold* until the dashboard is actually built — the data exists, the UI
  does not. **This is the #1 build item gating a sellable product.**
- **Cognee reliability is a flag.** The Face mechanism loads identity from Cognee; Cognee
  has a known silent-drop bug (bd Agency_OS-cjeo — personas unsearchable after accepted
  ingest). Faces depending on Cognee recall need that fixed before "it remembers" is a
  truthful pitch claim.
- **Wired-but-no-engine findings** (client_intelligence scrapers stubbed; onboarding flow
  has no backend) — these are the dormant Agency-OS-outbound product, NOT the platform
  being priced here. Keep them out of scope; but the *customer onboarding* flow (signup →
  verify → byo-key → first-task) being UI-only IS in scope — a customer literally cannot
  sign up and onboard today. Build gap.

**Position on the 6 areas:**
1. Thread-as-unit — concur. Counts fine. Reconcile the two tier-gap flags: Max's
   Solo↔Pro gap and Aiden's Team↔Distributor gap are *both real and not contradictory* —
   adopt both fixes (Solo per-thread add-on + Team overage-above-20).
2. Pricing — defer to Max's reasoned floor. Feasibility: P3 rate-cap is buildable now.
3. Self-hosted — concur fully with Aiden + Max: paid, source-available, never open-source
   the core. Feasibility: self-host packaging/licensing infra does NOT exist yet — it's a
   real build, not first-release. Sequence it after the dashboard.
4. Market — concur: technical solo founder first. Feasibility caveat: there's a readiness
   gap between "the fleet works for us" and "a customer can self-serve" — onboarding +
   dashboard must ship before *any* tier is sellable.
5. UX/dashboard — concur with the 4 must-haves (Aiden + Max converge). Flag: this is the
   largest build, currently stubs. It is the critical path to revenue.
6. Language — concur: drop "Face" customer-facing, keep "thread" for the technical ICP.

**Elliot headline for synthesis:** the product *strategy* (tiers, pricing shape, market,
self-hosted-as-paid-licence, language) is sound and the three of us substantially concur.
The gating issue is *readiness*, not strategy: the dashboard is stubs and customer
onboarding has no backend. Recommend the concurred doc state plainly — strategy ratified,
but "sellable" is gated on a dashboard build + onboarding backend, and give Dave that as
the honest critical path.

---

## CONVERGENCE / DIVERGENCE (for synthesis + concur round)

**Strong 3-way convergence:** thread-as-unit; seat/thread decoupling; BYO-key correct
(sell orchestration not tokens); self-hosted = paid + source-available, never open-source
the core; first dollar = technical solo founder; drop "Face" customer-facing; dashboard
4 must-haves; dashboard = admin panel.

**Reconcilable divergences:**
- Tier gaps — Max flags Solo↔Pro, Aiden flags Team↔Distributor. Not contradictory:
  synthesis adopts BOTH (Solo per-thread add-on $35-40 + Team overage above 20 threads).
- Pricing monotonicity — Max wants Pro repriced (~$229) or "3 seats" marketed as the
  premium; Aiden called spacing "defensible". Minor — synthesis: keep $249, market the
  seat premium explicitly (Max's own alternative). 

**Genuine Dave-decision items (surface with options, do not resolve):**
- Distributor "dedicated infra" definition — is $15/thread a software licence (distributor
  runs own hosts) or infra-bearing (then raise to $18-20)? Both Max + Aiden flag it.
- Elliot adds: the readiness gate — does Dave want to ratify strategy now and treat
  dashboard+onboarding as the build critical path, or hold productisation until those ship?

