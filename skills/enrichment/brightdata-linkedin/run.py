#!/usr/bin/env python3
"""
Bright Data LinkedIn Skill - Main execution logic
"""
import os
import asyncio
import sys
import aiohttp
import json
from typing import Dict, Optional
from urllib.parse import quote

# LinkedIn dataset ID
LINKEDIN_DATASET_ID = "gd_l1vikfnt1wgvvqz95w"


async def linkedin_profile_lookup(profile_url: str) -> Optional[Dict]:
    """
    Extract LinkedIn profile data using Bright Data API.
    
    Args:
        profile_url: LinkedIn profile or company URL
        
    Returns:
        Profile data dictionary or None if extraction failed
    """
    api_key = os.getenv("BRIGHTDATA_API_KEY")
    if not api_key:
        raise ValueError("BRIGHTDATA_API_KEY environment variable is required")
    
    # Bright Data API endpoint for LinkedIn dataset
    endpoint = f"https://api.brightdata.com/datasets/v3/{LINKEDIN_DATASET_ID}/snapshot"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Request payload for LinkedIn profile extraction
    payload = {
        "url": profile_url,
        "format": "json"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return normalize_linkedin_data(data, profile_url)
                elif response.status == 401:
                    raise ValueError("Invalid Bright Data API key")
                elif response.status == 429:
                    raise ValueError("Rate limit exceeded - please wait before retrying")
                else:
                    print(f"API request failed with status {response.status}")
                    response_text = await response.text()
                    print(f"Response: {response_text}")
                    return None
                    
        except aiohttp.ClientError as e:
            print(f"Network error during LinkedIn profile lookup: {e}")
            return None
        except Exception as e:
            print(f"Error during LinkedIn profile lookup: {e}")
            return None


def normalize_linkedin_data(raw_data: Dict, profile_url: str) -> Dict:
    """
    Normalize raw Bright Data LinkedIn response into standard format.
    
    Args:
        raw_data: Raw response from Bright Data API
        profile_url: Original profile URL requested
        
    Returns:
        Normalized profile data dictionary
    """
    if not raw_data:
        return {
            "profile_url": profile_url,
            "status": "not_found"
        }
    
    # Handle both company and personal profiles
    if isinstance(raw_data, list) and len(raw_data) > 0:
        profile = raw_data[0]
    else:
        profile = raw_data
    
    # Normalize common fields
    normalized = {
        "profile_url": profile_url,
        "status": "found",
        "name": profile.get("name") or profile.get("company_name"),
        "headline": profile.get("headline") or profile.get("tagline"),
        "location": profile.get("location"),
        "industry": profile.get("industry"),
        "website": profile.get("website"),
        "description": profile.get("description") or profile.get("about"),
    }
    
    # Company-specific fields
    if "company_size" in profile:
        normalized.update({
            "company_size": profile.get("company_size"),
            "founded": profile.get("founded_year"),
            "specialties": profile.get("specialties", []),
            "employees_count": profile.get("employee_count"),
            "follower_count": profile.get("followers"),
        })
    
    # Personal profile fields
    if "experience" in profile:
        normalized.update({
            "experience": profile.get("experience", []),
            "education": profile.get("education", []),
            "skills": profile.get("skills", []),
            "connections": profile.get("connection_count"),
        })
    
    # Remove None values
    return {k: v for k, v in normalized.items() if v is not None}


async def main():
    """Command line interface for LinkedIn profile lookup."""
    import argparse
    
    parser = argparse.ArgumentParser(description="LinkedIn Profile Lookup Tool")
    parser.add_argument("url", help="LinkedIn profile or company URL")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    try:
        result = await linkedin_profile_lookup(args.url)
        
        if result:
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(result, f, indent=2)
                print(f"Results saved to {args.output}")
            else:
                print(json.dumps(result, indent=2))
        else:
            print("No data extracted from LinkedIn profile")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())