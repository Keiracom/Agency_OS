# E2E Skill Files Placeholder Scan Report

**Generated:** 2026-01-18
**Scanned Directory:** `docs/e2e/library/cookbook/`
**Total Files Scanned:** 100+ Python skill files

---

## Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| `{{...}}` Double-brace placeholders | 47 occurrences | CRITICAL |
| `{...}` Single-brace placeholders | 250+ occurrences | CRITICAL |
| `YOUR_...` patterns | 0 | - |
| `<PLACEHOLDER>` patterns | 0 | - |
| TODO/FIXME test data comments | 3 | LOW |

**Total Placeholders Found:** ~300+

---

## Actual Test Data (from e2e_config.json)

These values should replace placeholders:

| Placeholder | Actual Value |
|-------------|--------------|
| `{{test_lead_id}}` / `{test_lead_id}` | Must be created during test |
| `{{test_campaign_id}}` / `{campaign_id}` | Must be created during test |
| `{client_id}` | `81dbaee6-4e71-48ad-be40-fa915fae66e0` |
| `{user_id}` | `a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2` |
| `{token}` | Obtained via Supabase auth login |
| `{api_url}` | `https://agency-os-production.up.railway.app` |
| `{frontend_url}` | `https://agency-os-liart.vercel.app` |
| `{supabase_url}` | `https://jatzvazlbusedwsnqxzr.supabase.co` |
| Test email recipient | `david.stephens@keiracom.com` |
| Test SMS recipient | `+61457543392` |

---

## CRITICAL - Double-Brace Placeholders (`{{...}}`)

These block testing because they are NOT valid Python f-string syntax and will appear literally in output.

### j4_clicksend_integration.py
- **Line 124:** `"lead_id": "{{test_lead_id}}"`
- **Line 136:** `"lead_id": "{{test_lead_id}}"`

### j4_rate_limiting.py
- **Line 34:** `"upstash_url": "{{UPSTASH_REDIS_URL}}"`
- **Line 92:** `"lead_id": "{{test_lead_id}}"`
- **Line 108:** `"lead_id": "{{test_lead_id}}"`
- **Line 124:** `"lead_id": "{{test_lead_id}}"`
- **Line 140:** `"lead_id": "{{test_lead_id}}"`

### j4_provider_selection.py
- **Line 116:** `"lead_id": "{{test_lead_id}}"`
- **Line 129:** `"lead_id": "{{test_lead_id}}"`

### j4_twilio_integration.py
- **Line 125:** `"lead_id": "{{test_lead_id}}"`
- **Line 136:** `"lead_id": "{{test_lead_id}}"`

### j4_live_sms_test.py
- **Line 81:** `"lead_id": "{{test_lead_id}}"`
- **Line 82:** `"message": "...Timestamp: {{timestamp}}"`
- **Line 94:** `"lead_id": "{{test_lead_id}}"`
- **Line 126:** `"{{first_name}}"` (template variable - acceptable)

### j4_sms_personalization.py
- **Lines 35-47:** Template variables like `{{first_name}}`, `{{last_name}}`, etc. (acceptable - these are template tokens)
- **Line 100:** `"lead_id": "{{test_lead_id}}"`
- **Line 101:** `"template": "Hi {{first_name}}..."` (template - acceptable)
- **Line 103:** `"campaign_id": "{{test_campaign_id}}"`
- **Line 116:** `"lead_id": "{{test_lead_id}}"`

### j4_test_mode.py
- **Line 76:** `"lead_id": "{{test_lead_id}}"`
- **Line 88:** `"lead_id": "{{test_lead_id}}"`

### j5_live_voice_test.py
- **Line 77:** `"lead_id": "{{test_lead_id}}"`
- **Line 78:** `"campaign_id": "{{test_campaign_id}}"`

### j5_error_handling.py
- **Line 88:** `"lead_id": "{{test_lead_id}}"`
- **Line 89:** `"campaign_id": "{{test_campaign_id}}"`
- **Line 113:** `"lead_id": "{{lead_without_phone}}"`
- **Line 114:** `"assistant_id": "{{test_assistant_id}}"`

### j5_als_validation.py
- **Line 80:** `"lead_id": "{{low_als_lead_id}}"`
- **Line 81:** `"assistant_id": "{{test_assistant_id}}"`

### j5_vapi_integration.py
- **Line 103:** `"campaign_id": "{{test_campaign_id}}"`
- **Line 131:** `"lead_id": "{{test_lead_id}}"`
- **Line 132:** `"assistant_id": "{{test_assistant_id}}"`

### j5_test_mode.py
- **Line 75:** `"lead_id": "{{test_lead_id}}"`
- **Line 76:** `"campaign_id": "{{test_campaign_id}}"`

### j8_meeting_service.py
- **Line 66:** `"lead_id": "{{test_lead_id}}"`

### j8_deal_service.py
- **Line 87:** `"lead_id": "{{test_lead_id}}"`

### j1_auto_provision.py
- **Line 17:** `"db_connection": "...{{DB_PASSWORD}}..."`

### j1_login_page.py
- **Line 18:** `"password": "{{TEST_USER_PASSWORD}}"`

### j3_live_email_test.py
- **Line 155:** `"not showing {{first_name}}"` (validation message - acceptable)

### j3_unsubscribe_handling.py
- **Line 32:** `"placeholder": "{{unsubscribe_link}}"` (template token - acceptable)

### j10_client_detail.py
- **Line 209:** `"/admin/clients/{{client_id}}"` (escaped brace in f-string - acceptable)

---

## CRITICAL - Single-Brace Placeholders (`{...}`)

These are used in curl commands and URLs that need runtime substitution.

### Files with `{token}` placeholder (needs auth token):
- j10_live_activity.py (lines 88, 114, 139)
- j10_admin_settings.py (lines 92, 116, 152)
- j10_kpi_section.py (lines 85, 105, 123, 141, 161)
- j10_compliance.py (lines 98, 120, 149, 175)
- j10_client_directory.py (lines 95, 127, 154, 210)
- j10_command_center.py (line 144)
- j10_client_detail.py (lines 63, 108, 132, 159)
- j10_revenue_page.py (lines 86, 114, 139)
- j10_rate_limits.py (line 91)
- j10_alerts_section.py (lines 61, 84, 111)
- j10_ai_costs.py (lines 91, 118, 143, 189)
- j10_system_errors.py (lines 83, 121)
- j10_system_queues.py (lines 93, 117)
- j10_system_status.py (line 127)
- j1_icp_confirmation.py (lines 63, 161)
- j1_icp_scraper.py (line 69)
- j1_job_tracking.py (line 123)
- j1_onboarding_api.py (lines 54, 107, 126)
- j1_onboarding_page.py (line 65)
- j1_edge_cases.py (line 112)
- j2_campaign_create.py (lines 71, 103)
- j2_campaign_persistence.py (lines 93, 94)
- j2_campaign_validation.py (lines 70, 134)
- j2_campaign_analytics.py (lines 56, 125)
- j2_campaign_export.py (lines 42, 106)
- j2_campaign_pool.py (lines 110, 111)
- j2_content_engine.py (lines 87, 92)
- j2_template_management.py (lines 69, 70)
- j2_sequence_config.py (lines 104, 105)
- j2_live_campaign_test.py (lines 74, 75)
- j2b_apollo_search.py (line 70)
- j2b_apollo_enrichment.py (lines 62, 63)
- j2b_enrichment_analytics.py (lines 49, 50, 67, 68)
- j3_email_engine.py (line 104)
- j3_email_personalization.py (lines 70, 80)
- j3_test_mode.py (line 94)
- j3_salesforge_integration.py (line 107)
- j3_live_email_test.py (line 116)
- j3_rate_limiting.py (line 102)
- j4_live_sms_test.py (line 92)
- j4_provider_selection.py (line 127)
- j4_rate_limiting.py (lines 106, 138)
- j4_clicksend_integration.py (line 134)
- j4_sms_personalization.py (line 114)
- j4_test_mode.py (line 86)
- j4_twilio_integration.py (line 134)
- j5_error_handling.py (lines 97, 122)
- j5_als_validation.py (line 90)
- j5_vapi_integration.py (lines 115, 140, 156)
- j5_live_voice_test.py (line 88)
- j5_test_mode.py (line 85)
- j6_linkedin_engine.py (line 128)
- j6_seat_management.py (lines 69, 100)
- j6_url_validation.py (line 92)
- j6_heyreach_integration.py (line 136)
- j6_test_mode.py (line 89)
- j6_live_linkedin_test.py (lines 66, 89)
- j6_connection_requests.py (line 109)
- j6_error_handling.py (line 112)
- j6_direct_messages.py (line 102)
- j6_account_management.py (line 65)
- j7_intent_classification.py (line 98)
- j7_reply_analyzer.py (lines 92, 138)
- j9_campaigns_list.py (lines 83, 103, 142)
- j9_leads_list.py (lines 91, 109, 148, 166, 184)
- j9_lead_detail.py (lines 86, 150, 169)
- j9_campaign_detail.py (lines 94, 135, 153, 172)
- j9_dashboard_stats.py (lines 85, 104, 123, 142)
- j9_activity_feed.py (line 188)
- j9_als_distribution.py (lines 122, 140)
- j9_icp_banner.py (lines 101, 140)
- j9_meetings_widget.py (lines 103, 144)
- j9_replies_page.py (lines 87, 106, 145, 164)
- j9_dashboard_load.py (line 64)
- j9_realtime_updates.py (lines 88, 135, 136)
- j9_reports_page.py (lines 80, 98, 117, 158)
- j9_settings_page.py (line 70)

### Files with `{client_id}` placeholder:
- j10_admin_settings.py (line 142)
- j10_client_directory.py (lines 153, 185)
- j10_client_detail.py (lines 56, 62, 100, 107, 125, 131, 149, 158)
- j1_icp_confirmation.py (lines 86, 103, 155)
- j1_onboarding_api.py (line 144)
- j1_onboarding_completion.py (line 146)
- j2_campaign_export.py (lines 52, 69, 90)
- j2_campaign_pool.py (line 105)
- j2_live_campaign_test.py (line 160)
- j9_activity_feed.py (line 107)
- j9_als_distribution.py (line 115)
- j9_dashboard_stats.py (lines 155, 159)

### Files with `{campaign_id}` placeholder:
- j2_campaign_analytics.py (lines 42, 55, 125)
- j2_campaign_persistence.py (lines 66, 87, 93, 108, 114, 135)
- j2_campaign_export.py (lines 42, 52, 69, 90, 106)
- j2_campaign_pool.py (lines 102, 105, 110)
- j2_live_campaign_test.py (lines 66, 74, 86, 160)
- j5_vapi_integration.py (line 117)
- j9_campaign_detail.py (lines 87, 93, 105, 127, 134, 146, 152, 164, 171)

### Files with `{lead_id}` placeholder:
- j2b_enrichment_analytics.py (lines 42, 49, 61, 67)
- j2b_apollo_enrichment.py (lines 55, 62)
- j2_content_engine.py (lines 76, 86)
- j2_template_management.py (lines 63, 69)
- j2_sequence_config.py (lines 98, 104)
- j3_email_personalization.py (line 70)
- j5_error_handling.py (line 99)
- j5_vapi_integration.py (line 142)
- j5_live_voice_test.py (line 90)
- j5_test_mode.py (line 87)
- j6_live_linkedin_test.py (lines 80, 91)
- j6_connection_requests.py (line 100)
- j6_error_handling.py (line 104)
- j6_direct_messages.py (line 93)
- j9_lead_detail.py (lines 79, 85, 97, 120, 142, 149, 161, 168, 197)
- j9_leads_list.py (line 197)
- j9_realtime_updates.py (line 135)

### Files with `{job_id}` placeholder:
- j1_edge_cases.py (line 152)
- j1_icp_confirmation.py (lines 56, 65, 148, 163)
- j1_job_tracking.py (lines 70, 79, 95, 114, 122, 137, 164)
- j1_onboarding_page.py (line 105)
- j1_onboarding_api.py (lines 28, 29, 94, 100, 106, 112, 118, 125, 139)

### Files with `{api_url}` placeholder:
All files with curl commands use `{api_url}` - this is expected and should be replaced at runtime.

### Files with `{TOKEN}` placeholder (uppercase):
- j8_deal_autocreate.py (line 79)
- j8_deal_pipeline.py (line 59)
- j8_deal_service.py (line 96)
- j8_e2e_meeting_deal_test.py (lines 133, 166, 184)
- j8_lost_deal_analysis.py (line 66)
- j8_meeting_service.py (line 75)
- j8_show_rate.py (line 120)
- j8_revenue_attribution.py (lines 72, 103)

### Files with `{call_id}` placeholder:
- j5_call_recording.py (line 28)
- j5_vapi_integration.py (lines 153, 159)

### Files with `{assistant_id}` placeholder:
- j5_als_validation.py (line 92)
- j5_error_handling.py (line 124)
- j5_vapi_integration.py (line 142)

### Files with `{meeting_id}` placeholder:
- j8_deal_autocreate.py (line 79)
- j8_e2e_meeting_deal_test.py (line 133)

### Files with `{deal_id}` placeholder:
- j8_e2e_meeting_deal_test.py (lines 166, 184)

---

## LOW - TODO/FIXME Comments

### j0_code_completeness.py
- **Line 74:** `"TODO in test": "Low - Note for later"` - This is a classification example, not an actual TODO

### j5_voice_engine.py
- **Line 34:** `"forbidden_patterns": ["TODO", "FIXME", "pass  # placeholder"]` - Pattern to search for, not actual TODO
- **Line 66:** Similar validation pattern

---

## Analysis and Recommendations

### 1. CRITICAL: Double-Brace Placeholders
**Impact:** Tests will fail or send literal `{{test_lead_id}}` in API calls
**Files Affected:** 18 files
**Fix:** Replace with actual test data or make dynamic at runtime

### 2. CRITICAL: Single-Brace Placeholders in Curl Commands
**Impact:** Curl examples won't work without manual substitution
**Files Affected:** 70+ files
**Design Decision:** These appear to be INTENTIONAL template strings meant to be substituted at runtime by the test executor

### 3. Placeholder Categories

| Category | Intent | Action Needed |
|----------|--------|---------------|
| `{{test_lead_id}}` | Test data ID | Create lead during test setup, inject ID |
| `{{test_campaign_id}}` | Test data ID | Create campaign during test setup, inject ID |
| `{token}` | Auth token | Obtain from Supabase login, inject |
| `{api_url}` | Base URL | Use LIVE_CONFIG value |
| `{client_id}` | Known ID | Use `81dbaee6-4e71-48ad-be40-fa915fae66e0` |
| `{user_id}` | Known ID | Use `a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2` |
| `{{first_name}}` etc | Template tokens | Leave as-is (personalization vars) |

### 4. Recommended Test Setup Flow

```python
# 1. Login and get token
token = supabase_login("e2e-sparro@test.agencyos.com", password)

# 2. Use known IDs from e2e_config.json
client_id = "81dbaee6-4e71-48ad-be40-fa915fae66e0"
user_id = "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2"

# 3. Create test lead (get ID)
test_lead = create_test_lead(client_id)
test_lead_id = test_lead["id"]

# 4. Create test campaign (get ID)
test_campaign = create_test_campaign(client_id)
test_campaign_id = test_campaign["id"]

# 5. Substitute placeholders in curl commands
command = curl_template.replace("{token}", token)
                       .replace("{api_url}", "https://agency-os-production.up.railway.app")
                       .replace("{client_id}", client_id)
                       .replace("{{test_lead_id}}", test_lead_id)
                       .replace("{{test_campaign_id}}", test_campaign_id)
```

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total cookbook files | ~100 |
| Files with double-brace issues | 18 |
| Files with single-brace patterns | 70+ |
| Total placeholder occurrences | ~300 |
| Files without issues | ~12 |

**Conclusion:** The placeholder system is intentionally designed for runtime substitution. The test executor must:
1. Authenticate and obtain a token
2. Use known IDs from `e2e_config.json` for client_id and user_id
3. Create test entities (leads, campaigns) and capture their IDs
4. Substitute all placeholders before executing curl commands or API calls
