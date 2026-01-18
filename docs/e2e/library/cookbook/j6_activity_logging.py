"""
Skill: J6.9 — Activity Logging
Journey: J6 - LinkedIn Outreach
Checks: 5

Purpose: Verify all LinkedIn actions create proper activity records.
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
# ACTIVITY LOGGING CONSTANTS
# =============================================================================

LINKEDIN_ACTIVITY_TYPES = {
    "connection_sent": "Connection request sent",
    "connection_accepted": "Connection request accepted",
    "connection_rejected": "Connection request rejected",
    "message_sent": "Direct message sent",
    "message_received": "Reply received",
    "profile_viewed": "Profile viewed",
}

ACTIVITY_REQUIRED_FIELDS = [
    "id",
    "lead_id",
    "campaign_id",
    "action",
    "channel",
    "created_at",
]

ACTIVITY_OPTIONAL_FIELDS = [
    "content_snapshot",
    "template_id",
    "metadata",
    "external_id",
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J6.9.1",
        "part_a": "Read `_log_activity` method in linkedin.py",
        "part_b": "N/A",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Activity logging method exists with required fields",
            "expect": {
                "code_contains": ["_log_activity", "activity", "lead_id", "action"]
            }
        }
    },
    {
        "id": "J6.9.2",
        "part_a": "Verify all required fields populated",
        "part_b": "Check activity schema",
        "key_files": ["src/models/activity.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, campaign_id, action, channel, created_at
                FROM activity
                WHERE channel = 'linkedin'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "all_fields_present": True,
                "required_fields": ["id", "lead_id", "action", "channel"]
            }
        }
    },
    {
        "id": "J6.9.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot field",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, action, content_snapshot
                FROM activity
                WHERE channel = 'linkedin'
                  AND content_snapshot IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_content_snapshot": True
            }
        }
    },
    {
        "id": "J6.9.4",
        "part_a": "Verify template_id stored (Phase 24B)",
        "part_b": "Check field when using templates",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "code_verify",
            "check": "template_id captured in activity when available",
            "expect": {
                "code_contains": ["template_id", "activity"]
            }
        }
    },
    {
        "id": "J6.9.5",
        "part_a": "Verify message_type tracked (connection vs message)",
        "part_b": "Check action field values",
        "key_files": ["src/engines/linkedin.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT action, COUNT(*) as count
                FROM activity
                WHERE channel = 'linkedin'
                  AND action IN ('connection_sent', 'message_sent')
                GROUP BY action;
            """,
            "expect": {
                "distinguishes_types": True,
                "valid_actions": ["connection_sent", "message_sent"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Activity created on every LinkedIn action",
    "Connection vs message distinguished by action field",
    "All required fields populated",
    "Content snapshot stored for analytics (Phase 16)",
    "Template ID tracked when using templates (Phase 24B)"
]

KEY_FILES = [
    "src/engines/linkedin.py",
    "src/models/activity.py"
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
    lines.append("### LinkedIn Activity Types")
    for action, description in LINKEDIN_ACTIVITY_TYPES.items():
        lines.append(f"  {action}: {description}")
    lines.append("")
    lines.append("### Required Activity Fields")
    lines.append(f"  {', '.join(ACTIVITY_REQUIRED_FIELDS)}")
    lines.append("")
    lines.append("### Optional Activity Fields")
    lines.append(f"  {', '.join(ACTIVITY_OPTIONAL_FIELDS)}")
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
