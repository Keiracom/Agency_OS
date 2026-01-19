#!/usr/bin/env python3
"""
SDK Implementation Progress Tracker

Usage:
    python progress.py status          Show current progress
    python progress.py next            Show next task with details
    python progress.py complete <id>   Mark task as completed
    python progress.py phase <id>      Show phase details
    python progress.py costs           Show cost tracking
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROGRESS_FILE = Path(__file__).parent / "progress.json"


def load_progress() -> dict:
    """Load progress from JSON file."""
    with open(PROGRESS_FILE) as f:
        return json.load(f)


def save_progress(data: dict) -> None:
    """Save progress to JSON file."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def cmd_status(data: dict) -> None:
    """Show current progress status."""
    print("\n" + "=" * 60)
    print("  SDK IMPLEMENTATION PROGRESS")
    print("=" * 60)
    print(f"\n  Status: {data['status'].upper()}")
    print(f"  Current Phase: {data['current_phase']}")
    print(f"  Current Task: {data['current_task']}")
    print(f"  Approved: {data['approved_date']}")

    # Count tasks
    total_tasks = 0
    completed_tasks = len(data['completed'])
    for phase in data['phases'].values():
        total_tasks += len(phase['tasks'])

    pct = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    print(f"\n  Progress: {completed_tasks}/{total_tasks} tasks ({pct:.0f}%)")

    # Progress bar (ASCII for Windows compatibility)
    bar_width = 40
    filled = int(bar_width * pct / 100)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(f"  [{bar}]")

    # Phase summary
    print("\n  PHASES:")
    print("  " + "-" * 56)
    for pid, phase in data['phases'].items():
        phase_completed = sum(1 for t in phase['tasks'] if t['status'] == 'completed')
        phase_total = len(phase['tasks'])
        status_icon = "[x]" if phase['status'] == 'completed' else "[ ]" if phase['status'] == 'pending' else "[>]"
        print(f"  {status_icon} {pid}: {phase['name']:<25} [{phase_completed}/{phase_total}]")

    print("\n" + "=" * 60 + "\n")


def cmd_next(data: dict) -> None:
    """Show next task to work on."""
    current_task_id = data['current_task']

    # Find the task
    for phase in data['phases'].values():
        for task in phase['tasks']:
            if task['id'] == current_task_id:
                print("\n" + "=" * 60)
                print(f"  NEXT TASK: {task['id']}")
                print("=" * 60)
                print(f"\n  Title: {task['title']}")
                print(f"  Phase: {phase['name']}")
                print(f"  Status: {task['status']}")

                if task.get('target_file'):
                    print(f"\n  Target: {task['target_file']}")
                if task.get('source_file'):
                    print(f"  Source: {task['source_file']}")

                print("\n  CHECKS:")
                for i, check in enumerate(task.get('checks', []), 1):
                    print(f"    {i}. [ ] {check}")

                print("\n  COMMANDS:")
                print(f"    python progress.py complete {task['id']}  # When done")
                print("\n" + "=" * 60 + "\n")
                return

    print(f"\nTask {current_task_id} not found.\n")


def cmd_complete(data: dict, task_id: str) -> None:
    """Mark a task as completed."""
    # Find and update the task
    for pid, phase in data['phases'].items():
        for task in phase['tasks']:
            if task['id'] == task_id:
                if task['status'] == 'completed':
                    print(f"\nTask {task_id} is already completed.\n")
                    return

                # Mark completed
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                data['completed'].append(task_id)

                # Find next task
                next_task = find_next_task(data)
                if next_task:
                    data['current_task'] = next_task['id']
                    data['current_phase'] = next_task['phase_id']

                    # Update phase status if needed
                    update_phase_status(data)

                save_progress(data)

                print(f"\n[DONE] Completed: {task_id} - {task['title']}")
                if next_task:
                    print(f"  Next: {next_task['id']} - {next_task['title']}")
                else:
                    print("  ALL TASKS COMPLETED!")
                print()
                return

    print(f"\nTask {task_id} not found.\n")


def find_next_task(data: dict) -> dict | None:
    """Find the next pending task."""
    for pid, phase in data['phases'].items():
        for task in phase['tasks']:
            if task['status'] == 'pending':
                return {'id': task['id'], 'title': task['title'], 'phase_id': pid}
    return None


def update_phase_status(data: dict) -> None:
    """Update phase statuses based on task completion."""
    for pid, phase in data['phases'].items():
        all_completed = all(t['status'] == 'completed' for t in phase['tasks'])
        any_completed = any(t['status'] == 'completed' for t in phase['tasks'])

        if all_completed:
            phase['status'] = 'completed'
        elif any_completed:
            phase['status'] = 'in_progress'
        else:
            phase['status'] = 'pending'


def cmd_phase(data: dict, phase_id: str) -> None:
    """Show details for a specific phase."""
    phase_id = phase_id.upper()

    if phase_id not in data['phases']:
        print(f"\nPhase {phase_id} not found. Available: {', '.join(data['phases'].keys())}\n")
        return

    phase = data['phases'][phase_id]

    print("\n" + "=" * 60)
    print(f"  PHASE {phase_id}: {phase['name']}")
    print("=" * 60)
    print(f"\n  {phase['description']}")
    print(f"  Status: {phase['status']}")

    print("\n  TASKS:")
    print("  " + "-" * 56)
    for task in phase['tasks']:
        icon = "[x]" if task['status'] == 'completed' else "[ ]"
        print(f"  {icon} {task['id']}: {task['title']}")
        if task.get('target_file'):
            print(f"       -> {task['target_file']}")

    print("\n" + "=" * 60 + "\n")


def cmd_costs(data: dict) -> None:
    """Show cost tracking."""
    costs = data.get('cost_tracking', {})

    print("\n" + "=" * 60)
    print("  SDK COST TRACKING")
    print("=" * 60)
    print(f"\n  Estimated Dev Hours: {costs.get('estimated_total_dev_hours', 'N/A')}")
    print(f"  Actual Hours: {costs.get('actual_hours', 0)}")
    print(f"  API Costs During Dev: ${costs.get('api_costs_during_dev', 0):.2f} AUD")

    print("\n  PER-AGENT COST LIMITS (from sdk_config.json):")
    print("  " + "-" * 56)
    print("    ICP Extraction:  $1.00 / 12 turns / 180s timeout")
    print("    Enrichment:      $1.50 / 10 turns / 120s timeout")
    print("    Email:           $0.50 /  5 turns /  60s timeout")
    print("    Voice KB:        $2.00 / 15 turns / 180s timeout")
    print("    Objection:       $0.50 /  5 turns /  60s timeout")

    print("\n" + "=" * 60 + "\n")


def cmd_note(data: dict, note: str) -> None:
    """Add a note to the progress file."""
    timestamp = datetime.now().strftime("%Y-%m-%d")
    data['notes'].append(f"{timestamp}: {note}")
    save_progress(data)
    print(f"\n[DONE] Note added: {note}\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    data = load_progress()

    if cmd == "status":
        cmd_status(data)
    elif cmd == "next":
        cmd_next(data)
    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("\nUsage: python progress.py complete <task_id>\n")
            return
        cmd_complete(data, sys.argv[2].upper())
    elif cmd == "phase":
        if len(sys.argv) < 3:
            print("\nUsage: python progress.py phase <phase_id>\n")
            return
        cmd_phase(data, sys.argv[2])
    elif cmd == "costs":
        cmd_costs(data)
    elif cmd == "note":
        if len(sys.argv) < 3:
            print("\nUsage: python progress.py note \"Your note here\"\n")
            return
        cmd_note(data, " ".join(sys.argv[2:]))
    else:
        print(f"\nUnknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
