# DIRECTIVE #305 — Card Quality Fixes: Name, Location, Placeholder Filter

## Working directory
/home/elliotbot/clawd/Agency_OS

## Audit findings (already done — use these, do not re-audit)

### Current company_name source (free_enrichment.py ~line 433):
```python
company_name = (
    title.split("|")[0].split("-")[0].strip()[:60]
    or _d.split(".")[0].replace("-", " ").title()
)
```
This is `page_title_prefix` or `domain_stem`. ABN entity names are NOT included. GMB names are NOT included.

### Current location source (pipeline_orchestrator.py ~line 553):
```python
location=(enrichment.get("website_address") or {}).get("suburb", location),
```
Where `location` defaults to "Australia". Only `website_address.suburb` (from JSON-LD) is checked.

### ABN result dict (free_enrichment.py _abn_result_from_row ~line 304):
Returns: abn_matched, gst_registered, entity_type, registration_date, abn_confidence, _abn_strategy
DOES NOT INCLUDE: trading_name, legal_name, state, postcode.

### GMB data (paid_enrichment.py _stage_paid):
GMB result has gmb_rating, gmb_review_count, phone, address — but address is a raw string, not parsed suburb/state.

### Email waterfall:
No placeholder blocklist exists currently.

### ProspectCard fields currently:
- company_name: str
- location: str (single string, "Australia" in 54% of cases)
- dm_email: Optional[str]

## FILES IN SCOPE ONLY
- src/pipeline/free_enrichment.py
- src/pipeline/pipeline_orchestrator.py
- src/pipeline/email_waterfall.py
- tests/test_pipeline/test_free_enrichment.py (or create new test file)

DO NOT touch: intelligence.py, paid_enrichment.py, discovery.py, outreach stack.

---

## TASK B — Business name waterfall

### Step B1: Add entity names to ABN result dict in free_enrichment.py

In `_abn_result_from_row()` (~line 304), add these fields to the returned dict:
```python
"abn_trading_name": row.get("trading_name") or "",
"abn_legal_name": row.get("legal_name") or "",
```

Also add to the live API path (~line 845 in strategy4 block), where `best` is a dict with `business_name`:
```python
"abn_trading_name": best.get("business_name") or "",
"abn_legal_name": "",
```

### Step B2: Add resolve_business_name() to pipeline_orchestrator.py

Add this function near the top of the file (after imports, before class definitions):

```python
_ABN_ENTITY_SUFFIX_RE = re.compile(
    r"\b(pty\.?\s*ltd\.?|pty\.?\s*limited|limited|ltd\.?|inc\.?|llc|"
    r"proprietary|trustee\s+for|the\s+trustee|as\s+trustee)\b",
    re.IGNORECASE,
)
_DOMAIN_STEM_RE = re.compile(r"^[a-z0-9]+$", re.IGNORECASE)


def resolve_business_name(
    domain: str,
    enrichment: dict,
    gmb_data: dict | None = None,
) -> str:
    """
    Business name waterfall — returns the best available display name.

    Priority:
    1. ABN trading_name (if not just entity suffixes and not blank)
    2. GMB business name from gmb_data
    3. ABN legal_name (cleaned of entity suffixes)
    4. Page title prefix (enrichment["company_name"])
    5. Domain stem

    A name is rejected if it:
    - Is blank or whitespace
    - Is only entity suffixes ("Pty Ltd")
    - Is an ABN number (9+ digits)
    - Contains only the TLD ("com.au")
    """
    def _is_valid(name: str) -> bool:
        if not name or not name.strip():
            return False
        cleaned = _ABN_ENTITY_SUFFIX_RE.sub("", name).strip(" .,")
        if not cleaned:
            return False  # was only suffixes
        if re.fullmatch(r"\d{9,11}", name.replace(" ", "")):
            return False  # ABN number
        if cleaned.lower() in ("com", "com.au", "net.au", "org.au", "au"):
            return False
        return True

    candidates = [
        enrichment.get("abn_trading_name", ""),
        (gmb_data or {}).get("gmb_name", ""),
        enrichment.get("abn_legal_name", ""),
        enrichment.get("company_name", ""),  # title-derived
    ]

    for name in candidates:
        if name and _is_valid(name.strip()):
            # Clean entity suffixes from ABN names but keep the rest
            return name.strip()[:80]

    # Domain stem fallback
    stem = domain[4:] if domain.startswith("www.") else domain
    stem = stem.split(".")[0].replace("-", " ").replace("_", " ").title()
    return stem or domain
```

### Step B3: Use resolve_business_name() at BOTH card build points in pipeline_orchestrator.py

Find the two ProspectCard build blocks (~line 551 and ~line 866) where `company_name` is set:

**Block 1** (around line 533-553):
```python
company_name = (
    enrichment.get("company_name")
    or enrichment.get("abn_entity_name")
    or domain
)
```
Replace with:
```python
company_name = resolve_business_name(domain, enrichment, paid.get("gmb_data"))
```

**Block 2** (around line 773):
Same pattern — also replace with `resolve_business_name(domain, enrichment, paid.get("gmb_data") if isinstance(paid, dict) else None)`.

Also fix the company_name used for DM identification and GMB queries (lines ~442, ~503) — same substitution.

---

## TASK C — Location waterfall

### Step C1: Add location fields to ProspectCard dataclass

In the `ProspectCard` dataclass (pipeline_orchestrator.py ~line 69), add:
```python
# Location fields (Directive #305 — replaces single "location" string)
location_suburb: str = ""
location_state: str = ""
location_display: str = ""  # "Surry Hills, NSW" or "NSW" or "Australia"
```

Keep the existing `location: str` field for backwards compat — but set it to `location_display`.

### Step C2: Add resolve_location() to pipeline_orchestrator.py

Add this near resolve_business_name():

```python
_AU_STATE_ABBR_RE = re.compile(
    r"\b(NSW|VIC|QLD|WA|SA|TAS|ACT|NT)\b", re.IGNORECASE
)
_AU_POSTCODE_RE = re.compile(r"\b(\d{4})\b")

# Map state names to abbreviations
_STATE_NAME_TO_ABBR: dict[str, str] = {
    "new south wales": "NSW", "victoria": "VIC", "queensland": "QLD",
    "western australia": "WA", "south australia": "SA", "tasmania": "TAS",
    "australian capital territory": "ACT", "northern territory": "NT",
}


def resolve_location(
    domain: str,
    enrichment: dict,
    gmb_data: dict | None = None,
    default_location: str = "Australia",
) -> tuple[str, str, str]:
    """
    Location waterfall — returns (suburb, state, display_string).

    Priority:
    1. GMB address — parse suburb + state from "123 Main St, Surry Hills NSW 2010"
    2. website_address (JSON-LD) suburb + state
    3. ABN state (from entity_state field if available)
    4. State extracted from HTML (enrichment.get("state_hint"))
    5. default_location passed from discovery

    Returns:
        (suburb, state, display) e.g. ("Surry Hills", "NSW", "Surry Hills, NSW")
        or ("", "NSW", "NSW")
        or ("", "", "Australia")
    """
    suburb = ""
    state = ""

    # Priority 1: GMB address
    gmb_address = (gmb_data or {}).get("gmb_address") or (gmb_data or {}).get("address") or ""
    if gmb_address:
        # Parse "123 Main St, Surry Hills NSW 2010" or "Surry Hills, NSW"
        # Try to find state abbreviation
        state_match = _AU_STATE_ABBR_RE.search(gmb_address)
        if state_match:
            state = state_match.group(0).upper()
            # Suburb is usually the word(s) before the state abbreviation
            before_state = gmb_address[:state_match.start()].strip().rstrip(",").strip()
            # Take the last comma-separated segment as suburb candidate
            parts = [p.strip() for p in before_state.split(",") if p.strip()]
            if parts:
                suburb = parts[-1]

    # Priority 2: JSON-LD address from website
    if not suburb:
        wa = enrichment.get("website_address") or {}
        if isinstance(wa, dict):
            suburb = wa.get("suburb") or wa.get("addressLocality") or wa.get("city") or ""
            if not state:
                state = wa.get("state") or wa.get("addressRegion") or ""
                # Normalize state name to abbreviation
                if state and len(state) > 3:
                    state = _STATE_NAME_TO_ABBR.get(state.lower(), state)
            if not state:
                postcode = wa.get("postcode") or wa.get("postalCode") or ""
                state = _postcode_to_state(str(postcode)) if postcode else ""

    # Priority 3: ABN state
    if not state:
        abn_state = enrichment.get("abn_state") or ""
        if abn_state:
            state = _STATE_NAME_TO_ABBR.get(abn_state.lower(), abn_state)

    # Priority 4: State hint from enrichment
    if not state:
        state_hint = enrichment.get("state_hint") or enrichment.get("state") or ""
        if state_hint:
            state = _STATE_NAME_TO_ABBR.get(state_hint.lower(), state_hint).upper()[:3]
            if not _AU_STATE_ABBR_RE.match(state):
                state = ""  # not a recognised AU state

    # Build display string
    if suburb and state:
        display = f"{suburb}, {state}"
    elif suburb:
        display = suburb
    elif state:
        display = state
    else:
        display = default_location or "Australia"

    return suburb, state, display


def _postcode_to_state(postcode: str) -> str:
    """Map Australian postcode prefix to state abbreviation."""
    try:
        pc = int(postcode)
        if 1000 <= pc <= 2999:
            return "NSW"
        if 3000 <= pc <= 3999:
            return "VIC"
        if 4000 <= pc <= 4999:
            return "QLD"
        if 5000 <= pc <= 5999:
            return "SA"
        if 6000 <= pc <= 6999:
            return "WA"
        if 7000 <= pc <= 7999:
            return "TAS"
        if 800 <= pc <= 999:
            return "NT"
        if 200 <= pc <= 299:
            return "ACT"
    except (ValueError, TypeError):
        pass
    return ""
```

### Step C3: Use resolve_location() at card build points

At both ProspectCard build points, replace the location assignment with:
```python
loc_suburb, loc_state, loc_display = resolve_location(
    domain, enrichment, paid.get("gmb_data") if isinstance(paid, dict) else None
)
card = ProspectCard(
    ...
    location=loc_display,
    location_suburb=loc_suburb,
    location_state=loc_state,
    location_display=loc_display,
    ...
)
```

---

## TASK D — Placeholder filter in email_waterfall.py

### Step D1: Add blocklists near the top of email_waterfall.py (after imports)

```python
# ── Placeholder email/phone blocklists (Directive #305) ──────────────────────

PLACEHOLDER_EMAILS: frozenset[str] = frozenset({
    "example@mail.com",
    "you@mail.com",
    "email@example.com",
    "info@example.com",
    "your@email.com",
    "name@email.com",
    "test@test.com",
    "admin@example.com",
    "yourname@email.com",
    "user@example.com",
    "email@yourdomain.com",
    "you@yourdomain.com",
    "hello@example.com",
    "someone@example.com",
    "address@example.com",
    "noreply@example.com",
})

PLACEHOLDER_PHONES: frozenset[str] = frozenset({
    "+1234567891",
    "1234567890",
    "0000000000",
    "1111111111",
    "2222222222",
    "3333333333",
    "4444444444",
    "5555555555",
    "6666666666",
    "7777777777",
    "8888888888",
    "9999999999",
    "0412345678",
    "0400000000",
    "0412000000",
})

_PLACEHOLDER_EMAIL_PATTERN = re.compile(
    r"(example|yourname|placeholder|test|yourdomain|your-domain"
    r"|your_email|youremail|noreply|no-reply)",
    re.IGNORECASE,
)

_ALL_SAME_DIGIT_RE = re.compile(r"^(\d)\1{7,}$")  # 8+ same digits
_SEQUENTIAL_PHONE_RE = re.compile(r"^(0?1234567|01234567|12345678|23456789|34567890)[\d]*$")


def is_placeholder_email(email: str) -> bool:
    """Return True if email is a known placeholder or matches placeholder patterns."""
    if not email:
        return False
    email_lower = email.lower().strip()
    if email_lower in PLACEHOLDER_EMAILS:
        return True
    local = email_lower.split("@")[0] if "@" in email_lower else email_lower
    if _PLACEHOLDER_EMAIL_PATTERN.search(local):
        return True
    return False


def is_placeholder_phone(phone: str) -> bool:
    """Return True if phone is a known placeholder or sequential/all-same-digit."""
    if not phone:
        return False
    digits_only = re.sub(r"[^\d]", "", phone)
    if not digits_only:
        return False
    norm = re.sub(r"[\s\-\(\)\+]", "", phone)
    if norm in PLACEHOLDER_PHONES or digits_only in {p.lstrip("+") for p in PLACEHOLDER_PHONES}:
        return True
    if _ALL_SAME_DIGIT_RE.match(digits_only):
        return True
    if _SEQUENTIAL_PHONE_RE.match(digits_only):
        return True
    return False
```

### Step D2: Apply is_placeholder_email() in discover_email()

In the `discover_email()` function, after each layer returns a result, check before returning:

```python
if result and result.email:
    if is_placeholder_email(result.email):
        logger.debug("email_waterfall placeholder rejected: %s domain=%s", result.email, domain)
        result = None  # fall through to next layer
    else:
        return result
```

Do this for Layer 0 (contact_registry), Layer 1 (website), and the final result. Layers 2 (Leadmagic) and 3 (BD) are trusted sources — don't apply placeholder filter there.

### Step D3: Export is_placeholder_email and is_placeholder_phone

Make sure these are importable from email_waterfall (they're already module-level so they should be).

---

## TASK E — Tests

Create `tests/test_pipeline/test_card_quality.py`:

```python
"""
Tests for card quality fixes — Directive #305:
- Business name waterfall (resolve_business_name)
- Location waterfall (resolve_location)
- Placeholder filter (is_placeholder_email, is_placeholder_phone)
"""
```

Write these 10 tests:

1. **test_abn_trading_name_priority**: enrichment has `abn_trading_name="Dental1 Clinic Pty Ltd"` → `resolve_business_name()` returns "Dental1 Clinic Pty Ltd" (not the domain stem)

2. **test_pty_ltd_alone_falls_through**: enrichment has `abn_trading_name="Pty Ltd"`, gmb_data has `gmb_name="Bright Smile Dental"` → returns "Bright Smile Dental"

3. **test_gmb_address_suburb_state**: `gmb_data={"gmb_address": "42 Main St, Parramatta NSW 2150"}` → `resolve_location()` returns `("Parramatta", "NSW", "Parramatta, NSW")`

4. **test_abn_postcode_resolves_to_state**: enrichment has `website_address={"postcode": "2000"}` and no other location → `resolve_location()` returns `("", "NSW", "NSW")`

5. **test_australia_only_when_all_fail**: no enrichment, no gmb_data → `resolve_location()` returns `("", "", "Australia")`

6. **test_placeholder_email_exact_match**: `is_placeholder_email("example@mail.com")` → True

7. **test_placeholder_email_pattern**: `is_placeholder_email("yourname@company.com")` → True

8. **test_real_email_passes**: `is_placeholder_email("john.smith@dentist.com.au")` → False

9. **test_placeholder_phone_all_same_digit**: `is_placeholder_phone("0000000000")` → True; `is_placeholder_phone("0412345678")` → True

10. **test_real_phone_passes**: `is_placeholder_phone("0412 987 654")` → False; `is_placeholder_phone("+61 2 9123 4567")` → False

---

## TASK F — Run tests

```bash
cd /home/elliotbot/clawd/Agency_OS
python3 -m pytest tests/test_pipeline/test_card_quality.py -v 2>&1 | tail -20
python3 -m pytest tests/ -q --ignore=tests/test_email_verifier.py --ignore=tests/enrichment/test_email_verifier.py 2>&1 | tail -6
```

Baseline: >= 1302 passed, 0 failed.

---

## TASK G — PR

```bash
git checkout -b feat/305-card-quality
git add src/pipeline/free_enrichment.py src/pipeline/pipeline_orchestrator.py src/pipeline/email_waterfall.py tests/test_pipeline/test_card_quality.py
git commit -m "feat(pipeline): #305 — business name waterfall, location waterfall, placeholder filter"
git push origin feat/305-card-quality
gh pr create --title "feat(pipeline): #305 — card quality: name waterfall, location waterfall, placeholder filter" --body "Fixes three card quality bugs from integration test #300.\n\n**Bug 1:** Business name = domain stem. Added resolve_business_name() waterfall: ABN trading_name → GMB name → ABN legal_name → title prefix → domain stem.\n\n**Bug 2:** Location = Australia. Added resolve_location() waterfall: GMB address → JSON-LD suburb/state → ABN postcode → state hint. Adds location_suburb/state/display fields to ProspectCard.\n\n**Bug 3:** Placeholder emails leaking. Added is_placeholder_email() + is_placeholder_phone() with blocklist + pattern matching. Applied to Layers 0+1 in discover_email().\n\n10 new tests in tests/test_pipeline/test_card_quality.py." --base main
```

---

## REQUIRED OUTPUT (LAW XIV)

After PR created:
1. PR URL
2. `grep -n "PLACEHOLDER_EMAILS\|PLACEHOLDER_PHONES" src/pipeline/email_waterfall.py`
3. `grep -n "resolve_business_name\|resolve_location\|name_waterfall\|location_waterfall" src/pipeline/pipeline_orchestrator.py`
4. Before/after example card showing the three fixes
5. Full pytest output (last 6 lines)

## COMPLETION

When done, run:
openclaw system event --text "Done: #305 — card quality fixes: name waterfall, location waterfall, placeholder filter. PR open." --mode now
