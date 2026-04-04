#!/usr/bin/env python3
"""Directive #243 Part 2 — businesses 12-26"""
import os, json, time, base64, re
from urllib.request import urlopen, Request

LOGIN = "david.stephens@keiracom.com"
PASSWORD = "9cb373dab8a0eff1"
AUTH = base64.b64encode(f"{LOGIN}:{PASSWORD}".encode()).decode()
DFS_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

BUSINESSES = [
    {"name": "Edward Lees Cars",             "suburb": None},
    {"name": "Business Telecom",             "suburb": "North Parramatta"},
    {"name": "Absolute Business Brokers",    "suburb": "Mulgrave"},
    {"name": "Outback Solar",                "suburb": "Penrith"},
    {"name": "Provincial Home Living",       "suburb": "Fyshwick"},
    {"name": "Adelaide Tarp Specialists",    "suburb": "Greenfields"},
    {"name": "Australian Exchange",          "suburb": "Lakemba"},
    {"name": "Splash Paediatric Therapy",    "suburb": "Werribee"},
    {"name": "Singleton Diggers",            "suburb": "Singleton"},
    {"name": "Strathfield Golf Club",        "suburb": "Strathfield"},
    {"name": "Bondi Bowlo",                  "suburb": "Bondi"},
    {"name": "Noosa Boathouse",              "suburb": "Noosa"},
    {"name": "Chatsworth-Iluka Bowls Club",  "suburb": "Iluka"},
    {"name": "The Mill Restaurant",          "suburb": None},
    {"name": "Strathfield Hotel",            "suburb": "Strathfield"},
]

def dfs_serp(keyword):
    payload = json.dumps([{"keyword": keyword, "location_name": "Australia", "language_name": "English", "depth": 10}]).encode()
    req = Request(DFS_URL, data=payload, headers={"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"})
    try:
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = []
        tasks = data.get("tasks", [])
        if tasks and tasks[0].get("result"):
            for item in tasks[0]["result"][0].get("items", []):
                if item.get("type") == "organic":
                    results.append({"title": item.get("title", ""), "url": item.get("url", "")})
                    if len(results) == 3: break
        return results, data.get("cost", 0)
    except Exception as e:
        print(f"    ERROR: {e}")
        return [], 0

total_cost = 0.0
results_log = []

for i, b in enumerate(BUSINESSES, 12):
    name = b["name"]
    suburb = b["suburb"] or ""
    prefix = f"{name} {suburb}".strip()
    queries = {"a": f"{prefix} owner", "b": f"{prefix} director", "c": f"{name} linkedin"}
    
    biz = {"business": name, "suburb": suburb, "queries": {}, "dm_name": None, "dm_query": None, "dm_source": None, "linkedin_url": None}
    
    print(f"\n  [{i}/26] {name}")
    for qtype, keyword in queries.items():
        serp, cost = dfs_serp(keyword)
        total_cost += cost
        biz["queries"][qtype] = {"keyword": keyword, "cost": cost, "top3": serp}
        print(f"    ({qtype}) \"{keyword}\" — {len(serp)} results, ${cost:.4f}")
        for r in serp:
            print(f"         Title: {r['title']}")
            print(f"         URL:   {r['url']}")
        
        # Extract LinkedIn profile URL
        if not biz["linkedin_url"]:
            for r in serp:
                if "linkedin.com/in/" in r["url"]:
                    biz["linkedin_url"] = r["url"]
                    break
        
        # Heuristic: owner/director name in title
        if not biz["dm_name"]:
            biz_words = set(name.lower().split())
            for r in serp:
                li_m = re.search(r'linkedin\.com/in/([^/?]+)', r["url"])
                if li_m:
                    slug = li_m.group(1).replace("-", " ").title()
                    if len(slug.split()) >= 2 and not any(w in slug.lower() for w in biz_words):
                        biz["dm_name"] = slug; biz["dm_query"] = qtype; biz["dm_source"] = "linkedin_url"; break
                title_lower = r["title"].lower()
                if any(kw in title_lower for kw in ["owner","director","founder","principal","proprietor","ceo","managing"]):
                    m = re.search(r'\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20})\b', r["title"])
                    if m:
                        cand = f"{m.group(1)} {m.group(2)}"
                        if not any(w in cand.lower() for w in biz_words):
                            biz["dm_name"] = cand; biz["dm_query"] = qtype; biz["dm_source"] = "serp_title"; break
        
        time.sleep(0.3)
    
    results_log.append(biz)

print("\n" + "="*60)
print("PART 2 PER-BUSINESS SUMMARY")
print("="*60)
for r in results_log:
    print(f"\n  {r['business']}")
    print(f"  DM: {'YES — ' + r['dm_name'] if r['dm_name'] else 'No'}" + (f" (q{r['dm_query']}, {r['dm_source']})" if r['dm_name'] else ""))
    print(f"  LinkedIn: {r['linkedin_url'] or 'None'}")

dm_found = sum(1 for r in results_log if r["dm_name"])
li_found = sum(1 for r in results_log if r["linkedin_url"])
print(f"\nPart 2: DM found {dm_found}/{len(results_log)}, LinkedIn {li_found}/{len(results_log)}")
print(f"Part 2 cost: ${total_cost:.4f} USD")
