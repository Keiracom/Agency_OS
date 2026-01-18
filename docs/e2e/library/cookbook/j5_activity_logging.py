"""
Skill: J5.8 — Activity Logging
Journey: J5 - Voice Outreach
Checks: 5

Purpose: Verify all calls create activity records.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "warning": "Activity logging verified through database queries"
}

# =============================================================================
# ACTIVITY LOGGING REQUIREMENTS
# =============================================================================

ACTIVITY_LOGGING = {
    "channel": "voice",
    "required_fields": [
        "lead_id",
        "campaign_id",
        "channel",
        "metadata",
        "created_at"
    ],
    "metadata_fields": {
        "on_start": ["to_number", "from_number", "lead_name", "call_id", "assistant_id"],
        "on_complete": ["duration", "ended_reason", "transcript", "recording_url"]
    },
    "content_snapshot": True  # Phase 16 requirement
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.8.1",
        "part_a": "Read `_log_call_activity` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Activity logging method exists",
            "expect": {
                "code_contains": ["_log_call_activity", "activity", "Activity"]
            }
        }
    },
    {
        "id": "J5.8.2",
        "part_a": "Verify activity created on call initiation",
        "part_b": "Check activity table after call",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, campaign_id, channel, metadata, created_at
                FROM activity
                WHERE channel = 'voice'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "min_rows": 1,
                "required_fields": ["id", "lead_id", "campaign_id", "channel", "metadata"]
            }
        }
    },
    {
        "id": "J5.8.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot field in activity",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, metadata->>'content_snapshot' as content_snapshot
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'content_snapshot' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "content_snapshot_present": True
            }
        }
    },
    {
        "id": "J5.8.4",
        "part_a": "Verify call metadata stored (to_number, from_number, lead_name)",
        "part_b": "Check metadata field in activity",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'to_number' as to_number,
                       metadata->>'from_number' as from_number,
                       metadata->>'lead_name' as lead_name,
                       metadata->>'call_id' as call_id
                FROM activity
                WHERE channel = 'voice'
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "required_fields": ["to_number", "from_number", "lead_name", "call_id"]
            }
        }
    },
    {
        "id": "J5.8.5",
        "part_a": "Verify call completion activity created",
        "part_b": "Check webhook handler creates activity",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'ended_reason' as ended_reason,
                       metadata->>'duration' as duration
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'ended_reason' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "ended_reason_present": True,
                "duration_present": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Activity created on call start",
    "Activity created on call end",
    "All metadata captured"
]

KEY_FILES = [
    "src/engines/voice.py"
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
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Activity Logging Requirements")
    lines.append(f"  Channel: {ACTIVITY_LOGGING['channel']}")
    lines.append(f"  Required Fields: {', '.join(ACTIVITY_LOGGING['required_fields'])}")
    lines.append("  Metadata on Start:")
    for field in ACTIVITY_LOGGING['metadata_fields']['on_start']:
        lines.append(f"    - {field}")
    lines.append("  Metadata on Complete:")
    for field in ACTIVITY_LOGGING['metadata_fields']['on_complete']:
        lines.append(f"    - {field}")
    lines.append(f"  Content Snapshot: {ACTIVITY_LOGGING['content_snapshot']}")
    lines.append("")
    lines.append("### Checks")
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
