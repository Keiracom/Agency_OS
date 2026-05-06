"""
Validation script: ContactOut 20-profile AU SMB enrichment test.
Uses synchronous httpx directly (standalone runner, not async).
"""

import os
import sys
import json
import httpx

CONTACTOUT_API_KEY = os.environ.get("CONTACTOUT_API_KEY", "")
if not CONTACTOUT_API_KEY:
    # Try loading from .env file
    env_path = os.path.expanduser("~/.config/agency-os/.env")
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("CONTACTOUT_API_KEY="):
                CONTACTOUT_API_KEY = line.split("=", 1)[1].strip()
                break

if not CONTACTOUT_API_KEY:
    print("ERROR: CONTACTOUT_API_KEY not set")
    sys.exit(1)

print(f"ContactOut key: {CONTACTOUT_API_KEY[:8]}...")

PROFILES = [
    {
        "url": "https://au.linkedin.com/in/joealphonse",
        "known_company": "Oatlands Dental",
        "known_domain": "oatlandsdental.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/duncancopp",
        "known_company": "Paddington Dental Surgery",
        "known_domain": "thepaddingtondentalsurgery.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/stephen-wilson-39a96b41",
        "known_company": "Allabout Plumbing",
        "known_domain": "allaboutplumbing.net.au",
    },
    {
        "url": "https://au.linkedin.com/in/karl-abel-b50b494a",
        "known_company": "Melbourne Plumbing Group",
        "known_domain": "melbourneplumbinggroup.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/andrew-scott-55635612",
        "known_company": "Highbury Plumbing",
        "known_domain": "highburyplumbing.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/sam-bell-b7aa12b6",
        "known_company": "Evans Plumbing",
        "known_domain": "evansplumbing.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/sean-parsonage-b3899422",
        "known_company": "Spadental",
        "known_domain": "spadental.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/david-jones-16112b116",
        "known_company": "North Shore Dental",
        "known_domain": "northsydneydental.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/josh-wilkinson-7978ab282",
        "known_company": "McGrath Plumbing",
        "known_domain": "mcgp.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/michael-garbett-2b2108aa",
        "known_company": "Mortons Solicitors",
        "known_domain": "moray.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/andrew-johnson-aa7aa431",
        "known_company": "AJ&Co Legal",
        "known_domain": "ajandco.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/travisschultz1",
        "known_company": "Travis Schultz & Partners",
        "known_domain": "schultzlaw.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/catherine-anne-walsh-5b635b35",
        "known_company": "Sydney Dental",
        "known_domain": "thedentist.net.au",
    },
    {
        "url": "https://au.linkedin.com/in/mark-nieh-7174958",
        "known_company": "Sydney CBD Dentistry",
        "known_domain": "sydneycbddentistry.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/fadi-shawy-8a44946a",
        "known_company": "Dental Practice",
        "known_domain": "",
    },
    {
        "url": "https://au.linkedin.com/in/peter-bakouris-0a8964113",
        "known_company": "Kalo Dental",
        "known_domain": "kalodental.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/grant-lawler-59271b192",
        "known_company": "Diverse Plumbing",
        "known_domain": "diverseplumbing.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/preetikennedy",
        "known_company": "Shopa Marketing",
        "known_domain": "shopamarketing.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/markkreuzer1",
        "known_company": "The Creative Works",
        "known_domain": "thecreativeworks.com.au",
    },
    {
        "url": "https://au.linkedin.com/in/stuart-edwards-3b334a42",
        "known_company": "Digital Movement",
        "known_domain": "digitalmovement.com.au",
    },
]

HEADERS = {
    "authorization": "basic",
    "token": CONTACTOUT_API_KEY,
}

PAYLOAD_INCLUDE = ["work_email", "personal_email", "phone"]


def select_best_email(work_emails, all_emails, company_domain):
    domain = (company_domain or "").lower().strip()
    if not domain:
        if work_emails:
            return work_emails[0], "no_company_domain"
        elif all_emails:
            return all_emails[0], "personal_only"
        return "", "none"
    for email in work_emails:
        if "@" in email and email.split("@")[1].lower() == domain:
            return email, "current_match"
    for email in all_emails:
        if "@" in email and email.split("@")[1].lower() == domain:
            return email, "current_match"
    if work_emails:
        return work_emails[0], "stale"
    if all_emails:
        return all_emails[0], "stale"
    return "", "none"


def select_best_phone(phones):
    for phone in phones:
        cleaned = phone.replace(" ", "").replace("-", "")
        if cleaned.startswith("+614") and len(cleaned) >= 12:
            return phone, True
        if cleaned.startswith("+61"):
            return phone, False
    if phones:
        return phones[0], False
    return "", False


results = []

print(f"\nRunning {len(PROFILES)} profiles...\n")

for i, prof in enumerate(PROFILES, 1):
    url = prof["url"]
    known_domain = prof["known_domain"]
    print(f"[{i:02d}/20] {url.split('/')[-1]}", end=" ... ", flush=True)

    try:
        resp = httpx.post(
            "https://api.contactout.com/v1/people/enrich",
            headers=HEADERS,
            json={"linkedin_url": url, "include": PAYLOAD_INCLUDE},
            timeout=30,
        )
        status_code = resp.status_code

        if status_code == 200:
            data = resp.json()
            profile = data.get("profile", {})
            full_name = profile.get("full_name", "")
            work_emails = profile.get("work_email", []) or []
            all_emails = profile.get("email", []) or []
            phones = profile.get("phone", []) or []
            company = profile.get("company", {}) or {}
            company_domain = company.get("domain", "") or company.get("email_domain", "") or ""

            best_email, confidence = select_best_email(
                work_emails, all_emails, known_domain or company_domain
            )
            best_phone, is_au_mobile = select_best_phone(phones)

            result = {
                "idx": i,
                "slug": url.split("/")[-1],
                "full_name": full_name,
                "found": True,
                "http_status": 200,
                "work_emails": work_emails,
                "all_emails": all_emails,
                "phones": phones,
                "company_name": company.get("name", ""),
                "company_domain": company_domain,
                "best_email": best_email,
                "confidence": confidence,
                "best_phone": best_phone,
                "is_au_mobile": is_au_mobile,
            }
            print(f"OK  name={full_name!r:30s} email={best_email or '—':40s} conf={confidence}")
        elif status_code == 404:
            result = {
                "idx": i,
                "slug": url.split("/")[-1],
                "found": False,
                "http_status": 404,
                "full_name": "",
                "work_emails": [],
                "all_emails": [],
                "phones": [],
                "company_name": "",
                "company_domain": "",
                "best_email": "",
                "confidence": "none",
                "best_phone": "",
                "is_au_mobile": False,
            }
            print("404 not found")
        else:
            result = {
                "idx": i,
                "slug": url.split("/")[-1],
                "found": False,
                "http_status": status_code,
                "full_name": "",
                "work_emails": [],
                "all_emails": [],
                "phones": [],
                "company_name": "",
                "company_domain": "",
                "best_email": "",
                "confidence": "error",
                "best_phone": "",
                "is_au_mobile": False,
                "error": resp.text[:200],
            }
            print(f"HTTP {status_code}: {resp.text[:100]}")

    except Exception as e:
        result = {
            "idx": i,
            "slug": url.split("/")[-1],
            "found": False,
            "http_status": 0,
            "full_name": "",
            "work_emails": [],
            "all_emails": [],
            "phones": [],
            "company_name": "",
            "company_domain": "",
            "best_email": "",
            "confidence": "error",
            "best_phone": "",
            "is_au_mobile": False,
            "error": str(e),
        }
        print(f"ERROR: {e}")

    results.append(result)

# Summary stats
found = [r for r in results if r["found"]]
with_email = [r for r in found if r["best_email"]]
current_match = [r for r in found if r["confidence"] == "current_match"]
stale = [r for r in found if r["confidence"] == "stale"]
no_domain = [r for r in found if r["confidence"] == "no_company_domain"]
personal_only = [r for r in found if r["confidence"] == "personal_only"]
no_email = [r for r in found if r["confidence"] == "none"]
with_phone = [r for r in found if r["best_phone"]]
au_mobile = [r for r in found if r["is_au_mobile"]]

print("\n" + "=" * 80)
print("RESULTS TABLE")
print("=" * 80)
print(f"{'#':>2}  {'Slug':<35} {'Name':<25} {'Email':<40} {'Conf':<20} {'Phone':<15} AU?")
print("-" * 80)
for r in results:
    found_str = r["full_name"][:24] if r["found"] else "(not found)"
    email_str = r["best_email"][:39] if r["best_email"] else "—"
    conf_str = r["confidence"][:19]
    phone_str = r["best_phone"][:14] if r["best_phone"] else "—"
    au_str = "Y" if r["is_au_mobile"] else ("n" if r["best_phone"] else "—")
    print(
        f"{r['idx']:>2}  {r['slug']:<35} {found_str:<25} {email_str:<40} {conf_str:<20} {phone_str:<15} {au_str}"
    )

print("=" * 80)
print(f"\nSUMMARY ({len(PROFILES)} profiles)")
print(f"  Profiles found:      {len(found)}/{len(PROFILES)}")
print(f"  With any email:      {len(with_email)}/{len(found)}")
print(f"    current_match:     {len(current_match)}")
print(f"    stale:             {len(stale)}")
print(f"    no_company_domain: {len(no_domain)}")
print(f"    personal_only:     {len(personal_only)}")
print(f"    none:              {len(no_email)}")
print(f"  With phone:          {len(with_phone)}/{len(found)}")
print(f"    AU mobile:         {len(au_mobile)}")

# Save output
out_path = "/home/elliotbot/clawd/Agency_OS/scripts/output/302_contactout_validation.json"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nFull results saved to: {out_path}")
