#!/usr/bin/env python3
"""
ABN Lookup Enrichment Skill
Usage: python run.py --abn "33051775556" OR --name "Company Name" [--state "VIC"]
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.integrations.abn_client import get_abn_client


async def main(abn: str = None, name: str = None, state: str = None):
    client = get_abn_client()

    if abn:
        # Clean ABN (remove spaces)
        abn_clean = abn.replace(" ", "")
        result = await client.search_by_abn(abn_clean)
    elif name:
        results = await client.search_by_name(name, state=state)
        result = results[0] if results else {"found": False, "error": "No match found"}
    else:
        print("Error: Must provide --abn or --name")
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ABN Lookup Enrichment")
    parser.add_argument("--abn", help="ABN to lookup (11 digits)")
    parser.add_argument("--name", help="Company name to search")
    parser.add_argument("--state", help="State code (NSW, VIC, etc.)")
    args = parser.parse_args()

    if not args.abn and not args.name:
        parser.error("Must provide either --abn or --name")

    asyncio.run(main(args.abn, args.name, args.state))
