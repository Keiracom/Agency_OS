"""
Skill: J7.6 — Conversation Threading (Phase 24D)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify conversation threads are created and managed.
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
# THREADING CONSTANTS
# =============================================================================

THREAD_STATUSES = {
    "active": "Ongoing conversation",
    "stale": "No activity for 7+ days",
    "closed": "Conversation ended with outcome"
}

THREAD_OUTCOMES = {
    "meeting_booked": "Lead booked a meeting",
    "rejected": "Lead explicitly declined",
    "unsubscribed": "Lead unsubscribed",
    "converted": "Lead converted to opportunity",
    "no_response": "Lead stopped responding"
}

MESSAGE_DIRECTIONS = {
    "inbound": "Message from lead to us",
    "outbound": "Message from us to lead"
}

CHANNEL_TYPES = ["email", "sms", "linkedin", "voice"]

STALE_THRESHOLD_DAYS = 7

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.6.1",
        "part_a": "Read `src/services/thread_service.py` — verify complete",
        "part_b": "N/A",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Thread service exists with required methods",
            "expect": {
                "code_contains": [
                    "ThreadService", "create_thread", "get_by_id",
                    "get_or_create_for_lead", "add_message", "update_status"
                ]
            }
        }
    },
    {
        "id": "J7.6.2",
        "part_a": "Verify `get_or_create_for_lead` method",
        "part_b": "Test thread creation",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.id, ct.lead_id, ct.channel, ct.status, ct.created_at
                FROM conversation_threads ct
                ORDER BY ct.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "lead_id", "channel", "status"]
            }
        }
    },
    {
        "id": "J7.6.3",
        "part_a": "Verify thread status: active, stale, closed",
        "part_b": "Check status transitions",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.status, COUNT(*) as count
                FROM conversation_threads ct
                GROUP BY ct.status;
            """,
            "expect": {
                "required_fields": ["status", "count"],
                "status_in": ["active", "stale", "closed"]
            }
        }
    },
    {
        "id": "J7.6.4",
        "part_a": "Verify `add_message` method",
        "part_b": "Test message adding",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT tm.id, tm.thread_id, tm.direction, tm.content_preview,
                       tm.sentiment, tm.position, tm.created_at
                FROM thread_messages tm
                ORDER BY tm.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "thread_id", "direction", "position"]
            }
        }
    },
    {
        "id": "J7.6.5",
        "part_a": "Verify message direction: inbound vs outbound",
        "part_b": "Check direction set",
        "key_files": ["src/services/thread_service.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT tm.direction, COUNT(*) as count
                FROM thread_messages tm
                GROUP BY tm.direction;
            """,
            "expect": {
                "required_fields": ["direction", "count"],
                "direction_in": ["inbound", "outbound"]
            }
        }
    },
    {
        "id": "J7.6.6",
        "part_a": "Verify activity linked to thread (conversation_thread_id)",
        "part_b": "Check activity.conversation_thread_id",
        "key_files": ["src/services/thread_service.py", "src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT a.id, a.action, a.conversation_thread_id, a.created_at
                FROM activities a
                WHERE a.conversation_thread_id IS NOT NULL
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "action", "conversation_thread_id"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Thread created on first reply",
    "Existing thread reused for same lead/channel",
    "Messages tracked with position",
    "Activity linked to thread"
]

KEY_FILES = [
    "src/services/thread_service.py",
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
    lines.append("### Thread Statuses")
    for status, description in THREAD_STATUSES.items():
        lines.append(f"  {status}: {description}")
    lines.append("")
    lines.append("### Thread Outcomes")
    for outcome, description in THREAD_OUTCOMES.items():
        lines.append(f"  {outcome}: {description}")
    lines.append("")
    lines.append("### Message Directions")
    for direction, description in MESSAGE_DIRECTIONS.items():
        lines.append(f"  {direction}: {description}")
    lines.append("")
    lines.append("### ThreadService Methods Reference")
    lines.append("- `create_thread()` — Create new conversation thread")
    lines.append("- `get_by_id()` — Get thread by UUID")
    lines.append("- `get_or_create_for_lead()` — Find existing or create new")
    lines.append("- `add_message()` — Add message with sentiment/intent/objection")
    lines.append("- `update_status()` — Update thread status")
    lines.append("- `set_outcome()` — Set final outcome (meeting_booked, rejected, etc.)")
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
