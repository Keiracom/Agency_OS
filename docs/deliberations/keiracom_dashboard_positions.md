# Keiracom Dashboard Spec — Working Positions

Dave directive 2026-05-20. Deliberators: Elliot (synthesis + implementation-feasibility),
Aiden (architecture + competitive — nav/header/integrations), Max (cost + quality —
spend/stat-cards/audit). Output → `ceo:deliberation:keiracom_dashboard_spec`. One session.

Foundation: product brief `ceo:deliberation:keiracom_product_output`. Function + content
only — no colours/aesthetics. Feel like Vercel/Railway infra tooling, not consumer AI.

---

## ELLIOT — implementation-feasibility lens (2026-05-20)

**Anchoring principle: spec only components that real data can drive.** Every card/graph/
table below names its data source. Where a source does not exist yet, it is flagged — the
spec must not promise a tile with nothing behind it.

**Data sources that actually exist (verified this session):**
- `spend_tracker` (Valkey `spend:<tenant>:<month>`) — per-tenant + per-thread spend.
- `container_monitor` / `container_lifecycle` — container status, health, uptime.
- `heartbeat_watchdog` + `heartbeat_reaper` — thread liveness, last-heartbeat, zombie/stuck
  detection, failed-task marking.
- `public.tasks` — task records (id, title [backfilled], status, priority).
- `public.task_verifications` — verification/outcome records.
- `interceptor_events` — per-model-call allow/deny, spend, rate-limit decisions.
- `public.cost_events`, `sync_events`, `governance_events` — cost + audit trails.
- The Valkey thread counter exists but is **decrement-only** — no live "threads active"
  count is reliably maintained today (flagged: needs the claim/increment path).

### (4) Thread activity view — THE primary view (my lead)

The default landing page. A grid of thread cards, one per thread the customer owns
(active + their tier ceiling shown, e.g. "4 / 6 threads").

**Per-thread card components:**
- Thread name/id + state badge.
- Current work — the title of the task the thread is on (from `public.tasks`).
- Uptime / age — since spawn (`container_lifecycle`).
- Live spend on this thread this month ($AUD, `spend_tracker`).
- Last heartbeat / last progress timestamp (`heartbeat_watchdog`) — the trust signal.
- A one-line "latest action" — most recent meaningful step (from the activity log).
- Actions: open detail, restart, terminate, view live log.

**Thread states (driven by container_monitor + watchdog + reaper):**
- `Spawning` — container starting, not yet ready.
- `Active` — healthy, heartbeat fresh, working a task.
- `Idle` — healthy, no task assigned (capacity available).
- `Stuck` — heartbeat stale past threshold; watchdog flagged, not yet reaped.
- `Failed` — reaper marked the task failed / container errored.
- `Terminated` — cleanly stopped.

**Detail drill-down (click a card):** full live log stream, the task history for that
thread, per-thread spend timeline, the verification records it produced.

### (7) Failure + alerts view (my lead)

Failures must be loud — "it tells me when something breaks" is a top-4 trust must-have.

- **Failed/stuck threads surface to the TOP of the thread view** (sort: Failed > Stuck >
  Active > Idle) — a customer never has to hunt for a problem.
- **A dedicated Alerts panel** (header bell + a section): each alert = severity, the
  thread, the failure reason (from `heartbeat_reaper` / `container_monitor` error), the
  last-good-heartbeat timestamp, time-since.
- **Failed thread card vs healthy:** failed card shows the error reason verbatim, the task
  that was in-flight, last-good-heartbeat, and a prominent Restart / Retry-task action.
  Healthy card shows the latest action + fresh heartbeat.
- **Actions on a failure:** restart thread, retry the failed task on a fresh thread, view
  the full log around the failure, dismiss/acknowledge the alert.
- Data: `heartbeat_watchdog` (stuck detection), `heartbeat_reaper` (failed marking),
  `container_monitor` (container errors), `interceptor_events` (denied calls).

### (10) Onboarding flow (my lead)

**Feasibility flag — load-bearing:** the current onboarding pages (signup → verify-email →
byo-key → first-task) are UI-only stubs with no backend (Orion's gap-hunt). The spec must
state the critical path AND that the backend for it is an explicit build item.

**First-login critical path — get them to a running thread fast:**
1. Signup + email verify.
2. **Enter BYO API key** — gated step; without a key no thread can run. Validate the key
   live before proceeding.
3. **Spawn first thread** — one click. The empty dashboard's primary CTA.
4. **Give it a first task** — a guided "what should your AI workforce do first" prompt.
5. Land on the thread activity view with thread #1 visibly Active and working.

**Empty states:** before thread #1, the dashboard is an empty thread grid with a single
"Spawn your first thread" CTA + a 3-step checklist (key entered / thread spawned / first
task given). No fake data, no demo cards — empty but oriented.

### Quick reads on the other 7 (defer leads to Aiden/Max)

- (1) Navigation: agree it should be flat + infra-tool spare. My implementation note —
  every section must map to a real data source; do not add a section the system can't
  populate. Default landing = Thread activity (4).
- (2) Header: persistent — thread count (active / ceiling), month-to-date spend, fleet
  health dot, alert bell. All from data that exists.
- (3) Stat cards: card-worthy = a number a customer checks every visit (active threads,
  MTD spend, tasks completed this period, failure count). Defer the set to Max.
- (5) Spend: defer to Max. Implementation note — `spend_tracker` gives per-tenant +
  per-thread; per-MODEL breakdown needs `interceptor_events` aggregation (exists).
- (6) Audit/outcomes: a completed task = the task record + its `task_verifications` rows
  (what was done + verification evidence). Searchable by thread, status, date.
- (8) Integrations: defer to Aiden. Implementation note — integration health is real
  (each integration has a status); "last used" needs a per-integration last-call
  timestamp, which may need adding.
- (9) Settings: tier, seat management, BYO API key config (rotate/replace), billing.

**Elliot headline:** the dashboard spec is feasible — most components have a live data
source today. The two honest flags: (a) onboarding has no backend yet — it is the
critical-path build; (b) a reliable live "threads active" count needs the thread-pool
claim/increment path built (ties to the thread-enforcement gap Dave just raised).

---

## AIDEN — architecture + competitive lens (received 2026-05-20)

Reference read: Vercel/Railway/Supabase/Render/Planetscale — pattern: one spine object as
landing, flat ~6-item nav, command-K, logs/observability first-class, settings last,
usage always visible. Keiracom spine = the THREAD.
- **(1) Nav:** flat 6 items — Threads (DEFAULT LANDING), Activity, Spend, Integrations,
  Alerts (count badge), Settings (last). Workspace-scoped.
- **(2) Header:** workspace switcher, thread-capacity meter (`4/6 threads` + overage
  indicator), global fleet-health dot (Healthy/Degraded/Failure, deep-links to Alerts),
  command palette (Cmd-K), account menu. Capacity meter + health dot never scroll away.
- **(8) Integrations (lead):** grid of integration cards — name+category, health
  (Connected/Degraded/Down/Not-configured live probe), last-used, capability summary
  ("what the fleet can DO with it"), usage-in-window. API-health strip above. Dedicated
  API-keys sub-panel (BYO model keys + per-integration creds, add/rotate/revoke,
  last-rotated, revoked-not-deleted for audit). "Show capability, not just connection."
- (3) cards: 4 max on landing — Live threads, Spend this cycle, Tasks completed 7d,
  Active alerts. (4) thread cards: id+callsign, state, current task, last-activity, mini
  log tail, cycle spend. (5)(6) defer to Max. (7) 3-place surfacing: header dot + Alerts
  badge + failed card. (9) tier/seats/keys/billing/fair-use-cap/workspace. (10) onboard
  INTO the live dashboard (overlay, not a wizard) — add key, connect integration, launch
  first thread, watch it run.
- **Headline:** Threads = default landing; header capacity-meter + health-dot
  non-negotiable; integrations lead with capability; onboard into the product.

## MAX — cost + quality lens (received 2026-05-20)

- **(3) Stat cards (lead):** card-worthy = single number, trend-able, actionable. Set:
  Active threads (N/M/ceiling), Threads rate-capped (sales signal), Spend this period (+
  delta), Projected spend, Tasks completed 7d, Failures/stuck, Fleet health %. Per-thread
  / per-integration / per-task detail → tables, not cards.
- **(5) Spend (lead, deepest):** TWO cost surfaces NEVER conflated — (i) Keiracom
  subscription (tier+seats+overage, predictable), (ii) model-token spend (variable, on
  the BYO key, metered). Headline shows both separately. Time-series (24h/7d/30d/cycle/
  custom). Breakdown toggle by thread (DEFAULT) / model / day / integration. Per-thread
  spend table. Projected spend + confidence. Budget/alert config wired to rate limiter.
  CSV export. TRUST MECHANICS (non-negotiable): per-thread spend MUST sum to the headline
  (reconciliation); "last updated" timestamp shown (metering lag is real); cents storage,
  cent display, no hiding rounding.
- **(6) Audit (lead):** completed-task record = id, thread, title, start/complete,
  duration, outcome, Faces involved, governance decisions fired, artifacts, token spend.
  List + drill-in timeline + search/filter. DATA INTEGRITY (non-negotiable): append-only
  immutable; each rollup links to source events (verifiable not trust-me); task audit
  spend MUST equal sum of that task's Face spend; every started task reaches a terminal
  state (reaper writes explicit "abandoned/reaped" — no silent vanish); UTC stored, AEST
  displayed.
- (1) nav: flat sidebar — **Overview (DEFAULT LANDING)**, Threads, Spend, Activity,
  Integrations, Settings. Overview = fleet status + spend snapshot + alerts in one glance.
- (2) header: tier indicator, thread-utilisation pill, fleet-health dot, **spend ticker
  always visible** (cost-lens choice), account menu.
- (4) thread card: id, state, current Face activity, last-message ts, messages today,
  spend today, integrations, owner. States: provisioning/idle/active/rate-capped/stuck/
  errored/terminating. (7) failed cards float to top; alert types incl. sustained
  rate-cap = sales signal. (9) overage rate + current overage count visible (bill never a
  surprise); keys pgcrypto-encrypted (#1051); Paddle billing (#981). (10) BYO key = HARD
  GATE; every empty state must TEACH.

---

## CONVERGENCE / DIVERGENCE (for the concur round)

**Strong 3-way convergence:** flat ~6-item nav, infra-tooling feel (Vercel/Railway) not
consumer AI; thread = spine object; thread activity view is the primary view with
per-thread cards (state + current work + spend + last-activity + mini log tail); thread
states (~provisioning/idle/active/rate-capped/stuck/errored/terminated); failures surface
in 3 places (header health dot + alerts + failed cards float to top); spend = two cost
surfaces never conflated, breakdowns thread/model/day, ranges, projected, export;
audit = append-only immutable completed-task records, searchable; integrations =
per-integration health + last-used + capability; onboarding = BYO key HARD GATE, onboard
INTO the live dashboard (overlay not wizard), empty states teach; settings = tier/seats/
keys/billing/annual-toggle/fair-use-cap.

**One real divergence — default landing page:**
- Aiden + Elliot: land on **Threads** (zero-click "I can see it working").
- Max: land on a dedicated **Overview** page (cards + spend snapshot + alerts), Threads
  one click away.
- **RECONCILIATION:** land on Threads; the summary **stat cards form the top band of the
  Threads view** — so the landing delivers BOTH the at-a-glance Overview content (Max's
  cards) AND the thread grid, scroll-free, in one surface. No separate Overview page.
  This is the standard infra-tool pattern (Vercel: the Deployments page carries the
  summary on top). Nav = Threads (default, cards-on-top) / Activity / Spend /
  Integrations / Alerts / Settings.

**Mechanism flags (not divergences — carry into the doc as hard requirements):**
- Max: spend reconciliation (per-thread sums to headline; task audit spend = sum of Face
  spend) — quality non-negotiable.
- Max: two-cost-surface separation (subscription vs token spend never conflated).
- Stat-card set: synthesise a tight landing set (~5) from Aiden's 4 + Max's 7.
