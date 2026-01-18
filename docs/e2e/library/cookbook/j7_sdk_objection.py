"""
Skill: J7.15 — SDK Objection Handler
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify SDK generates context-aware objection responses.
"""

CHECKS = [
    {
        "id": "J7.15.1",
        "part_a": "Verify SDK objection agent called for negative replies",
        "part_b": "Check reply_handler calls objection_agent when intent=objection",
        "key_files": ["src/engines/reply_handler.py", "src/agents/sdk_agents/objection_agent.py"]
    },
    {
        "id": "J7.15.2",
        "part_a": "Verify objection agent receives thread context",
        "part_b": "Check ObjectionInput includes thread_context with previous messages",
        "key_files": ["src/agents/sdk_agents/objection_agent.py", "src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J7.15.3",
        "part_a": "Verify objection type classified",
        "part_b": "Check: budget, timing, authority, need, competition, trust identified",
        "key_files": ["src/agents/sdk_agents/objection_agent.py"]
    },
    {
        "id": "J7.15.4",
        "part_a": "Verify response uses appropriate technique",
        "part_b": "Check technique_used: acknowledge_redirect, question_back, social_proof, etc.",
        "key_files": ["src/agents/sdk_agents/objection_agent.py", "src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J7.15.5",
        "part_a": "Verify escalate_to_human flag works",
        "part_b": "Check complex objections flagged for human review",
        "key_files": ["src/agents/sdk_agents/objection_agent.py"]
    },
    {
        "id": "J7.15.6",
        "part_a": "Verify response sent via correct channel",
        "part_b": "Check email/LinkedIn/SMS response matches original channel",
        "key_files": ["src/engines/reply_handler.py"]
    }
]

PASS_CRITERIA = [
    "Objection agent called for negative intent replies",
    "Thread context provided for continuity",
    "Objection type correctly classified",
    "Response technique appropriate for objection",
    "Human escalation works for complex cases",
    "Response sent on correct channel"
]

KEY_FILES = [
    "src/engines/reply_handler.py",
    "src/agents/sdk_agents/objection_agent.py",
    "src/agents/sdk_agents/sdk_models.py"
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
