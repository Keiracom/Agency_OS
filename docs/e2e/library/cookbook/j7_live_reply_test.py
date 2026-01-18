"""
Skill: J7.14 — Live Reply Test (All Channels)
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify real replies work end-to-end.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "client_id": "81dbaee6-4e71-48ad-be40-fa915fae66e0",
    "user_id": "a60bcdbd-4a31-43e7-bcc8-3ab998c44ac2",
    "test_email": "david.stephens@keiracom.com",
    "test_phone": "+61457543392",
}

# =============================================================================
# TEST RECIPIENTS CONFIGURATION
# =============================================================================

TEST_RECIPIENTS = {
    "email": "david.stephens@keiracom.com",
    "phone": "+61457543392",
    "linkedin": "https://www.linkedin.com/in/david-stephens-8847a636a/"
}

TEST_MODE_SETTING = "settings.TEST_MODE"

REQUIRED_PRIOR_TESTS = [
    "J3 - Email Outreach (to have sent email)",
    "J4 - SMS Outreach (to have sent SMS)",
    "J6 - LinkedIn Outreach (to have sent connection/message)"
]

# =============================================================================
# CHANNEL TEST PATTERNS
# =============================================================================

CHANNEL_TEST_PATTERNS = {
    "email": {
        "send_reply_to": "Reply to any outreach email",
        "webhook": "/webhooks/postmark/inbound",
        "match_field": "email"
    },
    "sms": {
        "send_reply_to": "Reply to any SMS from +61457543392",
        "webhook": "/webhooks/twilio/inbound",
        "match_field": "phone"
    },
    "linkedin": {
        "send_reply_to": "Reply to connection request or message",
        "webhook": "/webhooks/unipile/inbound",
        "match_field": "linkedin_url"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.14.1",
        "part_a": "N/A",
        "part_b": "Send email reply to outreach message",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Find an outreach email sent during J3 testing",
                "2. Reply to the email with an interested message",
                "3. Wait 30 seconds for webhook processing",
                "4. Check activities table for new 'replied' entry"
            ],
            "expect": {
                "activity_created": True,
                "channel": "email",
                "action": "replied"
            }
        }
    },
    {
        "id": "J7.14.2",
        "part_a": "N/A",
        "part_b": "Reply to SMS message",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Find an SMS sent during J4 testing",
                "2. Reply to the SMS from test phone",
                "3. Wait 30 seconds for webhook processing",
                "4. Check activities table for new 'replied' entry"
            ],
            "expect": {
                "activity_created": True,
                "channel": "sms",
                "action": "replied"
            }
        }
    },
    {
        "id": "J7.14.3",
        "part_a": "N/A",
        "part_b": "Reply to LinkedIn connection/message",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Find a LinkedIn connection request or message from J6 testing",
                "2. Accept connection and/or reply to message",
                "3. Wait 30 seconds for webhook processing",
                "4. Check activities table for new 'replied' entry"
            ],
            "expect": {
                "activity_created": True,
                "channel": "linkedin",
                "action": "replied"
            }
        }
    },
    {
        "id": "J7.14.4",
        "part_a": "N/A",
        "part_b": "Verify intent classified correctly",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.intent, a.intent_confidence, a.channel, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                ORDER BY a.created_at DESC
                LIMIT 3;
            """,
            "expect": {
                "required_fields": ["id", "intent", "intent_confidence"],
                "intent_is_not_null": True,
                "confidence_gte": 0.5
            }
        }
    },
    {
        "id": "J7.14.5",
        "part_a": "N/A",
        "part_b": "Verify thread created",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.id, ct.lead_id, ct.channel, ct.status, ct.created_at
                FROM conversation_threads ct
                ORDER BY ct.created_at DESC
                LIMIT 3;
            """,
            "expect": {
                "required_fields": ["id", "lead_id", "channel", "status"],
                "status_in": ["active", "closed"]
            }
        }
    },
    {
        "id": "J7.14.6",
        "part_a": "N/A",
        "part_b": "Verify lead status updated",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.status, l.last_replied_at, l.reply_count, l.email
                FROM leads l
                WHERE l.reply_count > 0
                ORDER BY l.last_replied_at DESC
                LIMIT 3;
            """,
            "expect": {
                "required_fields": ["id", "status", "last_replied_at", "reply_count"],
                "reply_count_gte": 1
            }
        }
    },
    {
        "id": "J7.14.7",
        "part_a": "N/A",
        "part_b": "Verify activity logged",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.lead_id, a.action, a.channel, a.intent,
                       a.content_preview, a.conversation_thread_id
                FROM activities a
                WHERE a.action = 'replied'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "lead_id", "action", "channel"],
                "content_preview_not_null": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Email reply processed successfully",
    "SMS reply processed successfully",
    "LinkedIn reply processed successfully",
    "Intent classification accurate",
    "Conversation thread created",
    "Lead status updated per intent"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/services/thread_service.py",
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
    lines.append("### Test Recipients Reference")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    for field, value in TEST_RECIPIENTS.items():
        lines.append(f"| Test {field.title()} | {value} |")
    lines.append(f"| TEST_MODE Setting | `{TEST_MODE_SETTING}` |")
    lines.append("")
    lines.append("### Required Prior Tests")
    lines.append("Note: Replies must match leads created during J3-J6 testing")
    for test in REQUIRED_PRIOR_TESTS:
        lines.append(f"  - {test}")
    lines.append("")
    lines.append("### Channel Test Patterns")
    for channel, pattern in CHANNEL_TEST_PATTERNS.items():
        lines.append(f"  {channel}:")
        lines.append(f"    Action: {pattern['send_reply_to']}")
        lines.append(f"    Webhook: {pattern['webhook']}")
        lines.append(f"    Match By: {pattern['match_field']}")
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
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"][:3]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
