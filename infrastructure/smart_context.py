#!/usr/bin/env python3
"""
Smart Context Retrieval for Mid-Session Hook

1. Extract keywords from message (regex, free)
2. Search Supabase knowledge (free)
3. If not found → Brave web search (free API)
4. Store new knowledge in Supabase (grows over time)
5. Return formatted context (~100-200 tokens)

Zero Claude API cost.
"""

import os
import sys
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Load environment
def load_env():
    env_path = os.path.expanduser('~/.config/agency-os/.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v.strip('"').strip("'")

load_env()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY')


def extract_keywords(message: str) -> list[str]:
    """Extract meaningful keywords from message."""
    # Remove common words
    stopwords = {'i', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 
                 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
                 'into', 'through', 'during', 'before', 'after', 'above', 'below',
                 'between', 'under', 'again', 'further', 'then', 'once', 'here',
                 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few',
                 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                 'and', 'but', 'if', 'or', 'because', 'until', 'while', 'this',
                 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
                 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his',
                 'she', 'her', 'it', 'its', 'they', 'them', 'their', 'want',
                 'like', 'get', 'make', 'know', 'think', 'see', 'look', 'use'}
    
    # Extract words
    words = re.findall(r'\b[a-zA-Z]{3,}\b', message.lower())
    
    # Filter and deduplicate
    keywords = list(set(w for w in words if w not in stopwords))
    
    return keywords[:10]  # Limit to 10 keywords


def search_supabase(keywords: list[str]) -> list[dict]:
    """Search Supabase for relevant knowledge."""
    if not SUPABASE_URL or not SUPABASE_KEY or not keywords:
        return []
    
    all_results = []
    
    try:
        # Search for each keyword individually
        for kw in keywords[:5]:
            encoded_kw = urllib.parse.quote(f"%{kw}%")
            url = f"{SUPABASE_URL}/rest/v1/elliot_knowledge?content=ilike.{encoded_kw}&select=category,summary,content&limit=3"
            
            req = urllib.request.Request(url, headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}'
            })
            
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                if isinstance(data, list):
                    all_results.extend(data)
        
        # Deduplicate by content
        seen = set()
        unique = []
        for item in all_results:
            content = item.get('content', '')
            if content not in seen:
                seen.add(content)
                unique.append(item)
        
        return unique[:5]
    except Exception as e:
        return []


def brave_search(query: str) -> list[dict]:
    """Search Brave for information."""
    if not BRAVE_API_KEY:
        return []
    
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://api.search.brave.com/res/v1/web/search?q={encoded}&count=3"
        
        req = urllib.request.Request(url, headers={
            'Accept': 'application/json',
            'X-Subscription-Token': BRAVE_API_KEY
        })
        
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            results = data.get('web', {}).get('results', [])
            return [{'title': r.get('title', ''), 
                     'description': r.get('description', ''),
                     'url': r.get('url', '')} 
                    for r in results[:3]]
    except Exception as e:
        return []


def store_knowledge(content: str, source_url: str, category: str = 'general'):
    """Store new knowledge in Supabase."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    
    try:
        data = json.dumps({
            'category': category,
            'content': content[:500],
            'summary': content[:100],
            'source_url': source_url,
            'source_type': 'inference',
            'confidence_score': 0.6
        }).encode()
        
        url = f"{SUPABASE_URL}/rest/v1/elliot_knowledge"
        req = urllib.request.Request(url, data=data, headers={
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }, method='POST')
        
        urllib.request.urlopen(req, timeout=5)
    except:
        pass  # Silent fail on store


def format_context(db_results: list, web_results: list) -> str:
    """Format results for injection."""
    lines = []
    
    if db_results:
        lines.append("## 📚 Relevant Knowledge")
        for item in db_results[:3]:
            summary = item.get('summary') or item.get('content', '')[:80]
            lines.append(f"- {summary}")
    
    if web_results:
        lines.append("## 🔍 Web Search Results")
        for item in web_results[:2]:
            lines.append(f"- {item['title']}: {item['description'][:100]}")
    
    return '\n'.join(lines) if lines else ''


def main():
    if len(sys.argv) < 2:
        return
    
    message = ' '.join(sys.argv[1:])
    
    # 1. Extract keywords
    keywords = extract_keywords(message)
    if not keywords:
        return
    
    # 2. Search Supabase
    db_results = search_supabase(keywords)
    
    # 3. If not found, try Brave search
    web_results = []
    if not db_results:
        query = ' '.join(keywords[:5])
        web_results = brave_search(query)
        
        # 4. Store web results for future
        for result in web_results:
            store_knowledge(
                f"{result['title']}: {result['description']}",
                result['url'],
                'general'
            )
    
    # 5. Format and output
    context = format_context(db_results, web_results)
    if context:
        print(context)


if __name__ == '__main__':
    main()
