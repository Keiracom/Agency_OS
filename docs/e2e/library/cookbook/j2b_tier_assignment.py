"""
Skill: J2B.6 — Tier Assignment
Journey: J2B - Lead Enrichment Pipeline
Checks: 5

Purpose: Verify ALS score maps to correct tier and all enrichment data stored in assignments.
"""

CHECKS = [
    {
        "id": "J2B.6.1",
        "part_a": "Verify tier boundaries: Hot (85-100), Warm (60-84), Cool (35-59), Cold (20-34), Dead (<20)",
        "part_b": "Test tier assignment for edge case scores (84, 85, 59, 60)",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J2B.6.2",
        "part_a": "Verify `als_score`, `als_tier`, `als_components` fields in lead_assignments",
        "part_b": "Query assignment record for score fields",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J2B.6.3",
        "part_a": "Verify `linkedin_person_data` and `linkedin_company_data` JSONB columns exist",
        "part_b": "Check schema for JSONB fields",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J2B.6.4",
        "part_a": "Verify `personalization_data`, `pain_points`, `icebreaker_hooks` stored",
        "part_b": "Query assignment for Claude analysis results",
        "key_files": ["src/models/lead.py"]
    },
    {
        "id": "J2B.6.5",
        "part_a": "Verify enrichment timestamps: `linkedin_person_scraped_at`, `enrichment_completed_at`",
        "part_b": "Check timestamps populated after enrichment flow",
        "key_files": ["src/models/lead.py"]
    }
]

PASS_CRITERIA = [
    "Tier boundaries match CLAUDE.md specification",
    "ALS score and components persisted to assignment",
    "LinkedIn data stored in JSONB columns",
    "Claude analysis results (pain_points, hooks) stored",
    "Enrichment timestamps track progress"
]

KEY_FILES = [
    "src/engines/scorer.py",
    "src/models/lead.py",
    "CLAUDE.md"
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
