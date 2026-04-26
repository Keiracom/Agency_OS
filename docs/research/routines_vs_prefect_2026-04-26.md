# P8 — Anthropic Routines vs Prefect Comparison

**Date:** 2026-04-26
**Author:** SCOUT (research clone)
**Branch:** `scout/p8-routines-comparison`
**Mission:** Decide whether to migrate scheduled flows from Prefect to Anthropic Routines (research preview, 2026-04-14), keep Prefect, or run both for different use cases.
**Verdict (TL;DR):** **KEEP Prefect for the entire operational graph. Reject migration.** Optionally run Routines on the side for non-load-bearing dev-bot automation (e.g., weekly PR digests) — but no production flow should move. Three structural blockers — 1-hour minimum schedule interval, per-claude.ai-account ownership model, and tier-capped daily run quotas — make Routines unfit for our 26-deployment surface.

---

## 1. Routines Capability Catalog

### 1.1 Launch and status

- **Release:** 2026-04-14, **research preview** (not GA). Behaviour, limits, and API surface explicitly subject to change ([Anthropic docs](https://code.claude.com/docs/en/routines); [DevOps.com](https://devops.com/claude-code-routines-anthropics-answer-to-unattended-dev-automation/)).
- **Runtime:** Anthropic-managed cloud only. No self-host, no on-prem, no local execution. "Routines execute on Anthropic-managed cloud infrastructure, so they keep working when your laptop is closed" ([Anthropic docs](https://code.claude.com/docs/en/routines)).
- **API beta header:** `anthropic-beta: experimental-cc-routine-2026-04-01` for the `/fire` endpoint.

### 1.2 Trigger types

| Trigger | Mechanism | Constraints |
|---|---|---|
| **Schedule** | Hourly / daily / weekdays / weekly presets, custom cron via `/schedule update` CLI | **Minimum interval: 1 hour.** Sub-hourly cron rejected. Stagger offset added (consistent per routine). |
| **API** | Per-routine bearer token, POST to `https://api.anthropic.com/v1/claude_code/routines/<id>/fire` | Token shown once, not retrievable; rotate via web UI. Body accepts optional `text` field as freeform context. |
| **GitHub event** | Pull request + Release only | No `push`, `issues`, `workflow_run`, `schedule`, or other events. Per-routine and per-account hourly webhook caps; events beyond the cap are **dropped, no replay**. |

A single routine can combine trigger types.

### 1.3 Repository and environment model

- **Repos cloned fresh per run** from the default branch. Claude pushes to `claude/`-prefixed branches by default. "Allow unrestricted branch pushes" toggleable per repo.
- **Cloud environment** defines: network access policy, environment variables (secrets), setup script (cached so it doesn't re-run every session) ([Claude Code on the web docs](https://code.claude.com/docs/en/claude-code-on-the-web#the-cloud-environment)).
- No persistent volume, no mounted disk, no local-file access.

### 1.4 Pricing and quotas

| Plan | $USD/month | Routines | Daily runs | AUD ≈ |
|---|---|---|---|---|
| Pro | $20 | 5 | 5 | $31 |
| Max | $100 | 15 | 15 | $155 |
| Team Premium | $100/seat (min 5 seats = $500) | 25 | 25 | $775 |
| Enterprise | bespoke | 25 | 25 | n/a |

Sources: [byteiota](https://byteiota.com/claude-code-routines-anthropic-kills-cron-jobs-adds-lock-in/), [Junia.ai](https://www.junia.ai/blog/claude-code-routines), [Anthropic docs](https://code.claude.com/docs/en/routines).

- **One-off runs do not count** toward the daily cap; they consume regular subscription usage.
- **Metered overage** available with "extra usage" enabled (Settings → Billing); without it, runs over the cap are rejected.
- Token usage during a run draws down the same subscription budget as interactive Claude Code sessions.

### 1.5 Identity, ownership, observability

- **Routines belong to an individual claude.ai account, not an org.** "They are not shared with teammates." Commits and connector actions appear as the owning user.
- Each run creates a Claude Code session viewable at `claude.ai/code/...`. Logs/traces are session-style, not structured ops dashboards.
- No documented retry semantics, no documented catch-up policy, no audit log API surface.

---

## 2. Prefect Current State (Agency OS)

`prefect.yaml` defines **26 deployments** on `agency-os-pool / agency-os-queue` (Prefect 3.0.0, Australia/Sydney timezone). Worker runs in `Dockerfile.worker` on Railway. Concurrency 10.

### 2.1 Active scheduled flows

| Flow | Schedule | Status | Notes |
|---|---|---|---|
| `health-check-flow` | `*/5 * * * *` Sydney | **active** | 5-minute health probe — detection always ON |
| `free-enrichment-flow` | `15 * * * *` UTC | **active** | Hourly BU stage-0/1 trigger fix; AUD 0 free-mode |

### 2.2 Paused scheduled flows (cron exists, schedule inactive — webhook-first policy)

| Flow | Schedule | Unpause criteria |
|---|---|---|
| `enrichment-flow` | `0 2 * * *` (daily 2am) | Dedicated test window |
| `outreach-flow` | `0 8-18 * * 1-5` (hourly business hours) | Campaign approval framework |
| `voice-outreach-flow` | `*/30 9-20 * * 1-6` | Vapi/Telnyx live + TCP Code verified |
| `reply-recovery-flow` | every 21600s (6h) | Reply tracking table populated |
| `pool-daily-allocation-flow` | `0 6 * * *` | Quota loop tested at scale |
| `credit-reset-flow` | `0 * * * *` (hourly) | Critical billing — paused=false but schedule inactive |
| `pattern-learning-flow` | `0 3 * * 0` (weekly Sunday) | CIS learning model ready |
| `warmup-monitor-flow` | `0 6 * * *` | WarmForge funded |
| `bu-closed-loop-flow` | `0 4 * * *` UTC | S3 ratification + AUD 0 budget verified |

### 2.3 Active webhook-triggered flows (no schedule, fired by app/API)

`campaign-flow`, `onboarding-flow`, `icp-reextract-flow`, `pool-population-flow`, `pool-assignment-flow`, `intelligence-flow`, `trigger-lead-research`, `client-pattern-learning-flow`, `pattern-backfill-flow`, `client-backfill-flow`, `monthly-replenishment-flow`, `campaign-evolution-flow`, `batch-campaign-evolution-flow`, `pipeline-f-master-flow` — **14 flows.**

### 2.4 Out-of-Prefect periodic jobs

`callback-poller` skill (Prefect callback table sweep, 60s interval) runs externally to `prefect.yaml`. Listed in dispatch as part of the comparison surface.

### 2.5 Prefect features Agency OS depends on

- Concurrency limit per pool (`agency-os-pool` cap 10) and per deployment (`voice-outreach-flow` cap 1).
- Cron schedules with timezone awareness (Australia/Sydney + UTC mix).
- Pause toggles at deployment level (governance gate per `prefect.yaml` policy block).
- Retries on task failure (Prefect default + custom retry decorators).
- Direct Supabase/Redis/HTTP access from worker container (no MCP indirection at runtime).
- Structured run history, parameters, tags, audit timeline in Prefect UI.

---

## 3. Per-Flow Parity Matrix

Legend: ✅ fits Routines, 🟡 partial / awkward, ❌ blocked.

| Flow | Cadence | Routines fit? | Blocker |
|---|---|---|---|
| `health-check-flow` | every 5 min | ❌ | Routines minimum interval is **1 hour** |
| `credit-reset-flow` | hourly | 🟡 | At minimum interval; loses headroom; consumes 24 daily-cap slots/day on Max plan alone |
| `free-enrichment-flow` | hourly | 🟡 | Same — 24 runs/day burns the full Max daily cap |
| `reply-recovery-flow` | every 6h | ✅ | Within minimum interval; 4 runs/day |
| `enrichment-flow` (daily 2am) | daily | ✅ | Fits — 1 run/day |
| `pool-daily-allocation-flow` | daily 6am | ✅ | Fits |
| `warmup-monitor-flow` | daily 6am | ✅ | Fits |
| `bu-closed-loop-flow` | daily 4am UTC | ✅ | Fits |
| `pattern-learning-flow` | weekly Sun 3am | ✅ | Fits |
| `outreach-flow` | hourly Mon-Fri 8-18 | 🟡 | 11 runs/day × 5 days = 55/wk — exceeds Max daily cap (15) on weekdays |
| `voice-outreach-flow` | every 30 min Mon-Sat 9-20 | ❌ | Sub-hourly schedule |
| `callback-poller` | every 60s | ❌ | Sub-hourly schedule |
| `pipeline-f-master-flow` | manual / on-demand | 🟡 | Could be API trigger; consumes a routine slot |
| 14 webhook-triggered flows | event-driven | 🟡 | Each needs its own API trigger routine; 14 × routine slots |

**Headcount math.** Mapping every operational deployment to Routines requires ~22 routine slots (excluding the 4 ❌-blocked sub-hourly flows). Pro (5) and Max (15) tiers are insufficient. **Team Premium ($775 AUD/month minimum)** is the smallest tier that fits the count, but its **25-runs-per-day account-wide cap** is consumed entirely by `credit-reset-flow` + `free-enrichment-flow` alone (48 hourly runs/day combined). With "extra usage" enabled, every additional run is metered — costs unbounded.

**The 1-hour minimum interval and the daily run cap are independently fatal.** Either kills the migration on its own.

---

## 4. Migration Cost vs Benefit

### 4.1 Engineering effort to migrate (worst case, full migration)

| Workstream | Estimate |
|---|---|
| Re-platform sub-hourly flows (health-check, callback-poller, voice-outreach) onto a separate scheduler — ironically reintroducing the orchestration layer we just removed | 5 days |
| Convert 14 webhook flows to API-trigger routines (per-routine token rotation, secret distribution to callers) | 5 days |
| Re-implement Prefect concurrency limits (pool=10, voice=1) in app layer — Routines has no concurrency primitive documented | 3 days |
| Replace Prefect retries with prompt-level retry logic | 3 days |
| Move Supabase/Redis credentials from Railway env to per-environment secrets in Routines + audit blast radius (per-claude.ai-account ownership) | 4 days |
| Re-create observability — Prefect UI run history → Claude Code session URLs + custom logging | 5 days |
| Owner-account migration runbook (what happens when the claude.ai owner leaves) | 2 days |
| Cost monitoring (metered overage tracking) | 2 days |
| **Total** | **~30 engineer-days** |

### 4.2 Gained (if we migrate)

- **One less infrastructure dependency.** Drop Prefect server + Railway worker container.
- **Native AI-native runtime.** Each run is a Claude Code session — no separate model orchestration.
- **GitHub-event triggers** for PR/Release reactions (we don't currently use this surface, but it's available).

### 4.3 Lost (if we migrate)

- **Sub-hourly scheduling** — `health-check-flow` (5min), `callback-poller` (60s), `voice-outreach-flow` (30min) cannot run on Routines.
- **Concurrency primitives.** Pool concurrency 10 and voice concurrency 1 are enforced by Prefect today; Routines documentation contains no concurrency control.
- **Catch-up on missed events.** Prefect retries; Routines drops over-cap webhook events with no replay.
- **Org-shared ownership.** Routines are per-claude.ai-account; bus factor goes to 1.
- **Self-hosting and provider portability.** Routines are Anthropic-only — no GPT-5/Gemini/Kimi fallback if Claude is down or repriced.
- **Cost predictability.** Metered overage on the 25-runs-per-day cap is uncapped. We currently pay flat Railway compute.
- **Direct DB/Redis access.** Worker today connects to Supabase/Redis on Railway's private network. Routines must reach them via public internet through the cloud environment's network policy — increases attack surface.

### 4.4 Vendor-lock-in cost

`byteiota` analysis is direct: "Routines only works inside Claude Code. Your automation logic isn't portable to Cursor, GitHub Copilot, or other AI coding tools." Migration cost away from Routines mirrors the cost into it. Prefect, by contrast, is open-source — we can self-host the server entirely if Prefect Cloud changes terms.

---

## 5. Recommendation — KEEP PREFECT

### 5.1 Decision

**Keep Prefect for the entire operational graph.** Reject migration. Three independent blockers, any one of which is sufficient:

1. **1-hour minimum schedule interval** invalidates `health-check-flow`, `callback-poller`, and `voice-outreach-flow`. We cannot operate with 5-minute health probes deferred to hourly.
2. **Per-claude.ai-account ownership** is unacceptable for a multi-bot, multi-callsign operation. Bus factor = 1 is a regression from current Railway+Prefect.
3. **Daily run cap (max 25 runs/day even on Team Premium)** is consumed by `credit-reset-flow` + `free-enrichment-flow` alone. Every other flow then runs on metered overage with no cost ceiling.

### 5.2 Limited hybrid use case (optional, low-priority)

**Routines has one defensible niche** in our world: meta-automation of dev workflow that does not touch production data:

- Weekly PR digest summarising ELLIOT/AIDEN merged PRs (GitHub `pull_request.closed` filtered to `is_merged: true` against Agency_OS).
- Nightly PR review bot for `release/*` branches.
- One-off cleanup runs ("in 2 weeks open a PR removing the X feature flag").

These do not appear in `prefect.yaml`, do not consume Prefect concurrency, and don't depend on Supabase/Redis. A single Pro plan ($31 AUD/month) covers them. **This is a separate, additive evaluation — not a migration.**

### 5.3 Suggested follow-up directives

- **P8-A — DO NOT migrate.** Document the decision in MANUAL.md and ceo_memory so the next dispatch doesn't re-litigate.
- **P8-B — Pilot Routines for dev-meta only.** One Pro account, one routine: weekly PR digest. 30-day trial; abandon if it doesn't save reviewer time.
- **P8-C — Prefect Cloud RBAC review.** As we add more callsigns (SCOUT joins ELLIOT/AIDEN), evaluate whether Prefect Cloud paid tier (workspaces, RBAC, audit log) is worth the spend versus self-hosting Prefect server on Railway. This is the *real* orchestration question — orthogonal to Routines.

---

## Sources

- [Anthropic — Run prompts on a schedule (Claude Code docs)](https://code.claude.com/docs/en/scheduled-tasks)
- [Anthropic — Automate work with routines](https://code.claude.com/docs/en/routines)
- [DevOps.com — Claude Code Routines: Anthropic's Answer to Unattended Dev Automation](https://devops.com/claude-code-routines-anthropics-answer-to-unattended-dev-automation/)
- [byteiota — Claude Code Routines: Anthropic Kills Cron Jobs, Adds Lock-In](https://byteiota.com/claude-code-routines-anthropic-kills-cron-jobs-adds-lock-in/)
- [Junia.ai — Claude Code Routines Explained](https://www.junia.ai/blog/claude-code-routines)
- [9to5Mac — Anthropic adds routines to redesigned Claude Code](https://9to5mac.com/2026/04/14/anthropic-adds-repeatable-routines-feature-to-claude-code-heres-how-it-works/)
- [The Register — Claude Code routines promise mildly clever cron jobs](https://www.theregister.com/2026/04/14/claude_code_routines/)
- Local: `/home/elliotbot/clawd/Agency_OS-scout/prefect.yaml` (26 deployments, Prefect 3.0.0)
