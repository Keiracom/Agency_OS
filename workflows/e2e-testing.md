# SOP: E2E Testing

**Role:** Tester  
**Trigger:** Journey needs validation  
**Time estimate:** 1-4 hours per journey

---

## Overview

End-to-end testing validates complete user journeys through Agency OS. Each journey (J0-J6) represents a critical user flow.

---

## Journeys

| ID | Journey | Description |
|----|---------|-------------|
| J0 | Signup | New user registration and onboarding |
| J1 | Lead Import | Importing leads from various sources |
| J2 | Campaign Create | Creating a multi-channel campaign |
| J3 | Outreach | Executing outreach (email, SMS, LinkedIn, voice) |
| J4 | Response Handling | Processing replies and lead responses |
| J5 | Analytics | Viewing campaign performance and ALS scores |
| J6 | Billing | Subscription and payment flows |

---

## Pre-flight Checklist

- [ ] Backend is running (Railway or local)
- [ ] Frontend is accessible (Vercel or local)
- [ ] Database has test data
- [ ] API keys configured for integrations being tested
- [ ] You have credentials for a test account

---

## Procedure

### 1. Prepare Test Environment

```bash
# Check services are up
curl https://[backend-url]/health

# Verify test account exists
# (check Supabase or create one)
```

### 2. Execute Journey

For each step in the journey:

1. **Document the action** — What are you doing?
2. **Capture the request** — API call or UI action
3. **Record the response** — What happened?
4. **Verify the outcome** — Did it work correctly?
5. **Screenshot if UI** — Evidence of state

### 3. Log Results

Create a test report:

```markdown
# Journey [X] Test Report

**Date:** YYYY-MM-DD
**Tester:** [agent]
**Environment:** [production/staging/local]

## Steps

### Step 1: [Name]
- Action: [what was done]
- Expected: [what should happen]
- Actual: [what did happen]
- Status: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL

[screenshot or evidence]

### Step 2: ...
```

### 4. File Issues

For any failures:

```bash
gh issue create \
  --title "E2E: [Journey] - [Step] fails" \
  --body "## Description
[What went wrong]

## Steps to Reproduce
1. ...

## Expected
[What should happen]

## Actual
[What happened]

## Evidence
[Screenshots, logs]"
```

---

## Output

- [ ] Test report for the journey
- [ ] Issues filed for any failures
- [ ] Journey status updated in BACKLOG.md
- [ ] Summary reported to main session

---

## Integration Testing Notes

### Email (Salesforge)
- Use test domains
- Check delivery in Salesforge dashboard
- Verify tracking works

### SMS (Twilio)
- Use test phone numbers
- Check message delivery status
- Verify opt-out handling

### LinkedIn (HeyReach/Unipile)
- Use test accounts
- Respect rate limits
- Check weekend rules

### Voice (Vapi)
- Use test phone numbers
- Record call outcomes
- Verify KB retrieval

---

## Escalation

If you encounter:
- Infrastructure issues → check Railway/Vercel status
- API errors → check integration credentials
- Data issues → check Supabase
- Logic bugs → file issue and escalate to Builder
