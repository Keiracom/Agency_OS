"""
Skill: J7.11 — Reply Recovery Flow (Safety Net)
Journey: J7 - Reply Handling
Checks: 7

Purpose: Verify 6-hourly polling catches missed webhook replies.
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
# REPLY RECOVERY CONSTANTS
# =============================================================================

RECOVERY_SCHEDULE = {
    "interval_hours": 6,
    "default_status": "PAUSED",
    "lookback_hours": 12
}

POLLING_CHANNELS = {
    "email": "Postmark API poll",
    "sms": "Twilio API poll",
    "linkedin": "Unipile API poll"
}

FLOW_TASKS = {
    "poll_email_replies_task": "Poll Postmark for inbound emails",
    "poll_sms_replies_task": "Poll Twilio for inbound SMS",
    "poll_linkedin_replies_task": "Poll Unipile for LinkedIn messages",
    "find_lead_by_contact_task": "Match reply to existing lead",
    "check_if_reply_processed_task": "Deduplicate against activities",
    "process_missed_reply_task": "Process via Closer engine"
}

DEDUPLICATION_FIELDS = {
    "email": "provider_message_id",
    "sms": "MessageSid",
    "linkedin": "message_id"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.11.1",
        "part_a": "Read `src/orchestration/flows/reply_recovery_flow.py` (548 lines)",
        "part_b": "N/A",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Reply recovery flow exists",
            "expect": {
                "code_contains": ["reply_recovery", "@flow", "poll", "recover"]
            }
        }
    },
    {
        "id": "J7.11.2",
        "part_a": "Verify `poll_email_replies_task` polls Postmark",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "api",
            "method": "GET",
            "url": "{prefect_url}/api/flow_runs?flow_name=reply_recovery_flow",
            "auth": False,
            "expect": {
                "status": 200,
                "body_is_array": True
            },
            "curl_command": """curl '{prefect_url}/api/flow_runs?flow_name=reply_recovery_flow'"""
        }
    },
    {
        "id": "J7.11.3",
        "part_a": "Verify `poll_sms_replies_task` polls Twilio",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SMS polling task exists",
            "expect": {
                "code_contains": ["poll_sms", "twilio", "inbound", "messages"]
            }
        }
    },
    {
        "id": "J7.11.4",
        "part_a": "Verify `poll_linkedin_replies_task` polls Unipile",
        "part_b": "Check logs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "LinkedIn polling task exists",
            "expect": {
                "code_contains": ["poll_linkedin", "unipile", "messages"]
            }
        }
    },
    {
        "id": "J7.11.5",
        "part_a": "Verify deduplication check (lines 255-287)",
        "part_b": "Simulate duplicate",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Deduplication logic exists",
            "expect": {
                "code_contains": ["dedup", "already_processed", "provider_message_id", "exists"]
            }
        }
    },
    {
        "id": "J7.11.6",
        "part_a": "Verify `process_missed_reply_task` calls Closer",
        "part_b": "Check processing",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py", "src/engines/closer.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Missed replies processed via Closer",
            "expect": {
                "code_contains": ["closer", "process_reply", "missed"]
            }
        }
    },
    {
        "id": "J7.11.7",
        "part_a": "Trigger flow manually in Prefect",
        "part_b": "Check recovery runs",
        "key_files": ["src/orchestration/flows/reply_recovery_flow.py"],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Open Prefect UI: {prefect_url}",
                "2. Navigate to Flows > reply_recovery_flow",
                "3. Click 'Run' to trigger manually",
                "4. Monitor flow run in Prefect UI",
                "5. Check logs for polling results",
                "6. Verify no duplicate activities created"
            ],
            "expect": {
                "flow_completes": True,
                "no_errors": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Polls all 3 channels",
    "Deduplication prevents double processing",
    "Missed replies processed correctly",
    "Flow runs on 6-hour schedule (PAUSED by default)"
]

KEY_FILES = [
    "src/orchestration/flows/reply_recovery_flow.py",
    "src/engines/closer.py"
]

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_prefect_url(path: str) -> str:
    """Get Prefect URL for flow management."""
    base = LIVE_CONFIG["prefect_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Recovery Schedule")
    for key, value in RECOVERY_SCHEDULE.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### Polling Channels")
    for channel, description in POLLING_CHANNELS.items():
        lines.append(f"  {channel}: {description}")
    lines.append("")
    lines.append("### Flow Tasks Reference")
    for task, description in FLOW_TASKS.items():
        lines.append(f"  {task}: {description}")
    lines.append("")
    lines.append("### Deduplication Fields")
    for channel, field in DEDUPLICATION_FIELDS.items():
        lines.append(f"  {channel}: {field}")
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
