"""
Contract: docs/e2e/tools/e2e_starter.py
Purpose: E2E Session Starter - Full context for Claude Code E2E testing sessions
Layer: CLI tool
Commands: start, context, brief, philosophy

Integrates:
- Test Plan (Sparro, recipients, ALS tiers, budget)
- Task Breakdown (Part A/B philosophy, what to look for)
- Current progress and next task
- Key source files for the task
"""

import io
import json
import sys
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths
BASE_DIR = Path(__file__).parent.parent
ROOT_DIR = BASE_DIR.parent.parent
STATE_DIR = BASE_DIR / "state"
COOKBOOK_DIR = BASE_DIR / "library" / "cookbook"
PROCESS_FILE = STATE_DIR / "process.json"

# =============================================================================
# TESTING PHILOSOPHY (from E2E_TASK_BREAKDOWN.md)
# =============================================================================

TESTING_PHILOSOPHY = """
## Every Sub-Task Has Two Parts

PART A: CODE & WIRING VERIFICATION
  - Read the actual source files
  - Trace the code path from trigger to completion
  - Check for incomplete implementations
  - Verify configuration is correct
  - Create missing files if needed

PART B: LIVE EXECUTION TEST
  - Execute the actual functionality
  - Observe behavior and logs
  - Compare to expected results
  - Document pass/fail
"""

WHAT_TO_LOOK_FOR = {
    "Missing Implementation": ["TODO", "FIXME", "pass", "NotImplementedError", "stub returns"],
    "Wrong Configuration": ["Env vars pointing to wrong service", "hardcoded dev URLs"],
    "Incomplete Wiring": ["API endpoint exists but doesn't call the engine"],
    "Silent Failures": ["try/except that swallows errors without logging"],
    "Missing Error Handling": ["No try/catch", "no user-friendly error messages"],
    "Wrong Dependencies": ["Importing from wrong layer", "circular imports"],
    "Missing Database": ["Tables/columns referenced but don't exist"],
    "Missing Files": ["Code imports file that doesn't exist"]
}

# =============================================================================
# TEST PLAN CONTEXT (from E2E_TEST_PLAN.md)
# =============================================================================

TEST_AGENCY = {
    "name": "Sparro Digital",
    "website": "https://sparro.com.au",
    "location": "Melbourne, Australia",
    "type": "Digital Marketing Agency (Performance Marketing)",
    "size": "30-50 employees",
    "mrr": "$100K+",
    "tier": "Velocity ($5,000/mo)",
    "services": "Paid Media, SEO, Social, Analytics",
    "target_clients": "E-commerce, Retail, DTC brands"
}

EXPECTED_ICP = {
    "titles": ["Marketing Manager", "Head of Digital", "E-commerce Manager", "CMO", "Founder"],
    "industries": ["E-commerce", "Retail", "DTC", "Fashion", "Beauty", "Consumer Goods"],
    "company_size": "10-200 employees",
    "location": "Australia (primary), NZ (secondary)",
    "pain_points": ["ROAS pressure", "scaling paid media", "attribution", "incrementality"]
}

TEST_RECIPIENTS = {
    "email": "david.stephens@keiracom.com",
    "sms": "+61457543392",
    "voice": "+61457543392",
    "linkedin": "linkedin.com/in/david-stephens-8847a636a/"
}

ALS_TIERS = {
    "Hot":  {"range": "85-100", "channels": "Email, SMS, LinkedIn, Voice, Direct Mail"},
    "Warm": {"range": "60-84",  "channels": "Email, LinkedIn, Voice"},
    "Cool": {"range": "35-59",  "channels": "Email, LinkedIn"},
    "Cold": {"range": "20-34",  "channels": "Email only"},
    "Dead": {"range": "<20",    "channels": "None (suppressed)"}
}

ALS_FORMULA = {
    "Data Quality":    {"max": 20, "weight": "20%", "measures": "Verified email, phone, LinkedIn"},
    "Authority":       {"max": 25, "weight": "25%", "measures": "Job title seniority"},
    "Company Fit":     {"max": 25, "weight": "25%", "measures": "Industry, size, location"},
    "Timing":          {"max": 15, "weight": "15%", "measures": "New role, hiring, funding"},
    "Risk":            {"max": 15, "weight": "15%", "measures": "Bounces, unsubscribes, competitors"},
    "LinkedIn Boost":  {"max": 10, "weight": "+",   "measures": "Engagement signals (posts, connections)"},
    "Buyer Boost":     {"max": 15, "weight": "+",   "measures": "Known agency buyer (Phase 24F)"}
}

BUDGET = {
    "total": "$65 AUD",
    "breakdown": {
        "Apollo": "$50 (50 credits for leads)",
        "Apify": "$2 (LinkedIn scraping)",
        "Anthropic": "$9 (ICP + content gen)",
        "Twilio": "$0.60 (SMS + Voice tests)",
        "Salesforge": "Included"
    }
}

CRITICAL_RULES = [
    "Hot tier starts at 85, NOT 80",
    "TEST_MODE must redirect ALL outreach to test recipients",
    "No paid API calls without CEO approval",
    "Email daily limit: 15 during warmup, 90 post-warmup",
    "LinkedIn: 20 requests/day/seat max (Rule 17)",
    "Always do Part A (code check) BEFORE Part B (live test)"
]

APPROVAL_GATES = {
    "GATE-1": {"trigger": "Start J0", "cost": "$0", "action": "Approve plan"},
    "GATE-2": {"trigger": "ICP extraction (J1.10)", "cost": "~$3", "action": "Approve Anthropic call"},
    "GATE-3": {"trigger": "Lead sourcing (J2.3)", "cost": "~$50", "action": "Approve Apollo credits"},
    "GATE-4": {"trigger": "Any outreach (J3+)", "cost": "~$1", "action": "Confirm TEST_MODE verified"}
}

# Journey-specific key files
JOURNEY_KEY_FILES = {
    "J0": ["Railway services", "config/", "src/integrations/"],
    "J1": ["frontend/app/auth/", "frontend/app/onboarding/", "src/api/routes/onboarding.py", "src/engines/icp_scraper.py"],
    "J2": ["frontend/app/campaigns/", "src/api/routes/campaigns.py", "src/integrations/apollo.py", "src/engines/scorer.py"],
    "J2B": ["src/engines/scout.py", "src/integrations/apify.py", "src/engines/scorer.py", "src/orchestration/flows/enrichment_flow.py"],
    "J3": ["src/engines/email.py", "src/integrations/salesforge.py", "src/orchestration/flows/outreach_flow.py"],
    "J4": ["src/engines/sms.py", "src/integrations/twilio.py", "src/integrations/clicksend.py", "src/integrations/dncr.py"],
    "J5": ["src/engines/voice.py", "src/integrations/vapi.py", "src/integrations/elevenlabs.py"],
    "J6": ["src/engines/linkedin.py", "src/integrations/unipile.py"],
    "J7": ["src/engines/closer.py", "src/api/routes/webhooks.py", "src/services/thread_service.py"],
    "J8": ["src/services/meeting_service.py", "src/services/deal_service.py", "src/api/routes/webhooks.py"],
    "J9": ["frontend/app/dashboard/", "src/api/routes/stats.py", "src/api/routes/leads.py"],
    "J10": ["frontend/app/admin/", "src/api/routes/admin.py"]
}


def load_json(filepath: Path, default=None):
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return default
    except (json.JSONDecodeError, IOError):
        return default


def load_skill(skill_file: str) -> dict:
    skill_path = COOKBOOK_DIR / skill_file
    if not skill_path.exists():
        return {}
    try:
        content = skill_path.read_text(encoding="utf-8")
        exec_globals = {}
        exec(content, exec_globals)
        return {
            "docstring": exec_globals.get("__doc__", ""),
            "checks": exec_globals.get("CHECKS", []),
            "pass_criteria": exec_globals.get("PASS_CRITERIA", []),
            "key_files": exec_globals.get("KEY_FILES", [])
        }
    except Exception as e:
        return {"error": str(e)}


def get_next_task() -> dict:
    process_data = load_json(PROCESS_FILE)
    if not process_data:
        return None
    completed = set(process_data.get("completed", []))
    phases = process_data.get("phases", {})
    for phase_id in sorted(phases.keys(), key=lambda x: (x.replace("J2B", "J2Z"))):
        phase = phases[phase_id]
        for task in phase.get("tasks", []):
            if task.get("id") not in completed:
                return {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "phase_id": phase_id,
                    "phase_name": phase.get("name"),
                    "skill_file": task.get("skill_file"),
                    "checks": task.get("checks", 0)
                }
    return None


def get_progress() -> dict:
    process_data = load_json(PROCESS_FILE)
    if not process_data:
        return {"total": 0, "completed": 0, "remaining": 0, "percent": 0}
    completed = len(process_data.get("completed", []))
    total = sum(len(p.get("tasks", [])) for p in process_data.get("phases", {}).values())
    return {
        "total": total,
        "completed": completed,
        "remaining": total - completed,
        "percent": round((completed / total) * 100, 1) if total > 0 else 0
    }


def section(title: str, char: str = "="):
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}")


def cmd_start():
    """Full session starter - everything Claude needs."""

    print("\n" + "=" * 70)
    print("  E2E TESTING SESSION STARTER")
    print("=" * 70)

    # Progress
    p = get_progress()
    print(f"\n  Progress: {p['completed']}/{p['total']} tasks ({p['percent']}%)")

    # Testing Philosophy
    section("TESTING PHILOSOPHY", "=")
    print(TESTING_PHILOSOPHY)

    # What to Look For
    section("WHAT TO LOOK FOR (Part A)", "-")
    for category, examples in WHAT_TO_LOOK_FOR.items():
        print(f"  {category}:")
        print(f"    {', '.join(examples)}")

    # Test Recipients (CRITICAL)
    section("TEST RECIPIENTS - ALL OUTREACH REDIRECTS HERE", "=")
    for channel, recipient in TEST_RECIPIENTS.items():
        print(f"  {channel.upper():10} {recipient}")

    # ALS Tiers
    section("ALS TIER THRESHOLDS", "-")
    for tier, info in ALS_TIERS.items():
        print(f"  {tier:5} {info['range']:8} -> {info['channels']}")
    print("\n  ** CRITICAL: Hot starts at 85, NOT 80 **")

    # Critical Rules
    section("CRITICAL RULES", "-")
    for i, rule in enumerate(CRITICAL_RULES, 1):
        print(f"  {i}. {rule}")

    # Next Task
    section("NEXT TASK", "=")
    next_task = get_next_task()
    if next_task:
        print(f"  ID:      {next_task['id']}")
        print(f"  Title:   {next_task['title']}")
        print(f"  Journey: {next_task['phase_id']} - {next_task['phase_name']}")
        print(f"  Checks:  {next_task['checks']}")

        # Journey key files
        journey_files = JOURNEY_KEY_FILES.get(next_task['phase_id'], [])
        if journey_files:
            print(f"\n  Journey Key Files:")
            for f in journey_files:
                print(f"    - {f}")

        # Load skill
        if next_task.get("skill_file"):
            skill = load_skill(next_task["skill_file"])
            if skill and not skill.get("error"):
                # Task-specific key files
                task_files = skill.get("key_files", [])
                if task_files:
                    print(f"\n  Task Key Files (READ THESE):")
                    for f in task_files:
                        print(f"    -> {f}")

                # Checks
                checks = skill.get("checks", [])
                if checks:
                    section("CHECKS TO PERFORM", "-")
                    for check in checks:
                        print(f"\n  [{check.get('id')}]")
                        print(f"    Part A: {check.get('part_a', 'N/A')}")
                        print(f"    Part B: {check.get('part_b', 'N/A')}")
                        if check.get('key_files'):
                            print(f"    Files:  {', '.join(check['key_files'])}")

                # Pass criteria
                criteria = skill.get("pass_criteria", [])
                if criteria:
                    section("PASS CRITERIA", "-")
                    for c in criteria:
                        print(f"  [ ] {c}")
    else:
        print("  All tasks completed!")

    # Commands
    section("COMMANDS", "-")
    print("  Complete:  python docs/e2e/tools/progress.py complete <ID> --summary \"...\"")
    print("  Capture:   python docs/e2e/tools/progress.py capture <name> \"description\"")
    print("  Status:    python docs/e2e/tools/progress.py status")
    print("  QA:        python docs/e2e/tools/qa_runner.py verify_all")

    # Approval gates reminder
    if next_task:
        phase = next_task['phase_id']
        if phase == "J1" and "10" in next_task['id']:
            print("\n  !! GATE-2: ICP extraction requires CEO approval for Anthropic (~$3)")
        elif phase == "J2" and "3" in next_task['id']:
            print("\n  !! GATE-3: Lead sourcing requires CEO approval for Apollo (~$50)")
        elif phase in ["J3", "J4", "J5", "J6"]:
            print("\n  !! GATE-4: Outreach requires TEST_MODE verification first")

    print("\n" + "=" * 70)
    print("  SESSION READY - Remember: Part A (code) before Part B (live test)")
    print("=" * 70 + "\n")


def cmd_context():
    """Show full test plan context."""

    section("TEST AGENCY: SPARRO DIGITAL", "=")
    for key, value in TEST_AGENCY.items():
        print(f"  {key}: {value}")

    section("EXPECTED ICP", "-")
    print(f"  Titles:      {', '.join(EXPECTED_ICP['titles'])}")
    print(f"  Industries:  {', '.join(EXPECTED_ICP['industries'])}")
    print(f"  Size:        {EXPECTED_ICP['company_size']}")
    print(f"  Location:    {EXPECTED_ICP['location']}")
    print(f"  Pain Points: {', '.join(EXPECTED_ICP['pain_points'])}")

    section("ALS SCORING FORMULA", "-")
    for component, info in ALS_FORMULA.items():
        print(f"  {component:15} max {info['max']:2} pts ({info['weight']}) - {info['measures']}")

    section("BUDGET: $65 AUD", "-")
    for api, cost in BUDGET['breakdown'].items():
        print(f"  {api:12} {cost}")

    section("APPROVAL GATES", "-")
    for gate, info in APPROVAL_GATES.items():
        print(f"  {gate}: {info['trigger']} -> {info['cost']} -> {info['action']}")

    print()


def cmd_philosophy():
    """Show just the testing philosophy."""

    section("E2E TESTING PHILOSOPHY", "=")
    print(TESTING_PHILOSOPHY)

    section("WHAT TO LOOK FOR", "-")
    for category, examples in WHAT_TO_LOOK_FOR.items():
        print(f"\n  {category}:")
        for ex in examples:
            print(f"    - {ex}")

    print()


def cmd_brief():
    """Ultra-short summary."""

    p = get_progress()
    next_task = get_next_task()

    print("\n" + "-" * 50)
    print("E2E BRIEF")
    print("-" * 50)
    print(f"Progress: {p['completed']}/{p['total']} ({p['percent']}%)")

    if next_task:
        print(f"Next:     {next_task['id']} - {next_task['title']}")
        if next_task.get("skill_file"):
            skill = load_skill(next_task["skill_file"])
            key_files = skill.get("key_files", [])
            if key_files:
                print(f"Files:    {', '.join(key_files[:3])}")

    print("-" * 50)
    print(f"Test Email: {TEST_RECIPIENTS['email']}")
    print("Hot Tier:   85-100 (NOT 80!)")
    print("Philosophy: Part A (code) -> Part B (live)")
    print("-" * 50 + "\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="E2E Session Starter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start       Full session context (DEFAULT)
  context     Test plan details only
  philosophy  Testing philosophy only
  brief       Quick summary

Examples:
  python e2e_starter.py
  python e2e_starter.py start
  python e2e_starter.py brief
"""
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "context", "philosophy", "brief"],
        help="Command (default: start)"
    )

    args = parser.parse_args()

    if args.command == "start":
        cmd_start()
    elif args.command == "context":
        cmd_context()
    elif args.command == "philosophy":
        cmd_philosophy()
    elif args.command == "brief":
        cmd_brief()


if __name__ == "__main__":
    main()
