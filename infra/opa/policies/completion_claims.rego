# Governance Phase 1 Track A — A2 Gatekeeper completion-claim policy.
#
# Input contract (POST /v1/data/agency/completion_claims/allow):
#   {
#     "callsign":     "atlas",
#     "directive_id": "GOV-PHASE1-TRACK-A",
#     "claim_text":   "...what the agent says it accomplished...",
#     "evidence":     "$ pytest -q\n.....\nOK",
#     "target_files": ["src/foo.py", "tests/test_foo.py"],
#     "store_writes": [
#       { "directive_id": "GOV-PHASE1-TRACK-A", "store": "manual" },
#       ...
#     ],
#     "frozen_paths": ["docs/IMMUTABLE.md", "src/legacy/*"]
#   }
#
# Allow only when ALL gates pass:
#   G1  evidence contains a raw shell prompt ('$ ' prefix)
#   G2  store_writes covers the four required stores for this directive
#       (manual, ceo_memory, cis_directive_metrics, drive_mirror)
#   G3  target_files contains no path matched by frozen_paths

package agency.completion_claims

import future.keywords.if
import future.keywords.in
import future.keywords.every

default allow := false

# --- evidence guard -------------------------------------------------------

evidence_has_raw_output if {
    contains(input.evidence, "$ ")
}

# --- store-write guard ----------------------------------------------------

required_stores := {"manual", "ceo_memory", "cis_directive_metrics", "drive_mirror"}

# Set of stores actually written for this directive.
written_stores contains s if {
    some w in input.store_writes
    w.directive_id == input.directive_id
    s := w.store
}

store_writes_complete if {
    every s in required_stores {
        s in written_stores
    }
}

# --- frozen-paths guard ---------------------------------------------------

# A target file is blocked if it matches any frozen path / glob.
# Glob convention (matches OPA glob.match with default delimiters
# = ["/"]): exact paths match exactly; "src/legacy/**" matches
# everything under src/legacy/ recursively; "src/legacy/*" only
# matches direct children. Authors should write registry entries
# with the appropriate wildcard for the lock they want.
frozen_hits contains path if {
    some path in input.target_files
    some pattern in input.frozen_paths
    glob.match(pattern, [], path)
}

no_frozen_targets if {
    count(frozen_hits) == 0
}

# --- top-level decision ---------------------------------------------------

allow if {
    evidence_has_raw_output
    store_writes_complete
    no_frozen_targets
}

# Human-readable failure reasons — surfaced by the Python client when
# allow is false.
deny_reasons contains msg if {
    not evidence_has_raw_output
    msg := "evidence missing raw shell output (no '$ ' prefix detected)"
}

deny_reasons contains msg if {
    not store_writes_complete
    missing := required_stores - written_stores
    msg := sprintf("store writes incomplete for %v: missing %v", [input.directive_id, missing])
}

deny_reasons contains msg if {
    not no_frozen_targets
    msg := sprintf("target files include frozen paths: %v", [frozen_hits])
}
