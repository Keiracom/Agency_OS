# Keiracom Customer Dashboard — Concurred Specification

**Deliberators:** Elliot (implementation-feasibility + synthesis), Aiden (architecture +
competitive), Max (cost + quality). **Status:** full 3-way concur — `[CONCUR:elliot]`
`[CONCUR:aiden]` `[CONCUR:max]`. Dave directive 2026-05-20, one-session deliberation.

Foundation: the concurred productisation doc (`ceo:deliberation:keiracom_product_output`).
**Function + content only — no colours or aesthetic style.** Design intent: the dashboard
must read as professional infrastructure tooling (Vercel / Railway / Supabase), never a
consumer AI product. The spine object is the **thread**. Every component below names the
data that drives it; where a data source does not exist yet it is flagged.

---

## 1. Navigation structure

Flat top-level nav, 6 items, no nested menus (infra-tool pattern — Vercel/Railway).
Workspace-scoped — a Keiracom account is one fleet.

- **Threads** — default landing page. The fleet view (§4) with the stat-card band (§3)
  on top. Zero-click "I can see it working."
- **Activity** — audit trail + outcomes ledger (§6).
- **Spend** — cost view (§5).
- **Integrations** — connected integrations + API health (§8).
- **Alerts** — failures + notifications (§7). Carries an unresolved-count badge.
- **Settings** — tier, seats, keys, billing (§9). Always last.

Default landing = Threads. Onboarding (§10) overlays this for first-login only. Nav
structure is static (predictable IA is itself a professional-tool signal); the only
data-driven element is the Alerts badge count.

## 2. Header / persistent elements

Always visible, every view, never scrolls away:

- **Workspace switcher** — workspace name + dropdown (multi-workspace / agency accounts).
- **Thread-capacity meter** — `live / included`, e.g. `14 / 20 threads`, with an overage
  indicator when any thread bills as overage. Data: live thread count (Dispatcher
  container_monitor / session_manager) + tier included-count (billing).
- **Global fleet-health dot** — single compact status: Healthy / Degraded / Failure.
  Degraded if any thread idle-stalled; Failure if any thread errored or a core service
  (NATS / Weaviate / Dispatcher) is down. Click → deep-links to Alerts. The expanded
  breakdown lives on the Fleet-health card (§3). Data: watchdog + reaper + integration
  health aggregate.
- **Spend ticker** — current-period model-token spend, always visible (cost is never
  more than a glance away). Data: spend_tracker.
- **Command palette (Cmd/Ctrl-K)** — jump to any thread, view, or action. Data: index of
  threads + nav + actions.
- **Account menu** — seat identity, tier label, billing shortcut, sign-out.

## 3. Stat cards

Five cards, forming the **top band of the Threads landing page** (not a separate Overview
page — the standard infra pattern: Vercel's Deployments page carries its summary on top).
Card-worthy = a single number, trend-able, actionable. Per-thread / per-integration /
per-task detail is table-buried, never a card.

- **Active threads** — `N active / M included` against tier ceiling, with a **rate-capped
  sub-figure** (`14/20 active · 2 rate-capped`). Rate-cap is a capacity fact and a sales
  signal. Data: session_manager / container_monitor + rate limiter.
- **Spend this period** — $AUD model-token spend, current billing period, + delta vs same
  point last period, with **projected end-of-period spend as a sub-element**. Data:
  spend_tracker (trend extrapolation for projection).
- **Tasks completed (7d)** — outcomes velocity; the renewal signal. Data: audit/outcomes.
- **Failures needing attention** — the ACTIONABLE card: count of unresolved alerts +
  one-click jump to Alerts. Answers "what do I need to do." `0` reads as reassuring.
  Data: watchdog + reaper.
- **Fleet health** — the SYSTEMS-STATUS card: threads-up + integrations-up + core-services
  (NATS / Weaviate / Dispatcher) up/down breakdown. Answers "is the platform itself OK."
  The expanded form of the header health dot — distinct from "Failures needing attention"
  (one is "what do I do", the other is "is the platform OK"). Data: container_monitor +
  integration health + core-service probes.

## 4. Thread activity view

The primary view and default landing. Below the stat-card band: a dense list/grid of
per-thread cards (Vercel deployment-row density, not consumer tiles), one per thread the
customer owns.

**Per-thread card:**
- Thread id/label + assigned agent callsign.
- **State badge** — `Provisioning` / `Active` / `Idle` / `Rate-capped` / `Stuck` /
  `Failed` / `Terminated`. Data: container_monitor + watchdog + reaper + rate limiter.
- Current work — one line: the title of the task the thread is on (public.tasks).
- Mini live log tail — last 1–3 lines; the "I can see it working" proof.
- Last-activity / last-heartbeat timestamp (relative). Data: heartbeat_watchdog.
- Cycle spend for this thread ($AUD). Data: spend_tracker.
- Per-card actions: open detail, pause/resume, restart, terminate, reassign task, rename.
- Bulk: select-multiple → pause / terminate.

**Failure ordering:** Failed and Stuck cards sort to the TOP — a customer never hunts for
a problem.

**Thread detail (drill-in):** full streamed live log, that thread's task history,
per-thread spend timeline, and the verification records it produced.

## 5. Spend / cost view

The #1 renewal driver — "I can see what it cost me."

**Two cost surfaces, NEVER conflated on screen (hard requirement):**
- **(i) Keiracom subscription** — tier + seats + thread overage. Predictable.
- **(ii) Model-token spend** — variable, on the customer's BYO API key, metered by
  spend_tracker via interceptor_proxy token counts. Surfaced as a transparency service —
  it is the customer's own key spend, no Keiracom markup.

The headline shows both, side by side, explicitly labelled — the buyer must never
confuse the two.

**Components:**
- Time-series graph — spend over time. Ranges 24h / 7d / 30d / billing-period / custom;
  granularity auto (hourly → daily).
- Breakdown toggle — by thread (DEFAULT — ties spend to the unit of sale) / by model /
  by day / by integration. Stacked bar.
- Per-thread spend table — thread, tokens in/out, $ cost, % of total, trend sparkline,
  sortable. This table backs the "Spend this period" card.
- Model breakdown — Opus / Sonnet / Haiku consumption (BYO-key customers pick models, so
  this shows where to optimise).
- Projected end-of-period spend + confidence; overage forecast.
- Budget / alert config — customer sets a $ threshold (per-thread or total); alert on
  projected breach, wired to the rate limiter.
- CSV export per period (finance teams require it).

**Trust mechanics (hard requirements — cost lens):**
- **Reconciliation** — the sum of per-thread spend MUST equal the headline. A spend view
  that does not reconcile destroys trust faster than any bug.
- **Honesty** — show a "last updated" timestamp (metering lag is real, do not hide it);
  label the source ("metered from your API key usage").
- Store in cents, display to the cent; no rounding that hides cost.

## 6. Audit trail + outcomes

The "I can point at value" surface — the system of record.

**Completed-task record:** task id, thread, title, started / completed timestamps,
duration, outcome (success / failed / partial / abandoned), Faces/agents involved,
governance decisions fired (which gates/rules), linked artifacts (PR links, commits,
files, messages), token spend for that task.

- **List view** — title, thread, outcome badge, completed-at, duration, spend.
- **Drill-in** — full task timeline: every Face spawn, every governance decision, every
  external action, timestamped.
- **Search / filter** — by thread, agent, date range, outcome, integration touched,
  free-text.

**Data integrity (hard requirements — quality lens):**
- **Append-only** — audit records immutable once written; no edit, no delete.
- **Traceability** — each rollup row links to its underlying source events (Face spawns,
  governance log, API calls) so a customer can VERIFY a number, not trust it.
- **Reconciliation** — a task's audit spend MUST equal the sum of that task's Face token
  spend in spend_tracker; the two stores agree or the number is not shippable.
- **Completeness** — every task that STARTED reaches a terminal state; the reaper writes
  an explicit "abandoned / reaped" outcome — no task silently vanishes.
- **Time** — store UTC, display AEST, timezone always explicit.

## 7. Failure + alerts

Failures must be loud — "it tells me when something breaks" is a top-4 trust must-have.

**Three-place surfacing (consistent):** the header fleet-health dot, the Alerts nav badge,
and the failed thread's own card state (failed/stuck cards float to the top of §4).

- **Alert row** — severity, source (thread / integration / core service), what failed,
  when, last-good timestamp, suggested action.
- **Alert types** — thread stuck (watchdog), thread errored (reaper), sustained rate-cap
  (= customer needs more threads — a sales signal), spend projected over budget,
  integration auth failed, core service down.
- **Failed card vs healthy card** — failed differs by state badge + a verbatim error
  summary line + last-healthy timestamp + retry count; healthy is quiet (latest action +
  fresh heartbeat).
- **User actions** — view error / logs, restart thread, retry the task on a fresh thread,
  acknowledge / snooze, mute a recurring class.
- Data: heartbeat_watchdog, heartbeat_reaper, container_monitor, rate limiter,
  spend_tracker, integration health probes.

## 8. Integrations / APIs

The view that makes Keiracom read as infrastructure. A grid of integration cards — one
per connected service (Slack, Linear, Supabase, Railway, Weaviate, Cognee, Resend,
Telnyx, Unipile, Vapi, model providers, etc.).

**Per integration card:**
- Name + category (memory / comms / model / infra / data).
- **Health indicator** — Connected / Degraded / Down / Not-configured (live probe — last
  successful call).
- **Last-used** — relative timestamp of last call. (Implementation flag: a per-integration
  last-call timestamp may need adding.)
- **Capability summary** — one line on what the fleet can DO with it ("send + read email",
  "vector recall", "place calls"). Lead with capability, not just connection state — the
  competitive differentiator.
- Usage-in-window — call count + error rate (7d).
- Which threads use it.
- Card actions: configure, test-connection, view recent calls, disconnect.

Above the grid: an **API-health strip** — aggregate connected / degraded / down counts.

**API keys sub-panel:** BYO model keys + per-integration credentials — add / rotate /
revoke, last-rotated date, granted scope. Rotation is one click; revoked keys show as
revoked, not deleted (audit). Keys encrypted at rest (pgcrypto). This panel is where the
BYO-key model becomes tangible to the buyer.

## 9. Settings / account

- **Tier** — current tier, included threads/seats, overage rate + current overage count
  (the bill is never a surprise), change-tier.
- **Seats** — list, invite, revoke, role per seat.
- **API keys** — links to the §8 keys panel (BYO model keys per provider, encrypted).
- **Billing** — payment method, invoices/receipts, next charge (subscription + projected
  overage shown separately), annual / monthly toggle.
- **Fair-use** — the published per-thread Face-spawn cap, visible so the buyer knows the
  rule.
- **Workspace** — name, danger zone.
- Data: dispatcher_customers, customer_api_keys, Paddle billing.

## 10. Onboarding flow

First login overlays the Threads view with a guided path — onboard INTO the live product
(Vercel/Railway pattern), not a separate wizard sandbox. Goal: one running thread, minimum
steps.

**Critical path to first running thread:**
1. Sign up + verify email.
2. **Add a model API key (BYO-key) — HARD GATE.** Nothing runs without it. Validate the
   key live before proceeding.
3. Connect at least one integration (or skip — the fleet runs with none, at reduced
   utility).
4. Confirm tier.
5. Launch the first thread + give it a first task (a guided "what should your AI workforce
   do first" prompt).
6. Land on the Threads view with thread #1 visibly `Active`, live log tail moving — that
   motion is the activation moment.

- A progress checklist persists in-header until complete.
- **Empty states must teach** — before thread #1 the Threads view explains what a thread
  is and offers a single "Provision your first thread" CTA + the 3-step checklist (key /
  thread / first task). No fake data, no demo cards.

**Implementation flag (load-bearing):** the current onboarding pages (signup →
verify-email → BYO-key → first-task) are UI-only stubs with no backend. The onboarding
backend is an explicit, critical-path build item — without it a customer cannot self-serve.

---

## Cross-cutting implementation notes

- Every component above is driven by a named, existing data source EXCEPT: (a) the
  onboarding backend (stubs only — must be built); (b) a reliable live "threads active"
  count needs the thread-pool claim/increment path (the Valkey thread counter is
  currently decrement-only — ties to the thread-enforcement gap raised separately); (c)
  per-integration "last-used" timestamp may need adding.
- These three are the build gaps between this spec and a shippable dashboard.

## Concurrence

`[CONCUR:elliot]` `[CONCUR:aiden]` `[CONCUR:max]` — full 3-way concur on all 10 sections,
the Threads-default + stat-card-band landing, the 5-card set, and the carried hard
requirements (spend reconciliation, two-cost-surface separation, audit reconciliation).
No deadlocks.
