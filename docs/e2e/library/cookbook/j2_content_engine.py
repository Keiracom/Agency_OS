"""
Skill: J2.9 — Content Generation
Journey: J2 - Campaign Creation & Management
Checks: 6

Purpose: Verify AI generates personalized content for sequences.

Content Types:
- Email: subject (50 chars) + body (150 words)
- SMS: 160 chars max
- LinkedIn: Connection note or message
- Voice: Call script
"""

CHECKS = [
    {
        "id": "J2.9.1",
        "part_a": "Read `src/engines/content.py` — verify `generate_email`",
        "part_b": "Check AI prompt structure",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.9.2",
        "part_a": "Verify spend limiter integration (Rule 15)",
        "part_b": "Check `anthropic.complete` call",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.9.3",
        "part_a": "Verify `generate_email_for_pool` for pool-first content",
        "part_b": "Test pool method",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.9.4",
        "part_a": "Verify SMS, LinkedIn, Voice generation methods exist",
        "part_b": "Check other generators",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.9.5",
        "part_a": "Verify personalization uses lead data (name, company, title)",
        "part_b": "Check lead_data in prompt",
        "key_files": ["src/engines/content.py"]
    },
    {
        "id": "J2.9.6",
        "part_a": "Verify JSON response parsing (subject + body)",
        "part_b": "Check response handling",
        "key_files": ["src/engines/content.py"]
    }
]

PASS_CRITERIA = [
    "Content engine generates personalized content",
    "AI spend tracked via limiter",
    "All 4 channels supported",
    "Response properly parsed"
]

KEY_FILES = [
    "src/engines/content.py"
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
