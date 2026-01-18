"""
Skill: J5.14 — SDK Voice KB Generation
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify SDK generates per-call knowledge base for Vapi voice calls.
"""

CHECKS = [
    {
        "id": "J5.14.1",
        "part_a": "Verify SDK voice KB agent called before voice call",
        "part_b": "Check voice engine calls voice_kb_agent for Hot leads",
        "key_files": ["src/engines/voice.py", "src/agents/sdk_agents/voice_kb_agent.py"]
    },
    {
        "id": "J5.14.2",
        "part_a": "Verify voice KB agent receives lead + enrichment data",
        "part_b": "Check VoiceKBInput includes lead, enrichment, campaign",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py", "src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J5.14.3",
        "part_a": "Verify pronunciation guide generated",
        "part_b": "Check output includes phonetic pronunciation for name, company",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"]
    },
    {
        "id": "J5.14.4",
        "part_a": "Verify personalized openers generated",
        "part_b": "Check multiple opener options with context for when to use",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"]
    },
    {
        "id": "J5.14.5",
        "part_a": "Verify pain point probes generated",
        "part_b": "Check questions mapped to identified pain points",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"]
    },
    {
        "id": "J5.14.6",
        "part_a": "Verify objection handlers populated",
        "part_b": "Check: no_budget, no_time, not_interested, using_competitor responses",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py", "src/agents/sdk_agents/sdk_models.py"]
    },
    {
        "id": "J5.14.7",
        "part_a": "Verify KB passed to Vapi assistant config",
        "part_b": "Check Vapi call includes dynamic KB in system prompt",
        "key_files": ["src/engines/voice.py", "src/integrations/vapi.py"]
    }
]

PASS_CRITERIA = [
    "Voice KB agent called for Hot leads before call",
    "Agent receives full context (lead + enrichment + campaign)",
    "Pronunciation guide accurate",
    "Multiple openers with use-case context",
    "Pain point probes relevant to enrichment",
    "All objection handlers populated",
    "KB injected into Vapi call"
]

KEY_FILES = [
    "src/engines/voice.py",
    "src/agents/sdk_agents/voice_kb_agent.py",
    "src/agents/sdk_agents/sdk_models.py",
    "src/integrations/vapi.py"
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
