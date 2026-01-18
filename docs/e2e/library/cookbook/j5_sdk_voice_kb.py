"""
Skill: J5.14 — SDK Voice KB Generation
Journey: J5 - Voice Outreach
Checks: 7

Purpose: Verify SDK generates per-call knowledge base for Vapi voice calls.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app",
    "warning": "SDK KB generation uses Claude API - may incur costs"
}

# =============================================================================
# SDK VOICE KB CONFIGURATION
# =============================================================================

SDK_VOICE_KB = {
    "agent_file": "src/agents/sdk_agents/voice_kb_agent.py",
    "models_file": "src/agents/sdk_agents/sdk_models.py",
    "trigger_condition": "Hot tier leads (ALS >= 85)",
    "input_requirements": [
        "lead data",
        "enrichment data",
        "campaign context"
    ],
    "output_components": {
        "pronunciation_guide": "Phonetic spelling for name, company",
        "personalized_openers": "3-5 context-aware opening lines",
        "pain_point_probes": "Questions mapped to identified pain points",
        "objection_handlers": {
            "no_budget": "Budget objection response",
            "no_time": "Time objection response",
            "not_interested": "Interest objection response",
            "using_competitor": "Competitor objection response"
        }
    }
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J5.14.1",
        "part_a": "Verify SDK voice KB agent called before voice call",
        "part_b": "Check voice engine calls voice_kb_agent for Hot leads",
        "key_files": ["src/engines/voice.py", "src/agents/sdk_agents/voice_kb_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Voice engine invokes voice KB agent for eligible leads",
            "expect": {
                "code_contains": ["voice_kb_agent", "generate_kb", "Hot"]
            }
        }
    },
    {
        "id": "J5.14.2",
        "part_a": "Verify voice KB agent receives lead + enrichment data",
        "part_b": "Check VoiceKBInput includes lead, enrichment, campaign",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py", "src/agents/sdk_agents/sdk_models.py"],
        "live_test": {
            "type": "code_verify",
            "check": "VoiceKBInput model has all required fields",
            "expect": {
                "code_contains": ["VoiceKBInput", "lead", "enrichment", "campaign"]
            }
        }
    },
    {
        "id": "J5.14.3",
        "part_a": "Verify pronunciation guide generated",
        "part_b": "Check output includes phonetic pronunciation for name, company",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Pronunciation guide included in output",
            "expect": {
                "code_contains": ["pronunciation", "phonetic", "name", "company"]
            }
        }
    },
    {
        "id": "J5.14.4",
        "part_a": "Verify personalized openers generated",
        "part_b": "Check multiple opener options with context for when to use",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Multiple personalized openers generated",
            "expect": {
                "code_contains": ["opener", "personalized", "context"]
            }
        }
    },
    {
        "id": "J5.14.5",
        "part_a": "Verify pain point probes generated",
        "part_b": "Check questions mapped to identified pain points",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Pain point probing questions generated",
            "expect": {
                "code_contains": ["pain_point", "probe", "question"]
            }
        }
    },
    {
        "id": "J5.14.6",
        "part_a": "Verify objection handlers populated",
        "part_b": "Check: no_budget, no_time, not_interested, using_competitor responses",
        "key_files": ["src/agents/sdk_agents/voice_kb_agent.py", "src/agents/sdk_agents/sdk_models.py"],
        "live_test": {
            "type": "code_verify",
            "check": "All standard objection handlers defined",
            "expect": {
                "code_contains": ["objection", "no_budget", "no_time", "not_interested", "competitor"]
            }
        }
    },
    {
        "id": "J5.14.7",
        "part_a": "Verify KB passed to Vapi assistant config",
        "part_b": "Check Vapi call includes dynamic KB in system prompt",
        "key_files": ["src/engines/voice.py", "src/integrations/vapi.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Generated KB injected into Vapi system prompt",
            "expect": {
                "code_contains": ["system_prompt", "kb", "knowledge_base", "assistant"]
            }
        }
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

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test URLs", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Warning: {LIVE_CONFIG['warning']}")
    lines.append("")
    lines.append("### SDK Voice KB Configuration")
    lines.append(f"  Agent File: {SDK_VOICE_KB['agent_file']}")
    lines.append(f"  Models File: {SDK_VOICE_KB['models_file']}")
    lines.append(f"  Trigger Condition: {SDK_VOICE_KB['trigger_condition']}")
    lines.append("  Input Requirements:")
    for req in SDK_VOICE_KB['input_requirements']:
        lines.append(f"    - {req}")
    lines.append("  Output Components:")
    for component, desc in SDK_VOICE_KB['output_components'].items():
        if isinstance(desc, dict):
            lines.append(f"    {component}:")
            for sub_key, sub_val in desc.items():
                lines.append(f"      - {sub_key}: {sub_val}")
        else:
            lines.append(f"    - {component}: {desc}")
    lines.append("")
    lines.append("### Checks")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A (Code): {check['part_a']}")
        lines.append(f"  Part B (Live): {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
