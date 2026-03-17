# SKILL_supabase_query.md
# Standard Supabase query patterns for Agency OS.
# Use exact patterns below. Never infer schema from names.
# Always paste verbatim results. Never summarise.

STEP 1: read ceo_memory (mandatory at session start)
  SELECT key, value, updated_at
  FROM ceo_memory
  ORDER BY updated_at DESC
  LIMIT 20;
  Read before any architectural decision.
  Contains directive counter, session state,
  all ratified decisions.

STEP 2: get current directive counter
  SELECT value FROM ceo_memory
  WHERE key = 'ceo:directives';
  Parse last= field for current directive number.
  Paste verbatim.

STEP 3: write directive completion to ceo_memory
  INSERT INTO ceo_memory (key, value, updated_at)
  VALUES (
    'ceo:directive_NNN_complete',
    jsonb_build_object(
      'status', 'complete',
      'pr', '#NNN',
      'branch', '[branch-name]',
      'notes', '[one line summary]'
    ),
    NOW()
  )
  ON CONFLICT (key) DO UPDATE
    SET value = EXCLUDED.value,
        updated_at = NOW();
  Replace NNN with actual directive number.
  Paste INSERT confirmation verbatim.

STEP 4: write to cis_directive_metrics
  INSERT INTO cis_directive_metrics
    (directive_number, status, pr_number, created_at)
  VALUES (NNN, 'complete', NNN, NOW());
  Replace NNN with actual values.
  Paste INSERT confirmation verbatim.

STEP 5: lead coverage by status
  SELECT
    status,
    COUNT(*) as total,
    COUNT(domain) as has_domain,
    COUNT(CASE WHEN enriched_at IS NOT NULL THEN 1 END)
      as enriched
  FROM leads
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY status
  ORDER BY total DESC;
  Paste verbatim.

STEP 6: compare enriched vs unenriched fields
  SELECT domain, company, propensity_score,
         als_score, status, enrichment_source
  FROM leads
  WHERE enriched_at IS NOT NULL
  ORDER BY created_at DESC LIMIT 20;

  SELECT domain, company, propensity_score,
         als_score, status, enrichment_source
  FROM leads
  WHERE enriched_at IS NULL
  ORDER BY created_at DESC LIMIT 20;

  Paste both verbatim. Compare field presence.

STEP 7: business_universe sample check
  SELECT abn, legal_name, trading_name,
         entity_type_code, state, status
  FROM business_universe
  LIMIT 5;
  Paste verbatim. Confirms table exists and has data.
