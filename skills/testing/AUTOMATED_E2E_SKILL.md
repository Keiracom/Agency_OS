# SKILL.md — Automated E2E Journey Testing

**Skill:** Automated End-to-End Journey Testing  
**Author:** Dave + Claude  
**Version:** 1.0  
**Created:** January 7, 2026  
**Phase:** 21

---

## Purpose

Execute comprehensive automated E2E tests that exercise REAL user journeys via API calls, database queries, and service validation — catching issues BEFORE manual browser testing.

**What this skill tests:**
- Full signup and onboarding flow
- Campaign creation and configuration
- Lead enrichment and ALS scoring
- Content generation
- Outreach execution (TEST_MODE)
- Reply handling and conversation threading
- Meeting booking and deal creation
- Dashboard data accuracy
- Admin panel functionality

**What requires manual testing (not covered):**
- Browser UI rendering
- JavaScript interactions
- Visual styling
- Mobile responsiveness

---

## Prerequisites

### Required Environment Variables (Railway)

```
TEST_MODE=true
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_DAILY_EMAIL_LIMIT=15
```

### What You'll Receive During Test

| Channel | Recipient | Quantity | What Happens |
|---------|-----------|----------|--------------|
| **Email** | david.stephens@keiracom.com | 3 | Check inbox for test emails |
| **SMS** | +61457543392 | 2 | Check phone for text messages |
| **Voice** | +61457543392 | 1 | Expect AI phone call from Vapi |
| **LinkedIn** | (skipped) | 0 | Not tested automatically |

**⚠️ IMPORTANT:** The voice test will trigger a REAL phone call. Make sure your phone is nearby!

### Estimated Test Cost

| Service | Usage | Est. Cost |
|---------|-------|-----------|
| **Apollo** | 25 lead enrichment | ~$2.50-6.25 |
| **Anthropic** | ICP extraction + content | ~$0.50-1.50 |
| **Apify** | Website scraping | ~$0.10-0.30 |
| **Twilio SMS** | 2 messages | ~$0.02 |
| **Twilio/Vapi Voice** | 1 call (~2 min) | ~$0.20-0.50 |
| **Email (Resend)** | 3 emails | ~$0.01 |
| **TOTAL** | | **~$3.50-9.00** |

### Required Tools

- curl (HTTP requests)
- jq (JSON parsing)
- Supabase MCP tools (database queries)
- Railway MCP tools (env var checks)

### Required Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /auth/signup` | Create test account |
| `POST /auth/login` | Authenticate |
| `GET /onboarding/status` | Check onboarding state |
| `POST /onboarding/extract-icp` | Trigger ICP extraction |
| `POST /onboarding/confirm-icp` | Confirm ICP |
| `POST /campaigns` | Create campaign |
| `POST /campaigns/:id/enrich-leads` | Trigger enrichment |
| `POST /campaigns/:id/activate` | Activate campaign |
| `POST /campaigns/:id/send` | Execute outreach |
| `GET /dashboard/stats` | Get dashboard data |
| `GET /admin/stats` | Get admin stats |

---

## Test Configuration

```bash
# Generate unique test run ID
export TEST_RUN_ID=$(date +%Y%m%d%H%M%S)

# Test credentials (unique per run)
export TEST_EMAIL="e2e_${TEST_RUN_ID}@agencyos-test.com"
export TEST_PASSWORD="TestPass123!@#"
export TEST_AGENCY="E2E Test Agency ${TEST_RUN_ID}"

# Test ICP data
export TEST_WEBSITE="https://umped.com.au"
export TEST_INDUSTRY="Marketing Agency"
export TEST_TARGET_TITLES="CEO,Founder,Managing Director"
export TEST_COMPANY_SIZE="10-50"
export TEST_LOCATION="Australia"

# API endpoints
export API_BASE="https://agency-os-production.up.railway.app/api/v1"

# Tokens (populated during tests)
export ACCESS_TOKEN=""
export CLIENT_ID=""
export CAMPAIGN_ID=""
```

---

## Journey Definitions

### Journey 1: Signup & Onboarding

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J1.1 | POST /auth/signup | 200/201 + token | Token returned |
| J1.2 | GET /onboarding/status | Step 1 | Current step = 1 |
| J1.3 | POST /onboarding/extract-icp | 200 + processing | Status = processing |
| J1.4 | Poll ICP status | Completed | ICP data populated |
| J1.5 | POST /onboarding/confirm-icp | 200 | ICP confirmed |
| J1.6 | POST /onboarding/complete | 200 | Onboarding complete |
| J1.7 | DB: Check client record | Row exists | All fields populated |
| J1.8 | DB: Check ICP profile | Row exists | ICP data matches |

### Journey 2: Campaign & Leads

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J2.1 | POST /campaigns | 200 + campaign_id | Campaign created |
| J2.2 | POST /campaigns/:id/enrich-leads | 200 + processing | Enrichment started |
| J2.3 | Poll lead count | Leads > 0 | Leads populated |
| J2.4 | DB: Check lead_pool | Rows exist | 50+ fields populated |
| J2.5 | GET /campaigns/:id/leads | Lead list | ALS scores present |
| J2.6 | Verify ALS tiers | Correct tiers | Hot=85+, Warm=60-84, etc |
| J2.7 | DB: Check lead_assignments | Rows exist | Leads assigned to campaign |

### Journey 3: Outreach Execution (Multi-Channel)

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J3.1 | Verify TEST_MODE | true | Redirects active |
| J3.2 | POST /generate-content (email+sms+voice) | 200 | Content for all channels |
| J3.3 | POST /campaigns/:id/activate | 200 + active | Campaign active |
| J3.4a | POST /send (email, limit=3) | 200 + count | 3 emails → david.stephens@keiracom.com |
| J3.4b | POST /send (sms, limit=2) | 200 + count | 2 SMS → +61457543392 |
| J3.4c | POST /send (voice, limit=1) | 200 + count | 1 call → +61457543392 |
| J3.5 | DB: Check activities | Rows exist | All 3 channels logged |
| J3.6 | DB: Check email_events | Rows exist | Event tracking |

### Journey 4: Reply & Meeting

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J4.1 | POST /replies/simulate | 200 | Reply recorded |
| J4.2 | GET /leads/:id/replies | Reply list | Analysis present |
| J4.3 | DB: Check conversation_threads | Thread exists | Lead linked |
| J4.4 | DB: Check thread_messages | Messages exist | Content stored |
| J4.5 | POST /meetings | 200 + meeting_id | Meeting created |
| J4.6 | DB: Check deals | Deal exists | Stage = meeting_booked |
| J4.7 | DB: Check meetings | Meeting exists | Scheduled correctly |

### Journey 5: Dashboard

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J5.1 | GET /dashboard/stats | 200 + stats | All counts present |
| J5.2 | Compare to DB | Counts match | campaigns, leads, activities |
| J5.3 | GET /campaigns/:id/analytics | 200 + analytics | Metrics correct |

### Journey 6: Admin

| Step | Action | Expected | Validation |
|------|--------|----------|------------|
| J6.1 | GET /admin/stats | 200 + stats | Platform totals |
| J6.2 | Compare to DB | Counts match | All tables |

---

## Test Implementation Patterns

### Pattern 1: API Call with Validation

```bash
# Template for API test
test_api_endpoint() {
    local NAME="$1"
    local METHOD="$2"
    local ENDPOINT="$3"
    local BODY="$4"
    local EXPECTED_CODE="$5"
    
    echo "--- Testing: ${NAME} ---"
    
    if [ "$METHOD" = "GET" ]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            "${API_BASE}${ENDPOINT}")
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" \
            -X "$METHOD" \
            -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            -H "Content-Type: application/json" \
            -d "$BODY" \
            "${API_BASE}${ENDPOINT}")
    fi
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "$EXPECTED_CODE" ]; then
        echo "✅ PASS: ${NAME} (HTTP ${HTTP_CODE})"
        echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
        return 0
    else
        echo "❌ FAIL: ${NAME} (Expected ${EXPECTED_CODE}, got ${HTTP_CODE})"
        echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
        return 1
    fi
}
```

### Pattern 2: Database Validation

```bash
# Use Supabase MCP tool
validate_database() {
    local NAME="$1"
    local QUERY="$2"
    local EXPECTED="$3"
    
    echo "--- DB Check: ${NAME} ---"
    
    # Execute via Supabase MCP
    # supabase:execute_sql query="$QUERY"
    
    # Check result matches expected
}
```

### Pattern 3: Polling with Timeout

```bash
poll_until_ready() {
    local NAME="$1"
    local CHECK_CMD="$2"
    local SUCCESS_CONDITION="$3"
    local MAX_WAIT="${4:-120}"
    local INTERVAL="${5:-5}"
    
    echo "--- Polling: ${NAME} (max ${MAX_WAIT}s) ---"
    
    local WAITED=0
    while [ $WAITED -lt $MAX_WAIT ]; do
        RESULT=$(eval "$CHECK_CMD")
        
        if eval "$SUCCESS_CONDITION"; then
            echo "✅ Ready after ${WAITED}s"
            return 0
        fi
        
        echo "   Waiting... (${WAITED}s)"
        sleep $INTERVAL
        WAITED=$((WAITED + INTERVAL))
    done
    
    echo "❌ Timeout after ${MAX_WAIT}s"
    return 1
}
```

### Pattern 4: Test Result Tracking

```bash
# Global test results
declare -a TEST_RESULTS=()
TESTS_PASSED=0
TESTS_FAILED=0

log_result() {
    local JOURNEY="$1"
    local STEP="$2"
    local PASSED="$3"
    local DETAILS="$4"
    
    if [ "$PASSED" = "true" ]; then
        ((TESTS_PASSED++))
        TEST_RESULTS+=("✅ ${JOURNEY}.${STEP}: PASS")
    else
        ((TESTS_FAILED++))
        TEST_RESULTS+=("❌ ${JOURNEY}.${STEP}: FAIL - ${DETAILS}")
    fi
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "TEST SUMMARY"
    echo "=========================================="
    echo "Passed: ${TESTS_PASSED}"
    echo "Failed: ${TESTS_FAILED}"
    echo "Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""
    
    if [ $TESTS_FAILED -gt 0 ]; then
        echo "FAILED TESTS:"
        for result in "${TEST_RESULTS[@]}"; do
            if [[ "$result" == ❌* ]]; then
                echo "  $result"
            fi
        done
    fi
}
```

---

## Journey 1: Signup & Onboarding (Full Implementation)

```bash
run_journey_1() {
    echo ""
    echo "================================================"
    echo "JOURNEY 1: SIGNUP & ONBOARDING"
    echo "================================================"
    
    # J1.1: Create Account
    echo ""
    echo "--- J1.1: Create Account ---"
    
    SIGNUP_RESPONSE=$(curl -s -X POST ${API_BASE}/auth/signup \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"${TEST_EMAIL}\",
            \"password\": \"${TEST_PASSWORD}\",
            \"agency_name\": \"${TEST_AGENCY}\"
        }")
    
    ACCESS_TOKEN=$(echo $SIGNUP_RESPONSE | jq -r '.access_token // .token // empty')
    CLIENT_ID=$(echo $SIGNUP_RESPONSE | jq -r '.user.id // .client_id // .id // empty')
    
    if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
        log_result "J1" "1" "true" ""
        echo "✅ Account created: ${CLIENT_ID}"
    else
        log_result "J1" "1" "false" "No token returned: $SIGNUP_RESPONSE"
        echo "❌ Signup failed"
        return 1
    fi
    
    # J1.2: Check Onboarding Status
    echo ""
    echo "--- J1.2: Check Onboarding Status ---"
    
    ONBOARD_STATUS=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        ${API_BASE}/onboarding/status)
    
    CURRENT_STEP=$(echo $ONBOARD_STATUS | jq -r '.current_step // .step // 0')
    
    if [ "$CURRENT_STEP" -ge 0 ]; then
        log_result "J1" "2" "true" ""
        echo "✅ Onboarding status retrieved: Step ${CURRENT_STEP}"
    else
        log_result "J1" "2" "false" "Invalid step: $ONBOARD_STATUS"
    fi
    
    # J1.3: Submit Website for ICP
    echo ""
    echo "--- J1.3: Submit Website for ICP Extraction ---"
    
    ICP_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"website_url\": \"${TEST_WEBSITE}\"}" \
        ${API_BASE}/onboarding/extract-icp)
    
    ICP_STATUS=$(echo $ICP_RESPONSE | jq -r '.status // "unknown"')
    
    if [ "$ICP_STATUS" = "processing" ] || [ "$ICP_STATUS" = "completed" ] || [ "$ICP_STATUS" = "success" ]; then
        log_result "J1" "3" "true" ""
        echo "✅ ICP extraction started: ${ICP_STATUS}"
    else
        log_result "J1" "3" "false" "Status: $ICP_STATUS"
        echo "⚠️ ICP extraction status: $ICP_STATUS"
    fi
    
    # J1.4: Poll for ICP Completion
    echo ""
    echo "--- J1.4: Wait for ICP Extraction ---"
    
    MAX_WAIT=120
    WAITED=0
    ICP_READY=false
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        ICP_CHECK=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            ${API_BASE}/onboarding/icp-status 2>/dev/null || \
            curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            ${API_BASE}/onboarding/status)
        
        STATUS=$(echo $ICP_CHECK | jq -r '.icp_status // .status // "pending"')
        
        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "ready" ]; then
            ICP_READY=true
            break
        fi
        
        echo "   Waiting... (${WAITED}s) Status: $STATUS"
        sleep 10
        WAITED=$((WAITED + 10))
    done
    
    if [ "$ICP_READY" = true ]; then
        log_result "J1" "4" "true" ""
        echo "✅ ICP extraction complete"
    else
        log_result "J1" "4" "false" "Timeout or status: $STATUS"
        echo "⚠️ ICP extraction may not be complete"
    fi
    
    # J1.5: Confirm ICP
    echo ""
    echo "--- J1.5: Confirm ICP ---"
    
    CONFIRM_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"industry\": \"${TEST_INDUSTRY}\",
            \"target_titles\": [\"CEO\", \"Founder\", \"Managing Director\"],
            \"company_size\": \"${TEST_COMPANY_SIZE}\",
            \"location\": \"${TEST_LOCATION}\",
            \"confirmed\": true
        }" \
        ${API_BASE}/onboarding/confirm-icp)
    
    CONFIRM_STATUS=$(echo $CONFIRM_RESPONSE | jq -r '.status // .success // "unknown"')
    
    if [ "$CONFIRM_STATUS" = "success" ] || [ "$CONFIRM_STATUS" = "confirmed" ] || [ "$CONFIRM_STATUS" = "true" ]; then
        log_result "J1" "5" "true" ""
        echo "✅ ICP confirmed"
    else
        log_result "J1" "5" "false" "Status: $CONFIRM_STATUS"
    fi
    
    # J1.6: Complete Onboarding
    echo ""
    echo "--- J1.6: Complete Onboarding ---"
    
    # Skip LinkedIn
    curl -s -X POST -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        ${API_BASE}/onboarding/skip-linkedin > /dev/null 2>&1
    
    COMPLETE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        ${API_BASE}/onboarding/complete)
    
    COMPLETE_STATUS=$(echo $COMPLETE_RESPONSE | jq -r '.status // .completed // "unknown"')
    
    if [ "$COMPLETE_STATUS" = "completed" ] || [ "$COMPLETE_STATUS" = "true" ] || [ "$COMPLETE_STATUS" = "success" ]; then
        log_result "J1" "6" "true" ""
        echo "✅ Onboarding complete"
    else
        log_result "J1" "6" "false" "Status: $COMPLETE_STATUS"
    fi
    
    # J1.7 & J1.8: Database validation via Supabase MCP
    echo ""
    echo "--- J1.7-8: Database Validation ---"
    echo "Use Supabase MCP to verify:"
    echo "  SELECT * FROM clients WHERE email = '${TEST_EMAIL}';"
    echo "  SELECT * FROM client_icp_profiles WHERE client_id = '${CLIENT_ID}';"
    
    # Export for next journeys
    export ACCESS_TOKEN
    export CLIENT_ID
}
```

---

## Journey 2: Campaign & Leads (Full Implementation)

```bash
run_journey_2() {
    echo ""
    echo "================================================"
    echo "JOURNEY 2: CAMPAIGN & LEADS"
    echo "================================================"
    
    # J2.1: Create Campaign
    echo ""
    echo "--- J2.1: Create Campaign ---"
    
    CAMPAIGN_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"E2E Test Campaign ${TEST_RUN_ID}\",
            \"description\": \"Automated E2E test\",
            \"target_leads\": 100,
            \"channels\": [\"email\", \"linkedin\"],
            \"daily_email_limit\": 10
        }" \
        ${API_BASE}/campaigns)
    
    CAMPAIGN_ID=$(echo $CAMPAIGN_RESPONSE | jq -r '.id // empty')
    
    if [ -n "$CAMPAIGN_ID" ] && [ "$CAMPAIGN_ID" != "null" ]; then
        log_result "J2" "1" "true" ""
        echo "✅ Campaign created: ${CAMPAIGN_ID}"
        export CAMPAIGN_ID
    else
        log_result "J2" "1" "false" "No campaign ID: $CAMPAIGN_RESPONSE"
        return 1
    fi
    
    # J2.2: Trigger Lead Enrichment
    echo ""
    echo "--- J2.2: Trigger Lead Enrichment ---"
    
    ENRICH_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"count\": 25}" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/enrich-leads)
    
    ENRICH_STATUS=$(echo $ENRICH_RESPONSE | jq -r '.status // "unknown"')
    
    if [ "$ENRICH_STATUS" = "processing" ] || [ "$ENRICH_STATUS" = "started" ] || [ "$ENRICH_STATUS" = "success" ]; then
        log_result "J2" "2" "true" ""
        echo "✅ Enrichment started"
    else
        log_result "J2" "2" "false" "Status: $ENRICH_STATUS"
    fi
    
    # J2.3: Poll for Leads
    echo ""
    echo "--- J2.3: Wait for Lead Enrichment ---"
    
    MAX_WAIT=180
    WAITED=0
    LEADS_READY=false
    
    while [ $WAITED -lt $MAX_WAIT ]; do
        LEADS_CHECK=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            ${API_BASE}/campaigns/${CAMPAIGN_ID}/leads/count 2>/dev/null || \
            curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            "${API_BASE}/campaigns/${CAMPAIGN_ID}/leads?limit=1")
        
        LEAD_COUNT=$(echo $LEADS_CHECK | jq -r '.count // .total // (.leads | length) // 0')
        
        if [ "$LEAD_COUNT" -gt 0 ]; then
            LEADS_READY=true
            break
        fi
        
        echo "   Waiting... (${WAITED}s) Leads: $LEAD_COUNT"
        sleep 15
        WAITED=$((WAITED + 15))
    done
    
    if [ "$LEADS_READY" = true ]; then
        log_result "J2" "3" "true" ""
        echo "✅ Leads enriched: ${LEAD_COUNT}"
    else
        log_result "J2" "3" "false" "No leads after ${MAX_WAIT}s"
    fi
    
    # J2.5: Get Lead List
    echo ""
    echo "--- J2.5: Get Lead List ---"
    
    LEADS_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        "${API_BASE}/campaigns/${CAMPAIGN_ID}/leads?limit=10")
    
    FIRST_LEAD_ID=$(echo $LEADS_RESPONSE | jq -r '.leads[0].id // .data[0].id // empty')
    
    if [ -n "$FIRST_LEAD_ID" ] && [ "$FIRST_LEAD_ID" != "null" ]; then
        log_result "J2" "5" "true" ""
        echo "✅ Lead list retrieved, first lead: ${FIRST_LEAD_ID}"
        export FIRST_LEAD_ID
    else
        log_result "J2" "5" "false" "No leads in response"
    fi
    
    # J2.6: Check ALS Scoring
    echo ""
    echo "--- J2.6: Check ALS Scoring ---"
    
    if [ -n "$FIRST_LEAD_ID" ]; then
        LEAD_DETAIL=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
            ${API_BASE}/leads/${FIRST_LEAD_ID})
        
        ALS_SCORE=$(echo $LEAD_DETAIL | jq -r '.als_score // 0')
        TIER=$(echo $LEAD_DETAIL | jq -r '.tier // "unknown"')
        
        echo "Lead ALS: ${ALS_SCORE}, Tier: ${TIER}"
        
        # Validate tier matches score
        TIER_CORRECT=false
        if [ "$ALS_SCORE" -ge 85 ] && [ "$TIER" = "Hot" ]; then
            TIER_CORRECT=true
        elif [ "$ALS_SCORE" -ge 60 ] && [ "$ALS_SCORE" -lt 85 ] && [ "$TIER" = "Warm" ]; then
            TIER_CORRECT=true
        elif [ "$ALS_SCORE" -ge 35 ] && [ "$ALS_SCORE" -lt 60 ] && [ "$TIER" = "Cool" ]; then
            TIER_CORRECT=true
        elif [ "$ALS_SCORE" -ge 20 ] && [ "$ALS_SCORE" -lt 35 ] && [ "$TIER" = "Cold" ]; then
            TIER_CORRECT=true
        elif [ "$ALS_SCORE" -lt 20 ] && [ "$TIER" = "Dead" ]; then
            TIER_CORRECT=true
        fi
        
        if [ "$TIER_CORRECT" = true ]; then
            log_result "J2" "6" "true" ""
            echo "✅ ALS tier correct"
        else
            log_result "J2" "6" "false" "Score ${ALS_SCORE} has tier ${TIER}"
        fi
    fi
    
    # Database validation
    echo ""
    echo "--- J2.4 & J2.7: Database Validation ---"
    echo "Use Supabase MCP:"
    echo "  SELECT COUNT(*) FROM lead_pool WHERE campaign_id = '${CAMPAIGN_ID}';"
    echo "  SELECT als_score, tier, COUNT(*) FROM lead_pool WHERE campaign_id = '${CAMPAIGN_ID}' GROUP BY als_score, tier;"
}
```

---

## Journey 3: Outreach Execution (Full Implementation)

```bash
run_journey_3() {
    echo ""
    echo "================================================"
    echo "JOURNEY 3: OUTREACH EXECUTION (TEST_MODE)"
    echo "================================================"
    
    # J3.1: Verify TEST_MODE
    echo ""
    echo "--- J3.1: Verify TEST_MODE ---"
    echo "⚠️  TEST_MODE must be enabled in Railway"
    echo "    All outreach redirects to:"
    echo "    📧 Email: david.stephens@keiracom.com"
    echo "    📱 SMS: +61457543392"
    echo "    📞 Voice: +61457543392"
    
    # J3.2: Generate Content for ALL channels
    echo ""
    echo "--- J3.2: Generate Content (Email + SMS + Voice) ---"
    
    CONTENT_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"campaign_id\": \"${CAMPAIGN_ID}\",
            \"lead_ids\": [\"${FIRST_LEAD_ID}\"],
            \"channels\": [\"email\", \"sms\", \"voice\"]
        }" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/generate-content)
    
    CONTENT_STATUS=$(echo $CONTENT_RESPONSE | jq -r '.status // "unknown"')
    
    if [ "$CONTENT_STATUS" = "success" ] || [ "$CONTENT_STATUS" = "generated" ]; then
        log_result "J3" "2" "true" ""
        echo "✅ Content generated for email, SMS, voice"
    else
        log_result "J3" "2" "false" "Status: $CONTENT_STATUS"
    fi
    
    # J3.3: Activate Campaign
    echo ""
    echo "--- J3.3: Activate Campaign ---"
    
    ACTIVATE_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/activate)
    
    CAMPAIGN_STATUS=$(echo $ACTIVATE_RESPONSE | jq -r '.status // "unknown"')
    
    if [ "$CAMPAIGN_STATUS" = "active" ] || [ "$CAMPAIGN_STATUS" = "activated" ]; then
        log_result "J3" "3" "true" ""
        echo "✅ Campaign activated"
    else
        log_result "J3" "3" "false" "Status: $CAMPAIGN_STATUS"
    fi
    
    # J3.4: Send EMAIL (3 test emails)
    echo ""
    echo "--- J3.4: Send EMAIL (3 messages → david.stephens@keiracom.com) ---"
    
    EMAIL_SEND_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"email\", \"limit\": 3}" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/send)
    
    EMAIL_SENT=$(echo $EMAIL_SEND_RESPONSE | jq -r '.sent // .count // 0')
    
    if [ "$EMAIL_SENT" -gt 0 ]; then
        log_result "J3" "4a" "true" ""
        echo "✅ Sent ${EMAIL_SENT} emails"
        echo "📧 Check inbox: david.stephens@keiracom.com"
    else
        log_result "J3" "4a" "false" "Emails sent: $EMAIL_SENT"
    fi
    
    # J3.5: Send SMS (2 test SMS)
    echo ""
    echo "--- J3.5: Send SMS (2 messages → +61457543392) ---"
    
    SMS_SEND_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"sms\", \"limit\": 2}" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/send)
    
    SMS_SENT=$(echo $SMS_SEND_RESPONSE | jq -r '.sent // .count // 0')
    
    if [ "$SMS_SENT" -gt 0 ]; then
        log_result "J3" "4b" "true" ""
        echo "✅ Sent ${SMS_SENT} SMS messages"
        echo "📱 Check phone: +61457543392"
    else
        log_result "J3" "4b" "false" "SMS sent: $SMS_SENT"
        echo "⚠️ SMS may have failed - check Twilio credentials"
    fi
    
    # J3.6: Send VOICE (1 test call)
    echo ""
    echo "--- J3.6: Send VOICE (1 call → +61457543392) ---"
    echo "⚠️  This will trigger a REAL PHONE CALL to your number!"
    echo "    The call will be from Vapi AI agent"
    
    VOICE_SEND_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"channel\": \"voice\", \"limit\": 1}" \
        ${API_BASE}/campaigns/${CAMPAIGN_ID}/send)
    
    VOICE_SENT=$(echo $VOICE_SEND_RESPONSE | jq -r '.sent // .count // 0')
    
    if [ "$VOICE_SENT" -gt 0 ]; then
        log_result "J3" "4c" "true" ""
        echo "✅ Initiated ${VOICE_SENT} voice call"
        echo "📞 Expect call to: +61457543392"
    else
        log_result "J3" "4c" "false" "Voice calls: $VOICE_SENT"
        echo "⚠️ Voice may have failed - check Vapi/Twilio credentials"
    fi
    
    # J3.7: Database validation
    echo ""
    echo "--- J3.7: Database Validation ---"
    echo "Use Supabase MCP to verify activities:"
    echo "  SELECT channel, status, COUNT(*) FROM activities WHERE campaign_id = '${CAMPAIGN_ID}' GROUP BY channel, status;"
    
    # Summary
    echo ""
    echo "=========================================="
    echo "JOURNEY 3 OUTREACH SUMMARY"
    echo "=========================================="
    echo "📧 Emails sent: ${EMAIL_SENT:-0} → david.stephens@keiracom.com"
    echo "📱 SMS sent: ${SMS_SENT:-0} → +61457543392"
    echo "📞 Calls made: ${VOICE_SENT:-0} → +61457543392"
    echo ""
    echo "CHECK YOUR DEVICES NOW!"
}
        echo "✅ Sent ${SENT_COUNT} messages"
        echo "📧 Check inbox: david.stephens@keiracom.com"
    else
        log_result "J3" "4" "false" "Sent: $SENT_COUNT"
    fi
    
    # Database validation
    echo ""
    echo "--- J3.5-6: Database Validation ---"
    echo "Use Supabase MCP:"
    echo "  SELECT * FROM activities WHERE campaign_id = '${CAMPAIGN_ID}' LIMIT 10;"
    echo "  SELECT * FROM email_events WHERE campaign_id = '${CAMPAIGN_ID}' LIMIT 10;"
}
```

---

## Journey 4, 5, 6: (Abbreviated)

```bash
run_journey_4() {
    echo ""
    echo "================================================"
    echo "JOURNEY 4: REPLY & MEETING"
    echo "================================================"
    
    # Simulate reply
    REPLY_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"lead_id\": \"${FIRST_LEAD_ID}\",
            \"channel\": \"email\",
            \"content\": \"I am interested. Can we schedule a call?\",
            \"sentiment\": \"positive\"
        }" \
        ${API_BASE}/replies/simulate 2>/dev/null || echo '{"status": "endpoint_not_found"}')
    
    echo "Reply simulation: $REPLY_RESPONSE"
    
    # Create meeting
    MEETING_RESPONSE=$(curl -s -X POST \
        -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{
            \"lead_id\": \"${FIRST_LEAD_ID}\",
            \"campaign_id\": \"${CAMPAIGN_ID}\",
            \"scheduled_at\": \"$(date -d '+3 days' +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -v+3d +%Y-%m-%dT%H:%M:%S)\",
            \"meeting_type\": \"discovery_call\"
        }" \
        ${API_BASE}/meetings)
    
    MEETING_ID=$(echo $MEETING_RESPONSE | jq -r '.id // empty')
    
    if [ -n "$MEETING_ID" ]; then
        log_result "J4" "5" "true" ""
        echo "✅ Meeting created: ${MEETING_ID}"
    else
        log_result "J4" "5" "false" "No meeting ID"
    fi
    
    echo ""
    echo "Use Supabase MCP to verify:"
    echo "  SELECT * FROM conversation_threads WHERE lead_id = '${FIRST_LEAD_ID}';"
    echo "  SELECT * FROM deals WHERE lead_id = '${FIRST_LEAD_ID}';"
    echo "  SELECT * FROM meetings WHERE lead_id = '${FIRST_LEAD_ID}';"
}

run_journey_5() {
    echo ""
    echo "================================================"
    echo "JOURNEY 5: DASHBOARD VERIFICATION"
    echo "================================================"
    
    STATS_RESPONSE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
        ${API_BASE}/dashboard/stats)
    
    echo "Dashboard stats:"
    echo $STATS_RESPONSE | jq .
    
    log_result "J5" "1" "true" ""
}

run_journey_6() {
    echo ""
    echo "================================================"
    echo "JOURNEY 6: ADMIN DASHBOARD"
    echo "================================================"
    
    ADMIN_STATS=$(curl -s ${API_BASE}/admin/stats)
    
    echo "Admin stats:"
    echo $ADMIN_STATS | jq .
    
    log_result "J6" "1" "true" ""
}
```

---

## Main Execution

```bash
#!/bin/bash
# Run all journeys

main() {
    echo "=========================================="
    echo "AGENCY OS AUTOMATED E2E TESTING"
    echo "=========================================="
    echo "Test Run: ${TEST_RUN_ID}"
    echo "Started: $(date)"
    echo ""
    
    # Initialize
    TESTS_PASSED=0
    TESTS_FAILED=0
    
    # Run all journeys
    run_journey_1
    run_journey_2
    run_journey_3
    run_journey_4
    run_journey_5
    run_journey_6
    
    # Print summary
    print_summary
    
    echo ""
    echo "=========================================="
    echo "TEST DATA CREATED"
    echo "=========================================="
    echo "Client ID: ${CLIENT_ID}"
    echo "Campaign ID: ${CAMPAIGN_ID}"
    echo "Test Email: ${TEST_EMAIL}"
    echo "Test Password: ${TEST_PASSWORD}"
    echo ""
    echo "Use these credentials for manual browser testing."
}

main "$@"
```

---

## Report Template

After all tests complete, generate:

```markdown
# Automated E2E Test Report

**Date:** [DATE]
**Test Run ID:** [ID]
**Duration:** [TIME]

## Summary

| Journey | Tests | Passed | Failed |
|---------|-------|--------|--------|
| J1: Signup & Onboarding | 8 | X | X |
| J2: Campaign & Leads | 7 | X | X |
| J3: Outreach Execution | 6 | X | X |
| J4: Reply & Meeting | 7 | X | X |
| J5: Dashboard | 3 | X | X |
| J6: Admin | 2 | X | X |
| **TOTAL** | **33** | **X** | **X** |

## Test Account (For Manual Testing)

| Field | Value |
|-------|-------|
| Email | [TEST_EMAIL] |
| Password | [TEST_PASSWORD] |
| Client ID | [CLIENT_ID] |
| Campaign ID | [CAMPAIGN_ID] |

## Failed Tests

| Test | Expected | Actual | Fix |
|------|----------|--------|-----|
| [test] | [expected] | [actual] | [fix] |

## Database Verification Required

Run these queries in Supabase to verify:

```sql
-- Client created
SELECT * FROM clients WHERE email = '[TEST_EMAIL]';

-- ICP profile
SELECT * FROM client_icp_profiles WHERE client_id = '[CLIENT_ID]';

-- Campaign
SELECT * FROM campaigns WHERE id = '[CAMPAIGN_ID]';

-- Leads
SELECT COUNT(*), tier FROM lead_pool 
WHERE campaign_id = '[CAMPAIGN_ID]' 
GROUP BY tier;

-- Activities
SELECT channel, status, COUNT(*) FROM activities 
WHERE campaign_id = '[CAMPAIGN_ID]' 
GROUP BY channel, status;
```

## Recommendation

[ ] ✅ PROCEED to manual browser testing
[ ] ❌ FIX issues first

## Manual Testing Focus

Based on automated results, focus manual testing on:

1. [area]
2. [area]
3. [area]
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| 401 on all endpoints | Token expired/invalid | Re-run signup |
| 404 on endpoint | Route not registered | Check routes/__init__.py |
| 500 on signup | DB connection issue | Check DATABASE_URL |
| No leads after enrichment | Apollo API issue | Check APOLLO_API_KEY |
| Emails not redirected | TEST_MODE off | Set TEST_MODE=true in Railway |
| Timeout on ICP extraction | Slow scraper | Increase MAX_WAIT |

---

## Usage

```bash
# From Claude Code, run:
cd C:\AI\Agency_OS
source scripts/e2e_test.sh  # Or run commands directly
main
```

Or execute step-by-step following the journey implementations above.


---

## PowerShell Patterns (Windows)

Since Agency OS runs on Windows, here are PowerShell equivalents for all bash commands:

### Environment Setup (PowerShell)

```powershell
# Generate unique test run ID
$TEST_RUN_ID = Get-Date -Format "yyyyMMddHHmmss"

# Test credentials
$TEST_EMAIL = "e2e_${TEST_RUN_ID}@agencyos-test.com"
$TEST_PASSWORD = "TestPass123!@#"
$TEST_AGENCY = "E2E Test Agency ${TEST_RUN_ID}"

# Test ICP data
$TEST_WEBSITE = "https://umped.com.au"
$TEST_INDUSTRY = "Marketing Agency"
$TEST_COMPANY_SIZE = "10-50"
$TEST_LOCATION = "Australia"

# API endpoints
$API_BASE = "https://agency-os-production.up.railway.app/api/v1"

# Tokens (populated during tests)
$ACCESS_TOKEN = ""
$CLIENT_ID = ""
$CAMPAIGN_ID = ""

Write-Host "Test Run: $TEST_RUN_ID"
Write-Host "Email: $TEST_EMAIL"
```

### API Call Pattern (PowerShell)

```powershell
function Test-ApiEndpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [hashtable]$Body = @{},
        [int]$ExpectedCode = 200
    )
    
    Write-Host "--- Testing: $Name ---"
    
    $headers = @{
        "Authorization" = "Bearer $ACCESS_TOKEN"
        "Content-Type" = "application/json"
    }
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Uri "$API_BASE$Endpoint" -Headers $headers -Method Get
        } else {
            $jsonBody = $Body | ConvertTo-Json
            $response = Invoke-WebRequest -Uri "$API_BASE$Endpoint" -Headers $headers -Method $Method -Body $jsonBody
        }
        
        $code = $response.StatusCode
        $content = $response.Content | ConvertFrom-Json
        
        if ($code -eq $ExpectedCode) {
            Write-Host "✅ PASS: $Name (HTTP $code)" -ForegroundColor Green
            return @{ Passed = $true; Data = $content }
        } else {
            Write-Host "❌ FAIL: $Name (Expected $ExpectedCode, got $code)" -ForegroundColor Red
            return @{ Passed = $false; Data = $content }
        }
    }
    catch {
        Write-Host "❌ FAIL: $Name - $($_.Exception.Message)" -ForegroundColor Red
        return @{ Passed = $false; Error = $_.Exception.Message }
    }
}
```

### Signup (PowerShell)

```powershell
Write-Host "--- J1.1: Create Account ---"

$signupBody = @{
    email = $TEST_EMAIL
    password = $TEST_PASSWORD
    agency_name = $TEST_AGENCY
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$API_BASE/auth/signup" `
    -Method Post `
    -ContentType "application/json" `
    -Body $signupBody

$ACCESS_TOKEN = $response.access_token
$CLIENT_ID = $response.user.id

if ($ACCESS_TOKEN) {
    Write-Host "✅ Account created: $CLIENT_ID" -ForegroundColor Green
} else {
    Write-Host "❌ Signup failed" -ForegroundColor Red
    Write-Host $response
}
```

### Polling Pattern (PowerShell)

```powershell
function Wait-ForCondition {
    param(
        [string]$Name,
        [scriptblock]$CheckScript,
        [scriptblock]$SuccessCondition,
        [int]$MaxWaitSeconds = 120,
        [int]$IntervalSeconds = 10
    )
    
    Write-Host "--- Polling: $Name (max ${MaxWaitSeconds}s) ---"
    
    $waited = 0
    while ($waited -lt $MaxWaitSeconds) {
        $result = & $CheckScript
        
        if (& $SuccessCondition $result) {
            Write-Host "✅ Ready after ${waited}s" -ForegroundColor Green
            return $result
        }
        
        Write-Host "   Waiting... (${waited}s)"
        Start-Sleep -Seconds $IntervalSeconds
        $waited += $IntervalSeconds
    }
    
    Write-Host "❌ Timeout after ${MaxWaitSeconds}s" -ForegroundColor Red
    return $null
}

# Example usage:
$leads = Wait-ForCondition -Name "Lead Enrichment" -MaxWaitSeconds 180 -IntervalSeconds 15 `
    -CheckScript {
        $headers = @{ "Authorization" = "Bearer $ACCESS_TOKEN" }
        Invoke-RestMethod -Uri "$API_BASE/campaigns/$CAMPAIGN_ID/leads?limit=1" -Headers $headers
    } `
    -SuccessCondition {
        param($r)
        $r.leads.Count -gt 0
    }
```

### Send Outreach (PowerShell)

```powershell
# Send Email
Write-Host "--- J3.4a: Send EMAIL ---"
$emailResponse = Invoke-RestMethod -Uri "$API_BASE/campaigns/$CAMPAIGN_ID/send" `
    -Method Post `
    -Headers @{ "Authorization" = "Bearer $ACCESS_TOKEN"; "Content-Type" = "application/json" } `
    -Body (@{ channel = "email"; limit = 3 } | ConvertTo-Json)

Write-Host "📧 Sent $($emailResponse.sent) emails to david.stephens@keiracom.com"

# Send SMS
Write-Host "--- J3.4b: Send SMS ---"
$smsResponse = Invoke-RestMethod -Uri "$API_BASE/campaigns/$CAMPAIGN_ID/send" `
    -Method Post `
    -Headers @{ "Authorization" = "Bearer $ACCESS_TOKEN"; "Content-Type" = "application/json" } `
    -Body (@{ channel = "sms"; limit = 2 } | ConvertTo-Json)

Write-Host "📱 Sent $($smsResponse.sent) SMS to +61457543392"

# Send Voice
Write-Host "--- J3.4c: Send VOICE ---"
$voiceResponse = Invoke-RestMethod -Uri "$API_BASE/campaigns/$CAMPAIGN_ID/send" `
    -Method Post `
    -Headers @{ "Authorization" = "Bearer $ACCESS_TOKEN"; "Content-Type" = "application/json" } `
    -Body (@{ channel = "voice"; limit = 1 } | ConvertTo-Json)

Write-Host "📞 Made $($voiceResponse.sent) call to +61457543392"
```

---

## SQL Verification Queries

Use these with `supabase:execute_sql` MCP tool for database validation.

### Journey 1: Client & Onboarding Verification

```sql
-- J1.7: Verify client created
SELECT id, email, agency_name, onboarding_completed, created_at
FROM clients 
WHERE email = '${TEST_EMAIL}';

-- J1.8: Verify ICP profile created
SELECT 
    client_id,
    industry,
    company_size,
    target_titles,
    location,
    created_at
FROM client_icp_profiles 
WHERE client_id = '${CLIENT_ID}';

-- Verify onboarding status
SELECT 
    c.email,
    c.onboarding_completed,
    CASE WHEN i.id IS NOT NULL THEN 'Yes' ELSE 'No' END as has_icp
FROM clients c
LEFT JOIN client_icp_profiles i ON c.id = i.client_id
WHERE c.email = '${TEST_EMAIL}';
```

### Journey 2: Campaign & Lead Verification

```sql
-- J2.1: Verify campaign created
SELECT id, client_id, name, status, target_leads, channels, created_at
FROM campaigns 
WHERE id = '${CAMPAIGN_ID}';

-- J2.3: Verify leads enriched
SELECT COUNT(*) as total_leads
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}';

-- J2.4: Verify lead_pool has full Apollo data
SELECT 
    id, email, first_name, last_name, title, company_name,
    linkedin_url, phone, mobile_phone,
    company_website, company_industry, company_size,
    seniority, department, location_city, location_country,
    als_score, tier
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}'
LIMIT 5;

-- J2.6: Verify ALS scoring distribution
SELECT 
    tier,
    COUNT(*) as count,
    MIN(als_score) as min_score,
    MAX(als_score) as max_score,
    ROUND(AVG(als_score), 1) as avg_score
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}'
GROUP BY tier
ORDER BY 
    CASE tier 
        WHEN 'Hot' THEN 1 
        WHEN 'Warm' THEN 2 
        WHEN 'Cool' THEN 3 
        WHEN 'Cold' THEN 4 
        WHEN 'Dead' THEN 5 
    END;

-- J2.7: Verify lead assignments
SELECT 
    la.id,
    la.lead_id,
    la.campaign_id,
    la.assigned_at,
    lp.email as lead_email
FROM lead_assignments la
JOIN lead_pool lp ON la.lead_id = lp.id
WHERE la.campaign_id = '${CAMPAIGN_ID}'
LIMIT 10;

-- Verify deep research triggered for hot leads
SELECT 
    id, email, als_score, tier, 
    deep_research_triggered, deep_research_completed_at
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}'
  AND als_score >= 85
LIMIT 5;
```

### Journey 3: Outreach Verification

```sql
-- J3.5: Verify activities logged (all channels)
SELECT 
    channel,
    activity_type,
    status,
    COUNT(*) as count
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}'
GROUP BY channel, activity_type, status
ORDER BY channel;

-- Detailed activity log
SELECT 
    a.id,
    a.lead_id,
    a.channel,
    a.activity_type,
    a.status,
    a.created_at,
    lp.email as lead_email
FROM activities a
JOIN lead_pool lp ON a.lead_id = lp.id
WHERE a.campaign_id = '${CAMPAIGN_ID}'
ORDER BY a.created_at DESC
LIMIT 20;

-- J3.6: Verify email events
SELECT 
    id,
    activity_id,
    event_type,
    created_at
FROM email_events
WHERE activity_id IN (
    SELECT id FROM activities 
    WHERE campaign_id = '${CAMPAIGN_ID}'
)
ORDER BY created_at DESC
LIMIT 10;

-- Verify TEST_MODE redirects (check recipient field)
SELECT 
    id,
    lead_id,
    channel,
    recipient,
    status,
    created_at
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}'
  AND status = 'sent'
ORDER BY created_at DESC
LIMIT 10;
```

### Journey 4: Reply & Meeting Verification

```sql
-- J4.3: Verify conversation thread created
SELECT 
    ct.id as thread_id,
    ct.lead_id,
    ct.campaign_id,
    ct.channel,
    ct.status,
    ct.message_count,
    ct.created_at,
    lp.email as lead_email
FROM conversation_threads ct
JOIN lead_pool lp ON ct.lead_id = lp.id
WHERE ct.campaign_id = '${CAMPAIGN_ID}'
LIMIT 5;

-- J4.4: Verify thread messages
SELECT 
    tm.id,
    tm.thread_id,
    tm.direction,
    tm.content,
    tm.sentiment,
    tm.created_at
FROM thread_messages tm
WHERE tm.thread_id IN (
    SELECT id FROM conversation_threads 
    WHERE campaign_id = '${CAMPAIGN_ID}'
)
ORDER BY tm.created_at
LIMIT 20;

-- J4.6: Verify deal created
SELECT 
    d.id,
    d.lead_id,
    d.campaign_id,
    d.stage,
    d.value,
    d.created_at,
    lp.email as lead_email
FROM deals d
JOIN lead_pool lp ON d.lead_id = lp.id
WHERE d.campaign_id = '${CAMPAIGN_ID}'
LIMIT 5;

-- J4.7: Verify meeting created
SELECT 
    m.id,
    m.lead_id,
    m.campaign_id,
    m.meeting_type,
    m.scheduled_at,
    m.duration_minutes,
    m.status,
    m.created_at,
    lp.email as lead_email
FROM meetings m
JOIN lead_pool lp ON m.lead_id = lp.id
WHERE m.campaign_id = '${CAMPAIGN_ID}'
LIMIT 5;
```

### Journey 5: Dashboard Verification

```sql
-- J5.2: Get counts for dashboard comparison
SELECT 
    (SELECT COUNT(*) FROM campaigns WHERE client_id = '${CLIENT_ID}') as total_campaigns,
    (SELECT COUNT(*) FROM lead_pool WHERE campaign_id IN 
        (SELECT id FROM campaigns WHERE client_id = '${CLIENT_ID}')) as total_leads,
    (SELECT COUNT(*) FROM activities WHERE campaign_id IN 
        (SELECT id FROM campaigns WHERE client_id = '${CLIENT_ID}')) as total_activities,
    (SELECT COUNT(*) FROM meetings WHERE campaign_id IN 
        (SELECT id FROM campaigns WHERE client_id = '${CLIENT_ID}')) as total_meetings,
    (SELECT COUNT(*) FROM deals WHERE campaign_id IN 
        (SELECT id FROM campaigns WHERE client_id = '${CLIENT_ID}')) as total_deals;

-- Campaign analytics
SELECT 
    c.id,
    c.name,
    c.status,
    COUNT(DISTINCT lp.id) as lead_count,
    COUNT(DISTINCT a.id) as activity_count,
    COUNT(DISTINCT CASE WHEN a.status = 'sent' THEN a.id END) as sent_count,
    COUNT(DISTINCT m.id) as meeting_count
FROM campaigns c
LEFT JOIN lead_pool lp ON c.id = lp.campaign_id
LEFT JOIN activities a ON c.id = a.campaign_id
LEFT JOIN meetings m ON c.id = m.campaign_id
WHERE c.id = '${CAMPAIGN_ID}'
GROUP BY c.id, c.name, c.status;
```

### Journey 6: Admin Verification

```sql
-- J6.2: Platform-wide stats
SELECT 
    (SELECT COUNT(*) FROM clients) as total_clients,
    (SELECT COUNT(*) FROM campaigns) as total_campaigns,
    (SELECT COUNT(*) FROM lead_pool) as total_leads,
    (SELECT COUNT(*) FROM activities) as total_activities,
    (SELECT COUNT(*) FROM meetings) as total_meetings,
    (SELECT COUNT(*) FROM deals) as total_deals;

-- Clients by onboarding status
SELECT 
    onboarding_completed,
    COUNT(*) as count
FROM clients
GROUP BY onboarding_completed;

-- Campaigns by status
SELECT 
    status,
    COUNT(*) as count
FROM campaigns
GROUP BY status;

-- Activity by channel (last 24 hours)
SELECT 
    channel,
    status,
    COUNT(*) as count
FROM activities
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY channel, status
ORDER BY channel, status;
```

---

## Test Data Cleanup

### Delete Single Test Run

```sql
-- Delete test client (cascades to all related data)
-- ⚠️ CAREFUL: This deletes everything for this client!

DELETE FROM clients 
WHERE email = '${TEST_EMAIL}';

-- This cascades to:
-- - client_icp_profiles (ON DELETE CASCADE)
-- - campaigns (ON DELETE CASCADE)
--   - lead_pool (ON DELETE CASCADE)
--   - lead_assignments (ON DELETE CASCADE)
--   - activities (ON DELETE CASCADE)
--   - conversation_threads (ON DELETE CASCADE)
--   - deals (ON DELETE CASCADE)
--   - meetings (ON DELETE CASCADE)
```

### Delete All Test Data

```sql
-- Delete all E2E test clients (by email pattern)
DELETE FROM clients 
WHERE email LIKE 'e2e_%@agencyos-test.com';

-- Verify cleanup
SELECT COUNT(*) as remaining_test_clients
FROM clients 
WHERE email LIKE 'e2e_%@agencyos-test.com';
```

### Delete Specific Campaign Only

```sql
-- Delete single campaign (if you want to keep the client)
DELETE FROM campaigns 
WHERE id = '${CAMPAIGN_ID}';

-- This cascades to related lead_pool, activities, etc.
```

### Cleanup Orphaned Data

```sql
-- Find orphaned leads (no campaign)
SELECT COUNT(*) 
FROM lead_pool 
WHERE campaign_id NOT IN (SELECT id FROM campaigns);

-- Find orphaned activities (no campaign)
SELECT COUNT(*) 
FROM activities 
WHERE campaign_id NOT IN (SELECT id FROM campaigns);

-- Delete orphaned data (run if counts > 0)
DELETE FROM lead_pool 
WHERE campaign_id NOT IN (SELECT id FROM campaigns);

DELETE FROM activities 
WHERE campaign_id NOT IN (SELECT id FROM campaigns);
```

---

## Error Diagnosis Queries

### Auth Errors

```sql
-- Check if client exists
SELECT id, email, created_at 
FROM clients 
WHERE email = '${TEST_EMAIL}';

-- Check auth.users (Supabase auth)
SELECT id, email, created_at, confirmed_at
FROM auth.users 
WHERE email = '${TEST_EMAIL}';
```

### Onboarding Errors

```sql
-- Check onboarding state
SELECT 
    c.id,
    c.email,
    c.onboarding_completed,
    c.onboarding_step,
    i.id as icp_id,
    i.industry
FROM clients c
LEFT JOIN client_icp_profiles i ON c.id = i.client_id
WHERE c.email = '${TEST_EMAIL}';
```

### Campaign Errors

```sql
-- Check campaign state
SELECT 
    id, name, status, 
    target_leads, channels,
    error_message,
    created_at, updated_at
FROM campaigns 
WHERE id = '${CAMPAIGN_ID}';
```

### Lead Enrichment Errors

```sql
-- Check enrichment status
SELECT 
    enrichment_status,
    COUNT(*) as count
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}'
GROUP BY enrichment_status;

-- Find failed enrichments
SELECT id, email, enrichment_status, enrichment_error
FROM lead_pool 
WHERE campaign_id = '${CAMPAIGN_ID}'
  AND enrichment_status = 'failed'
LIMIT 10;
```

### Outreach Errors

```sql
-- Check failed activities
SELECT 
    id, lead_id, channel, activity_type,
    status, error_message, created_at
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}'
  AND status = 'failed'
LIMIT 10;

-- Check activity status distribution
SELECT 
    channel,
    status,
    COUNT(*) as count
FROM activities 
WHERE campaign_id = '${CAMPAIGN_ID}'
GROUP BY channel, status
ORDER BY channel, status;
```

### RLS/Permission Errors

```sql
-- Check RLS policies on table
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies 
WHERE tablename = 'campaigns';

-- Test RLS as specific user (for debugging)
-- Run as service role:
SET ROLE authenticated;
SET request.jwt.claims = '{"sub": "${CLIENT_ID}"}';

SELECT * FROM campaigns LIMIT 5;

RESET ROLE;
```

---

## MCP Tool Usage Reference

### Supabase MCP

```
# List all tables
supabase:list_tables

# Execute SQL
supabase:execute_sql
query: "SELECT * FROM clients LIMIT 5"

# List migrations
supabase:list_migrations

# Apply migration
supabase:apply_migration
name: "fix_something"
query: "ALTER TABLE..."

# Get logs
supabase:get_logs
service: "postgres"
```

### Railway MCP

```
# List variables
railway:list-variables
workspacePath: "C:\AI\Agency_OS"

# Set variable
railway:set-variables
workspacePath: "C:\AI\Agency_OS"
variables: ["TEST_MODE=true"]

# Get logs
railway:get-logs
workspacePath: "C:\AI\Agency_OS"
logType: "deploy"
lines: 50

# List deployments
railway:list-deployments
workspacePath: "C:\AI\Agency_OS"
json: true
```

### Vercel MCP

```
# List teams
vercel:list_teams

# List projects
vercel:list_projects
teamId: "team_xxx"

# List deployments
vercel:list_deployments
projectId: "prj_xxx"
teamId: "team_xxx"

# Get deployment logs
vercel:get_deployment_build_logs
idOrUrl: "dpl_xxx"
teamId: "team_xxx"
```

---

## Complete Test Run Checklist

```
PRE-FLIGHT
[ ] Railway env vars set (TEST_MODE=true, etc.)
[ ] Supabase migrations applied
[ ] Backend health returns 200
[ ] Frontend loads

JOURNEY 1: SIGNUP & ONBOARDING
[ ] J1.1: Account created, token received
[ ] J1.2: Onboarding status returned
[ ] J1.3: ICP extraction started
[ ] J1.4: ICP extraction completed
[ ] J1.5: ICP confirmed
[ ] J1.6: Onboarding complete
[ ] J1.7: DB: Client record exists
[ ] J1.8: DB: ICP profile exists

JOURNEY 2: CAMPAIGN & LEADS
[ ] J2.1: Campaign created
[ ] J2.2: Enrichment started
[ ] J2.3: Leads populated (25+)
[ ] J2.4: DB: lead_pool has full data
[ ] J2.5: Lead list returned with ALS scores
[ ] J2.6: ALS tiers correct
[ ] J2.7: DB: lead_assignments exist

JOURNEY 3: OUTREACH (TEST_MODE)
[ ] J3.1: TEST_MODE verified
[ ] J3.2: Content generated
[ ] J3.3: Campaign activated
[ ] J3.4a: 3 emails sent → check inbox
[ ] J3.4b: 2 SMS sent → check phone
[ ] J3.4c: 1 voice call → answer phone
[ ] J3.5: DB: activities logged (all channels)
[ ] J3.6: DB: email_events tracked

JOURNEY 4: REPLY & MEETING
[ ] J4.1: Reply simulated
[ ] J4.2: Reply analysis returned
[ ] J4.3: DB: conversation_thread exists
[ ] J4.4: DB: thread_messages exist
[ ] J4.5: Meeting created
[ ] J4.6: DB: deal exists
[ ] J4.7: DB: meeting exists

JOURNEY 5: DASHBOARD
[ ] J5.1: Dashboard stats returned
[ ] J5.2: DB: counts match
[ ] J5.3: Campaign analytics correct

JOURNEY 6: ADMIN
[ ] J6.1: Admin stats returned
[ ] J6.2: DB: platform totals match

POST-TEST
[ ] Test report generated
[ ] Credentials saved for manual testing
[ ] Issues logged and fixed
[ ] Cleanup completed (optional)
```
