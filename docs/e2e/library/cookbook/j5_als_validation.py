"""
Skill: J5.5 — ALS Score Validation
Journey: J5 - Voice Outreach
Checks: 3

Purpose: Verify ALS >= 70 required for voice calls.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "warning": "Voice calls only allowed for ALS >= 70 (Hot/Warm+ tier)"
}

# =============================================================================
# ALS THRESHOLDS FOR VOICE
# =============================================================================

ALS_VOICE_THRESHOLDS = {
    "min_als_for_voice": 70,  # NOT 85 - voice is for Warm+ leads
    "tier_mapping": {
        "Hot": {"min": 85, "max": 100, "voice_allowed": True},
        "Warm": {"min": 60, "max": 84, "voice_allowed": True},  # Only 70+ Warm
        "Cool": {"min": 35, "max": 59, "voice_allowed": False},
        "Cold": {"min": 20, "max": 34, "voice_allowed": False},
        "Dead": {"min": 0, "max": 19, "voice_allowed": False}
    },
    "rejection_message": "Lead ALS score too low for voice outreach"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.5.1",
        "part_a": "Read voice.py lines 163-171 — verify ALS check implemented",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "ALS validation exists in voice engine",
            "expect": {
                "code_contains": ["als_score", "70", "ALS"]
            }
        }
    },
    {
        "id": "J5.5.2",
        "part_a": "Verify threshold is 70 (not 85) — check constant value",
        "part_b": "N/A",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Voice threshold is 70, not 85",
            "expect": {
                "code_contains": ["70"],
                "logic_check": "Threshold should be 70 for Warm+ leads, not 85 (Hot only)"
            }
        }
    },
    {
        "id": "J5.5.3",
        "part_a": "Verify error returned for low ALS",
        "part_b": "Test with ALS=60 lead, verify rejection",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "api",
            "method": "POST",
            "url": "{api_url}/api/v1/voice/calls",
            "auth": True,
            "body": {
                "lead_id": "{{low_als_lead_id}}",
                "assistant_id": "{{test_assistant_id}}"
            },
            "test_setup": "Find or create lead with ALS < 70",
            "expect": {
                "status": 400,
                "body_contains": "ALS",
                "error_type": "validation_error"
            },
            "curl_command": """curl -X POST '{api_url}/api/v1/voice/calls' \\
  -H 'Authorization: Bearer {token}' \\
  -H 'Content-Type: application/json' \\
  -d '{"lead_id": "{low_als_lead_id}", "assistant_id": "{assistant_id}"}'"""
        }
    }
]

PASS_CRITERIA = [
    "Voice requires ALS >= 70",
    "Low ALS leads rejected",
    "Clear error message returned"
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
    lines.append("### ALS Voice Thresholds")
    lines.append(f"  Minimum ALS for Voice: {ALS_VOICE_THRESHOLDS['min_als_for_voice']}")
    lines.append("  Tier Mapping:")
    for tier, config in ALS_VOICE_THRESHOLDS['tier_mapping'].items():
        voice_status = "Allowed" if config['voice_allowed'] else "Blocked"
        lines.append(f"    {tier}: {config['min']}-{config['max']} -> {voice_status}")
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
            if lt.get("test_setup"):
                lines.append(f"  Setup: {lt['test_setup']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
