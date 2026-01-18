"""
Skill: J7.15 — SDK Objection Handler
Journey: J7 - Reply Handling
Checks: 6

Purpose: Verify SDK generates context-aware objection responses.
"""

# =============================================================================
# LIVE TEST CONFIGURATION
# =============================================================================

LIVE_CONFIG = {
    "api_url": "https://agency-os-production.up.railway.app",
    "frontend_url": "https://agency-os-liart.vercel.app",
    "supabase_url": "https://jatzvazlbusedwsnqxzr.supabase.co",
    "prefect_url": "https://prefect-server-production-f9b1.up.railway.app"
}

# =============================================================================
# SDK OBJECTION HANDLER CONSTANTS
# =============================================================================

OBJECTION_TYPES = {
    "budget": "Price or cost concerns",
    "timing": "Not the right time",
    "authority": "Not the decision maker",
    "need": "No perceived need",
    "competition": "Using another solution",
    "trust": "Credibility concerns"
}

RESPONSE_TECHNIQUES = {
    "acknowledge_redirect": "Validate concern, then redirect to value",
    "question_back": "Ask clarifying question to understand better",
    "social_proof": "Share similar customer success stories",
    "reframe": "Reframe the objection as a benefit",
    "trial_offer": "Offer low-risk trial or demo",
    "case_study": "Share specific case study/data"
}

SDK_AGENT_FILES = {
    "objection_agent": "src/agents/sdk_agents/objection_agent.py",
    "sdk_models": "src/agents/sdk_agents/sdk_models.py",
    "reply_handler": "src/engines/reply_handler.py"
}

ESCALATION_TRIGGERS = {
    "complex_objection": "Multi-faceted or unusual objection",
    "high_value_lead": "Lead score above threshold",
    "repeated_objection": "Same objection raised multiple times",
    "legal_mention": "Legal or contract concerns mentioned"
}

# =============================================================================
# CHECKS
# =============================================================================

CHECKS = [
    {
        "id": "J7.15.1",
        "part_a": "Verify SDK objection agent called for negative replies",
        "part_b": "Check reply_handler calls objection_agent when intent=objection",
        "key_files": ["src/engines/reply_handler.py", "src/agents/sdk_agents/objection_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Objection agent invoked for negative intents",
            "expect": {
                "code_contains": ["objection_agent", "not_interested", "handle_objection"]
            }
        }
    },
    {
        "id": "J7.15.2",
        "part_a": "Verify objection agent receives thread context",
        "part_b": "Check ObjectionInput includes thread_context with previous messages",
        "key_files": ["src/agents/sdk_agents/objection_agent.py", "src/agents/sdk_agents/sdk_models.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Thread context passed to objection agent",
            "expect": {
                "code_contains": ["thread_context", "previous_messages", "ObjectionInput"]
            }
        }
    },
    {
        "id": "J7.15.3",
        "part_a": "Verify objection type classified",
        "part_b": "Check: budget, timing, authority, need, competition, trust identified",
        "key_files": ["src/agents/sdk_agents/objection_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Objection type classification implemented",
            "expect": {
                "code_contains": ["budget", "timing", "authority", "need", "competition", "trust"]
            }
        }
    },
    {
        "id": "J7.15.4",
        "part_a": "Verify response uses appropriate technique",
        "part_b": "Check technique_used: acknowledge_redirect, question_back, social_proof, etc.",
        "key_files": ["src/agents/sdk_agents/objection_agent.py", "src/agents/sdk_agents/sdk_models.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Response technique selection implemented",
            "expect": {
                "code_contains": ["technique", "acknowledge", "question", "social_proof"]
            }
        }
    },
    {
        "id": "J7.15.5",
        "part_a": "Verify escalate_to_human flag works",
        "part_b": "Check complex objections flagged for human review",
        "key_files": ["src/agents/sdk_agents/objection_agent.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Human escalation flag implemented",
            "expect": {
                "code_contains": ["escalate", "human", "review", "flag"]
            }
        }
    },
    {
        "id": "J7.15.6",
        "part_a": "Verify response sent via correct channel",
        "part_b": "Check email/LinkedIn/SMS response matches original channel",
        "key_files": ["src/engines/reply_handler.py"],
        "live_test": {
            "type": "code_verify",
            "check": "Response channel matching implemented",
            "expect": {
                "code_contains": ["channel", "email", "linkedin", "sms", "send"]
            }
        }
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

# =============================================================================
# EXECUTION HELPERS
# =============================================================================

def get_api_url(path: str) -> str:
    """Get full API URL for live testing."""
    base = LIVE_CONFIG["api_url"]
    return f"{base}{path}"

def get_instructions() -> str:
    """Return formatted instructions for Claude Code."""
    lines = [f"## {__doc__}", "", "### Live Test Configuration", ""]
    lines.append(f"- API: {LIVE_CONFIG['api_url']}")
    lines.append(f"- Frontend: {LIVE_CONFIG['frontend_url']}")
    lines.append(f"- Supabase: {LIVE_CONFIG['supabase_url']}")
    lines.append(f"- Prefect: {LIVE_CONFIG['prefect_url']}")
    lines.append("")
    lines.append("### Objection Types")
    for objection, description in OBJECTION_TYPES.items():
        lines.append(f"  {objection}: {description}")
    lines.append("")
    lines.append("### Response Techniques")
    for technique, description in RESPONSE_TECHNIQUES.items():
        lines.append(f"  {technique}: {description}")
    lines.append("")
    lines.append("### SDK Agent Files")
    for name, path in SDK_AGENT_FILES.items():
        lines.append(f"  {name}: {path}")
    lines.append("")
    lines.append("### Escalation Triggers")
    for trigger, description in ESCALATION_TRIGGERS.items():
        lines.append(f"  {trigger}: {description}")
    lines.append("")
    lines.append("### Checks")
    lines.append("")
    for check in CHECKS:
        lines.append(f"**{check['id']}**")
        lines.append(f"  Part A: {check['part_a']}")
        lines.append(f"  Part B: {check['part_b']}")
        if check.get("key_files"):
            lines.append(f"  Key Files: {', '.join(check['key_files'])}")
        lt = check.get("live_test", {})
        if lt:
            lines.append(f"  Live Test Type: {lt.get('type', 'N/A')}")
        lines.append("")
    lines.append("### Pass Criteria")
    for criterion in PASS_CRITERIA:
        lines.append(f"- [ ] {criterion}")
    return "\n".join(lines)
