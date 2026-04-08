# #300-FIX-6 — Stage 11 Card Quality + Draft Emails + BD Snapshot + Manual Update

## Context

Read these files first:
- /home/elliotbot/clawd/Agency_OS/scripts/integration_test_300k.py (Stage 11 script)
- /home/elliotbot/clawd/Agency_OS/src/pipeline/intelligence.py (refine_evidence — around lines 450-530)
- /home/elliotbot/clawd/memory/2026-04-01.md (session log with all directive details)

## Key facts from investigation:

**Current 300k_cards.json stats:**
- 248 OK cards, 243 have draft_email_subject, 243 have draft_email_body
- Business name = domain stem: 158/248 (64% still using domain stem!)
- Location = 'Australia' (generic): 135/248 (54% have no real location)

**Root causes:**
1. refine_evidence context does NOT include business_name, dm_name, dm_title, location — Haiku writes generic emails
2. lico description has names like 'FOCUS DENTAL GROUP | 6 followers' but _extract_biz_from_lico_desc returns ALL CAPS
3. HTML page title (in 300b_scrape.json 'title' field) is unused — rich source of real business names
4. lidm.get('location') has 'Sydney, New South Wales, Australia' — not being used properly
5. comp location_signals has ['Australia'] only mostly — not useful

---

## IMPLEMENT THESE FIXES

### FIX 1: Pass context into refine_evidence

**File: /home/elliotbot/clawd/Agency_OS/src/pipeline/intelligence.py**

In the `refine_evidence` function, the `context` dict is built before calling Haiku.
Add these fields to the context dict:
- "business_name": website_data.get("business_name", domain)
- "dm_name": website_data.get("dm_name", "")
- "dm_title": website_data.get("dm_title", "")
- "location": website_data.get("location", "")
- "category": website_data.get("category", "")

Also update the `_EVIDENCE_SYSTEM` prompt string. Find the line that defines the draft_email_body instruction (around line 450 where it says "draft_email_body":...) and update it to say:
"draft_email_body": "4-6 sentence email body. Address {dm_name} by first name. Reference the business name and location. Reference ONE specific signal. Match to the service. End with ONE question. Sign off with {{agency_name}}."

**File: /home/elliotbot/clawd/Agency_OS/scripts/integration_test_300k.py**

In `process_domain`, the `website_d` dict is built around line 230.
Add these additional keys to website_d before the refine_evidence call:
```python
"business_name": business_name,
"dm_name": dm.get("dm_name"),
"dm_title": dm.get("dm_title"),
"location": location,
"category": dm.get("category"),
```

---

### FIX 2: Business name — title-case ALL CAPS + use HTML title tag

**File: /home/elliotbot/clawd/Agency_OS/scripts/integration_test_300k.py**

1. Update `_extract_biz_from_lico_desc` to title-case ALL CAPS results:
```python
def _extract_biz_from_lico_desc(desc: str) -> str:
    """'FOCUS DENTAL GROUP | 6 followers' → 'Focus Dental Group'"""
    if desc and "|" in desc:
        name = desc.split("|")[0].strip()
        if name and name == name.upper() and len(name) > 2:
            name = name.title()
        return name
    return ""
```

2. Add a new helper `_extract_biz_from_title_tag` to parse HTML page titles:
```python
import re as _re
_TITLE_SEP_RE = _re.compile(r'\s*[|—–\-]\s*')
_TITLE_FILLER_RE = _re.compile(
    r'^(home|welcome|about|dentist|dental|clinic|medical|law|legal|accounting'
    r'|plumber|electrician|builder|#\d+|best|top|leading|professional)',
    _re.IGNORECASE
)

def _extract_biz_from_title_tag(title: str) -> str:
    """'#1 Dentist in Browns Plains - Dental Aspects' → 'Dental Aspects'"""
    if not title:
        return ""
    title = title.replace("&amp;", "&").replace("&#039;", "'")
    parts = [p.strip() for p in _TITLE_SEP_RE.split(title) if p.strip()]
    if not parts:
        return ""
    # Prefer last part if it looks like a brand (short, not filler)
    last = parts[-1]
    first = parts[0]
    if 1 <= len(last.split()) <= 5 and not _TITLE_FILLER_RE.match(last):
        return last[:60]
    if 1 <= len(first.split()) <= 5 and not _TITLE_FILLER_RE.match(first):
        return first[:60]
    return ""
```

3. In `build_domain_index`: load 300b_scrape.json and add 'scrape' to each domain's data dict.
   The scrape data is keyed by domain in a 'domains' list.

4. In `process_domain`: 
   - Add `scrape = data.get("scrape", {})`
   - Add `scrape_title_biz = _extract_biz_from_title_tag(scrape.get("title", ""))`
   - Update business_name priority chain: `lico_biz or dm_title_biz or lidm_biz or scrape_title_biz or domain_stem`

---

### FIX 3: Location — use lidm.location properly

**File: /home/elliotbot/clawd/Agency_OS/scripts/integration_test_300k.py**

1. Add helper to shorten verbose LinkedIn location strings:
```python
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
```

2. Add helper to extract suburb from HTML title tag:
```python
def _extract_location_from_title(title: str) -> str:
    """'#1 Dentist in Browns Plains & Regents Park' → 'Browns Plains'"""
    m = _AU_CITIES_RE.search(title or "")
    return m.group(0) if m else ""
```

3. In `process_domain`, update location resolution (replace current 4-line block):
```python
lidm_location = _shorten_location(lidm.get("location") or "")
lico_location = _extract_location_from_desc(lico.get("description", ""))
comp_comprehension = comp.get("comprehension") or {}
comp_location_sigs = comp_comprehension.get("location_signals") or []
comp_location = next(
    (s for s in comp_location_sigs if s and s.lower() != "australia"),
    ""
)
scrape_location = _extract_location_from_title(scrape.get("title", ""))
location = (lidm_location or lico_location or comp_location or scrape_location or "")[:50]
```

Note: `scrape` must be loaded first (from Fix 2). Also `comp` is already in `data` dict (it's loaded in build_domain_index as "comp"). Make sure `comp = data["comp"]` line is BEFORE the location resolution.

---

### FIX 4: Placeholder email filter — verify and add comment

**File: /home/elliotbot/clawd/Agency_OS/scripts/integration_test_300k.py**

Find `_PLACEHOLDER_RE`. The current patterns are correct — they catch template HTML placeholder emails only. 
DO NOT add info@, admin@, hello@, contact@ etc — those are real business emails.

Just add a comment above the regex:
```python
# Filters out HTML template placeholder emails only.
# DO NOT add real business emails like info@, admin@, contact@ — those are legitimate.
```

---

### FIX 5: Check BD snapshot sd_mnfd94hgsyllcqjlx

Run this Python script to check the snapshot status:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

import httpx
from src.integrations.brightdata_client import BRIGHTDATA_SCRAPER_KEY

r = httpx.get(
    "https://api.brightdata.com/datasets/v3/progress/sd_mnfd94hgsyllcqjlx",
    headers={"Authorization": f"Bearer {BRIGHTDATA_SCRAPER_KEY}"},
    timeout=10,
)
print("Status code:", r.status_code)
print("Response:", r.text[:1000])
```

Save as /tmp/check_bd.py and run with: `python3 /tmp/check_bd.py`

If status is "ready":
- Download profiles with the logic already in `check_bd_snapshot()` in the 300k script
- Merge into 300j_linkedin_dm.json (logic already implemented in 300k main())
- Report how many profiles were available

If status is NOT "ready" (still running, failed, etc.): just report the status and move on.

---

### FIX 6: Re-run Stage 11

After implementing all fixes, run Stage 11:

```bash
cd /home/elliotbot/clawd/Agency_OS
python3 scripts/integration_test_300k.py
```

If this takes >5 minutes OR if it needs the full 260 domains for a realistic test, that's fine — let it run.

Check the output stats. Verify:
- business_name = domain stem count should be MUCH lower (target <50%)
- location = 'Australia' count should be MUCH lower (target <30%)
- Draft emails should reference DM name and business name

---

### FIX 7: Commit

After successful rerun, commit all changes:
```
git add -A
git commit -m "fix(pipeline): #300-FIX-6 — card quality, draft emails, business name, location, BD snapshot"
git push
```

---

### FIX 8: Manual update for directives #295-#301

Read the drive-manual skill:
/home/elliotbot/clawd/skills/drive-manual/SKILL.md

Then update the Agency OS Manual for ALL directives since #294 (last documented).

What to document (from memory/2026-04-01.md):
- #300 Integration Test (11-stage pipeline, 730 domains, results)
- #300-FIX through #300-FIX-6 (the 14 issues, PR #264, schema split, email fixes, etc.)
- #301 SMTP Email Discovery (built email_verifier.py, Railway Reacher deployment, port 25 blocked)

Also check memory/2026-03-31.md, 2026-03-29.md, 2026-03-28.md for directives #295-#299 if they exist.

For each directive, update Section 12 (Directive Log) and any relevant architecture sections.

---

## CONSTRAINTS
- Test baseline: run `pytest /home/elliotbot/clawd/Agency_OS/tests/ -x -q --timeout=30 2>&1 | tail -5` first
- Don't break existing tests
- No new API keys needed
- python3 is the correct command (not python)
- Working dir: /home/elliotbot/clawd/Agency_OS

## COMPLETION
When done, run:
openclaw system event --text "Done: #300-FIX-6 complete — card quality fixes, Stage 11 rerun, Manual updated for directives since #278" --mode now
