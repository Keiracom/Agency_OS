#!/usr/bin/env python3
"""
Directive #244 — Qualification Gate Rate Research
Tests affordability + need signals across 50 GMaps businesses.
Read-only. No DB writes.
"""
import re, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ssl

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

# ── 50 businesses from gmb_pilot_results (sequential, no cherry-picking) ──────
BUSINESSES = [
    {"name": "ENERGY EQUITY HOLDINGS",         "domain": "ewon.com.au",                        "category": "Non-profit organization",        "rating": 3.1, "reviews": 0},
    {"name": "VISTA MEDIA INTERNATIONAL",       "domain": "vistamedia.com.au",                  "category": "Marketing agency",               "rating": 5.0, "reviews": 0},
    {"name": "HOSPITALITY EQUIPMENT",           "domain": "hospitalitysuppliesexpress.com.au",  "category": "Restaurant supply store",        "rating": 4.8, "reviews": 0},
    {"name": "JONES LANG LASALLE QLD",          "domain": "jll.com.au",                         "category": "Property",                       "rating": None,"reviews": 0},
    {"name": "Hands Across the Water",          "domain": "handsacrossthewater.org.au",         "category": "Charity",                        "rating": 5.0, "reviews": 0},
    {"name": "MUSCLEMANIA FITNESS",             "domain": "musclemania.com.au",                 "category": "Exercise equipment store",       "rating": 4.4, "reviews": 0},
    {"name": "Carlton Australia",               "domain": "carltoninbusiness.com.au",           "category": "Business networking",            "rating": None,"reviews": 0},
    {"name": "CAREWELL HEALTH",                 "domain": "carewell.com.au",                    "category": "Medical equipment",              "rating": 5.0, "reviews": 0},
    {"name": "MARLIN INVESTMENTS",              "domain": "marlingroup.com.au",                 "category": "Property investment",            "rating": 5.0, "reviews": 0},
    {"name": "River Road Transport",            "domain": "riverina.com.au",                    "category": "Agricultural service",           "rating": 5.0, "reviews": 0},
    {"name": "Nice Line Painting",              "domain": "pinkpages.com.au",                   "category": "Painter",                        "rating": 5.0, "reviews": 0},
    {"name": "BEST EVER CLEANING",             "domain": "bestevercleaning.com.au",            "category": "Upholstery cleaning service",    "rating": 4.9, "reviews": 52},
    {"name": "CENTURY 21 TONY MOSES",           "domain": "century21.com.au",                   "category": "Real estate agency",             "rating": 4.6, "reviews": 0},
    {"name": "COVENANT CHRISTIAN SCHOOL",       "domain": "covenant.nsw.edu.au",                "category": "School",                         "rating": None,"reviews": 0},
    {"name": "Meridian Surveys",                "domain": "meridiansurvey.com.au",              "category": "Land surveyor",                  "rating": None,"reviews": 0},
    {"name": "Visually Unique",                 "domain": "visuallyunique.com.au",              "category": "Graphic designer",               "rating": 5.0, "reviews": 33},
    {"name": "Coastal Mattress Direct",         "domain": "coastalmattressdirect.com.au",       "category": "Mattress store",                 "rating": 5.0, "reviews": 0},
    {"name": "TOP LIGHTING",                    "domain": "toplightingonline.com.au",           "category": "Lighting store",                 "rating": 2.1, "reviews": 0},
    {"name": "DAWSON PLUMBING",                 "domain": "dawsonplumbing.com.au",              "category": "Plumber",                        "rating": 4.9, "reviews": 0},
    {"name": "NC ENGINEERING",                  "domain": "nceng.com.au",                       "category": "Corporate office",               "rating": 3.2, "reviews": 0},
    {"name": "WAHROONGA MEDICAL",               "domain": "wahroongagp.com.au",                 "category": "Doctor",                         "rating": 4.9, "reviews": 0},
    {"name": "Keiraville Pharmacy",             "domain": "keiravillepharmacy.com.au",          "category": "Pharmacy",                       "rating": 4.3, "reviews": 0},
    {"name": "SMITH & GRAY",                    "domain": "smithandgray.com.au",                "category": "Furniture maker",                "rating": 5.0, "reviews": 0},
    {"name": "CARMEN REMOVALS",                 "domain": "carmengreens.com.au",                "category": "Moving and storage",             "rating": 4.6, "reviews": 0},
    {"name": "ALPINE NURSERIES",                "domain": "alpinenurseries.com.au",             "category": "Plant nursery",                  "rating": 3.3, "reviews": 0},
    {"name": "UNIQUE ADVISERS",                 "domain": "uniqueadvisers.com.au",              "category": "Financial planner",              "rating": 5.0, "reviews": 0},
    {"name": "The East Chinese Restaurant",     "domain": "theeast.com.au",                     "category": "Chinese restaurant",             "rating": 4.1, "reviews": 0},
    {"name": "The Pioneers Lodge",              "domain": "pioneerslodge.com.au",               "category": "Assisted living facility",       "rating": 5.0, "reviews": 0},
    {"name": "Pittwater RSL",                   "domain": "pittwaterrsl.com.au",                "category": "RSL club",                       "rating": 3.9, "reviews": 0},
    {"name": "CASSINS",                         "domain": "cassins.com.au",                     "category": "Construction company",           "rating": 4.7, "reviews": 0},
    {"name": "WILLIAMSON TOOL & ENGINEERING",   "domain": "willeng.com.au",                     "category": "Mechanical engineer",            "rating": 5.0, "reviews": 1},
    {"name": "BERRIMA'S NATURAL AUSTRALIA",     "domain": "berrimawool.com",                    "category": "Clothing store",                 "rating": 5.0, "reviews": 5},
    {"name": "Domino's Pizza Canley Vale",      "domain": "dominos.com.au",                     "category": "Pizza restaurant",               "rating": 3.8, "reviews": 0},
    {"name": "Simon Ekas Catering",             "domain": "simonekascatering.com.au",           "category": "Caterer",                        "rating": 4.8, "reviews": 37},
    {"name": "Lounge Lovers",                   "domain": "loungelovers.com.au",                "category": "Furniture store",                "rating": 4.6, "reviews": 0},
    {"name": "SHIRDI BABA SOCIETY",             "domain": "shirdisai.org.au",                   "category": "Hindu temple",                   "rating": 4.9, "reviews": 458},
    {"name": "NETTEX AUSTRALIA",                "domain": "nettex.au",                          "category": "Wholesaler",                     "rating": 4.2, "reviews": 33},
    {"name": "COMPLETE CARE CHIRO",             "domain": "completecarechiro.com.au",           "category": "Chiropractor",                   "rating": 5.0, "reviews": 0},
    {"name": "WATCH US",                        "domain": "watchus.com.au",                     "category": "Watch store",                    "rating": 4.3, "reviews": 0},
    {"name": "CHINA PROCUREMENT",               "domain": "chinadirectsourcing.com.au",         "category": "International trade",            "rating": 4.7, "reviews": 67},
    {"name": "SAPATO IMPORTS",                  "domain": "sapatoimports.com",                  "category": "Shoe store",                     "rating": 5.0, "reviews": 0},
    {"name": "STRATHFIELD HOTEL",               "domain": "strathfieldhotel.com.au",            "category": "Hotel",                          "rating": 3.5, "reviews": 831},
    {"name": "NATURAL PLAY CHILDREN'S CENTRE",  "domain": "naturalplaychildrenscentre.com.au",  "category": "Day care center",                "rating": 4.9, "reviews": 9},
    {"name": "GEORGE GOOLEY",                   "domain": "georgegooley.com.au",                "category": "Clothing store",                 "rating": None,"reviews": 0},
    {"name": "NATIONAL PROPERTY PORTFOLIOS",    "domain": "nationalpropertyportfolios.com",     "category": "Property management",            "rating": None,"reviews": 0},
    # Extra from gmb_vendor_test_dfs to reach 50
    {"name": "Business Telecom",                "domain": "businesstelecom.com.au",             "category": "Telecom",                        "rating": 4.8, "reviews": 965},
    {"name": "Absolute Business Brokers",       "domain": "absolutbusinessbrokers.com.au",      "category": "Business broker",                "rating": 4.6, "reviews": 304},
    {"name": "Outback Solar",                   "domain": "outbacksolar.com.au",                "category": "Solar panels",                   "rating": 5.0, "reviews": 57},
    {"name": "Provincial Home Living",          "domain": "provincialhomeliving.com.au",        "category": "Furniture store",                "rating": 4.7, "reviews": 33},
    {"name": "Adelaide Tarp Specialists",       "domain": "tarps.com.au",                       "category": "Tarp/canvas supplier",           "rating": 4.2, "reviews": 20},
]

# ── Website signal checker ────────────────────────────────────────────────────
def fetch_html(domain, timeout=8):
    for scheme in ("https", "http"):
        try:
            url = f"{scheme}://www.{domain}" if not domain.startswith("www.") else f"{scheme}://{domain}"
            req = Request(url, headers={"User-Agent": UA})
            resp = urlopen(req, timeout=timeout, context=CTX)
            html = resp.read(200_000).decode("utf-8", errors="ignore")
            return html, url
        except Exception:
            pass
    try:
        url = f"https://{domain}"
        req = Request(url, headers={"User-Agent": UA})
        resp = urlopen(req, timeout=timeout, context=CTX)
        return resp.read(200_000).decode("utf-8", errors="ignore"), url
    except Exception as e:
        return None, None

def check_signals(b):
    html, final_url = fetch_html(b["domain"])
    signals = {
        # Affordability
        "A1_gads": False,    # Google Ads pixel
        "A2_fbads": False,   # Facebook pixel
        "A3_pro_site": False,# Professional site (has nav, multiple pages)
        "A5_10plus_reviews": b["reviews"] >= 10,
        "A6_staff_page": False, # team/staff/about page
        "A8_years_3plus": False,# 3+ years
        # Need
        "N1_no_pixels": False,  # No tracking at all
        "N2_ads_no_conv": False, # Ads but no conversion tracking
        "N3_not_mobile": False,  # No viewport meta
        "N4_outdated": False,    # Old copyright
        "N5_rating_below4": (b["rating"] is not None and b["rating"] < 4.0),
        "N6_under10_reviews": b["reviews"] < 10,
        "N7_no_social": False,  # No social links
        "fetch_ok": html is not None,
    }

    if html is None:
        signals["N1_no_pixels"] = True  # Can't verify = assume no tracking
        signals["N7_no_social"] = True
        return signals

    h = html.lower()

    # A1 — Google Ads
    signals["A1_gads"] = any(x in h for x in ["googleadservices", "aw-", "google_conversion", "gtag('config', 'aw-", "googletag.pubads"])

    # A2 — Facebook pixel
    signals["A2_fbads"] = any(x in h for x in ["fbq(", "connect.facebook.net", "facebook.com/tr", "fbevents.js"])

    # A3 — Professional site (basic heuristic: has nav menu, multiple internal links)
    nav_count = len(re.findall(r'<nav|<ul.*?class.*?nav|<div.*?menu', h))
    internal_links = len(re.findall(rf'href=["\']/?(?!http|mailto|tel|#)[^"\']+["\']', h))
    signals["A3_pro_site"] = nav_count >= 1 or internal_links >= 5

    # A6 — Staff/team page
    signals["A6_staff_page"] = any(x in h for x in ["our team", "meet the team", "our staff", "about us", "meet our", "/team", "/about", "/staff"])

    # A8 — Years in business (look for 3+ year old copyright or "est.", "founded", "since")
    year_m = re.findall(r'(?:©|copyright|est\.?|since|founded)\s*(\d{4})', h)
    if year_m:
        oldest = min(int(y) for y in year_m if 1990 <= int(y) <= 2030)
        signals["A8_years_3plus"] = (2026 - oldest) >= 3

    # N1 — No tracking pixels
    has_any_pixel = signals["A1_gads"] or signals["A2_fbads"] or "google-analytics" in h or "gtag(" in h or "ga(" in h or "_gaq" in h
    signals["N1_no_pixels"] = not has_any_pixel

    # N2 — Has ads but no conversion tracking
    if signals["A1_gads"] or signals["A2_fbads"]:
        has_conv = any(x in h for x in ["gtag('event'", "fbq('track'", "conversion_event", "addtocart", "purchase"])
        signals["N2_ads_no_conv"] = not has_conv

    # N3 — Not mobile responsive (no viewport)
    signals["N3_not_mobile"] = "viewport" not in h

    # N4 — Outdated (copyright 2020 or older)
    copy_years = re.findall(r'(?:©|copyright)\s*(\d{4})', h)
    if copy_years:
        newest = max(int(y) for y in copy_years if 1990 <= int(y) <= 2030)
        signals["N4_outdated"] = newest <= 2020

    # N7 — No social media
    has_social = any(x in h for x in ["facebook.com/", "instagram.com/", "linkedin.com/", "twitter.com/", "tiktok.com/"])
    signals["N7_no_social"] = not has_social

    return signals

# ── Run parallel ──────────────────────────────────────────────────────────────
print("=" * 70)
print("DIRECTIVE #244 — QUALIFICATION GATE RATE")
print("=" * 70)
print(f"Testing {len(BUSINESSES)} businesses...\n")

results = [None] * len(BUSINESSES)

with ThreadPoolExecutor(max_workers=8) as ex:
    future_map = {ex.submit(check_signals, b): i for i, b in enumerate(BUSINESSES)}
    for f in as_completed(future_map):
        i = future_map[f]
        try:
            results[i] = f.result()
        except Exception as e:
            results[i] = {"fetch_ok": False, "A1_gads": False, "A2_fbads": False,
                          "A3_pro_site": False, "A5_10plus_reviews": BUSINESSES[i]["reviews"] >= 10,
                          "A6_staff_page": False, "A8_years_3plus": False,
                          "N1_no_pixels": True, "N2_ads_no_conv": False, "N3_not_mobile": True,
                          "N4_outdated": False, "N5_rating_below4": False,
                          "N6_under10_reviews": BUSINESSES[i]["reviews"] < 10,
                          "N7_no_social": True}
        print(f"  [{i+1}/50] done: {BUSINESSES[i]['name']}")

# ── Per-business report ───────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PER-BUSINESS REPORT")
print("=" * 70)

qual_count = 0
afford_only = 0
need_only = 0
neither = 0
both_count = 0

# Signal tallies
a_tally = {"A1_gads": 0, "A2_fbads": 0, "A3_pro_site": 0, "A5_10plus_reviews": 0,
           "A6_staff_page": 0, "A8_years_3plus": 0}
n_tally = {"N1_no_pixels": 0, "N2_ads_no_conv": 0, "N3_not_mobile": 0,
           "N4_outdated": 0, "N5_rating_below4": 0, "N6_under10_reviews": 0, "N7_no_social": 0}

pair_tally = {}

for i, (b, s) in enumerate(zip(BUSINESSES, results)):
    a_sigs = [k for k in a_tally if s.get(k)]
    n_sigs = [k for k in n_tally if s.get(k)]

    for k in a_sigs: a_tally[k] += 1
    for k in n_sigs: n_tally[k] += 1

    has_a = len(a_sigs) > 0
    has_n = len(n_sigs) > 0
    qualified = has_a and has_n

    if qualified: both_count += 1
    elif has_a: afford_only += 1
    elif has_n: need_only += 1
    else: neither += 1

    status = "✅ QUALIFIED" if qualified else ("⚠️ AFFORD-ONLY" if has_a else ("⚠️ NEED-ONLY" if has_n else "❌ NEITHER"))

    print(f"\n[{i+1}] {b['name']} ({b['category']})")
    print(f"     Domain: {b['domain']} | Rating: {b['rating']} | Reviews: {b['reviews']}")
    print(f"     Fetch: {'OK' if s.get('fetch_ok') else 'FAILED'}")
    print(f"     Affordability: {a_sigs if a_sigs else 'NONE'}")
    print(f"     Need: {n_sigs if n_sigs else 'NONE'}")
    print(f"     → {status}")

    # Track signal pairs
    for a in a_sigs:
        for n in n_sigs:
            pair = f"{a}+{n}"
            pair_tally[pair] = pair_tally.get(pair, 0) + 1

# ── Summary ───────────────────────────────────────────────────────────────────
n_biz = len(BUSINESSES)
afford_any = both_count + afford_only
need_any = both_count + need_only

print("\n" + "=" * 70)
print("SUMMARY TABLE")
print("=" * 70)
print(f"  Total businesses: {n_biz}")
print(f"  Fetch succeeded:  {sum(1 for s in results if s.get('fetch_ok'))}/{n_biz}")
print()
print(f"  Have 1+ affordability signal: {afford_any}/{n_biz} = {afford_any/n_biz*100:.0f}%")
print(f"  Have 1+ need signal:          {need_any}/{n_biz} = {need_any/n_biz*100:.0f}%")
print(f"  BOTH (qualified):             {both_count}/{n_biz} = {both_count/n_biz*100:.0f}%")
print(f"  Affordability only:           {afford_only}/{n_biz}")
print(f"  Need only:                    {need_only}/{n_biz}")
print(f"  Neither:                      {neither}/{n_biz}")
print()
print("  Affordability signal breakdown:")
for k, v in sorted(a_tally.items(), key=lambda x: -x[1]):
    print(f"    {k}: {v}/{n_biz} = {v/n_biz*100:.0f}%")
print()
print("  Need signal breakdown:")
for k, v in sorted(n_tally.items(), key=lambda x: -x[1]):
    print(f"    {k}: {v}/{n_biz} = {v/n_biz*100:.0f}%")
print()
print("  Top signal pairs (A+N combinations):")
for pair, count in sorted(pair_tally.items(), key=lambda x: -x[1])[:10]:
    print(f"    {pair}: {count}")

# ── Revised funnel math ───────────────────────────────────────────────────────
qual_rate = both_count / n_biz
print(f"\n{'=' * 70}")
print("REVISED FUNNEL MATH — Ignition tier (600 qualified complete records/month)")
print("=" * 70)
print(f"  Qualification gate rate: {qual_rate*100:.0f}%")
print()

# Working backwards from 600
target = 600
dm_hit = 0.59
email_hit = 0.65
mobile_hit = 0.40
# complete record = DM name + email + mobile
# survival: qual_rate × dm_hit × email_hit × mobile_hit
complete_rate = qual_rate * dm_hit * email_hit * mobile_hit
discoveries_needed = int(target / complete_rate) if complete_rate > 0 else 99999
post_gate = int(discoveries_needed * qual_rate)

print(f"  Pipeline survival rate: {qual_rate:.0%} × {dm_hit:.0%} (DM) × {email_hit:.0%} (email) × {mobile_hit:.0%} (mobile) = {complete_rate:.1%}")
print(f"  Discoveries needed for 600 complete: ~{discoveries_needed:,}")
print(f"  Post-qualification pool: ~{post_gate:,}")
print()
print("  Monthly cost breakdown:")
cost_dfs_rank = discoveries_needed * 0.0101
cost_serp_owner = post_gate * 0.006
cost_email = int(post_gate * dm_hit) * 0.015
cost_mobile = int(post_gate * dm_hit * email_hit * 0.50) * 0.077
total = cost_dfs_rank + cost_serp_owner + cost_email + cost_mobile
print(f"    DFS domain_rank_overview ({discoveries_needed:,} × $0.0101): ${cost_dfs_rank:.2f}")
print(f"    DFS SERP owner search ({post_gate:,} × $0.006):              ${cost_serp_owner:.2f}")
print(f"    Leadmagic email ({int(post_gate * dm_hit):,} × $0.015):               ${cost_email:.2f}")
print(f"    Leadmagic mobile ({int(post_gate * dm_hit * email_hit * 0.5):,} × $0.077):              ${cost_mobile:.2f}")
print(f"    TOTAL:                                                      ${total:.2f} USD/month")
print(f"    Cost per complete record: ${total/target:.3f} USD")
print()
print("  Note: YP scraping (Stage 1), ICP filter, website audit = $0")
print("  BD GMB dependency: ZERO in this funnel (YP-first discovery)")
