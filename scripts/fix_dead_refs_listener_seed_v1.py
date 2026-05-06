#!/usr/bin/env python3
"""GOV-10 fix for LISTENER-KNOWLEDGE-SEED-V1 — split combined dead-ref chunks
into individual per-dead-ref chunks so 'what replaced X' retrieval hits
a chunk that IS the answer, not a chunk that contains the answer in a list.

Deletes 2 combined chunks (35e7db15 MANUAL, e603df7c ARCHITECTURE) and
inserts 12 individual chunks in their place.
"""

import json
import os
import sys
from datetime import datetime, timezone

import httpx

ENV_FILE = "/home/elliotbot/.config/agency-os/.env"
EMBED_MODEL = "text-embedding-3-small"
DIRECTIVE_ID = "LISTENER-KNOWLEDGE-SEED-V1"
FIX_TAG = "GOV10-dead-ref-split"

IDS_TO_DELETE = [
    "35e7db15-83f4-4189-aca9-6d83d94503f8",  # MANUAL.md combined DEAD providers
    "e603df7c-18f0-4e3f-a9c4-9b28a32fec92",  # ARCHITECTURE.md combined Deprecated vendors
]

NEW_CHUNKS = [
    {
        "content": "Dead reference: Proxycurl is deprecated. Replacement: Bright Data LinkedIn Profile dataset (gd_l1viktl72bvl7bjuj0). Reason: LinkedIn lawsuit killed Proxycurl as a viable vendor. Ratified in Directive #167.",
        "section": "Dead References",
        "sub_section": "Proxycurl",
        "origin_file": "docs/MANUAL.md + ARCHITECTURE.md",
        "tags": ["dead-ref", "proxycurl", "bright-data", "linkedin", "replacement"],
    },
    {
        "content": "Dead reference: Apollo (for enrichment) is deprecated. Replacement: Bright Data LinkedIn Profile + business_universe JOIN. Apollo was the old contact database; the v7 waterfall replaced it with Bright Data endpoints plus our local BU cache.",
        "section": "Dead References",
        "sub_section": "Apollo",
        "origin_file": "ARCHITECTURE.md",
        "tags": ["dead-ref", "apollo", "bright-data", "business-universe", "replacement"],
    },
    {
        "content": "Dead reference: Apify (as GMB scraper) is deprecated. Replacement: Bright Data GMB Web Scraper (dataset gd_m8ebnr0q2qlklc02fz). EXCEPTION: Apify harvestapi/linkedin-profile-scraper remains active in Pipeline F v2.1 for L2 LinkedIn verification. Apify facebook-posts-scraper active for Stage 9 social.",
        "section": "Dead References",
        "sub_section": "Apify",
        "origin_file": "docs/MANUAL.md + ARCHITECTURE.md",
        "tags": ["dead-ref", "apify", "bright-data", "gmb", "replacement", "exception"],
    },
    {
        "content": "Dead reference: Hunter.io (for email finding) is deprecated. Replacement: Leadmagic email-finder at $0.015 per email (pipeline stage T3). EXCEPTION: Hunter email-finder still active as L2 fallback in Pipeline F v2.1 when score >= 70. Ratified in Directive #167.",
        "section": "Dead References",
        "sub_section": "Hunter.io",
        "origin_file": "docs/MANUAL.md + ARCHITECTURE.md",
        "tags": ["dead-ref", "hunter", "leadmagic", "email", "replacement", "exception"],
    },
    {
        "content": "Dead reference: Kaspr is deprecated. Replacement: Leadmagic mobile-finder at $0.077 per mobile (pipeline stage T5). Ratified in Directive #167.",
        "section": "Dead References",
        "sub_section": "Kaspr",
        "origin_file": "docs/MANUAL.md + ARCHITECTURE.md",
        "tags": ["dead-ref", "kaspr", "leadmagic", "mobile", "replacement"],
    },
    {
        "content": "Dead reference: Clay is deprecated. Replacement: none required — was person enrichment, removed, not needed under the v7 waterfall architecture.",
        "section": "Dead References",
        "sub_section": "Clay",
        "origin_file": "ARCHITECTURE.md",
        "tags": ["dead-ref", "clay", "removal"],
    },
    {
        "content": "Dead reference: Webshare is deprecated. Replacement: Bright Data (handles proxy rotation as part of its service).",
        "section": "Dead References",
        "sub_section": "Webshare",
        "origin_file": "ARCHITECTURE.md",
        "tags": ["dead-ref", "webshare", "bright-data", "proxy", "replacement"],
    },
    {
        "content": "Dead reference: SERP API is deprecated. Replacement: DataForSEO (all search results + SERP endpoints).",
        "section": "Dead References",
        "sub_section": "SERP API",
        "origin_file": "ARCHITECTURE.md",
        "tags": ["dead-ref", "serp-api", "dataforseo", "replacement"],
    },
    {
        "content": "Dead reference: Direct mail as an outreach channel is deprecated. Replacement: none — removed permanently from the outreach stack. Outreach is email + LinkedIn + voice only.",
        "section": "Dead References",
        "sub_section": "Direct mail",
        "origin_file": "ARCHITECTURE.md",
        "tags": ["dead-ref", "direct-mail", "outreach", "removal"],
    },
    {
        "content": "Dead reference: ZeroBounce is deprecated. Status: parked — do not build. Not used in v7 architecture. Reacher is blocked, and email validation is not a gap we're prioritising.",
        "section": "Dead References",
        "sub_section": "ZeroBounce",
        "origin_file": "docs/MANUAL.md + ARCHITECTURE.md",
        "tags": ["dead-ref", "zerobounce", "parked", "email-validation"],
    },
    {
        "content": "Dead reference: Spider.cloud as primary scraper is deprecated. Replacement: httpx handles ~90% of domains; Spider.cloud retained as JS fallback for the ~10% requiring JS rendering. Ratified in Directive #295.",
        "section": "Dead References",
        "sub_section": "Spider.cloud",
        "origin_file": "docs/MANUAL.md",
        "tags": ["dead-ref", "spider-cloud", "httpx", "scraper", "replacement"],
    },
    {
        "content": "Dead reference: DFS Domain Technologies endpoint is deprecated. Replacement: none — disqualified, not replaced. Reason: 1.3% AU coverage (1 of 78 test domains matched) makes it unusable for tech-gap signal extraction. Confirmed via live test March 2026. DFS paid_etv similarly disqualified: AU top dental domain returns $150/mo, cannot distinguish SMB budget ranges.",
        "section": "Dead References",
        "sub_section": "DFS Domain Technologies + paid_etv",
        "origin_file": "docs/MANUAL.md",
        "tags": ["dead-ref", "dfs", "dataforseo", "disqualified", "au-coverage"],
    },
]


def load_env() -> None:
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def main() -> None:
    load_env()
    now_iso = datetime.now(timezone.utc).isoformat()
    sb_url = os.environ["SUPABASE_URL"]
    sb_key = os.environ["SUPABASE_SERVICE_KEY"]
    sb_headers = {
        "apikey": sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    with httpx.Client(timeout=60) as client:
        # Step 1 — embed new chunks
        print(f"Embedding {len(NEW_CHUNKS)} replacement chunks...")
        resp = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={"model": EMBED_MODEL, "input": [c["content"] for c in NEW_CHUNKS]},
        )
        resp.raise_for_status()
        data = resp.json()
        for c, item in zip(NEW_CHUNKS, data["data"]):
            c["_embedding"] = item["embedding"]
        print(f"  tokens used: {data.get('usage', {}).get('total_tokens', 0)}")

        # Step 2 — delete the 2 combined chunks
        for rid in IDS_TO_DELETE:
            del_resp = client.delete(
                f"{sb_url}/rest/v1/agent_memories?id=eq.{rid}",
                headers=sb_headers,
            )
            if del_resp.status_code not in (200, 204):
                print(
                    f"DELETE FAILED for {rid}: {del_resp.status_code} {del_resp.text[:200]}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(f"  deleted {rid}")

        # Step 3 — insert 12 new chunks
        rows = []
        for c in NEW_CHUNKS:
            rows.append(
                {
                    "callsign": "system",
                    "source_type": "verified_fact",
                    "content": c["content"],
                    "typed_metadata": {
                        "source": "governance_doc",
                        "section": c["section"],
                        "sub_section": c["sub_section"],
                        "origin_file": c["origin_file"],
                        "seeded_at": now_iso,
                        "seeded_by": DIRECTIVE_ID,
                        "ingested_by": DIRECTIVE_ID,
                        "fix_tag": FIX_TAG,
                    },
                    "tags": c["tags"],
                    "state": "confirmed",
                    "confidence": 1.0,
                    "trust": "dave_confirmed",
                    "embedding": c["_embedding"],
                    "directive_id": DIRECTIVE_ID,
                }
            )

        ins_resp = client.post(
            f"{sb_url}/rest/v1/agent_memories",
            headers=sb_headers,
            json=rows,
        )
        if ins_resp.status_code not in (200, 201, 204):
            print(f"INSERT FAILED: {ins_resp.status_code} {ins_resp.text[:500]}", file=sys.stderr)
            sys.exit(1)
        print(f"  inserted {len(rows)} individual dead-ref chunks")

    print(
        f"\nGOV-10 fix complete: -2 combined, +{len(NEW_CHUNKS)} individual = net +{len(NEW_CHUNKS) - 2} rows"
    )


if __name__ == "__main__":
    main()
