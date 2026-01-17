"""
Contract: tools/e2e.py
Purpose: E2E Testing runner - manages multi-session E2E testing with state persistence
Layer: CLI tool
Commands: status, next, complete, config
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# Paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
E2E_STATE_FILE = STATE_DIR / "e2e_state.json"
E2E_CONFIG_FILE = STATE_DIR / "e2e_config.json"
HISTORY_FILE = STATE_DIR / "session_history.json"

# Journey file mapping
JOURNEY_FILES = {
    "J0": "J0_INFRASTRUCTURE.md",
    "J1": "J1_ONBOARDING.md",
    "J2": "J2_CAMPAIGN.md",
    "J2B": "J2B_ENRICHMENT.md",
    "J3": "J3_EMAIL.md",
    "J4": "J4_SMS.md",
    "J5": "J5_VOICE.md",
    "J6": "J6_LINKEDIN.md",
    "J7": "J7_REPLY.md",
    "J8": "J8_MEETING.md",
    "J9": "J9_DASHBOARD.md",
    "J10": "J10_ADMIN.md",
}

JOURNEY_NAMES = {
    "J0": "Infrastructure & Wiring Audit",
    "J1": "Signup & Onboarding",
    "J2": "Campaign Setup",
    "J2B": "Lead Enrichment",
    "J3": "Email Outreach",
    "J4": "SMS Outreach",
    "J5": "Voice Outreach",
    "J6": "LinkedIn Outreach",
    "J7": "Reply Handling",
    "J8": "Meeting Booking",
    "J9": "Dashboard & Analytics",
    "J10": "Admin & Billing",
}


def load_json(filepath: Path, default=None):
    """Load JSON file, return default if missing or invalid."""
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return default
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return default


def save_json(filepath: Path, data):
    """Save data to JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def log_to_history(task_id: str, action: str, summary: str):
    """Log action to session history."""
    history = load_json(HISTORY_FILE, default=[])
    history.append({
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "action": action,
        "summary": summary,
    })
    save_json(HISTORY_FILE, history)


def get_journey_id(group_id: str) -> str:
    """Extract journey ID from group ID (e.g., J1.4 → J1, J2B.3 → J2B)."""
    match = re.match(r'^(J\d+B?)', group_id)
    return match.group(1) if match else None


def parse_group_from_journey(journey_path: Path, group_id: str) -> dict | None:
    """Extract a specific group's content from a journey markdown file."""
    if not journey_path.exists():
        return None

    with open(journey_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern to match group header: ### J1.4 — Title
    group_pattern = rf'### ({re.escape(group_id)}) — ([^\n]+)'
    match = re.search(group_pattern, content)
    if not match:
        return None

    group_title = match.group(2).strip()
    start_pos = match.start()

    # Find the end - either next E2E_SESSION_BREAK or next ### header
    end_pattern = r'<!-- E2E_SESSION_BREAK:|^### J\d+'
    end_match = re.search(end_pattern, content[match.end():], re.MULTILINE)

    if end_match:
        end_pos = match.end() + end_match.start()
        group_content = content[start_pos:end_pos].strip()

        # Extract next group from session break
        break_match = re.search(r'Next: (J[\d]+B?\.[\d]+)', content[end_pos:end_pos+200])
        next_group = break_match.group(1) if break_match else None
    else:
        group_content = content[start_pos:].strip()
        next_group = None

    # Count checks (lines starting with | J)
    check_count = len(re.findall(r'\| J[\d]+B?\.[\d]+\.[\d]+', group_content))

    return {
        "id": group_id,
        "title": group_title,
        "content": group_content,
        "next_group": next_group,
        "check_count": check_count,
    }


def get_next_group(state: dict) -> str | None:
    """Determine the next group based on current state."""
    current = state.get("current")
    completed = state.get("completed", [])
    journey_totals = state.get("journey_totals", {})

    if not current:
        return "J0.1"  # Start from beginning

    # Parse current group
    journey_id = get_journey_id(current)
    if not journey_id:
        return None

    # Get current group number
    match = re.match(r'J[\d]+B?\.(\d+)', current)
    if not match:
        return None

    current_num = int(match.group(1))
    total_in_journey = journey_totals.get(journey_id, 0)

    # If current group is completed, move to next
    if current in completed:
        if current_num < total_in_journey:
            return f"{journey_id}.{current_num + 1}"
        else:
            # Move to next journey
            journey_order = list(JOURNEY_FILES.keys())
            try:
                idx = journey_order.index(journey_id)
                if idx + 1 < len(journey_order):
                    next_journey = journey_order[idx + 1]
                    return f"{next_journey}.1"
            except ValueError:
                pass
            return None  # All done

    return current  # Current group not completed yet


def cmd_status(args):
    """Show current E2E testing position and progress."""
    state = load_json(E2E_STATE_FILE)
    config = load_json(E2E_CONFIG_FILE)

    if not state:
        print("E2E state not initialized")
        return 1

    current = state.get("current", "Not started")
    status = state.get("status", "unknown")
    session = state.get("session", 0)
    completed = state.get("completed", [])
    issues = state.get("issues", [])
    fixes = state.get("fixes", [])
    blockers = state.get("blockers", [])
    journey_totals = state.get("journey_totals", {})
    last_summary = state.get("last_summary", "")

    # Calculate totals
    total_groups = sum(journey_totals.values())
    total_completed = len(completed)

    # Get current journey info
    journey_id = get_journey_id(current) if current else None
    journey_name = JOURNEY_NAMES.get(journey_id, "Unknown") if journey_id else "Not started"

    print(f"\n{'='*60}")
    print("E2E TESTING STATUS")
    print(f"{'='*60}")
    print(f"Current Group:   {current}")
    print(f"Journey:         {journey_id} - {journey_name}" if journey_id else "Journey:         Not started")
    print(f"Status:          {status}")
    print(f"Session:         {session}")
    print(f"Overall:         {total_completed}/{total_groups} groups ({(total_completed/total_groups*100):.1f}%)" if total_groups else "Overall:         0/0 groups")

    print(f"\n{'-'*60}")
    print("JOURNEY PROGRESS:")
    print(f"{'-'*60}")

    for jid, total in journey_totals.items():
        j_completed = len([c for c in completed if c.startswith(f"{jid}.")])
        pct = (j_completed / total * 100) if total else 0
        bar_filled = int(pct / 10)
        bar = '#' * bar_filled + '.' * (10 - bar_filled)
        status_icon = "[x]" if j_completed == total else ("[ ]" if j_completed == 0 else "[~]")
        jname = JOURNEY_NAMES.get(jid, jid)
        print(f"  {status_icon} {jid}: [{bar}] {j_completed}/{total} - {jname}")

    print(f"\n{'-'*60}")
    print("STATS:")
    print(f"{'-'*60}")
    print(f"  Issues Found:  {len(issues)}")
    print(f"  Fixes Applied: {len(fixes)}")
    print(f"  Blockers:      {len(blockers)}")

    if blockers:
        print(f"\n  Active Blockers:")
        for b in blockers:
            print(f"    - {b}")

    if last_summary:
        print(f"\n{'-'*60}")
        print("LAST SESSION:")
        print(f"{'-'*60}")
        print(f"  {last_summary[:200]}{'...' if len(last_summary) > 200 else ''}")

    # Show next action
    print(f"\n{'-'*60}")
    print("NEXT ACTION:")
    print(f"{'-'*60}")

    if status == "awaiting_approval":
        print(f"  CEO approval required to continue to {current}")
        print(f"  Run: python tools/e2e.py next  (after approval)")
    elif blockers:
        print(f"  Resolve blockers before continuing")
    else:
        next_group = get_next_group(state)
        if next_group:
            print(f"  Run: python tools/e2e.py next")
            print(f"  This will show tasks for {next_group}")
        else:
            print(f"  All E2E testing complete!")

    print(f"\n{'='*60}\n")
    return 0


def cmd_next(args):
    """Show the next group's tasks with full context."""
    state = load_json(E2E_STATE_FILE)
    config = load_json(E2E_CONFIG_FILE)

    if not state:
        print("E2E state not initialized")
        return 1

    current = state.get("current")
    status = state.get("status", "unknown")
    completed = state.get("completed", [])
    session = state.get("session", 0)

    # Determine which group to show
    if current and current not in completed:
        group_id = current
    else:
        group_id = get_next_group(state)

    if not group_id:
        print("All E2E testing complete!")
        return 0

    journey_id = get_journey_id(group_id)
    if not journey_id:
        print(f"Invalid group ID: {group_id}")
        return 1

    journey_file = JOURNEY_FILES.get(journey_id)
    if not journey_file:
        print(f"Unknown journey: {journey_id}")
        return 1

    journey_path = BASE_DIR / journey_file
    group_data = parse_group_from_journey(journey_path, group_id)

    if not group_data:
        print(f"Could not find group {group_id} in {journey_file}")
        return 1

    # Build context output
    print(f"\n{'='*60}")
    print(f"E2E SESSION {session + 1} — {group_id} {group_data['title']}")
    print(f"{'='*60}")
    print(f"Journey:     {journey_id} - {JOURNEY_NAMES.get(journey_id, 'Unknown')}")
    print(f"Group:       {group_id} ({group_data['check_count']} checks)")
    print(f"Status:      {status}")
    if group_data['next_group']:
        print(f"After This:  {group_data['next_group']}")

    # Show relevant config
    print(f"\n{'-'*60}")
    print("CONFIG (from e2e_config.json):")
    print(f"{'-'*60}")

    test_user = config.get("test_user", {})
    test_recipients = config.get("test_recipients", {})
    api_endpoints = config.get("api_endpoints", {})

    print(f"  Test User:     {test_user.get('email', 'N/A')}")
    print(f"  Test Client:   {test_user.get('client_id', 'N/A')[:8]}..." if test_user.get('client_id') else "  Test Client:   N/A")
    print(f"  Recipient:     {test_recipients.get('email', 'N/A')}")
    print(f"  Backend API:   {api_endpoints.get('backend_api', 'N/A')}")
    print(f"  Frontend:      {api_endpoints.get('frontend', 'N/A')}")

    # Check approval gates
    gates = config.get("approval_gates", {})
    for gate_id, gate in gates.items():
        if gate.get("journey") == group_id and not gate.get("approved"):
            print(f"\n{'!'*60}")
            print(f"BLOCKED: {gate_id} - {gate.get('trigger')}")
            print(f"Cost: ${gate.get('cost_aud', 0)} AUD")
            print(f"CEO approval required before proceeding")
            print(f"{'!'*60}")

    # Show the group content
    print(f"\n{'-'*60}")
    print("TASKS THIS SESSION:")
    print(f"{'-'*60}")
    print(group_data['content'])

    # Show completion instructions
    print(f"\n{'-'*60}")
    print("ON COMPLETION:")
    print(f"{'-'*60}")
    print(f"  1. Execute all Part A (wiring) and Part B (live) checks")
    print(f"  2. Log any issues to docs/e2e/ISSUES_FOUND.md")
    print(f"  3. Log any fixes to docs/e2e/FIXES_APPLIED.md")
    print(f"  4. Run: python tools/e2e.py complete {group_id} --summary \"what was done\"")
    if group_data['next_group']:
        print(f"  5. Wait for CEO approval, then: python tools/e2e.py next")

    print(f"\n{'='*60}\n")
    return 0


def cmd_complete(args):
    """Mark a group as complete."""
    state = load_json(E2E_STATE_FILE)

    if not state:
        print("E2E state not initialized")
        return 1

    group_id = args.group_id
    summary = args.summary or "No summary provided"

    # Validate group_id format
    if not re.match(r'^J[\d]+B?\.[\d]+$', group_id):
        print(f"Invalid group ID format: {group_id}")
        print("Expected format: J0.1, J1.4, J2B.3, etc.")
        return 1

    completed = state.get("completed", [])

    # Check if already completed
    if group_id in completed:
        print(f"Group {group_id} is already marked complete")
        return 0

    # Update state
    completed.append(group_id)
    state["completed"] = completed
    state["session"] = state.get("session", 0) + 1
    state["last_run"] = datetime.now().isoformat()
    state["last_summary"] = summary
    state["status"] = "awaiting_approval"

    # Determine next group
    journey_id = get_journey_id(group_id)
    journey_totals = state.get("journey_totals", {})
    match = re.match(r'J[\d]+B?\.(\d+)', group_id)
    current_num = int(match.group(1)) if match else 0
    total_in_journey = journey_totals.get(journey_id, 0)

    if current_num < total_in_journey:
        next_group = f"{journey_id}.{current_num + 1}"
    else:
        # Move to next journey
        journey_order = list(JOURNEY_FILES.keys())
        try:
            idx = journey_order.index(journey_id)
            if idx + 1 < len(journey_order):
                next_journey = journey_order[idx + 1]
                next_group = f"{next_journey}.1"
            else:
                next_group = None
        except ValueError:
            next_group = None

    state["current"] = next_group if next_group else group_id

    # Save state
    save_json(E2E_STATE_FILE, state)

    # Log to session history
    log_to_history(group_id, "e2e_complete", summary)

    print(f"\n{'='*60}")
    print(f"COMPLETED: {group_id}")
    print(f"{'='*60}")
    print(f"Summary: {summary}")
    print(f"Session: {state['session']}")
    print(f"Total Completed: {len(completed)}")

    print(f"\n{'-'*60}")
    print("STATUS: awaiting_approval")
    print(f"{'-'*60}")
    if next_group:
        print(f"Next group: {next_group}")
        print(f"CEO approval required to continue")
        print(f"\nAfter approval, run: python tools/e2e.py next")
    else:
        print("All E2E testing complete!")

    print(f"\n{'='*60}\n")
    return 0


def cmd_config(args):
    """Show test configuration summary."""
    config = load_json(E2E_CONFIG_FILE)

    if not config:
        print("E2E config not found")
        return 1

    print(f"\n{'='*60}")
    print("E2E TEST CONFIGURATION")
    print(f"{'='*60}")

    # Test Agency
    agency = config.get("test_agency", {})
    print(f"\nTEST AGENCY:")
    print(f"  Name:     {agency.get('name', 'N/A')}")
    print(f"  Website:  {agency.get('website', 'N/A')}")
    print(f"  Industry: {agency.get('industry', 'N/A')}")
    print(f"  Tier:     {agency.get('tier', 'N/A')} (${agency.get('tier_price_aud', 0)}/mo)")

    # Test User
    user = config.get("test_user", {})
    print(f"\nTEST USER:")
    print(f"  Email:     {user.get('email', 'N/A')}")
    print(f"  Name:      {user.get('full_name', 'N/A')}")
    print(f"  User ID:   {user.get('user_id', 'N/A')[:8]}..." if user.get('user_id') else "  User ID:   N/A")
    print(f"  Client ID: {user.get('client_id', 'N/A')[:8]}..." if user.get('client_id') else "  Client ID: N/A")

    # Test Recipients
    recipients = config.get("test_recipients", {})
    print(f"\nTEST RECIPIENTS (all outreach goes here):")
    print(f"  Email:    {recipients.get('email', 'N/A')}")
    print(f"  SMS:      {recipients.get('sms', 'N/A')}")
    print(f"  Voice:    {recipients.get('voice', 'N/A')}")

    # API Endpoints
    endpoints = config.get("api_endpoints", {})
    print(f"\nAPI ENDPOINTS:")
    print(f"  Backend:  {endpoints.get('backend_api', 'N/A')}")
    print(f"  Frontend: {endpoints.get('frontend', 'N/A')}")
    print(f"  Supabase: {endpoints.get('supabase_url', 'N/A')}")
    print(f"  Prefect:  {endpoints.get('prefect_server', 'N/A')}")

    # Budget
    budget = config.get("budget", {})
    print(f"\nBUDGET:")
    print(f"  Total: ${budget.get('total_aud', 0)} AUD")
    breakdown = budget.get("breakdown", {})
    for item, details in breakdown.items():
        if isinstance(details, dict) and details.get("cost_aud", 0) > 0:
            print(f"    {item}: ${details['cost_aud']}")

    # Approval Gates
    gates = config.get("approval_gates", {})
    print(f"\nAPPROVAL GATES:")
    for gate_id, gate in gates.items():
        status = "[x]" if gate.get("approved") else "[ ]"
        print(f"  {status} {gate_id}: {gate.get('trigger', 'N/A')} (${gate.get('cost_aud', 0)})")

    # Limits
    limits = config.get("limits", {})
    print(f"\nTEST LIMITS:")
    print(f"  Leads to source: {limits.get('leads_to_source', 'N/A')}")
    print(f"  Leads to enrich: {limits.get('leads_to_enrich', 'N/A')}")
    print(f"  Emails/day:      {limits.get('emails_per_day', 'N/A')}")
    print(f"  SMS/day:         {limits.get('sms_per_day', 'N/A')}")
    print(f"  Voice calls:     {limits.get('voice_calls', 'N/A')}")
    print(f"  LinkedIn:        {limits.get('linkedin_requests', 'N/A')}")

    print(f"\n{'='*60}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Agency OS E2E Testing Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/e2e.py status              Show current position
  python tools/e2e.py next                Get next group's tasks
  python tools/e2e.py complete J1.4 -s "All checks passed"
  python tools/e2e.py config              Show test configuration
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status command
    status_parser = subparsers.add_parser("status", help="Show current E2E testing position")
    status_parser.set_defaults(func=cmd_status)

    # next command
    next_parser = subparsers.add_parser("next", help="Show next group's tasks with full context")
    next_parser.set_defaults(func=cmd_next)

    # complete command
    complete_parser = subparsers.add_parser("complete", help="Mark a group as complete")
    complete_parser.add_argument("group_id", help="Group ID to complete (e.g., J1.4)")
    complete_parser.add_argument("--summary", "-s", help="Completion summary")
    complete_parser.set_defaults(func=cmd_complete)

    # config command
    config_parser = subparsers.add_parser("config", help="Show test configuration summary")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
