"""
Skill: J5.4 — Voice Engine Implementation
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify voice engine is fully implemented.
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
    "warning": "Voice engine tests may initiate real calls - use TEST_MODE"
}

# =============================================================================
# VOICE ENGINE REQUIREMENTS
# =============================================================================

VOICE_ENGINE_REQUIREMENTS = {
    "base_class": "OutreachEngine",
    "required_methods": [
        "send",
        "create_campaign_assistant",
        "get_call_status",
        "get_call_transcript",
        "process_call_webhook"
    ],
    "forbidden_patterns": ["TODO", "FIXME", "pass  # placeholder"],
    "min_implementation_lines": 200
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.4.1",
        "part_a": "Read `src/engines/voice.py` — verify `send` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "send method is fully implemented",
            "expect": {
                "code_contains": ["def send", "async def send", "EngineResult"],
                "code_not_contains": ["pass  # placeholder"]
            }
        }
    },
    {
        "id": "J5.4.2",
        "part_a": "Verify no TODO/FIXME/pass in voice.py — `grep -n \"TODO\\|FIXME\\|pass\" src/engines/voice.py`",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "No incomplete implementation markers",
            "expect": {
                "code_not_contains": ["TODO", "FIXME", "pass  # placeholder", "NotImplementedError"]
            }
        }
    },
    {
        "id": "J5.4.3",
        "part_a": "Verify `create_campaign_assistant` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "create_campaign_assistant method exists",
            "expect": {
                "code_contains": ["create_campaign_assistant", "assistant_id"]
            }
        }
    },
    {
        "id": "J5.4.4",
        "part_a": "Verify `get_call_status` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "get_call_status method exists",
            "expect": {
                "code_contains": ["get_call_status", "call_id"]
            }
        }
    },
    {
        "id": "J5.4.5",
        "part_a": "Verify `get_call_transcript` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "get_call_transcript method exists",
            "expect": {
                "code_contains": ["get_call_transcript", "transcript"]
            }
        }
    },
    {
        "id": "J5.4.6",
        "part_a": "Verify `process_call_webhook` method implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "process_call_webhook method exists",
            "expect": {
                "code_contains": ["process_call_webhook", "webhook"]
            }
        }
    },
    {
        "id": "J5.4.7",
        "part_a": "Verify OutreachEngine base class extended — check class definition",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py", "src/engines/base.py"],
        "live_test": {
            "type": "code_verify",
            "check": "VoiceEngine extends OutreachEngine",
            "expect": {
                "code_contains": ["class VoiceEngine", "OutreachEngine"]
            }
        }
    }
]

PASS_CRITERIA = [
    "No incomplete implementations",
    "All methods have implementations",
    "Extends OutreachEngine correctly"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/engines/base.py"
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
    lines.append("### Voice Engine Requirements")
    lines.append(f"  Base Class: {VOICE_ENGINE_REQUIREMENTS['base_class']}")
    lines.append(f"  Required Methods: {', '.join(VOICE_ENGINE_REQUIREMENTS['required_methods'])}")
    lines.append(f"  Forbidden Patterns: {', '.join(VOICE_ENGINE_REQUIREMENTS['forbidden_patterns'])}")
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
