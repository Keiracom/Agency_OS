"""
Skill: J11.12 — SDK Cost Validation
Journey: J11 - SDK Foundation
Checks: 5

Purpose: Verify actual SDK costs match estimates within acceptable margin.
"""

CHECKS = [
    {
        "id": "J11.12.1",
        "part_a": "Run 10 enrichment calls and record actual costs",
        "part_b": "Calculate average cost per enrichment",
        "key_files": ["tests/e2e/sdk/test_cost_validation.py"]
    },
    {
        "id": "J11.12.2",
        "part_a": "Compare actual vs estimated enrichment cost",
        "part_b": "Estimate: $0.45 AUD — verify actual within 20% ($0.36-$0.54)",
        "key_files": ["docs/e2e/accounting/sdk_cost_comparison_optimized.csv"]
    },
    {
        "id": "J11.12.3",
        "part_a": "Run 10 email generation calls and record costs",
        "part_b": "Calculate average cost per email",
        "key_files": ["tests/e2e/sdk/test_cost_validation.py"]
    },
    {
        "id": "J11.12.4",
        "part_a": "Compare actual vs estimated email cost",
        "part_b": "Estimate: $0.15 AUD — verify actual within 20% ($0.12-$0.18)",
        "key_files": ["docs/e2e/accounting/sdk_cost_comparison_optimized.csv"]
    },
    {
        "id": "J11.12.5",
        "part_a": "Document any cost variances > 20%",
        "part_b": "If variance high, identify cause (token count, retries, etc.)",
        "key_files": ["docs/e2e/ISSUES_FOUND.md"]
    }
]

PASS_CRITERIA = [
    "Enrichment cost within 20% of estimate",
    "Email cost within 20% of estimate",
    "Voice KB cost within 20% of estimate",
    "No unexpected cost spikes",
    "Variances documented with root cause"
]

KEY_FILES = [
    "tests/e2e/sdk/test_cost_validation.py",
    "docs/e2e/accounting/sdk_cost_comparison_optimized.csv"
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
