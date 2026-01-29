# Agency OS — Roadmap

*What's next, in priority order.*

---

## Current Focus (P0)

### E2E Testing — Phase 21
**Status:** 🔴 All journeys J0-J6 failing
**Blocker for:** Launch

Test journeys needed:
- J0: Lead import and scoring
- J1: Email sequence execution
- J2: LinkedIn outreach flow
- J3: SMS/voice integration
- J4: Multi-channel orchestration
- J5: Meeting booking flow
- J6: Full funnel tracking

**Why it matters:** Can't launch without proving the system works end-to-end with real API calls.

### Dashboard Production Swap
**Status:** 🟡 Prototype ready, not deployed
**Blocker for:** Launch

- Production dashboard still uses banned commodity language
- V4 customer-focused prototype ready (dashboard-v4-customer.html)
- Need to swap DashboardHome.tsx with prototype components

---

## Next Up (P1)

### Database Latency
- Current: 2.2 seconds
- Likely cause: Railway backend in wrong region vs Supabase AP-Southeast-1
- Impact: User experience, API timeouts

### Dependency Pinning
- All requirements use >= instead of ==
- Risk: Builds break when dependencies update
- Fix: Pin exact versions, use dependabot for updates

### Test Coverage
- Current: 47 test files vs 185 source files
- Target: Critical paths covered
- Priority: Orchestration, ALS scoring, channel integrations

---

## Backlog (P2)

### Dead Code Cleanup
- resend.py, heyreach.py still in repo but deprecated
- _test_token.txt with JWT committed to git (security risk)
- Xero financial data accidentally committed

### Documentation
- API documentation incomplete
- Onboarding guide needed for new agencies
- Internal architecture docs need refresh

---

## Future Vision (P3+)

### Phase H (Client Transparency)
- Items 40-44: Complete ✅
- Items 45-47: Remaining
- Goal: Full visibility into what the system is doing

### ML Enhancement
- WHO/WHAT/WHEN/HOW detectors exist but could be improved
- Pattern learning from successful conversions
- ICP refinement automation

### New Channels
- Direct mail integration (ClickSend ready)
- WhatsApp (when compliant)
- Retargeting integration

---

## Launch Checklist

Before going live with paying customers:

- [ ] E2E tests passing (J0-J6)
- [ ] Dashboard V4 deployed
- [ ] Database latency < 500ms
- [ ] All P0 bugs resolved ✅
- [ ] Critical test coverage
- [ ] Error monitoring active
- [ ] Backup/recovery tested
- [ ] Pricing page live
- [ ] Onboarding flow ready
- [ ] Support process defined

---

*Update when priorities shift or items complete.*
