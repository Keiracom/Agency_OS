"""
Skill: J5.3 — ElevenLabs Voice Configuration
Journey: J5 - Voice Outreach
Checks: 4

Purpose: Verify ElevenLabs voice synthesis is configured.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "elevenlabs_dashboard": "https://elevenlabs.io/app",
    "warning": "ElevenLabs usage through Vapi may incur costs"
}

# =============================================================================
# ELEVENLABS VOICE CONFIGURATION
# =============================================================================

ELEVENLABS_CONFIG = {
    "default_voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - Male Australian
    "provider": "11labs",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75
    },
    "language": "en-AU",
    "available_voices": {
        "adam": "pNInz6obpgDQGcFmaJgB",
        "rachel": "21m00Tcm4TlvDq8ikWAM",
        "josh": "TxGEqnHWrfWFTfGW9XjX"
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.3.1",
        "part_a": "Verify default voice ID in voice.py — `DEFAULT_VOICE_ID = \"pNInz6obpgDQGcFmaJgB\"`",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Default voice ID is set correctly",
            "expect": {
                "code_contains": ["pNInz6obpgDQGcFmaJgB", "DEFAULT_VOICE_ID"]
            }
        }
    },
    {
        "id": "J5.3.2",
        "part_a": "Verify ElevenLabs provider in vapi.py — `voice.provider = \"11labs\"`",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Voice provider set to 11labs",
            "expect": {
                "code_contains": ["11labs", "provider"]
            }
        }
    },
    {
        "id": "J5.3.3",
        "part_a": "Verify voice stability/similarity settings — stability: 0.5, similarityBoost: 0.75",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Voice stability and similarity settings configured",
            "expect": {
                "code_contains": ["stability", "similarity"]
            }
        }
    },
    {
        "id": "J5.3.4",
        "part_a": "Verify language set to Australian English — `language: \"en-AU\"`",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Language set to Australian English",
            "expect": {
                "code_contains": ["en-AU"]
            }
        }
    }
]

PASS_CRITERIA = [
    "ElevenLabs voice ID configured",
    "Voice stability settings appropriate",
    "Australian English language set"
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
    lines.append(f"- ElevenLabs Dashboard: {LIVE_CONFIG['elevenlabs_dashboard']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### ElevenLabs Configuration")
    lines.append(f"  Default Voice ID: {ELEVENLABS_CONFIG['default_voice_id']}")
    lines.append(f"  Provider: {ELEVENLABS_CONFIG['provider']}")
    lines.append(f"  Language: {ELEVENLABS_CONFIG['language']}")
    lines.append(f"  Stability: {ELEVENLABS_CONFIG['voice_settings']['stability']}")
    lines.append(f"  Similarity Boost: {ELEVENLABS_CONFIG['voice_settings']['similarity_boost']}")
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
