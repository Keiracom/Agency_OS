-- P1.7: Mark BDMs with NULL linkedin_url as not-current
-- These are non-actionable placeholder rows from Stage 5
BEGIN;

UPDATE business_decision_makers
SET is_current = FALSE, updated_at = NOW()
WHERE is_current = TRUE
  AND linkedin_url IS NULL;

-- Also mark BDMs for blocked domains as not-current
UPDATE business_decision_makers
SET is_current = FALSE, updated_at = NOW()
WHERE is_current = TRUE
  AND business_universe_id IN (
    SELECT id FROM business_universe
    WHERE domain IN (
      '1300smiles.com.au','bupadental.com.au','dentalcorp.com.au','dentalone.com.au',
      'marchorthodontics.com.au','maven.dental','mavendental.com.au','mcdental.com.au',
      'nationaldentalcare.com.au','nibdental.com.au','odontologie.com.au',
      'pacificsmiles.com.au','primarydental.com.au','rsdentalgroup.com.au',
      'smileclub.com.au','smilepath.com.au','smilesolutions.com.au','smileteam.com.au',
      'stjohnhealth.com.au','totalortho.com.au'
    )
  );

COMMIT;
