"""
Skill: J7.5 — Reply Analyzer (Phase 24D)
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify sentiment, objection, and question analysis.
"""

CHECKS = [
    {
        "id": "J7.5.1",
        "part_a": "Read `src/services/reply_analyzer.py` — verify complete (501 lines)",
        "part_b": "N/A",
        "key_files": ["src/services/reply_analyzer.py"]
    },
    {
        "id": "J7.5.2",
        "part_a": "Verify sentiment detection (positive, neutral, negative, mixed)",
        "part_b": "Test various sentiments",
        "key_files": ["src/services/reply_analyzer.py"]
    },
    {
        "id": "J7.5.3",
        "part_a": "Verify objection types (timing, budget, authority, need, competitor, trust)",
        "part_b": "Test objection replies",
        "key_files": ["src/services/reply_analyzer.py"]
    },
    {
        "id": "J7.5.4",
        "part_a": "Verify question extraction",
        "part_b": "Test question replies",
        "key_files": ["src/services/reply_analyzer.py"]
    },
    {
        "id": "J7.5.5",
        "part_a": "Verify topic extraction",
        "part_b": "Check topics identified",
        "key_files": ["src/services/reply_analyzer.py"]
    },
    {
        "id": "J7.5.6",
        "part_a": "Verify AI analysis with rule-based fallback",
        "part_b": "Disable AI, test rules",
        "key_files": ["src/services/reply_analyzer.py"]
    }
]

PASS_CRITERIA = [
    "Sentiment detected correctly",
    "Objection types identified",
    "Questions extracted",
    "Topics identified",
    "Fallback rules work"
]

KEY_FILES = [
    "src/services/reply_analyzer.py"
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
    lines.append("### Objection Types Reference")
    lines.append("- timing: \"not now\", \"next quarter\", etc.")
    lines.append("- budget: \"expensive\", \"can't afford\", etc.")
    lines.append("- authority: \"not my decision\", \"need to ask\", etc.")
    lines.append("- need: \"don't need\", \"already have\", etc.")
    lines.append("- competitor: \"using another\", \"contract with\", etc.")
    lines.append("- trust: \"never heard of\", \"is this legit\", etc.")
    return "\n".join(lines)
