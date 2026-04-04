#!/usr/bin/env python3
"""
Directive #243 — DFS SERP Owner Search Research
Tests whether "[business name] [suburb] owner/director/linkedin" finds DM names
via DataForSEO SERP. Read-only research. No DB writes.
"""
import os, json, time, base64, subprocess, re
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Credentials ──────────────────────────────────────────────────────────────
LOGIN = "david.stephens@keiracom.com"
PASSWORD = "9cb373dab8a0eff1"
AUTH = base64.b64encode(f"{LOGIN}:{PASSWORD}".encode()).decode()
DFS_URL = "https://api.dataforseo.com/v3/serp/google/organic/live/advanced"

# ── Business list (seed) ──────────────────────────────────────────────────────
BUSINESSES = [
    {"name": "Dive Centre Manly",           "domain": "divesydney.com.au",              "suburb": "Manly",           "phone": "+61299770311"},
    {"name": "Onesta Restaurant",            "domain": "onestacucina.com.au",            "suburb": None,              "phone": None},
    {"name": "Austech Mechanic",             "domain": "austechmechanic.com.au",         "suburb": "Lake Macquarie",  "phone": "+61249497773"},
    {"name": "Dental Folk",                  "domain": "dentalfolk.com.au",              "suburb": None,              "phone": None},
    {"name": "Fencing Components",           "domain": "fencingcomponents.com.au",       "suburb": None,              "phone": None},
    {"name": "Curry Monitor",                "domain": "currymonitor.com.au",            "suburb": None,              "phone": None},
    {"name": "Zanvak",                       "domain": "zanvak.com.au",                  "suburb": None,              "phone": None},
    {"name": "Nowra Toyota",                 "domain": "nowratoyota.com.au",             "suburb": "Nowra",           "phone": None},
    {"name": "Gifts Australia",              "domain": "giftsaustralia.com.au",          "suburb": None,              "phone": None},
    {"name": "Ichiban Teppanyaki",           "domain": "ichibanteppanyaki.com.au",       "suburb": None,              "phone": None},
    {"name": "Beyond the Sky Stargazing",    "domain": "beyondtheskystargazing.com.au",  "suburb": None,              "phone": None},
    {"name": "Edward Lees Cars",             "domain": "edwardlees.com.au",              "suburb": None,              "phone": None},
    {"name": "Business Telecom",             "domain": "businesstelecom.com.au",         "suburb": "North Parramatta","phone": "+611300721100"},
    {"name": "Absolute Business Brokers",    "domain": "absolutbusinessbrokers.com.au",  "suburb": "Mulgrave",        "phone": "+61395667300"},
    {"name": "Outback Solar",                "domain": "outbacksolar.com.au",            "suburb": "Penrith",         "phone": "+611300020130"},
    {"name": "Provincial Home Living",       "domain": "provincialhomeliving.com.au",    "suburb": "Fyshwick",        "phone": "+61261473810"},
    {"name": "Adelaide Tarp Specialists",    "domain": "tarps.com.au",                   "suburb": "Greenfields",     "phone": "+61882584060"},
    {"name": "Australian Exchange",          "domain": "ausexchange.com.au",             "suburb": "Lakemba",         "phone": "+61297407447"},
    {"name": "Splash Paediatric Therapy",    "domain": "splashtherapy.com.au",           "suburb": "Werribee",        "phone": "+61387316555"},
    # Additional from gmb_pilot_results (pre-fetched below)
    {"name": "Singleton Diggers",            "domain": "singletondiggers.com.au",        "suburb": "Singleton",       "phone": None},
    {"name": "Zanvak Knives",                "domain": "zanvak.com.au",                  "suburb": None,              "phone": None},
    {"name": "Beyond the Sky",               "domain": "beyondtheskystargazing.com.au",  "suburb": "Hunter Valley",   "phone": None},
    {"name": "Strathfield Golf Club",        "domain": "strathfieldgolf.com.au",         "suburb": "Strathfield",     "phone": None},
    {"name": "Bondi Bowlo",                  "domain": "bondibowlo.com",                 "suburb": "Bondi",           "phone": None},
    {"name": "Noosa Boathouse",              "domain": "noosaboathouse.com.au",          "suburb": "Noosa",           "phone": None},
    {"name": "Onesta Cucina",                "domain": "onestacucina.com.au",            "suburb": "Melbourne",       "phone": None},
    {"name": "Chatsworth-Iluka Bowls Club",  "domain": "ilukabowls.com.au",              "suburb": "Iluka",           "phone": None},
    {"name": "Presentable Gifts",            "domain": "giftsaustralia.com.au",          "suburb": "Australia",       "phone": None},
    {"name": "The Mill Restaurant",          "domain": "themillrestaurant.com.au",       "suburb": None,              "phone": None},
    {"name": "Strathfield Hotel",            "domain": "strathfieldhotel.com.au",        "suburb": "Strathfield",     "phone": None},
]

# Deduplicate by domain
seen_domains = set()
unique_businesses = []
for b in BUSINESSES:
    if b["domain"] not in seen_domains:
        seen_domains.add(b["domain"])
        unique_businesses.append(b)
BUSINESSES = unique_businesses[:30]

# ── Jina suburb resolver ──────────────────────────────────────────────────────
def resolve_suburb(domain):
    """Try to extract suburb from homepage via Jina."""
    try:
        url = f"https://r.jina.ai/https://{domain}"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, timeout=10)
        text = resp.read().decode("utf-8", errors="ignore")
        lines = text.split("\n")[:120]
        # Look for AU suburb patterns
        for line in lines:
            m = re.search(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),?\s+(NSW|VIC|QLD|WA|SA|TAS|NT|ACT)\b', line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

# ── DFS SERP query ────────────────────────────────────────────────────────────
def dfs_serp(keyword):
    """Run one DFS SERP query. Returns top 3 organic results."""
    payload = json.dumps([{
        "keyword": keyword,
        "location_name": "Australia",
        "language_name": "English",
        "depth": 10
    }]).encode()
    req = Request(DFS_URL, data=payload, headers={
        "Authorization": f"Basic {AUTH}",
        "Content-Type": "application/json"
    })
    try:
        resp = urlopen(req, timeout=30)
        data = json.loads(resp.read())
        results = []
        tasks = data.get("tasks", [])
        if tasks and tasks[0].get("result"):
            items = tasks[0]["result"][0].get("items", [])
            for item in items:
                if item.get("type") == "organic":
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", "")
                    })
                    if len(results) == 3:
                        break
        cost = data.get("cost", 0)
        return results, cost
    except Exception as e:
        return [], 0

# ── Name detection helpers ────────────────────────────────────────────────────
PERSON_TITLE_RE = re.compile(
    r'\b(?:founder|owner|director|ceo|managing director|principal|proprietor|'
    r'president|chairman|head|manager)\b', re.IGNORECASE
)
NAME_RE = re.compile(r'\b([A-Z][a-z]{1,20})\s+([A-Z][a-z]{1,20})\b')

def extract_name_from_results(results, business_name):
    """Heuristic: look for a person name in titles/URLs of SERP results."""
    biz_words = set(business_name.lower().split())
    for r in results:
        title = r["title"]
        url = r["url"]
        full = f"{title} {url}"
        # LinkedIn profile URL pattern
        li_match = re.search(r'linkedin\.com/in/([^/?]+)', url)
        if li_match:
            slug = li_match.group(1).replace("-", " ").title()
            # Filter out generic slugs
            if len(slug.split()) >= 2 and not any(w in slug.lower() for w in biz_words):
                return slug, "linkedin"
        # Name in title with owner/director context
        if PERSON_TITLE_RE.search(title):
            names = NAME_RE.findall(title)
            for fn, ln in names:
                candidate = f"{fn} {ln}"
                if not any(w in candidate.lower() for w in biz_words):
                    return candidate, "serp_title"
    return None, None

def find_linkedin_url(results):
    for r in results:
        if "linkedin.com/in/" in r["url"]:
            return r["url"]
    return None

# ── Main research loop ────────────────────────────────────────────────────────
print("=" * 70)
print("DIRECTIVE #243 — DFS SERP OWNER SEARCH")
print("=" * 70)

# Resolve suburbs for unknowns
print("\n[STEP 1] Resolving suburbs via Jina...")
for b in BUSINESSES:
    if not b["suburb"]:
        suburb = resolve_suburb(b["domain"])
        b["suburb"] = suburb
        status = suburb if suburb else "not found"
        print(f"  {b['name']}: {status}")
        time.sleep(0.5)

print("\n[BUSINESS LIST - 30 entries]")
for i, b in enumerate(BUSINESSES, 1):
    print(f"  {i:2}. {b['name']} | {b['domain']} | suburb={b['suburb']} | phone={b['phone']}")

# Run queries
print("\n[STEP 2] Running DFS SERP queries (3 per business)...")
total_cost = 0.0
results_log = []

for i, b in enumerate(BUSINESSES, 1):
    name = b["name"]
    suburb = b["suburb"] or ""
    prefix = f"{name} {suburb}".strip()

    queries = {
        "a": f"{prefix} owner",
        "b": f"{prefix} director",
        "c": f"{name} linkedin"
    }

    biz_result = {
        "business": name,
        "domain": b["domain"],
        "suburb": suburb,
        "phone": b["phone"],
        "queries": {},
        "dm_name": None,
        "dm_query": None,
        "dm_source": None,
        "linkedin_url": None,
    }

    print(f"\n  [{i}/30] {name}")
    for qtype, keyword in queries.items():
        serp_results, cost = dfs_serp(keyword)
        total_cost += cost
        biz_result["queries"][qtype] = {
            "keyword": keyword,
            "cost": cost,
            "top3": serp_results
        }
        print(f"    ({qtype}) \"{keyword}\" — {len(serp_results)} results, ${cost:.4f}")
        for r in serp_results:
            print(f"         Title: {r['title']}")
            print(f"         URL:   {r['url']}")

        # Extract DM name if not found yet
        if not biz_result["dm_name"]:
            dm, source = extract_name_from_results(serp_results, name)
            if dm:
                biz_result["dm_name"] = dm
                biz_result["dm_query"] = qtype
                biz_result["dm_source"] = source

        # Extract LinkedIn URL
        if not biz_result["linkedin_url"]:
            li = find_linkedin_url(serp_results)
            if li:
                biz_result["linkedin_url"] = li

        time.sleep(0.3)  # small pause between queries

    results_log.append(biz_result)

# ── Step 3: Per-business report ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("[STEP 3] PER-BUSINESS REPORT")
print("=" * 70)
for r in results_log:
    print(f"\n  Business: {r['business']} ({r['domain']})")
    print(f"  DM name found: {'YES — ' + r['dm_name'] if r['dm_name'] else 'No'}")
    if r['dm_name']:
        print(f"  Query type: ({r['dm_query']})  Source: {r['dm_source']}")
    print(f"  LinkedIn URL: {r['linkedin_url'] or 'None'}")
    print(f"  Phone in data: {'Yes — ' + r['phone'] if r['phone'] else 'No'}")

# ── Step 4: Summary table ─────────────────────────────────────────────────────
dm_any = sum(1 for r in results_log if r["dm_name"])
dm_a = sum(1 for r in results_log if r["dm_query"] == "a")
dm_b = sum(1 for r in results_log if r["dm_query"] == "b")
dm_c = sum(1 for r in results_log if r["dm_query"] == "c")
li_any = sum(1 for r in results_log if r["linkedin_url"])
phone_any = sum(1 for r in results_log if r["phone"])
n = len(results_log)

print("\n" + "=" * 70)
print("[STEP 4] SUMMARY TABLE")
print("=" * 70)
print(f"  Total businesses tested: {n}")
print(f"  DM name found (any query): {dm_any} / {n} = {dm_any/n*100:.0f}%")
print(f"  Found via (a) owner:       {dm_a} / {n} = {dm_a/n*100:.0f}%")
print(f"  Found via (b) director:    {dm_b} / {n} = {dm_b/n*100:.0f}%")
print(f"  Found via (c) linkedin:    {dm_c} / {n} = {dm_c/n*100:.0f}%")
print(f"  LinkedIn URL found:        {li_any} / {n} = {li_any/n*100:.0f}%")
print(f"  Phone in data:             {phone_any} / {n} = {phone_any/n*100:.0f}%")
print(f"  Total DFS spend:           ${total_cost:.4f} USD")

# ── Step 5: Revised funnel (if hit rate ≥ 40%) ───────────────────────────────
hit_rate = dm_any / n
if hit_rate >= 0.40:
    print("\n" + "=" * 70)
    print("[STEP 5] REVISED FUNNEL MATH — Ignition tier (600 complete records/month)")
    print("=" * 70)
    # Pool sizes
    post_icp = 9000
    post_free_signal = int(post_icp * 0.35)    # 3,150
    post_website_audit = int(post_free_signal * 0.80)  # 2,520
    post_dfs_rank = post_website_audit  # all get domain_rank_overview
    post_gate = int(post_dfs_rank * 0.50)       # 50% pass gap score ≥60
    dm_found = int(post_gate * hit_rate)
    with_email = int(dm_found * 0.65)           # Leadmagic est 65% hit
    with_mobile = int(with_email * 0.40)        # Leadmagic mobile est 40% of email-found

    # Costs
    cost_dfs_rank = post_dfs_rank * 0.0101
    cost_dfs_serp_owner = post_gate * 0.006     # 3 queries × $0.002
    cost_leadmagic_email = dm_found * 0.015
    cost_leadmagic_mobile = with_email * 0.50 * 0.077  # mobile only for score≥80 (~50%)
    cost_total = cost_dfs_rank + cost_dfs_serp_owner + cost_leadmagic_email + cost_leadmagic_mobile

    print(f"  Post-ICP pool:              {post_icp:,}")
    print(f"  Post-free-signal (35%):     {post_free_signal:,}")
    print(f"  Post-website-audit (80%):   {post_website_audit:,}")
    print(f"  DFS domain_rank_overview:   {post_dfs_rank:,} × $0.0101 = ${cost_dfs_rank:.2f}")
    print(f"  Post-gap-gate (50%):        {post_gate:,}")
    print(f"  DFS SERP owner search:      {post_gate:,} × $0.006 = ${cost_dfs_serp_owner:.2f}")
    print(f"  DM name found ({hit_rate*100:.0f}%):        {dm_found:,}")
    print(f"  Leadmagic email (65%):      {with_email:,} × $0.015 = ${cost_leadmagic_email:.2f}")
    print(f"  Leadmagic mobile (50%):     {with_mobile:,} × $0.077 = ${cost_leadmagic_mobile:.2f}")
    print(f"  Complete records out:       ~{with_mobile:,}")
    print(f"  Total monthly cost:         ${cost_total:.2f} USD")
    print(f"  Cost per complete record:   ${cost_total/max(with_mobile,1):.3f} USD")
else:
    print(f"\n  Hit rate {hit_rate*100:.0f}% < 40% threshold — revised funnel not applicable.")

# ── Write addendum to research doc ───────────────────────────────────────────
OUTPUT_PATH = "/home/elliotbot/clawd/docs/directive-241-research.md"
addendum = [
    "\n\n---\n\n## ADDENDUM 2: DFS SERP Owner Search (Directive #243)\n",
    f"**Generated:** 2026-03-24\n",
    f"**Businesses tested:** {n}\n",
    f"**Total DFS spend:** ${total_cost:.4f} USD\n\n",
    "### Summary Table\n\n",
    f"| Metric | Count | % of {n} |\n",
    "|---|---|---|\n",
    f"| DM name found (any query) | {dm_any} | {dm_any/n*100:.0f}% |\n",
    f"| Found via (a) owner | {dm_a} | {dm_a/n*100:.0f}% |\n",
    f"| Found via (b) director | {dm_b} | {dm_b/n*100:.0f}% |\n",
    f"| Found via (c) linkedin | {dm_c} | {dm_c/n*100:.0f}% |\n",
    f"| LinkedIn URL found | {li_any} | {li_any/n*100:.0f}% |\n",
    f"| Phone available | {phone_any} | {phone_any/n*100:.0f}% |\n\n",
    "### Per-Business Results\n\n",
]
for r in results_log:
    addendum.append(f"**{r['business']}** ({r['domain']}) | suburb: {r['suburb'] or 'unknown'}\n")
    addendum.append(f"- DM name: {r['dm_name'] or 'Not found'}")
    if r['dm_name']:
        addendum.append(f" (query {r['dm_query']}, source: {r['dm_source']})")
    addendum.append(f"\n- LinkedIn: {r['linkedin_url'] or 'None'}\n")
    addendum.append(f"- Phone: {r['phone'] or 'None'}\n\n")
    for qt, qd in r['queries'].items():
        addendum.append(f"  ({qt}) `{qd['keyword']}`\n")
        for res in qd['top3']:
            addendum.append(f"  - [{res['title']}]({res['url']})\n")
    addendum.append("\n")

with open(OUTPUT_PATH, "a") as f:
    f.writelines(addendum)

print(f"\n[DONE] Addendum written to {OUTPUT_PATH}")
print(f"Total cost: ${total_cost:.4f} USD")
