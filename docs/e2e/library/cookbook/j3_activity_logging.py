"""
Skill: J3.6 - Activity Logging
Journey: J3 - Email Outreach
Checks: 5

Purpose: Verify all sends create activity records with complete field population.
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

ACTIVITY_FIELDS = {
    "core": ["id", "lead_id", "campaign_id", "client_id", "channel", "action", "created_at"],
    "email_specific": ["provider_message_id", "thread_id", "subject", "from_email", "to_email"],
    "phase_16": ["content_snapshot"],
    "phase_24b": ["template_id", "ab_test_id", "ab_variant"],
}

CONTENT_SNAPSHOT_FIELDS = {
    "required": ["subject", "body", "from_email"],
    "optional": ["html_body", "links", "attachments"],
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J3.6.1",
        "part_a": "Read `_log_activity` method in email.py - verify implementation",
        "part_b": "N/A (code verification only)",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Email engine has _log_activity method that creates activity records",
            "expect": {
                "code_contains": ["_log_activity", "Activity", "session", "add", "commit"]
            }
        }
    },
    {
        "id": "J3.6.2",
        "part_a": "Verify all core fields populated (provider_message_id, thread_id, subject, etc.)",
        "part_b": "Check activity record after test send for all fields",
        "key_files": ["src/engines/email.py", "src/models/activity.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, campaign_id, client_id, channel, action,
                       metadata->>'provider_message_id' as message_id,
                       metadata->>'thread_id' as thread_id,
                       metadata->>'subject' as subject,
                       metadata->>'from_email' as from_email,
                       metadata->>'to_email' as to_email,
                       created_at
                FROM activities
                WHERE channel = 'email'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "all_core_fields_populated": True,
                "message_id_not_null": True
            }
        }
    },
    {
        "id": "J3.6.3",
        "part_a": "Verify content_snapshot stored (Phase 16 requirement)",
        "part_b": "Check activity record for content_snapshot JSON structure",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'content_snapshot' as content_snapshot
                FROM activities
                WHERE channel = 'email' AND metadata->>'content_snapshot' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "content_snapshot_has_subject": True,
                "content_snapshot_has_body": True
            },
            "manual_steps": [
                "1. Query activities for content_snapshot field",
                "2. Parse JSON and verify structure",
                "3. Check for subject, body, from_email at minimum",
                "4. Verify HTML body stored if applicable"
            ]
        }
    },
    {
        "id": "J3.6.4",
        "part_a": "Verify template_id and ab_test_id stored (Phase 24B requirements)",
        "part_b": "Check activity record for Phase 24B fields",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'template_id' as template_id,
                       metadata->>'ab_test_id' as ab_test_id,
                       metadata->>'ab_variant' as ab_variant
                FROM activities
                WHERE channel = 'email'
                ORDER BY created_at DESC
                LIMIT 10;
            """,
            "expect": {
                "rows_exist": True,
                "template_id_tracked": True
            },
            "note": "ab_test_id and ab_variant may be null if not part of A/B test"
        }
    },
    {
        "id": "J3.6.5",
        "part_a": "Verify full_message_body and links_included extracted and stored",
        "part_b": "Check activity record for message body and parsed links",
        "key_files": ["src/engines/email.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'full_message_body' as body,
                       metadata->>'links_included' as links
                FROM activities
                WHERE channel = 'email' AND metadata->>'full_message_body' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "rows_exist": True,
                "body_stored": True,
                "links_parsed": True
            },
            "manual_steps": [
                "1. Send email with links in body",
                "2. Query activity record",
                "3. Verify full_message_body contains complete email",
                "4. Verify links_included is JSON array of URLs"
            ]
        }
    }
]

PASS_CRITERIA = [
    "Activity created on every send",
    "All Phase 16 fields populated (content_snapshot)",
    "All Phase 24B fields populated (template_id, ab_test_id, ab_variant)",
    "Content snapshot captures for CIS learning",
    "Links extracted and stored in links_included"
]

KEY_FILES = [
    "src/engines/email.py",
    "src/models/activity.py",
    "src/services/activity_service.py"
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
    lines.append("### Activity Fields")
    lines.append(f"  Core: {', '.join(ACTIVITY_FIELDS['core'])}")
    lines.append(f"  Email Specific: {', '.join(ACTIVITY_FIELDS['email_specific'])}")
    lines.append(f"  Phase 16: {', '.join(ACTIVITY_FIELDS['phase_16'])}")
    lines.append(f"  Phase 24B: {', '.join(ACTIVITY_FIELDS['phase_24b'])}")
    lines.append("")
    lines.append("### Content Snapshot Structure")
    lines.append(f"  Required: {', '.join(CONTENT_SNAPSHOT_FIELDS['required'])}")
    lines.append(f"  Optional: {', '.join(CONTENT_SNAPSHOT_FIELDS['optional'])}")
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
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
