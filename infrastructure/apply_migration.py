#!/usr/bin/env python3
"""
Apply Supabase migrations using the service key.

Usage:
    python apply_migration.py <migration_file>
    python apply_migration.py 002_scoring_columns.sql
"""

import os
import sys
from pathlib import Path

from supabase import create_client, Client


def get_supabase_client() -> Client:
    """Create Supabase client with service key for admin operations."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not url:
        raise ValueError("SUPABASE_URL environment variable not set")
    if not key:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")
    
    return create_client(url, key)


def apply_migration(migration_path: str) -> None:
    """Apply a SQL migration file to Supabase."""
    path = Path(migration_path)
    
    # Handle relative paths - check migrations directory
    if not path.exists():
        migrations_dir = Path(__file__).parent / "migrations"
        path = migrations_dir / migration_path
    
    if not path.exists():
        raise FileNotFoundError(f"Migration file not found: {migration_path}")
    
    sql = path.read_text()
    print(f"Applying migration: {path.name}")
    print("-" * 50)
    
    client = get_supabase_client()
    
    # Execute the migration via RPC
    # Using the postgres function for raw SQL execution
    try:
        result = client.rpc("exec_sql", {"query": sql}).execute()
        print(f"✓ Migration applied successfully")
        if result.data:
            print(f"Result: {result.data}")
    except Exception as e:
        # If exec_sql doesn't exist, try direct postgrest approach
        # or inform user to run via SQL editor
        error_msg = str(e)
        if "exec_sql" in error_msg or "function" in error_msg.lower():
            print(f"Note: exec_sql RPC not available.")
            print(f"Please run the migration directly in Supabase SQL Editor:")
            print(f"\n{sql}\n")
            print(f"Or use: supabase db push (if using Supabase CLI)")
        else:
            raise


def main():
    if len(sys.argv) < 2:
        # Default to the scoring columns migration
        migration_file = "002_scoring_columns.sql"
    else:
        migration_file = sys.argv[1]
    
    try:
        apply_migration(migration_file)
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
