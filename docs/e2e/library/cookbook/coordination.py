"""
Agent Pipeline Coordination Skill for Agency OS

The Agency OS development pipeline uses three specialized Claude Code agents
working in parallel. Each agent has a specific role and communicates through files.

Version: 2.0
Author: CTO (Claude)
Created: December 24, 2025

Pipeline Architecture:
    BUILDER (Terminal 1) -> Creates new files, completes stubs, updates PROGRESS.md
    QA (Terminal 2) -> Scans for issues, categorizes issues, routes to handler
    FIXER (Terminal 3) -> Fixes violations, documents fixes, skips MISSING

Communication Flow:
    - Agents communicate ONLY through files
    - No direct communication between agents
    - Each agent reads/writes specific locations
"""

from typing import Dict, List


def get_instructions() -> str:
    """Return the key instructions for pipeline coordination."""
    return """
AGENT PIPELINE COORDINATION
===========================

1. AGENT RESPONSIBILITIES:
   - Builder: Create production code (reads PROGRESS.md, writes src/, frontend/)
   - QA: Detect issues, route correctly (reads src/, writes qa_reports/, builder_tasks/)
   - Fixer: Fix violations only (reads qa_reports/, writes src/, fixer_reports/)

2. ISSUE ROUTING (Critical Concept):
   QA categorizes, then routes to the correct handler:

   MISSING     -> builder_tasks/ -> BUILDER creates
   INCOMPLETE  -> builder_tasks/ -> BUILDER completes
   CRITICAL    -> qa_reports/    -> FIXER fixes
   HIGH        -> qa_reports/    -> FIXER fixes
   MEDIUM      -> qa_reports/    -> (logged only)
   LOW         -> qa_reports/    -> (logged only)

3. TIMING STRATEGY:
   - Builder: On demand (human-driven)
   - QA: Every 90 seconds (fast detection)
   - Fixer: Every 2 minutes (time to fix + QA can verify)

4. SUCCESS CRITERIA:
   Pipeline is complete when QA reports:
   - MISSING files: 0
   - INCOMPLETE files: 0
   - CRITICAL issues: 0
   - HIGH issues: 0
   - Fixes verified: 100%

5. CONFLICT RESOLUTION:
   - Fixer makes surgical fixes with '# FIXED by fixer-agent' markers
   - Builder works around markers, doesn't remove them
   - If conflict, Fixer's fix takes priority
   - After 3 failed attempts, escalate to needs_human.md
"""


def get_code_templates() -> Dict[str, str]:
    """Return code templates for coordination."""
    return {
        "monitoring_commands": MONITORING_COMMANDS,
        "file_structure": FILE_STRUCTURE,
    }


def get_agent_config() -> Dict[str, Dict]:
    """Return configuration for each agent."""
    return {
        "builder": {
            "primary_job": "Create production code",
            "reads": ["PROGRESS.md", "builder_tasks/", "skills/"],
            "writes": ["src/", "frontend/", "PROGRESS.md"],
            "cycle": "On demand",
        },
        "qa": {
            "primary_job": "Detect issues, route correctly",
            "reads": ["src/", "frontend/", "PROGRESS.md", "fixer_reports/"],
            "writes": ["qa_reports/", "builder_tasks/"],
            "cycle": "90 seconds",
        },
        "fixer": {
            "primary_job": "Fix violations only",
            "reads": ["qa_reports/", "PROGRESS.md", "skills/"],
            "writes": ["src/", "frontend/", "fixer_reports/"],
            "cycle": "2 minutes",
        },
    }


def get_issue_routing() -> Dict[str, Dict[str, str]]:
    """Return issue routing configuration."""
    return {
        "MISSING": {"handler": "Builder", "written_to": "builder_tasks/pending.md"},
        "INCOMPLETE": {"handler": "Builder", "written_to": "builder_tasks/pending.md"},
        "CRITICAL": {"handler": "Fixer", "written_to": "qa_reports/report_*.md"},
        "HIGH": {"handler": "Fixer", "written_to": "qa_reports/report_*.md"},
        "MEDIUM": {"handler": "(logged)", "written_to": "qa_reports/report_*.md"},
        "LOW": {"handler": "(logged)", "written_to": "qa_reports/report_*.md"},
    }


def get_communication_protocol() -> List[Dict[str, str]]:
    """Return the communication protocol between agents."""
    return [
        {"from": "Builder", "to": "QA", "via": "src/, frontend/", "content": "Code to scan"},
        {"from": "QA", "to": "Builder", "via": "builder_tasks/pending.md", "content": "Missing/incomplete files"},
        {"from": "QA", "to": "Fixer", "via": "qa_reports/report_*.md", "content": "Violations to fix"},
        {"from": "Fixer", "to": "QA", "via": "fixer_reports/fixes_*.md", "content": "Fixes to verify"},
        {"from": "Fixer", "to": "codebase", "via": "src/, frontend/", "content": "Fixed code"},
    ]


def get_conflict_resolution() -> Dict[str, str]:
    """Return conflict resolution strategies."""
    return {
        "same_file_edit": "Fixer makes surgical fixes with markers; Builder works around them",
        "qa_reports_fixed_issue": "QA's next cycle (90 seconds) will see new code; auto-resolves",
        "fixer_breaks_something": "QA's next scan catches regression; reports as REGRESSION",
        "issue_keeps_reopening": "After 3 failed attempts, Fixer escalates to needs_human.md",
    }


def check_pipeline_status(
    missing_count: int,
    incomplete_count: int,
    critical_count: int,
    high_count: int,
    fixes_verified_pct: float
) -> Dict[str, any]:
    """
    Check if the pipeline is complete.

    Args:
        missing_count: Number of missing files
        incomplete_count: Number of incomplete files
        critical_count: Number of critical issues
        high_count: Number of high issues
        fixes_verified_pct: Percentage of fixes verified

    Returns:
        Status dictionary with is_complete flag and details
    """
    is_complete = (
        missing_count == 0 and
        incomplete_count == 0 and
        critical_count == 0 and
        high_count == 0 and
        fixes_verified_pct >= 100.0
    )

    return {
        "is_complete": is_complete,
        "missing_files": missing_count,
        "incomplete_files": incomplete_count,
        "critical_issues": critical_count,
        "high_issues": high_count,
        "fixes_verified": fixes_verified_pct,
        "blockers": [] if is_complete else _get_blockers(
            missing_count, incomplete_count, critical_count, high_count, fixes_verified_pct
        ),
    }


def _get_blockers(missing: int, incomplete: int, critical: int, high: int, verified: float) -> List[str]:
    """Get list of blockers preventing pipeline completion."""
    blockers = []
    if missing > 0:
        blockers.append(f"{missing} missing files (Builder required)")
    if incomplete > 0:
        blockers.append(f"{incomplete} incomplete files (Builder required)")
    if critical > 0:
        blockers.append(f"{critical} critical issues (Fixer required)")
    if high > 0:
        blockers.append(f"{high} high issues (Fixer required)")
    if verified < 100.0:
        blockers.append(f"Only {verified}% fixes verified (need 100%)")
    return blockers


# =============================================================================
# TEMPLATES
# =============================================================================

MONITORING_COMMANDS = """
# Check Builder tasks
cat "Agents/Builder Agent/builder_tasks/pending.md"

# Check QA status
cat "Agents/QA Agent/qa_reports/status.md"

# Check Fixer status
cat "Agents/Fixer Agent/fixer_reports/status.md"

# See latest QA report
ls -t "Agents/QA Agent/qa_reports/"report_*.md | head -1 | xargs cat

# See latest Fixer log
ls -t "Agents/Fixer Agent/fixer_reports/"fixes_*.md | head -1 | xargs cat

# See escalated issues
cat "Agents/Fixer Agent/fixer_reports/needs_human.md"
"""

FILE_STRUCTURE = """
C:\\AI\\Agency_OS\\
|
+-- Agents/
|   +-- Builder Agent/
|   |   +-- BUILDER_AGENT_PROMPT.md
|   |   +-- builder_tasks/
|   |       +-- pending.md          # QA writes, Builder reads
|   |
|   +-- QA Agent/
|   |   +-- QA_AGENT_PROMPT.md
|   |   +-- qa_reports/
|   |       +-- report_*.md         # Scan reports
|   |       +-- status.md           # Current status
|   |
|   +-- Fixer Agent/
|       +-- FIXER_AGENT_PROMPT.md
|       +-- fixer_reports/
|           +-- fixes_*.md          # Fix logs
|           +-- status.md           # Fixer status
|           +-- needs_human.md      # Escalated issues
|
+-- skills/
|   +-- SKILL_INDEX.md              # Master index
|   +-- agents/
|       +-- BUILDER_SKILL.md
|       +-- QA_SKILL.md
|       +-- FIXER_SKILL.md
|       +-- COORDINATION_SKILL.md
|
+-- PROJECT_BLUEPRINT.md            # Source of truth
+-- PROGRESS.md                     # Build status
"""


if __name__ == "__main__":
    print(get_instructions())
