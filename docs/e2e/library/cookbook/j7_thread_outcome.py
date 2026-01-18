"""
Skill: J7.9 — Thread Outcome (Phase 24D)
Journey: J7 - Reply Handling
Checks: 4

Purpose: Verify thread outcomes are set based on reply intent.
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
# THREAD OUTCOME CONSTANTS
# =============================================================================

THREAD_OUTCOMES = {
    "meeting_booked": "Lead scheduled a meeting",
    "rejected": "Lead explicitly declined",
    "unsubscribed": "Lead opted out of communications",
    "converted": "Lead moved to opportunity stage",
    "no_response": "Thread went stale without response"
}

INTENT_TO_OUTCOME_MAP = {
    "meeting_request": "meeting_booked",
    "not_interested": "rejected",
    "unsubscribe": "rejected"
}

OUTCOME_CLOSERS = {
    "meeting_booked": "Positive close - meeting scheduled",
    "rejected": "Negative close - explicit decline",
    "unsubscribed": "Negative close - opted out",
    "no_response": "Neutral close - timeout"
}

ACTIVE_INTENTS = ["interested", "question", "out_of_office", "auto_reply"]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.9.1",
        "part_a": "Read `_update_thread_outcome` method (closer.py lines 568-601)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_update_thread_outcome method exists",
            "expect": {
                "code_contains": ["_update_thread_outcome", "outcome", "set_outcome"]
            }
        }
    },
    {
        "id": "J7.9.2",
        "part_a": "Verify meeting_request → outcome=\"meeting_booked\"",
        "part_b": "Test meeting reply",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.id, ct.outcome, ct.outcome_reason, ct.lead_id, ct.status
                FROM conversation_threads ct
                WHERE ct.outcome = 'meeting_booked'
                ORDER BY ct.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "outcome", "lead_id"],
                "outcome_equals": "meeting_booked"
            }
        }
    },
    {
        "id": "J7.9.3",
        "part_a": "Verify not_interested/unsubscribe → outcome=\"rejected\"",
        "part_b": "Test rejection",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.id, ct.outcome, ct.outcome_reason, ct.status
                FROM conversation_threads ct
                WHERE ct.outcome = 'rejected'
                ORDER BY ct.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "outcome", "status"],
                "outcome_equals": "rejected",
                "status_equals": "closed"
            }
        }
    },
    {
        "id": "J7.9.4",
        "part_a": "Verify interested/question → thread stays active",
        "part_b": "Test positive reply",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ct.id, ct.status, ct.outcome,
                       (SELECT a.intent FROM activities a
                        WHERE a.conversation_thread_id = ct.id
                        ORDER BY a.created_at DESC LIMIT 1) as last_intent
                FROM conversation_threads ct
                WHERE ct.status = 'active'
                ORDER BY ct.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "status"],
                "status_equals": "active",
                "outcome_is_null": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Thread outcome set correctly",
    "Outcome reason captured",
    "Positive intents keep thread active",
    "Negative intents close thread"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/services/thread_service.py"
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
    lines.append("### Thread Outcomes")
    for outcome, description in THREAD_OUTCOMES.items():
        lines.append(f"  {outcome}: {description}")
    lines.append("")
    lines.append("### Intent to Outcome Mapping")
    for intent, outcome in INTENT_TO_OUTCOME_MAP.items():
        lines.append(f"  {intent} -> {outcome}")
    lines.append("")
    lines.append("### Active Intents (Thread Stays Open)")
    lines.append(f"  {', '.join(ACTIVE_INTENTS)}")
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
