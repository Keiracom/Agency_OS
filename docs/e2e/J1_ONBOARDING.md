# J1: Signup & Onboarding

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Depends On:** J0 Complete
**Last Updated:** January 11, 2026
**Sub-Tasks:** 15 groups, 58 individual checks
**CTO Verified:** Yes - all sub-tasks based on actual code review

---

## Overview

Tests the complete new user journey from landing page through to dashboard with confirmed ICP.

**Key Components (VERIFIED in codebase):**
- Login page with email/password + Google OAuth
- Signup page with metadata (full_name, company_name)
- Auto-provision trigger (migration 016)
- Auth callback with onboarding status check
- Middleware route protection
- Onboarding flow (website URL → ICP extraction)
- Manual fallback (paste content, LinkedIn URL, skip)
- LinkedIn credential connection with 2FA
- Prefect-triggered ICP extraction

**User Journey:**
```
/login → Sign Up → Email Confirm → /auth/callback → /onboarding → ICP Extraction → /dashboard
```

---

## Sub-Tasks

### J1.1 — Login Page
**Purpose:** Verify login page renders and authenticates users.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.1.1 | Read `frontend/app/(auth)/login/page.tsx` — verify Supabase `signInWithPassword` | Load /login, verify form renders |
| J1.1.2 | Verify `createBrowserClient()` import from `@/lib/supabase` | Submit valid credentials, observe redirect to /dashboard |
| J1.1.3 | Verify Google OAuth uses `signInWithOAuth` with provider "google" | Click Google button, observe OAuth flow |
| J1.1.4 | Verify redirect URL is `${window.location.origin}/auth/callback` | After OAuth, verify callback handles redirect |
| J1.1.5 | Verify error toast on failed login | Submit invalid credentials, verify error message |

**Key Files:**
- `frontend/app/(auth)/login/page.tsx`
- `frontend/lib/supabase.ts`

**Pass Criteria:**
- [ ] Login page renders without console errors
- [ ] Email/password login works
- [ ] Google OAuth redirects to callback
- [ ] Error handling shows toast

<!-- E2E_SESSION_BREAK: J1.1 complete. Next: J1.2 Signup Page -->

---

### J1.2 — Signup Page & Validation
**Purpose:** Verify signup page collects required metadata and creates auth user.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.2.1 | Read `frontend/app/(auth)/signup/page.tsx` — verify fields: email, password, full_name, company_name | Load /signup, verify all 4 fields present |
| J1.2.2 | Verify `signUp()` passes metadata in `options.data` | Fill form, submit, check Supabase auth.users |
| J1.2.3 | Verify password minLength=8 attribute | Submit short password, verify validation |
| J1.2.4 | Verify `emailRedirectTo` is `/auth/callback` | After signup, check email for correct link |
| J1.2.5 | Verify success redirects to /login with "check email" message | Submit valid signup, verify redirect + toast |

**Key Files:**
- `frontend/app/(auth)/signup/page.tsx`

**Pass Criteria:**
- [ ] All 4 fields render
- [ ] Validation prevents weak passwords
- [ ] Confirmation email sent
- [ ] Redirect to login after signup

<!-- E2E_SESSION_BREAK: J1.2 complete. Next: J1.3 Auto-Provisioning -->

---

### J1.3 — Auto-Provisioning Trigger
**Purpose:** Verify database trigger creates client + membership on user signup.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.3.1 | Read `supabase/migrations/016_auto_provision_client.sql` — verify trigger exists | N/A |
| J1.3.2 | Verify `handle_new_user()` creates user in `users` table | After signup, query users table |
| J1.3.3 | Verify function creates client with tier='ignition', subscription_status='trialing', credits=1250 | Query clients table for new record |
| J1.3.4 | Verify function creates membership with role='owner', accepted_at=NOW() | Query memberships table |
| J1.3.5 | Verify trigger is `AFTER INSERT ON auth.users` | Check trigger exists in database |

**Key Files:**
- `supabase/migrations/016_auto_provision_client.sql`

**Verification Query:**
```sql
-- After signup, verify all 3 records exist
SELECT u.id, u.email, c.name, c.tier, c.subscription_status, m.role
FROM users u
JOIN memberships m ON m.user_id = u.id
JOIN clients c ON c.id = m.client_id
WHERE u.email = 'test@example.com';
```

**Pass Criteria:**
- [ ] User record created in users table
- [ ] Client record created with tier=ignition
- [ ] Membership created with role=owner
- [ ] All 3 records linked correctly

<!-- E2E_SESSION_BREAK: J1.3 complete. Next: J1.4 Auth Callback -->

---

### J1.4 — Auth Callback
**Purpose:** Verify callback exchanges code and checks onboarding status.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.4.1 | Read `frontend/app/auth/callback/route.ts` — verify `exchangeCodeForSession` | Click email confirmation link |
| J1.4.2 | Verify `get_onboarding_status()` RPC called | Check database for RPC execution |
| J1.4.3 | Verify redirect to /onboarding if `needs_onboarding=true` | New user → should redirect to /onboarding |
| J1.4.4 | Verify redirect to /dashboard if `needs_onboarding=false` | User with ICP confirmed → should redirect to /dashboard |
| J1.4.5 | Verify error handling redirects to `/login?error=auth_failed` | Simulate invalid code |

**Key Files:**
- `frontend/app/auth/callback/route.ts`

**Pass Criteria:**
- [ ] Code exchange works
- [ ] New users redirect to /onboarding
- [ ] Returning users redirect to /dashboard
- [ ] Errors handled gracefully

<!-- E2E_SESSION_BREAK: J1.4 complete. Next: J1.5 Middleware Protection -->

---

### J1.5 — Middleware Route Protection
**Purpose:** Verify protected routes require authentication.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.5.1 | Read `frontend/middleware.ts` — verify protectedRoutes array | N/A |
| J1.5.2 | Verify /dashboard in protected list | Access /dashboard unauthenticated, verify redirect to /login |
| J1.5.3 | Verify /admin in protected list | Access /admin unauthenticated, verify redirect |
| J1.5.4 | Verify /onboarding in protected list | Access /onboarding unauthenticated, verify redirect |
| J1.5.5 | Verify public routes bypass middleware | Access /, /login, /signup without auth, verify allowed |

**Key Files:**
- `frontend/middleware.ts`

**Pass Criteria:**
- [ ] Protected routes redirect to /login
- [ ] Redirect includes `?redirect=` param
- [ ] Public routes accessible without auth

<!-- E2E_SESSION_BREAK: J1.5 complete. Next: J1.6 Onboarding Page -->

---

### J1.6 — Onboarding Page (Website URL)
**Purpose:** Verify main onboarding page accepts website URL and triggers extraction.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.6.1 | Read `frontend/app/onboarding/page.tsx` — verify form exists | Load /onboarding, verify input field |
| J1.6.2 | Verify API call to `/api/v1/onboarding/analyze` | Submit URL, check network request |
| J1.6.3 | Verify Authorization header includes session token | Check request headers |
| J1.6.4 | Verify `job_id` stored in localStorage | After submit, check localStorage |
| J1.6.5 | Verify redirect to `/dashboard?icp_job={job_id}` | After submit, verify URL |
| J1.6.6 | Verify "Skip for now" link goes to /onboarding/skip | Click skip, verify navigation |

**Key Files:**
- `frontend/app/onboarding/page.tsx`
- `src/api/routes/onboarding.py`

**Pass Criteria:**
- [ ] Page renders with URL input
- [ ] Submit triggers API call
- [ ] Job ID received and stored
- [ ] Redirect to dashboard with job param

<!-- E2E_SESSION_BREAK: J1.6 complete. Next: J1.7 Onboarding API -->

---

### J1.7 — Onboarding API Endpoints
**Purpose:** Verify backend onboarding API is complete and triggers Prefect.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.7.1 | Read `src/api/routes/onboarding.py` — verify POST /onboarding/analyze | Call API, verify 202 response |
| J1.7.2 | Verify endpoint looks up client from memberships | Check query logic |
| J1.7.3 | Verify `run_deployment("icp_onboarding_flow/onboarding-flow")` called | Check Prefect UI for flow run |
| J1.7.4 | Verify GET /onboarding/status/{job_id} returns progress | Poll status endpoint |
| J1.7.5 | Verify GET /onboarding/result/{job_id} returns extracted ICP | After completion, get result |
| J1.7.6 | Verify POST /onboarding/confirm saves to clients table | Confirm ICP, query database |

**Key Files:**
- `src/api/routes/onboarding.py`
- `src/orchestration/flows/onboarding_flow.py`

**API Endpoints:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /onboarding/analyze | Start extraction |
| GET | /onboarding/status/{job_id} | Check progress |
| GET | /onboarding/result/{job_id} | Get extracted ICP |
| POST | /onboarding/confirm | Confirm and apply ICP |

**Pass Criteria:**
- [ ] Analyze endpoint returns job_id
- [ ] Prefect flow triggered
- [ ] Status endpoint returns progress
- [ ] Result endpoint returns ICP data
- [ ] Confirm endpoint saves to database

<!-- E2E_SESSION_BREAK: J1.7 complete. Next: J1.8 ICP Scraper Engine -->

---

### J1.8 — ICP Scraper Engine (Waterfall)
**Purpose:** Verify ICP scraper implements full waterfall architecture.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.8.1 | Read `src/engines/icp_scraper.py` — verify waterfall tiers | N/A |
| J1.8.2 | Verify Tier 0: URL validation via `url_validator.validate_and_normalize()` | Submit invalid URL, verify error |
| J1.8.3 | Verify Tier 1: Apify Cheerio via `scrape_website_with_waterfall()` | Submit static site URL |
| J1.8.4 | Verify Tier 2: Apify Playwright fallback | Submit JS-heavy site URL |
| J1.8.5 | Verify `needs_fallback=True` generates manual fallback URL | Submit Cloudflare-protected site |
| J1.8.6 | Verify portfolio page direct fetch via `_fetch_portfolio_pages()` | Check for /portfolio, /case-studies |
| J1.8.7 | Verify social links extraction via `_extract_social_links()` | Check scraped data includes social URLs |

**Key Files:**
- `src/engines/icp_scraper.py` (1200+ lines - VERIFIED complete)
- `src/engines/url_validator.py`
- `src/integrations/apify.py`

**Waterfall Tiers:**
| Tier | Method | When Used |
|------|--------|-----------|
| 0 | URL Validation | Always first |
| 1 | Apify Cheerio | Static HTML sites |
| 2 | Apify Playwright | JS-rendered sites |
| 3 | Camoufox | Cloudflare (future) |
| 4 | Manual Fallback | When tiers 1-3 fail |

**Pass Criteria:**
- [ ] URL validation rejects invalid URLs
- [ ] Cheerio scrapes static sites
- [ ] Playwright handles JS sites
- [ ] Manual fallback URL generated on failure
- [ ] Social links extracted

<!-- E2E_SESSION_BREAK: J1.8 complete. Next: J1.9 Manual Entry Fallback -->

---

### J1.9 — Manual Entry Fallback
**Purpose:** Verify manual entry page handles scraper failures.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.9.1 | Read `frontend/app/onboarding/manual-entry/page.tsx` — verify 3 tabs | Load page, verify tabs |
| J1.9.2 | Verify "Paste Content" tab calls `/api/v1/onboarding/analyze-content` | Paste content, submit |
| J1.9.3 | Verify min 100 character validation | Submit short content, verify error |
| J1.9.4 | Verify "Use LinkedIn" tab calls `/api/v1/onboarding/analyze-linkedin` | Enter LinkedIn URL, submit |
| J1.9.5 | Verify LinkedIn URL validation (must contain linkedin.com/company) | Enter invalid URL, verify error |
| J1.9.6 | Verify "Skip" tab calls `/api/v1/onboarding/skip-icp` | Enter company name, skip |
| J1.9.7 | Verify failedUrl preserved from query param | Access with ?url=xxx, verify shown |

**Key Files:**
- `frontend/app/onboarding/manual-entry/page.tsx` (360+ lines - VERIFIED complete)

**Pass Criteria:**
- [ ] All 3 tabs render
- [ ] Paste content validated (min 100 chars)
- [ ] LinkedIn URL validated
- [ ] Skip creates basic profile
- [ ] Failed URL shown to user

<!-- E2E_SESSION_BREAK: J1.9 complete. Next: J1.10 LinkedIn Connection -->

---

### J1.10 — LinkedIn Credential Connection
**Purpose:** Verify LinkedIn connection flow with 2FA support.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.10.1 | Read `frontend/app/onboarding/linkedin/page.tsx` — verify state machine | Load page, verify form |
| J1.10.2 | Verify `useLinkedInConnect` hook calls backend | Enter credentials, submit |
| J1.10.3 | Verify 2FA state triggers `LinkedInTwoFactor` component | If 2FA required, verify code input |
| J1.10.4 | Verify `useLinkedInVerify2FA` hook submits code | Enter 2FA code, submit |
| J1.10.5 | Verify success state shows `LinkedInSuccess` component | After connect, verify success screen |
| J1.10.6 | Verify polling for async connection completion | Check poll interval (2s, max 30 attempts) |
| J1.10.7 | Verify "Skip for now" bypasses connection | Click skip, verify redirect to dashboard |

**Key Files:**
- `frontend/app/onboarding/linkedin/page.tsx` (225 lines - VERIFIED complete)
- `frontend/hooks/use-linkedin.ts`
- `frontend/components/onboarding/LinkedInCredentialForm.tsx`

**Connection States:**
| State | Component | Next Action |
|-------|-----------|-------------|
| form | LinkedInCredentialForm | Submit credentials |
| connecting | LinkedInConnecting | Wait for response |
| 2fa | LinkedInTwoFactor | Enter 2FA code |
| success | LinkedInSuccess | Continue to dashboard |
| error | Error message | Retry or skip |

**Pass Criteria:**
- [ ] Credential form renders
- [ ] Connection attempt triggers backend
- [ ] 2FA handled when required
- [ ] Success displays profile info
- [ ] Skip allows bypass

<!-- E2E_SESSION_BREAK: J1.10 complete. Next: J1.11 Job Tracking -->

---

### J1.11 — ICP Extraction Job Tracking
**Purpose:** Verify extraction job progress is tracked and reported.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.11.1 | Verify `icp_extraction_jobs` table exists | Query table schema |
| J1.11.2 | Verify job created with status='pending' on analyze | Check database after submit |
| J1.11.3 | Verify status updates to 'running' when Prefect starts | Check during extraction |
| J1.11.4 | Verify `completed_steps` and `total_steps` updated | Poll status endpoint |
| J1.11.5 | Verify `extracted_icp` JSONB populated on completion | Query database after complete |
| J1.11.6 | Verify `error_message` populated on failure | Trigger failure, check database |

**Key Files:**
- `src/api/routes/onboarding.py`
- Migration creating `icp_extraction_jobs` table

**Job Status Flow:**
```
pending → running → completed (or failed)
```

**Pass Criteria:**
- [ ] Job record created
- [ ] Progress tracked
- [ ] ICP data saved on success
- [ ] Error captured on failure

<!-- E2E_SESSION_BREAK: J1.11 complete. Next: J1.12 ICP Confirmation -->

---

### J1.12 — ICP Confirmation Flow
**Purpose:** Verify ICP can be confirmed and applied to client.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.12.1 | Verify POST /onboarding/confirm endpoint | Call with job_id |
| J1.12.2 | Verify ICP fields saved to clients table | Query clients table |
| J1.12.3 | Verify `icp_confirmed_at` timestamp set | Check column populated |
| J1.12.4 | Verify pool population Prefect flow triggered | Check Prefect UI |
| J1.12.5 | Verify adjustments can be applied before confirm | Pass adjustments, verify saved |

**Key Files:**
- `src/api/routes/onboarding.py` (confirm_icp function at line 517)

**Fields Updated on Confirm:**
| Column | Source |
|--------|--------|
| website_url | ICP data |
| company_description | ICP data |
| services_offered | ICP data (TEXT[]) |
| icp_industries | ICP data (TEXT[]) |
| icp_company_sizes | ICP data (TEXT[]) |
| icp_locations | ICP data (TEXT[]) |
| icp_titles | ICP data (TEXT[]) |
| icp_pain_points | ICP data (TEXT[]) |
| als_weights | ICP data (JSONB) |
| icp_confirmed_at | NOW() |

**Pass Criteria:**
- [ ] Confirm saves ICP to client
- [ ] All fields populated
- [ ] Pool population triggered
- [ ] Adjustments applied if provided

<!-- E2E_SESSION_BREAK: J1.12 complete. Next: J1.13 Onboarding Completion -->

---

### J1.13 — Onboarding Completion
**Purpose:** Verify onboarding completes and user lands on dashboard.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.13.1 | Verify `icp_confirmed_at` being set marks onboarding complete | Query database |
| J1.13.2 | Verify `get_onboarding_status()` returns `needs_onboarding=false` after confirm | Call RPC |
| J1.13.3 | Verify dashboard loads without redirect loop | Access /dashboard after confirm |
| J1.13.4 | Verify ICP data displayed on dashboard | Check dashboard shows ICP |
| J1.13.5 | Verify activity logged for onboarding completion | Query activities table |

**Pass Criteria:**
- [ ] Onboarding status reflects complete
- [ ] Dashboard accessible
- [ ] No redirect loops
- [ ] ICP visible on dashboard

<!-- E2E_SESSION_BREAK: J1.13 complete. Next: J1.14 Database Schema -->

---

### J1.14 — Database Schema Verification
**Purpose:** Verify all required tables and columns exist.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.14.1 | Verify `users` table has: id, email, full_name | Query schema |
| J1.14.2 | Verify `clients` table has all ICP columns | Query schema |
| J1.14.3 | Verify `memberships` table has: user_id, client_id, role, accepted_at | Query schema |
| J1.14.4 | Verify `icp_extraction_jobs` table exists | Query schema |
| J1.14.5 | Verify `handle_new_user` trigger exists | Query pg_triggers |
| J1.14.6 | Verify `get_onboarding_status` function exists | Call RPC |

**Schema Verification Queries:**
```sql
-- Check users table
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'users';

-- Check trigger exists
SELECT tgname FROM pg_trigger WHERE tgname = 'on_auth_user_created';

-- Check RPC exists
SELECT proname FROM pg_proc WHERE proname = 'get_onboarding_status';
```

**Pass Criteria:**
- [ ] All tables exist
- [ ] All columns exist
- [ ] Trigger exists and active
- [ ] RPC callable

<!-- E2E_SESSION_BREAK: J1.14 complete. Next: J1.15 Edge Cases -->

---

### J1.15 — Edge Cases & Error Handling
**Purpose:** Test failure scenarios and edge cases.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J1.15.1 | Verify session expiry handled | Let session expire, verify redirect to login |
| J1.15.2 | Verify duplicate email rejected | Try signup with existing email |
| J1.15.3 | Verify invalid URL rejected | Submit malformed URL |
| J1.15.4 | Verify extraction timeout handled | Submit slow site, check timeout behavior |
| J1.15.5 | Verify browser refresh preserves job_id | Refresh during extraction, verify continues |
| J1.15.6 | Verify concurrent extractions handled | Submit multiple URLs |
| J1.15.7 | Verify deleted user/client rejected | Delete user, try access |

**Pass Criteria:**
- [ ] Session expiry redirects cleanly
- [ ] Duplicate email shows error
- [ ] Invalid URLs rejected
- [ ] Timeouts handled gracefully
- [ ] Refresh doesn't break flow

<!-- E2E_SESSION_BREAK: J1.15 complete. J1 JOURNEY COMPLETE. Next: J2 Campaign -->

---

## Completion Criteria

All checks must pass before proceeding to J2:

- [ ] **J1.1** Login page works (email + Google OAuth)
- [ ] **J1.2** Signup creates auth user with metadata
- [ ] **J1.3** Auto-provision creates user + client + membership
- [ ] **J1.4** Auth callback routes correctly based on onboarding status
- [ ] **J1.5** Middleware protects routes
- [ ] **J1.6** Onboarding page triggers extraction
- [ ] **J1.7** API endpoints complete and trigger Prefect
- [ ] **J1.8** ICP scraper waterfall implemented
- [ ] **J1.9** Manual fallback handles scraper failures
- [ ] **J1.10** LinkedIn connection with 2FA works
- [ ] **J1.11** Job tracking accurate
- [ ] **J1.12** ICP confirm saves data
- [ ] **J1.13** Onboarding completes successfully
- [ ] **J1.14** Database schema correct
- [ ] **J1.15** Edge cases handled

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Login page | `frontend/app/(auth)/login/page.tsx` | 202 | VERIFIED |
| Signup page | `frontend/app/(auth)/signup/page.tsx` | 173 | VERIFIED |
| Auth callback | `frontend/app/auth/callback/route.ts` | 47 | VERIFIED |
| Middleware | `frontend/middleware.ts` | 53 | VERIFIED |
| Onboarding main | `frontend/app/onboarding/page.tsx` | 160 | VERIFIED |
| Manual entry | `frontend/app/onboarding/manual-entry/page.tsx` | 362 | VERIFIED |
| LinkedIn connect | `frontend/app/onboarding/linkedin/page.tsx` | 225 | VERIFIED |
| Onboarding API | `src/api/routes/onboarding.py` | 774 | VERIFIED |
| ICP scraper | `src/engines/icp_scraper.py` | 1216 | VERIFIED |
| Auto-provision | `supabase/migrations/016_auto_provision_client.sql` | 152 | VERIFIED |

---

## Notes

**CTO Verification:** Each sub-task was created after reading the actual code files. This is not assumption-based - it reflects what's actually implemented.

**TEST_MODE:** J1 does not require TEST_MODE. No outbound messages are sent during onboarding.

**Prefect Flows Used:**
- `icp_onboarding_flow/onboarding-flow` - triggered by /onboarding/analyze
- `pool_population/pool-population-flow` - triggered after ICP confirm

**Observation from Code Review:**
The onboarding flow is more streamlined than originally documented. The main steps are:
1. Website URL input → ICP extraction
2. Optional LinkedIn connection
3. ICP confirmation

CRM connection, sender profile, and customer import are NOT part of the current onboarding flow - they happen later in Settings.
