#!/usr/bin/env python3
"""T2 GMB Enrichment Script - Bright Data Web Scraper API"""

import os
import json
import time
import requests
from difflib import SequenceMatcher

API_KEY = os.environ.get("BRIGHTDATA_API_KEY")
DATASET_ID = "gd_m8ebnr0q2qlklc02fz"
BASE_URL = "https://api.brightdata.com/datasets/v3"

STATE_TO_CITY = {
    "NSW": "Sydney",
    "VIC": "Melbourne",
    "QLD": "Brisbane",
    "WA": "Perth",
    "SA": "Adelaide",
    "TAS": "Hobart",
    "ACT": "Canberra",
    "NT": "Darwin",
}


def fuzzy_match(s1, s2):
    """Return similarity ratio between two strings"""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def trigger_collection(company_name, city):
    """Trigger Bright Data collection"""
    url = f"{BASE_URL}/trigger"
    params = {
        "dataset_id": DATASET_ID,
        "type": "discover_new",
        "discover_by": "location",
        "notify": "false",
        "include_errors": "true",
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"input": [{"country": "AU", "keyword": f"{company_name} {city}", "lat": ""}]}

    resp = requests.post(url, params=params, headers=headers, json=payload, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("snapshot_id")
    else:
        print(f"  Trigger error: {resp.status_code} - {resp.text[:200]}")
        return None


def poll_for_completion(snapshot_id, max_wait=180):
    """Poll until snapshot is ready"""
    url = f"{BASE_URL}/progress/{snapshot_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}

    start = time.time()
    while time.time() - start < max_wait:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status")
            if status == "ready":
                return True
            elif status == "failed":
                print(f"  Collection failed: {data}")
                return False
        time.sleep(10)
    print(f"  Timeout waiting for snapshot {snapshot_id}")
    return False


def fetch_results(snapshot_id):
    """Fetch completed results"""
    url = f"{BASE_URL}/snapshot/{snapshot_id}"
    params = {"format": "json"}
    headers = {"Authorization": f"Bearer {API_KEY}"}

    resp = requests.get(url, params=params, headers=headers, timeout=30)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  Fetch error: {resp.status_code}")
        return []


def find_best_match(company_name, results, threshold=0.70):
    """Find best fuzzy match from results"""
    best_match = None
    best_score = 0

    for r in results:
        name = r.get("name", "")
        score = fuzzy_match(company_name, name)
        if score > best_score:
            best_score = score
            best_match = r

    if best_score >= threshold:
        return best_match, best_score
    return None, best_score


def enrich_lead(company_name, city, state):
    """Run full T2 enrichment for a single lead"""
    city = city or STATE_TO_CITY.get(state, "Sydney")

    print(f"\n[GMB] {company_name} ({city}, {state})")

    # Step 1: Trigger
    snapshot_id = trigger_collection(company_name, city)
    if not snapshot_id:
        return None
    print(f"  Snapshot: {snapshot_id}")

    # Step 2: Poll
    if not poll_for_completion(snapshot_id):
        return None

    # Step 3: Fetch
    results = fetch_results(snapshot_id)
    print(f"  Results: {len(results)} businesses found")

    if not results:
        return None

    # Step 4: Match
    match, score = find_best_match(company_name, results)
    if match:
        print(f"  Match: {match.get('name')} (score: {score:.2f})")
        return {
            "name": match.get("name"),
            "phone": match.get("phone_number"),
            "website": match.get("open_website"),
            "address": match.get("address"),
            "category": match.get("category"),
            "rating": match.get("rating"),
            "reviews_count": match.get("reviews_count"),
            "place_id": match.get("place_id"),
            "match_score": score,
        }
    else:
        print(f"  No match found (best score: {score:.2f})")
        return None


if __name__ == "__main__":
    # Test with the 9 leads
    leads = [
        {
            "id": "c98a78de-16ab-430a-b815-e42689d874c7",
            "company_name": "Zeemo",
            "city": "Melbourne",
            "state": "VIC",
        },
        {
            "id": "8b9789f9-8fb9-4054-afd2-e9978013a9a1",
            "company_name": "Think Creative Agency",
            "city": "Sydney",
            "state": "NSW",
        },
        {
            "id": "118a46ae-4bca-485b-8d7b-96952f43b419",
            "company_name": "Defiant Digital",
            "city": "Sydney",
            "state": "NSW",
        },
        {
            "id": "4113220b-6f04-40be-8d1e-92c2810736b3",
            "company_name": "McKenzie Partners",
            "city": "Sydney",
            "state": "NSW",
        },
        {
            "id": "3a470c3f-a856-41ca-a2e1-d0506a8cd0de",
            "company_name": "Nous Company",
            "city": "Brisbane",
            "state": "QLD",
        },
        {
            "id": "f883b096-167f-495d-935b-c0efec6a1157",
            "company_name": "Soak Creative",
            "city": "Brisbane",
            "state": "QLD",
        },
        {
            "id": "d3d2f5c7-50b0-4c28-80a8-d7d7886aa746",
            "company_name": "Nimbl",
            "city": "Melbourne",
            "state": "VIC",
        },
        {
            "id": "78f52075-2ada-4cb7-9e25-1b0de944c2b2",
            "company_name": "LittleBIG Marketing",
            "city": "Melbourne",
            "state": "VIC",
        },
        {
            "id": "e29ef89c-6f5e-4f42-bdb6-e62b63a37b2a",
            "company_name": "Anchor Digital Marketing",
            "city": "Brisbane",
            "state": "QLD",
        },
    ]

    results = []
    for lead in leads:
        result = enrich_lead(lead["company_name"], lead["city"], lead["state"])
        results.append({"id": lead["id"], "company_name": lead["company_name"], "gmb_data": result})

    # Output results
    print("\n" + "=" * 80)
    print("T2 ENRICHMENT RESULTS")
    print("=" * 80)
    for r in results:
        gmb = r["gmb_data"]
        if gmb:
            print(
                f"✅ {r['company_name']}: {gmb.get('phone')} | {gmb.get('rating')} ⭐ | {gmb.get('category')}"
            )
        else:
            print(f"❌ {r['company_name']}: No GMB match")

    # Save results to JSON
    with open("/home/elliotbot/clawd/scripts/t2_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to t2_results.json")
