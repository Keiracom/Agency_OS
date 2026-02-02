#!/usr/bin/env python3
"""
Run the Elliot Brain migration and migrate MEMORY.md
"""
import os
import sys
import json
import hashlib
from pathlib import Path

# Load environment
env_file = Path.home() / ".config/agency-os/.env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, _, value = line.partition('=')
                # Remove quotes if present
                value = value.strip().strip('"').strip("'")
                os.environ[key.strip()] = value

import psycopg2
from psycopg2.extras import Json

# Get database URL (use the migrations one for DDL - port 5432)
DATABASE_URL = os.getenv("DATABASE_URL_MIGRATIONS") or os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found")
    sys.exit(1)

# Convert asyncpg URL to psycopg2 format if needed
DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

print("🔌 Connecting to Supabase...")

try:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    print("✅ Connected to database")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

# ============================================
# STEP 1: RUN SCHEMA MIGRATION
# ============================================
print("\n🏗️  Running schema migration...")

migration_file = Path(__file__).parent / "001_elliot_brain.sql"
with open(migration_file) as f:
    sql = f.read()

try:
    cur.execute(sql)
    print("✅ Schema migration complete")
except Exception as e:
    if "already exists" in str(e).lower():
        print("⚠️  Some objects already exist (continuing...)")
    else:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

# ============================================
# STEP 2: MIGRATE MEMORY.md
# ============================================
print("\n🧠 Migrating MEMORY.md...")

workspace = Path("/home/elliotbot/clawd")
memory_file = workspace / "MEMORY.md"

if memory_file.exists():
    with open(memory_file, encoding="utf-8") as f:
        content = f.read()
    
    # Parse sections from MEMORY.md
    sections = []
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('## '):
            if current_section:
                sections.append({
                    'section': current_section,
                    'content': '\n'.join(current_content).strip()
                })
            current_section = line[3:].strip()
            current_content = []
        else:
            current_content.append(line)
    
    # Don't forget the last section
    if current_section:
        sections.append({
            'section': current_section,
            'content': '\n'.join(current_content).strip()
        })
    
    # Insert each section as a memory
    inserted = 0
    for section in sections:
        if not section['content']:
            continue
            
        try:
            cur.execute("""
                INSERT INTO elliot_internal.memories (content, type, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                section['content'],
                'core_fact',
                Json({
                    'source_file': 'MEMORY.md',
                    'section': section['section'],
                    'migrated_at': 'now()'
                })
            ))
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  Failed to insert section '{section['section']}': {e}")
    
    print(f"✅ Migrated {inserted} sections from MEMORY.md")
else:
    print("⚠️  MEMORY.md not found at expected path")

# ============================================
# STEP 3: MIGRATE DAILY LOGS (last 7 days)
# ============================================
print("\n📅 Migrating recent daily logs...")

daily_dir = workspace / "memory" / "daily"
if daily_dir.exists():
    log_files = sorted(daily_dir.glob("*.md"), reverse=True)[:7]
    
    for log_file in log_files:
        with open(log_file, encoding="utf-8") as f:
            content = f.read()
        
        try:
            cur.execute("""
                INSERT INTO elliot_internal.memories (content, type, metadata)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                content,
                'daily_log',
                Json({
                    'source_file': str(log_file.name),
                    'date': log_file.stem,
                    'migrated_at': 'now()'
                })
            ))
            print(f"  ✅ {log_file.name}")
        except Exception as e:
            print(f"  ⚠️  Failed: {log_file.name}: {e}")
    
    print(f"✅ Migrated {len(log_files)} daily logs")
else:
    print("⚠️  Daily logs directory not found")

# ============================================
# STEP 4: VERIFY
# ============================================
print("\n🔍 Verifying migration...")

cur.execute("SELECT COUNT(*) FROM elliot_internal.memories")
count = cur.fetchone()[0]
print(f"✅ Total memories in database: {count}")

cur.execute("SELECT type, COUNT(*) FROM elliot_internal.memories GROUP BY type")
for row in cur.fetchall():
    print(f"   - {row[0]}: {row[1]}")

# Cleanup
cur.close()
conn.close()

print("\n" + "="*50)
print("✅ MIGRATION COMPLETE")
print("="*50)
print("\nNext steps:")
print("1. Embeddings need to be generated (requires OpenAI API call)")
print("2. Test search_memories function")
print("3. Update Clawdbot config to use vector search")
