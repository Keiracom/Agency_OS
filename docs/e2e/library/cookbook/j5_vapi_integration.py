"""
Skill: J5.2 — Vapi Integration
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify Vapi client is properly configured.
"""

CHECKS = [
    {
        "id": "J5.2.1",
        "part_a": "Read `src/integrations/vapi.py` — verify complete implementation",
        "part_b": "N/A",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.2.2",
        "part_a": "Verify `VAPI_API_KEY` env var exists",
        "part_b": "Check Railway vars for VAPI_API_KEY",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J5.2.3",
        "part_a": "Verify `VAPI_PHONE_NUMBER_ID` env var exists",
        "part_b": "Check Railway vars for VAPI_PHONE_NUMBER_ID",
        "key_files": ["src/config/settings.py"]
    },
    {
        "id": "J5.2.4",
        "part_a": "Verify `create_assistant` method implemented",
        "part_b": "Test assistant creation via API",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.2.5",
        "part_a": "Verify `start_outbound_call` method implemented",
        "part_b": "Test call initiation via API",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.2.6",
        "part_a": "Verify `get_call` method implemented",
        "part_b": "Test call status retrieval via API",
        "key_files": ["src/integrations/vapi.py"]
    },
    {
        "id": "J5.2.7",
        "part_a": "Verify `parse_webhook` method implemented",
        "part_b": "Test webhook parsing with sample payload",
        "key_files": ["src/integrations/vapi.py"]
    }
]

PASS_CRITERIA = [
    "Vapi integration is complete (290 lines verified)",
    "API key and phone number configured",
    "Assistant operations work",
    "Call operations work",
    "Webhook parsing works"
]

KEY_FILES = [
    "src/integrations/vapi.py",
    "src/config/settings.py"
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
