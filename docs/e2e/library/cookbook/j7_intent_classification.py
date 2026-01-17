"""
Skill: J7.4 — Closer Engine Intent Classification
Journey: J7 - Reply Handling
Checks: 5

Purpose: Verify AI-powered intent classification works correctly.
"""

CHECKS = [
    {
        "id": "J7.4.1",
        "part_a": "Read `src/engines/closer.py` — verify 7 intent types (lines 39-47)",
        "part_b": "N/A",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.4.2",
        "part_a": "Verify `anthropic.classify_intent` call (line 164)",
        "part_b": "Test classification",
        "key_files": ["src/engines/closer.py", "src/integrations/anthropic.py"]
    },
    {
        "id": "J7.4.3",
        "part_a": "Verify confidence score returned",
        "part_b": "Check confidence > 0.7",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.4.4",
        "part_a": "Verify reasoning captured",
        "part_b": "Check reasoning in result",
        "key_files": ["src/engines/closer.py"]
    },
    {
        "id": "J7.4.5",
        "part_a": "Test all 7 intent types",
        "part_b": "Send 7 different replies",
        "key_files": ["src/engines/closer.py"]
    }
]

PASS_CRITERIA = [
    "All 7 intent types recognized",
    "Confidence scores returned",
    "AI reasoning captured",
    "Low-confidence triggers fallback"
]

KEY_FILES = [
    "src/engines/closer.py",
    "src/integrations/anthropic.py"
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
    lines.append("")
    lines.append("### Intent Types Reference")
    lines.append("```python")
    lines.append("INTENT_MAP = {")
    lines.append('    "meeting_request": IntentType.MEETING_REQUEST,')
    lines.append('    "interested": IntentType.INTERESTED,')
    lines.append('    "question": IntentType.QUESTION,')
    lines.append('    "not_interested": IntentType.NOT_INTERESTED,')
    lines.append('    "unsubscribe": IntentType.UNSUBSCRIBE,')
    lines.append('    "out_of_office": IntentType.OUT_OF_OFFICE,')
    lines.append('    "auto_reply": IntentType.AUTO_REPLY,')
    lines.append("}")
    lines.append("```")
    return "\n".join(lines)
