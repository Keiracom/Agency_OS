"""
#336-v2 Pipeline Reorder Audit
Tasks A-F: Scrape employees, filter DMs, compare vs Stage 6, enrich via ContactOut, metrics.
"""

import json
import os
import time
import requests
from datetime import datetime

# ── Env ──────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv

load_dotenv("/home/elliotbot/.config/agency-os/.env")

APIFY_TOKEN = os.environ["APIFY_API_TOKEN"]
CONTACTOUT_KEY = os.environ["CONTACTOUT_API_KEY"]

INPUT_STAGE8 = "/home/elliotbot/clawd/Agency_OS/scripts/output/335_1_stage_8.json"
INPUT_STAGE6 = "/home/elliotbot/clawd/Agency_OS/scripts/output/332_stage_6.json"
OUT_RAW = "/home/elliotbot/clawd/Agency_OS/scripts/output/336_v2_employees_raw.json"
OUT_NEWDMS = "/home/elliotbot/clawd/Agency_OS/scripts/output/336_v2_new_dms.json"
OUT_METRICS = "/home/elliotbot/clawd/Agency_OS/scripts/output/336_v2_reordered_metrics.json"

ACTOR_ID = "george.the.developer~linkedin-company-employees-scraper"

DM_KEYWORDS = [
    "owner",
    "founder",
    "co-founder",
    "principal",
    "director",
    "managing director",
    "ceo",
    "chief executive",
    "partner",
    "senior partner",
    "practice manager",
    "practice owner",
    "head of",
    "lead",
    "president",
]

AU_LOCATIONS = [
    "australia",
    "sydney",
    "melbourne",
    "brisbane",
    "perth",
    "adelaide",
    "canberra",
    "hobart",
    "darwin",
    "nsw",
    "vic",
    "qld",
    "wa",
    "sa",
    "act",
    "tas",
    "nt",
    "new south wales",
    "victoria",
    "queensland",
    "western australia",
    "south australia",
    "australian capital territory",
    "tasmania",
    "northern territory",
]


# ── Task A: Extract eligible LinkedIn URLs ────────────────────────────────────
def task_a_extract_urls():
    print("\n=== TASK A: Extract eligible LinkedIn URLs ===")
    with open(INPUT_STAGE8) as f:
        stage8 = json.load(f)
    domains_data = stage8["domains"]
    eligible = {}
    for domain, info in domains_data.items():
        linkedin_url = info.get("linkedin_url")
        url_source = info.get("url_source", "none")
        if linkedin_url and url_source != "none":
            eligible[domain] = linkedin_url
    print(f"Total domains: {len(domains_data)}")
    print(f"Eligible (linkedin_url not null AND url_source != none): {len(eligible)}")
    return eligible


def apify_run_async(companies, poll_interval=15, max_wait=600):
    """Start Apify actor, poll until done, return items."""
    start_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs?token={APIFY_TOKEN}"
    print(f"  Starting actor async run for {len(companies)} companies...")
    resp = requests.post(start_url, json={"companies": companies}, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to start actor: {resp.status_code} {resp.text[:300]}")
    run_data = resp.json()
    run_id = run_data["data"]["id"]
    dataset_id = run_data["data"]["defaultDatasetId"]
    print(f"  Run ID: {run_id}, Dataset: {dataset_id}")

    # Poll for completion
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        status_resp = requests.get(status_url, timeout=15)
        if status_resp.status_code != 200:
            print(f"  Warning: status check returned {status_resp.status_code}")
            continue
        run_status = status_resp.json()["data"]["status"]
        print(f"  [{elapsed}s] Status: {run_status}")
        if run_status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            break

    if run_status != "SUCCEEDED":
        raise RuntimeError(f"Actor run did not succeed: {run_status}")

    # Fetch dataset items (paginated)
    items = []
    offset = 0
    limit = 1000
    while True:
        items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}&offset={offset}&limit={limit}"
        items_resp = requests.get(items_url, timeout=30)
        batch = items_resp.json()
        if not batch:
            break
        items.extend(batch)
        print(f"  Fetched {len(items)} items so far (offset={offset})")
        if len(batch) < limit:
            break
        offset += limit

    return items, elapsed


def task_a_scrape(eligible_urls):
    print("\n=== TASK A: Scrape employees via Apify (async) ===")
    companies = list(eligible_urls.values())
    t0 = time.time()
    try:
        employees, actor_elapsed = apify_run_async(companies, poll_interval=15, max_wait=900)
        wall_time = time.time() - t0
        print(f"  Total employees: {len(employees)}, wall_time: {wall_time:.1f}s")
        return employees, wall_time, None
    except Exception as e:
        wall_time = time.time() - t0
        print(f"  Error: {e}")
        return [], wall_time, str(e)


# ── Task B: Filter to DM candidates ──────────────────────────────────────────
def task_b_filter(employees):
    print("\n=== TASK B: Filter to DM candidates ===")
    print(f"Raw employees: {len(employees)}")

    if employees:
        sample = employees[0]
        print(f"  Sample keys: {list(sample.keys())}")
        print(f"  Sample record snippet: {json.dumps(sample, indent=2)[:400]}")

    title_filtered = []
    for emp in employees:
        headline = (emp.get("headline") or emp.get("title") or emp.get("position") or "").lower()
        if any(kw in headline for kw in DM_KEYWORDS):
            title_filtered.append(emp)

    print(f"Title-filtered (DM keywords): {len(title_filtered)}")

    loc_filtered = []
    for emp in title_filtered:
        location = (emp.get("location") or emp.get("locationName") or "").lower()
        if any(loc in location for loc in AU_LOCATIONS):
            loc_filtered.append(emp)

    print(f"Location-filtered (AU): {len(loc_filtered)}")
    return title_filtered, loc_filtered


# ── Task C: Compare vs Stage 6 ────────────────────────────────────────────────
def task_c_compare(loc_filtered_dms, eligible_urls):
    print("\n=== TASK C: Compare vs Stage 6 ===")
    with open(INPUT_STAGE6) as f:
        stage6 = json.load(f)
    stage6_domains = {d["domain"]: d for d in stage6["domains"]}

    # Build map: normalized company URL -> list of DM candidates
    company_to_dms = {}
    for emp in loc_filtered_dms:
        comp_url = (
            emp.get("company") or emp.get("companyUrl") or emp.get("companyLinkedInUrl") or ""
        ).rstrip("/")
        if not comp_url:
            continue
        if comp_url not in company_to_dms:
            company_to_dms[comp_url] = []
        company_to_dms[comp_url].append(emp)

    no_dm_domains = [d["domain"] for d in stage6["domains"] if not d.get("dm_found")]
    print(f"No-DM companies in Stage 6: {len(no_dm_domains)}")

    results = {}
    match_count = new_count = no_change_count = 0

    for domain, s6_data in stage6_domains.items():
        li_url = eligible_urls.get(domain, "").rstrip("/")
        new_dms = []
        if li_url:
            for emp_url_norm, dms in company_to_dms.items():
                if li_url in emp_url_norm or emp_url_norm in li_url:
                    new_dms = dms
                    break

        s6_has_dm = s6_data.get("dm_found", False)
        best_new = new_dms[0] if new_dms else None

        if s6_has_dm and best_new:
            status = "MATCH"
            match_count += 1
        elif s6_has_dm and not best_new:
            status = "NO_CHANGE"
            no_change_count += 1
        elif not s6_has_dm and best_new:
            status = "NEW"
            new_count += 1
        else:
            status = "NO_CHANGE"
            no_change_count += 1

        results[domain] = {
            "status": status,
            "stage6_dm": s6_data.get("dm_name"),
            "stage6_dm_role": s6_data.get("dm_role"),
            "new_dm_candidates": len(new_dms),
            "best_new_dm": best_new,
        }

    print(f"  MATCH:     {match_count}")
    print(f"  NEW:       {new_count}  (Stage 6 had no DM, employee list provides one)")
    print(f"  NO_CHANGE: {no_change_count}")

    recovered = sum(1 for d in no_dm_domains if results.get(d, {}).get("status") == "NEW")
    print(f"\nNo-DM recovery: {recovered}/{len(no_dm_domains)} companies now have a DM candidate")

    return results, no_dm_domains


# ── Task D: Enrich NEW DMs via ContactOut ────────────────────────────────────
def task_d_enrich(compare_results):
    print("\n=== TASK D: Enrich NEW DMs via ContactOut ===")
    new_dms_to_enrich = []
    for domain, result in compare_results.items():
        if result["status"] == "NEW" and result.get("best_new_dm"):
            emp = result["best_new_dm"]
            profile_url = (
                emp.get("profileUrl")
                or emp.get("url")
                or emp.get("linkedInUrl")
                or emp.get("linkedin_url")
            )
            if profile_url:
                new_dms_to_enrich.append(
                    {"domain": domain, "employee": emp, "profile_url": profile_url}
                )

    print(f"NEW DMs with profileUrl: {len(new_dms_to_enrich)}")

    enriched = []
    for item in new_dms_to_enrich:
        profile_url = item["profile_url"]
        print(f"  Enriching: {profile_url[:70]}...")
        try:
            resp = requests.post(
                "https://api.contactout.com/v1/people/enrich",
                headers={"authorization": "basic", "token": CONTACTOUT_KEY},
                json={"linkedin_url": profile_url},
                timeout=30,
            )
            result_data = (
                resp.json()
                if resp.status_code == 200
                else {"error": resp.status_code, "body": resp.text[:200]}
            )
            emails = (
                result_data.get("profile", {}).get("emails", []) if "profile" in result_data else []
            )
            mobiles = (
                result_data.get("profile", {}).get("phones", []) if "profile" in result_data else []
            )
            enriched.append(
                {
                    "domain": item["domain"],
                    "name": item["employee"].get("name") or item["employee"].get("fullName"),
                    "headline": item["employee"].get("headline"),
                    "profile_url": profile_url,
                    "status_code": resp.status_code,
                    "emails": emails,
                    "mobiles": mobiles,
                    "raw_response": result_data,
                }
            )
            print(f"    Status: {resp.status_code}, emails: {len(emails)}, mobiles: {len(mobiles)}")
        except Exception as e:
            print(f"    Error: {e}")
            enriched.append({"domain": item["domain"], "profile_url": profile_url, "error": str(e)})

    email_found = sum(1 for e in enriched if e.get("emails"))
    mobile_found = sum(1 for e in enriched if e.get("mobiles"))
    print(
        f"\nContactOut results: {len(enriched)} enriched, {email_found} email found, {mobile_found} mobile found"
    )
    return enriched


# ── Task E: Metrics comparison ────────────────────────────────────────────────
def task_e_metrics(employees, title_filtered, loc_filtered, compare_results, enriched_dms):
    print("\n=== TASK E: Metrics Comparison Table ===")
    with open(INPUT_STAGE6) as f:
        stage6 = json.load(f)
    domains_list = stage6["domains"]

    total = len(domains_list)
    stage6_dm_count = sum(1 for d in domains_list if d.get("dm_found"))
    stage6_no_dm = total - stage6_dm_count
    new_recoveries = sum(1 for v in compare_results.values() if v["status"] == "NEW")
    new_total_dm = stage6_dm_count + new_recoveries
    new_coverage_pct = (new_total_dm / total * 100) if total else 0

    table = f"""
+--------------------------------+------------------+--------------------------+
|         Metric                 | Stage 6 (Before) | Stage6+Employees (After) |
+--------------------------------+------------------+--------------------------+
| Total companies                | {total:>16} | {total:>24} |
| DM identified                  | {stage6_dm_count:>16} | {new_total_dm:>24} |
| No DM                          | {stage6_no_dm:>16} | {stage6_no_dm - new_recoveries:>24} |
| Coverage %                     | {stage6_dm_count / total * 100:>15.1f}% | {new_coverage_pct:>23.1f}% |
+--------------------------------+------------------+--------------------------+
| New recoveries                 |              --- | {new_recoveries:>24} |
| ContactOut enriched            |              --- | {len(enriched_dms):>24} |
| Verified emails (new DMs)      |              --- | {sum(1 for e in enriched_dms if e.get("emails")):>24} |
| Verified mobiles (new DMs)     |              --- | {sum(1 for e in enriched_dms if e.get("mobiles")):>24} |
+--------------------------------+------------------+--------------------------+

Employee Scrape Stats:
  Total raw employees:     {len(employees)}
  Title-filtered (DM kw):  {len(title_filtered)}
  Location-filtered (AU):  {len(loc_filtered)}
"""
    if employees:
        from collections import Counter
        import statistics

        comp_counts = Counter()
        for emp in employees:
            comp = (emp.get("company") or emp.get("companyUrl") or "unknown").rstrip("/")
            comp_counts[comp] += 1
        counts_list = list(comp_counts.values())
        if counts_list:
            table += f"""Per-company employee counts:
  Companies with employees: {len(comp_counts)}
  Min: {min(counts_list)}, Median: {statistics.median(counts_list):.0f}, Max: {max(counts_list)}
"""
    print(table)
    return table


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{'=' * 60}")
    print(f"#336-v2 Pipeline Reorder Audit — {datetime.now().isoformat()}")
    print(f"{'=' * 60}")

    # Task A
    eligible_urls = task_a_extract_urls()
    employees, elapsed, error = task_a_scrape(eligible_urls)

    if error:
        print(f"Apify error: {error}")

    # Save raw
    with open(OUT_RAW, "w") as f:
        json.dump(
            {
                "directive": "#336-v2",
                "wall_time_s": elapsed,
                "total_employees": len(employees),
                "eligible_companies": len(eligible_urls),
                "employees": employees,
            },
            f,
            indent=2,
        )
    print(f"\nRaw saved: {OUT_RAW}")

    # Task B
    title_filtered, loc_filtered = task_b_filter(employees)

    # Task C
    compare_results, no_dm_domains = task_c_compare(loc_filtered, eligible_urls)

    # Task D
    enriched_dms = task_d_enrich(compare_results)

    # Save new DMs
    new_dm_list = []
    for domain, result in compare_results.items():
        if result["status"] == "NEW":
            enrich_match = next((e for e in enriched_dms if e["domain"] == domain), {})
            new_dm_list.append(
                {
                    "domain": domain,
                    "candidate": result.get("best_new_dm"),
                    "contactout": enrich_match,
                }
            )

    with open(OUT_NEWDMS, "w") as f:
        json.dump(new_dm_list, f, indent=2)
    print(f"New DMs saved: {OUT_NEWDMS}")

    # Task E
    metrics_table = task_e_metrics(
        employees, title_filtered, loc_filtered, compare_results, enriched_dms
    )

    # Save metrics
    stage6_dm_count = sum(1 for v in compare_results.values() if v.get("stage6_dm"))
    new_recoveries = sum(1 for v in compare_results.values() if v["status"] == "NEW")
    metrics = {
        "directive": "#336-v2",
        "timestamp": datetime.now().isoformat(),
        "wall_time_s": elapsed,
        "stage8_total_domains": 57,
        "eligible_linkedin_urls": len(eligible_urls),
        "raw_employees": len(employees),
        "title_filtered": len(title_filtered),
        "location_filtered": len(loc_filtered),
        "stage6_dm_count": stage6_dm_count,
        "new_recoveries": new_recoveries,
        "contactout_enriched": len(enriched_dms),
        "emails_found": sum(1 for e in enriched_dms if e.get("emails")),
        "mobiles_found": sum(1 for e in enriched_dms if e.get("mobiles")),
        "compare_summary": {
            "MATCH": sum(1 for v in compare_results.values() if v["status"] == "MATCH"),
            "NEW": new_recoveries,
            "NO_CHANGE": sum(1 for v in compare_results.values() if v["status"] == "NO_CHANGE"),
        },
        "metrics_table": metrics_table,
    }
    with open(OUT_METRICS, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Metrics saved: {OUT_METRICS}")

    # Task F
    print("""
=== TASK F: Alternatives Evaluated (per #336-META) ===

1. george.the.developer/linkedin-company-employees-scraper
   Status: TESTED (this run)
   Result: See metrics above

2. apimaestro/linkedin-company-employees-scraper-no-cookies
   Status: TESTED in earlier session (#335 series)
   Result: Returned 0 results on brydens.com.au. RULED OUT — empty results.

3. artificially/linkedin-employees-scraper
   Status: NOT TESTED this run
   Reason: 200 runs, 52 users — lower adoption. Not retested.

4. BD LinkedIn Company dataset (gd_l1viktl72bvl7bjuj0)
   Status: NOT RETESTED this directive
   Notes: Returns employees field, deprecated for 75% slug failure. Revisit with validated URLs.

5. Direct scrape (ScrapFly / Phantom)
   Status: NOT VIABLE — higher cost, proxy infrastructure required. Not suitable for diagnostic.
""")

    print("\n=== AUDIT COMPLETE ===")
    return metrics


if __name__ == "__main__":
    main()
