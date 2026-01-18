"""
Skill: J5.6 — Assistant Configuration
Journey: J5 - Voice Outreach
Checks: 5

Purpose: Verify AI assistant is properly configured.
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
    "warning": "Assistant configuration affects live call behavior"
}

# =============================================================================
# ASSISTANT CONFIGURATION
# =============================================================================

ASSISTANT_CONFIG = {
    "model": "claude-sonnet-4-20250514",
    "max_duration_seconds": 300,  # 5 minutes
    "recording_enabled": True,
    "transcription_enabled": True,
    "conversation_rules": [
        "Be polite and professional",
        "Introduce yourself clearly",
        "Stay on topic",
        "Handle objections gracefully",
        "Ask for meeting booking when appropriate"
    ],
    "voice_provider": "11labs",
    "language": "en-AU"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.6.1",
        "part_a": "Read `_build_system_prompt` method in voice.py",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "System prompt builder exists",
            "expect": {
                "code_contains": ["_build_system_prompt", "system_prompt", "prompt"]
            }
        }
    },
    {
        "id": "J5.6.2",
        "part_a": "Verify system prompt includes conversation rules",
        "part_b": "Check prompt content for rules",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "System prompt includes conversation guidelines",
            "expect": {
                "code_contains": ["professional", "polite", "meeting", "objection"]
            }
        }
    },
    {
        "id": "J5.6.3",
        "part_a": "Verify max_duration_seconds = 300 (5 min)",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Max call duration is 5 minutes (300 seconds)",
            "expect": {
                "code_contains": ["300", "max_duration", "maxDuration"]
            }
        }
    },
    {
        "id": "J5.6.4",
        "part_a": "Verify model = claude-sonnet-4-20250514",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Using Claude Sonnet model for voice assistant",
            "expect": {
                "code_contains": ["claude", "sonnet", "anthropic"]
            }
        }
    },
    {
        "id": "J5.6.5",
        "part_a": "Verify recording enabled in config",
        "part_b": "Check config value",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Recording is enabled for calls",
            "expect": {
                "code_contains": ["recording", "recordingEnabled", "true"]
            }
        }
    }
]

PASS_CRITERIA = [
    "System prompt well-defined",
    "Max duration appropriate",
    "Recording enabled for review"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/integrations/vapi.py"
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
    lines.append("### Assistant Configuration")
    lines.append(f"  Model: {ASSISTANT_CONFIG['model']}")
    lines.append(f"  Max Duration: {ASSISTANT_CONFIG['max_duration_seconds']} seconds")
    lines.append(f"  Recording: {ASSISTANT_CONFIG['recording_enabled']}")
    lines.append(f"  Voice Provider: {ASSISTANT_CONFIG['voice_provider']}")
    lines.append(f"  Language: {ASSISTANT_CONFIG['language']}")
    lines.append("  Conversation Rules:")
    for rule in ASSISTANT_CONFIG['conversation_rules']:
        lines.append(f"    - {rule}")
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
