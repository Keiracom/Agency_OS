"""
Skill: J7.7 — Lead Status Updates
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify lead status updates based on reply intent.
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
# STATUS UPDATE CONSTANTS
# =============================================================================

LEAD_STATUSES = {
    "new": "Newly added lead",
    "enriched": "Lead data enriched",
    "in_sequence": "Active in outreach sequence",
    "replied": "Lead has replied",
    "converted": "Lead booked meeting or converted",
    "unsubscribed": "Lead opted out",
    "bounced": "Email bounced"
}

INTENT_STATUS_MAP = {
    "meeting_request": {"status": "converted", "action": "Create meeting task"},
    "interested": {"status": "in_sequence", "action": "Create follow-up task"},
    "question": {"status": None, "action": "Create response task"},
    "not_interested": {"status": "enriched", "action": "Pause outreach"},
    "unsubscribe": {"status": "unsubscribed", "action": "Add to suppression list"},
    "out_of_office": {"status": None, "action": "Schedule 2-week follow-up"},
    "auto_reply": {"status": None, "action": "Ignored"}
}

LEAD_TRACKING_FIELDS = {
    "last_replied_at": "Timestamp of last reply",
    "reply_count": "Total number of replies",
    "last_outreach_at": "Last outreach timestamp",
    "next_outreach_at": "Scheduled next outreach"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.7.1",
        "part_a": "Read `_handle_intent` method (closer.py lines 413-498)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_handle_intent method exists with intent routing",
            "expect": {
                "code_contains": ["_handle_intent", "meeting_request", "not_interested", "unsubscribe"]
            }
        }
    },
    {
        "id": "J7.7.2",
        "part_a": "Verify MEETING_REQUEST → CONVERTED status",
        "part_b": "Test meeting request",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.status, a.intent, a.created_at
                FROM leads l
                JOIN activities a ON a.lead_id = l.id
                WHERE a.intent = 'meeting_request'
                AND l.status = 'converted'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "status", "intent"],
                "status_equals": "converted"
            }
        }
    },
    {
        "id": "J7.7.3",
        "part_a": "Verify INTERESTED → stays IN_SEQUENCE",
        "part_b": "Test interested reply",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.status, a.intent
                FROM leads l
                JOIN activities a ON a.lead_id = l.id
                WHERE a.intent = 'interested'
                ORDER BY a.created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "status", "intent"]
            }
        }
    },
    {
        "id": "J7.7.4",
        "part_a": "Verify NOT_INTERESTED → pauses outreach",
        "part_b": "Test not interested",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Not interested intent pauses outreach",
            "expect": {
                "code_contains": ["not_interested", "pause", "outreach", "sequence"]
            }
        }
    },
    {
        "id": "J7.7.5",
        "part_a": "Verify UNSUBSCRIBE → UNSUBSCRIBED status",
        "part_b": "Test unsubscribe",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.status, l.email
                FROM leads l
                WHERE l.status = 'unsubscribed'
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "status", "email"],
                "status_equals": "unsubscribed"
            }
        }
    },
    {
        "id": "J7.7.6",
        "part_a": "Verify OUT_OF_OFFICE → schedules 2-week follow-up",
        "part_b": "Test OOO reply",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "OOO detection schedules follow-up",
            "expect": {
                "code_contains": ["out_of_office", "follow_up", "schedule", "14", "days"]
            }
        }
    },
    {
        "id": "J7.7.7",
        "part_a": "Verify `last_replied_at` and `reply_count` updated",
        "part_b": "Check lead fields",
        "key_files": ["src/engines/closer.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.last_replied_at, l.reply_count, l.updated_at
                FROM leads l
                WHERE l.reply_count > 0
                ORDER BY l.last_replied_at DESC
                LIMIT 5;
            """,
            "expect": {
                "required_fields": ["id", "last_replied_at", "reply_count"],
                "reply_count_gte": 1
            }
        }
    }
]

PASS_CRITERIA = [
    "Status updates correctly per intent",
    "reply_count incremented",
    "last_replied_at updated",
    "Tasks created for actionable intents"
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
    lines.append("### Lead Statuses")
    for status, description in LEAD_STATUSES.items():
        lines.append(f"  {status}: {description}")
    lines.append("")
    lines.append("### Intent to Status Mapping Reference")
    lines.append("| Intent | Status Update | Additional Action |")
    lines.append("|--------|--------------|-------------------|")
    for intent, mapping in INTENT_STATUS_MAP.items():
        status = mapping['status'] or 'No change'
        action = mapping['action']
        lines.append(f"| {intent} | {status} | {action} |")
    lines.append("")
    lines.append("### Lead Tracking Fields")
    for field, description in LEAD_TRACKING_FIELDS.items():
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
