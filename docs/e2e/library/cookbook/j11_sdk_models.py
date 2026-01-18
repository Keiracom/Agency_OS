"""
Skill: J11.3 — SDK Models & Schemas
Journey: J11 - SDK Foundation
Checks: 4

Purpose: Verify Pydantic models match JSON schemas for all agent types.
"""

CHECKS = [
    {
        "id": "J11.3.1",
        "part_a": "Read `src/agents/sdk_agents/sdk_models.py` — verify model classes exist",
        "part_b": "Check EnrichmentInput, EnrichmentOutput, EmailInput, EmailOutput, etc.",
        "key_files": ["src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J11.3.2",
        "part_a": "Verify models match `config/sdk_schemas.json` definitions",
        "part_b": "Compare field names, types, required fields between Python and JSON",
        "key_files": ["src/agents/sdk_agents/sdk_models.py", "config/sdk_schemas.json"]
    },
    {
        "id": "J11.3.3",
        "part_a": "Test model validation with valid data",
        "part_b": "Instantiate each model with sample data — no validation errors",
        "key_files": ["src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J11.3.4",
        "part_a": "Test model validation with invalid data",
        "part_b": "Verify Pydantic raises ValidationError for missing required fields",
        "key_files": ["src/agents/sdk_agents/sdk_models.py"]
    }
]

PASS_CRITERIA = [
    "All model classes defined (Enrichment, Email, VoiceKB, Objection, Classification)",
    "Pydantic models match JSON schema field definitions",
    "Valid data passes validation",
    "Invalid data raises appropriate errors"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_models.py",
    "config/sdk_schemas.json"
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
