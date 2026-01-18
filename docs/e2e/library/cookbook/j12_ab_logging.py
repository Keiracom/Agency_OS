"""
Skill: J12.3 — A/B Comparison Logging
Journey: J12 - SDK Rollout & Monitoring
Checks: 4

Purpose: Verify SDK vs non-SDK outputs logged for quality comparison.
"""

CHECKS = [
    {
        "id": "J12.3.1",
        "part_a": "Verify A/B log table exists",
        "part_b": "Check sdk_ab_comparisons table schema",
        "key_files": ["src/models/sdk_logs.py"]
    },
    {
        "id": "J12.3.2",
        "part_a": "Verify both outputs logged for same lead (shadow mode)",
        "part_b": "Check SDK output and non-SDK output stored side by side",
        "key_files": ["src/engines/scout.py"]
    },
    {
        "id": "J12.3.3",
        "part_a": "Verify quality metrics captured",
        "part_b": "Check: personalization_score, confidence, cost, tokens_used",
        "key_files": ["src/models/sdk_logs.py"]
    },
    {
        "id": "J12.3.4",
        "part_a": "Verify admin dashboard shows A/B comparison",
        "part_b": "Check /admin/sdk/comparison page displays side-by-side",
        "key_files": ["frontend/app/admin/sdk/comparison/page.tsx"]
    }
]

PASS_CRITERIA = [
    "A/B comparison table exists",
    "Both outputs stored for analysis",
    "Quality metrics captured",
    "Admin can view comparison"
]

KEY_FILES = [
    "src/models/sdk_logs.py",
    "src/engines/scout.py",
    "frontend/app/admin/sdk/comparison/page.tsx"
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
