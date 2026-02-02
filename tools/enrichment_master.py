#!/usr/bin/env python3
"""
Enrichment Master Tool - Lead and company data enrichment.

Consolidates: apollo, apify

Usage:
    python3 tools/enrichment_master.py <action> <provider> [query] [options]

⚠️ REQUIRES API KEYS - Costs money per request!
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Load env
def load_env():
    env_file = Path.home() / ".config/agency-os/.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    value = value.strip().strip('"').strip("'")
                    os.environ[key.strip()] = value

load_env()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

# ============================================
# APOLLO
# ============================================

def apollo_people_search(query: str = None, domain: str = None, title: str = None, limit: int = 10) -> list[dict]:
    """Search people via Apollo API."""
    
    if not APOLLO_API_KEY:
        return [{"error": "APOLLO_API_KEY not set. This is a PAID API."}]
    
    url = "https://api.apollo.io/v1/mixed_people/search"
    
    payload = {
        "api_key": APOLLO_API_KEY,
        "per_page": limit,
    }
    
    if query:
        payload["q_keywords"] = query
    if domain:
        payload["q_organization_domains"] = domain
    if title:
        payload["person_titles"] = [title]
    
    try:
        req = Request(url, method="POST",
                      data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
        
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        results = []
        for person in data.get("people", []):
            results.append({
                "name": person.get("name"),
                "title": person.get("title"),
                "company": person.get("organization", {}).get("name"),
                "email": person.get("email"),
                "linkedin": person.get("linkedin_url"),
            })
        
        return results
    except HTTPError as e:
        return [{"error": f"Apollo API error: {e.code}"}]


def apollo_company_search(domain: str) -> dict:
    """Get company info via Apollo."""
    
    if not APOLLO_API_KEY:
        return {"error": "APOLLO_API_KEY not set"}
    
    url = "https://api.apollo.io/v1/organizations/enrich"
    payload = {"api_key": APOLLO_API_KEY, "domain": domain}
    
    try:
        req = Request(url, method="POST",
                      data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json"})
        
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
        
        org = data.get("organization", {})
        return {
            "name": org.get("name"),
            "domain": org.get("primary_domain"),
            "industry": org.get("industry"),
            "employees": org.get("estimated_num_employees"),
            "linkedin": org.get("linkedin_url"),
            "description": org.get("short_description"),
        }
    except HTTPError as e:
        return {"error": f"Apollo API error: {e.code}"}


# ============================================
# APIFY
# ============================================

def apify_run_actor(actor_id: str, input_data: dict) -> dict:
    """Run an Apify actor."""
    
    if not APIFY_API_KEY:
        return {"error": "APIFY_API_KEY not set. This is a PAID API."}
    
    url = f"https://api.apify.com/v2/acts/{actor_id}/runs?token={APIFY_API_KEY}"
    
    try:
        req = Request(url, method="POST",
                      data=json.dumps(input_data).encode(),
                      headers={"Content-Type": "application/json"})
        
        with urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode())
        
        return {
            "runId": data.get("data", {}).get("id"),
            "status": data.get("data", {}).get("status"),
            "note": "Use apify_get_results with runId to fetch results",
        }
    except HTTPError as e:
        return {"error": f"Apify API error: {e.code}"}


def apify_get_results(run_id: str) -> list[dict]:
    """Get results from Apify run."""
    
    if not APIFY_API_KEY:
        return [{"error": "APIFY_API_KEY not set"}]
    
    url = f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?token={APIFY_API_KEY}"
    
    try:
        req = Request(url)
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except HTTPError as e:
        return [{"error": f"Apify API error: {e.code}"}]


# ============================================
# ROUTER
# ============================================

def route(action: str, provider: str, **kwargs) -> list[dict] | dict:
    """Route to appropriate enrichment handler."""
    
    query = kwargs.get("query")
    domain = kwargs.get("domain")
    title = kwargs.get("title")
    limit = kwargs.get("limit", 10)
    actor_id = kwargs.get("actor_id")
    run_id = kwargs.get("run_id")
    
    if provider == "apollo":
        if action == "people":
            return apollo_people_search(query, domain, title, limit)
        elif action == "company":
            if not domain:
                return [{"error": "domain required for company lookup"}]
            return [apollo_company_search(domain)]
        else:
            return [{"error": f"Unknown action for apollo: {action}"}]
    
    elif provider == "apify":
        if action == "run":
            if not actor_id:
                return [{"error": "actor_id required"}]
            return [apify_run_actor(actor_id, kwargs.get("input", {}))]
        elif action == "results":
            if not run_id:
                return [{"error": "run_id required"}]
            return apify_get_results(run_id)
        else:
            return [{"error": f"Unknown action for apify: {action}"}]
    
    else:
        return [{"error": f"Unknown provider: {provider}"}]


def main():
    parser = argparse.ArgumentParser(description="Enrichment Master Tool")
    parser.add_argument("action", choices=["people", "company", "run", "results"])
    parser.add_argument("provider", choices=["apollo", "apify"])
    parser.add_argument("--query", "-q", help="Search query")
    parser.add_argument("--domain", "-d", help="Company domain")
    parser.add_argument("--title", "-t", help="Job title filter")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--actor-id", help="Apify actor ID")
    parser.add_argument("--run-id", help="Apify run ID")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    print("⚠️  WARNING: These APIs cost money. Ensure you have permission.")
    
    results = route(
        action=args.action,
        provider=args.provider,
        query=args.query,
        domain=args.domain,
        title=args.title,
        limit=args.limit,
        actor_id=args.actor_id,
        run_id=args.run_id,
    )
    
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
