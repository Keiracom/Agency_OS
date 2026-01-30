"""
Action Engine Prefect Flow
==========================
Runs after daily scrape to process new high-value knowledge.
Can also be triggered manually.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from prefect import flow, task, get_run_logger

# Add infrastructure to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from infrastructure.action_engine import (
    process_new_knowledge,
    get_high_value_knowledge,
    get_pending_signoffs,
    complete_action,
    RELEVANCE_THRESHOLD,
)
from infrastructure.task_tracker import (
    get_pending_tasks,
    heartbeat_check,
    check_task_status,
)


@task(name="scan-high-value-knowledge")
def scan_knowledge_task() -> dict:
    """
    Scan for high-value knowledge items.
    
    Returns count and summary of actionable knowledge.
    """
    logger = get_run_logger()
    
    knowledge_items = get_high_value_knowledge(threshold=RELEVANCE_THRESHOLD, limit=20)
    
    logger.info(f"Found {len(knowledge_items)} high-value knowledge items (score >= {RELEVANCE_THRESHOLD})")
    
    summary = {
        "count": len(knowledge_items),
        "by_category": {},
        "items": [],
    }
    
    for item in knowledge_items:
        # Count by category
        category = item.category or "unknown"
        summary["by_category"][category] = summary["by_category"].get(category, 0) + 1
        
        # Add item summary
        summary["items"].append({
            "id": item.id,
            "title": item.title[:80],
            "category": category,
            "score": item.relevance_score,
        })
    
    return summary


@task(name="process-knowledge")
def process_knowledge_task() -> dict:
    """
    Process high-value knowledge and create sign-off requests.
    """
    logger = get_run_logger()
    
    result = process_new_knowledge()
    
    logger.info(f"Processed {result['processed']} knowledge items")
    logger.info(f"Created {len(result['signoffs_created'])} sign-off requests")
    
    if result["skipped"]:
        logger.info(f"Skipped {len(result['skipped'])} items")
        for skip in result["skipped"]:
            logger.debug(f"  - {skip['title'][:50]}: {skip['reason']}")
    
    if result["errors"]:
        logger.warning(f"Errors: {len(result['errors'])}")
        for error in result["errors"]:
            logger.warning(f"  - {error['title'][:50]}: {error['error']}")
    
    return result


@task(name="check-executing-actions")
def check_executing_actions_task() -> dict:
    """
    Check on currently executing actions (spawned agents).
    
    Uses task_tracker heartbeat to detect stuck/failed agents.
    """
    logger = get_run_logger()
    
    # Run task tracker heartbeat
    heartbeat_result = heartbeat_check()
    
    logger.info(f"Pending tasks: {heartbeat_result['pending_count']}")
    logger.info(f"Stuck tasks: {heartbeat_result['stuck_count']}")
    
    if heartbeat_result["retried"]:
        logger.info(f"Retried {len(heartbeat_result['retried'])} failed tasks")
    
    if heartbeat_result["failed"]:
        logger.warning(f"Permanently failed: {len(heartbeat_result['failed'])} tasks")
    
    for alert in heartbeat_result.get("alerts", []):
        logger.warning(alert)
    
    return heartbeat_result


@task(name="summarize-pending")
def summarize_pending_task() -> dict:
    """
    Summarize pending sign-off requests.
    """
    logger = get_run_logger()
    
    pending = get_pending_signoffs()
    
    summary = {
        "pending_count": len(pending),
        "by_action": {},
        "oldest": None,
    }
    
    for signoff in pending:
        action = signoff.action_type
        summary["by_action"][action] = summary["by_action"].get(action, 0) + 1
    
    if pending:
        oldest = pending[-1]  # Already sorted by created_at desc
        summary["oldest"] = {
            "id": oldest.id,
            "title": oldest.title[:50],
            "created_at": oldest.created_at,
        }
    
    logger.info(f"Pending sign-offs: {len(pending)}")
    for action, count in summary["by_action"].items():
        logger.info(f"  - {action}: {count}")
    
    return summary


@flow(name="action-engine-flow")
def action_engine_flow(
    process: bool = True,
    check_executing: bool = True,
) -> dict:
    """
    Main Action Engine flow.
    
    Runs after daily scrape to:
    1. Scan for high-value knowledge
    2. Create sign-off requests
    3. Check on executing agents
    4. Summarize pending items
    
    Args:
        process: Whether to process new knowledge (default: True)
        check_executing: Whether to check executing actions (default: True)
        
    Returns:
        Flow execution summary
    """
    logger = get_run_logger()
    
    logger.info("=" * 50)
    logger.info("Action Engine Flow Started")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 50)
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scan": None,
        "process": None,
        "executing": None,
        "pending": None,
    }
    
    # Step 1: Scan for high-value knowledge
    scan_result = scan_knowledge_task()
    results["scan"] = scan_result
    
    # Step 2: Process knowledge (create sign-offs)
    if process and scan_result["count"] > 0:
        process_result = process_knowledge_task()
        results["process"] = process_result
    else:
        logger.info("Skipping processing (no new knowledge or disabled)")
    
    # Step 3: Check executing actions
    if check_executing:
        executing_result = check_executing_actions_task()
        results["executing"] = executing_result
    
    # Step 4: Summarize pending
    pending_result = summarize_pending_task()
    results["pending"] = pending_result
    
    # Final summary
    logger.info("=" * 50)
    logger.info("Action Engine Flow Complete")
    logger.info(f"Knowledge scanned: {scan_result['count']}")
    if results["process"]:
        logger.info(f"Sign-offs created: {results['process']['processed']}")
    logger.info(f"Pending approvals: {pending_result['pending_count']}")
    logger.info("=" * 50)
    
    return results


@flow(name="action-engine-scan-only")
def scan_only_flow() -> dict:
    """
    Lightweight scan flow - just check for knowledge, don't process.
    
    Useful for monitoring without creating sign-offs.
    """
    logger = get_run_logger()
    
    scan_result = scan_knowledge_task()
    pending_result = summarize_pending_task()
    
    return {
        "scan": scan_result,
        "pending": pending_result,
    }


@flow(name="action-engine-health-check")
def health_check_flow() -> dict:
    """
    Health check flow - check on executing tasks and cleanup.
    
    Run periodically to ensure no stuck agents.
    """
    logger = get_run_logger()
    
    executing_result = check_executing_actions_task()
    pending_result = summarize_pending_task()
    
    return {
        "executing": executing_result,
        "pending": pending_result,
        "healthy": executing_result["stuck_count"] == 0 and len(executing_result.get("alerts", [])) == 0,
    }


# ============================================
# CLI Entry Point
# ============================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Action Engine Flow")
    parser.add_argument(
        "command",
        choices=["run", "scan", "health"],
        default="run",
        nargs="?",
        help="Flow to run (run=full, scan=check only, health=monitor tasks)"
    )
    parser.add_argument(
        "--no-process",
        action="store_true",
        help="Skip processing (scan only)"
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Skip checking executing actions"
    )
    
    args = parser.parse_args()
    
    if args.command == "scan":
        result = scan_only_flow()
    elif args.command == "health":
        result = health_check_flow()
    else:
        result = action_engine_flow(
            process=not args.no_process,
            check_executing=not args.no_check,
        )
    
    import json
    print(json.dumps(result, indent=2, default=str))
