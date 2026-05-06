"""
FM-BUILD-V1 Stage 2 — ContactOut Facilities Manager Search
Searches 549 companies for FM title variants, saves raw profiles to JSON.
"""

import csv
import json
import time
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

# ── env ──────────────────────────────────────────────────────────────────────
load_dotenv("/home/elliotbot/.config/agency-os/.env")
API_KEY = os.environ["CONTACTOUT_API_KEY"]
# ContactOut uses "token" header (not Basic/Bearer)
SEARCH_URL = "https://api.contactout.com/v1/people/search"
HEADERS = {"token": API_KEY, "Content-Type": "application/json"}

# ── paths ─────────────────────────────────────────────────────────────────────
REPO = Path("/home/elliotbot/clawd/Agency_OS")
TARGET_CSV = REPO / "scripts" / "fm_target_list.csv"
OUTPUT_JSON = REPO / "scripts" / "fm_raw_profiles.json"

# ── title variants ────────────────────────────────────────────────────────────
PRIMARY_TITLES = ["Facilities Manager", "Facilities Coordinator"]
SECONDARY_TITLES = [
    "Property Manager",
    "Site Manager",
    "Maintenance Manager",
    "Operations Manager",
]

# ── exclusion keywords ────────────────────────────────────────────────────────
EXCLUSION_TERMS = [
    "IT Facilities",
    "Digital Facilities",
    "Marketing Facilities",
    "Events Facilities",
    "HR Facilities",
]

# ── helpers ───────────────────────────────────────────────────────────────────


def load_companies(csv_path: Path) -> list[dict]:
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def should_exclude(title: str) -> bool:
    t = title or ""
    for term in EXCLUSION_TERMS:
        if term.lower() in t.lower():
            return True
    return False


def search_contactout(company_name: str, title: str, retried: bool = False) -> list[dict]:
    """Return list of raw profile dicts for one (company, title) combo.
    NOTE: ContactOut 'title' field is ignored server-side; 'keyword' performs
    actual title-keyword matching. Client-side exclusion filter still applied.
    """
    payload = {
        "keyword": title,
        "company": [company_name],
        "location": ["Australia"],
        "page_size": 10,
    }
    try:
        resp = requests.post(SEARCH_URL, headers=HEADERS, json=payload, timeout=30)
        if resp.status_code == 429:
            if retried:
                print(f"    [429 again] giving up on ({company_name}, {title})")
                return []
            print(f"    [429] rate limit — sleeping 30s then retry")
            time.sleep(30)
            return search_contactout(company_name, title, retried=True)
        if resp.status_code != 200:
            print(f"    [ERR {resp.status_code}] {company_name} / {title}: {resp.text[:120]}")
            return []
        data = resp.json()
        profiles_raw = data.get("profiles", {})
        # ContactOut returns a dict when results exist, empty list when zero results
        if isinstance(profiles_raw, list):
            return []  # empty result
        return list(profiles_raw.items())  # [(linkedin_url, profile_obj), ...]
    except Exception as exc:
        print(f"    [EXCEPTION] {company_name} / {title}: {exc}")
        return []


def normalise_profile(linkedin_url: str, raw: dict, company_row: dict, title_searched: str) -> dict:
    """Flatten ContactOut raw profile into our output schema."""
    company_obj = raw.get("company") or {}
    return {
        "linkedin_url": linkedin_url,
        "full_name": raw.get("full_name", ""),
        "title": raw.get("title", ""),
        "company_name": company_obj.get("name", ""),
        "company_searched": company_row.get("company_name", ""),
        "sector": company_row.get("sector", ""),
        "employer_type": company_row.get("employer_type", ""),
        "location": raw.get("location", ""),
        "headline": raw.get("headline", ""),
        "title_variant_matched": title_searched,
        "raw_profile": raw,
    }


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    companies = load_companies(TARGET_CSV)
    print(f"Loaded {len(companies)} companies from {TARGET_CSV}")

    seen_urls: set[str] = set()
    profiles: list[dict] = []
    companies_with_results = 0
    credits_used = 0
    title_dist: dict[str, int] = {}

    for idx, company_row in enumerate(companies, start=1):
        company_name = company_row["company_name"]
        found_primary = 0

        if idx % 25 == 0 or idx == 1:
            print(f"\n[{idx}/{len(companies)}] credits used so far: {credits_used}")

        # ── primary titles (always search) ────────────────────────────────────
        for title in PRIMARY_TITLES:
            time.sleep(2)
            results = search_contactout(company_name, title)
            credits_used += 1
            for linkedin_url, raw in results:
                raw_title = raw.get("title", "")
                if should_exclude(raw_title):
                    continue
                if linkedin_url in seen_urls:
                    continue
                seen_urls.add(linkedin_url)
                profiles.append(normalise_profile(linkedin_url, raw, company_row, title))
                found_primary += 1
                title_dist[title] = title_dist.get(title, 0) + 1

        # ── secondary titles (only if primary returned 0) ─────────────────────
        if found_primary == 0:
            for title in SECONDARY_TITLES:
                time.sleep(2)
                results = search_contactout(company_name, title)
                credits_used += 1
                for linkedin_url, raw in results:
                    raw_title = raw.get("title", "")
                    if should_exclude(raw_title):
                        continue
                    if linkedin_url in seen_urls:
                        continue
                    seen_urls.add(linkedin_url)
                    profiles.append(normalise_profile(linkedin_url, raw, company_row, title))
                    title_dist[title] = title_dist.get(title, 0) + 1
                # stop secondaries as soon as one variant finds something
                if any(p["company_searched"] == company_name for p in profiles[-10:]):
                    break

        if any(p["company_searched"] == company_name for p in profiles):
            companies_with_results += 1

    # ── build output ──────────────────────────────────────────────────────────
    all_titles_searched = PRIMARY_TITLES + [t for t in SECONDARY_TITLES if t in title_dist]

    output = {
        "metadata": {
            "run_date": str(date.today()),
            "companies_searched": len(companies),
            "companies_with_results": companies_with_results,
            "total_profiles": len(profiles),
            "search_credits_used": credits_used,
            "title_variants_searched": all_titles_searched,
            "title_variant_distribution": title_dist,
        },
        "profiles": profiles,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, indent=2, ensure_ascii=False))

    # ── final summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FM Stage 2 — COMPLETE")
    print(f"  Companies searched:        {len(companies)}")
    print(f"  Companies with FM results: {companies_with_results}")
    print(f"  Total unique profiles:     {len(profiles)}")
    print(f"  Estimated credits used:    {credits_used}")
    print(f"  Title variant distribution:")
    for t, n in sorted(title_dist.items(), key=lambda x: -x[1]):
        print(f"    {t}: {n}")
    print(f"\nOutput written to: {OUTPUT_JSON}")
    print("=" * 60)


if __name__ == "__main__":
    main()
