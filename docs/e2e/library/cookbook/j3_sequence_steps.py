"""
Skill: J3.11 - Sequence Steps
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify email sequence steps execute correctly with proper threading.
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
# SEQUENCE CONSTANTS
# =============================================================================

SEQUENCE_CONFIG = {
    "max_steps": 5,
    "default_wait_days": [3, 5, 7],  # Days between steps 1-2, 2-3, 3-4
    "threading_required": True,
}

THREADING_CONFIG = {
    "step_1": {
        "is_followup": False,
        "in_reply_to": None,
        "references": None,
    },
    "step_2_plus": {
        "is_followup": True,
        "in_reply_to": "previous_message_id",
        "references": "all_previous_message_ids",
    },
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.11.1",
        "part_a": "Read `src/orchestration/flows/outreach_flow.py` - verify sequence step handling",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Outreach flow handles sequence steps with proper increment",
            "expect": {
                "code_contains": ["sequence_step", "is_followup", "step", "increment"]
            }
        }
    },
    {
        "id": "J3.11.2",
        "part_a": "Verify sequence_step incremented correctly on each send",
        "part_b": "Send sequence of emails, check step numbers",
        "key_files": ["src/orchestration/flows/outreach_flow.py", "src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT lead_id, metadata->>'sequence_step' as step,
                       metadata->>'thread_id' as thread_id,
                       created_at
                FROM activities
                WHERE channel = 'email'
                ORDER BY lead_id, created_at
                LIMIT 20;
            """,
            "expect": {
                "rows_exist": True,
                "steps_increment": True,
                "thread_id_consistent": True
            },
            "manual_steps": [
                "1. Find a lead with multiple email activities",
                "2. Verify step numbers are 1, 2, 3 in order",
                "3. Verify thread_id is same across all steps",
                "4. Verify created_at shows appropriate time gaps"
            ]
        }
    },
    {
        "id": "J3.11.3",
        "part_a": "Verify is_followup flag set correctly for steps > 1",
        "part_b": "Check email headers for threading on step 2+",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "is_followup flag triggers threading headers",
            "expect": {
                "code_contains": ["is_followup", "sequence_step", "> 1", "In-Reply-To"]
            },
            "manual_steps": [
                "1. Check email.py for is_followup handling",
                "2. Verify step > 1 sets is_followup = True",
                "3. Verify is_followup triggers In-Reply-To header",
                "4. Check received follow-up email for threading"
            ]
        }
    },
    {
        "id": "J3.11.4",
        "part_a": "Verify thread_id maintained across sequence steps",
        "part_b": "Check activity records for consistent thread_id",
        "key_files": ["src/engines/email.py", "src/models/activity.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT lead_id,
                       COUNT(DISTINCT metadata->>'thread_id') as unique_threads,
                       COUNT(*) as total_emails
                FROM activities
                WHERE channel = 'email' AND lead_id IS NOT NULL
                GROUP BY lead_id
                HAVING COUNT(*) > 1
                ORDER BY total_emails DESC
                LIMIT 10;
            """,
            "expect": {
                "rows_exist": True,
                "one_thread_per_lead": True
            },
            "manual_steps": [
                "1. Query leads with multiple email activities",
                "2. Verify each lead has exactly 1 unique thread_id",
                "3. If multiple thread_ids found, investigate why",
                "4. Verify threading visible in email client"
            ]
        }
    },
    {
        "id": "J3.11.5",
        "part_a": "Verify sequence respects wait times between steps",
        "part_b": "Check Prefect flow scheduling for step delays",
        "key_files": ["src/orchestration/flows/outreach_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Sequence steps scheduled with appropriate delays",
            "expect": {
                "code_contains": ["wait_days", "schedule", "delay", "timedelta"]
            },
            "manual_steps": [
                "1. Check outreach_flow.py for step scheduling",
                "2. Verify wait times configurable per sequence",
                "3. Check Prefect UI for scheduled future runs",
                "4. Verify step 2 not sent immediately after step 1"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Sequence steps increment correctly (1, 2, 3...)",
    "is_followup flag triggers threading for step 2+",
    "Thread ID maintained across all sequence steps",
    "Wait times between steps respected",
    "Emails appear threaded in recipient inbox"
]

KEY_FILES = [
    "src/orchestration/flows/outreach_flow.py",
    "src/engines/email.py",
    "src/models/activity.py",
    "src/models/sequence.py"
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
    lines.append("### Sequence Configuration")
    lines.append(f"  Max Steps: {SEQUENCE_CONFIG['max_steps']}")
    lines.append(f"  Default Wait Days: {SEQUENCE_CONFIG['default_wait_days']}")
    lines.append(f"  Threading Required: {SEQUENCE_CONFIG['threading_required']}")
    lines.append("")
    lines.append("### Threading Configuration")
    lines.append("  Step 1: No threading (initial email)")
    lines.append("  Step 2+: In-Reply-To and References headers set")
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
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
