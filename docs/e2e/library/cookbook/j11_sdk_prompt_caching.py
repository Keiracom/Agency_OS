"""
Skill: J11.7 — SDK Prompt Caching
Journey: J11 - SDK Foundation
Checks: 5

Purpose: Verify prompt caching reduces costs by caching ICP and industry context.
"""

CHECKS = [
    {
        "id": "J11.7.1",
        "part_a": "Verify cache key patterns from config",
        "part_b": "Check sdk:icp:{client_id}, sdk:industry:{slug}, sdk:company:{domain}",
        "key_files": ["config/sdk_config.json"]
    },
    {
        "id": "J11.7.2",
        "part_a": "Verify ICP context cached per client",
        "part_b": "First call caches, second call uses cached — check Redis/memory",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.7.3",
        "part_a": "Verify industry research cached",
        "part_b": "Two leads same industry — second uses cached context",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.7.4",
        "part_a": "Verify cache TTL enforced (300 seconds default)",
        "part_b": "Wait past TTL — verify cache miss and refresh",
        "key_files": ["config/sdk_config.json", "src/agents/sdk_agents/sdk_brain.py"]
    },
    {
        "id": "J11.7.5",
        "part_a": "Verify cache hit rate tracked",
        "part_b": "Check monitoring reports cache_hit_rate metric",
        "key_files": ["src/agents/sdk_agents/sdk_brain.py"]
    }
]

PASS_CRITERIA = [
    "Cache keys follow defined patterns",
    "ICP context cached and reused",
    "Industry research cached across leads",
    "Cache expires after TTL",
    "Cache hit rate tracked for monitoring"
]

KEY_FILES = [
    "src/agents/sdk_agents/sdk_brain.py",
    "config/sdk_config.json"
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
