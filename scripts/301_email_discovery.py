#!/usr/bin/env python3
"""
#301 — Run SMTP email discovery + verification on all 260 DMs.
Reads 300f_dm.json + 300g_email.json, runs discover_and_verify_batch,
saves results to scripts/output/301_email_discovery.json.
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path
from collections import defaultdict

import importlib.util

# Direct import to avoid enrichment __init__.py circular deps
_spec = importlib.util.spec_from_file_location(
    "email_verifier",
    str(Path(__file__).parent.parent / "src" / "enrichment" / "email_verifier.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
discover_and_verify_batch = _mod.discover_and_verify_batch
verify_emails = _mod.verify_emails

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

dm_data = json.load(open(OUTPUT_DIR / "300f_dm.json"))
domains_300f = {d["domain"]: d for d in dm_data["domains"] if d.get("dm_found")}

email_data = json.load(open(OUTPUT_DIR / "300g_email.json"))
email_map = {d["domain"]: d for d in email_data["domains"]}

# ---------------------------------------------------------------------------
# Build prospect list
# ---------------------------------------------------------------------------

def split_name(full_name: str) -> tuple[str, str]:
    """Split 'First Last' into (first, last). Handles multi-word names."""
    if not full_name:
        return "", ""
    parts = full_name.strip().split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


prospects = []
for domain, dm in domains_300f.items():
    first, last = split_name(dm.get("dm_name", ""))
    email_entry = email_map.get(domain, {})
    existing_email = email_entry.get("email") if email_entry.get("email_found") else None

    # Strip www. for clean domain
    clean_domain = re.sub(r"^www\.", "", domain)

    prospects.append({
        "domain": clean_domain,
        "original_domain": domain,
        "category": dm.get("category", "unknown"),
        "dm_name": dm.get("dm_name", ""),
        "first_name": first,
        "last_name": last,
        "existing_email": existing_email,
        "email_source": email_entry.get("email_source", "none"),
        "email_verified": email_entry.get("email_verified", False),
    })

print(f"Total prospects: {len(prospects)}")
with_existing = [p for p in prospects if p["existing_email"]]
without_email = [p for p in prospects if not p["existing_email"]]
print(f"  With existing email: {len(with_existing)}")
print(f"  Without email: {len(without_email)}")

# ---------------------------------------------------------------------------
# Run batch
# ---------------------------------------------------------------------------

t0 = time.time()
print(f"\nRunning discover_and_verify_batch on {len(prospects)} prospects...")
print("(sem=20 concurrent, ~10s timeout per connection)\n")

results = asyncio.run(discover_and_verify_batch(prospects))

total_time = time.time() - t0
print(f"\nCompleted in {total_time:.1f}s")

# ---------------------------------------------------------------------------
# Process results
# ---------------------------------------------------------------------------

output = []
pattern_hits = defaultdict(int)

PATTERN_NAMES = [
    "first", "last", "first.last", "last.first",
    "firstlast", "lastfirst", "f.last", "flast",
    "first.l", "first_last", "f_last", "first-last", "f-last",
]

stats = {
    "domains_tested": len(results),
    "no_mx": 0,
    "accept_all": 0,
    "smtp_error": 0,
    "verified_dm_email": 0,
    "existing_verified": 0,
    "no_valid_email": 0,
    "company_email_verified": 0,
}

for r in results:
    smtp = r.get("smtp_result", {})
    existing = r.get("existing_email")
    verified_list = smtp.get("verified_emails", [])
    domain = r["domain"]
    first = r["first_name"].lower()
    last = r["last_name"].lower()
    f = first[:1]

    # Classify result
    smtp_error = smtp.get("error")
    if smtp.get("mx_host") is None:
        stats["no_mx"] += 1
    elif smtp.get("accept_all"):
        stats["accept_all"] += 1
    elif smtp_error and not verified_list:
        stats["smtp_error"] += 1

    # Which pattern verified?
    dm_email_found = None
    company_email_found = None
    for email in verified_list:
        local = email.split("@")[0].lower()
        # Check if it matches a DM pattern
        expected_locals = [
            first, last,
            f"{first}.{last}", f"{last}.{first}",
            f"{first}{last}", f"{last}{first}",
            f"{f}.{last}", f"{f}{last}",
            f"{first}.{last[:1]}",
            f"{first}_{last}", f"{f}_{last}",
            f"{first}-{last}", f"{f}-{last}",
        ]
        if local in expected_locals:
            if dm_email_found is None:
                dm_email_found = email
            # Track which pattern
            for pname, exp in zip(PATTERN_NAMES, expected_locals):
                if local == exp:
                    pattern_hits[pname] += 1
                    break
        elif any(local.startswith(p) for p in ("info", "contact", "admin", "hello", "office", "reception", "enquiries", "enquiry")):
            company_email_found = email

    if dm_email_found:
        stats["verified_dm_email"] += 1
    if company_email_found:
        stats["company_email_verified"] += 1

    # Verify existing email
    existing_now_verified = False
    if existing and existing in verified_list:
        stats["existing_verified"] += 1
        existing_now_verified = True

    if not dm_email_found and not company_email_found and not existing_now_verified:
        if not smtp.get("accept_all") and smtp.get("mx_host"):
            stats["no_valid_email"] += 1

    output.append({
        "domain": r["original_domain"],
        "category": r["category"],
        "dm_name": r["dm_name"],
        "existing_email": existing,
        "existing_email_source": r["email_source"],
        "existing_verified_by_smtp": existing_now_verified,
        "smtp_verified_dm_email": dm_email_found,
        "smtp_verified_company_email": company_email_found,
        "smtp_all_verified": verified_list,
        "mx_host": smtp.get("mx_host"),
        "accept_all": smtp.get("accept_all", False),
        "patterns_tested": smtp.get("patterns_tested", 0),
        "time_seconds": smtp.get("time_seconds", 0),
        "error": smtp_error,
    })

stats["total_sendable"] = stats["verified_dm_email"] + stats["company_email_verified"] + stats["existing_verified"]
stats["total_time_seconds"] = round(total_time, 1)
stats["cost_usd"] = 0.0

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

final = {
    "stage": "301_email_discovery",
    "summary": stats,
    "pattern_hits": dict(sorted(pattern_hits.items(), key=lambda x: -x[1])),
    "domains": output,
}
json.dump(final, open(OUTPUT_DIR / "301_email_discovery.json", "w"), indent=2)
print(f"Saved to {OUTPUT_DIR}/301_email_discovery.json")

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("REPORT: #301 SMTP Email Discovery — 260 AU DMs")
print("=" * 60)
print(f"Domains tested:          {stats['domains_tested']}")
print(f"No MX record:            {stats['no_mx']}")
print(f"Accept-all (unverifiable): {stats['accept_all']}")
print(f"SMTP errors:             {stats['smtp_error']}")
print(f"")
print(f"Verified DM email found: {stats['verified_dm_email']}")
print(f"Existing email verified: {stats['existing_verified']}")
print(f"Company email verified:  {stats['company_email_verified']}")
print(f"No valid email found:    {stats['no_valid_email']}")
print(f"Total sendable:          {stats['total_sendable']}")
print(f"")
print(f"Total time:              {stats['total_time_seconds']}s")
print(f"Cost:                    $0.00")

print(f"\nPer-pattern hit rate:")
for pattern, count in sorted(pattern_hits.items(), key=lambda x: -x[1]):
    print(f"  {pattern:<20}: {count} hits")

print(f"\n--- ALL 260 RESULTS (LAW XIV) ---")
print(json.dumps(output, indent=2))
