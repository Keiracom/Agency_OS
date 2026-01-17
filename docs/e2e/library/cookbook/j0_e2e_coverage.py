"""
Skill: J0.9 — E2E Coverage Verification (Meta-Check)
Journey: J0 - Infrastructure & Wiring Audit
Checks: 7

Purpose: Verify all major Prefect flows and engines have E2E journey coverage.
"""

CHECKS = [
    {
        "id": "J0.9.1",
        "part_a": "List all flows in `src/orchestration/flows/`",
        "part_b": "Cross-reference with E2E journeys",
        "key_files": ["src/orchestration/flows/"]
    },
    {
        "id": "J0.9.2",
        "part_a": "List all engines in `src/engines/`",
        "part_b": "Verify each has journey coverage",
        "key_files": ["src/engines/"]
    },
    {
        "id": "J0.9.3",
        "part_a": "Verify enrichment flows have journey (J2B)",
        "part_b": "Check enrichment_flow.py covered",
        "key_files": ["src/orchestration/flows/enrichment_flow.py"]
    },
    {
        "id": "J0.9.4",
        "part_a": "Verify scoring engine has journey (J2B.5)",
        "part_b": "Check scorer.py covered",
        "key_files": ["src/engines/scorer.py"]
    },
    {
        "id": "J0.9.5",
        "part_a": "Verify each outreach channel has journey (J3-J6)",
        "part_b": "Check all 4 channels",
        "key_files": ["src/engines/email.py", "src/engines/sms.py", "src/engines/voice.py", "src/engines/linkedin.py"]
    },
    {
        "id": "J0.9.6",
        "part_a": "Verify reply handling has journey (J7)",
        "part_b": "Check reply_flow.py covered",
        "key_files": ["src/orchestration/flows/reply_flow.py"]
    },
    {
        "id": "J0.9.7",
        "part_a": "Verify meeting/deals has journey (J8)",
        "part_b": "Check meeting_flow.py covered",
        "key_files": ["src/orchestration/flows/meeting_flow.py"]
    }
]

PASS_CRITERIA = [
    "Every Prefect flow has E2E journey coverage",
    "Every engine has E2E journey coverage",
    "No orphan flows/engines without tests",
    "Coverage map is up-to-date"
]

KEY_FILES = [
    "src/orchestration/flows/",
    "src/engines/"
]

# Flow-to-Journey Mapping
FLOW_MAPPING = [
    {"flow": "campaign_flow.py", "journey": "J2.4", "status": "Covered"},
    {"flow": "pool_population_flow.py", "journey": "J2.5", "status": "Covered"},
    {"flow": "pool_assignment_flow.py", "journey": "J2.6", "status": "Covered"},
    {"flow": "lead_enrichment_flow.py", "journey": "J2B", "status": "Covered"},
    {"flow": "outreach_flow.py (email)", "journey": "J3", "status": "Covered"},
    {"flow": "outreach_flow.py (sms)", "journey": "J4", "status": "Covered"},
    {"flow": "outreach_flow.py (voice)", "journey": "J5", "status": "Covered"},
    {"flow": "outreach_flow.py (linkedin)", "journey": "J6", "status": "Covered"},
    {"flow": "reply_recovery_flow.py", "journey": "J7", "status": "Covered"},
    {"flow": "meeting_flow.py", "journey": "J8", "status": "Covered"},
    {"flow": "onboarding_flow.py", "journey": "J1", "status": "Covered"},
]

# Engine-to-Journey Mapping
ENGINE_MAPPING = [
    {"engine": "scorer.py", "journey": "J2.7, J2B.5", "status": "Covered"},
    {"engine": "scout.py", "journey": "J2B.2-J2B.3", "status": "Covered"},
    {"engine": "content.py", "journey": "J2.9", "status": "Covered"},
    {"engine": "email.py", "journey": "J3", "status": "Covered"},
    {"engine": "sms.py", "journey": "J4", "status": "Covered"},
    {"engine": "voice.py", "journey": "J5", "status": "Covered"},
    {"engine": "linkedin.py", "journey": "J6", "status": "Covered"},
    {"engine": "reply_handler.py", "journey": "J7", "status": "Covered"},
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
