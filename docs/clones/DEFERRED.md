# PHASE 2.1 + 2.2 — Deferred Items

**Context:** Aiden dispatched Phase 2.1 (dashboard wiring) + 2.2 (outreach safety layer) to ORION on 2026-04-23 with a 90-minute timebox. Aiden approved scope narrowing to 2+2 solid slices. Remaining items from the original dispatch are logged here for the next dispatch.

**Shipped on `orion/phase-2.1-2.2`:**
- Track 2.1a: Activity feed wired from `mockActivityFeed` → `useLiveActivityFeed` (30s polling against `/api/v1/reports/clients/{id}/activities`). Hot prospects / week ahead / warm replies / quick stats were already wired via `useDashboardV4`.
- Track 2.1b: `frontend/lib/provider-labels.ts` — canonical label scrub utility (DFS organic ETV → Organic traffic value, Unipile → LinkedIn, ElevenAgents → Voice AI, Salesforge → Email, Keira white-label via `agencyPersona`). Applied to activity feed text in `frontend/app/dashboard/page.tsx`.
- Track 2.2a: `src/outreach/safety/timing_engine.py` — multi-channel (Email, LinkedIn, Voice, SMS) with workday + work-hour + optimal-window filters, AU 2026 public holidays, prospect-TZ aware, `next_window_start` computed. 13 tests passing.
- Track 2.2b: `src/outreach/safety/compliance_guard.py` — suppression + DNCR (voice/SMS only) + TCP hours (9am–8pm Mon–Sat, no Sunday) + SPAM_ACT unsubscribe. 22 tests passing.

**Test baseline added:** `tests/outreach/safety/` — 35 tests, 100% pass on `pytest tests/outreach/safety/ -v`.

---

## Deferred — Track 2.1 (Dashboard Wiring)

| Item | Description | Status | Recommended next dispatch |
|------|-------------|--------|----------------------------|
| 2.1.1a | Home route Today strip (hero + Maya-working + funnel bar + attention cards) full Master v10 port | **Deferred** | Ship as its own dispatch — `PHASE-2.1-HOME-V10-PORT`; requires Master v10 HTML read + component extraction ~3 hr |
| 2.1.1b | Pipeline route — Kanban + Table toggle | **Deferred** | `PHASE-2.1-PIPELINE-KANBAN` ~4 hr |
| 2.1.1c | Meetings route — Calendar + briefings | **Deferred** | `PHASE-2.1-MEETINGS-CALENDAR` ~4 hr |
| 2.1.1d | Feed route — activity timeline | **Deferred** (feed hook now wired on /dashboard; dedicated /activity route still a stub) | `PHASE-2.1-FEED-ROUTE` ~2 hr |
| 2.1.1e | Right-drawer prospect detail across all surfaces | **Deferred** | `PHASE-2.1-PROSPECT-DRAWER` ~3 hr; must coordinate with existing lead detail component |
| 2.1.3 | Supabase Realtime subscriptions (outreach_events, reply_events, dm_meetings, bu_lifecycle), subscribe-per-view | **Deferred** | `PHASE-2.1-REALTIME` — needs channel multiplexing decision and auth model ~4 hr |
| 2.1.5 | Unified outreach timeline (past green + future amber + Pause/Skip/Accelerate controls) | **Deferred** | `PHASE-2.1-UNIFIED-TIMELINE` ~5 hr; depends on 2.2 dispatcher wrapper for Pause/Skip/Accelerate actions |
| 2.1.6 | VR grade popovers clickable on all prospects with context-dependent content | **Deferred** | `PHASE-2.1-VR-POPOVERS` ~3 hr |
| 2.1-test | Frontend test runner (Vitest) install + config | **Deferred** | Blocker: `frontend/package.json` has no test script or vitest/jest dep. Added `provider-labels.ts` without test runner — spec exists in this doc as pseudocode. Dispatch `FRONTEND-TEST-RUNNER-SETUP` ~1 hr |

## Deferred — Track 2.2 (Outreach Safety Layer)

| Item | Description | Status | Recommended next dispatch |
|------|-------------|--------|----------------------------|
| 2.2.2 | Rate limiter (Email 50→100 warming ladder, LinkedIn 100/week 50/day, Voice 3/24hr, SMS 1/cycle) | **Deferred** | `PHASE-2.2-RATE-LIMITER` ~3 hr. `src/memory/ratelimit.py` + `src/services/rate_limit_manager.py` exist — unify + extend per-channel caps |
| 2.2.2a | Mailbox rotation pool (5–10 domains) + warming state machine | **Deferred** | `PHASE-2.2-MAILBOX-ROTATION` ~4 hr |
| 2.2.4 | Dispatcher wrapper over Salesforge/Unipile/ElevenAgents with webhook → outreach_events | **Deferred** | `PHASE-2.2-DISPATCHER-WRAPPER` ~6 hr. Largest ticket — central choke point, needs architect-0 sign-off |
| 2.2.5 | Prefect flows (hourly pending-touches pipeline, daily warming/cycle/deliverability, weekly LinkedIn reset + mailbox stats, monthly cycle-close) | **Deferred** | `PHASE-2.2-PREFECT-FLOWS` ~5 hr |
| 2.2.6 | Deliverability monitor — bounce >5% auto-pause, spam complaint >0.1% quarantine, LinkedIn 402/429 → 7-day cooldown | **Deferred** | `PHASE-2.2-DELIVERABILITY-MONITOR` ~4 hr |

## Integration gaps

- **Timing engine ↔ rate limiter:** Rate limiter (2.2.2) will call `timing_engine.check()` before consuming a token. Wrapper interface TBD when 2.2.2 ships.
- **Compliance guard ↔ suppression_manager:** `compliance_guard.ComplianceGuard` takes injected `suppression_lookup` callable. Real integration with `src/services/suppression_manager.py` (if it exists) is deferred to `PHASE-2.2-COMPLIANCE-WIRE`.
- **Compliance guard ↔ DNCR API:** DNCR lookup is injected, not implemented. Real ACMA DNCR API client is deferred — needs the `WASH` or similar service integration (~2 hr) plus API credentials in env.

## Estimates summary

- Deferred 2.1 items: ~24 hr total
- Deferred 2.2 items: ~22 hr total
- **Total remaining on Phase 2.1 + 2.2:** ~46 hr vs the 90-min ORION slice shipped today.

This confirms the scope-narrowing decision — the full dispatch was 30x the timebox. Shipping 4 solid foundations with tests beats 12 half-built surfaces.
