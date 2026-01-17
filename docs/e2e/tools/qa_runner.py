"""
Contract: docs/e2e/tools/qa_runner.py
Purpose: QA Agent - Verifies skill files after each journey is built
Layer: CLI tool
Commands: verify <journey>, verify_all, report

Features:
- Validates skill files exist for a journey
- Checks CHECKS list has all items
- Verifies PASS_CRITERIA populated
- Generates reports in agents/qa/reports/
"""

import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Paths relative to this file's location
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
LIBRARY_DIR = BASE_DIR / "library"
PROCESS_FILE = STATE_DIR / "process.json"
COOKBOOK_DIR = LIBRARY_DIR / "cookbook"
QA_REPORTS_DIR = BASE_DIR.parent.parent / "agents" / "qa" / "reports"


def load_json(filepath: Path, default=None):
    """Load JSON file, return default if missing."""
    if default is None:
        default = {}
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return default
    except (json.JSONDecodeError, IOError):
        return default


def load_skill_file(skill_file: str) -> dict:
    """Load and validate a skill file."""
    skill_path = COOKBOOK_DIR / skill_file
    result = {
        "exists": False,
        "has_checks": False,
        "has_pass_criteria": False,
        "has_key_files": False,
        "check_count": 0,
        "pass_criteria_count": 0,
        "errors": []
    }

    if not skill_path.exists():
        result["errors"].append(f"File not found: {skill_file}")
        return result

    result["exists"] = True

    try:
        content = skill_path.read_text(encoding="utf-8")
        exec_globals = {}
        exec(content, exec_globals)

        checks = exec_globals.get("CHECKS", [])
        pass_criteria = exec_globals.get("PASS_CRITERIA", [])
        key_files = exec_globals.get("KEY_FILES", [])

        if checks:
            result["has_checks"] = True
            result["check_count"] = len(checks)
            # Validate each check has required fields
            for i, check in enumerate(checks):
                if not check.get("id"):
                    result["errors"].append(f"Check {i} missing 'id'")
                if not check.get("part_a"):
                    result["errors"].append(f"Check {check.get('id', i)} missing 'part_a'")
                if not check.get("part_b"):
                    result["errors"].append(f"Check {check.get('id', i)} missing 'part_b'")
        else:
            result["errors"].append("No CHECKS defined")

        if pass_criteria:
            result["has_pass_criteria"] = True
            result["pass_criteria_count"] = len(pass_criteria)
        else:
            result["errors"].append("No PASS_CRITERIA defined")

        result["has_key_files"] = bool(key_files)

    except Exception as e:
        result["errors"].append(f"Parse error: {str(e)}")

    return result


def verify_journey(journey_id: str, verbose: bool = True) -> dict:
    """Verify all skill files for a journey."""
    process_data = load_json(PROCESS_FILE)

    if not process_data.get("phases"):
        return {"error": "process.json not loaded", "passed": False}

    phases = process_data.get("phases", {})
    if journey_id not in phases:
        return {"error": f"Journey {journey_id} not found", "passed": False}

    phase = phases[journey_id]
    tasks = phase.get("tasks", [])

    results = {
        "journey_id": journey_id,
        "journey_name": phase.get("name", journey_id),
        "expected_tasks": len(tasks),
        "verified_tasks": 0,
        "passed_tasks": 0,
        "failed_tasks": 0,
        "total_checks": 0,
        "tasks": [],
        "errors": [],
        "passed": True,
        "timestamp": datetime.now().isoformat()
    }

    for task in tasks:
        skill_file = task.get("skill_file")
        task_id = task.get("id")
        expected_checks = task.get("checks", 0)

        if not skill_file:
            results["errors"].append(f"Task {task_id} missing skill_file")
            results["failed_tasks"] += 1
            results["passed"] = False
            continue

        skill_result = load_skill_file(skill_file)
        results["verified_tasks"] += 1

        task_result = {
            "id": task_id,
            "title": task.get("title"),
            "skill_file": skill_file,
            "expected_checks": expected_checks,
            "actual_checks": skill_result["check_count"],
            "passed": skill_result["exists"] and skill_result["has_checks"] and not skill_result["errors"],
            "errors": skill_result["errors"]
        }

        results["tasks"].append(task_result)
        results["total_checks"] += skill_result["check_count"]

        if task_result["passed"]:
            results["passed_tasks"] += 1
        else:
            results["failed_tasks"] += 1
            results["passed"] = False

    if verbose:
        print_journey_report(results)

    return results


def print_journey_report(results: dict):
    """Print a journey verification report."""
    print(f"\n{'=' * 60}")
    print(f"QA REPORT: {results['journey_id']} - {results['journey_name']}")
    print(f"{'=' * 60}")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Expected Tasks: {results['expected_tasks']}")
    print(f"Verified Tasks: {results['verified_tasks']}")
    print(f"Passed: {results['passed_tasks']}")
    print(f"Failed: {results['failed_tasks']}")
    print(f"Total Checks: {results['total_checks']}")
    print(f"\nOverall: {'PASSED' if results['passed'] else 'FAILED'}")

    if results["errors"]:
        print(f"\n{'-' * 60}")
        print("JOURNEY-LEVEL ERRORS:")
        for error in results["errors"]:
            print(f"  - {error}")

    failed_tasks = [t for t in results["tasks"] if not t["passed"]]
    if failed_tasks:
        print(f"\n{'-' * 60}")
        print("FAILED TASKS:")
        for task in failed_tasks:
            print(f"\n  {task['id']}: {task['title']}")
            print(f"    File: {task['skill_file']}")
            for error in task["errors"]:
                print(f"    - {error}")

    passed_tasks = [t for t in results["tasks"] if t["passed"]]
    if passed_tasks:
        print(f"\n{'-' * 60}")
        print(f"PASSED TASKS: {len(passed_tasks)}/{len(results['tasks'])}")
        for task in passed_tasks:
            print(f"  [OK] {task['id']}: {task['title']} ({task['actual_checks']} checks)")

    print(f"\n{'=' * 60}\n")


def save_report(results: dict, journey_id: str):
    """Save QA report to file."""
    QA_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    report_file = QA_REPORTS_DIR / f"qa_{journey_id}_{timestamp}.json"

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Report saved: {report_file}")
    return report_file


def cmd_verify(args):
    """Verify a single journey."""
    journey_id = args.journey.upper()
    results = verify_journey(journey_id, verbose=True)

    if args.save:
        save_report(results, journey_id)

    return 0 if results.get("passed") else 1


def cmd_verify_all(args):
    """Verify all journeys."""
    process_data = load_json(PROCESS_FILE)
    phases = process_data.get("phases", {})

    all_passed = True
    summary = []

    for journey_id in sorted(phases.keys(), key=lambda x: (x.replace("J2B", "J2Z"))):
        results = verify_journey(journey_id, verbose=False)
        summary.append({
            "journey": journey_id,
            "name": results.get("journey_name", ""),
            "passed": results.get("passed", False),
            "tasks": f"{results.get('passed_tasks', 0)}/{results.get('expected_tasks', 0)}",
            "checks": results.get("total_checks", 0)
        })
        if not results.get("passed"):
            all_passed = False

    print(f"\n{'=' * 60}")
    print("QA SUMMARY - ALL JOURNEYS")
    print(f"{'=' * 60}")

    for item in summary:
        status = "[PASS]" if item["passed"] else "[FAIL]"
        print(f"  {status} {item['journey']}: {item['name']} ({item['tasks']} tasks, {item['checks']} checks)")

    print(f"\n{'=' * 60}")
    print(f"OVERALL: {'ALL PASSED' if all_passed else 'SOME FAILURES'}")
    print(f"{'=' * 60}\n")

    return 0 if all_passed else 1


def main():
    parser = argparse.ArgumentParser(
        description="QA Agent - Verify E2E skill files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  verify <journey>   Verify a single journey (e.g., J0, J1, J2B)
  verify_all         Verify all journeys

Examples:
  python qa_runner.py verify J0
  python qa_runner.py verify J1 --save
  python qa_runner.py verify_all
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a single journey")
    verify_parser.add_argument("journey", help="Journey ID (e.g., J0, J1, J2B)")
    verify_parser.add_argument("--save", action="store_true", help="Save report to file")
    verify_parser.set_defaults(func=cmd_verify)

    # verify_all command
    verify_all_parser = subparsers.add_parser("verify_all", help="Verify all journeys")
    verify_all_parser.set_defaults(func=cmd_verify_all)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
