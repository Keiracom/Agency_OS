#!/usr/bin/env python3
"""
Full Knowledge Pipeline Trigger
===============================
Master script to run the complete knowledge acquisition and processing pipeline.

Usage:
    python run_knowledge_pipeline.py [--scrape] [--process] [--all]
    python run_knowledge_pipeline.py --scrape          # Run scrapers only
    python run_knowledge_pipeline.py --process         # Run action engine only
    python run_knowledge_pipeline.py --all             # Run both (default)
    python run_knowledge_pipeline.py --dry-run         # Show what would run

Pipeline Steps:
    1. Run learning_scrape_flow (all sources: HN, PH, GitHub, YouTube, Reddit, Twitter)
    2. Run action_engine.py process (create sign-off requests for high-value items)
    3. Report summary

Schedule: Daily at 7am AEST (21:00 UTC previous day)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add infrastructure to path
INFRA_DIR = Path(__file__).parent
sys.path.insert(0, str(INFRA_DIR))

# Load environment
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_summary(title: str, data: dict, indent: int = 0):
    """Print a formatted summary."""
    prefix = "  " * indent
    print(f"{prefix}{title}:")
    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}  {key}:")
            for k, v in value.items():
                print(f"{prefix}    {k}: {v}")
        else:
            print(f"{prefix}  {key}: {value}")


async def run_scrape() -> dict:
    """
    Run the learning scrape flow.
    
    Returns:
        dict with scrape results
    """
    print_header("STEP 1: Running Knowledge Scrapers")
    
    try:
        from prefect_flows.flows.learning_scrape import daily_learning_scrape
        
        print("Starting scrapers...")
        print("  - HackerNews (top + Show HN + Ask HN)")
        print("  - ProductHunt (today's launches)")
        print("  - GitHub Trending (Python, TypeScript, Collections)")
        print("  - YouTube (target channels + AI/SaaS topics)")
        print("  - Reddit (r/SaaS, r/Entrepreneur, r/sales, r/startups, etc.)")
        print("  - Twitter (AI/SaaS topics)")
        print()
        
        # Run the flow
        result = await daily_learning_scrape(
            hn_limit_per_keyword=50,
            gh_limit_per_keyword=15,
            reddit_limit_per_search=50,
            yt_limit_per_keyword=30,
            ph_limit=10,
            twitter_limit_per_keyword=25
        )
        
        print("\n✅ Scrape Complete!")
        print_summary("Results", result)
        
        return {
            "success": True,
            "step": "scrape",
            "result": result
        }
        
    except Exception as e:
        print(f"\n❌ Scrape Failed: {e}")
        return {
            "success": False,
            "step": "scrape",
            "error": str(e)
        }


def run_process() -> dict:
    """
    Run the action engine to process high-value knowledge.
    
    Returns:
        dict with processing results
    """
    print_header("STEP 2: Processing High-Value Knowledge")
    
    try:
        from action_engine import process_new_knowledge
        
        print("Scanning for high-value knowledge items (relevance >= 0.8)...")
        print("Creating sign-off requests for actionable items...")
        print()
        
        # Run the processor
        result = process_new_knowledge()
        
        print("\n✅ Processing Complete!")
        print(f"  Processed: {result.get('processed', 0)} items")
        
        if result.get('signoffs_created'):
            print(f"  Sign-offs created: {len(result['signoffs_created'])}")
            for signoff in result['signoffs_created'][:5]:  # Show first 5
                print(f"    - [{signoff['action_type']}] {signoff['title'][:50]}...")
        
        if result.get('skipped'):
            print(f"  Skipped: {len(result['skipped'])} items")
        
        if result.get('errors'):
            print(f"  Errors: {len(result['errors'])}")
            for err in result['errors'][:3]:
                print(f"    - {err['title'][:40]}: {err['error']}")
        
        return {
            "success": True,
            "step": "process",
            "result": result
        }
        
    except Exception as e:
        print(f"\n❌ Processing Failed: {e}")
        return {
            "success": False,
            "step": "process",
            "error": str(e)
        }


def generate_report(scrape_result: dict, process_result: dict) -> str:
    """
    Generate a summary report of the pipeline run.
    
    Returns:
        Formatted report string
    """
    now = datetime.now(timezone.utc)
    
    report_lines = [
        "",
        "=" * 60,
        "  KNOWLEDGE PIPELINE SUMMARY",
        f"  {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "=" * 60,
        "",
    ]
    
    # Scrape results
    if scrape_result.get("success"):
        sr = scrape_result.get("result", {})
        report_lines.extend([
            "📊 SCRAPE RESULTS:",
            f"   Total scraped: {sr.get('total_scraped', 0)}",
            f"   Unique items: {sr.get('unique', 0)}",
            f"   Stored: {sr.get('stored', 0)}",
            "",
            "   Sources:",
        ])
        for source, count in sr.get("sources", {}).items():
            report_lines.append(f"     - {source}: {count}")
        
        relevance = sr.get("relevance_distribution", {})
        report_lines.extend([
            "",
            "   Relevance Distribution:",
            f"     - High (0.8+): {relevance.get('high', 0)}",
            f"     - Medium (0.5-0.8): {relevance.get('medium', 0)}",
            f"     - Low (<0.5): {relevance.get('low', 0)}",
            "",
        ])
    else:
        report_lines.extend([
            "❌ SCRAPE FAILED:",
            f"   Error: {scrape_result.get('error', 'Unknown')}",
            "",
        ])
    
    # Process results
    if process_result.get("success"):
        pr = process_result.get("result", {})
        report_lines.extend([
            "🎯 PROCESSING RESULTS:",
            f"   High-value items processed: {pr.get('processed', 0)}",
            f"   Sign-off requests created: {len(pr.get('signoffs_created', []))}",
            f"   Items skipped: {len(pr.get('skipped', []))}",
            f"   Errors: {len(pr.get('errors', []))}",
            "",
        ])
        
        if pr.get('signoffs_created'):
            report_lines.append("   Pending Sign-offs:")
            for signoff in pr['signoffs_created'][:5]:
                report_lines.append(f"     • [{signoff['action_type']}] {signoff['title'][:45]}...")
            if len(pr['signoffs_created']) > 5:
                report_lines.append(f"     ... and {len(pr['signoffs_created']) - 5} more")
        report_lines.append("")
    else:
        report_lines.extend([
            "❌ PROCESSING FAILED:",
            f"   Error: {process_result.get('error', 'Unknown')}",
            "",
        ])
    
    # Overall status
    overall_success = scrape_result.get("success") and process_result.get("success")
    status_emoji = "✅" if overall_success else "⚠️"
    report_lines.extend([
        "=" * 60,
        f"  {status_emoji} PIPELINE STATUS: {'SUCCESS' if overall_success else 'PARTIAL FAILURE'}",
        "=" * 60,
        "",
    ])
    
    return "\n".join(report_lines)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Elliot Knowledge Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_knowledge_pipeline.py --all          # Run full pipeline
  python run_knowledge_pipeline.py --scrape       # Scrape only
  python run_knowledge_pipeline.py --process      # Process only
  python run_knowledge_pipeline.py --dry-run      # Show what would run
        """
    )
    
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Run scrapers only"
    )
    parser.add_argument(
        "--process",
        action="store_true",
        help="Run action engine only"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run full pipeline (default)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would run without executing"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    
    args = parser.parse_args()
    
    # Default to --all if nothing specified
    if not args.scrape and not args.process and not args.all:
        args.all = True
    
    # Determine what to run
    run_scrape_step = args.scrape or args.all
    run_process_step = args.process or args.all
    
    if args.dry_run:
        print("\n🔍 DRY RUN - Would execute:")
        if run_scrape_step:
            print("  1. Learning Scrape Flow")
            print("     - HackerNews (top + Show HN + Ask HN)")
            print("     - ProductHunt (today's launches)")
            print("     - GitHub Trending (Python, TypeScript, Collections)")
            print("     - YouTube (target channels + AI/SaaS)")
            print("     - Reddit (r/SaaS, r/Entrepreneur, r/sales, etc.)")
            print("     - Twitter (AI/SaaS topics)")
        if run_process_step:
            print("  2. Action Engine Processing")
            print("     - Scan for high-value knowledge (relevance >= 0.8)")
            print("     - Create sign-off requests")
            print("     - Send Telegram notifications")
        return
    
    start_time = datetime.now(timezone.utc)
    print(f"\n🚀 Starting Knowledge Pipeline at {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    scrape_result = {"success": True, "step": "scrape", "result": {}}
    process_result = {"success": True, "step": "process", "result": {}}
    
    # Run scrape step
    if run_scrape_step:
        scrape_result = await run_scrape()
    
    # Run process step
    if run_process_step:
        process_result = run_process()
    
    # Generate and print report
    if args.json:
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "scrape": scrape_result,
            "process": process_result,
            "success": scrape_result.get("success") and process_result.get("success")
        }
        print(json.dumps(output, indent=2, default=str))
    else:
        report = generate_report(scrape_result, process_result)
        print(report)
        
        duration = datetime.now(timezone.utc) - start_time
        print(f"⏱️  Total duration: {duration.total_seconds():.1f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
