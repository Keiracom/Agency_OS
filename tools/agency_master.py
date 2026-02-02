#!/usr/bin/env python3
"""
Agency Product Tool - Agency OS product management.

Consolidates: agency-os, agency-os-ui

Usage:
    python3 tools/agency_master.py <action> [options]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# ============================================
# PATHS
# ============================================

AGENCY_OS_PATH = Path("/home/elliotbot/projects/Agency_OS")
FRONTEND_PATH = Path("/home/elliotbot/projects/elliot-dashboard")

# ============================================
# DEPLOY ACTIONS
# ============================================

def check_deploy_status() -> dict:
    """Check deployment status across services."""
    
    status = {
        "backend": {"path": str(AGENCY_OS_PATH), "exists": AGENCY_OS_PATH.exists()},
        "frontend": {"path": str(FRONTEND_PATH), "exists": FRONTEND_PATH.exists()},
    }
    
    # Check for uncommitted changes
    for name, info in status.items():
        if info["exists"]:
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=info["path"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                info["clean"] = len(result.stdout.strip()) == 0
                info["branch"] = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=info["path"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).stdout.strip()
            except Exception as e:
                info["error"] = str(e)
    
    return status


def list_open_prs() -> list[dict]:
    """List open PRs for Agency OS."""
    
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--json", "number,title,author,createdAt,url"],
            cwd=AGENCY_OS_PATH,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return [{"error": result.stderr}]
    except FileNotFoundError:
        return [{"error": "gh CLI not installed"}]
    except Exception as e:
        return [{"error": str(e)}]


def run_tests() -> dict:
    """Run test suite."""
    
    try:
        result = subprocess.run(
            ["pytest", "-v", "--tb=short", "-q"],
            cwd=AGENCY_OS_PATH,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "passed": result.returncode == 0,
            "output": result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout,
            "errors": result.stderr[-500:] if result.stderr else None,
        }
    except FileNotFoundError:
        return {"error": "pytest not installed"}
    except Exception as e:
        return {"error": str(e)}


# ============================================
# AUDIT ACTIONS
# ============================================

def audit_env() -> dict:
    """Audit environment variables."""
    
    env_file = Path.home() / ".config/agency-os/.env"
    
    if not env_file.exists():
        return {"error": f"Env file not found: {env_file}"}
    
    with open(env_file) as f:
        lines = f.readlines()
    
    required_keys = [
        "SUPABASE_URL", "SUPABASE_KEY", "DATABASE_URL",
        "PREFECT_API_URL", "REDIS_URL",
        "ANTHROPIC_API_KEY",
    ]
    
    found = {}
    missing = []
    
    for key in required_keys:
        is_set = any(line.strip().startswith(f"{key}=") for line in lines)
        if is_set:
            found[key] = "✅ Set"
        else:
            missing.append(key)
    
    return {
        "env_file": str(env_file),
        "found": found,
        "missing": missing,
        "total_vars": len([l for l in lines if l.strip() and not l.startswith('#') and '=' in l]),
    }


def audit_schema() -> list[dict]:
    """List database tables."""
    
    try:
        # Import and use database tool
        from database_master import postgres_tables
        return postgres_tables()
    except ImportError:
        # Fallback to direct query
        import psycopg2
        
        env_file = Path.home() / ".config/agency-os/.env"
        DATABASE_URL = None
        
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("DATABASE_URL"):
                        DATABASE_URL = line.split("=", 1)[1].strip().strip('"')
                        break
        
        if not DATABASE_URL:
            return [{"error": "DATABASE_URL not found"}]
        
        DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute("""
            SELECT table_schema, table_name 
            FROM information_schema.tables 
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
        """)
        results = [{"schema": r[0], "table": r[1]} for r in cur.fetchall()]
        cur.close()
        conn.close()
        return results


# ============================================
# UI ACTIONS
# ============================================

def check_ui_components() -> dict:
    """Check UI component status."""
    
    html_path = Path("/home/elliotbot/clawd/agency-os-html")
    
    if not html_path.exists():
        return {"error": "agency-os-html directory not found"}
    
    components = list(html_path.glob("*.html"))
    
    return {
        "path": str(html_path),
        "components": [c.name for c in components],
        "count": len(components),
    }


# ============================================
# ROUTER
# ============================================

def route(action: str, **kwargs) -> dict | list[dict]:
    """Route to appropriate action."""
    
    if action == "status":
        return check_deploy_status()
    elif action == "prs":
        return list_open_prs()
    elif action == "test":
        return run_tests()
    elif action == "audit-env":
        return audit_env()
    elif action == "audit-schema":
        return audit_schema()
    elif action == "ui-check":
        return check_ui_components()
    else:
        return {"error": f"Unknown action: {action}"}


def format_results(results, action: str) -> str:
    """Format results for display."""
    
    if isinstance(results, dict) and "error" in results:
        return f"❌ Error: {results['error']}"
    
    output = [f"🏢 Agency OS - {action.upper()}", "=" * 50]
    
    if action == "status":
        for name, info in results.items():
            status = "✅" if info.get("exists") and info.get("clean") else "⚠️"
            output.append(f"{status} {name}: {info.get('branch', 'N/A')}")
            if not info.get("clean", True):
                output.append("    ⚠️ Uncommitted changes")
    
    elif action == "prs":
        for pr in results:
            output.append(f"  #{pr.get('number')} {pr.get('title')[:50]}")
            output.append(f"      by {pr.get('author', {}).get('login', '?')}")
    
    elif action == "audit-env":
        output.append(f"Env file: {results.get('env_file')}")
        output.append(f"Total vars: {results.get('total_vars')}")
        if results.get("missing"):
            output.append(f"⚠️ Missing: {', '.join(results['missing'])}")
        else:
            output.append("✅ All required vars set")
    
    elif action == "ui-check":
        output.append(f"Path: {results.get('path')}")
        output.append(f"Components: {results.get('count')}")
        for comp in results.get("components", []):
            output.append(f"  - {comp}")
    
    else:
        output.append(json.dumps(results, indent=2, default=str))
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Agency Product Tool")
    parser.add_argument("action", choices=[
        "status", "prs", "test", "audit-env", "audit-schema", "ui-check"
    ])
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    results = route(action=args.action)
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_results(results, args.action))


if __name__ == "__main__":
    main()
