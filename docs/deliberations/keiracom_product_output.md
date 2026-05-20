# Keiracom Productisation — Concurred Deliberation Output

**Deliberators:** Elliot (implementation-feasibility + synthesis), Aiden (architecture +
competitive), Max (cost + quality). **Status:** full 3-way concur — `[CONCUR:max]` +
`[CONCUR:aiden]` on record. Dave directive 2026-05-20. All figures $AUD (USD×1.55).

This is one agreed position. Two items are explicitly left as Dave-decisions (§7).

---

## 1. Product + tiers

**Thread is the right unit of sale — keep it.** A thread maps 1:1 to the real cost object:
one Docker container + tmux session + a Valkey counter slice + Weaviate/Cognee query load.
Billing on threads = billing on the actual cost driver. Thread-provisioning is already
built (the Dispatcher: container_lifecycle, interceptor_proxy, auth_minter, watchdog,
reaper, spend_tracker) and running — thread-as-unit is feasible now, not aspirational.

**Seat/thread decoupling is correct.** Seats = auth/collaboration surface; threads =
compute. Keep them separate.

**No feature gates — keep.** One codebase, zero conditional gating: smaller governance
surface, GOV-12 friendly. Differentiation is purely capacity (threads + seats).

**Tiers (concurred shape):**
- Solo — $79/mo — 2 threads, 1 seat
- Pro — $249/mo — 6 threads, 3 seats
- Team — $649/mo — 20 threads, unlimited seats
- Distributor — $775 base + per-thread (rate — see §7a) — wholesale, white-label, dedicated infra
- Self-Hosted — paid source-available licence (see §3)

**Two tier gaps — adopt both fixes, at ONE consistent overage rate:**
- Gap A (Solo→Pro): a single-seat buyer needing 3–6 threads faces a forced 3× jump.
  Fix: a Solo per-thread add-on so they grow without changing tier.
- Gap B (Team→Distributor): a non-reseller org needing 30–80 threads has no home.
  Fix: Team overage — per-thread billing above the 20-thread included count.
- **Both use the same per-thread overage price (~$37/thread/mo)** — one number for the
  same physical resource; two different rates would read as arbitrary (Aiden Note B).

**Pro must be sold explicitly as the multi-seat tier (Aiden Note A).** With the Solo
add-on, Solo $79 + 4 add-on threads ≈ $227 buys 6 threads / 1 seat, vs Pro $249 for
6 threads / 3 seats. This is coherent ONLY if Pro's value is stated plainly as
collaboration + access control (3 seats) — not left implicit. Otherwise a price-
sensitive single-seat buyer rationally never reaches Pro and Pro becomes a dead rung.

---

## 2. Pricing

**Reasoned per-thread cost floor (Max, cost lens):** a thread's COGS is *pure
infrastructure* — BYO API keys mean the customer's key pays all LLM tokens, so Keiracom
carries zero token volatility. Margins are an infra-efficiency game, not a model-cost
gamble. Vultr build: 4 vCPU/8GB host ≈$74/mo at 8–12 threads/host; shared services
(Cognee+Weaviate ≈$149, Supabase Pro ≈$39, storage/bandwidth ≈$20) ≈$208/mo. Amortised
effective per-thread cost: **pre-scale (≤20 live threads) ~$18–22; modest scale
(50–100) ~$12–15; at scale (200+) ~$8–10.**

**Margins:** Solo $39.50/thread ≈49% GM pre-scale; Pro $41.50/thread ≈53%; Team
$32.45/thread is thinnest pre-scale (≈38–44%). Blended ~50–55% pre-scale → 65–70% at
modest scale. Healthy for an infra-bearing product — BYO-key is what makes it healthy.

**Pricing holds.** Keep Solo $79 / Pro $249 / Team $649. The apparent non-monotonicity
(Pro $41.50/thread > Solo $39.50/thread) is an artifact of dividing total by threads
while ignoring seat value — attribute the premium to seats (§1, Aiden) and it resolves.

**MECHANISM — fair-use Face-spawn rate cap (Max P3 — convergence item, non-negotiable).**
A flat per-thread price is an *unbounded-COGS unit* unless Face-spawn rate per thread is
capped. The reasoned cost floor above is only enforceable if pricing is tied to the
existing per-tenant sliding-window rate limiter (shipped, PRs #962/#966). The final
pricing MUST ship with a published per-thread fair-use Face-spawn cap. Without it the
floor is not a floor.

**P4 — annual pricing (~2 months free).** Cash-flow + retention; a pre-revenue company
needs the cash cycle.

---

## 3. Self-hosted

**Self-hosted should exist — as a PAID source-available licence. Never open-source the
core.** This is the single highest-leverage IP decision in the deliberation.

A self-hoster receives the entire moat in one tarball: the Dispatcher, the NATS
coordination fabric, the governance engine, agent definitions, and the Weaviate/Cognee
memory layer. Open-sourcing that core is existential risk to the Distributor business —
a competitor forks the orchestration + governance + memory core, rebrands, and resells;
the Distributor tier becomes unsellable.

**Recommendation:**
- Source-available commercial licence (BSL-style or a Keiracom EULA): the customer runs
  the code, may NOT offer it as a competing service, may not strip attribution.
- Price as an **annual licence + support**, NOT per-thread — you cannot reliably meter
  someone else's infra. High floor (≥$2,000/mo equivalent) so it never cannibalises
  Team/Distributor.
- **Open-core hedge:** open-source the *periphery* (skill SDK, integration shims, BYO-key
  adapters) to drive ecosystem adoption; keep the Dispatcher + governance engine +
  coordination fabric proprietary.
- Buyer: regulated / air-gapped / data-residency customers who cannot use shared infra —
  not a cheap escape hatch from the SaaS tiers.

**Feasibility flag (Elliot):** self-host packaging + licensing infrastructure does not
exist yet. It is a real build — sequence it after the dashboard, not first-release.

---

## 4. Market

**First dollar — the technical solo founder** already running agent CLIs (Claude Code,
OpenClaw) who feels multi-agent orchestration toil today: manual coordination, lost
context, no shared memory. They self-serve, are not price-sensitive at $79–249, and
convert on Solo the moment they see the fleet view.

**Competitive landscape:**
- *Frameworks* (LangGraph/LangChain Platform, CrewAI, AG2/Autogen, OpenAI Agents SDK) —
  not direct competitors. Libraries you assemble; Keiracom is a running, governed fleet.
- *Managed agent products* (Devin/Cognition, Factory, Lindy, IDE background-agents) —
  mostly single-agent or task-scoped. Keiracom is multi-agent *operations*, persistent.
- *The real competitor is DIY* — "Claude Code + tmux + scripts," literally what this
  repo started as. Keiracom sells the productised version of that.

**The moat is the coordination layer — not the agents.** Governance-as-code, the NATS
fabric, shared Weaviate/Cognee memory, the fleet dashboard. The agents are Claude — which
is exactly why BYO API key is correct: Keiracom sells orchestration, not tokens.

**Risk:** DIY is free and improving (Claude Code keeps adding orchestration). Keiracom
must out-run it on what a solo dev won't build themselves — governance, multi-agent
coordination, durable shared memory. If that gap narrows, Solo churns first.

**Later/larger segments:** agencies & consultancies running client work = the genuine
Distributor ICP (white-label, per-client isolation). Regulated enterprise = the
self-host buyer. Both real; neither is the first dollar.

---

## 5. UX + dashboard

The dashboard IS the admin panel — one surface, correct. Four things a customer must see
to trust the product and renew (all backed by data the system already produces):

1. **Live fleet / thread activity** — what every thread is doing right now. Trust = "I
   can see it working."
2. **Real-time spend — per-thread and total.** spend_tracker.py already meters it; with
   BYO-key, surface the model-token spend the customer's key incurred, broken down by
   thread. "I can see what it cost me" is the #1 renewal driver.
3. **Outcomes / audit trail** — what shipped, what's pending, which governance decisions
   fired. Renewal = "I can point at value."
4. **Failure surfacing** — idle/stuck/errored threads (watchdog + reaper data) shown
   plainly. Trust = "it tells me when something breaks instead of failing silently."

**Critical-path flag (Elliot, implementation lens):** the dashboard is currently mostly
stubs — admin pages render mock data with no API calls; dispatcher dashboard pages are
placeholders. The data exists; the UI does not. **Building the dashboard is the #1 item
gating a sellable product.** See §7b.

---

## 6. Language

- **"Thread"** — acceptable for the technical-founder ICP (reads as concurrency), and fine
  in-product. Do NOT lead the marketing one-liner with it; A/B-test "lane" / "worker" as
  the buyer base broadens.
- **"Face"** — drop entirely as a customer-facing term. It sounds like a UI avatar, not a
  stateless per-message responder. It is an internal architecture detail (an ephemeral
  agent: load last-20 messages + identity from Cognee + context from Weaviate, respond,
  terminate). Customers buy threads; Faces are implementation.
- **One-sentence pitch (concurred):** *"Keiracom runs your AI workforce — a governed fleet
  of agents that coordinate, remember, and ship real work. Buy concurrent threads, bring
  your own model key, and see every action and every dollar in one dashboard."*

---

## 7. Items left for Dave (genuine decisions — not deliberator calls)

**(a) Distributor "dedicated infra" model.** The $775 base + per-thread economics depend
on what "dedicated infra" means. Two options:
- *Licence-only:* the distributor supplies and pays for their own Vultr hosts; the
  per-thread fee (~$15) is a software licence. Highest-margin path for Keiracom.
- *Infra-bearing:* Keiracom provisions per-distributor isolated infra (separate hosts +
  isolated NATS + isolated Weaviate — a real deployment topology). Then the per-thread
  fee must rise to ~$18–20 to clear the pre-scale cost floor.
Dave's call — it determines both the price and the DevOps commitment.

**(b) Readiness gate.** The product *strategy* in §§1–6 is sound and the three
deliberators concur. But "sellable" is gated on build readiness, not strategy: the
dashboard is stubs and customer onboarding (signup → verify → BYO-key → first-task) has
no backend — a customer cannot self-serve today. Two options:
- *Ratify strategy now,* and treat the dashboard build + onboarding backend as the
  declared critical path to first revenue.
- *Hold productisation* until the dashboard + onboarding ship, then ratify.
Dave's call — it sets whether go-to-market work starts in parallel or waits.

---

## Concurrence

`[CONCUR:elliot]` `[CONCUR:aiden]` `[CONCUR:max]` — full 3-way concur on §§1–6 and on
surfacing §7(a)+(b) to Dave as options. No deadlocks.
