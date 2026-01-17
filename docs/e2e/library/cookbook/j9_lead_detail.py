"""
Skill: J9.7 — Lead Detail Page
Journey: J9 - Client Dashboard
Checks: 5

Purpose: Verify lead detail page displays complete lead information including
contact details, ALS scorecard, activity timeline, and communication history.
"""

CHECKS = [
    {
        "id": "J9.7.1",
        "part_a": "Verify lead detail page renders",
        "part_b": "Navigate to /dashboard/leads/[id], check page renders with lead data",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"]
    },
    {
        "id": "J9.7.2",
        "part_a": "Verify lead contact information displays",
        "part_b": "Page shows name, email, phone, company, title, LinkedIn URL",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"]
    },
    {
        "id": "J9.7.3",
        "part_a": "Verify ALS scorecard displays with breakdown",
        "part_b": "ALSScorecard component shows total score and factor breakdown",
        "key_files": ["frontend/components/leads/ALSScorecard.tsx", "frontend/app/dashboard/leads/[id]/page.tsx"]
    },
    {
        "id": "J9.7.4",
        "part_a": "Verify activity timeline shows all interactions",
        "part_b": "Timeline shows emails sent, replies, score changes, status updates",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx"]
    },
    {
        "id": "J9.7.5",
        "part_a": "Verify communication history displays",
        "part_b": "Email thread and/or call transcripts display with timestamps",
        "key_files": ["frontend/app/dashboard/leads/[id]/page.tsx", "frontend/components/communication/TranscriptViewer.tsx"]
    },
]

PASS_CRITERIA = [
    "Lead detail page renders without errors",
    "Contact information displays completely",
    "ALS scorecard shows score and breakdown",
    "Activity timeline shows all interactions",
    "Communication history displays with transcripts",
]

KEY_FILES = [
    "frontend/app/dashboard/leads/[id]/page.tsx",
    "frontend/components/leads/ALSScorecard.tsx",
    "frontend/components/communication/TranscriptViewer.tsx",
    "src/api/routes/leads.py",
    "src/models/lead.py",
]


def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Checks", ""]
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    lines.append("")
    lines.append("### Key Files")
    for f in KEY_FILES:
        lines.append(f"- {f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_instructions())
