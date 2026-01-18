"""
Skill: J7.10 — Activity Logging
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify all replies create comprehensive activity records.
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
# ACTIVITY LOGGING CONSTANTS
# =============================================================================

ACTIVITY_ACTIONS = {
    "replied": "Inbound reply from lead",
    "email_sent": "Outbound email sent",
    "sms_sent": "Outbound SMS sent",
    "linkedin_message_sent": "Outbound LinkedIn message",
    "call_completed": "Voice call completed"
}

ACTIVITY_CHANNELS = ["email", "sms", "linkedin", "voice"]

ACTIVITY_FIELDS = {
    "action": "Type of activity (replied, sent, etc.)",
    "channel": "Communication channel",
    "intent": "Classified intent from AI",
    "intent_confidence": "Confidence score (0.0-1.0)",
    "provider_message_id": "External provider's message ID",
    "in_reply_to": "ID of message being replied to",
    "content_preview": "First 500 chars of message",
    "conversation_thread_id": "Link to conversation thread"
}

METADATA_FIELDS = {
    "message_preview": "Shortened content preview",
    "message_length": "Full message character count",
    "sentiment": "Detected sentiment",
    "objection_type": "Detected objection if any"
}

CONTENT_PREVIEW_LENGTH = 500

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.10.1",
        "part_a": "Read `_log_reply_activity` method (closer.py lines 356-411)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_log_reply_activity method exists",
            "expect": {
                "code_contains": ["_log_reply_activity", "Activity", "create"]
            }
        }
    },
    {
        "id": "J7.10.2",
        "part_a": "Verify action=\"replied\"",
        "part_b": "Check activity.action",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.action, a.channel, a.created_at
                FROM activities a
                WHERE a.action = 'replied'
                ORDER BY a.created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "required_fields": ["id", "action", "channel"],
                "action_equals": "replied"
            }
        }
    },
    {
        "id": "J7.10.3",
        "part_a": "Verify intent and intent_confidence stored",
        "part_b": "Check activity fields",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.intent, a.intent_confidence, a.action
                FROM activities a
                WHERE a.action = 'replied'
                AND a.intent IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "intent", "intent_confidence"],
                "intent_confidence_range": [0.0, 1.0]
            }
        }
    },
    {
        "id": "J7.10.4",
        "part_a": "Verify content_preview stored (500 chars)",
        "part_b": "Check preview",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.content_preview, LENGTH(a.content_preview) as preview_len
                FROM activities a
                WHERE a.action = 'replied'
                AND a.content_preview IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "content_preview"],
                "preview_len_lte": 500
            }
        }
    },
    {
        "id": "J7.10.5",
        "part_a": "Verify conversation_thread_id linked",
        "part_b": "Check thread link",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.conversation_thread_id, ct.status as thread_status
                FROM activities a
                LEFT JOIN conversation_threads ct ON ct.id = a.conversation_thread_id
                WHERE a.action = 'replied'
                AND a.conversation_thread_id IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "conversation_thread_id"]
            }
        }
    },
    {
        "id": "J7.10.6",
        "part_a": "Verify provider_message_id stored",
        "part_b": "Check dedup field",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.provider_message_id, a.channel
                FROM activities a
                WHERE a.action = 'replied'
                AND a.provider_message_id IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "provider_message_id", "channel"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Activity created for every reply",
    "Intent classification recorded",
    "Thread linked",
    "Deduplication by provider_message_id"
]

KEY_FILES = [
    "src/engines/closer.py"
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
    lines.append("### Activity Actions")
    for action, description in ACTIVITY_ACTIONS.items():
        lines.append(f"  {action}: {description}")
    lines.append("")
    lines.append("### Activity Channels")
    lines.append(f"  {', '.join(ACTIVITY_CHANNELS)}")
    lines.append("")
    lines.append("### Activity Fields Reference")
    for field, description in ACTIVITY_FIELDS.items():
        lines.append(f"  {field}: {description}")
    lines.append("")
    lines.append("### Metadata Fields")
    for field, description in METADATA_FIELDS.items():
        lines.append(f"  {field}: {description}")
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
