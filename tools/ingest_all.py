#!/usr/bin/env python3
"""
Full Project Ingest Tool - Recursively scan and ingest all text files.

Authorization: Dave (2026-02-02) - UNRESTRICTED KNOWLEDGE INGEST

Usage:
    python3 tools/ingest_all.py [--root /path] [--dry-run]
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
from psycopg2.extras import Json

# ============================================
# CONFIG
# ============================================

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

DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")
if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

# Directories to skip
SKIP_DIRS = {
    '.git', 'node_modules', '__pycache__', '.next', 'out', 
    '.venv', 'venv', 'env', '.cache', 'dist', 'build',
    '.pytest_cache', '.mypy_cache', '.ruff_cache',
    'coverage', '.coverage', 'htmlcov',
}

# Binary/skip extensions
SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.webp', '.svg',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.exe', '.dll', '.so', '.dylib',
    '.pyc', '.pyo', '.whl', '.egg',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.ttf', '.woff', '.woff2', '.eot',
    '.db', '.sqlite', '.sqlite3',
    '.lock',  # package-lock.json handled separately
}

# Extension to type mapping
EXTENSION_TYPE_MAP = {
    # Documentation
    '.md': 'documentation',
    '.txt': 'documentation',
    '.rst': 'documentation',
    
    # Code - Python
    '.py': 'code_python',
    
    # Code - JavaScript/TypeScript
    '.js': 'code_javascript',
    '.jsx': 'code_javascript',
    '.ts': 'code_typescript',
    '.tsx': 'code_typescript',
    
    # Code - Web
    '.html': 'code_html',
    '.css': 'code_css',
    '.scss': 'code_css',
    '.less': 'code_css',
    
    # Config
    '.json': 'config',
    '.yaml': 'config',
    '.yml': 'config',
    '.toml': 'config',
    '.ini': 'config',
    '.cfg': 'config',
    '.conf': 'config',
    '.env': 'config_sensitive',
    
    # Shell
    '.sh': 'code_shell',
    '.bash': 'code_shell',
    '.zsh': 'code_shell',
    
    # SQL
    '.sql': 'code_sql',
    
    # Other
    '.xml': 'config',
    '.csv': 'data',
}

# Sensitive filename patterns
SENSITIVE_PATTERNS = ['.env', 'key', 'secret', 'credential', 'token', 'password', 'auth']


def get_file_type(filepath: Path) -> str:
    """Determine file type based on extension and name."""
    ext = filepath.suffix.lower()
    name = filepath.name.lower()
    
    # Check for special files
    if name in ('dockerfile', 'makefile', 'procfile'):
        return 'config'
    if name.startswith('.env'):
        return 'config_sensitive'
    if name in ('readme.md', 'changelog.md', 'contributing.md'):
        return 'documentation'
    
    return EXTENSION_TYPE_MAP.get(ext, 'unknown')


def is_sensitive(filepath: Path) -> bool:
    """Check if file contains sensitive data."""
    name = filepath.name.lower()
    return any(pattern in name for pattern in SENSITIVE_PATTERNS)


def should_skip_dir(dirname: str) -> bool:
    """Check if directory should be skipped."""
    return dirname in SKIP_DIRS or dirname.startswith('.')


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    ext = filepath.suffix.lower()
    name = filepath.name.lower()
    
    # Skip binary extensions
    if ext in SKIP_EXTENSIONS:
        return True
    
    # Skip package-lock (too large, no value)
    if name == 'package-lock.json':
        return True
    
    # Skip if no extension and not a known special file
    if not ext and name not in ('dockerfile', 'makefile', 'procfile', '.gitignore', '.dockerignore'):
        return True
    
    return False


def compute_hash(content: str) -> str:
    """Compute content hash for deduplication."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def scan_directory(root: Path) -> list[dict]:
    """Recursively scan directory for files to ingest."""
    files = []
    
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories (modifies in-place)
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        
        for filename in filenames:
            filepath = Path(dirpath) / filename
            
            if should_skip_file(filepath):
                continue
            
            try:
                # Try to read as text
                content = filepath.read_text(encoding='utf-8', errors='ignore')
                
                # Skip empty files
                if not content.strip():
                    continue
                
                # Skip very large files (>500KB)
                if len(content) > 500_000:
                    print(f"⚠️ Skipping large file: {filepath} ({len(content)} bytes)")
                    continue
                
                rel_path = filepath.relative_to(root)
                file_type = get_file_type(filepath)
                sensitive = is_sensitive(filepath)
                
                files.append({
                    'path': str(rel_path),
                    'content': content,
                    'type': file_type,
                    'sensitive': sensitive,
                    'size': len(content),
                    'hash': compute_hash(content),
                })
                
            except Exception as e:
                print(f"⚠️ Error reading {filepath}: {e}")
                continue
    
    return files


def ingest_to_database(files: list[dict], dry_run: bool = False) -> dict:
    """Insert files into elliot_internal.memories."""
    
    if dry_run:
        return {
            'total': len(files),
            'inserted': 0,
            'skipped': 0,
            'dry_run': True,
        }
    
    print(f"📥 Connecting to database...", flush=True)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print(f"✅ Connected. Ingesting {len(files)} files...", flush=True)
    
    inserted = 0
    skipped = 0
    total = len(files)
    
    for i, file in enumerate(files):
        # Build metadata
        metadata = {
            'source': 'file_ingest',
            'path': file['path'],
            'ingested_at': datetime.now(timezone.utc).isoformat(),
        }
        
        if file['sensitive']:
            metadata['sensitivity'] = 'high'
        
        # Build content with path header
        content = f"FILE: {file['path']}\nTYPE: {file['type']}\n\n{file['content']}"
        
        # Truncate if too long (keep first 50K chars)
        if len(content) > 50_000:
            content = content[:50_000] + "\n\n[TRUNCATED]"
        
        # Check for existing content (by path in metadata)
        cur.execute("""
            SELECT id FROM elliot_internal.memories 
            WHERE metadata->>'path' = %s AND deleted_at IS NULL
        """, (file['path'],))
        
        if cur.fetchone():
            skipped += 1
            continue
        
        try:
            # Note: content_hash is a generated column, don't insert into it
            cur.execute("""
                INSERT INTO elliot_internal.memories 
                (content, type, metadata)
                VALUES (%s, %s, %s)
            """, (content, file['type'], Json(metadata)))
            inserted += 1
            
            # Progress every 100 files
            if inserted % 100 == 0:
                conn.commit()  # Commit in batches
                print(f"   Progress: {i+1}/{total} processed, {inserted} inserted", flush=True)
                
        except Exception as e:
            print(f"⚠️ Error inserting {file['path']}: {e}", flush=True)
            conn.rollback()
            continue
    
    conn.commit()
    cur.close()
    conn.close()
    
    return {
        'total': len(files),
        'inserted': inserted,
        'skipped': skipped,
        'dry_run': False,
    }


def main():
    parser = argparse.ArgumentParser(description="Full Project Ingest Tool")
    parser.add_argument("--root", default="/home/elliotbot/clawd", 
                        help="Root directory to scan")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scan only, don't insert")
    
    args = parser.parse_args()
    
    root = Path(args.root)
    
    if not root.exists():
        print(f"❌ Root directory not found: {root}", flush=True)
        sys.exit(1)
    
    print(f"🔍 Scanning: {root}", flush=True)
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'LIVE INGEST'}", flush=True)
    print("=" * 60, flush=True)
    
    # Scan
    files = scan_directory(root)
    
    # Group by type for summary
    by_type = {}
    for f in files:
        t = f['type']
        by_type[t] = by_type.get(t, 0) + 1
    
    print(f"\n📊 Files Found: {len(files)}")
    for t, count in sorted(by_type.items()):
        sensitive_count = sum(1 for f in files if f['type'] == t and f['sensitive'])
        sens_str = f" (🔒 {sensitive_count} sensitive)" if sensitive_count else ""
        print(f"   {t}: {count}{sens_str}")
    
    # Ingest
    print("\n" + "=" * 60)
    result = ingest_to_database(files, args.dry_run)
    
    print(f"\n✅ Ingest Complete")
    print(f"   Total scanned: {result['total']}")
    print(f"   Inserted: {result['inserted']}")
    print(f"   Skipped (duplicates): {result['skipped']}")
    
    if not args.dry_run:
        print("\n⚠️ Run embedding flow to vectorize new memories:")
        print("   python3 orchestration/flows/maintenance/embed_memories.py")


if __name__ == "__main__":
    main()
