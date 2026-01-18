"""
Skill: J4.7 — Activity Logging
Journey: J4 - SMS Outreach
Checks: 5

Purpose: Verify all sends create activity records with Phase 16/24B fields.
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
# SMS DOMAIN CONSTANTS
# =============================================================================

ACTIVITY_ACTIONS = {
    "sms_sent": "SMS successfully sent",
    "sms_delivered": "SMS confirmed delivered",
    "sms_failed": "SMS send failed",
    "sms_reply": "SMS reply received",
    "sms_optout": "Lead opted out via STOP",
    "rejected_dncr": "SMS blocked by DNCR"
}

PHASE_16_FIELDS = {
    "content_snapshot": {
        "description": "Full content at time of send",
        "fields": ["message_body", "char_count", "encoding", "segments"]
    },
    "conversion_tracking": {
        "description": "Link click and conversion data",
        "fields": ["links_included", "click_tracked", "conversion_value"]
    }
}

PHASE_24B_FIELDS = {
    "ab_testing": {
        "description": "A/B test variant tracking",
        "fields": ["template_id", "ab_test_id", "ab_variant"]
    }
}

SMS_ACTIVITY_REQUIRED_FIELDS = [
    "lead_id",
    "action",
    "channel",
    "provider_message_id",
    "sequence_step",
    "content_preview",
    "metadata"
]

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.7.1",
        "part_a": "Read `_log_activity` method in sms.py",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "_log_activity method exists and logs SMS events",
            "expect": {
                "code_contains": ["_log_activity", "Activity", "create"]
            }
        }
    },
    {
        "id": "J4.7.2",
        "part_a": "Verify all fields populated (provider_message_id, sequence_step, content_preview)",
        "part_b": "Check activity schema",
        "key_files": ["src/engines/sms.py", "src/models/activity.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id, lead_id, action, channel,
                       metadata->>'provider_message_id' as provider_message_id,
                       metadata->>'sequence_step' as sequence_step,
                       content_preview
                FROM activity
                WHERE channel = 'sms'
                  AND action = 'sms_sent'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "required_fields": ["provider_message_id", "sequence_step", "content_preview"],
                "channel_value": "sms"
            }
        }
    },
    {
        "id": "J4.7.3",
        "part_a": "Verify content_snapshot stored (Phase 16)",
        "part_b": "Check snapshot structure",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'content_snapshot' as content_snapshot,
                       metadata->'content_snapshot'->>'message_body' as message_body,
                       metadata->'content_snapshot'->>'char_count' as char_count
                FROM activity
                WHERE channel = 'sms'
                  AND action = 'sms_sent'
                  AND metadata->>'content_snapshot' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 3;
            """,
            "expect": {
                "has_rows": True,
                "content_snapshot_has": ["message_body", "char_count"]
            }
        }
    },
    {
        "id": "J4.7.4",
        "part_a": "Verify template_id, ab_test_id, ab_variant stored (Phase 24B)",
        "part_b": "Check fields",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'template_id' as template_id,
                       metadata->>'ab_test_id' as ab_test_id,
                       metadata->>'ab_variant' as ab_variant
                FROM activity
                WHERE channel = 'sms'
                  AND action = 'sms_sent'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "fields_present_when_applicable": ["template_id", "ab_test_id", "ab_variant"]
            }
        }
    },
    {
        "id": "J4.7.5",
        "part_a": "Verify full_message_body and links_included extracted",
        "part_b": "Check parsed links",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->'content_snapshot'->>'full_message_body' as full_body,
                       metadata->'content_snapshot'->>'links_included' as links
                FROM activity
                WHERE channel = 'sms'
                  AND action = 'sms_sent'
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "has_rows": True,
                "full_body_stored": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Activity created on every send",
    "DNCR rejections logged as `rejected_dncr` action",
    "All Phase 16 fields populated (content_snapshot)",
    "All Phase 24B fields populated (template_id, ab_test_id, ab_variant)",
    "Links extracted and stored"
]

KEY_FILES = [
    "src/engines/sms.py",
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
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Activity Actions")
    for action, desc in ACTIVITY_ACTIONS.items():
        lines.append(f"  {action}: {desc}")
    lines.append("")
    lines.append("### Phase 16 Fields (Content Snapshot)")
    for key, value in PHASE_16_FIELDS.items():
        lines.append(f"  {key}: {value['fields']}")
    lines.append("")
    lines.append("### Phase 24B Fields (A/B Testing)")
    for key, value in PHASE_24B_FIELDS.items():
        lines.append(f"  {key}: {value['fields']}")
    lines.append("")
    lines.append("### Required Activity Fields")
    lines.append(f"  {', '.join(SMS_ACTIVITY_REQUIRED_FIELDS)}")
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
            if lt.get("check"):
                lines.append(f"  Check: {lt['check']}")
            if lt.get("query"):
                lines.append(f"  Query: (database query)")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
