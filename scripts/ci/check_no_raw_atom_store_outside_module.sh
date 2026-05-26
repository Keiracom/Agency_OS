#!/usr/bin/env bash
# Atomization pilot Week 1 guard — raw atom-store SQL forbidden outside the
# canonical module. All keiracom_atoms / keiracom_atom_supersession_edges /
# keiracom_atomizer_jobs access MUST go through AtomStore (tenant-prefix
# guard + DI for testability + frozen vocabulary checks).
#
# Mirrors:
#   - boundary-matrix-v1 guard (b) (PR #1169) — direct DB drivers outside MAL
#   - A7 CB-10 cache-discipline (PR #1173) — raw redis outside cache/
#
# Scope: src/keiracom_system/ ONLY. Legacy Agency_OS BDR surface (src/pipeline/
# etc.) does not touch keiracom_atoms — pattern would be 0 hits anyway.
#
# Exempt path: src/keiracom_system/atomization/ — the canonical module owner.
#
# Pattern: SQL keywords referencing the 3 atomization tables. Matches both
# direct .execute("INSERT INTO keiracom_atoms...") and similar SELECT/UPDATE/
# DELETE. The Python-source grep regex catches the verb + table-name pair on
# the same line (the common Python query string shape).

set -euo pipefail

SCOPE="src/keiracom_system"

if [ ! -d "$SCOPE" ]; then
  echo "OK (atom-store-discipline): $SCOPE not present — guard inactive."
  exit 0
fi

# Capture SQL verb + atomization table name in the same line. Tolerates leading
# quotes and indentation. Both keiracom_atoms (base) and the _supersession_edges
# + _atomizer_jobs suffixes are caught — they're all part of the atom-store API.
PATTERN='(INSERT[[:space:]]+INTO[[:space:]]+keiracom_atom|UPDATE[[:space:]]+keiracom_atom|DELETE[[:space:]]+FROM[[:space:]]+keiracom_atom|FROM[[:space:]]+keiracom_atom)'

raw=$(grep -rnE --include='*.py' "$PATTERN" "$SCOPE" 2>/dev/null || true)

# Exempt the atomization module itself.
hits=$(printf '%s\n' "$raw" \
  | grep -v -E '^src/keiracom_system/atomization/' \
  | grep -v -E '^[[:space:]]*$' || true)

if [ -n "$hits" ]; then
  echo "FAIL (atom-store-discipline): raw SQL against atomization tables found"
  echo "outside src/keiracom_system/atomization/. All atom-store access MUST go"
  echo "through AtomStore — the tenant-prefix guard + frozen vocabulary checks"
  echo "depend on the module boundary. Route the call through AtomStore."
  echo ""
  echo "See docs/architecture/design/atomization_pilot_schema_lock_proposal.md §6."
  echo ""
  echo "Offending lines:"
  echo "$hits"
  exit 1
fi

echo "OK (atom-store-discipline): no raw atom-store SQL outside atomization module."
exit 0
