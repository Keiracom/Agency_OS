#!/usr/bin/env python3
"""
Scoring Agents
==============
LLM-powered scoring pipeline for knowledge items.

Uses Claude 3 Haiku to score content for:
- Business relevance (Agency OS / B2B sales automation)
- Learning relevance (AI agent improvement)

Then routes to appropriate action types.

Usage:
    python scoring_agents.py                    # Score unscored items
    python scoring_agents.py --limit 50         # Limit batch size
    python scoring_agents.py --dry-run          # Preview without updates
    python scoring_agents.py --reprocess        # Re-score all items
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

import httpx
from supabase import create_client, Client

# Load environment
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# ============================================
# Configuration
# ============================================

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://jatzvazlbusedwsnqxzr.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Model for scoring (cheap + fast)
SCORING_MODEL = "claude-3-haiku-20240307"
MAX_CONCURRENT = 20
DEFAULT_BATCH_SIZE = 100

# ============================================
# Scoring Prompts
# ============================================

BUSINESS_SCORER_PROMPT = """
You are scoring content for relevance to Agency OS - a B2B sales automation platform.

CONTENT:
Title: {title}
Description: {description}
Source: {source}

Score 0-100 for relevance to:
- Cold email automation
- Sales outreach tools
- Lead generation
- B2B prospecting
- CRM/pipeline automation
- Email deliverability
- Competitors (Instantly, Smartlead, Apollo, Lemlist)

Return JSON only:
{{"score": 0-100, "reasoning": "one line"}}
"""

LEARNING_SCORER_PROMPT = """
You are scoring content for relevance to improving AI agent capabilities.

CONTENT:
Title: {title}
Description: {description}
Source: {source}

Score 0-100 for relevance to:
- LLM memory architectures
- Multi-agent orchestration
- Agent planning and reasoning
- Self-improvement patterns
- Tool use by LLMs
- Persistent context
- Reflection loops
- Prompt engineering

Return JSON only:
{{"score": 0-100, "reasoning": "one line"}}
"""

ACTION_ROUTER_PROMPT = """
Given these scores, determine the action type:

Title: {title}
Business Score: {business_score}
Learning Score: {learning_score}

Action types:
- evaluate_tool: It's a tool/library we might use
- research: Deep dive topic, extract insights
- absorb: Prompt pattern or technique to learn
- competitive_intel: Competitor information
- skip: Not actionable

Return JSON only:
{{"action_type": "...", "reasoning": "one line"}}
"""

# ============================================
# Data Classes
# ============================================

@dataclass
class ScoringResult:
    """Result from scoring a knowledge item."""
    item_id: str
    business_score: int
    business_reasoning: str
    learning_score: int
    learning_reasoning: str
    action_type: str
    action_reasoning: str
    combined_score: float  # For relevance_score field

    def to_metadata_update(self) -> dict:
        """Convert to metadata dict for DB update."""
        return {
            "scoring": {
                "business_score": self.business_score,
                "business_reasoning": self.business_reasoning,
                "learning_score": self.learning_score,
                "learning_reasoning": self.learning_reasoning,
                "action_type": self.action_type,
                "action_reasoning": self.action_reasoning,
                "scored_at": datetime.now(timezone.utc).isoformat(),
            }
        }


# ============================================
# Anthropic API Client
# ============================================

class AnthropicScorer:
    """Async client for Claude scoring."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()
    
    async def score(self, prompt: str) -> dict:
        """Call Claude API and parse JSON response."""
        if not self.client:
            raise RuntimeError("Client not initialized. Use async with.")
        
        try:
            response = await self.client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": SCORING_MODEL,
                    "max_tokens": 256,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["content"][0]["text"]
            
            # Parse JSON from response
            # Handle potential markdown wrapping
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
            
        except httpx.HTTPStatusError as e:
            print(f"  ⚠ API error: {e.response.status_code}")
            return {"score": 0, "reasoning": f"API error: {e.response.status_code}"}
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON parse error: {e}")
            return {"score": 0, "reasoning": "Failed to parse response"}
        except Exception as e:
            print(f"  ⚠ Scoring error: {e}")
            return {"score": 0, "reasoning": str(e)}


# ============================================
# Database Functions
# ============================================

def get_supabase_client() -> Client:
    """Get Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_unscored_items(client: Client, limit: int = DEFAULT_BATCH_SIZE, reprocess: bool = False) -> list:
    """Fetch knowledge items that haven't been scored yet."""
    query = client.table("elliot_knowledge").select("*")
    
    if not reprocess:
        # Items without scoring in metadata
        # We check for items where metadata->scoring is null
        query = query.or_("metadata.is.null,metadata->scoring.is.null")
    
    query = query.is_("deleted_at", "null")
    query = query.order("learned_at", desc=True)
    query = query.limit(limit)
    
    result = query.execute()
    return result.data if result.data else []


def update_item_scores(client: Client, item_id: str, result: ScoringResult) -> bool:
    """Update a knowledge item with scoring results."""
    try:
        # Get current metadata
        current = client.table("elliot_knowledge").select("metadata").eq("id", item_id).single().execute()
        current_metadata = current.data.get("metadata") or {}
        
        # Merge scoring into metadata
        updated_metadata = {**current_metadata, **result.to_metadata_update()}
        
        # Update item
        client.table("elliot_knowledge").update({
            "metadata": updated_metadata,
            "relevance_score": result.combined_score,
        }).eq("id", item_id).execute()
        
        return True
    except Exception as e:
        print(f"  ⚠ DB update error for {item_id}: {e}")
        return False


# ============================================
# Scoring Pipeline
# ============================================

async def score_item(scorer: AnthropicScorer, item: dict) -> Optional[ScoringResult]:
    """Score a single knowledge item with both scorers."""
    item_id = item["id"]
    title = item.get("summary") or item.get("content", "")[:200]
    description = item.get("content", "")
    source = item.get("source_type", "unknown")
    source_url = item.get("source_url", "")
    
    if source_url:
        source = f"{source} ({source_url})"
    
    # Run business and learning scorers in parallel
    business_prompt = BUSINESS_SCORER_PROMPT.format(
        title=title,
        description=description[:500],
        source=source,
    )
    learning_prompt = LEARNING_SCORER_PROMPT.format(
        title=title,
        description=description[:500],
        source=source,
    )
    
    business_result, learning_result = await asyncio.gather(
        scorer.score(business_prompt),
        scorer.score(learning_prompt),
    )
    
    business_score = business_result.get("score", 0)
    learning_score = learning_result.get("score", 0)
    
    # Route to action type
    action_prompt = ACTION_ROUTER_PROMPT.format(
        title=title,
        business_score=business_score,
        learning_score=learning_score,
    )
    action_result = await scorer.score(action_prompt)
    
    # Calculate combined score (weighted average)
    combined_score = round((business_score * 0.6 + learning_score * 0.4) / 100, 2)
    
    return ScoringResult(
        item_id=item_id,
        business_score=business_score,
        business_reasoning=business_result.get("reasoning", ""),
        learning_score=learning_score,
        learning_reasoning=learning_result.get("reasoning", ""),
        action_type=action_result.get("action_type", "skip"),
        action_reasoning=action_result.get("reasoning", ""),
        combined_score=combined_score,
    )


async def run_scoring_pipeline(
    limit: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
    reprocess: bool = False,
) -> dict:
    """
    Main scoring pipeline.
    
    Called by Elliot on command.
    1. Query unscored items
    2. Score each with both scorers (parallel)
    3. Route action type
    4. Update DB
    5. Return summary
    
    Args:
        limit: Maximum items to process
        dry_run: If True, don't update DB
        reprocess: If True, re-score already scored items
    
    Returns:
        dict with summary statistics
    """
    print("\n" + "=" * 60)
    print("  SCORING PIPELINE")
    print("=" * 60 + "\n")
    
    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set")
        return {"error": "Missing API key", "processed": 0}
    
    # Fetch items
    client = get_supabase_client()
    print(f"📥 Fetching {'all' if reprocess else 'unscored'} items (limit: {limit})...")
    items = fetch_unscored_items(client, limit, reprocess)
    
    if not items:
        print("✅ No items to score")
        return {"processed": 0, "message": "No unscored items"}
    
    print(f"📋 Found {len(items)} items to score\n")
    
    # Track results
    results = {
        "processed": 0,
        "successful": 0,
        "failed": 0,
        "by_action_type": {},
        "high_business": [],  # score >= 70
        "high_learning": [],  # score >= 70
    }
    
    # Process in batches of MAX_CONCURRENT
    async with AnthropicScorer(ANTHROPIC_API_KEY) as scorer:
        for i in range(0, len(items), MAX_CONCURRENT):
            batch = items[i:i + MAX_CONCURRENT]
            batch_num = i // MAX_CONCURRENT + 1
            total_batches = (len(items) + MAX_CONCURRENT - 1) // MAX_CONCURRENT
            
            print(f"🔄 Processing batch {batch_num}/{total_batches} ({len(batch)} items)...")
            
            # Score items in parallel
            tasks = [score_item(scorer, item) for item in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for item, result in zip(batch, batch_results):
                results["processed"] += 1
                
                if isinstance(result, Exception):
                    print(f"  ❌ {item['id'][:8]}... - Error: {result}")
                    results["failed"] += 1
                    continue
                
                if result is None:
                    results["failed"] += 1
                    continue
                
                # Log result
                title_short = (item.get("summary") or item.get("content", ""))[:40]
                print(f"  ✓ {title_short}...")
                print(f"    Business: {result.business_score} | Learning: {result.learning_score} → {result.action_type}")
                
                # Track by action type
                results["by_action_type"][result.action_type] = \
                    results["by_action_type"].get(result.action_type, 0) + 1
                
                # Track high scorers
                if result.business_score >= 70:
                    results["high_business"].append({
                        "id": item["id"],
                        "title": title_short,
                        "score": result.business_score,
                    })
                if result.learning_score >= 70:
                    results["high_learning"].append({
                        "id": item["id"],
                        "title": title_short,
                        "score": result.learning_score,
                    })
                
                # Update DB
                if not dry_run:
                    if update_item_scores(client, item["id"], result):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1
                else:
                    results["successful"] += 1
            
            # Small delay between batches to avoid rate limiting
            if i + MAX_CONCURRENT < len(items):
                await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "-" * 40)
    print("📊 SCORING SUMMARY")
    print("-" * 40)
    print(f"  Processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"\n  By Action Type:")
    for action, count in sorted(results["by_action_type"].items()):
        print(f"    {action}: {count}")
    
    if results["high_business"]:
        print(f"\n  🎯 High Business Relevance ({len(results['high_business'])}):")
        for item in results["high_business"][:5]:
            print(f"    [{item['score']}] {item['title']}")
    
    if results["high_learning"]:
        print(f"\n  🧠 High Learning Relevance ({len(results['high_learning'])}):")
        for item in results["high_learning"][:5]:
            print(f"    [{item['score']}] {item['title']}")
    
    if dry_run:
        print("\n  ⚠️  DRY RUN - No database updates made")
    
    print()
    return results


async def run_full_pipeline(limit: int = DEFAULT_BATCH_SIZE, dry_run: bool = False):
    """
    Run scoring pipeline then trigger action engine.
    """
    # Run scoring
    results = await run_scoring_pipeline(limit=limit, dry_run=dry_run)
    
    if results.get("successful", 0) > 0 and not dry_run:
        # Trigger action engine to process high-value items
        print("\n🚀 Triggering Action Engine...")
        try:
            from infrastructure.action_engine import process_pending_knowledge
            action_results = process_pending_knowledge()
            print(f"   Action engine processed {action_results.get('processed', 0)} items")
            results["action_engine"] = action_results
        except Exception as e:
            print(f"   ⚠️ Action engine error: {e}")
            results["action_engine_error"] = str(e)
    
    return results


# ============================================
# CLI
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Score knowledge items with LLM agents")
    parser.add_argument("--limit", type=int, default=DEFAULT_BATCH_SIZE, 
                        help=f"Max items to process (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview scoring without DB updates")
    parser.add_argument("--reprocess", action="store_true",
                        help="Re-score already scored items")
    parser.add_argument("--full", action="store_true",
                        help="Run scoring + action engine")
    args = parser.parse_args()
    
    if args.full:
        results = asyncio.run(run_full_pipeline(
            limit=args.limit,
            dry_run=args.dry_run,
        ))
    else:
        results = asyncio.run(run_scoring_pipeline(
            limit=args.limit,
            dry_run=args.dry_run,
            reprocess=args.reprocess,
        ))
    
    # Exit with error code if failures
    if results.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
