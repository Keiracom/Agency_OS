"""
Elliot Memory Sync Service

Syncs memory files (markdown) ↔ Supabase database.
Designed to run as a Prefect flow on Railway.

Features:
- File watching for real-time sync
- Bidirectional sync with conflict detection
- Markdown parsing to structured data
- Checksum-based change detection
"""

import hashlib
import json
import os
import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

import yaml
from supabase import create_client, Client
from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import redis


# =============================================================================
# CONFIGURATION
# =============================================================================

MEMORY_BASE_PATH = Path("/home/elliotbot/clawd")
DAILY_PATH = MEMORY_BASE_PATH / "memory" / "daily"
WEEKLY_PATH = MEMORY_BASE_PATH / "memory" / "weekly"
PATTERNS_FILE = MEMORY_BASE_PATH / "memory" / "PATTERNS.md"
RULES_FILE = MEMORY_BASE_PATH / "knowledge" / "RULES.md"
LEARNINGS_FILE = MEMORY_BASE_PATH / "knowledge" / "LEARNINGS.md"
DECISIONS_FILE = MEMORY_BASE_PATH / "knowledge" / "DECISIONS.md"


class SyncDirection(Enum):
    FILE_TO_DB = "file_to_db"
    DB_TO_FILE = "db_to_file"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class SyncResult:
    file_path: str
    direction: SyncDirection
    status: str  # 'synced', 'conflict', 'error', 'skipped'
    message: str
    checksum: Optional[str] = None


# =============================================================================
# MARKDOWN PARSERS
# =============================================================================

def parse_daily_log(content: str, file_date: date) -> Dict[str, Any]:
    """Parse a daily log markdown file into structured data."""
    result = {
        "log_date": file_date.isoformat(),
        "accomplishments": [],
        "interactions": [],
        "issues": [],
        "notes": "",
        "raw_content": content,
    }
    
    current_section = None
    section_content = []
    
    lines = content.split('\n')
    for line in lines:
        # Detect section headers
        if line.startswith('## '):
            # Save previous section
            if current_section and section_content:
                _save_section(result, current_section, section_content)
            
            current_section = line[3:].strip().lower()
            section_content = []
        elif line.startswith('- ') and current_section:
            # List item
            item = line[2:].strip()
            section_content.append(item)
        elif line.strip() and current_section:
            # Continuation or notes
            if current_section == 'notes':
                section_content.append(line)
    
    # Save last section
    if current_section and section_content:
        _save_section(result, current_section, section_content)
    
    return result


def _save_section(result: Dict, section: str, content: List[str]):
    """Save parsed section content to result dict."""
    if 'accomplishment' in section:
        result['accomplishments'] = content
    elif 'interaction' in section:
        result['interactions'] = [_parse_interaction(i) for i in content]
    elif 'issue' in section or 'problem' in section:
        result['issues'] = content
    elif 'note' in section:
        result['notes'] = '\n'.join(content)


def _parse_interaction(text: str) -> Dict[str, str]:
    """Parse an interaction string into structured format."""
    # Format: "[channel] with [person]: summary" or just "summary"
    match = re.match(r'\[([^\]]+)\]\s*(?:with\s+([^:]+):)?\s*(.+)', text)
    if match:
        return {
            "channel": match.group(1),
            "with": match.group(2) or "",
            "summary": match.group(3),
        }
    return {"channel": "unknown", "with": "", "summary": text}


def parse_weekly_rollup(content: str, year_week: str) -> Dict[str, Any]:
    """Parse a weekly rollup markdown file."""
    result = {
        "year_week": year_week,
        "key_accomplishments": [],
        "decisions_made": [],
        "patterns_noticed": [],
        "open_questions": [],
        "summary": "",
        "raw_content": content,
    }
    
    current_section = None
    section_content = []
    
    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section and section_content:
                _save_weekly_section(result, current_section, section_content)
            current_section = line[3:].strip().lower()
            section_content = []
        elif line.startswith('- ') and current_section:
            section_content.append(line[2:].strip())
        elif line.strip() and current_section == 'summary':
            section_content.append(line)
    
    if current_section and section_content:
        _save_weekly_section(result, current_section, section_content)
    
    return result


def _save_weekly_section(result: Dict, section: str, content: List[str]):
    """Save weekly section content."""
    if 'accomplishment' in section:
        result['key_accomplishments'] = content
    elif 'decision' in section:
        result['decisions_made'] = [{"summary": d} for d in content]
    elif 'pattern' in section:
        result['patterns_noticed'] = content
    elif 'question' in section:
        result['open_questions'] = content
    elif 'summary' in section:
        result['summary'] = '\n'.join(content)


def parse_rules(content: str) -> List[Dict[str, Any]]:
    """Parse RULES.md into list of rule objects."""
    rules = []
    current_category = "general"
    current_rule = None
    
    for line in content.split('\n'):
        if line.startswith('## '):
            current_category = line[3:].strip().lower().replace(' ', '_')
        elif line.startswith('### '):
            if current_rule:
                rules.append(current_rule)
            title = line[4:].strip()
            current_rule = {
                "rule_key": _slugify(title),
                "category": current_category,
                "title": title,
                "description": "",
                "severity": "standard",
            }
        elif current_rule and line.strip():
            if line.startswith('**Severity:**'):
                current_rule['severity'] = line.split(':')[1].strip().lower()
            else:
                current_rule['description'] += line.strip() + ' '
    
    if current_rule:
        rules.append(current_rule)
    
    # Clean up descriptions
    for rule in rules:
        rule['description'] = rule['description'].strip()
    
    return rules


def parse_learnings(content: str) -> List[Dict[str, Any]]:
    """Parse LEARNINGS.md into list of learning objects."""
    learnings = []
    current_category = "general"
    current_learning = None
    
    for line in content.split('\n'):
        if line.startswith('## '):
            current_category = line[3:].strip().lower().replace(' ', '_')
        elif line.startswith('### '):
            if current_learning:
                learnings.append(current_learning)
            title = line[4:].strip()
            current_learning = {
                "learning_key": _slugify(title),
                "category": current_category,
                "title": title,
                "description": "",
                "impact_level": "medium",
            }
        elif current_learning and line.strip():
            if line.startswith('**Impact:**'):
                current_learning['impact_level'] = line.split(':')[1].strip().lower()
            elif line.startswith('**Context:**'):
                current_learning['context'] = line.split(':', 1)[1].strip()
            else:
                current_learning['description'] += line.strip() + ' '
    
    if current_learning:
        learnings.append(current_learning)
    
    for learning in learnings:
        learning['description'] = learning['description'].strip()
    
    return learnings


def parse_decisions(content: str) -> List[Dict[str, Any]]:
    """Parse DECISIONS.md into list of decision objects."""
    decisions = []
    current_decision = None
    current_field = None
    
    for line in content.split('\n'):
        if line.startswith('### '):
            if current_decision:
                decisions.append(current_decision)
            
            # Parse date and title from header: "### [2026-01-28] Decision Title"
            match = re.match(r'###\s*\[?(\d{4}-\d{2}-\d{2})\]?\s*(.+)', line)
            if match:
                current_decision = {
                    "decision_key": _slugify(match.group(2)),
                    "decision_date": match.group(1),
                    "title": match.group(2),
                    "context": "",
                    "options": [],
                    "chosen_option": "",
                    "rationale": "",
                    "expected_outcome": "",
                    "actual_outcome": "",
                    "outcome_status": "pending",
                    "learning_extracted": "",
                }
                current_field = None
        elif current_decision:
            if line.startswith('**Context:**'):
                current_field = 'context'
                current_decision['context'] = line.split(':', 1)[1].strip()
            elif line.startswith('**Options:**'):
                current_field = 'options'
            elif line.startswith('**Decision:**'):
                current_field = 'chosen_option'
                current_decision['chosen_option'] = line.split(':', 1)[1].strip()
            elif line.startswith('**Rationale:**'):
                current_field = 'rationale'
                current_decision['rationale'] = line.split(':', 1)[1].strip()
            elif line.startswith('**Expected outcome:**'):
                current_field = 'expected_outcome'
                current_decision['expected_outcome'] = line.split(':', 1)[1].strip()
            elif line.startswith('**Actual outcome:**'):
                current_field = 'actual_outcome'
                val = line.split(':', 1)[1].strip()
                if val and val != '[Fill in later]':
                    current_decision['actual_outcome'] = val
                    current_decision['outcome_status'] = 'success'  # Default if filled
            elif line.startswith('**Learning:**'):
                current_field = 'learning_extracted'
                val = line.split(':', 1)[1].strip()
                if val and val != '[Fill in later]':
                    current_decision['learning_extracted'] = val
            elif line.startswith('- ') and current_field == 'options':
                current_decision['options'].append({"option": line[2:].strip()})
            elif line.strip() and current_field in ['context', 'rationale']:
                current_decision[current_field] += ' ' + line.strip()
    
    if current_decision:
        decisions.append(current_decision)
    
    return decisions


def _slugify(text: str) -> str:
    """Convert text to a slug for use as a key."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '_', text)
    text = text.strip('_')
    return text[:100]  # Limit length


# =============================================================================
# MARKDOWN GENERATORS (for DB → File sync)
# =============================================================================

def generate_daily_markdown(data: Dict[str, Any]) -> str:
    """Generate markdown from daily log database record."""
    lines = [f"# {data['log_date']}", ""]
    
    if data.get('accomplishments'):
        lines.extend(["## Accomplishments", ""])
        for item in data['accomplishments']:
            lines.append(f"- {item}")
        lines.append("")
    
    if data.get('interactions'):
        lines.extend(["## Interactions", ""])
        for item in data['interactions']:
            if isinstance(item, dict):
                channel = item.get('channel', 'unknown')
                with_person = item.get('with', '')
                summary = item.get('summary', '')
                if with_person:
                    lines.append(f"- [{channel}] with {with_person}: {summary}")
                else:
                    lines.append(f"- [{channel}] {summary}")
            else:
                lines.append(f"- {item}")
        lines.append("")
    
    if data.get('issues'):
        lines.extend(["## Issues", ""])
        for item in data['issues']:
            lines.append(f"- {item}")
        lines.append("")
    
    if data.get('notes'):
        lines.extend(["## Notes", "", data['notes'], ""])
    
    return '\n'.join(lines)


def generate_rules_markdown(rules: List[Dict[str, Any]]) -> str:
    """Generate RULES.md from database records."""
    lines = ["# Operating Rules", ""]
    
    # Group by category
    categories: Dict[str, List[Dict]] = {}
    for rule in rules:
        cat = rule.get('category', 'general')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(rule)
    
    for category, cat_rules in categories.items():
        lines.extend([f"## {category.replace('_', ' ').title()}", ""])
        for rule in sorted(cat_rules, key=lambda r: r.get('sort_order', 0)):
            lines.extend([
                f"### {rule['title']}",
                "",
                rule['description'],
                "",
            ])
            if rule.get('severity') != 'standard':
                lines.insert(-1, f"**Severity:** {rule['severity']}")
    
    return '\n'.join(lines)


# =============================================================================
# SUPABASE OPERATIONS
# =============================================================================

def get_supabase_client() -> Client:
    """Create Supabase client from environment."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for sync
    return create_client(url, key)


def get_file_checksum(file_path: Path) -> str:
    """Calculate MD5 checksum of file."""
    if not file_path.exists():
        return ""
    content = file_path.read_text()
    return hashlib.md5(content.encode()).hexdigest()


@task
def sync_daily_log(file_path: Path, direction: SyncDirection, supabase: Client) -> SyncResult:
    """Sync a single daily log file."""
    logger = get_run_logger()
    
    # Extract date from filename (YYYY-MM-DD.md)
    file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
    file_checksum = get_file_checksum(file_path)
    
    # Get current DB state
    db_result = supabase.table("elliot_daily_logs") \
        .select("*") \
        .eq("log_date", file_date.isoformat()) \
        .execute()
    
    db_record = db_result.data[0] if db_result.data else None
    db_checksum = db_record.get("file_checksum") if db_record else None
    
    if direction == SyncDirection.FILE_TO_DB:
        if not file_path.exists():
            return SyncResult(str(file_path), direction, "skipped", "File does not exist")
        
        # Check if file changed since last sync
        if db_checksum == file_checksum:
            return SyncResult(str(file_path), direction, "skipped", "No changes")
        
        # Parse and upsert
        content = file_path.read_text()
        parsed = parse_daily_log(content, file_date)
        parsed["file_checksum"] = file_checksum
        parsed["sync_source"] = "file"
        parsed["synced_at"] = datetime.utcnow().isoformat()
        
        supabase.table("elliot_daily_logs").upsert(
            parsed,
            on_conflict="log_date"
        ).execute()
        
        logger.info(f"Synced {file_path.name} to database")
        return SyncResult(str(file_path), direction, "synced", "File synced to DB", file_checksum)
    
    elif direction == SyncDirection.DB_TO_FILE:
        if not db_record:
            return SyncResult(str(file_path), direction, "skipped", "No DB record")
        
        # Check if DB changed (sync_source = 'dashboard')
        if db_record.get("sync_source") != "dashboard":
            return SyncResult(str(file_path), direction, "skipped", "DB not modified by dashboard")
        
        # Generate markdown and write
        markdown = generate_daily_markdown(db_record)
        file_path.write_text(markdown)
        
        # Update checksum in DB
        new_checksum = get_file_checksum(file_path)
        supabase.table("elliot_daily_logs").update({
            "file_checksum": new_checksum,
            "sync_source": "file",
            "synced_at": datetime.utcnow().isoformat(),
        }).eq("log_date", file_date.isoformat()).execute()
        
        logger.info(f"Synced {file_date} from database to file")
        return SyncResult(str(file_path), direction, "synced", "DB synced to file", new_checksum)
    
    return SyncResult(str(file_path), direction, "error", "Invalid direction")


@task
def sync_rules(direction: SyncDirection, supabase: Client) -> SyncResult:
    """Sync RULES.md."""
    logger = get_run_logger()
    file_path = RULES_FILE
    
    if direction == SyncDirection.FILE_TO_DB:
        if not file_path.exists():
            return SyncResult(str(file_path), direction, "skipped", "File does not exist")
        
        content = file_path.read_text()
        rules = parse_rules(content)
        
        # Delete existing and insert new (full replace)
        supabase.table("elliot_rules").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        
        for i, rule in enumerate(rules):
            rule["sort_order"] = i
            rule["is_active"] = True
            supabase.table("elliot_rules").insert(rule).execute()
        
        logger.info(f"Synced {len(rules)} rules to database")
        return SyncResult(str(file_path), direction, "synced", f"Synced {len(rules)} rules")
    
    elif direction == SyncDirection.DB_TO_FILE:
        result = supabase.table("elliot_rules") \
            .select("*") \
            .eq("is_active", True) \
            .order("sort_order") \
            .execute()
        
        markdown = generate_rules_markdown(result.data)
        file_path.write_text(markdown)
        
        logger.info(f"Synced {len(result.data)} rules to file")
        return SyncResult(str(file_path), direction, "synced", f"Synced {len(result.data)} rules")
    
    return SyncResult(str(file_path), direction, "error", "Invalid direction")


@task
def sync_learnings(direction: SyncDirection, supabase: Client) -> SyncResult:
    """Sync LEARNINGS.md."""
    logger = get_run_logger()
    file_path = LEARNINGS_FILE
    
    if direction == SyncDirection.FILE_TO_DB:
        if not file_path.exists():
            return SyncResult(str(file_path), direction, "skipped", "File does not exist")
        
        content = file_path.read_text()
        learnings = parse_learnings(content)
        
        for learning in learnings:
            supabase.table("elliot_learnings").upsert(
                learning,
                on_conflict="learning_key"
            ).execute()
        
        logger.info(f"Synced {len(learnings)} learnings to database")
        return SyncResult(str(file_path), direction, "synced", f"Synced {len(learnings)} learnings")
    
    return SyncResult(str(file_path), direction, "skipped", "DB→file not implemented for learnings")


@task
def sync_decisions(direction: SyncDirection, supabase: Client) -> SyncResult:
    """Sync DECISIONS.md."""
    logger = get_run_logger()
    file_path = DECISIONS_FILE
    
    if direction == SyncDirection.FILE_TO_DB:
        if not file_path.exists():
            return SyncResult(str(file_path), direction, "skipped", "File does not exist")
        
        content = file_path.read_text()
        decisions = parse_decisions(content)
        
        for decision in decisions:
            supabase.table("elliot_decisions").upsert(
                decision,
                on_conflict="decision_key"
            ).execute()
        
        logger.info(f"Synced {len(decisions)} decisions to database")
        return SyncResult(str(file_path), direction, "synced", f"Synced {len(decisions)} decisions")
    
    return SyncResult(str(file_path), direction, "skipped", "DB→file not implemented for decisions")


@task
def update_sync_state(file_path: str, file_type: str, result: SyncResult, supabase: Client):
    """Update sync state tracking table."""
    supabase.table("elliot_sync_state").upsert({
        "file_path": file_path,
        "file_type": file_type,
        "file_checksum": result.checksum,
        "last_sync_at": datetime.utcnow().isoformat(),
        "last_sync_direction": result.direction.value,
        "sync_status": result.status,
        "sync_error": result.message if result.status == "error" else None,
    }, on_conflict="file_path").execute()


@task
def log_activity(activity_type: str, summary: str, details: Dict = None, supabase: Client = None):
    """Log sync activity."""
    if supabase is None:
        supabase = get_supabase_client()
    
    supabase.table("elliot_activity").insert({
        "activity_type": activity_type,
        "channel": "sync_service",
        "summary": summary,
        "details": details or {},
        "status": "completed",
    }).execute()


# =============================================================================
# PREFECT FLOWS
# =============================================================================

@flow(name="elliot-sync-all")
def sync_all_files(direction: str = "file_to_db"):
    """Sync all memory files to/from database."""
    logger = get_run_logger()
    logger.info(f"Starting full sync: {direction}")
    
    sync_dir = SyncDirection(direction)
    supabase = get_supabase_client()
    results = []
    
    # Sync daily logs
    if DAILY_PATH.exists():
        for file in DAILY_PATH.glob("*.md"):
            if file.stem == "TEMPLATE":
                continue
            result = sync_daily_log(file, sync_dir, supabase)
            results.append(result)
            update_sync_state(str(file), "daily", result, supabase)
    
    # Sync knowledge files
    results.append(sync_rules(sync_dir, supabase))
    results.append(sync_learnings(sync_dir, supabase))
    results.append(sync_decisions(sync_dir, supabase))
    
    # Log summary
    synced = sum(1 for r in results if r.status == "synced")
    skipped = sum(1 for r in results if r.status == "skipped")
    errors = sum(1 for r in results if r.status == "error")
    
    log_activity(
        "sync",
        f"Full sync completed: {synced} synced, {skipped} skipped, {errors} errors",
        {"synced": synced, "skipped": skipped, "errors": errors, "direction": direction},
        supabase
    )
    
    logger.info(f"Sync completed: {synced} synced, {skipped} skipped, {errors} errors")
    return results


@flow(name="elliot-sync-daily")
def sync_single_daily(date_str: str, direction: str = "file_to_db"):
    """Sync a single daily log by date."""
    supabase = get_supabase_client()
    file_path = DAILY_PATH / f"{date_str}.md"
    sync_dir = SyncDirection(direction)
    
    result = sync_daily_log(file_path, sync_dir, supabase)
    update_sync_state(str(file_path), "daily", result, supabase)
    
    return result


# =============================================================================
# FILE WATCHER (for real-time sync)
# =============================================================================

class MemoryFileHandler(FileSystemEventHandler):
    """Watch memory files and trigger sync on changes."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.debounce_seconds = 5
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix != ".md":
            return
        
        # Debounce: check if we recently queued this file
        cache_key = f"sync:debounce:{file_path}"
        if self.redis.exists(cache_key):
            return
        
        self.redis.setex(cache_key, self.debounce_seconds, "1")
        
        # Queue sync job
        self.redis.rpush("sync:queue", json.dumps({
            "file_path": str(file_path),
            "timestamp": datetime.utcnow().isoformat(),
        }))
        
        print(f"Queued sync for: {file_path}")


def start_file_watcher():
    """Start watching memory files for changes."""
    redis_url = os.environ.get("REDIS_URL")
    redis_client = redis.from_url(redis_url)
    
    event_handler = MemoryFileHandler(redis_client)
    observer = Observer()
    
    # Watch memory and knowledge directories
    observer.schedule(event_handler, str(DAILY_PATH), recursive=False)
    observer.schedule(event_handler, str(MEMORY_BASE_PATH / "knowledge"), recursive=False)
    
    observer.start()
    print("File watcher started")
    
    try:
        while True:
            # Process sync queue
            item = redis_client.lpop("sync:queue")
            if item:
                data = json.loads(item)
                file_path = Path(data["file_path"])
                
                # Determine file type and sync
                if "daily" in str(file_path):
                    sync_single_daily.with_options(name=f"sync-{file_path.stem}")()
                elif file_path.name == "RULES.md":
                    sync_rules(SyncDirection.FILE_TO_DB, get_supabase_client())
                elif file_path.name == "LEARNINGS.md":
                    sync_learnings(SyncDirection.FILE_TO_DB, get_supabase_client())
                elif file_path.name == "DECISIONS.md":
                    sync_decisions(SyncDirection.FILE_TO_DB, get_supabase_client())
            
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()


# =============================================================================
# ENTRY POINTS
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "sync":
            direction = sys.argv[2] if len(sys.argv) > 2 else "file_to_db"
            sync_all_files(direction)
        
        elif command == "watch":
            start_file_watcher()
        
        else:
            print(f"Unknown command: {command}")
            print("Usage: python sync_service.py [sync|watch] [direction]")
    else:
        # Default: run full sync
        sync_all_files()
