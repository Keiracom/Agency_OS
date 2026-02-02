#!/usr/bin/env python3
"""
Database Master Tool - Unified database interface.

Consolidates: supabase, postgres, redis

Usage:
    python3 tools/database_master.py <action> <target> [options]
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Load env
def load_env():
    env_file = Path.home() / ".config/agency-os/.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value

load_env()

# ============================================
# SUPABASE / POSTGRES
# ============================================

def postgres_query(sql: str) -> list[dict]:
    """Execute SQL query."""
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        return [{"error": "psycopg2 not installed"}]
    
    DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        return [{"error": "DATABASE_URL not set"}]
    
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql)
        
        if cur.description:  # SELECT query
            results = [dict(row) for row in cur.fetchall()]
        else:  # INSERT/UPDATE/DELETE
            conn.commit()
            results = [{"affected_rows": cur.rowcount}]
        
        cur.close()
        conn.close()
        return results
    except Exception as e:
        return [{"error": str(e)}]


def postgres_tables() -> list[dict]:
    """List all tables."""
    sql = """
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """
    return postgres_query(sql)


def postgres_describe(table: str) -> list[dict]:
    """Describe table schema."""
    # Handle schema.table format
    if '.' in table:
        schema, table_name = table.split('.', 1)
        sql = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = '{schema}' AND table_name = '{table_name}'
        """
    else:
        sql = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table}'
        """
    return postgres_query(sql)


# ============================================
# REDIS
# ============================================

def redis_get(key: str) -> dict:
    """Get value from Redis."""
    
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        return {"error": "REDIS_URL not set"}
    
    try:
        import redis
    except ImportError:
        return {"error": "redis package not installed"}
    
    try:
        r = redis.from_url(REDIS_URL)
        value = r.get(key)
        if value:
            try:
                return {"key": key, "value": json.loads(value)}
            except json.JSONDecodeError:
                return {"key": key, "value": value.decode()}
        return {"key": key, "value": None}
    except Exception as e:
        return {"error": str(e)}


def redis_set(key: str, value: str, ttl: int = None) -> dict:
    """Set value in Redis."""
    
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        return {"error": "REDIS_URL not set"}
    
    try:
        import redis
    except ImportError:
        return {"error": "redis package not installed"}
    
    try:
        r = redis.from_url(REDIS_URL)
        if ttl:
            r.setex(key, ttl, value)
        else:
            r.set(key, value)
        return {"status": "ok", "key": key}
    except Exception as e:
        return {"error": str(e)}


def redis_keys(pattern: str = "*") -> list[str]:
    """List Redis keys matching pattern."""
    
    REDIS_URL = os.getenv("REDIS_URL")
    if not REDIS_URL:
        return [{"error": "REDIS_URL not set"}]
    
    try:
        import redis
    except ImportError:
        return [{"error": "redis package not installed"}]
    
    try:
        r = redis.from_url(REDIS_URL)
        keys = r.keys(pattern)
        return [k.decode() for k in keys]
    except Exception as e:
        return [{"error": str(e)}]


# ============================================
# ROUTER
# ============================================

def route(action: str, target: str, **kwargs) -> list[dict] | dict:
    """Route to appropriate database handler."""
    
    sql = kwargs.get("sql")
    table = kwargs.get("table")
    key = kwargs.get("key")
    value = kwargs.get("value")
    ttl = kwargs.get("ttl")
    pattern = kwargs.get("pattern", "*")
    
    if target in ("supabase", "postgres"):
        if action == "query":
            if not sql:
                return [{"error": "sql required"}]
            return postgres_query(sql)
        elif action == "tables":
            return postgres_tables()
        elif action == "describe":
            if not table:
                return [{"error": "table required"}]
            return postgres_describe(table)
        else:
            return [{"error": f"Unknown action for {target}: {action}"}]
    
    elif target == "redis":
        if action == "get":
            if not key:
                return [{"error": "key required"}]
            return [redis_get(key)]
        elif action == "set":
            if not key or not value:
                return [{"error": "key and value required"}]
            return [redis_set(key, value, ttl)]
        elif action == "keys":
            return redis_keys(pattern)
        else:
            return [{"error": f"Unknown action for redis: {action}"}]
    
    else:
        return [{"error": f"Unknown target: {target}"}]


def format_results(results, action: str) -> str:
    """Format results for display."""
    
    if isinstance(results, dict):
        results = [results]
    
    if not results:
        return "No results."
    
    if "error" in results[0]:
        return f"❌ Error: {results[0]['error']}"
    
    output = [f"📊 Results ({len(results)} rows)", "=" * 50]
    
    if action == "tables":
        for row in results:
            output.append(f"  {row.get('table_schema', 'public')}.{row.get('table_name')}")
    elif action == "describe":
        for row in results:
            nullable = "NULL" if row.get("is_nullable") == "YES" else "NOT NULL"
            output.append(f"  {row.get('column_name'):20} {row.get('data_type'):15} {nullable}")
    else:
        output.append(json.dumps(results[:10], indent=2, default=str))
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Database Master Tool")
    parser.add_argument("action", choices=["query", "tables", "describe", "get", "set", "keys"])
    parser.add_argument("target", choices=["supabase", "postgres", "redis"])
    parser.add_argument("--sql", help="SQL query")
    parser.add_argument("--table", help="Table name")
    parser.add_argument("--key", help="Redis key")
    parser.add_argument("--value", help="Redis value")
    parser.add_argument("--ttl", type=int, help="Redis TTL in seconds")
    parser.add_argument("--pattern", default="*", help="Redis key pattern")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    results = route(
        action=args.action,
        target=args.target,
        sql=args.sql,
        table=args.table,
        key=args.key,
        value=args.value,
        ttl=args.ttl,
        pattern=args.pattern,
    )
    
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_results(results, args.action))


if __name__ == "__main__":
    main()
