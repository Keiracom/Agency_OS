#!/usr/bin/env python3
"""
Smart Knowledge Injection
Queries Supabase for relevant tools/knowledge based on context.
Returns formatted markdown for injection (~100-200 tokens max).

Must be run with the infrastructure venv:
  /home/elliotbot/clawd/infrastructure/.venv/bin/python3 smart_inject.py "context"
"""

import os
import sys

def load_env():
    """Load environment from .env file."""
    env_path = os.path.expanduser('~/.config/agency-os/.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v.strip('"').strip("'")

def get_relevant_knowledge(limit: int = 4) -> str:
    """Query Supabase for recent high-confidence knowledge."""
    
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        return ""
    
    try:
        from supabase import create_client
        client = create_client(url, key)
        
        result = client.table('elliot_knowledge') \
            .select('category, summary, content, source_type') \
            .gte('confidence_score', 0.5) \
            .order('learned_at', desc=True) \
            .limit(limit) \
            .execute()
        
        if not result.data:
            return ""
        
        lines = ["## 🧠 Recent Knowledge (auto-injected, ~100 tokens)"]
        for item in result.data:
            summary = item.get('summary') or item.get('content', '')[:80]
            category = item.get('category', 'general')
            lines.append(f"- [{category}] {summary}")
        
        return '\n'.join(lines)
        
    except Exception as e:
        return f"<!-- Knowledge query error: {str(e)[:50]} -->"


def get_tool_index() -> str:
    """Get the minimal tools index."""
    index_path = os.path.expanduser('~/clawd/knowledge/tools/_index.md')
    if os.path.exists(index_path):
        with open(index_path) as f:
            return f.read()
    return ""


def main():
    load_env()
    
    parts = []
    
    # Always include tool index (~50 tokens)
    tool_index = get_tool_index()
    if tool_index:
        parts.append(tool_index)
    
    # Add recent knowledge from Supabase (~100 tokens)
    knowledge = get_relevant_knowledge()
    if knowledge:
        parts.append(knowledge)
    
    if parts:
        print('\n\n'.join(parts))


if __name__ == '__main__':
    main()
