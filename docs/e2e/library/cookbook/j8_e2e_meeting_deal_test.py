"""
Skill: J8.14 — End-to-End Meeting-to-Deal Test
Journey: J8 - Meeting & Deals
Checks: 9

Purpose: Verify full meeting-to-deal flow works.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
}

# =============================================================================
# E2E FLOW CONSTANTS
# =============================================================================

E2E_CONSTANTS = {
    "flow_steps": [
        "webhook_received",
        "meeting_created",
        "lead_status_updated",
        "outcome_recorded",
        "deal_created",
        "deal_progressed",
        "deal_closed",
        "attribution_calculated",
        "crm_pushed",
    ],
    "test_lead": {
        "email": "e2e-test@example.com",
        "name": "E2E Test Lead",
    },
    "test_calendly_payload": {
        "event": "invitee.created",
        "payload": {
            "event_type": {"name": "Discovery Call", "duration": 30},
            "invitee": {"email": "e2e-test@example.com", "name": "E2E Test Lead"},
            "scheduled_event": {
                "start_time": "2024-01-25T10:00:00Z",
                "end_time": "2024-01-25T10:30:00Z",
                "uri": "https://calendly.com/events/e2e-test-123"
            }
        }
    },
    "expected_final_state": {
        "meeting_status": "completed",
        "meeting_outcome": "good",
        "lead_status": "converted",
        "deal_stage": "closed_won",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J8.14.1",
        "part_a": "N/A",
        "part_b": "Send Calendly webhook for new booking",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/crm/meeting",
            "headers": {"Content-Type": "application/json"},
            "body": "{test_calendly_payload}",
            "expect": {
                "status": [200, 201],
                "response_contains": ["success", "meeting"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/webhooks/crm/meeting' -H 'Content-Type: application/json' -d '{\"event\": \"invitee.created\", \"payload\": {...}}'"
        }
    },
    {
        "id": "J8.14.2",
        "part_a": "N/A",
        "part_b": "Verify meeting created",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, lead_id, status, meeting_type FROM meetings WHERE calendar_event_id = 'e2e-test-123' ORDER BY created_at DESC LIMIT 1",
            "expect": {
                "has_rows": True,
                "status": "scheduled"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/meetings?calendar_event_id=eq.e2e-test-123&order=created_at.desc&limit=1' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.14.3",
        "part_a": "N/A",
        "part_b": "Verify lead status updated to meeting_booked",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, status, meeting_booked_at FROM leads WHERE email = 'e2e-test@example.com'",
            "expect": {
                "status": "meeting_booked",
                "meeting_booked_at_not_null": True
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/leads?email=eq.e2e-test@example.com&select=id,status,meeting_booked_at' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.14.4",
        "part_a": "N/A",
        "part_b": "Record meeting outcome as 'good'",
        "key_files": ["src/services/meeting_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/meetings/{meeting_id}/outcome",
            "auth": True,
            "body": {
                "outcome": "good",
                "showed_up": True,
                "notes": "Great discovery call, moving to proposal",
                "create_deal": True
            },
            "expect": {
                "status": [200, 201],
                "response_contains": ["meeting", "deal"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/meetings/{meeting_id}/outcome' -H 'Authorization: Bearer {TOKEN}' -d '{\"outcome\": \"good\", \"create_deal\": true}'"
        }
    },
    {
        "id": "J8.14.5",
        "part_a": "N/A",
        "part_b": "Verify deal auto-created",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT d.id, d.stage, d.meeting_id, m.outcome FROM deals d JOIN meetings m ON d.meeting_id = m.id WHERE m.calendar_event_id = 'e2e-test-123'",
            "expect": {
                "has_rows": True,
                "stage": "qualified"
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?select=id,stage,meeting_id,meetings(outcome)&meetings.calendar_event_id=eq.e2e-test-123' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.14.6",
        "part_a": "N/A",
        "part_b": "Progress deal through stages",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "PATCH",
            "url": "{api_url}/api/v1/deals/{deal_id}",
            "auth": True,
            "body": {"stage": "proposal"},
            "expect": {
                "status": [200],
                "response_contains": ["stage", "proposal"]
            },
            "curl_command": "curl -X PATCH '{api_url}/api/v1/deals/{deal_id}' -H 'Authorization: Bearer {TOKEN}' -d '{\"stage\": \"proposal\"}'"
        }
    },
    {
        "id": "J8.14.7",
        "part_a": "N/A",
        "part_b": "Close deal as won",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/deals/{deal_id}/close-won",
            "auth": True,
            "body": {"value": 15000, "notes": "Signed contract"},
            "expect": {
                "status": [200],
                "response_contains": ["closed_won", "15000"]
            },
            "curl_command": "curl -X POST '{api_url}/api/v1/deals/{deal_id}/close-won' -H 'Authorization: Bearer {TOKEN}' -d '{\"value\": 15000}'"
        }
    },
    {
        "id": "J8.14.8",
        "part_a": "N/A",
        "part_b": "Verify revenue attribution calculated",
        "key_files": ["src/services/deal_service.py"],
        "live_test": {
            "type": "db_query",
            "query": "SELECT id, converting_channel, attributed_revenue FROM deals WHERE id = '{deal_id}'",
            "expect": {
                "converting_channel_not_null": True,
                "attributed_revenue": 15000
            },
            "curl_command": "curl -X GET '{supabase_url}/rest/v1/deals?id=eq.{deal_id}&select=id,converting_channel,attributed_revenue' -H 'apikey: {SUPABASE_ANON_KEY}'"
        }
    },
    {
        "id": "J8.14.9",
        "part_a": "N/A",
        "part_b": "Verify CRM push (if configured)",
        "key_files": ["src/services/crm_push_service.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Check if agency has CRM integration configured",
                "2. If HubSpot: verify deal appears in HubSpot",
                "3. If Pipedrive: verify deal appears in Pipedrive",
                "4. Check crm_push_status field in database",
                "5. Verify no push errors in logs"
            ],
            "expect": {
                "crm_push_status": ["success", "not_configured"],
                "no_errors": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Full flow completes without errors",
    "Meeting created correctly",
    "Deal created from meeting",
    "Attribution calculated",
    "Lead marked as converted"
]

KEY_FILES = [
    "src/api/routes/webhooks.py",
    "src/services/meeting_service.py",
    "src/services/deal_service.py",
    "src/services/crm_push_service.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_live_url(path: str) -> str:
    """Get full URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_frontend_url(path: str) -> str:
    """Get full frontend URL for live testing."""
    base = LIVE_CONFIG["frontend_url"]
    return f"{base}{path}"

def get_supabase_url(path: str) -> str:
    """Get full Supabase URL for database queries."""
    base = LIVE_CONFIG["supabase_url"]
    return f"{base}{path}"

def get_prefect_url(path: str) -> str:
    """Get full Prefect URL."""
    base = LIVE_CONFIG["prefect_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### E2E Flow Steps")
    for i, step in enumerate(E2E_CONSTANTS['flow_steps'], 1):
        lines.append(f"  {i}. {step}")
    lines.append("")
    lines.append("### Test Lead")
    lines.append(f"  - Email: {E2E_CONSTANTS['test_lead']['email']}")
    lines.append(f"  - Name: {E2E_CONSTANTS['test_lead']['name']}")
    lines.append("")
    lines.append("### Expected Final State")
    for key, value in E2E_CONSTANTS['expected_final_state'].items():
        lines.append(f"  - {key}: {value}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
            if lt.get("url"):
                lines.append(f"  URL: {lt['url']}")
            if lt.get("query"):
                lines.append(f"  Query: {lt['query']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command']}")
            if lt.get("steps"):
                lines.append("  Manual Steps:")
                for step in lt["steps"]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
