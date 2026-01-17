# J0: Infrastructure & Wiring Audit

**Priority:** P0 — Must pass before any journey testing
**Groups:** 9 (J0.1 - J0.9)
**Checks:** 54 total

> **Note:** Status is tracked in `e2e_state.json`, not here. This file contains instructions only.

---

## Overview

This journey verifies that all infrastructure, services, and code wiring is correct BEFORE testing user flows. This catches issues like:

- Prefect pointing to Cloud instead of self-hosted
- Missing environment variables
- Stubbed or incomplete implementations
- Wrong database connections (port 5432 vs 6543)
- Missing Docker dependencies

---

## Sub-Tasks

### J0.1 — Railway Services Health
**Purpose:** Verify all 3 Railway services are deployed and responding.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.1.1 | Read Dockerfile — verify entry point is `uvicorn src.api.main:app` | Call https://agency-os-production.up.railway.app/api/v1/health |
| J0.1.2 | Read Dockerfile.prefect — verify start script exists | Call https://prefect-server-production-f9b1.up.railway.app/api/health |
| J0.1.3 | Read Dockerfile.worker — verify PYTHONPATH=/app | Check Prefect UI for active worker |
| J0.1.4 | Read docker-compose.yml — verify 3-service architecture | N/A (Railway deployment) |
| J0.1.5 | Check scripts/start-prefect-server.sh uses Railway PORT | Verify Prefect UI accessible |
| J0.1.6 | Check scripts/start-prefect-worker.sh waits for server health | Check worker logs for "Started worker" |

**Pass Criteria:**
- [ ] API returns `{"status": "healthy"}` with HTTP 200
- [ ] Prefect returns healthy status
- [ ] Worker shows as online in Prefect UI

<!-- E2E_SESSION_BREAK: J0.1 complete. Next: J0.2 Environment Variables -->

---

### J0.2 — Environment Variables Audit
**Purpose:** Every required env var exists in Railway AND has valid format.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.2.1 | Read config/.env.example — list ALL required vars | Use `railway variables --service agency-os --kv` to verify |
| J0.2.2 | Read src/config/settings.py — check which vars have defaults | Identify vars that will crash if missing |
| J0.2.3 | Verify DATABASE_URL uses port 6543 (Transaction Pooler) | Query database, check no "prepared statement" errors |
| J0.2.4 | Verify DATABASE_URL_MIGRATIONS uses port 5432 | N/A (migrations run separately) |
| J0.2.5 | Verify PREFECT_API_URL points to Railway service, not Prefect Cloud | Check worker logs for connection URL |
| J0.2.6 | Verify SENTRY_DSN is set | Trigger test error, verify appears in Sentry |
| J0.2.7 | Verify TEST_MODE=false in production | Confirm via settings endpoint or logs |

**Critical Variables to Verify:**

| Variable | Required | Format Check |
|----------|----------|--------------|
| DATABASE_URL | Yes | Must contain `:6543/` |
| DATABASE_URL_MIGRATIONS | Yes | Must contain `:5432/` |
| SUPABASE_URL | Yes | Must be `https://*.supabase.co` |
| SUPABASE_KEY | Yes | Must start with `eyJ` (JWT) |
| SUPABASE_SERVICE_KEY | Yes | Must start with `eyJ` (JWT) |
| REDIS_URL | Yes | Must be `redis://` or `rediss://` |
| PREFECT_API_URL | Yes | Must NOT contain `api.prefect.cloud` |
| ANTHROPIC_API_KEY | Yes | Must start with `sk-ant-` |
| SENTRY_DSN | Yes | Must be `https://*.ingest.sentry.io` |

**Pass Criteria:**
- [ ] All required vars present in Railway
- [ ] DATABASE_URL uses port 6543
- [ ] PREFECT_API_URL is self-hosted URL
- [ ] No Prefect Cloud references

<!-- E2E_SESSION_BREAK: J0.2 complete. Next: J0.3 Prefect Configuration -->

---

### J0.3 — Prefect Configuration Verification
**Purpose:** Confirm Prefect is self-hosted and flows are deployed.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.3.1 | Read prefect.yaml — verify work pool `agency-os-pool` | Check Prefect UI → Work Pools |
| J0.3.2 | Read prefect.yaml — list all 15 flows | Check Prefect UI → Deployments |
| J0.3.3 | Verify webhook-triggered flows are ACTIVE | Check deployment schedules in UI |
| J0.3.4 | Verify scheduled flows are PAUSED by default | Confirm schedules show "Paused" |
| J0.3.5 | Read scripts/start-prefect-worker.sh — verify pool creation | Check worker creates pool on startup |
| J0.3.6 | Verify PREFECT_API_DATABASE_CONNECTION_URL is PostgreSQL | Check Prefect server logs for "Using PostgreSQL" |

**Expected Flows (15 total):**

| Flow | Trigger | Expected State |
|------|---------|----------------|
| campaign-flow | Webhook | Active |
| enrichment-flow | Schedule (2 AM) | PAUSED |
| outreach-flow | Schedule (8-6 PM) | PAUSED |
| reply-recovery-flow | Schedule (6-hourly) | PAUSED |
| onboarding-flow | Webhook | Active |
| icp-reextract-flow | Webhook | Active |
| pool-population-flow | Webhook | Active |
| pool-assignment-flow | Webhook | Active |
| pool-daily-allocation-flow | Schedule (6 AM) | PAUSED |
| intelligence-flow | Webhook | Active |
| trigger-lead-research | Webhook | Active |
| pattern-learning-flow | Schedule (Sunday 3 AM) | PAUSED |
| client-pattern-learning-flow | Webhook | Active |
| pattern-backfill-flow | Manual | Active |
| client-backfill-flow | Webhook | Active |

**Pass Criteria:**
- [ ] Work pool `agency-os-pool` exists
- [ ] All 15 flows deployed
- [ ] Webhook flows are Active
- [ ] Scheduled flows are Paused
- [ ] Prefect using PostgreSQL (not SQLite)

<!-- E2E_SESSION_BREAK: J0.3 complete. Next: J0.4 Database Connection -->

---

### J0.4 — Database Connection Verification
**Purpose:** Verify correct pooler port and connection settings.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.4.1 | Read src/integrations/supabase.py — verify pool settings | N/A |
| J0.4.2 | Verify pool_size=5, max_overflow=10 | Check active connections in Supabase dashboard |
| J0.4.3 | Verify statement_cache_size=0 (Supavisor compatibility) | Execute query, no "prepared statement" errors |
| J0.4.4 | Verify expire_on_commit=False | N/A |
| J0.4.5 | Read get_db_session() — verify commit/rollback/close | N/A |
| J0.4.6 | Test database query via health endpoint | Call /api/v1/health/ready, check database latency |

**Expected Configuration:**
```python
pool_size=5
max_overflow=10
pool_timeout=30
pool_recycle=1800
pool_pre_ping=True
statement_cache_size=0  # CRITICAL for Supavisor
```

**Pass Criteria:**
- [ ] Connection uses port 6543
- [ ] Statement caching disabled
- [ ] Health check returns database healthy
- [ ] No connection pool exhaustion errors

<!-- E2E_SESSION_BREAK: J0.4 complete. Next: J0.5 Integration Wiring -->

---

### J0.5 — Integration Wiring Audit
**Purpose:** Verify each integration client is properly configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.5.1 | Read src/integrations/anthropic.py — verify AsyncAnthropic init | Make test completion call (budget check) |
| J0.5.2 | Verify AI spend limiter checks Redis | Check `v1:ai_spend:daily:YYYY-MM-DD` key |
| J0.5.3 | Read src/integrations/apollo.py — verify httpx client | Call Apollo health/status (if available) |
| J0.5.4 | Read src/integrations/resend.py — verify API key set | Send test email (TEST_MODE) |
| J0.5.5 | Read src/integrations/twilio.py — verify Client init | Send test SMS (TEST_MODE) |
| J0.5.6 | Read src/integrations/heyreach.py — verify httpx client | Check API key validity |
| J0.5.7 | Read src/integrations/vapi.py — verify httpx client | Check API key validity |
| J0.5.8 | Read src/integrations/redis.py — verify async client | PING Redis via health check |
| J0.5.9 | Read src/integrations/sentry_utils.py — verify init | Trigger test error, check Sentry |

**Integration Status Matrix:**

| Integration | File | Client Type | Async | Spend Limit |
|-------------|------|-------------|-------|-------------|
| Anthropic | anthropic.py | AsyncAnthropic | Yes | Yes (50 AUD/day) |
| Apollo | apollo.py | httpx.AsyncClient | Yes | No (credit-based) |
| Apify | apify.py | ApifyClient | Yes | No |
| Clay | clay.py | httpx.AsyncClient | Yes | No |
| Resend | resend.py | resend SDK | Yes | No |
| Postmark | postmark.py | httpx.AsyncClient | Yes | No |
| Twilio | twilio.py | twilio.rest.Client | Sync* | No |
| HeyReach | heyreach.py | httpx.AsyncClient | Yes | No |
| Vapi | vapi.py | httpx.AsyncClient | Yes | No |
| ElevenLabs | elevenlabs.py | httpx.AsyncClient | Yes | No |
| ClickSend | clicksend.py | httpx.AsyncClient | Yes | No |
| DataForSEO | dataforseo.py | httpx + Basic Auth | Yes | No |
| Redis | redis.py | redis.asyncio | Yes | N/A |
| Supabase | supabase.py | SQLAlchemy | Yes | N/A |

*Note: Twilio uses sync client — potential blocking issue in async context

**Pass Criteria:**
- [ ] All integration files exist
- [ ] All clients initialize without errors
- [ ] API keys are valid (test calls succeed)
- [ ] AI spend limiter functional

<!-- E2E_SESSION_BREAK: J0.5 complete. Next: J0.6 Code Completeness -->

---

### J0.6 — Code Completeness Scan
**Purpose:** Find incomplete implementations that would cause runtime failures.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.6.1 | Search for `TODO` in src/ | List and categorize by severity |
| J0.6.2 | Search for `FIXME` in src/ | List and categorize by severity |
| J0.6.3 | Search for `pass` statements (empty functions) | Verify none in critical paths |
| J0.6.4 | Search for `NotImplementedError` | Verify none in production code |
| J0.6.5 | Search for `raise Exception` (generic) | Should use custom exceptions |
| J0.6.6 | Search for `# type: ignore` | Review each for valid reason |
| J0.6.7 | Search for hardcoded URLs/IPs | Should use env vars |
| J0.6.8 | Search for `print()` statements | Should use logging |

**Severity Classification:**

| Pattern | Severity | Action |
|---------|----------|--------|
| `TODO` in engine | Critical | Must fix before E2E |
| `TODO` in test | Low | Note for later |
| `pass` in API route | Critical | Will cause 500 error |
| `pass` in utility | Medium | May cause silent failure |
| `NotImplementedError` | Critical | Will crash at runtime |
| Hardcoded localhost | Critical | Won't work in production |

**Pass Criteria:**
- [ ] No critical TODOs blocking user flows
- [ ] No empty `pass` in API routes or engines
- [ ] No `NotImplementedError` in production code
- [ ] No hardcoded localhost URLs

<!-- E2E_SESSION_BREAK: J0.6 complete. Next: J0.7 Import Hierarchy -->

---

### J0.7 — Import Hierarchy Verification
**Purpose:** Ensure no circular imports or layer violations.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.7.1 | Verify models/ only imports from exceptions | Grep imports in src/models/ |
| J0.7.2 | Verify integrations/ only imports from models | Grep imports in src/integrations/ |
| J0.7.3 | Verify engines/ only imports from models, integrations | Grep imports in src/engines/ |
| J0.7.4 | Verify orchestration/ can import all layers | Grep imports in src/orchestration/ |
| J0.7.5 | Check for engine-to-engine imports (forbidden) | Should pass data via orchestration |
| J0.7.6 | Run `python -c "import src.api.main"` | No ImportError |

**Import Hierarchy (Enforced):**
```
Layer 4: src/orchestration/  → Can import ALL below
Layer 3: src/engines/        → models, integrations ONLY
Layer 2: src/integrations/   → models ONLY
Layer 1: src/models/         → exceptions ONLY
```

**Common Violations:**
- Engine importing another engine
- Integration importing engine
- Model importing integration

**Pass Criteria:**
- [ ] No engine-to-engine imports
- [ ] No integration-to-engine imports
- [ ] API starts without ImportError
- [ ] All flows import without error

<!-- E2E_SESSION_BREAK: J0.7 complete. Next: J0.8 Docker & Deployment -->

---

### J0.8 — Docker & Deployment Verification
**Purpose:** Verify Docker builds and deployment config is correct.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.8.1 | Read Dockerfile — verify multi-stage build | Build locally: `docker build -t test .` |
| J0.8.2 | Verify non-root user (appuser) | Check container user in logs |
| J0.8.3 | Verify HEALTHCHECK command | Container health status |
| J0.8.4 | Read .github/workflows/ci.yml — verify jobs | Check GitHub Actions runs |
| J0.8.5 | Verify Railway deploy step | Check Railway deployment logs |
| J0.8.6 | Verify all requirements in requirements.txt | No ModuleNotFoundError at runtime |
| J0.8.7 | Check Camoufox stage (optional) | Only if Tier 3 scraping needed |

**CI/CD Pipeline Jobs:**

| Job | Tool | Purpose | Blocking? |
|-----|------|---------|-----------|
| backend-lint | Ruff | Code style | Yes |
| backend-typecheck | MyPy | Type safety | No (|| true) |
| backend-test | Pytest | Tests | No (|| true) |
| frontend-check | ESLint + TSC | Lint + Types | No (|| true) |
| deploy | Railway CLI | Auto-deploy main | Yes |

**Pass Criteria:**
- [ ] Docker builds without errors
- [ ] CI pipeline passes
- [ ] Railway deployment succeeds
- [ ] No missing dependencies at runtime

<!-- E2E_SESSION_BREAK: J0.8 complete. Next: J0.9 E2E Coverage Verification -->

---

### J0.9 — E2E Coverage Verification (Meta-Check)
**Purpose:** Verify all major Prefect flows and engines have E2E journey coverage.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J0.9.1 | List all flows in `src/orchestration/flows/` | Cross-reference with E2E journeys |
| J0.9.2 | List all engines in `src/engines/` | Verify each has journey coverage |
| J0.9.3 | Verify enrichment flows have journey (J2B) | Check enrichment_flow.py covered |
| J0.9.4 | Verify scoring engine has journey (J2B.5) | Check scorer.py covered |
| J0.9.5 | Verify each outreach channel has journey (J3-J6) | Check all 4 channels |
| J0.9.6 | Verify reply handling has journey (J7) | Check reply_flow.py covered |
| J0.9.7 | Verify meeting/deals has journey (J8) | Check meeting_flow.py covered |

**Flow-to-Journey Mapping:**

| Prefect Flow | E2E Journey | Status |
|--------------|-------------|--------|
| `campaign_flow.py` | J2.4 | ✅ Covered |
| `pool_population_flow.py` | J2.5 | ✅ Covered |
| `pool_assignment_flow.py` | J2.6 | ✅ Covered |
| `lead_enrichment_flow.py` | J2B | ✅ Covered |
| `outreach_flow.py` (email) | J3 | ✅ Covered |
| `outreach_flow.py` (sms) | J4 | ✅ Covered |
| `outreach_flow.py` (voice) | J5 | ✅ Covered |
| `outreach_flow.py` (linkedin) | J6 | ✅ Covered |
| `reply_recovery_flow.py` | J7 | ✅ Covered |
| `meeting_flow.py` | J8 | ✅ Covered |
| `onboarding_flow.py` | J1 | ✅ Covered |

**Engine-to-Journey Mapping:**

| Engine | E2E Journey | Status |
|--------|-------------|--------|
| `scorer.py` | J2.7, J2B.5 | ✅ Covered |
| `scout.py` | J2B.2-J2B.3 | ✅ Covered |
| `content.py` | J2.9 | ✅ Covered |
| `email.py` | J3 | ✅ Covered |
| `sms.py` | J4 | ✅ Covered |
| `voice.py` | J5 | ✅ Covered |
| `linkedin.py` | J6 | ✅ Covered |
| `reply_handler.py` | J7 | ✅ Covered |

**Pass Criteria:**
- [ ] Every Prefect flow has E2E journey coverage
- [ ] Every engine has E2E journey coverage
- [ ] No orphan flows/engines without tests
- [ ] Coverage map is up-to-date

<!-- E2E_SESSION_BREAK: J0.9 complete. J0 JOURNEY COMPLETE. Next: J1 Onboarding -->

---

## Completion Criteria

All checks must pass before proceeding to J1:

- [ ] **J0.1** All Railway services healthy and responding
- [ ] **J0.2** All required env vars present with correct values
- [ ] **J0.3** Prefect self-hosted, all flows deployed, correct states
- [ ] **J0.4** Database using port 6543, pooling configured
- [ ] **J0.5** All integrations have valid API keys
- [ ] **J0.6** No critical TODO/FIXME/pass blocking user flows
- [ ] **J0.7** No import hierarchy violations
- [ ] **J0.8** Docker builds, CI passes, deployment works
- [ ] **J0.9** All flows and engines have E2E journey coverage

---

## Key Files Reference

| Component | File |
|-----------|------|
| API Dockerfile | `Dockerfile` |
| Prefect Dockerfile | `Dockerfile.prefect` |
| Worker Dockerfile | `Dockerfile.worker` |
| Docker Compose | `docker-compose.yml` |
| Prefect Config | `prefect.yaml` |
| Settings | `src/config/settings.py` |
| Env Example | `config/.env.example` |
| CI/CD | `.github/workflows/ci.yml` |
| Health Routes | `src/api/routes/health.py` |
| Database | `src/integrations/supabase.py` |
| Redis | `src/integrations/redis.py` |
| Integrations | `src/integrations/*.py` |
| Start Scripts | `scripts/start-prefect-*.sh` |

---

## Notes

**Why J0 First:**
The Prefect Cloud vs Self-hosted issue was caught because someone manually checked. This journey automates that verification so infrastructure issues are caught BEFORE testing user flows.

**TEST_MODE:**
J0 does NOT require TEST_MODE. It verifies infrastructure only. TEST_MODE is used starting J3 (Email Outreach).
