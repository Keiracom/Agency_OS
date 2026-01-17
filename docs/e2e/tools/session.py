"""
Contract: tools/session.py
Purpose: Session history manager for Agency OS
Layer: CLI tool
Commands: log, history
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
HISTORY_FILE = STATE_DIR / "session_history.json"


def load_history() -> list:
    """Load session history, return empty list if missing."""
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load history: {e}")
        return []


def save_history(history: list):
    """Save session history to file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)


def cmd_log(args):
    """Log an entry to session history."""
    history = load_history()

    entry = {
        "timestamp": datetime.now().isoformat(),
        "task_id": args.task_id,
        "action": args.action,
        "summary": args.summary,
    }

    if args.duration:
        entry["duration_minutes"] = args.duration

    history.append(entry)
    save_history(history)

    print(f"Logged: [{args.action}] {args.task_id}")
    if args.summary:
        print(f"Summary: {args.summary}")

    return 0


def cmd_history(args):
    """Show session history."""
    history = load_history()

    if not history:
        print("No session history")
        return 0

    # Apply --last filter
    if args.last and args.last > 0:
        history = history[-args.last:]

    print(f"\n{'='*60}")
    print("SESSION HISTORY")
    print(f"{'='*60}")
    print(f"Showing {len(history)} entries")
    print(f"{'─'*60}\n")

    for entry in history:
        timestamp = entry.get("timestamp", "unknown")
        task_id = entry.get("task_id", "unknown")
        action = entry.get("action", "unknown")
        summary = entry.get("summary", "")
        duration = entry.get("duration_minutes")

        # Format timestamp for display
        try:
            dt = datetime.fromisoformat(timestamp)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            time_str = timestamp

        print(f"[{time_str}] {action.upper()}: {task_id}")
        if summary:
            print(f"  {summary}")
        if duration:
            print(f"  Duration: {duration} min")
        print()

    print(f"{'='*60}\n")
    return 0


def cmd_clear(args):
    """Clear session history."""
    if args.confirm:
        save_history([])
        print("Session history cleared")
        return 0
    else:
        print("Use --confirm to clear session history")
        return 1


def cmd_export(args):
    """Export session history to a file."""
    history = load_history()

    if not history:
        print("No session history to export")
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)

    print(f"Exported {len(history)} entries to {output_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Agency OS Session History Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # log command
    log_parser = subparsers.add_parser("log", help="Log an entry")
    log_parser.add_argument("task_id", help="Task ID")
    log_parser.add_argument("action", help="Action performed (e.g., started, completed, blocked)")
    log_parser.add_argument("summary", help="Summary of what was done")
    log_parser.add_argument("--duration", "-d", type=int, help="Duration in minutes")
    log_parser.set_defaults(func=cmd_log)

    # history command
    history_parser = subparsers.add_parser("history", help="Show session history")
    history_parser.add_argument("--last", "-n", type=int, help="Show last N entries")
    history_parser.set_defaults(func=cmd_history)

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear session history")
    clear_parser.add_argument("--confirm", action="store_true", help="Confirm clearing")
    clear_parser.set_defaults(func=cmd_clear)

    # export command
    export_parser = subparsers.add_parser("export", help="Export history to file")
    export_parser.add_argument("output", help="Output file path")
    export_parser.set_defaults(func=cmd_export)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
