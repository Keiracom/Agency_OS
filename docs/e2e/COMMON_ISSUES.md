# Common Issues & Fixes — E2E Testing

**Purpose:** Quick reference for common failure patterns and their fixes
**Source:** Extracted from skills/testing/E2E_TESTING_SKILL.md (Jan 11, 2026)

---

## Category 1: Authentication

### Problem: Auth callback redirect loop
```
Symptoms: Page refreshes endlessly after email confirmation
Root cause: Session not set or client record not found
Fix: Check auth callback error handling
File: frontend/app/auth/callback/route.ts
```

### Problem: Client not auto-provisioned
```
Symptoms: Dashboard shows "No client found"
Root cause: Trigger not firing on auth.users insert
Fix: Verify trigger exists and function works
File: supabase/migrations/016_auto_provision_client.sql
```

### Problem: 401 Unauthorized
```
Symptoms: API returns 401, user is logged in
Root cause: JWT not sent or expired
Fix: Check Authorization header, refresh token logic
File: frontend/lib/api.ts
```

---

## Category 2: ICP Extraction

### Problem: JSON parsing error
```
Symptoms: "Failed to parse JSON response"
Root cause: Claude returns markdown-wrapped JSON
Fix: Strip ```json fences before parsing
File: src/agents/skills/website_parser.py
```

### Problem: Empty ICP extraction
```
Symptoms: Extraction returns nothing, no error
Root cause: Cloudflare blocking, waterfall not progressing
Fix: Check scraper logs, verify waterfall fallthrough
File: src/engines/icp_scraper.py
```

### Problem: Scraper timeout
```
Symptoms: ICP extraction takes > 60s
Root cause: All tiers failing, stuck on retry
Fix: Check Apify credits, verify proxy config for Camoufox
File: src/integrations/apify.py, src/integrations/camoufox_scraper.py
```

---

## Category 3: API Errors

### Problem: CORS error
```
Symptoms: Browser console shows Access-Control-Allow-Origin error
Root cause: Backend CORS not configured for frontend URL
Fix: Add frontend URL to CORS origins
File: src/main.py
```

### Problem: 404 on endpoint
```
Symptoms: API returns 404
Root cause: Route not registered
Fix: Check routes/__init__.py includes the route file
File: src/api/routes/__init__.py
```

### Problem: 500 on API call
```
Symptoms: Internal server error
Root cause: Various - check logs
Fix: Check Railway logs with `railway logs --service agency-os`
```

---

## Category 4: Database

### Problem: RLS policy blocking
```
Symptoms: Query returns empty when data exists
Root cause: RLS policy too restrictive
Fix: Check policy uses auth.uid() correctly
File: supabase/migrations/*.sql
```

### Problem: Missing columns
```
Symptoms: Column not found error
Root cause: Migration not applied
Fix: Run migrations in Supabase Dashboard
```

### Problem: Foreign key constraint
```
Symptoms: Insert fails with FK violation
Root cause: Referenced record doesn't exist
Fix: Ensure parent record created first
```

---

## Category 5: Outreach (J3)

### Problem: Emails not redirected in TEST_MODE
```
Symptoms: Real leads receive emails during testing
Root cause: TEST_MODE not set or engine not checking
Fix: Verify TEST_MODE=true in Railway, check engine redirect logic
File: src/engines/email.py (check for settings.TEST_MODE)
```

### Problem: SMS fails
```
Symptoms: No SMS received
Root cause: Twilio credentials or phone format
Fix: Check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, phone format (+61...)
File: src/integrations/twilio.py
```

### Problem: Voice call not triggered
```
Symptoms: No phone call received
Root cause: Vapi configuration
Fix: Check VAPI_API_KEY, voice agent ID
File: src/integrations/vapi.py
```

---

## Category 6: Infrastructure

### Problem: Prefect going to Cloud instead of self-hosted
```
Symptoms: Flows run but don't appear in self-hosted Prefect UI
Root cause: PREFECT_API_URL not set or wrong
Fix: Set PREFECT_API_URL=https://prefect-server-production-f9b1.up.railway.app/api
File: Railway environment variables
```

### Problem: Database connection timeout
```
Symptoms: Slow or failed DB queries
Root cause: Wrong port or pool exhaustion
Fix: Use port 6543 (Transaction Pooler), check pool settings
File: src/config/settings.py
```

### Problem: Redis connection failed
```
Symptoms: Cache operations fail
Root cause: Upstash credentials wrong
Fix: Check UPSTASH_REDIS_URL
File: src/integrations/redis.py
```

---

## Diagnosis Commands

### Check backend health
```bash
curl https://agency-os-production.up.railway.app/api/v1/health
```

### Check Railway logs
```bash
railway logs --service agency-os -n 100
```

### Check Prefect logs
```bash
railway logs --service prefect-worker -n 100
```

### Query database directly
```sql
-- Check if client exists
SELECT id, email, onboarding_completed FROM clients WHERE email = 'TEST_EMAIL';

-- Check campaign status
SELECT id, name, status FROM campaigns WHERE id = 'CAMPAIGN_ID';

-- Check activity log
SELECT channel, status, COUNT(*) FROM activities
WHERE campaign_id = 'CAMPAIGN_ID' GROUP BY channel, status;
```

---

## Escalation Triggers

Stop and ask CEO when:

1. **Database schema change needed** — Migration affects production
2. **Credentials missing** — Need API key or secret
3. **Third-party down** — Supabase, Apollo, etc. not responding
4. **Unclear requirement** — Test expectation ambiguous
5. **Breaking change risk** — Fix might affect other features
6. **About to run J3/J4** — Confirm TEST_MODE is deployed and working
