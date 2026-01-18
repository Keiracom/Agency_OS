"""
Skill: J3.8 - Unsubscribe Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify unsubscribe requests are handled correctly and lead status updated.
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
# UNSUBSCRIBE HANDLING CONSTANTS
# =============================================================================

UNSUBSCRIBE_CONFIG = {
    "status_update": "UNSUBSCRIBED",
    "exclude_from_sends": True,
    "compliance": ["CAN-SPAM", "GDPR"],
    "link_required": True,
}

UNSUBSCRIBE_LINK = {
    "placeholder": "{{unsubscribe_link}}",
    "endpoint": "/unsubscribe/{token}",
    "token_expiry_days": None,  # Never expires
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.8.1",
        "part_a": "Read `src/services/email_events_service.py` - verify unsubscribe event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email events service handles unsubscribe events",
            "expect": {
                "code_contains": ["unsubscribe", "UNSUBSCRIBED", "handle_event", "status"]
            }
        }
    },
    {
        "id": "J3.8.2",
        "part_a": "Verify lead status updated to UNSUBSCRIBED on unsubscribe event",
        "part_b": "Simulate unsubscribe webhook, check lead record",
        "key_files": ["src/services/email_events_service.py", "src/models/lead.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/email/salesforge",
            "auth": False,
            "body": {
                "event_type": "unsubscribe",
                "message_id": "test-message-id",
                "email": "unsubscribed@example.com",
                "timestamp": "2024-01-01T00:00:00Z"
            },
            "expect": {
                "status": [200, 202],
                "body_contains": ["processed", "success"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/webhooks/email/salesforge' \\
  -H 'Content-Type: application/json' \\
  -d '{\"event_type\": \"unsubscribe\", \"message_id\": \"test\", \"email\": \"test@example.com\"}'""",
            "note": "Use test message_id that doesn't exist in production"
        }
    },
    {
        "id": "J3.8.3",
        "part_a": "Verify unsubscribed leads excluded from future sends (JIT validation)",
        "part_b": "Attempt send to unsubscribed lead, verify rejection",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.email, l.status, l.updated_at,
                       ee.event_type, ee.created_at as event_time
                FROM lead_pool l
                JOIN email_events ee ON ee.lead_id = l.id
                WHERE l.status = 'UNSUBSCRIBED'
                ORDER BY ee.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "lead_status_unsubscribed": True,
                "event_recorded": True
            },
            "manual_steps": [
                "1. Check outreach_flow.py for JIT validation",
                "2. Verify it checks lead.status != 'UNSUBSCRIBED'",
                "3. Verify send is skipped with appropriate log message",
                "4. Verify no activity created for skipped sends"
            ]
        }
    },
    {
        "id": "J3.8.4",
        "part_a": "Verify unsubscribe link included in emails (CAN-SPAM compliance)",
        "part_b": "Check sent email for unsubscribe link presence",
        "key_files": ["src/engines/email.py", "src/engines/content.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'full_message_body' as body,
                       metadata->>'links_included' as links
                FROM activities
                WHERE channel = 'email'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "body_contains_unsubscribe": True,
                "links_include_unsubscribe": True
            },
            "manual_steps": [
                "1. Send test email",
                "2. Check received email for unsubscribe link",
                "3. Verify link is visible and clickable",
                "4. Click link and verify it works (use test data)",
                "5. Verify lead status changes to UNSUBSCRIBED"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Unsubscribe events update lead status to UNSUBSCRIBED",
    "Unsubscribed leads excluded from JIT validation",
    "Unsubscribe events recorded in email_events table",
    "Emails include unsubscribe link (CAN-SPAM)"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/models/lead.py",
    "src/orchestration/flows/outreach_flow.py",
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
    lines.append("### Unsubscribe Configuration")
    lines.append(f"  Status Update: {UNSUBSCRIBE_CONFIG['status_update']}")
    lines.append(f"  Exclude from Sends: {UNSUBSCRIBE_CONFIG['exclude_from_sends']}")
    lines.append(f"  Compliance: {', '.join(UNSUBSCRIBE_CONFIG['compliance'])}")
    lines.append("")
    lines.append("### Unsubscribe Link")
    lines.append(f"  Placeholder: {UNSUBSCRIBE_LINK['placeholder']}")
    lines.append(f"  Endpoint: {UNSUBSCRIBE_LINK['endpoint']}")
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
            if lt.get("note"):
                lines.append(f"  Note: {lt['note']}")
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:60]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
