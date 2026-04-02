"""
DIRECTIVE #300k — Integration Test: Stage 11
Haiku Evidence Refinement — Final Prospect Cards

260 DM-found prospects. Haiku receives ALL accumulated intelligence
and produces the final prospect card copy.
Cost: ~$0.80 (260 × $0.003 Haiku)
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

import httpx
from src.config.settings import settings
from src.pipeline.intelligence import refine_evidence
from src.utils.asyncpg_connection import get_asyncpg_pool

BASE_DIR   = os.path.dirname(__file__)
OUT_DIR    = os.path.join(BASE_DIR, "output")
OUTPUT     = os.path.join(OUT_DIR, "300k_cards.json")

HAIKU_IN_COST  = 0.80  / 1_000_000
HAIKU_OUT_COST = 4.0   / 1_000_000
SEM_HAIKU      = asyncio.Semaphore(55)
BD_SNAPSHOT_ID = "sd_mnfd94hgsyllcqjlx"


import re as _re

# ── Helper: placeholder email filter ──────────────────────────────────────────

# Filters out HTML template placeholder emails only.
# DO NOT add real business emails like info@, admin@, contact@ — those are legitimate.
_PLACEHOLDER_RE = _re.compile(
    r"example@|test@|you@|your@|user@|mail@|email@|no-?reply@|noreply@"
    r"|example\.com|yourdomain|placeholder|samplesite",
    _re.IGNORECASE,
)


def _is_placeholder_email(email: str) -> bool:
    return bool(email and _PLACEHOLDER_RE.search(email))


# ── Helper: DM contamination check ────────────────────────────────────────────

def _is_contaminated_dm(dm: dict) -> tuple[bool, str]:
    """Returns (is_contaminated, reason)."""
    name = dm.get("dm_name") or ""
    linkedin = dm.get("dm_linkedin_url") or ""
    domain = dm.get("domain") or ""

    # ALL CAPS name = company profile
    if name and name == name.upper() and len(name.split()) >= 2:
        return True, f"ALL_CAPS_NAME: {name}"

    # Non-AU LinkedIn profile on AU domain
    if domain.endswith(".com.au") or domain.endswith(".au"):
        non_au_prefixes = ["in.linkedin.com", "uk.linkedin.com", "de.linkedin.com",
                           "fr.linkedin.com", "ca.linkedin.com"]
        for prefix in non_au_prefixes:
            if prefix in linkedin:
                return True, f"NON_AU_PROFILE: {prefix}"

    return False, ""


# ── Helper: business name extractors ─────────────────────────────────────────

def _extract_biz_from_lico_desc(desc: str) -> str:
    """'FOCUS DENTAL GROUP | 6 followers' → 'Focus Dental Group'"""
    if desc and "|" in desc:
        name = desc.split("|")[0].strip()
        if name and name == name.upper() and len(name) > 2:
            name = name.title()
        return name
    return ""


_TITLE_SEP_RE = _re.compile(r'\s*[|—–\-]\s*')
_TITLE_FILLER_RE = _re.compile(
    r'^(home|welcome|about|dentist|dental|clinic|medical|law|legal|accounting'
    r'|plumber|electrician|builder|#\d+|best|top|leading|professional)',
    _re.IGNORECASE,
)


def _extract_biz_from_title_tag(title: str) -> str:
    """'#1 Dentist in Browns Plains - Dental Aspects' → 'Dental Aspects'"""
    if not title:
        return ""
    title = title.replace("&amp;", "&").replace("&#039;", "'")
    parts = [p.strip() for p in _TITLE_SEP_RE.split(title) if p.strip()]
    if not parts:
        return ""
    last = parts[-1]
    first = parts[0]
    if 1 <= len(last.split()) <= 5 and not _TITLE_FILLER_RE.match(last):
        return last[:60]
    if 1 <= len(first.split()) <= 5 and not _TITLE_FILLER_RE.match(first):
        return first[:60]
    return ""


def _extract_biz_from_title(title: str) -> str:
    """'Owner at Bright Smile Dental' → 'Bright Smile Dental'"""
    if title and " at " in title.lower():
        return title.split(" at ")[-1].strip()
    return ""


# ── Helper: location extractor ────────────────────────────────────────────────

_AU_CITIES_RE = _re.compile(
    r'\b(Sydney|Melbourne|Brisbane|Perth|Adelaide|Hobart|Darwin|Canberra'
    r'|Gold Coast|Sunshine Coast|Newcastle|Wollongong|Geelong'
    r'|NSW|VIC|QLD|SA|WA|TAS|NT|ACT)\b',
    _re.IGNORECASE,
)


def _extract_location_from_desc(desc: str) -> str:
    """Try to find a suburb/city in LinkedIn company description."""
    m = _AU_CITIES_RE.search(desc or "")
    return m.group(0) if m else ""


_STATE_ABBR = {
    "New South Wales": "NSW", "Victoria": "VIC", "Queensland": "QLD",
    "Western Australia": "WA", "South Australia": "SA", "Tasmania": "TAS",
    "Australian Capital Territory": "ACT", "Northern Territory": "NT",
}


def _shorten_location(location: str) -> str:
    """'Sydney, New South Wales, Australia' → 'Sydney NSW'"""
    if not location:
        return ""
    for full, abbr in _STATE_ABBR.items():
        location = location.replace(full, abbr)
    location = location.replace(", Australia", "").strip().rstrip(",").strip()
    return location[:50]


def _extract_location_from_title(title: str) -> str:
    """'#1 Dentist in Browns Plains & Regents Park' → 'Browns Plains'"""
    m = _AU_CITIES_RE.search(title or "")
    return m.group(0) if m else ""


# ── Data loading helpers ──────────────────────────────────────────────────────

def load_json(filename: str) -> dict | list:
    path = os.path.join(OUT_DIR, filename)
    with open(path) as f:
        return json.load(f)


def check_bd_snapshot() -> list[dict]:
    """One-time synchronous check of the BD snapshot."""
    import httpx as hx
    from src.integrations.brightdata_client import BRIGHTDATA_SCRAPER_KEY
    key = BRIGHTDATA_SCRAPER_KEY
    try:
        r = hx.get(
            f"https://api.brightdata.com/datasets/v3/progress/{BD_SNAPSHOT_ID}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=8,
        )
        status = r.json().get("status")
        print(f"BD snapshot {BD_SNAPSHOT_ID}: status={status}", flush=True)
        if status == "ready":
            dl = hx.get(
                f"https://api.brightdata.com/datasets/v3/snapshot/{BD_SNAPSHOT_ID}?format=json",
                headers={"Authorization": f"Bearer {key}"},
                timeout=60,
            )
            if dl.status_code == 200:
                records = dl.json()
                print(f"  Downloaded {len(records)} BD profile records", flush=True)
                return records if isinstance(records, list) else [records]
        return []
    except Exception as e:
        print(f"BD snapshot check failed: {e}", flush=True)
        return []


def build_domain_index(dm_found: list[dict]) -> dict[str, dict]:
    """Load all stage outputs and merge into one record per domain."""
    # Load sources
    comp_data   = load_json("300c_comprehend.json")
    intent_data = load_json("300e_intent.json")
    email_data  = load_json("300g_v2_email.json")
    combined    = load_json("300gh_combined.json")
    lico_data   = load_json("300i_linkedin_co.json")
    lidm_data   = load_json("300j_linkedin_dm.json")
    scrape_data = load_json("300b_scrape.json")

    # Load affordability data (has entity/ABN info)
    try:
        afford_data = load_json("300d_afford.json")
        afford_map  = {d["domain"]: d for d in afford_data.get("domains", [])}
    except Exception:
        afford_map = {}

    # Build lookup maps
    comp_map   = {d["domain"]: d for d in comp_data.get("domains", [])}
    intent_map = {d["domain"]: d for d in intent_data.get("domains", [])}
    email_map  = {d.get("domain"): d for d in email_data.get("domains", [])}
    mobile_map = {d["domain"]: d for d in combined.get("domains", [])}
    lico_map   = {d["domain"]: d for d in lico_data.get("domains", []) if d.get("data")}
    lidm_map   = {d["domain"]: d for d in lidm_data.get("domains", []) if d.get("data")}
    scrape_map = {d["domain"]: d for d in scrape_data.get("domains", [])}

    index = {}
    for p in dm_found:
        domain = p["domain"]
        index[domain] = {
            "dm":      p,
            "comp":    comp_map.get(domain, {}),
            "intent":  intent_map.get(domain, {}),
            "email":   email_map.get(domain, {}),
            "mobile":  mobile_map.get(domain, {}),
            "lico":    lico_map.get(domain, {}).get("data") or {},
            "lidm":    lidm_map.get(domain, {}).get("data") or {},
            "afford":  afford_map.get(domain, {}),
            "scrape":  scrape_map.get(domain, {}),
        }
    return index


async def upsert_card(pool, domain: str, card: dict) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE business_universe SET
                    pipeline_stage = GREATEST(pipeline_stage, 11)
                WHERE domain = $1
                """,
                domain,
            )
    except Exception:
        pass


async def process_domain(
    domain: str,
    data: dict,
    pool,
    done: list,
    total: int,
    t0: float,
) -> dict:
    dm     = data["dm"]
    comp   = data["comp"]
    intent = data["intent"]
    email  = data["email"]
    mobile = data["mobile"]
    lico   = data["lico"]
    lidm   = data["lidm"]
    scrape = data.get("scrape", {})

    # ── DM contamination check ────────────────────────────────────────────────
    is_bad, bad_reason = _is_contaminated_dm(dm)
    if is_bad:
        return {
            "domain": domain,
            "category": dm.get("category", ""),
            "intent_band": intent.get("intent_band", ""),
            "intent_score": intent.get("intent_score", 0),
            "dm_found": False,
            "dm_contamination_reason": bad_reason,
            "dm_name": None,
            "dm_title": None,
            "dm_email": None,
            "dm_email_verified": False,
            "dm_mobile": None,
            "dm_linkedin": None,
            "channels_available": [],
            "headline_signal": "",
            "recommended_service": "",
            "outreach_angle": "",
            "evidence_statements": [],
            "draft_email_subject": "",
            "draft_email_body": "",
            "haiku_tokens_in": 0,
            "haiku_tokens_out": 0,
            "cost_usd": 0,
            "_skipped": True,
        }

    # ── Resolve contact fields ────────────────────────────────────────────────
    raw_email   = email.get("email") or mobile.get("email") or None
    dm_email    = raw_email if raw_email and not _is_placeholder_email(raw_email) else None
    dm_email_v  = email.get("email_verified", False) if dm_email else False
    dm_mobile   = mobile.get("mobile") or None
    dm_linkedin = dm.get("dm_linkedin_url")
    landline    = (mobile.get("contact_data_prefill") or {}).get("company_phone")
    company_email = (mobile.get("contact_data_prefill") or {}).get("company_email")

    channels = []
    if dm_email:    channels.append("email")
    if dm_linkedin: channels.append("linkedin")
    if dm_mobile:   channels.append("mobile")
    if landline:    channels.append("landline")

    # ── Derive business name & location ──────────────────────────────────────
    comp_comprehension = comp.get("comprehension") or {}

    # Business name priority: lico > dm_title > lidm headline > HTML title > domain stem
    lico_biz         = _extract_biz_from_lico_desc(lico.get("description", ""))
    dm_title_biz     = _extract_biz_from_title(dm.get("dm_title", ""))
    lidm_biz         = _extract_biz_from_title(lidm.get("headline", ""))
    scrape_title_biz = _extract_biz_from_title_tag(scrape.get("title", ""))
    domain_stem      = (domain[4:] if domain.startswith("www.") else domain).split(".")[0].replace("-", " ").title()
    business_name    = (lico_biz or dm_title_biz or lidm_biz or scrape_title_biz or domain_stem)[:60]

    # Location priority: lidm > lico desc > comp signals > HTML title > empty
    lidm_location = _shorten_location(lidm.get("location") or "")
    lico_location = _extract_location_from_desc(lico.get("description", ""))
    comp_location_sigs = (comp.get("comprehension") or {}).get("location_signals") or []
    comp_location = next(
        (s for s in comp_location_sigs if s and s.lower() != "australia"),
        ""
    )
    scrape_location = _extract_location_from_title(scrape.get("title", ""))
    location = (lidm_location or lico_location or comp_location or scrape_location or "")[:50]

    # ── Build refine_evidence inputs ──────────────────────────────────────────
    intent_d = {
        "band":           intent.get("intent_band", "UNKNOWN"),
        "score":          intent.get("intent_score", 0),
        "primary_signal": "",
        "evidence":       intent.get("evidence", []),
    }

    review_d = {}  # GMB review text not available

    website_d = {
        "services":         comp_comprehension.get("services", []),
        "pain_indicators":  comp_comprehension.get("pain_indicators", []),
        "business_maturity": comp_comprehension.get("business_maturity", "unknown"),
        "has_ads":          intent.get("google_ads_active", False),
        "ad_count":         intent.get("google_ads_count", 0),
        "gmb_found":        intent.get("gmb_found", False),
        "gmb_rating":       intent.get("gmb_rating"),
        "gmb_review_count": intent.get("gmb_review_count", 0),
        "has_booking":      (comp_comprehension.get("technology_signals") or {}).get("has_booking_system", False),
        "has_analytics":    (comp_comprehension.get("technology_signals") or {}).get("has_analytics", False),
        "has_conversion":   (comp_comprehension.get("technology_signals") or {}).get("has_conversion_tracking", False),
        "business_name":    business_name,
        "dm_name":          dm.get("dm_name"),
        "dm_title":         dm.get("dm_title"),
        "location":         location,
        "category":         dm.get("category"),
        "linkedin_company": {
            "followers":      lico.get("follower_count"),
            "activity_level": lico.get("activity_level"),
            "job_postings":   lico.get("job_postings", 0),
        } if lico else None,
        "dm_profile": {
            "headline":       lidm.get("headline"),
            "connections":    lidm.get("connections_count"),
            "activity_level": lidm.get("activity_level"),
        } if lidm else None,
    }

    # Call refine_evidence
    t_haiku = time.monotonic()
    async with SEM_HAIKU:
        try:
            refined = await refine_evidence(domain, intent_d, review_d, website_d)
        except Exception as exc:
            refined = {
                "evidence_statements": [],
                "headline_signal": str(exc),
                "recommended_service": "",
                "outreach_angle": "",
                "_error": str(exc),
            }
    haiku_ms = round((time.monotonic() - t_haiku) * 1000)

    # Estimate tokens (Haiku prompt ~600 in, ~300 out)
    tok_in  = 600
    tok_out = 300
    cost    = tok_in * HAIKU_IN_COST + tok_out * HAIKU_OUT_COST

    card = {
        "domain":          domain,
        "category":        dm.get("category", ""),
        "business_name":   business_name,
        "location":        location,
        "intent_band":     intent.get("intent_band", ""),
        "intent_score":    intent.get("intent_score", 0),
        "dm_name":         dm.get("dm_name"),
        "dm_title":        dm.get("dm_title"),
        "dm_email":        dm_email,
        "dm_email_verified": dm_email_v,
        "dm_mobile":       dm_mobile,
        "dm_linkedin":     dm_linkedin,
        "company_email":   company_email,
        "landline":        landline,
        "channels_available": channels,
        "headline_signal":     refined.get("headline_signal", ""),
        "recommended_service": refined.get("recommended_service", ""),
        "outreach_angle":      refined.get("outreach_angle", ""),
        "evidence_statements": refined.get("evidence_statements", []),
        "draft_email_subject": refined.get("draft_email_subject", ""),
        "draft_email_body":    refined.get("draft_email_body", ""),
        "haiku_tokens_in":  tok_in,
        "haiku_tokens_out": tok_out,
        "haiku_ms":         haiku_ms,
        "cost_usd":         round(cost, 5),
    }

    await upsert_card(pool, domain, card)

    done[0] += 1
    if done[0] % 25 == 0:
        elapsed = time.monotonic() - t0
        rate = done[0] / elapsed
        eta  = (total - done[0]) / rate if rate > 0 else 0
        print(f"  {done[0]}/{total} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

    return card


async def main():
    print("=" * 60)
    print("DIRECTIVE #300k — Stage 11: Haiku Evidence Refinement")
    print("260 DM-found prospects → final prospect cards")
    print("=" * 60)

    # TASK A: Check BD snapshot
    bd_records = check_bd_snapshot()

    # Load DM-found list
    dm_data  = load_json("300f_dm.json")
    dm_found = [d for d in dm_data["domains"] if d.get("dm_found")]
    print(f"\nLoaded {len(dm_found)} DM-found domains")

    # If BD returned data, save to 300j for use in index
    if bd_records:
        profile_map = {}
        for rec in bd_records:
            url = (rec.get("input") or {}).get("url") or rec.get("input_url") or rec.get("url", "")
            profile_map[url] = rec
        # Update 300j with BD data
        j_data = load_json("300j_linkedin_dm.json")
        for row in j_data["domains"]:
            rec = profile_map.get(row.get("dm_linkedin_url"))
            if rec and not row.get("data"):
                raw_activity = rec.get("activity") or []
                row["data"] = {
                    "headline": rec.get("occupation") or "",
                    "connections_count": rec.get("connections"),
                    "location": rec.get("city"),
                    "activity_level": ("active" if len(raw_activity) >= 8
                                       else "moderate" if len(raw_activity) >= 2
                                       else "lurker"),
                    "recent_posts": [{"text": (p.get("title") or "")[:300]} for p in raw_activity[:3]],
                    "career_history": [],
                    "skills": [],
                    "cost_usd": "0.00075",
                }
                row["scraped"] = True
        with open(os.path.join(OUT_DIR, "300j_linkedin_dm.json"), "w") as f:
            json.dump(j_data, f, indent=2, default=str)
        print(f"  Merged {len(bd_records)} BD profiles into 300j", flush=True)

    # Build merged index
    index = build_domain_index(dm_found)

    # Init DB pool
    dsn  = settings.database_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    pool = await get_asyncpg_pool(dsn, min_size=1, max_size=20)

    t0    = time.monotonic()
    done  = [0]
    total = len(dm_found)

    tasks = [
        process_domain(p["domain"], index[p["domain"]], pool, done, total, t0)
        for p in dm_found
        if p["domain"] in index
    ]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.monotonic() - t0
    await pool.close()

    # Normalise
    cards: list[dict] = []
    errors = 0
    for i, r in enumerate(raw_results):
        if isinstance(r, Exception):
            cards.append({"domain": dm_found[i]["domain"], "_exception": str(r)})
            errors += 1
        else:
            cards.append(r)

    ok = [c for c in cards if not c.get("_exception")]

    # ── STATS ──
    total_cost = sum(c.get("cost_usd", 0) for c in ok)

    has_email    = sum(1 for c in ok if c.get("dm_email"))
    has_v_email  = sum(1 for c in ok if c.get("dm_email_verified"))
    has_mobile   = sum(1 for c in ok if c.get("dm_mobile"))
    has_linkedin = sum(1 for c in ok if c.get("dm_linkedin"))
    has_landline = sum(1 for c in ok if c.get("landline"))
    has_all4     = sum(1 for c in ok if len(c.get("channels_available", [])) >= 4)

    svc_dist: dict[str, int] = {}
    for c in ok:
        svc = c.get("recommended_service", "Unknown")
        svc_dist[svc] = svc_dist.get(svc, 0) + 1

    print()
    print("=" * 60)
    print("=== TASK C REPORT ===")
    print()
    print(f"1. BD snapshot: {'READY — {len(bd_records)} profiles downloaded' if bd_records else 'Still running — proceeded without it'}")
    print(f"2. Processed: {len(cards)} | Errors: {errors}")
    print(f"3. Haiku cost: ${total_cost:.3f} USD")
    print(f"4. Wall-clock: {elapsed:.1f}s")
    print()
    print("5. CHANNEL COVERAGE (260 cards):")
    print(f"   Has email:          {has_email}")
    print(f"   Has verified email: {has_v_email}")
    print(f"   Has mobile:         {has_mobile}")
    print(f"   Has LinkedIn:       {has_linkedin}")
    print(f"   Has landline:       {has_landline}")
    print(f"   Has all 4 channels: {has_all4}")
    print()
    print("6. SERVICE DISTRIBUTION:")
    for svc, count in sorted(svc_dist.items(), key=lambda x: -x[1])[:8]:
        print(f"   {svc}: {count}")

    # Show 5 sample cards
    print()
    print("7. SAMPLE CARDS (5):")
    samples = [c for c in ok if c.get("evidence_statements") and c.get("headline_signal")][:5]
    for c in samples:
        print(f"\n[{c['domain']} — {c.get('intent_band')} — {c.get('recommended_service')}]")
        print(json.dumps({
            k: c[k] for k in [
                "business_name", "dm_name", "dm_title", "dm_email", "dm_mobile",
                "channels_available", "headline_signal", "recommended_service",
                "outreach_angle", "evidence_statements",
                "draft_email_subject", "draft_email_body",
            ] if k in c
        }, indent=2, default=str))

    # Save
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump({
            "stage": "300k_cards",
            "summary": {
                "total": len(cards), "ok": len(ok), "errors": errors,
                "haiku_cost_usd": round(total_cost, 3),
                "elapsed_seconds": round(elapsed, 1),
                "channel_coverage": {
                    "email": has_email, "verified_email": has_v_email,
                    "mobile": has_mobile, "linkedin": has_linkedin,
                    "landline": has_landline, "all_4": has_all4,
                },
                "service_distribution": svc_dist,
            },
            "cards": cards,
        }, f, indent=2, default=str)
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
