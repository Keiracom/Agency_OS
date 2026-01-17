# E2E Testing Reference

> **Status is tracked in `e2e_state.json` ONLY.**
> Run `/e2e status` to see current progress.

---

## Quick Commands

| Command | Purpose |
|---------|---------|
| `/e2e status` | Show current position and progress |
| `/e2e approve` | CEO approves next group (required before continue) |
| `/e2e continue` | Execute next group (requires prior approval) |
| `/e2e fix ISS-XXX` | Fix a specific issue |
| `/e2e report` | Generate CEO summary |

---

## Journey Reference

| Journey | Name | Groups | Description |
|---------|------|--------|-------------|
| J0 | Infrastructure Audit | 9 | Services, env vars, Prefect, database, integrations |
| J1 | Signup & Onboarding | 15 | User signup → ICP extraction → dashboard |
| J2 | Campaign & Leads | 12 | Create campaign, source leads, score |
| J2B | Lead Enrichment | 8 | LinkedIn scraping, data enrichment, ALS |
| J3 | Email Outreach | 12 | Salesforge integration, sending, tracking |
| J4 | SMS Outreach | 12 | Twilio integration, sending, tracking |
| J5 | Voice Outreach | 13 | Vapi integration, calls, tracking |
| J6 | LinkedIn Outreach | 13 | HeyReach integration, messages, tracking |
| J7 | Reply Handling | 12 | Classification, routing, responses |
| J8 | Meeting & Deals | 13 | Calendar booking, deal creation |
| J9 | Dashboard Validation | 16 | Metrics accuracy, UI verification |
| J10 | Admin Dashboard | 14 | Platform admin functionality |

**Total:** ~139 groups across 12 journeys

---

## Test Configuration

| Field | Value |
|-------|-------|
| Test Agency | Sparro Digital |
| Website | https://sparro.com.au |
| Test Email | david.stephens@keiracom.com |
| Test Phone | +61457543392 |
| Daily Email Limit | 15 |
| E2E Budget | $60 AUD |

Full config: `e2e_config.json`

---

## File Structure

```
docs/e2e/
├── e2e_state.json      ← SINGLE SOURCE OF TRUTH
├── e2e_config.json     ← Test configuration
├── E2E_MASTER.md       ← This file (reference only)
├── J0_INFRASTRUCTURE.md - J10_ADMIN.md  ← Journey instructions
├── ISSUES_FOUND.md     ← Issue log
└── FIXES_APPLIED.md    ← Fix log
```

---

## Workflow

```
1. CEO: /e2e status         → See current state
2. CEO: /e2e approve        → Approve next group
3. Claude: /e2e continue    → Execute group, update JSON, stop
4. Repeat from step 1
```

**Key principle:** Claude cannot continue without CEO approval. The `/e2e continue` command enforces this.

---

## Journey Files

| File | Content |
|------|---------|
| `J0_INFRASTRUCTURE.md` | Infrastructure & Wiring Audit |
| `J1_ONBOARDING.md` | Signup & Onboarding |
| `J2_CAMPAIGN.md` | Campaign & Leads |
| `J2B_ENRICHMENT.md` | Lead Enrichment |
| `J3_EMAIL.md` | Email Outreach |
| `J4_SMS.md` | SMS Outreach |
| `J5_VOICE.md` | Voice Outreach |
| `J6_LINKEDIN.md` | LinkedIn Outreach |
| `J7_REPLY.md` | Reply Handling |
| `J8_MEETING.md` | Meeting & Deals |
| `J9_DASHBOARD.md` | Dashboard Validation |
| `J10_ADMIN.md` | Admin Dashboard |
