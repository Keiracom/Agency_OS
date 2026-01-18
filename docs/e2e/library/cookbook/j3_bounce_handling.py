"""
Skill: J3.7 - Bounce Handling
Journey: J3 - Email Outreach
Checks: 4

Purpose: Verify bounced emails are handled correctly and lead status updated.
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
# BOUNCE HANDLING CONSTANTS
# =============================================================================

BOUNCE_TYPES = {
    "hard": {
        "status_update": "BOUNCED",
        "exclude_from_sends": True,
        "reasons": ["invalid_email", "domain_not_found", "mailbox_full_permanent"]
    },
    "soft": {
        "status_update": None,
        "exclude_from_sends": False,
        "reasons": ["mailbox_full_temporary", "server_busy", "quota_exceeded"]
    }
}

WEBHOOK_EVENTS = {
    "bounce": ["hard_bounce", "soft_bounce"],
    "endpoint": "/api/v1/webhooks/email/salesforge"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.7.1",
        "part_a": "Read `src/services/email_events_service.py` - verify bounce event handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/services/email_events_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email events service handles bounce events",
            "expect": {
                "code_contains": ["bounce", "hard_bounce", "soft_bounce", "handle_event", "process"]
            }
        }
    },
    {
        "id": "J3.7.2",
        "part_a": "Verify hard bounce vs soft bounce differentiation in event processing",
        "part_b": "Simulate both bounce types via webhook, check handling",
        "key_files": ["src/services/email_events_service.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/webhooks/email/salesforge",
            "auth": False,
            "body": {
                "event_type": "hard_bounce",
                "message_id": "test-message-id",
                "email": "bounced@example.com",
                "reason": "invalid_email",
                "timestamp": "2024-01-01T00:00:00Z"
            },
            "expect": {
                "status": [200, 202],
                "body_contains": ["processed", "success"]
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/webhooks/email/salesforge' \\
  -H 'Content-Type: application/json' \\
  -d '{\"event_type\": \"hard_bounce\", \"message_id\": \"test\", \"email\": \"test@example.com\"}'""",
            "note": "Use test message_id that doesn't exist in production"
        }
    },
    {
        "id": "J3.7.3",
        "part_a": "Verify lead status updated to BOUNCED on hard bounce",
        "part_b": "Check lead record after hard bounce event",
        "key_files": ["src/services/email_events_service.py", "src/models/lead.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.email, l.status, l.updated_at,
                       ee.event_type, ee.created_at as event_time
                FROM lead_pool l
                JOIN email_events ee ON ee.lead_id = l.id
                WHERE ee.event_type = 'hard_bounce'
                ORDER BY ee.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "lead_status_bounced": True,
                "event_recorded": True
            },
            "manual_steps": [
                "1. Find a lead with hard bounce event",
                "2. Verify lead status = 'BOUNCED'",
                "3. Verify timestamp shows status changed after bounce",
                "4. Verify bounced leads excluded from future sends"
            ]
        }
    },
    {
        "id": "J3.7.4",
        "part_a": "Verify bounced leads excluded from future sends (JIT validation)",
        "part_b": "Attempt send to bounced lead, verify rejection",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "JIT validation excludes bounced leads from sends",
            "expect": {
                "code_contains": ["BOUNCED", "exclude", "skip", "validation", "status"]
            },
            "manual_steps": [
                "1. Check outreach_flow.py for JIT validation",
                "2. Verify it checks lead.status != 'BOUNCED'",
                "3. Verify send is skipped with appropriate log message",
                "4. Verify no activity created for skipped sends"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Hard bounces update lead status to BOUNCED",
    "Soft bounces logged but lead status unchanged",
    "Bounced leads excluded from JIT validation",
    "Bounce events recorded in email_events table"
]

KEY_FILES = [
    "src/services/email_events_service.py",
    "src/models/lead.py",
    "src/orchestration/flows/outreach_flow.py",
    "src/api/routes/webhooks.py"
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
    lines.append("### Bounce Types")
    for bounce_type, config in BOUNCE_TYPES.items():
        lines.append(f"  {bounce_type.upper()}:")
        lines.append(f"    Status Update: {config['status_update']}")
        lines.append(f"    Exclude from Sends: {config['exclude_from_sends']}")
    lines.append("")
    lines.append("### Webhook Endpoint")
    lines.append(f"  {WEBHOOK_EVENTS['endpoint']}")
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
