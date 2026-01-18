"""
Skill: J3.2 - Salesforge Integration
Journey: J3 - Email Outreach
Checks: 6

Purpose: Verify Salesforge is the primary email sender with full API integration.
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
# SALESFORGE CONSTANTS
# =============================================================================

SALESFORGE_CONFIG = {
    "api_base_url": "https://api.salesforge.ai",
    "rate_limit_per_domain": 50,
    "warmforge_compatible": True,
    "tracking_enabled": True,
}

EMAIL_TAGS = {
    "required": ["campaign_id", "lead_id", "client_id"],
    "optional": ["sequence_step", "ab_variant"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.2.1",
        "part_a": "Read `src/integrations/salesforge.py` - verify complete implementation (402 lines)",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/integrations/salesforge.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Salesforge integration is complete with all required methods",
            "expect": {
                "code_contains": ["SalesforgeClient", "send_email", "send_batch", "get_account", "create_sequence"],
                "min_lines": 350
            }
        }
    },
    {
        "id": "J3.2.2",
        "part_a": "Verify `SALESFORGE_API_KEY` env var exists in settings",
        "part_b": "Check Railway vars for SALESFORGE_API_KEY",
        "key_files": ["src/config/settings.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Settings contains SALESFORGE_API_KEY field",
            "expect": {
                "code_contains": ["SALESFORGE_API_KEY"]
            },
            "manual_steps": [
                "1. Run: railway variables --service agency-os --kv | grep SALESFORGE",
                "2. Verify SALESFORGE_API_KEY is set (not empty)",
                "3. Key should start with 'sf_' or similar prefix"
            ]
        }
    },
    {
        "id": "J3.2.3",
        "part_a": "Verify API key format validation in SalesforgeClient",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/integrations/salesforge.py"],
        "live_test": {
            "type": "code_verify",
            "check": "API key validation present in client initialization",
            "expect": {
                "code_contains": ["api_key", "raise", "ValueError", "__init__"]
            }
        }
    },
    {
        "id": "J3.2.4",
        "part_a": "Verify `send_email` method complete with all required parameters",
        "part_b": "Call Salesforge API with test data (TEST_MODE)",
        "key_files": ["src/integrations/salesforge.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/outreach/send-test-email",
            "auth": True,
            "body": {
                "to_email": "test@example.com",
                "subject": "Salesforge Integration Test",
                "body": "Testing Salesforge send_email method via API",
                "from_email": "test@warmforge.domain"
            },
            "expect": {
                "status": [200, 202],
                "body_has_fields": ["message_id", "status"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/outreach/send-test-email' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{\"to_email\": \"test@example.com\", \"subject\": \"Test\", \"body\": \"Test body\"}'""",
            "warning": "Sends real email in TEST_MODE (redirected to test recipient)"
        }
    },
    {
        "id": "J3.2.5",
        "part_a": "Verify batch sending support via `send_batch` method",
        "part_b": "Test batch method with 2-3 test emails",
        "key_files": ["src/integrations/salesforge.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_batch method exists and processes multiple emails",
            "expect": {
                "code_contains": ["send_batch", "List[", "for ", "results"]
            },
            "manual_steps": [
                "1. Check src/integrations/salesforge.py for send_batch method",
                "2. Verify it accepts List of email payloads",
                "3. Verify it returns List of results",
                "4. Verify error handling for partial failures"
            ]
        }
    },
    {
        "id": "J3.2.6",
        "part_a": "Verify tags sent with emails (campaign_id, lead_id, client_id)",
        "part_b": "Check Salesforge dashboard for tagged emails",
        "key_files": ["src/integrations/salesforge.py", "src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'provider_message_id' as message_id,
                       metadata->>'campaign_id' as campaign_id,
                       metadata->>'lead_id' as lead_id,
                       metadata->>'client_id' as client_id
                FROM activities
                WHERE channel = 'email' AND provider = 'salesforge'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "tags_present": ["campaign_id", "lead_id", "client_id"]
            },
            "manual_steps": [
                "1. Send test email via API",
                "2. Check Salesforge dashboard for the email",
                "3. Verify tags are visible in Salesforge UI",
                "4. Verify tags match database activity record"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Salesforge integration is complete (402 lines verified)",
    "API key configured in Railway",
    "Emails send successfully via Salesforge",
    "Tags attached for tracking",
    "Warmforge mailbox compatibility preserved",
    "Rate limit 50/day/domain respected"
]

KEY_FILES = [
    "src/integrations/salesforge.py",
    "src/config/settings.py",
    "src/engines/email.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API URL: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend URL: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase URL: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect URL: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Salesforge Configuration")
    lines.append(f"  API Base: {SALESFORGE_CONFIG['api_base_url']}")
    lines.append(f"  Rate Limit: {SALESFORGE_CONFIG['rate_limit_per_domain']}/day/domain")
    lines.append(f"  Required Tags: {', '.join(EMAIL_TAGS['required'])}")
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
            if lt.get("warning"):
                lines.append(f"  Warning: {lt['warning']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
