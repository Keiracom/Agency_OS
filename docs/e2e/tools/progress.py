"""
Contract: docs/e2e/tools/progress.py
Purpose: E2E Task runner with debrief gate - manages task progression, completion, and knowledge capture
Layer: CLI tool
Commands: next, complete, force_complete, capture, status, history

Features:
- Reads task instructions from library/cookbook/j*_*.py
- Writes captured learnings to library/drafts/
- Logs to state/session_history.json on every complete
- Debrief gate blocks completion until capture or force
"""

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
LIBRARY_DIR = BASE_DIR / "library"
PROCESS_FILE = STATE_DIR / "process.json"
HISTORY_FILE = STATE_DIR / "session_history.json"
COOKBOOK_DIR = LIBRARY_DIR / "cookbook"
DRAFTS_DIR = LIBRARY_DIR / "drafts"


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


def load_skill(skill_file: str) -> Optional[dict]:
    """Load skill module from cookbook and extract CHECKS, PASS_CRITERIA, KEY_FILES."""
    skill_path = COOKBOOK_DIR / skill_file
    if not skill_path.exists():
        return None

    try:
        # Read and parse the skill file
        content = skill_path.read_text(encoding="utf-8")

        # Extract data by executing the module
        skill_data = {}
        exec_globals = {}
        exec(content, exec_globals)

        skill_data["checks"] = exec_globals.get("CHECKS", [])
        skill_data["pass_criteria"] = exec_globals.get("PASS_CRITERIA", [])
        skill_data["key_files"] = exec_globals.get("KEY_FILES", [])
        skill_data["docstring"] = exec_globals.get("__doc__", "")

        return skill_data
    except Exception as e:
        print(f"Warning: Could not parse skill {skill_file}: {e}")
        return None


def get_skill_file_for_task(task_id: str) -> str:
    """Generate skill filename from task ID (e.g., J0.1 -> j0_railway_health.py)."""
    # This will be populated from the process.json skill_file field
    return f"{task_id.lower().replace('.', '_')}.py"


def get_all_tasks(process_data: dict) -> list[dict]:
    """Extract all tasks from all phases, flattened and sorted."""
    tasks = []
    phases = process_data.get("phases", {})

    # Sort phases by key (J0, J1, J2, J2B, J3, etc.)
    def phase_sort_key(phase_id):
        # Handle J2B specially
        if phase_id == "J2B":
            return ("J2", "B")
        return (phase_id, "")

    sorted_phases = sorted(phases.items(), key=lambda x: phase_sort_key(x[0]))

    for phase_id, phase_data in sorted_phases:
        phase_tasks = phase_data.get("tasks", [])
        for task in phase_tasks:
            task["_phase_id"] = phase_id
            task["_phase_name"] = phase_data.get("name", phase_id)
            tasks.append(task)

    return tasks


def find_next_task(process_data: dict) -> Optional[dict]:
    """Find the next pending task."""
    completed = set(process_data.get("completed", []))
    tasks = get_all_tasks(process_data)

    for task in tasks:
        if task.get("id") not in completed and task.get("status") != "completed":
            return task
    return None


def find_task_by_id(process_data: dict, task_id: str) -> tuple[Optional[dict], Optional[str]]:
    """Find a task by its ID, return (task, phase_id)."""
    phases = process_data.get("phases", {})
    for phase_id, phase_data in phases.items():
        for task in phase_data.get("tasks", []):
            if task.get("id") == task_id:
                return task, phase_id
    return None, None


def log_completion(task_id: str, summary: str, drafts_created: list[str] = None, forced: bool = False):
    """Log task completion to session history."""
    history = load_json(HISTORY_FILE, default=[])
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": task_id,
        "action": "completed",
        "summary": summary,
        "forced": forced,
        "drafts_created": drafts_created or [],
    }
    history.append(entry)
    save_json(HISTORY_FILE, history)


def check_debrief_status(task_id: str) -> tuple[bool, list[str]]:
    """Check if debrief has been provided for current task (drafts created since task started)."""
    # Get recent drafts created
    drafts = []
    if DRAFTS_DIR.exists():
        for draft_file in DRAFTS_DIR.glob("*.py"):
            drafts.append(draft_file.stem)

    # For now, we'll track via a pending_debrief file
    pending_file = STATE_DIR / "pending_debrief.json"
    pending = load_json(pending_file, default={})

    task_drafts = pending.get(task_id, {}).get("drafts", [])
    has_debrief = len(task_drafts) > 0

    return has_debrief, task_drafts


def mark_task_pending_debrief(task_id: str):
    """Mark a task as awaiting debrief."""
    pending_file = STATE_DIR / "pending_debrief.json"
    pending = load_json(pending_file, default={})

    if task_id not in pending:
        pending[task_id] = {
            "started_at": datetime.now().isoformat(),
            "drafts": []
        }
        save_json(pending_file, pending)


def record_draft_for_task(task_id: str, draft_name: str):
    """Record that a draft was created for a task."""
    pending_file = STATE_DIR / "pending_debrief.json"
    pending = load_json(pending_file, default={})

    if task_id in pending:
        if draft_name not in pending[task_id]["drafts"]:
            pending[task_id]["drafts"].append(draft_name)
            save_json(pending_file, pending)


def clear_pending_debrief(task_id: str):
    """Clear pending debrief status after completion."""
    pending_file = STATE_DIR / "pending_debrief.json"
    pending = load_json(pending_file, default={})

    if task_id in pending:
        del pending[task_id]
        save_json(pending_file, pending)


def get_current_task_id(process_data: dict) -> Optional[str]:
    """Get the current task ID from process data or find next."""
    current = process_data.get("current_group")
    if current:
        return current

    next_task = find_next_task(process_data)
    return next_task.get("id") if next_task else None


def cmd_next(args):
    """Show the next pending task with full context from skill file."""
    process_data = load_json(PROCESS_FILE)

    if not process_data.get("phases"):
        print("No tasks loaded. Run process.json setup first.")
        return 1

    task = find_next_task(process_data)
    if not task:
        print("\n" + "=" * 60)
        print("ALL TASKS COMPLETED!")
        print("=" * 60 + "\n")
        return 0

    print(f"\n{'=' * 60}")
    print(f"NEXT TASK: {task.get('id', 'unknown')}")
    print(f"{'=' * 60}")
    print(f"Phase: {task.get('_phase_name', 'unknown')}")
    print(f"Title: {task.get('title', 'No title')}")
    print(f"Checks: {task.get('checks', 0)}")

    # Load skill file for detailed instructions
    skill_file = task.get("skill_file")
    if skill_file:
        skill_data = load_skill(skill_file)
        if skill_data:
            print(f"\n{'-' * 40}")
            print("SKILL INSTRUCTIONS:")
            print(f"{'-' * 40}")

            if skill_data.get("docstring"):
                print(f"\n{skill_data['docstring']}")

            if skill_data.get("checks"):
                print("\n### Checks:")
                for check in skill_data["checks"]:
                    print(f"\n**{check.get('id', 'N/A')}**")
                    print(f"  Part A: {check.get('part_a', 'N/A')}")
                    print(f"  Part B: {check.get('part_b', 'N/A')}")
                    if check.get("key_files"):
                        print(f"  Key Files: {', '.join(check['key_files'])}")

            if skill_data.get("pass_criteria"):
                print("\n### Pass Criteria:")
                for criterion in skill_data["pass_criteria"]:
                    print(f"- [ ] {criterion}")

            if skill_data.get("key_files"):
                print("\n### Key Files:")
                for file in skill_data["key_files"]:
                    print(f"  - {file}")
        else:
            print(f"\n  (Skill file not found: library/cookbook/{skill_file})")

    # Mark task as pending debrief
    mark_task_pending_debrief(task.get("id"))

    # Update current_group in process file
    process_data["current_group"] = task.get("id")
    save_json(PROCESS_FILE, process_data)

    print(f"\n{'=' * 60}")
    print("After completing, use one of:")
    print("  python progress.py capture <name> <description>  - Capture a learning")
    print("  python progress.py complete <task_id> --summary <summary>  - Complete with debrief")
    print("  python progress.py force_complete <task_id> --summary <summary>  - Skip debrief")
    print(f"{'=' * 60}\n")
    return 0


def cmd_complete(args):
    """Mark a task as complete. Requires debrief (capture) unless forced."""
    process_data = load_json(PROCESS_FILE)

    if not process_data.get("phases"):
        print("No tasks loaded")
        return 1

    task_id = args.task_id
    task, phase_id = find_task_by_id(process_data, task_id)

    if not task:
        print(f"Task not found: {task_id}")
        return 1

    # Check if already completed
    completed = process_data.get("completed", [])
    if task_id in completed:
        print(f"Task {task_id} is already completed")
        return 0

    # Check debrief status
    has_debrief, drafts = check_debrief_status(task_id)

    if not has_debrief and not args.summary:
        print(f"\n{'=' * 60}")
        print(f"DEBRIEF REQUIRED for {task_id}")
        print(f"{'=' * 60}")
        print("\nBefore completing, you must either:")
        print("  1. Capture a learning: python progress.py capture <name> <description>")
        print("  2. Force complete: python progress.py force_complete <task_id> --summary <why>")
        print("\nThis ensures we capture knowledge from every task.")
        print(f"{'=' * 60}\n")
        return 1

    # If no drafts but has summary, warn but allow
    if not has_debrief and args.summary:
        print(f"Warning: No drafts captured for {task_id}, but summary provided.")
        print("Consider using 'capture' for reusable learnings.\n")

    # Update task status
    task["status"] = "completed"
    task["completed_at"] = datetime.now().isoformat()
    if args.summary:
        task["completion_summary"] = args.summary
    task["drafts_created"] = drafts

    # Add to completed list
    if task_id not in completed:
        completed.append(task_id)
    process_data["completed"] = completed

    # Update tracking
    process_data["last_updated"] = datetime.now().isoformat()
    process_data["session"] = process_data.get("session", 1)

    # Find and set next task
    save_json(PROCESS_FILE, process_data)  # Save first so find_next_task works
    next_task = find_next_task(process_data)
    if next_task:
        process_data["current_group"] = next_task.get("id")
        process_data["current_phase"] = next_task.get("_phase_id", process_data.get("current_phase"))

    save_json(PROCESS_FILE, process_data)

    # Log to session history
    log_completion(task_id, args.summary or "No summary provided", drafts, forced=False)

    # Clear pending debrief
    clear_pending_debrief(task_id)

    print(f"Completed: {task_id}")
    if args.summary:
        print(f"Summary: {args.summary}")
    if drafts:
        print(f"Drafts captured: {', '.join(drafts)}")

    # Show next task hint
    if next_task:
        print(f"\nNext task: {next_task.get('id')} - {next_task.get('title')}")
    else:
        print("\nAll tasks completed!")

    return 0


def cmd_force_complete(args):
    """Force complete a task without debrief gate."""
    process_data = load_json(PROCESS_FILE)

    if not process_data.get("phases"):
        print("No tasks loaded")
        return 1

    task_id = args.task_id
    task, phase_id = find_task_by_id(process_data, task_id)

    if not task:
        print(f"Task not found: {task_id}")
        return 1

    # Check if already completed
    completed = process_data.get("completed", [])
    if task_id in completed:
        print(f"Task {task_id} is already completed")
        return 0

    if not args.summary:
        print("Error: --summary required for force_complete")
        print("Explain why no learning was captured.")
        return 1

    # Update task status
    task["status"] = "completed"
    task["completed_at"] = datetime.now().isoformat()
    task["completion_summary"] = args.summary
    task["forced"] = True
    task["drafts_created"] = []

    # Add to completed list
    if task_id not in completed:
        completed.append(task_id)
    process_data["completed"] = completed

    # Update tracking
    process_data["last_updated"] = datetime.now().isoformat()

    # Find and set next task
    save_json(PROCESS_FILE, process_data)
    next_task = find_next_task(process_data)
    if next_task:
        process_data["current_group"] = next_task.get("id")
        process_data["current_phase"] = next_task.get("_phase_id", process_data.get("current_phase"))

    save_json(PROCESS_FILE, process_data)

    # Log to session history
    log_completion(task_id, args.summary, [], forced=True)

    # Clear pending debrief
    clear_pending_debrief(task_id)

    print(f"Force completed: {task_id}")
    print(f"Reason: {args.summary}")

    if next_task:
        print(f"\nNext task: {next_task.get('id')} - {next_task.get('title')}")
    else:
        print("\nAll tasks completed!")

    return 0


def cmd_capture(args):
    """Capture a learning/pattern as a draft for later cookbook promotion."""
    name = args.name
    description = args.description

    # Validate name (alphanumeric + underscore)
    safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())

    # Create drafts directory if needed
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    # Create draft file
    draft_path = DRAFTS_DIR / f"{safe_name}.py"

    # Get current task for context
    process_data = load_json(PROCESS_FILE)
    current_task = get_current_task_id(process_data)

    draft_content = f'''"""
Draft: {safe_name}
Captured: {datetime.now().isoformat()}
Source Task: {current_task or 'Unknown'}
Status: draft (pending review for cookbook promotion)

Description:
{description}
"""

# Pattern/Learning Details
# ========================
#
# TODO: Add specific code patterns, commands, or procedures learned
#
# Example structure:
#
# PATTERN_NAME = "{safe_name}"
#
# STEPS = [
#     "Step 1: ...",
#     "Step 2: ...",
# ]
#
# KEY_COMMANDS = [
#     "command 1",
#     "command 2",
# ]
#
# GOTCHAS = [
#     "Watch out for...",
# ]
'''

    draft_path.write_text(draft_content, encoding="utf-8")

    # Record draft for current task
    if current_task:
        record_draft_for_task(current_task, safe_name)

    print(f"\nDraft captured: {draft_path}")
    print(f"Task: {current_task or 'Unknown'}")
    print(f"Description: {description[:100]}...")
    print("\nEdit the draft file to add specific patterns and procedures.")
    print("When ready to complete task, run: python progress.py complete <task_id>")

    return 0


def cmd_status(args):
    """Show progress overview with drafts waiting."""
    process_data = load_json(PROCESS_FILE)

    if not process_data.get("phases"):
        print("No tasks loaded")
        return 0

    print(f"\n{'=' * 60}")
    print("E2E TESTING PROGRESS")
    print(f"{'=' * 60}")
    print(f"Version: {process_data.get('version', 'unknown')}")
    print(f"Session: {process_data.get('session', 1)}")
    print(f"Current Phase: {process_data.get('current_phase', 'None')}")
    print(f"Current Group: {process_data.get('current_group', 'None')}")
    print(f"Last Updated: {process_data.get('last_updated', 'Never')}")

    total_tasks = 0
    completed_tasks = 0

    completed_list = process_data.get("completed", [])

    phases = process_data.get("phases", {})
    print(f"\n{'-' * 60}")
    print("PHASES:")
    print(f"{'-' * 60}")

    # Sort phases
    def phase_sort_key(phase_id):
        if phase_id == "J2B":
            return ("J2", "B")
        return (phase_id, "")

    sorted_phases = sorted(phases.items(), key=lambda x: phase_sort_key(x[0]))

    for phase_id, phase_data in sorted_phases:
        phase_name = phase_data.get("name", phase_id)
        tasks = phase_data.get("tasks", [])
        phase_completed = sum(1 for t in tasks if t.get("id") in completed_list)
        phase_total = len(tasks)

        total_tasks += phase_total
        completed_tasks += phase_completed

        status_icon = "[x]" if phase_completed == phase_total else "[ ]"
        print(f"  {status_icon} {phase_id}: {phase_name} ({phase_completed}/{phase_total})")

    print(f"\n{'-' * 60}")
    print("SUMMARY:")
    print(f"{'-' * 60}")
    print(f"  Total Tasks: {total_tasks}")
    print(f"  Completed: {completed_tasks}")
    print(f"  Remaining: {total_tasks - completed_tasks}")

    if total_tasks > 0:
        progress_pct = (completed_tasks / total_tasks) * 100
        print(f"  Progress: {progress_pct:.1f}%")

    # Show drafts waiting for review
    if DRAFTS_DIR.exists():
        drafts = list(DRAFTS_DIR.glob("*.py"))
        if drafts:
            print(f"\n{'-' * 60}")
            print(f"DRAFTS PENDING REVIEW: {len(drafts)}")
            print(f"{'-' * 60}")
            for draft in drafts[:5]:  # Show first 5
                print(f"  - {draft.stem}")
            if len(drafts) > 5:
                print(f"  ... and {len(drafts) - 5} more")

    # Show next task
    next_task = find_next_task(process_data)
    if next_task:
        print(f"\n{'-' * 60}")
        print(f"NEXT: {next_task.get('id')} - {next_task.get('title')}")

    print(f"\n{'=' * 60}\n")
    return 0


def cmd_history(args):
    """Show session history of completions."""
    history = load_json(HISTORY_FILE, default=[])

    if not history:
        print("No history yet.")
        return 0

    print(f"\n{'=' * 60}")
    print("SESSION HISTORY")
    print(f"{'=' * 60}")

    # Show recent entries (last 20)
    recent = history[-20:] if len(history) > 20 else history

    for entry in recent:
        timestamp = entry.get("timestamp", "Unknown")[:19]  # Trim microseconds
        task_id = entry.get("task_id", "Unknown")
        action = entry.get("action", "unknown")
        forced = " (FORCED)" if entry.get("forced") else ""
        drafts = entry.get("drafts_created", [])

        print(f"\n{timestamp}")
        print(f"  Task: {task_id} [{action}]{forced}")
        if entry.get("summary"):
            print(f"  Summary: {entry['summary'][:80]}...")
        if drafts:
            print(f"  Drafts: {', '.join(drafts)}")

    print(f"\n{'=' * 60}")
    print(f"Total completions: {len(history)}")
    print(f"{'=' * 60}\n")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="E2E Task Runner with Debrief Gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  next            Show next pending task with full instructions
  complete        Mark task complete (requires debrief or summary)
  force_complete  Mark task complete without debrief
  capture         Capture a learning/pattern as draft
  status          Show progress overview
  history         Show session history

Examples:
  python progress.py next
  python progress.py capture auth_callback_fix "Fixed the callback redirect issue"
  python progress.py complete J1.4 --summary "Callback working, drafted fix pattern"
  python progress.py force_complete J1.4 --summary "No new learnings, straightforward test"
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # next command
    next_parser = subparsers.add_parser("next", help="Show next pending task")
    next_parser.set_defaults(func=cmd_next)

    # complete command
    complete_parser = subparsers.add_parser("complete", help="Mark task as complete")
    complete_parser.add_argument("task_id", help="Task ID to complete")
    complete_parser.add_argument("--summary", "-s", help="Completion summary (required if no drafts)")
    complete_parser.set_defaults(func=cmd_complete)

    # force_complete command
    force_parser = subparsers.add_parser("force_complete", help="Force complete without debrief")
    force_parser.add_argument("task_id", help="Task ID to complete")
    force_parser.add_argument("--summary", "-s", required=True, help="Reason for skipping debrief")
    force_parser.set_defaults(func=cmd_force_complete)

    # capture command
    capture_parser = subparsers.add_parser("capture", help="Capture a learning as draft")
    capture_parser.add_argument("name", help="Name for the draft (alphanumeric)")
    capture_parser.add_argument("description", help="Description of what was learned")
    capture_parser.set_defaults(func=cmd_capture)

    # status command
    status_parser = subparsers.add_parser("status", help="Show progress overview")
    status_parser.set_defaults(func=cmd_status)

    # history command
    history_parser = subparsers.add_parser("history", help="Show session history")
    history_parser.set_defaults(func=cmd_history)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
