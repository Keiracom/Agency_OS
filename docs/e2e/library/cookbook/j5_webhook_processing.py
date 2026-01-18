"""
Skill: J5.9 — Webhook Processing
Journey: J5 - Voice Outreach
Checks: 6

Purpose: Verify call webhooks are processed correctly.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "webhook_url": "https://agency-os-production.up.railway.app/webhooks/vapi/call",
    "warning": "Webhook testing requires actual Vapi calls or mock payloads"
}

# =============================================================================
# WEBHOOK CONFIGURATION
# =============================================================================

WEBHOOK_CONFIG = {
    "endpoint": "/webhooks/vapi/call",
    "supported_events": [
        "call-started",
        "call-ended",
        "transcript-update",
        "function-call",
        "speech-update"
    ],
    "required_fields_per_event": {
        "call-started": ["call_id", "phone_number", "assistant_id"],
        "call-ended": ["call_id", "ended_reason", "duration", "transcript", "recording_url"],
        "transcript-update": ["call_id", "transcript"]
    },
    "meeting_booked_keywords": ["book", "schedule", "meeting", "appointment", "calendar"]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.9.1",
        "part_a": "Read `process_call_webhook` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Webhook processor method exists",
            "expect": {
                "code_contains": ["process_call_webhook", "webhook", "event"]
            }
        }
    },
    {
        "id": "J5.9.2",
        "part_a": "Verify webhook endpoint exists in webhooks.py — `/webhooks/vapi/call`",
        "part_b": "N/A",
        "key_files": ["src/api/routes/webhooks.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Webhook route registered",
            "expect": {
                "code_contains": ["/webhooks/vapi", "vapi", "POST"]
            }
        }
    },
    {
        "id": "J5.9.3",
        "part_a": "Verify call-ended event handling",
        "part_b": "Check event processing logic",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "call-ended event is handled",
            "expect": {
                "code_contains": ["call-ended", "ended_reason", "duration"]
            }
        }
    },
    {
        "id": "J5.9.4",
        "part_a": "Verify transcript stored in activity metadata",
        "part_b": "Check activity after call ends",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'transcript' as transcript
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'transcript' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "transcript_present": True,
                "transcript_not_empty": True
            }
        }
    },
    {
        "id": "J5.9.5",
        "part_a": "Verify recording_url stored in activity metadata",
        "part_b": "Check activity after call ends",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'recording_url' as recording_url
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'recording_url' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1;
            """,
            "expect": {
                "recording_url_present": True,
                "recording_url_format": "https://"
            }
        }
    },
    {
        "id": "J5.9.6",
        "part_a": "Verify meeting_booked detection",
        "part_b": "Check lead status update logic",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Meeting booking detection implemented",
            "expect": {
                "code_contains": ["meeting_booked", "meeting", "book", "scheduled"]
            }
        }
    }
]

PASS_CRITERIA = [
    "Webhooks processed correctly",
    "Transcript captured",
    "Recording URL captured",
    "Meeting booking detected"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/api/routes/webhooks.py"
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
    lines.append(f"- Webhook URL: {LIVE_CONFIG['webhook_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### Webhook Configuration")
    lines.append(f"  Endpoint: {WEBHOOK_CONFIG['endpoint']}")
    lines.append(f"  Supported Events: {', '.join(WEBHOOK_CONFIG['supported_events'])}")
    lines.append("  Required Fields per Event:")
    for event, fields in WEBHOOK_CONFIG['required_fields_per_event'].items():
        lines.append(f"    {event}: {', '.join(fields)}")
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
