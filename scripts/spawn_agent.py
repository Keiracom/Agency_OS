#!/usr/bin/env python3
"""
================================================================================
SPAWN_AGENT.PY — Sub-Agent Handshake Protocol with Quota Intelligence
================================================================================

Purpose (CEO Summary):
    Spawns sub-agents with governance injection AND quota tracking. We operate
    under Claude Max subscription (no per-token costs), but we have a finite
    daily message quota. Every unnecessary turn burns quota.

Key Concepts:
    - MESSAGE BURN: Number of turns a sub-agent takes to complete a task
    - EXTERNAL SPEND: $AUD costs for services like Apollo, Prospeo (LAW II)
    - LAZY GUARD: Sub-agents must be concise — no fluff, no wasted turns

Cost Model:
    - Model tokens: $0 (Claude Max subscription)
    - External APIs: Tracked per-call in $AUD
    - Quota: ~100 messages/5hrs (estimated Max ceiling)

Usage:
    python3 scripts/spawn_agent.py --task "Research X" --type research --dry-run
    python3 scripts/spawn_agent.py --task "Generate Y" --type codegen --timeout 300

================================================================================
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from typing import Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ============================================================================
# QUOTA CONSTANTS
# ============================================================================

# Claude Max estimated limits (conservative)
DAILY_MESSAGE_QUOTA = 100  # Messages per ~5hr window
WARNING_THRESHOLD = 0.7    # Warn at 70% usage
CRITICAL_THRESHOLD = 0.9   # Critical at 90% usage

# Sub-agent turn budgets by task type
TURN_BUDGETS = {
    "research": 5,      # Research should complete in 5 turns max
    "codegen": 8,       # Code generation may need more iteration
    "analysis": 4,      # Analysis should be focused
    "scraping": 3,      # Scraping is straightforward
}

# ============================================================================
# LAW INJECTION HEADER (WITH QUOTA INTELLIGENCE)
# ============================================================================

LAW_INJECTION_HEADER = """
## 🔒 GOVERNANCE INJECTION (Laws I-V) + QUOTA INTELLIGENCE

You are a sub-agent spawned by Elliot (CTO of Keiracom). You operate under Claude Max subscription.

### ⚡ THE LAZY GUARD (CRITICAL)

**YOU MUST BE CONCISE AND CORRECT.**

- Model tokens cost $0 (Claude Max), but MESSAGE QUOTA IS FINITE
- Every unnecessary turn burns quota that could be used elsewhere
- Your turn budget: **{turn_budget} messages MAX**
- If you exceed this, you are wasting Dave's subscription

**Anti-patterns (FORBIDDEN):**
- "Let me think about this..." → Just give the answer
- "I'll break this into steps..." → Do it silently, report results
- "Here's what I found so far..." → Only report when COMPLETE
- Asking clarifying questions → Use reasonable assumptions, note them

**Pattern (REQUIRED):**
- Receive task → Execute → Return complete JSON output
- One shot if possible. Multi-turn only if genuinely blocked.

---

### LAW I: Context Anchor
- FORBIDDEN from assuming you know a skill's current state
- MUST read SKILL.md before first use of any tool
- If a tool is not documented, it does not exist

### LAW II: Australia First Financial Gate
- Model costs: $0 (Claude Max)
- External API costs (Apollo, Prospeo, etc.): MUST track in $AUD
- Exchange rate: 1 USD = 1.55 AUD

### LAW III: Justification Requirement
- Include Governance Trace for every decision
- Format: [Rule: X] -> [Action: Y]

### LAW IV: Non-Coder Bridge
- No code blocks over 20 lines without a Conceptual Summary

### LAW V: Memory Integrity
- FORBIDDEN from saving memories directly to Supabase
- Return all proposed memories in `memories_proposed` field

---

## 📍 CURRENT CONTEXT

- **Project:** {project}
- **Phase:** {phase}
- **Parent Session:** {parent_session}
- **Spawned At:** {spawned_at}
- **Turn Budget:** {turn_budget} messages

---

## 📋 YOUR TASK

{task}

---

## 📤 REQUIRED OUTPUT FORMAT (STRICT)

Return ONLY this JSON object. No preamble. No explanation outside the JSON.

```json
{{
  "status": "complete" | "partial" | "failed",
  "findings": [
    "Finding 1: Concise factual statement",
    "Finding 2: Another fact"
  ],
  "external_spend_aud": 0.00,
  "spend_breakdown": [
    {{"service": "Apollo", "operation": "people_search", "calls": 1, "cost_aud": 0.05}}
  ],
  "message_count": 1,
  "turn_budget": {turn_budget},
  "budget_status": "under" | "at" | "over",
  "memories_proposed": [
    {{
      "type": "fact" | "decision" | "rule" | "cost_event",
      "content": "Concise memory content",
      "metadata": {{"source": "sub-agent", "task_type": "{task_type}"}}
    }}
  ],
  "governance_trace": [
    "[Rule: LAW I] -> [Action: Read SKILL.md]",
    "[Rule: LAW II] -> [Action: Tracked Apollo cost: $0.05 AUD]"
  ],
  "errors": [],
  "notes": "Any assumptions made"
}}
```

**CRITICAL:** `message_count` must accurately reflect how many turns you took.
"""

# ============================================================================
# QUOTA TRACKING
# ============================================================================

def load_daily_quota_usage() -> dict:
    """Load today's quota usage from state."""
    import subprocess
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    result = subprocess.run(
        [
            "python3", f"{PROJECT_ROOT}/tools/database_master.py",
            "query", "supabase",
            "--sql", f"SELECT value FROM elliot_internal.state WHERE key = 'quota_{today}';"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    try:
        if '"value":' in result.stdout:
            import re
            match = re.search(r'"value":\s*(\{[^}]+\})', result.stdout, re.DOTALL)
            if match:
                return json.loads(match.group(1))
    except:
        pass
    
    return {
        "date": today,
        "total_messages": 0,
        "sub_agent_messages": 0,
        "elliot_messages": 0,
        "external_spend_aud": 0.0
    }


def update_quota_usage(message_count: int, external_spend: float, is_sub_agent: bool = True):
    """Update quota usage in state."""
    import subprocess
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    current = load_daily_quota_usage()
    
    current["total_messages"] = current.get("total_messages", 0) + message_count
    current["external_spend_aud"] = current.get("external_spend_aud", 0) + external_spend
    
    if is_sub_agent:
        current["sub_agent_messages"] = current.get("sub_agent_messages", 0) + message_count
    else:
        current["elliot_messages"] = current.get("elliot_messages", 0) + message_count
    
    # Calculate percentage
    current["quota_percent"] = round(current["total_messages"] / DAILY_MESSAGE_QUOTA * 100, 1)
    current["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    value_json = json.dumps(current)
    
    subprocess.run(
        [
            "python3", f"{PROJECT_ROOT}/tools/database_master.py",
            "query", "supabase",
            "--sql", f"""
                INSERT INTO elliot_internal.state (key, value)
                VALUES ('quota_{today}', '{value_json}'::jsonb)
                ON CONFLICT (key) DO UPDATE SET
                    value = '{value_json}'::jsonb,
                    version = elliot_internal.state.version + 1,
                    updated_at = NOW();
            """
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    return current


def get_quota_status() -> dict:
    """Get current quota status with warnings."""
    usage = load_daily_quota_usage()
    total = usage.get("total_messages", 0)
    percent = total / DAILY_MESSAGE_QUOTA
    
    status = {
        "total_used": total,
        "quota_limit": DAILY_MESSAGE_QUOTA,
        "percent_used": round(percent * 100, 1),
        "remaining": DAILY_MESSAGE_QUOTA - total,
        "external_spend_aud": usage.get("external_spend_aud", 0),
        "level": "ok"
    }
    
    if percent >= CRITICAL_THRESHOLD:
        status["level"] = "critical"
        status["warning"] = f"🚨 CRITICAL: {status['percent_used']}% quota used. Conserve messages!"
    elif percent >= WARNING_THRESHOLD:
        status["level"] = "warning"
        status["warning"] = f"⚠️ WARNING: {status['percent_used']}% quota used. Be concise."
    
    return status


# ============================================================================
# STATE LOADER
# ============================================================================

def load_current_state() -> dict:
    """Load current_process from Supabase."""
    import subprocess
    
    result = subprocess.run(
        [
            "python3", f"{PROJECT_ROOT}/tools/database_master.py",
            "query", "supabase",
            "--sql", "SELECT value FROM elliot_internal.state WHERE key = 'current_process';"
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT
    )
    
    try:
        if '"value":' in result.stdout:
            import re
            match = re.search(r'"value":\s*(\{[^}]+\})', result.stdout, re.DOTALL)
            if match:
                return json.loads(match.group(1))
    except:
        pass
    
    return {"project": "Unknown", "phase": "Unknown"}


# ============================================================================
# SPAWN LOGIC
# ============================================================================

def build_injected_task(task: str, task_type: str, parent_session: str) -> str:
    """Build the full task with Law Injection + Quota Intelligence."""
    
    state = load_current_state()
    turn_budget = TURN_BUDGETS.get(task_type, 5)
    
    return LAW_INJECTION_HEADER.format(
        project=state.get("project", "Unknown"),
        phase=state.get("phase", "Unknown"),
        parent_session=parent_session,
        spawned_at=datetime.now(timezone.utc).isoformat(),
        task=task,
        task_type=task_type,
        turn_budget=turn_budget
    )


def generate_content_hash(content: str) -> str:
    """Generate hash for deduplication."""
    return hashlib.sha256(content.strip().lower().encode()).hexdigest()[:16]


def absorb_output(output: dict, task_id: str) -> dict:
    """
    Process sub-agent output:
    1. Update quota tracking
    2. Deduplicate memories
    3. Queue for signoff
    """
    result = {
        "quota_update": None,
        "memories_absorbed": 0,
        "memories_duplicate": 0,
        "budget_compliance": None
    }
    
    # Update quota
    message_count = output.get("message_count", 1)
    external_spend = output.get("external_spend_aud", 0)
    result["quota_update"] = update_quota_usage(message_count, external_spend)
    
    # Check budget compliance
    turn_budget = output.get("turn_budget", 5)
    if message_count > turn_budget:
        result["budget_compliance"] = f"OVER by {message_count - turn_budget} turns"
    elif message_count == turn_budget:
        result["budget_compliance"] = "AT budget"
    else:
        result["budget_compliance"] = f"UNDER by {turn_budget - message_count} turns ✓"
    
    # Process memories (dedup logic here)
    memories = output.get("memories_proposed", [])
    result["memories_absorbed"] = len(memories)  # Simplified; real impl checks hashes
    
    return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Spawn sub-agent with governance + quota intelligence"
    )
    parser.add_argument("--task", "-t", required=True, help="Task to delegate")
    parser.add_argument("--type", choices=["research", "codegen", "analysis", "scraping"],
                        default="research", help="Task type")
    parser.add_argument("--parent-session", default=os.environ.get("CLAWDBOT_SESSION_KEY", "unknown"))
    parser.add_argument("--dry-run", action="store_true", help="Preview without spawning")
    parser.add_argument("--quota-status", action="store_true", help="Show current quota status")
    parser.add_argument("--timeout", type=int, default=300)
    
    args = parser.parse_args()
    
    # Quota status check
    if args.quota_status:
        status = get_quota_status()
        print(json.dumps(status, indent=2))
        return
    
    # Check quota before spawning
    quota = get_quota_status()
    if quota["level"] == "critical":
        print(f"🚨 {quota['warning']}")
        print("Consider completing tasks manually to conserve quota.")
        if not args.dry_run:
            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                return
    elif quota["level"] == "warning":
        print(f"⚠️ {quota['warning']}")
    
    # Build injected task
    injected_task = build_injected_task(args.task, args.type, args.parent_session)
    turn_budget = TURN_BUDGETS.get(args.type, 5)
    
    if args.dry_run:
        print("=" * 70)
        print("DRY RUN — Injected Task Preview")
        print(f"Turn Budget: {turn_budget} messages")
        print(f"Quota Status: {quota['percent_used']}% used ({quota['remaining']} remaining)")
        print("=" * 70)
        print(injected_task)
        print("=" * 70)
        return
    
    task_id = hashlib.sha256(f"{args.task}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
    
    print(f"[SPAWN] Task ID: {task_id}")
    print(f"[SPAWN] Type: {args.type}")
    print(f"[SPAWN] Turn Budget: {turn_budget}")
    print(f"[SPAWN] Quota: {quota['percent_used']}% used")
    print()
    print("=" * 70)
    print("CLAWDBOT SPAWN COMMAND:")
    print("=" * 70)
    print(f"""
sessions_spawn(
    task=\"\"\"{injected_task}\"\"\",
    label="subagent-{task_id}",
    cleanup="delete",
    runTimeoutSeconds={args.timeout}
)
""")


if __name__ == "__main__":
    main()
