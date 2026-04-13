-- P1.6: Mark duplicate BDMs as not-current, keeping highest propensity per linkedin_url
BEGIN;

WITH ranked AS (
    SELECT bdm.id,
           ROW_NUMBER() OVER (
               PARTITION BY bdm.linkedin_url
               ORDER BY bu.propensity_score DESC NULLS LAST, bdm.created_at ASC
           ) AS rn
    FROM business_decision_makers bdm
    JOIN business_universe bu ON bu.id = bdm.business_universe_id
    WHERE bdm.is_current = TRUE
      AND bdm.linkedin_url IS NOT NULL
)
UPDATE business_decision_makers
SET is_current = FALSE, updated_at = NOW()
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

COMMIT;
