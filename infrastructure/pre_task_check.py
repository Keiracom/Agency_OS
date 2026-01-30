#!/usr/bin/env python3
"""
Pre-Task Knowledge Check
========================
Retrieves relevant tools and knowledge for a given task description.
Used by Elliot before executing tasks to ensure proper tooling.

Usage:
    python pre_task_check.py "build landing page from video"
    python pre_task_check.py "analyze codebase structure"
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Optional

# Add parent to path to avoid import conflicts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.expanduser("~/.config/agency-os/.env"))

# ============================================
# Configuration
# ============================================

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")


def get_db_connection():
    """Get PostgreSQL connection."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set")
    return psycopg2.connect(DATABASE_URL)


# ============================================
# Knowledge Retrieval
# ============================================

def search_tools_by_keyword(keywords: list[str], max_results: int = 10) -> list[dict]:
    """
    Search for tools matching any of the keywords.
    
    Args:
        keywords: List of keywords to search for
        max_results: Maximum results to return
    
    Returns:
        List of matching tool records
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build OR conditions for keywords
    conditions = []
    params = []
    for kw in keywords:
        conditions.append("(content ILIKE %s OR summary ILIKE %s OR %s = ANY(tags))")
        params.extend([f"%{kw}%", f"%{kw}%", kw.lower()])
    
    where_clause = " OR ".join(conditions) if conditions else "TRUE"
    
    query = f"""
        SELECT 
            id, category, content, summary, confidence_score, 
            tags, metadata, learned_at
        FROM elliot_knowledge
        WHERE deleted_at IS NULL 
        AND category = 'tool_discovery'
        AND ({where_clause})
        ORDER BY confidence_score DESC, learned_at DESC
        LIMIT %s
    """
    params.append(max_results)
    
    cur.execute(query, params)
    columns = ['id', 'category', 'content', 'summary', 'confidence_score', 'tags', 'metadata', 'learned_at']
    results = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return results


def get_all_tools() -> list[dict]:
    """Get all tools from knowledge base."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            id, category, content, summary, confidence_score, 
            tags, metadata, learned_at
        FROM elliot_knowledge
        WHERE deleted_at IS NULL 
        AND category = 'tool_discovery'
        ORDER BY confidence_score DESC
    """)
    
    columns = ['id', 'category', 'content', 'summary', 'confidence_score', 'tags', 'metadata', 'learned_at']
    results = [dict(zip(columns, row)) for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return results


def extract_keywords(task: str) -> list[str]:
    """Extract relevant keywords from task description."""
    # Common domain keywords to look for
    domain_keywords = {
        'video': ['video', 'mp4', 'avi', 'movie', 'clip', 'recording', 'footage'],
        'audio': ['audio', 'mp3', 'wav', 'sound', 'music'],
        'codebase': ['codebase', 'code', 'repository', 'repo', 'project', 'analyze'],
        'frontend': ['frontend', 'ui', 'landing', 'page', 'website', 'react', 'html'],
        'scraping': ['scrape', 'scraping', 'crawl', 'trends', 'twitter', 'social'],
        'processing': ['processing', 'convert', 'transform', 'extract'],
        'ai': ['ai', 'llm', 'gpt', 'claude', 'generate'],
    }
    
    task_lower = task.lower()
    keywords = set()
    
    for domain, terms in domain_keywords.items():
        for term in terms:
            if term in task_lower:
                keywords.add(domain)
                keywords.add(term)
    
    # Add individual words from task
    for word in task_lower.split():
        if len(word) > 3 and word.isalpha():
            keywords.add(word)
    
    return list(keywords)


def get_relevant_tools(task: str) -> dict:
    """
    Get tools relevant to a task description.
    
    Args:
        task: Task description
    
    Returns:
        Dict with relevant tools and formatted output
    """
    keywords = extract_keywords(task)
    
    # Search for tools
    tools = search_tools_by_keyword(keywords) if keywords else get_all_tools()
    
    # Score tools by relevance
    scored_tools = []
    for tool in tools:
        score = 0
        tool_text = (tool.get('content', '') + ' ' + tool.get('summary', '')).lower()
        tags = [t.lower() for t in (tool.get('tags') or [])]
        metadata = tool.get('metadata') or {}
        use_cases = [u.lower() for u in metadata.get('use_cases', [])]
        
        for kw in keywords:
            if kw in tool_text:
                score += 1
            if kw in tags:
                score += 2  # Tags are more specific
            for uc in use_cases:
                if kw in uc:
                    score += 3  # Use cases are most specific
        
        if score > 0:
            scored_tools.append((score, tool))
    
    # Sort by score
    scored_tools.sort(reverse=True, key=lambda x: x[0])
    
    return {
        'task': task,
        'keywords': keywords,
        'tools': [t[1] for t in scored_tools],
        'match_scores': {t[1].get('metadata', {}).get('tool_name', 'unknown'): t[0] for t in scored_tools}
    }


def format_for_injection(result: dict) -> str:
    """Format results for prompt injection."""
    lines = [
        "## 🔧 Relevant Tools for This Task",
        ""
    ]
    
    if not result['tools']:
        lines.append("No specific tools found. Using general knowledge.")
        return "\n".join(lines)
    
    for tool in result['tools']:
        metadata = tool.get('metadata', {})
        tool_name = metadata.get('tool_name', 'Unknown')
        summary = tool.get('summary', '')
        
        lines.append(f"### {tool_name}")
        lines.append(f"*{summary}*")
        lines.append("")
        lines.append(tool.get('content', ''))
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


# ============================================
# CLI
# ============================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python pre_task_check.py <task_description>")
        print("\nExamples:")
        print('  python pre_task_check.py "build landing page from video"')
        print('  python pre_task_check.py "analyze codebase structure"')
        sys.exit(1)
    
    task = " ".join(sys.argv[1:])
    
    print(f"🔍 Analyzing task: {task}")
    print("-" * 50)
    
    result = get_relevant_tools(task)
    
    print(f"\n📋 Keywords extracted: {result['keywords']}")
    print(f"🛠️  Tools found: {len(result['tools'])}")
    
    if result['tools']:
        print(f"\n📊 Match scores:")
        for name, score in result['match_scores'].items():
            print(f"   - {name}: {score}")
    
    print("\n" + "=" * 50)
    print("FORMATTED FOR INJECTION:")
    print("=" * 50)
    print(format_for_injection(result))
    
    # Also output JSON for programmatic use
    if '--json' in sys.argv:
        print("\n" + "=" * 50)
        print("JSON OUTPUT:")
        print("=" * 50)
        # Convert non-serializable types
        output = {
            'task': result['task'],
            'keywords': result['keywords'],
            'tools': [
                {
                    'id': str(t['id']),
                    'name': t.get('metadata', {}).get('tool_name', 'unknown'),
                    'summary': t.get('summary', ''),
                    'tags': t.get('tags', []),
                    'confidence': t.get('confidence_score', 0)
                }
                for t in result['tools']
            ],
            'match_scores': result['match_scores']
        }
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
