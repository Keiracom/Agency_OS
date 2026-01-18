"""
Skill: J4.4 — SMS Engine Implementation
Journey: J4 - SMS Outreach
Checks: 7

Purpose: Verify SMS engine is fully implemented.
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
    "test_phone": "+61457543392"
}

# =============================================================================
# SMS DOMAIN CONSTANTS
# =============================================================================

SMS_ENGINE_CONFIG = {
    "class_name": "SMSEngine",
    "base_class": "OutreachEngine",
    "required_methods": [
        "send",
        "send_batch",
        "check_dncr",
        "_log_activity",
        "_validate_phone"
    ],
    "layer": 3,
    "imports_allowed": ["models", "integrations"]
}

DNCR_CONFIG = {
    "check_before_send": True,
    "error_class": "DNCRError",
    "australian_mobile_prefix": "+614",
    "blocked_action": "rejected_dncr"
}

SMS_LIMITS = {
    "daily_per_number": 100,
    "max_message_length_gsm7": 160,
    "max_message_length_unicode": 70,
    "batch_size_max": 50
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J4.4.1",
        "part_a": "Read `src/engines/sms.py` — verify `send` method",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SMSEngine.send method exists and is complete",
            "expect": {
                "code_contains": ["def send(", "async def send(", "EngineResult"],
                "no_incomplete": True
            }
        }
    },
    {
        "id": "J4.4.2",
        "part_a": "Verify no TODO/FIXME/pass in sms.py",
        "part_b": "Run `grep -n \"TODO\\|FIXME\\|pass\" src/engines/sms.py`",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "No incomplete implementations",
            "expect": {
                "no_patterns": ["TODO", "FIXME", "pass  # "],
                "grep_empty": True
            },
            "curl_command": """# Search for incomplete code:
grep -n "TODO\\|FIXME\\|pass$" src/engines/sms.py"""
        }
    },
    {
        "id": "J4.4.3",
        "part_a": "Verify `send_batch` method for bulk sends",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send_batch method exists for bulk operations",
            "expect": {
                "code_contains": ["def send_batch(", "async def send_batch("]
            }
        }
    },
    {
        "id": "J4.4.4",
        "part_a": "Verify `check_dncr` method exposed",
        "part_b": "N/A",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "check_dncr method exists for Do-Not-Call check",
            "expect": {
                "code_contains": ["check_dncr", "DNCR"]
            }
        }
    },
    {
        "id": "J4.4.5",
        "part_a": "Verify OutreachEngine base class extended",
        "part_b": "Check class definition",
        "key_files": ["src/engines/sms.py", "src/engines/outreach_base.py"],
        "live_test": {
            "type": "code_verify",
            "check": "SMSEngine extends OutreachEngine",
            "expect": {
                "code_contains": ["class SMSEngine(OutreachEngine)", "from .outreach_base import OutreachEngine"]
            }
        }
    },
    {
        "id": "J4.4.6",
        "part_a": "Verify DNCR check happens before send",
        "part_b": "Trace code path",
        "key_files": ["src/engines/sms.py", "src/integrations/twilio.py"],
        "live_test": {
            "type": "code_verify",
            "check": "DNCR check occurs early in send flow",
            "expect": {
                "logic": "check_dncr called before twilio.send_sms",
                "code_pattern": "check_dncr.*then.*send_sms"
            }
        }
    },
    {
        "id": "J4.4.7",
        "part_a": "Verify DNCRError raised when blocked",
        "part_b": "Check exception handling",
        "key_files": ["src/engines/sms.py"],
        "live_test": {
            "type": "code_verify",
            "check": "DNCRError is raised for blocked numbers",
            "expect": {
                "code_contains": ["DNCRError", "raise DNCRError"]
            }
        }
    }
]

PASS_CRITERIA = [
    "No incomplete implementations (TODO/FIXME/pass)",
    "All methods have implementations",
    "Validation for required fields",
    "Extends OutreachEngine correctly",
    "DNCR check before send",
    "DNCRError handled properly"
]

KEY_FILES = [
    "src/engines/sms.py",
    "src/engines/outreach_base.py",
    "src/integrations/twilio.py",
    "src/integrations/dncr.py"
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
    lines.append("### SMS Engine Configuration")
    lines.append(f"  Class: {SMS_ENGINE_CONFIG['class_name']}")
    lines.append(f"  Base Class: {SMS_ENGINE_CONFIG['base_class']}")
    lines.append(f"  Layer: {SMS_ENGINE_CONFIG['layer']}")
    lines.append(f"  Required Methods: {', '.join(SMS_ENGINE_CONFIG['required_methods'])}")
    lines.append("")
    lines.append("### DNCR Configuration")
    for key, value in DNCR_CONFIG.items():
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("### SMS Limits")
    for key, value in SMS_LIMITS.items():
        lines.append(f"  {key}: {value}")
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
            if lt.get("curl_command"):
                lines.append(f"  Curl: {lt['curl_command'][:80]}...")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
