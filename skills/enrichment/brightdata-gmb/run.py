#!/usr/bin/env python3
"""
Bright Data GMB Skill - Main execution logic

This replaces the deprecated DIY GMB scraper (src/integrations/gmb_scraper.py).
Uses Bright Data Google Maps SERP API for business searches.
Cost: $0.0015/request vs $0.006/lead DIY scraper (75% reduction).
"""
import os
import asyncio
import sys
import aiohttp
import json
from typing import List, Dict, Optional


async def gmb_search(query: str, location: str = None) -> List[Dict]:
    """
    Search Google Maps for businesses using Bright Data SERP API.
    
    Args:
        query: Search query (e.g., "marketing agency")
        location: Optional location filter (e.g., "Melbourne")
        
    Returns:
        List of business records from Google Maps
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
    
    # Construct search query
    search_query = query
    if location:
        search_query = f"{query} {location}"
    
    # Bright Data Google Maps SERP API endpoint
    endpoint = "https://api.brightdata.com/serp/google_maps"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": search_query,
        "location": location or "Australia",
        "language": "en",
        "format": "json",
        "limit": 20  # Maximum results per request
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return normalize_gmb_results(data, query, location)
                elif response.status == 401:
                    raise ValueError("Invalid Bright Data API key")
                elif response.status == 429:
                    raise ValueError("Rate limit exceeded - please wait before retrying")
                else:
                    print(f"API request failed with status {response.status}")
                    response_text = await response.text()
                    print(f"Response: {response_text}")
                    return []
                    
        except aiohttp.ClientError as e:
            print(f"Network error during GMB search: {e}")
            return []
        except Exception as e:
            print(f"Error during GMB search: {e}")
            return []


def normalize_gmb_results(raw_data: Dict, query: str, location: str = None) -> List[Dict]:
    """
    Normalize raw Bright Data Google Maps response into standard format.
    
    Args:
        raw_data: Raw response from Bright Data API
        query: Original search query
        location: Original location filter
        
    Returns:
        List of normalized business records
    """
    if not raw_data or 'results' not in raw_data:
        return []
    
    normalized_results = []
    
    for business in raw_data.get('results', []):
        normalized = {
            "name": business.get("title") or business.get("name"),
            "title": business.get("title"),
            "address": business.get("address"),
            "phone": business.get("phone"),
            "website": business.get("website") or business.get("url"),
            "rating": business.get("rating"),
            "reviews_count": business.get("reviews_count") or business.get("num_reviews"),
            "category": business.get("category") or business.get("type"),
            "place_id": business.get("place_id") or business.get("gid"),
            "hours": business.get("hours") or business.get("opening_hours"),
            "description": business.get("snippet") or business.get("description"),
            "latitude": business.get("latitude") or business.get("lat"),
            "longitude": business.get("longitude") or business.get("lng"),
            "price_range": business.get("price_range"),
            "thumbnail": business.get("thumbnail"),
        }
        
        # Clean up the data
        normalized = {k: v for k, v in normalized.items() if v is not None}
        
        # Add metadata
        normalized["search_query"] = query
        normalized["search_location"] = location
        normalized["source"] = "bright_data_gmb"
        
        if normalized.get("name"):  # Only include businesses with names
            normalized_results.append(normalized)
    
    return normalized_results


async def gmb_search_with_fallbacks(business_name: str, location: str = "Australia") -> List[Dict]:
    """
    Search Google Maps with multiple fallback strategies.
    
    This mimics the waterfall approach of the deprecated DIY scraper
    but uses Bright Data API for all searches.
    
    Args:
        business_name: Business name to search for
        location: Location to search in
        
    Returns:
        List of business records, empty if no matches found
    """
    search_strategies = [
        business_name,  # Exact name
        f'"{business_name}"',  # Quoted exact match
        f"{business_name} {location}",  # Name with location
        business_name.replace(" Pty Ltd", "").replace(" Ltd", ""),  # Strip legal suffixes
    ]
    
    for strategy in search_strategies:
        print(f"Trying search strategy: {strategy}")
        results = await gmb_search(strategy, location)
        
        if results:
            print(f"Found {len(results)} results with strategy: {strategy}")
            return results
    
    print("No results found with any search strategy")
    return []


async def main():
    """Command line interface for GMB search."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Google Maps Business Search Tool")
    parser.add_argument("query", help="Search query (e.g., 'marketing agency')")
    parser.add_argument("--location", help="Location filter (e.g., 'Melbourne')")
    parser.add_argument("--output", help="Output file path (optional)")
    parser.add_argument("--fallbacks", action="store_true", help="Use fallback search strategies")
    
    args = parser.parse_args()
    
    try:
        if args.fallbacks:
            results = await gmb_search_with_fallbacks(args.query, args.location or "Australia")
        else:
            results = await gmb_search(args.query, args.location)
        
        if results:
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Found {len(results)} businesses, saved to {args.output}")
            else:
                print(f"Found {len(results)} businesses:")
                for business in results:
                    print(f"  {business['name']} - {business.get('address', 'No address')}")
        else:
            print("No businesses found")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())