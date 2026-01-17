"""
Skill: J10.10 — AI Costs Page
Journey: J10 - Admin Dashboard
Checks: 6

Purpose: Verify AI/LLM cost tracking and budget management.
"""

CHECKS = [
    {
        "id": "J10.10.1",
        "part_a": "Read `frontend/app/admin/costs/ai/page.tsx` — verify cost display",
        "part_b": "Load AI costs page, verify metrics render",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"]
    },
    {
        "id": "J10.10.2",
        "part_a": "Verify total AI spend displays correctly",
        "part_b": "Check spend matches llm_usage table sum",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.10.3",
        "part_a": "Verify cost breakdown by model",
        "part_b": "Check GPT-4, Claude costs display separately",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"]
    },
    {
        "id": "J10.10.4",
        "part_a": "Verify cost breakdown by feature",
        "part_b": "Check ICP analysis, email generation, etc. costs",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"]
    },
    {
        "id": "J10.10.5",
        "part_a": "Verify budget vs actual comparison",
        "part_b": "Check budget threshold warnings work",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"]
    },
    {
        "id": "J10.10.6",
        "part_a": "Verify cost trend chart displays",
        "part_b": "Check historical cost data renders in chart",
        "key_files": ["frontend/app/admin/costs/ai/page.tsx"]
    }
]

PASS_CRITERIA = [
    "AI costs page loads correctly",
    "Total spend is accurate",
    "Model breakdown is accurate",
    "Feature breakdown is accurate",
    "Budget warnings function",
    "Cost trend chart displays"
]

KEY_FILES = [
    "frontend/app/admin/costs/ai/page.tsx",
    "src/api/routes/admin.py",
    "src/models/llm_usage.py"
]

# AI Cost Categories Reference
AI_COST_CATEGORIES = [
    {"category": "ICP Analysis", "models": ["claude-3-opus", "gpt-4"], "typical_cost": "$0.10-0.50 per analysis"},
    {"category": "Email Generation", "models": ["claude-3-haiku", "gpt-3.5-turbo"], "typical_cost": "$0.01-0.05 per email"},
    {"category": "Lead Scoring", "models": ["claude-3-haiku"], "typical_cost": "$0.005 per lead"},
    {"category": "Reply Classification", "models": ["claude-3-haiku"], "typical_cost": "$0.01 per reply"}
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
