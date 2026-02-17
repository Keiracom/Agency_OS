#!/usr/bin/env python3
"""
Hunter Email Verification Skill - Main execution logic

Free plan: 50 searches/cycle, resets 2026-03-07
"""
import os
import asyncio
import sys
import aiohttp
import json
from typing import Dict, List, Optional
from urllib.parse import quote


async def verify_domain(domain: str) -> Optional[Dict]:
    """
    Verify domain and find associated emails using Hunter.io API.
    
    Args:
        domain: Domain to verify and search (e.g., "mustardcreative.com.au")
        
    Returns:
        Domain verification and email discovery results
    """
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        raise ValueError("HUNTER_API_KEY environment variable is required")
    
    # Hunter.io domain search endpoint
    endpoint = "https://api.hunter.io/v2/domain-search"
    
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 10  # Limit results to conserve API quota
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return normalize_hunter_domain_data(data, domain)
                elif response.status == 401:
                    raise ValueError("Invalid Hunter.io API key")
                elif response.status == 429:
                    raise ValueError("API rate limit exceeded - monthly quota exhausted")
                elif response.status == 400:
                    response_data = await response.json()
                    error_msg = response_data.get('errors', [{}])[0].get('details', 'Bad request')
                    raise ValueError(f"Invalid request: {error_msg}")
                else:
                    print(f"API request failed with status {response.status}")
                    response_text = await response.text()
                    print(f"Response: {response_text}")
                    return None
                    
        except aiohttp.ClientError as e:
            print(f"Network error during domain verification: {e}")
            return None
        except Exception as e:
            print(f"Error during domain verification: {e}")
            return None


async def find_emails(domain: str, limit: int = 10) -> List[Dict]:
    """
    Find email addresses for a specific domain.
    
    Args:
        domain: Domain to search
        limit: Maximum number of emails to return
        
    Returns:
        List of email records
    """
    result = await verify_domain(domain)
    if result and result.get("emails"):
        return result["emails"][:limit]
    return []


async def verify_email(email: str) -> Optional[Dict]:
    """
    Verify a specific email address using Hunter.io.
    
    Args:
        email: Email address to verify
        
    Returns:
        Email verification result
    """
    api_key = os.getenv("HUNTER_API_KEY")
    if not api_key:
        raise ValueError("HUNTER_API_KEY environment variable is required")
    
    # Hunter.io email verifier endpoint
    endpoint = "https://api.hunter.io/v2/email-verifier"
    
    params = {
        "email": email,
        "api_key": api_key
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return normalize_hunter_email_data(data, email)
                elif response.status == 401:
                    raise ValueError("Invalid Hunter.io API key")
                elif response.status == 429:
                    raise ValueError("API rate limit exceeded - monthly quota exhausted")
                else:
                    print(f"Email verification failed with status {response.status}")
                    return None
                    
        except Exception as e:
            print(f"Error verifying email {email}: {e}")
            return None


def normalize_hunter_domain_data(raw_data: Dict, domain: str) -> Dict:
    """
    Normalize raw Hunter.io domain search response.
    
    Args:
        raw_data: Raw response from Hunter.io API
        domain: Original domain searched
        
    Returns:
        Normalized domain data dictionary
    """
    if not raw_data or 'data' not in raw_data:
        return {
            "domain": domain,
            "status": "not_found",
            "emails": []
        }
    
    data = raw_data['data']
    
    normalized = {
        "domain": domain,
        "status": "found",
        "disposable": data.get('disposable', False),
        "webmail": data.get('webmail', False),
        "accept_all": data.get('accept_all', False),
        "pattern": data.get('pattern'),
        "organization": data.get('organization'),
        "country": data.get('country'),
        "state": data.get('state'),
        "emails": [],
        "sources": []
    }
    
    # Normalize email results
    for email in data.get('emails', []):
        normalized_email = {
            "value": email.get('value'),
            "type": email.get('type'),  # generic, personal
            "confidence": email.get('confidence'),
            "first_name": email.get('first_name'),
            "last_name": email.get('last_name'),
            "position": email.get('position'),
            "department": email.get('department'),
            "linkedin": email.get('linkedin'),
            "twitter": email.get('twitter'),
            "phone_number": email.get('phone_number'),
            "verification": {
                "date": email.get('verification', {}).get('date'),
                "status": email.get('verification', {}).get('status')
            }
        }
        
        # Remove None values
        normalized_email = {k: v for k, v in normalized_email.items() if v is not None}
        normalized['emails'].append(normalized_email)
    
    # Normalize sources
    for source in data.get('sources', []):
        normalized_source = {
            "domain": source.get('domain'),
            "uri": source.get('uri'),
            "extracted_on": source.get('extracted_on'),
            "last_seen_on": source.get('last_seen_on')
        }
        
        normalized_source = {k: v for k, v in normalized_source.items() if v is not None}
        normalized['sources'].append(normalized_source)
    
    return normalized


def normalize_hunter_email_data(raw_data: Dict, email: str) -> Dict:
    """Normalize Hunter.io email verification response."""
    if not raw_data or 'data' not in raw_data:
        return {"email": email, "status": "unknown"}
    
    data = raw_data['data']
    
    return {
        "email": email,
        "status": data.get('status'),  # valid, invalid, accept_all, unknown
        "result": data.get('result'),
        "score": data.get('score'),
        "regexp": data.get('regexp'),
        "gibberish": data.get('gibberish'),
        "disposable": data.get('disposable'),
        "webmail": data.get('webmail'),
        "mx_records": data.get('mx_records', False),
        "smtp_server": data.get('smtp_server', False),
        "smtp_check": data.get('smtp_check', False),
        "accept_all": data.get('accept_all', False),
        "block": data.get('block', False)
    }


async def main():
    """Command line interface for Hunter email verification."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hunter Email Verification Tool")
    parser.add_argument("--domain", help="Domain to verify and search")
    parser.add_argument("--email", help="Specific email to verify")
    parser.add_argument("--limit", type=int, default=10, help="Max emails to return")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    if not args.domain and not args.email:
        print("Error: Must specify either --domain or --email")
        sys.exit(1)
    
    try:
        if args.domain:
            result = await verify_domain(args.domain)
            if result:
                print(f"Domain verification for {args.domain}:")
                print(f"  Organization: {result.get('organization', 'N/A')}")
                print(f"  Pattern: {result.get('pattern', 'N/A')}")
                print(f"  Emails found: {len(result.get('emails', []))}")
                
                if args.output:
                    with open(args.output, 'w') as f:
                        json.dump(result, f, indent=2)
                    print(f"Results saved to {args.output}")
            else:
                print(f"No data found for domain {args.domain}")
        
        if args.email:
            result = await verify_email(args.email)
            if result:
                print(f"Email verification for {args.email}:")
                print(f"  Status: {result.get('status', 'N/A')}")
                print(f"  Score: {result.get('score', 'N/A')}")
                print(f"  Valid format: {not result.get('gibberish', True)}")
            else:
                print(f"Could not verify email {args.email}")
                
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())