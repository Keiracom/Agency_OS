"""
Skill: J10.9 — Revenue Page
Journey: J10 - Admin Dashboard
Checks: 4

Purpose: Verify revenue tracking and reporting functionality.
"""

CHECKS = [
    {
        "id": "J10.9.1",
        "part_a": "Read `frontend/app/admin/revenue/page.tsx` — verify revenue display",
        "part_b": "Load revenue page, verify metrics render",
        "key_files": ["frontend/app/admin/revenue/page.tsx"]
    },
    {
        "id": "J10.9.2",
        "part_a": "Verify MRR (Monthly Recurring Revenue) calculation",
        "part_b": "Check MRR matches sum of client subscriptions",
        "key_files": ["frontend/app/admin/revenue/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.9.3",
        "part_a": "Verify revenue trend chart displays",
        "part_b": "Check chart renders with historical data",
        "key_files": ["frontend/app/admin/revenue/page.tsx"]
    },
    {
        "id": "J10.9.4",
        "part_a": "Verify revenue breakdown by client",
        "part_b": "Check per-client revenue displays correctly",
        "key_files": ["frontend/app/admin/revenue/page.tsx"]
    }
]

PASS_CRITERIA = [
    "Revenue page loads correctly",
    "MRR calculation is accurate",
    "Revenue trend chart displays",
    "Per-client breakdown is accurate"
]

KEY_FILES = [
    "frontend/app/admin/revenue/page.tsx",
    "src/api/routes/admin.py"
]

# Revenue Metrics Reference
REVENUE_METRICS = [
    {"metric": "MRR", "calculation": "Sum of all active client monthly fees"},
    {"metric": "ARR", "calculation": "MRR * 12"},
    {"metric": "Churn", "calculation": "Cancelled MRR / Total MRR"},
    {"metric": "Net Revenue", "calculation": "New MRR - Churned MRR"},
    {"metric": "LTV", "calculation": "Average MRR * Average customer lifetime"}
]

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
