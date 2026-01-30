# Agency OS — Full Repo Audit
**Date:** 2026-01-28
**Auditor:** Elliot (CTO)
**Repo:** Keiracom/Agency_OS

---

## Executive Summary

Agency OS is a substantial codebase (~99K lines Python, 185 source files, 49 migrations) with solid architecture decisions. But it has the hallmarks of being built by AI agents without enough human QA: **CI is broken and has been for weeks, test coverage is minimal, dependencies are unpinned, and the frontend doesn't build.** The backend API is alive but has concerning 2.2-second database latency. You're closer to launch than it might feel, but there are real issues to fix before a customer touches this.

---

## 🟢 What's Good

### Production Services — Mostly Alive
| Service | Status | Response Time |
|---------|--------|---------------|
| Backend API | ✅ HTTP 200 | 3.2s |
| Frontend (Vercel) | ✅ HTTP 200 | 1.6s |
| Prefect Server | ✅ HTTP 200 | 1.1s |
| Supabase | ⚠️ HTTP 404 (expected for root) | 0.1s |
| Database | ✅ Connected | 2,232ms latency ⚠️ |
| Redis | ✅ Connected | 241ms |

### Architecture — Well Designed
- Clean 4-layer import hierarchy (models → integrations → engines → orchestration)
- **No major import violations** — engines import from `base.py` and shared utils within the same layer (acceptable pattern)
- No engines importing from orchestration ✅
- No integrations importing from engines ✅
- No models importing up the chain ✅

### Security
- No hardcoded API keys in Python source ✅
- Sentry integrated for error tracking ✅
- Dockerfiles use non-root users ✅
- `.gitignore` covers `.env` files ✅
- Supabase RLS policies present (migration 009) ✅

### Documentation
- Extensive phase docs, architecture docs, specs
- CLAUDE.md is thorough and well-structured
- Clear blueprint and progress tracking

---

## 🔴 Critical Issues

### 1. CI/CD is Broken — Every Recent Build Fails
**Last 5 CI runs: ALL FAILURES.** The pipeline hasn't passed since at least Jan 22.

Failures:
- **Ruff linter** — code style violations
- **Frontend build** — TypeScript errors (`No overload matches this call`)

This means: code is being committed to `main` without any automated checks actually gating it. The `|| true` on mypy and eslint means those checks are cosmetic.

**Impact:** You could deploy broken code to production at any time.

### 2. Database Latency: 2,232ms
The health endpoint shows database latency over 2 seconds. For a SaaS product, this is extremely slow. Likely causes:
- Backend is on Railway (probably US region) connecting to Supabase (AP-Southeast)
- Connection pooling may not be optimized
- No connection pool warming

**Impact:** Every API call will feel sluggish to users.

### 3. No Dependency Pinning
All 57 Python dependencies use `>=` (minimum version) instead of `==` (exact version):
```
fastapi>=0.109.0
sqlalchemy>=2.0.0
anthropic>=0.39.0
```
**Impact:** Any `pip install` could pull breaking changes. Builds are not reproducible. A minor update to any dep could break production overnight.

### 4. Test Token Committed to Git
`_test_token.txt` contains a full Supabase JWT token in the repo. Even if it's a test token, this is in git history forever.

### 5. Supabase Anon Key in `.env.production`
`frontend/.env.production` contains the Supabase anon key committed to git. While anon keys are designed to be public-facing, having it in version control alongside the pattern of other secrets is risky.

---

## 🟡 Warnings

### 6. Test Coverage is Thin
- **185 source files** but only **47 test files** (35 unit, 2 integration, 6 live)
- Key areas with NO tests:
  - Most API routes untested
  - Most integrations untested  
  - Service layer largely untested
- The E2E test suite (Phase 21) has been stuck at 🔴 for all journeys

### 7. Frontend Has Build Errors
CI shows TypeScript errors in the frontend build. The frontend is deployed on Vercel (which caches), but any redeploy could fail.

### 8. 42 TODOs and 20 FIXMEs in Source
Notable ones:
- `src/api/routes/leads.py`: "TODO: Integrate with Prefect enrichment flow" (×2)
- `src/api/routes/crm.py`: Hardcoded frontend URL
- `src/api/routes/webhooks.py`: "TODO: Log to Sentry in production"
- `src/api/routes/admin.py`: "TODO: Implement ai_usage_logs table"
- `src/api/dependencies.py`: "TODO: Implement API-level rate limiting"

### 9. Several Integrations Lack Retry Logic
| Integration | Error Handling | Retries |
|-------------|---------------|---------|
| Apollo | ✅ Good | ✅ Has retries |
| Salesforge | ✅ Good | ❌ No retries |
| Vapi | ⚠️ Minimal | ❌ No retries |
| Unipile | ✅ Good | ✅ Has retries |
| Twilio | ❌ File not found (twilio_sms.py) | N/A |

### 10. Images/Binaries in Git
~40 PNG/JPG files in `docs/marketing/` bloating the repo. Should be in cloud storage or Git LFS.

### 11. Migration Gaps
Migrations skip from 018→021 and 021→024. Not necessarily a problem, but suggests some migrations were deleted or renumbered.

### 12. Database Has Minimal Data
- Only **1 client** (Keira Communications — your test company)
- Only **11 leads** in lead_pool
- Only **2 campaigns** (both E2E tests)
- No real customer data to validate against

### 13. Stale/Deprecated Integrations
- `src/integrations/resend.py` still exists (217 lines) but Resend was replaced by Salesforge
- `src/integrations/heyreach.py` still exists (481 lines) but HeyReach was replaced by Unipile
- `src/integrations/postmark.py` exists (307 lines) — unclear if used
- `src/integrations/serper.py` exists (381 lines) — unclear if used

---

## 📊 Codebase Stats

| Metric | Count |
|--------|-------|
| Python source files | 185 |
| Total Python lines | ~99,000 |
| Frontend pages | 47 |
| Database migrations | 49 |
| Database tables | 112 (exposed via API) |
| API integrations | 22 |
| Prefect flow deployments | 17 (12 active, 5 paused) |
| Test files | 47 |
| Git repo size | 9.3 MB |

### Code by Layer
| Layer | Lines |
|-------|-------|
| Services | 16,878 |
| Engines | 16,732 |
| Orchestration | 15,191 |
| API | 15,255 |
| Agents | 14,782 |
| Integrations | 9,811 |
| Models | 5,195 |

---

## 🎯 Prioritized Action Plan

### P0 — Do Immediately (Before Any Customer)
1. **Fix CI pipeline** — ruff errors + frontend TypeScript errors. Every merge to main should pass.
2. **Pin all Python dependencies** — generate a `requirements.lock` with exact versions from a working deploy.
3. **Investigate database latency** — 2.2s is unacceptable. Check Railway region vs Supabase region.
4. **Remove `_test_token.txt`** from repo and add to `.gitignore`.
5. **Remove dead integration code** (resend.py, heyreach.py) or clearly mark as deprecated.

### P1 — Before First Customer
6. **Complete E2E testing** (Phase 21) — this is THE blocker.
7. **Add retry logic** to Salesforge and Vapi integrations.
8. **Fix hardcoded frontend URL** in crm.py.
9. **Resolve the 42 TODOs** — at minimum the API-level ones.
10. **Add basic integration tests** for the critical path: signup → onboarding → campaign → outreach.

### P2 — Soon After Launch
11. **Move images to cloud storage** and out of git.
12. **Clean up console.logs** in frontend (8 found).
13. **Implement rate limiting** at API level.
14. **Set up proper staging environment** for testing.
15. **Upgrade Next.js** from 14.0.4 (current LTS is higher).

---

*This audit represents the state of the codebase as of 2026-01-28. It was conducted by reading actual files, hitting real endpoints, and checking git history — not from documentation alone.*
