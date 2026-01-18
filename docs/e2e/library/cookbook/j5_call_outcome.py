"""
Skill: J5.11 — Call Outcome Handling
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify call outcomes are classified and handled.
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
    "warning": "Outcome testing requires completed voice calls"
}

# =============================================================================
# CALL OUTCOME CONFIGURATION
# =============================================================================

CALL_OUTCOMES = {
    "ended_reasons": [
        "customer-ended-call",
        "assistant-ended-call",
        "silence-timeout",
        "max-duration-reached",
        "error",
        "voicemail"
    ],
    "positive_outcomes": ["meeting_booked", "callback_requested", "interested"],
    "negative_outcomes": ["not_interested", "wrong_number", "do_not_call"],
    "neutral_outcomes": ["voicemail", "no_answer", "busy"],
    "status_mapping": {
        "meeting_booked": "converted",
        "callback_requested": "engaged",
        "interested": "engaged",
        "not_interested": "dead",
        "do_not_call": "dnc"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.11.1",
        "part_a": "Verify ended_reason captured from webhook",
        "part_b": "Check parsing logic",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "ended_reason extracted from webhook payload",
            "expect": {
                "code_contains": ["ended_reason", "endedReason", "webhook"]
            }
        }
    },
    {
        "id": "J5.11.2",
        "part_a": "Verify outcome stored in activity metadata",
        "part_b": "Check activity after call",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'ended_reason' as ended_reason,
                       metadata->>'outcome' as outcome,
                       metadata->>'duration' as duration
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'ended_reason' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "min_rows": 1,
                "ended_reason_present": True,
                "ended_reason_in_list": ["customer-ended-call", "assistant-ended-call",
                                         "silence-timeout", "max-duration-reached"]
            }
        }
    },
    {
        "id": "J5.11.3",
        "part_a": "Verify lead status updated on meeting booked",
        "part_b": "Check lead update logic",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Lead status updated based on call outcome",
            "expect": {
                "code_contains": ["meeting_booked", "status", "converted", "lead"]
            }
        }
    },
    {
        "id": "J5.11.4",
        "part_a": "Verify reply_count incremented",
        "part_b": "Check lead update logic",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT l.id, l.reply_count,
                       (SELECT COUNT(*) FROM activity a
                        WHERE a.lead_id = l.id AND a.channel = 'voice') as voice_activities
                FROM lead_pool l
                WHERE l.reply_count > 0
                ORDER BY l.updated_at DESC
                LIMIT 5;
            """,
            "expect": {
                "reply_count_matches_activities": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Outcomes captured correctly",
    "Lead status updated appropriately",
    "Meeting bookings detected"
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
    lines.append("### Call Outcome Configuration")
    lines.append(f"  Ended Reasons: {', '.join(CALL_OUTCOMES['ended_reasons'][:4])}...")
    lines.append(f"  Positive Outcomes: {', '.join(CALL_OUTCOMES['positive_outcomes'])}")
    lines.append(f"  Negative Outcomes: {', '.join(CALL_OUTCOMES['negative_outcomes'])}")
    lines.append("  Status Mapping:")
    for outcome, status in CALL_OUTCOMES['status_mapping'].items():
        lines.append(f"    {outcome} -> {status}")
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
