#!/usr/bin/env python3
"""
#300-TEST: ContactOut vs Forager provider test
Tests both providers against 10 AU DM LinkedIn URLs.
API keys read from environment only — never hardcoded.
"""

import json
import os
import time
import requests
from pathlib import Path

# API keys from environment
CONTACTOUT_API_KEY = os.environ.get("CONTACTOUT_API_KEY")
FORAGER_API_KEY = os.environ.get("FORAGER_API_KEY")

if not CONTACTOUT_API_KEY:
    raise ValueError("CONTACTOUT_API_KEY not set in environment")
if not FORAGER_API_KEY:
    raise ValueError("FORAGER_API_KEY not set in environment")

print(f"ContactOut key: {CONTACTOUT_API_KEY[:8]}...")
print(f"Forager key: {FORAGER_API_KEY[:8]}...")

# Load data
data_path = Path(__file__).parent / "output" / "300f_dm.json"
data = json.load(open(data_path))
domains = data["domains"]

# Pick 10: mix of dental, construction, legal
with_li = [d for d in domains if d.get("dm_linkedin_url") and d.get("dm_found")]
dental = [d for d in with_li if d.get("category") == "Dental"][:4]
construction = [d for d in with_li if d.get("category") == "Construction"][:3]
legal = [d for d in with_li if d.get("category") == "Legal"][:3]
sample = dental + construction + legal
print(f"\nSelected {len(sample)} leads: {len(dental)} dental, {len(construction)} construction, {len(legal)} legal")


def call_contactout(linkedin_url: str) -> dict:
    start = time.time()
    try:
        resp = requests.get(
            "https://api.contactout.com/v1/people/linkedin",
            params={"profile": linkedin_url, "include_phone": "true"},
            headers={"Authorization": f"token {CONTACTOUT_API_KEY}"},
            timeout=15,
        )
        ms = int((time.time() - start) * 1000)
        print(f"  ContactOut status: {resp.status_code} ({ms}ms)")
        if resp.status_code == 200:
            body = resp.json()
            profile = body.get("profile", {})
            emails = profile.get("emails", [])
            phones = profile.get("phones", profile.get("phone_numbers", []))
            email = emails[0] if emails else None
            phone = phones[0] if phones else None
            return {
                "email_found": bool(email),
                "email": email,
                "mobile_found": bool(phone),
                "mobile": phone,
                "response_time_ms": ms,
                "error": None,
            }
        else:
            return {
                "email_found": False,
                "email": None,
                "mobile_found": False,
                "mobile": None,
                "response_time_ms": ms,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        return {
            "email_found": False,
            "email": None,
            "mobile_found": False,
            "mobile": None,
            "response_time_ms": ms,
            "error": str(e),
        }


def call_forager(linkedin_url: str) -> dict:
    start = time.time()
    try:
        # Forager API v2 — try enrich endpoint with bearer token
        resp = requests.post(
            "https://api.forager.ai/v1/enrich",
            json={"linkedin_url": linkedin_url},
            headers={
                "Authorization": f"Bearer {FORAGER_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        ms = int((time.time() - start) * 1000)
        print(f"  Forager status: {resp.status_code} ({ms}ms)")
        if resp.status_code == 200:
            body = resp.json()
            # Try common field patterns
            email = (
                body.get("email")
                or body.get("work_email")
                or body.get("personal_email")
                or (body.get("emails", [None])[0] if body.get("emails") else None)
            )
            phone = (
                body.get("phone")
                or body.get("mobile")
                or body.get("mobile_phone")
                or (body.get("phones", [None])[0] if body.get("phones") else None)
            )
            return {
                "email_found": bool(email),
                "email": email,
                "mobile_found": bool(phone),
                "mobile": phone,
                "response_time_ms": ms,
                "error": None,
                "_raw": body,
            }
        else:
            return {
                "email_found": False,
                "email": None,
                "mobile_found": False,
                "mobile": None,
                "response_time_ms": ms,
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }
    except Exception as e:
        ms = int((time.time() - start) * 1000)
        return {
            "email_found": False,
            "email": None,
            "mobile_found": False,
            "mobile": None,
            "response_time_ms": ms,
            "error": str(e),
        }


# Run tests
results = []
for i, lead in enumerate(sample, 1):
    li_url = lead["dm_linkedin_url"]
    name = lead.get("dm_name", "unknown")
    cat = lead.get("category", "unknown")
    print(f"\n[{i}/10] {name} ({cat})")
    print(f"  URL: {li_url}")

    co_result = call_contactout(li_url)
    fo_result = call_forager(li_url)

    # Strip _raw from output (keep clean)
    fo_clean = {k: v for k, v in fo_result.items() if k != "_raw"}

    results.append(
        {
            "linkedin_url": li_url,
            "category": cat,
            "dm_name": name,
            "contactout": co_result,
            "forager": fo_clean,
        }
    )

# Save
out_path = Path(__file__).parent / "output" / "300_provider_test.json"
out_path.parent.mkdir(exist_ok=True)
json.dump(results, open(out_path, "w"), indent=2)
print(f"\n\nResults saved to {out_path}")

# ---- REPORT ----
print("\n" + "=" * 60)
print("REPORT: ContactOut vs Forager — 10 AU LinkedIn URLs")
print("=" * 60)

for provider in ["contactout", "forager"]:
    emails = sum(1 for r in results if r[provider]["email_found"])
    mobiles = sum(1 for r in results if r[provider]["mobile_found"])
    both = sum(1 for r in results if r[provider]["email_found"] and r[provider]["mobile_found"])
    neither = sum(1 for r in results if not r[provider]["email_found"] and not r[provider]["mobile_found"])
    avg_ms = sum(r[provider]["response_time_ms"] for r in results) / len(results)
    errors = [r[provider]["error"] for r in results if r[provider]["error"]]

    print(f"\n--- {provider.upper()} ---")
    print(f"Emails found:  {emails}/10")
    print(f"Mobiles found: {mobiles}/10")
    print(f"Both found:    {both}/10")
    print(f"Neither found: {neither}/10")
    print(f"Avg response:  {avg_ms:.0f}ms")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")

print("\n--- ALL 10 RESULTS (LAW XIV) ---")
print(json.dumps(results, indent=2))
