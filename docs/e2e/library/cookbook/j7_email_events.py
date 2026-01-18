"""
Skill: J7.12 — Email Event Webhooks (Opens/Clicks/Bounces)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify email engagement events are tracked.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app"
}

# =============================================================================
# EMAIL EVENT CONSTANTS
# =============================================================================

WEBHOOK_ENDPOINTS = {
    "postmark_bounce": "/webhooks/postmark/bounce",
    "postmark_spam": "/webhooks/postmark/spam",
    "resend_events": "/webhooks/email/resend",
    "salesforge_events": "/webhooks/salesforge/events"
}

EMAIL_EVENT_TYPES = {
    "sent": "Email successfully sent",
    "delivered": "Email delivered to recipient",
    "opened": "Email opened (tracking pixel)",
    "clicked": "Link in email clicked",
    "bounced": "Email bounced (hard or soft)",
    "complained": "Marked as spam",
    "unsubscribed": "Clicked unsubscribe link"
}

BOUNCE_TYPES = {
    "hard": "Permanent delivery failure (invalid email)",
    "soft": "Temporary delivery failure (mailbox full, etc.)"
}

EVENT_TO_STATUS_MAP = {
    "bounced": "bounced",
    "complained": "unsubscribed",
    "unsubscribed": "unsubscribed"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.12.1",
        "part_a": "Read `/webhooks/postmark/bounce` endpoint (line 340)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Postmark bounce webhook endpoint exists",
            "expect": {
                "code_contains": ["/webhooks/postmark/bounce", "async def", "bounce"]
            }
        }
    },
    {
        "id": "J7.12.2",
        "part_a": "Read `/webhooks/postmark/spam` endpoint (line 410)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Postmark spam complaint webhook exists",
            "expect": {
                "code_contains": ["/webhooks/postmark/spam", "spam", "complaint"]
            }
        }
    },
    {
        "id": "J7.12.3",
        "part_a": "Read `/webhooks/email/resend` endpoint (line 1169)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/webhooks/email/resend",
            "auth": False,
            "body": {
                "type": "email.opened",
                "data": {
                    "email_id": "test-email-001",
                    "to": "test@example.com",
                    "opened_at": "2026-01-18T10:00:00Z"
                }
            },
            "expect": {
                "status": 200
            },
            "curl_command": """curl -X POST '{api_url}/webhooks/email/resend' \\
  -H 'Content-Type: application/json' \\
  -d '{"type": "email.opened", "data": {"email_id": "test-001"}}'"""
        }
    },
    {
        "id": "J7.12.4",
        "part_a": "Read `/webhooks/salesforge/events` endpoint (line 1003)",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Salesforge event webhook exists",
            "expect": {
                "code_contains": ["/webhooks/salesforge", "events", "salesforge"]
            }
        }
    },
    {
        "id": "J7.12.5",
        "part_a": "Verify bounce updates lead status",
        "part_b": "Test bounce event",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.status, l.email, l.updated_at
                FROM leads l
                WHERE l.status = 'bounced'
                ORDER BY l.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "status", "email"],
                "status_equals": "bounced"
            }
        }
    },
    {
        "id": "J7.12.6",
        "part_a": "Verify spam complaint triggers unsubscribe",
        "part_b": "Test spam event",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Spam complaint triggers unsubscribe status",
            "expect": {
                "code_contains": ["spam", "unsubscribe", "complained", "status"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Bounce webhook updates lead",
    "Spam complaint triggers unsubscribe",
    "Opens/clicks tracked in activity"
]

KEY_FILES = [
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
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Webhook Endpoints")
    for name, endpoint in WEBHOOK_ENDPOINTS.items():
        lines.append(f"  {name}: {endpoint}")
    lines.append("")
    lines.append("### Event Types Tracked")
    for event, description in EMAIL_EVENT_TYPES.items():
        lines.append(f"  {event}: {description}")
    lines.append("")
    lines.append("### Bounce Types")
    for bounce_type, description in BOUNCE_TYPES.items():
        lines.append(f"  {bounce_type}: {description}")
    lines.append("")
    lines.append("### Event to Status Mapping")
    for event, status in EVENT_TO_STATUS_MAP.items():
        lines.append(f"  {event} -> {status}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
