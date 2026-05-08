# Agency OS Frontend — Playwright E2E

**Status:** SCAFFOLD ONLY (2026-05-08). Hold-fire on running until Phase 0 triggers.

## What this is

Phase 1 deliverable A1 from the locked roadmap: a Playwright headless smoke test that verifies the deployed frontend at `app.agencyxos.ai` renders a working signup form + auth gate + post-login dashboard content.

Closes the two UNVERIFIED items from the 2026-05-08 trust verification audit (V6):

- Signup form actually renders + submits (the CSR React bundle works)
- Authenticated `/dashboard` renders meaningful content (not blank, not error)

## Why hold-fire

Per Max's directive 2026-05-08 ("E approved with constraint — scaffold and config only, no production test runs, no npm install against prod"):

- Spec file + config exist for review
- `npm install -D @playwright/test` not yet run (would touch `package-lock.json` against npm registry — Phase 0 install step)
- Tests targeting prod login flow are skipped — require seeded test account from `scripts/seed_demo_tenant.py`

## Pre-flight before first run

1. Phase 0 trigger lands (Salesforge + Unipile keys regenerated, frontend deploys stable on main)
2. Seed test tenant: `python scripts/seed_demo_tenant.py` to ensure stable Demo Agency identity
3. Export test creds: `export TEST_LOGIN_EMAIL=demo@... TEST_LOGIN_PASSWORD=...`
4. Install Playwright: `cd frontend && npm install -D @playwright/test && npx playwright install chromium`
5. Optional override: `export PLAYWRIGHT_BASE_URL=https://staging.agencyxos.ai` to target staging

## Run

```bash
cd frontend
npx playwright test e2e/smoke.spec.ts --project=chromium
```

## Exit criteria for A1 deliverable

All three non-skipped tests pass + the skipped `authed dashboard renders content` test unskipped and passing. Then V6 UNVERIFIED items are closed.

## See also

- `docs/audits/aiden/audit_verify_2026-05-08.md` — origin V6 UNVERIFIED items
- `scripts/seed_demo_tenant.py` — stable test tenant identity
- `playwright.config.ts` — test runner config (sibling file)
