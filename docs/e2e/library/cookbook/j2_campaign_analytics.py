"""
Skill: J2.10 — Campaign Sequences
Journey: J2 - Campaign Creation & Management
Checks: 5

Purpose: Verify sequence step creation and management.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co"
}

# =============================================================================
# SEQUENCE STRUCTURE
# =============================================================================

SEQUENCE_STRUCTURE = {
    "step_fields": ["step_number", "channel", "delay_days", "template_id"],
    "channels": ["email", "sms", "linkedin", "voice"],
    "max_steps": 10,
    "typical_delays": [0, 2, 3, 5, 7]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J2.10.1",
        "part_a": "Read POST `/campaigns/{id}/sequences` endpoint",
        "part_b": "Check sequence creation",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/sequences",
            "auth": True,
            "body": {
                "steps": [
                    {"step_number": 1, "channel": "email", "delay_days": 0},
                    {"step_number": 2, "channel": "email", "delay_days": 3},
                    {"step_number": 3, "channel": "linkedin", "delay_days": 5}
                ]
            },
            "expect": {
                "status": [200, 201],
                "body_has_field": "sequence_id"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/campaigns/{campaign_id}/sequences' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"steps": [{"step_number": 1, "channel": "email", "delay_days": 0}]}'"""
        }
    },
    {
        "id": "J2.10.2",
        "part_a": "Verify sequence_steps table schema",
        "part_b": "Check step_number, channel, delay_days",
        "key_files": ["src/models/outreach.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'sequence_steps'
                ORDER BY ordinal_position;
            """,
            "expect": {
                "columns_exist": ["id", "sequence_id", "step_number", "channel", "delay_days", "template_id"]
            }
        }
    },
    {
        "id": "J2.10.3",
        "part_a": "Verify step templates linked to sequences",
        "part_b": "Check template_id relationship",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ss.id, ss.step_number, ss.channel, ss.template_id, t.name as template_name
                FROM sequence_steps ss
                LEFT JOIN templates t ON t.id = ss.template_id
                LIMIT 10;
            """,
            "expect": {
                "template_join_works": True
            },
            "note": "template_id may be NULL if using AI-generated content"
        }
    },
    {
        "id": "J2.10.4",
        "part_a": "Verify sequence ordering (step_number)",
        "part_b": "Create multi-step sequence",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT ss.sequence_id, ss.step_number, ss.channel, ss.delay_days
                FROM sequence_steps ss
                ORDER BY ss.sequence_id, ss.step_number
                LIMIT 20;
            """,
            "expect": {
                "step_numbers_sequential": True,
                "delay_days_increasing": True
            }
        }
    },
    {
        "id": "J2.10.5",
        "part_a": "Verify channel-specific sequence validation",
        "part_b": "Check channel requirements",
        "key_files": ["src/api/routes/campaigns.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/campaigns/{campaign_id}/sequences",
            "auth": True,
            "body": {
                "steps": [
                    {"step_number": 1, "channel": "invalid_channel", "delay_days": 0}
                ]
            },
            "expect": {
                "status": 422,
                "body_contains": ["channel", "invalid"]
            },
            "note": "Should reject invalid channel values"
        }
    }
]

PASS_CRITERIA = [
    "Sequences can be created for campaigns",
    "Multiple steps with delays supported",
    "Templates can be attached to steps",
    "Channel validation applied (email, sms, linkedin, voice only)"
]

KEY_FILES = [
    "src/api/routes/campaigns.py",
    "src/models/outreach.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append("")
    lines.append("### Sequence Structure")
    lines.append(f"  Channels: {', '.join(SEQUENCE_STRUCTURE['channels'])}")
    lines.append(f"  Max Steps: {SEQUENCE_STRUCTURE['max_steps']}")
    lines.append(f"  Typical Delays: {SEQUENCE_STRUCTURE['typical_delays']} days")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
