# Claude Code Prompt: Execute Outreach Test (Email, SMS, Voice)

**Phase:** Final E2E Validation  
**Prerequisites:** All bugs fixed, TEST_MODE verified  
**Goal:** Dave receives real emails, SMS, and phone call

---

## ⚠️ PRE-FLIGHT CHECKLIST

**STOP! Before running ANY outreach:**

- [ ] Bug 1 deployed (User model `is_platform_admin`)
- [ ] Bug 2 deployed (Pool population working)
- [ ] Bug 3 deployed (Lead enrichment working)
- [ ] Bug 4 deployed (Campaign counter working)
- [ ] `TEST_MODE=true` in Railway
- [ ] `TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com` in Railway
- [ ] `TEST_SMS_RECIPIENT=+61457543392` in Railway
- [ ] `TEST_VOICE_RECIPIENT=+61457543392` in Railway
- [ ] Leads exist in campaign (minimum 10)
- [ ] Leads have ALS scores

**If ANY of these are not confirmed, STOP and fix first.**

---

## 🔍 VERIFY TEST_MODE IS ACTIVE

### Check Railway Environment
```bash
# Use Railway MCP or CLI
railway variables | grep TEST_MODE

# Must show:
# TEST_MODE=true
```

### Check Backend Config
```bash
curl "https://agency-os-production.up.railway.app/api/v1/health" | jq '.config.test_mode // "not exposed"'
```

### Verify Redirect Logic in Code
```bash
# Each engine should have redirect:
grep -A 5 "TEST_MODE" src/engines/email.py
grep -A 5 "TEST_MODE" src/engines/sms.py
grep -A 5 "TEST_MODE" src/engines/voice.py
```

**Expected pattern:**
```python
if settings.TEST_MODE:
    recipient = settings.TEST_EMAIL_RECIPIENT  # or SMS/VOICE
    logger.info(f"TEST_MODE: Redirecting to {recipient}")
```

---

## 📧 PHASE 1: EMAIL OUTREACH TEST

### Goal
Dave receives 3 personalized cold emails at `david.stephens@keiracom.com`

### Execute

```bash
# Use existing test credentials from E2E test
export ACCESS_TOKEN="<from previous test>"
export CLIENT_ID="<from previous test>"
export CAMPAIGN_ID="<from previous test>"
export API_BASE="https://agency-os-production.up.railway.app/api/v1"

# 1. Verify leads exist
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/leads?limit=5" | jq '.leads | length'

# Should be >= 5 leads

# 2. Generate email content (if not already done)
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/generate-content" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channels": ["email"], "limit": 5}'

# 3. Send 3 test emails
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channel": "email", "limit": 3}'
```

### What to Check
```bash
# Check activities were logged
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/activities?channel=email&limit=5" | jq '.activities[] | {to, subject, status, created_at}'

# In database:
# SELECT * FROM activities WHERE campaign_id = '${CAMPAIGN_ID}' AND channel = 'email' ORDER BY created_at DESC LIMIT 5;
```

### Dave's Verification
- [ ] Received 3 emails at `david.stephens@keiracom.com`
- [ ] Emails are personalized (lead name, company mentioned)
- [ ] Subject lines are compelling
- [ ] Body copy quality is good
- [ ] Icebreakers make sense

---

## 📱 PHASE 2: SMS OUTREACH TEST

### Goal
Dave receives 2 SMS messages at `+61457543392`

### Execute

```bash
# 1. Generate SMS content
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/generate-content" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channels": ["sms"], "limit": 3}'

# 2. Send 2 test SMS
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channel": "sms", "limit": 2}'
```

### What to Check
```bash
# Check activities
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/activities?channel=sms&limit=3" | jq '.activities[] | {to, message, status}'

# Check Twilio logs if available
```

### Dave's Verification
- [ ] Received 2 SMS at `+61457543392`
- [ ] Messages are short and compelling
- [ ] CTA is clear
- [ ] Looks professional

---

## 📞 PHASE 3: VOICE OUTREACH TEST

### Goal
Dave receives 1 AI phone call at `+61457543392`

⚠️ **This will trigger a REAL phone call!**

### Execute

```bash
# 1. Generate voice script
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/generate-content" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channels": ["voice"], "limit": 2}'

# 2. Trigger 1 voice call
echo "📞 CALLING NOW - Answer your phone!"
curl -X POST "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/send" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"channel": "voice", "limit": 1}'
```

### What to Check
```bash
# Check activity logged
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/activities?channel=voice&limit=2" | jq '.activities[] | {to, status, duration}'

# Check Vapi logs if available
```

### Dave's Verification
- [ ] Received phone call at `+61457543392`
- [ ] AI voice sounds natural
- [ ] Script makes sense
- [ ] Handles objections well (if tested)

---

## 📊 PHASE 4: VERIFY ALL ACTIVITIES LOGGED

```bash
# Get all activities for campaign
curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "${API_BASE}/clients/${CLIENT_ID}/campaigns/${CAMPAIGN_ID}/activities" | jq '{
    total: .total,
    by_channel: .activities | group_by(.channel) | map({channel: .[0].channel, count: length})
  }'
```

### Expected Output
```json
{
  "total": 6,
  "by_channel": [
    {"channel": "email", "count": 3},
    {"channel": "sms", "count": 2},
    {"channel": "voice", "count": 1}
  ]
}
```

---

## ✅ SUCCESS CRITERIA

| Channel | Sent | Received | Quality |
|---------|------|----------|---------|
| Email | 3 | ✅ 3 | Dave rates content |
| SMS | 2 | ✅ 2 | Dave rates content |
| Voice | 1 | ✅ 1 | Dave rates voice quality |

### Database Verification
```sql
-- Run via Supabase MCP

-- Activities logged
SELECT channel, status, COUNT(*) 
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}' 
GROUP BY channel, status;

-- Should show:
-- email | sent | 3
-- sms   | sent | 2  
-- voice | sent | 1

-- All redirected to test recipients
SELECT to_email, to_phone, COUNT(*) 
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}' 
GROUP BY to_email, to_phone;

-- Should show test recipients, NOT real lead contacts
```

---

## 🐛 TROUBLESHOOTING

### Emails Not Arriving
1. Check spam folder
2. Check Resend dashboard for delivery status
3. Check activity status in database
4. Verify TEST_EMAIL_RECIPIENT is correct

### SMS Not Arriving
1. Check Twilio dashboard for delivery status
2. Verify phone number format (+61...)
3. Check activity status in database
4. Verify TEST_SMS_RECIPIENT is correct

### Voice Call Not Coming
1. Check Vapi dashboard for call status
2. Ensure phone is on and not on DND
3. Check activity status in database
4. Verify TEST_VOICE_RECIPIENT is correct
5. Check if Twilio phone number is linked to Vapi

---

## 📝 REPORT TEMPLATE

After all tests complete, document:

```markdown
# E2E Outreach Test Report

**Date:** [DATE]
**Test Run ID:** [ID]

## Summary

| Channel | Attempted | Delivered | Quality Rating (1-10) |
|---------|-----------|-----------|----------------------|
| Email | 3 | [X] | [X] |
| SMS | 2 | [X] | [X] |
| Voice | 1 | [X] | [X] |

## Email Quality Notes
- Subject lines: [Good/Needs work]
- Personalization: [Good/Needs work]
- CTA: [Good/Needs work]
- Sample: "[paste best email]"

## SMS Quality Notes
- Length: [Appropriate/Too long]
- CTA: [Clear/Unclear]
- Sample: "[paste SMS]"

## Voice Quality Notes
- Voice naturalness: [Natural/Robotic]
- Script flow: [Smooth/Awkward]
- Objection handling: [Tested/Not tested]

## Issues Found
1. [Issue]
2. [Issue]

## Recommendations
1. [Recommendation]
2. [Recommendation]

## Verdict
[ ] PASS - Ready for launch
[ ] FAIL - Needs fixes before launch
```

---

## 🎉 AFTER SUCCESS

If all outreach tests pass:

1. **Update PROGRESS.md** with test results
2. **Document in `docs/audits/`** 
3. **Notify Dave** with summary
4. **Keep TEST_MODE=true** until ready for real launch
5. **Plan launch date** (after mailbox warmup completes Jan 20)

**Next steps for launch:**
- Disable TEST_MODE
- Create first real client (Umped)
- Start first real campaign
- Monitor deliverability
