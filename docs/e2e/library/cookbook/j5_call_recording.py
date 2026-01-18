"""
Skill: J5.10 — Call Recording
Journey: J5 - Voice Outreach
Checks: 3

Purpose: Verify call recordings are captured.
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
    "warning": "Recording tests require completed voice calls"
}

# =============================================================================
# RECORDING CONFIGURATION
# =============================================================================

RECORDING_CONFIG = {
    "enabled": True,
    "storage_provider": "vapi",  # Vapi hosts recordings
    "url_format": "https://vapi.ai/recordings/{call_id}",
    "retention_days": 90,
    "supported_formats": ["mp3", "wav"],
    "metadata_fields": ["recording_url", "duration", "call_id"]
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.10.1",
        "part_a": "Verify `recordingEnabled: true` in config",
        "part_b": "Check vapi.py config",
        "key_files": ["src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Recording is enabled in Vapi config",
            "expect": {
                "code_contains": ["recording", "recordingEnabled", "true", "True"]
            }
        }
    },
    {
        "id": "J5.10.2",
        "part_a": "Verify recording_url stored in activity",
        "part_b": "Check webhook handler stores URL",
        "key_files": ["src/engines/voice.py"],
        "live_test": {
            "type": "db_query",
            "query": """
                SELECT id,
                       metadata->>'recording_url' as recording_url,
                       metadata->>'call_id' as call_id,
                       created_at
                FROM activity
                WHERE channel = 'voice'
                  AND metadata->>'recording_url' IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 5;
            """,
            "expect": {
                "min_rows": 1,
                "recording_url_present": True,
                "recording_url_format": "https://"
            }
        }
    },
    {
        "id": "J5.10.3",
        "part_a": "N/A",
        "part_b": "Access recording URL, verify audio plays",
        "key_files": [],
        "live_test": {
            "type": "manual",
            "steps": [
                "1. Query activity table for recent voice call with recording_url",
                "2. Copy the recording_url from metadata",
                "3. Open URL in browser or audio player",
                "4. Verify audio plays and contains expected conversation",
                "5. Note: May require Vapi authentication to access"
            ],
            "expect": {
                "audio_plays": True,
                "audio_quality": "clear",
                "contains_conversation": True
            }
        }
    }
]

PASS_CRITERIA = [
    "Recording enabled",
    "Recording URL stored",
    "Recording accessible"
]

KEY_FILES = [
    "src/integrations/vapi.py",
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
    lines.append("### Recording Configuration")
    lines.append(f"  Enabled: {RECORDING_CONFIG['enabled']}")
    lines.append(f"  Storage Provider: {RECORDING_CONFIG['storage_provider']}")
    lines.append(f"  URL Format: {RECORDING_CONFIG['url_format']}")
    lines.append(f"  Retention: {RECORDING_CONFIG['retention_days']} days")
    lines.append(f"  Formats: {', '.join(RECORDING_CONFIG['supported_formats'])}")
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
            if lt.get("steps"):
                lines.append("  Steps:")
                for step in lt["steps"][:3]:
                    lines.append(f"    {step}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
