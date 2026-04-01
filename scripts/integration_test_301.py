"""
DIRECTIVE #301 — SMTP Email Discovery + Verification
Run on all 260 DMs from Stage 11 (300k_cards.json).
Zero cost. No external API.
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")

from src.enrichment.email_verifier import (
    generate_patterns,
    discover_email,
    verify_emails,
    SMTP_SEM,
)
from src.pipeline.email_waterfall import _parse_name

INPUT_CARDS = os.path.join(os.path.dirname(__file__), "output", "300k_cards.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "output", "301_email_discovery.json")

# Placeholder email patterns to skip
import re
_PLACEHOLDER_RE = re.compile(
    r"example@|test@|you@|your@|user@|mail@|email@|no-?reply@|noreply@"
    r"|example\.com|yourdomain|placeholder|samplesite",
    re.IGNORECASE,
)

async def main():
    print("=" * 60)
    print("DIRECTIVE #301 — SMTP Email Discovery + Verification")
    print("260 DMs: RCPT TO probing, 13 patterns, zero cost")
    print("=" * 60)

    cards_data = json.load(open(INPUT_CARDS))
    cards = [c for c in cards_data["cards"] if not c.get("_exception") and not c.get("_skipped")]
    print(f"Loaded {len(cards)} prospect cards")

    t0    = time.monotonic()
    done  = [0]
    total = len(cards)

    pattern_hits: dict[str, int] = {}  # track which patterns get verified

    async def process_card(c: dict) -> dict:
        domain   = c.get("domain", "")
        dm_name  = c.get("dm_name") or ""
        existing = c.get("dm_email")

        # Skip placeholder emails
        if existing and _PLACEHOLDER_RE.search(existing):
            existing = None

        # Parse name
        first, last = _parse_name(dm_name)

        # Clean domain
        d = domain[4:] if domain.startswith("www.") else domain

        # Run discovery
        smtp_result = await discover_email(first, last, d)

        # Track pattern hits
        for email in smtp_result.get("verified_emails", []):
            local = email.split("@")[0]
            # Identify which template this matches
            if first and last:
                f, l, fi, li = first, last, first[0] if first else "", last[0] if last else ""
                if local == f"{f}.{l}":    pattern_hits["first.last"] = pattern_hits.get("first.last", 0) + 1
                elif local == f"{fi}.{l}": pattern_hits["f.last"]      = pattern_hits.get("f.last", 0) + 1
                elif local == f:           pattern_hits["first"]        = pattern_hits.get("first", 0) + 1
                elif local == l:           pattern_hits["last"]         = pattern_hits.get("last", 0) + 1
                elif local == f"{f}{l}":   pattern_hits["firstlast"]    = pattern_hits.get("firstlast", 0) + 1
                elif local == f"{fi}{l}":  pattern_hits["flast"]        = pattern_hits.get("flast", 0) + 1
                else:                      pattern_hits["other"]        = pattern_hits.get("other", 0) + 1

        best_email = smtp_result["verified_emails"][0] if smtp_result.get("verified_emails") else None

        # Also verify existing email if not in probe results
        existing_verified = False
        if existing and not smtp_result.get("accept_all") and not smtp_result.get("error"):
            if existing in smtp_result.get("verified_emails", []):
                existing_verified = True

        done[0] += 1
        if done[0] % 25 == 0:
            elapsed = time.monotonic() - t0
            rate = done[0] / elapsed
            eta  = (total - done[0]) / rate if rate > 0 else 0
            print(f"  {done[0]}/{total} | {elapsed:.0f}s | ETA {eta:.0f}s", flush=True)

        return {
            "domain":              domain,
            "dm_name":             dm_name,
            "existing_email":      existing,
            "existing_verified":   existing_verified,
            "smtp_verified_email": best_email,
            "accept_all":          smtp_result.get("accept_all", False),
            "no_mx":               smtp_result.get("error") == "no_mx",
            "patterns_tested":     smtp_result.get("patterns_tested", 0),
            "all_verified":        smtp_result.get("verified_emails", []),
            "time_seconds":        smtp_result.get("time_seconds", 0),
            "error":               smtp_result.get("error"),
            "mx_host":             smtp_result.get("mx_host"),
        }

    tasks = [process_card(c) for c in cards]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.monotonic() - t0

    # Normalise
    clean = []
    errors = 0
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            clean.append({"domain": cards[i].get("domain"), "_exception": str(r)})
            errors += 1
        else:
            clean.append(r)

    ok = [r for r in clean if not r.get("_exception")]

    # Stats
    accept_all    = sum(1 for r in ok if r.get("accept_all"))
    no_mx         = sum(1 for r in ok if r.get("no_mx"))
    verified_dm   = sum(1 for r in ok if r.get("smtp_verified_email"))
    verified_exist = sum(1 for r in ok if r.get("existing_verified"))
    no_email      = sum(1 for r in ok if not r.get("smtp_verified_email") and not r.get("existing_verified"))
    sendable      = sum(1 for r in ok if r.get("smtp_verified_email") or r.get("existing_verified"))

    print()
    print("=" * 60)
    print("=== DIRECTIVE #301 REPORT ===")
    print()
    print(f"Domains tested:           {len(ok)}")
    print(f"Errors:                   {errors}")
    print(f"Accept-all domains:       {accept_all}  (can't verify — server accepts everything)")
    print(f"No MX record:             {no_mx}")
    print(f"Verified DM email found:  {verified_dm}")
    print(f"Existing email verified:  {verified_exist}")
    print(f"No valid email found:     {no_email}")
    print(f"Total sendable:           {sendable}")
    print()
    print("Per-pattern hit rate:")
    for pattern, count in sorted(pattern_hits.items(), key=lambda x: -x[1]):
        print(f"  {pattern}: {count}")
    print()
    print(f"Total time: {elapsed:.1f}s")
    print(f"Cost: $0.00")

    # 5 examples
    ex_found    = next((r for r in ok if r.get("smtp_verified_email")), None)
    ex_exist_v  = next((r for r in ok if r.get("existing_verified")), None)
    ex_accept   = next((r for r in ok if r.get("accept_all")), None)
    ex_no_mx    = next((r for r in ok if r.get("no_mx")), None)
    ex_none     = next((r for r in ok if not r.get("smtp_verified_email") and not r.get("existing_verified") and not r.get("accept_all") and not r.get("no_mx")), None)

    def show(label, r):
        if r is None:
            print(f"\n[{label}]: NOT FOUND"); return
        print(f"\n[{label}]")
        print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, indent=2))

    show("NEW EMAIL VERIFIED",        ex_found)
    show("EXISTING EMAIL VERIFIED",   ex_exist_v)
    show("ACCEPT-ALL DOMAIN",         ex_accept)
    show("NO MX RECORD",              ex_no_mx)
    show("NO EMAIL FOUND",            ex_none)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "directive": "301",
            "summary": {
                "total": len(clean), "ok": len(ok), "errors": errors,
                "accept_all": accept_all, "no_mx": no_mx,
                "verified_dm": verified_dm, "existing_verified": verified_exist,
                "no_email": no_email, "sendable": sendable,
                "pattern_hits": pattern_hits,
                "elapsed_seconds": round(elapsed, 1),
                "cost_usd": 0.0,
            },
            "results": clean,
        }, f, indent=2)
    print(f"\nSaved: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
