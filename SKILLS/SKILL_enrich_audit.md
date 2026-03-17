# SKILL_enrich_audit.md
# Read-only. No code changes during this skill.
# Reference: ARCHITECTURE.md Sections 3-5, 8, 10

STEP 1: confirm location + read architecture header
  pwd
  head -10 ARCHITECTURE.md
  Paste both verbatim.

STEP 2: verify Clay fully removed from call chain
  grep -n "CLAY_MAX_PERCENTAGE\|clay_budget\|\
use_clay\|_enrich_tier2\|clay\.enrich" \
    src/engines/scout.py
  Paste verbatim. Expected: no output.
  Any hit = critical finding, report to CEO.

STEP 3: verify batch_size is 500
  grep -n "batch_size" src/engines/scout.py
  Paste verbatim. Expected value: 500.

STEP 4: verify all except blocks have logging
  grep -n "except" src/engines/scout.py
  For each except line found, paste that line plus
  the following 3 lines verbatim.
  Every except block must have a logger call.
  Silent except blocks are critical findings.

STEP 5: verify _has_company_data fallback intact
  grep -n "_has_company_data\|gmb_place_id" \
    src/engines/scout.py
  Paste verbatim. This fallback must exist.
  Reference: ARCHITECTURE.md Section 8.
  If missing: critical finding, report to CEO.

STEP 6: verify Leadmagic live, Hunter/Kaspr dead
  grep -n "leadmagic\|hunter\|kaspr" \
    src/integrations/siege_waterfall.py -i
  Paste verbatim.
  leadmagic: expected and correct.
  hunter or kaspr: critical finding, report to CEO.

STEP 7: verify T1 is Supabase JOIN not API call
  grep -n "business_universe\|abn_client\|ABN_LOOKUP" \
    src/engines/scout.py
  Paste verbatim.
  T1 must query business_universe table.
  It must NOT call abn_client API at runtime.

STEP 8: verify env vars present
  printenv | grep -i \
    "BRIGHT\|LEADMAGIC\|ABN\|DATAFORSEO\|ANTHROPIC"
  Paste key NAMES only — redact all values.
  Flag any missing key against ARCHITECTURE.md Section 9.

STEP 9: domain coverage query
  Follow SKILLS/SKILL_supabase_query.md Step 5.
  Paste verbatim.
  Calculate: enriched / total as percentage.
  Baseline: 3.7% (15/409 from v29). Target post-fix: 80%+

STEP 10: findings report
  Answer each with evidence from above steps:
  1. Is Clay fully removed from enrichment chain?
  2. Is batch_size 500?
  3. Does every except block log the exception?
  4. Is _has_company_data fallback intact?
  5. Is T1 a Supabase JOIN (not an API call)?
  6. Are all required env vars present?
  7. Current enrichment coverage percentage?
  8. Any other findings?
