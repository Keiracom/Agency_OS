"""
Skill: J10.3 — KPI Section
Journey: J10 - Admin Dashboard
Checks: 8

Purpose: Verify Key Performance Indicator cards display correct metrics.
"""

CHECKS = [
    {
        "id": "J10.3.1",
        "part_a": "Read admin page KPI component — verify metrics list",
        "part_b": "Load dashboard, verify KPI cards render",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.3.2",
        "part_a": "Verify Active Leads KPI displays correctly",
        "part_b": "Check lead count matches database count",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.3.3",
        "part_a": "Verify Active Campaigns KPI displays correctly",
        "part_b": "Check campaign count matches active campaigns",
        "key_files": ["frontend/app/admin/page.tsx", "src/api/routes/admin.py"]
    },
    {
        "id": "J10.3.4",
        "part_a": "Verify Revenue KPI displays correctly",
        "part_b": "Check revenue figure is calculated correctly",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/revenue/page.tsx"]
    },
    {
        "id": "J10.3.5",
        "part_a": "Verify AI Cost KPI displays correctly",
        "part_b": "Check AI spend matches cost tracking",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/costs/ai/page.tsx"]
    },
    {
        "id": "J10.3.6",
        "part_a": "Verify Client Count KPI displays correctly",
        "part_b": "Check client count matches database",
        "key_files": ["frontend/app/admin/page.tsx", "frontend/app/admin/clients/page.tsx"]
    },
    {
        "id": "J10.3.7",
        "part_a": "Verify KPI trend indicators work",
        "part_b": "Check up/down arrows reflect actual changes",
        "key_files": ["frontend/app/admin/page.tsx"]
    },
    {
        "id": "J10.3.8",
        "part_a": "Verify KPI cards link to detail pages",
        "part_b": "Click each KPI card, verify navigation",
        "key_files": ["frontend/app/admin/page.tsx"]
    }
]

PASS_CRITERIA = [
    "All KPI cards render with data",
    "Lead count is accurate",
    "Campaign count is accurate",
    "Revenue calculation is correct",
    "AI cost tracking is accurate",
    "Client count matches reality",
    "Trend indicators reflect actual changes",
    "KPI cards are clickable and navigate correctly"
]

KEY_FILES = [
    "frontend/app/admin/page.tsx",
    "src/api/routes/admin.py",
    "frontend/app/admin/revenue/page.tsx",
    "frontend/app/admin/costs/ai/page.tsx",
    "frontend/app/admin/clients/page.tsx"
]

# KPI Metrics Reference
KPI_METRICS = [
    {"name": "Active Leads", "source": "leads table count", "trend": "7-day change"},
    {"name": "Active Campaigns", "source": "campaigns where status='active'", "trend": "vs last month"},
    {"name": "Revenue", "source": "revenue table sum", "trend": "MTD vs last month"},
    {"name": "AI Costs", "source": "llm_usage table sum", "trend": "MTD vs budget"},
    {"name": "Clients", "source": "clients table count", "trend": "30-day change"},
    {"name": "Messages Sent", "source": "outreach_log count", "trend": "24h count"}
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
