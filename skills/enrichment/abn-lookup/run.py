#!/usr/bin/env python3
"""
ABN Lookup Skill - Main execution logic
"""
import os
import asyncio
import sys
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.integrations.abn_client import ABNClient


async def abn_lookup(abn: str) -> Optional[Dict]:
    """
    Look up business details by ABN.
    
    Args:
        abn: Australian Business Number (11 digits)
        
    Returns:
        Business record dictionary or None if not found
    """
    auth_guid = os.getenv("ABN_LOOKUP_GUID")
    if not auth_guid:
        raise ValueError("ABN_LOOKUP_GUID environment variable is required")
    
    async with ABNClient(auth_guid) as client:
        return await client.lookup_by_abn(abn)


async def abn_search_by_name(
    name: str,
    state: str = None,
    postcode: str = None,
    active_only: bool = True,
    entity_types: List[str] = None
) -> List[Dict]:
    """
    Search ABN by business name.
    
    Args:
        name: Business name to search
        state: State code (NSW, VIC, QLD, etc.)
        postcode: Postcode filter
        active_only: Only return active ABNs
        entity_types: Filter by entity type codes (PRV, PUB, IND, etc.)
        
    Returns:
        List of business records matching search criteria
    """
    auth_guid = os.getenv("ABN_LOOKUP_GUID")
    if not auth_guid:
        raise ValueError("ABN_LOOKUP_GUID environment variable is required")
    
    # Default entity types exclude trusts and super funds
    if entity_types is None:
        entity_types = ["PRV", "PUB", "IND"]
    
    async with ABNClient(auth_guid) as client:
        return await client.search_by_name(
            name=name,
            state=state,
            postcode=postcode,
            active_only=active_only,
            entity_type_code=entity_types
        )


async def main():
    """Command line interface for ABN lookup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ABN Lookup Tool")
    parser.add_argument("--abn", help="ABN to lookup (11 digits)")
    parser.add_argument("--name", help="Business name to search")
    parser.add_argument("--state", help="State code filter")
    parser.add_argument("--postcode", help="Postcode filter")
    parser.add_argument("--include-inactive", action="store_true", help="Include inactive ABNs")
    
    args = parser.parse_args()
    
    if not args.abn and not args.name:
        print("Error: Must specify either --abn or --name")
        sys.exit(1)
    
    try:
        if args.abn:
            result = await abn_lookup(args.abn)
            if result:
                print(f"Found ABN {args.abn}:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
            else:
                print(f"ABN {args.abn} not found")
        
        if args.name:
            results = await abn_search_by_name(
                name=args.name,
                state=args.state,
                postcode=args.postcode,
                active_only=not args.include_inactive
            )
            
            print(f"Found {len(results)} results for '{args.name}':")
            for result in results:
                print(f"  ABN: {result.get('abn', 'N/A')}")
                print(f"  Name: {result.get('entity_name', 'N/A')}")
                print(f"  Type: {result.get('entity_type_name', 'N/A')}")
                print(f"  Status: {result.get('status', 'N/A')}")
                print()
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())