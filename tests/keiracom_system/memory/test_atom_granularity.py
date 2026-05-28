"""tests for keiracom_system.memory.atom_granularity — Wave 1 CUTOVER GATE 3g9t.

Coverage matrix (Aiden gate-validator discipline: >=4 negatives per rule):
- R1 size bounds      — 2 positive + 4 negative
- R2 single-concept   — 4 positive + 5 negative
- R3 source-pointer   — 3 positive + 4 negative
- R4 canonical fields — 2 positive + 3 negative
- escape valves       — 4 scenarios
- batch validator     — 2 scenarios
"""

from __future__ import annotations

import pytest

from src.keiracom_system.memory.atom_granularity import (
    GranularityRules,
    ValidationOutcome,
    validate_atom,
    validate_atoms,
)


def _atom(content: str, **extras):
    base = {"id": "atom-1", "content": content, "source_ref": "pr:1228"}
    base.update(extras)
    return base


# ============== R1 — size bounds ==============


def test_r1_atom_with_content_in_bounds_passes():
    out = validate_atom(_atom("X" * 200))
    assert out.ok
    assert out.violations == []


def test_r1_atom_at_exact_min_chars_passes():
    out = validate_atom(_atom("X" * 50))
    assert out.ok


def test_r1_min_violation_below_50_chars():
    out = validate_atom(_atom("short"))
    assert not out.ok
    assert any(v.rule_id == "R1.min" for v in out.violations)


def test_r1_max_violation_above_2000_chars():
    out = validate_atom(_atom("X" * 2001))
    assert not out.ok
    assert any(v.rule_id == "R1.max" for v in out.violations)


def test_r1_strips_whitespace_before_counting():
    # 50 X's surrounded by whitespace must pass; whitespace doesn't pad.
    out = validate_atom(_atom("   " + "X" * 50 + "   "))
    assert out.ok
    out_bad = validate_atom(_atom("   " + "X" * 10 + "   "))
    assert not out_bad.ok
    assert any(v.rule_id == "R1.min" for v in out_bad.violations)


def test_r1_custom_rules_can_relax_bounds():
    rules = GranularityRules(min_content_chars=10, max_content_chars=20)
    assert validate_atom(_atom("X" * 15), rules=rules).ok
    assert not validate_atom(_atom("X" * 25), rules=rules).ok


# ============== R2 — single-concept heuristics ==============


def test_r2_atom_with_three_short_sentences_passes():
    out = validate_atom(_atom("One sentence. Another sentence. A third short one for context."))
    assert out.ok


def test_r2_violation_too_many_sentences():
    content = ". ".join(f"Statement number {i} carries enough words to count" for i in range(6))
    out = validate_atom(_atom(content + "."))
    assert not out.ok
    assert any(v.rule_id == "R2.a" for v in out.violations)


def test_r2_violation_too_many_multi_concept_connectors():
    content = (
        "We migrated to Hindsight as the MAL engine in V1 architecture. "
        "Additionally, we adopted Weaviate. "
        "Furthermore, the Valkey cache went in for tool calls."
    )
    out = validate_atom(_atom(content))
    assert not out.ok
    assert any(v.rule_id == "R2.b" for v in out.violations)


def test_r2_single_connector_is_fine_transitional():
    content = (
        "We migrated to Hindsight as the MAL engine in V1 architecture. "
        "Additionally, the wrapper layer ships in PR #1134."
    )
    out = validate_atom(_atom(content))
    # One connector is transitional, not multi-concept.
    assert out.ok or not any(v.rule_id == "R2.b" for v in out.violations)


def test_r2_violation_too_many_h2_h3_headings():
    content = (
        "## Section A\n"
        "Body lines that bring this above the fifty char min comfortably indeed.\n"
        "## Section B\n"
        "More body content also helping the size minimum requirement here too.\n"
        "## Section C\n"
        "Final body content padding so the size rule is comfortably above min.\n"
        "## Section D\n"
        "And one more block of body content to keep this beyond the floor."
    )
    out = validate_atom(_atom(content))
    assert not out.ok
    assert any(v.rule_id == "R2.c" for v in out.violations)


def test_r2_collapses_repeated_punctuation_so_ellipsis_doesnt_inflate():
    # "..." was counted as multiple sentence terminators in a naive impl;
    # the validator must collapse repeated . to one terminator.
    content = "First thought... second... third... fourth fact lands here."
    out = validate_atom(_atom(content))
    # Should NOT trigger R2.a — collapsed sentence count is <=5.
    assert not any(v.rule_id == "R2.a" for v in out.violations)


def test_r2_skipped_when_single_concept_override_true():
    content = ". ".join(f"Statement number {i} carries enough words" for i in range(10)) + "."
    out = validate_atom(_atom(content, single_concept_override=True))
    # R2 entirely bypassed; R1 still applies but content is large enough to pass.
    assert out.exempt_reason == "single_concept_override"
    assert not any(v.rule_id.startswith("R2") for v in out.violations)


def test_r2_h2_headings_caps_at_3_default():
    content = (
        "## A\n"
        "Body content here that's at least fifty chars long for the size rule yes.\n"
        "## B\n"
        "More body content also above minimum required size for the size rule.\n"
        "## C\n"
        "Final body content keeping us above the minimum size requirement now ok."
    )
    out = validate_atom(_atom(content))
    # 3 headings is exactly the cap; should NOT fail R2.c.
    assert not any(v.rule_id == "R2.c" for v in out.violations)


# ============== R3 — source-pointer non-trivial ==============


def test_r3_pr_source_ref_passes():
    out = validate_atom(_atom("X" * 100, source_ref="pr:1228"))
    assert out.ok


def test_r3_commit_sha_source_ref_passes():
    out = validate_atom(_atom("X" * 100, source_ref="commit:5c8c54e3e"))
    assert out.ok


def test_r3_ceo_memory_key_source_ref_passes():
    out = validate_atom(_atom("X" * 100, source_ref="ceo:memory_abstraction_layer_v1"))
    assert out.ok


def test_r3_violation_source_ref_too_short():
    out = validate_atom(_atom("X" * 100, source_ref="pr:1"))
    assert not out.ok
    assert any(v.rule_id == "R3" for v in out.violations)


def test_r3_violation_source_ref_empty_string():
    atom = {"id": "a1", "content": "X" * 100, "source_ref": ""}
    out = validate_atom(atom)
    assert not out.ok
    # Empty string is treated as "field present but trivial" or "field absent"
    # depending on falsy check — both are violations.
    assert any(v.rule_id in {"R3", "R4"} for v in out.violations)


def test_r3_violation_source_ref_missing_entirely():
    atom = {"id": "a1", "content": "X" * 100}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R4" for v in out.violations)


def test_r3_provenance_source_nested_field_accepted():
    # Alias: nested provenance.source must be accepted too.
    atom = {
        "id": "a1",
        "content": "X" * 100,
        "provenance": {"source": "drive:1p9F:p3"},
    }
    out = validate_atom(atom)
    assert out.ok


# ============== R4 — canonical field names ==============


def test_r4_ad_hoc_field_name_origin_not_accepted():
    atom = {"id": "a1", "content": "X" * 100, "origin": "pr:1228"}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R4" for v in out.violations)


def test_r4_ad_hoc_field_name_from_not_accepted():
    atom = {"id": "a1", "content": "X" * 100, "from": "pr:1228"}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R4" for v in out.violations)


def test_r4_ad_hoc_field_name_cited_from_not_accepted():
    atom = {"id": "a1", "content": "X" * 100, "cited_from": "pr:1228"}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R4" for v in out.violations)


def test_r4_custom_rules_can_widen_accepted_keys():
    rules = GranularityRules(accepted_source_ref_keys=frozenset({"source_ref", "origin"}))
    atom = {"id": "a1", "content": "X" * 100, "origin": "pr:1228"}
    out = validate_atom(atom, rules=rules)
    assert out.ok


# ============== Escape valves ==============


def test_granularity_exempt_bypasses_all_rules():
    atom = {
        "id": "a1",
        "content": "x",  # would fail R1
        "origin": "weird",  # would fail R4
        "granularity_exempt": True,
    }
    out = validate_atom(atom)
    assert out.ok
    assert out.exempt_reason == "granularity_exempt"
    assert out.violations == []


def test_single_concept_override_does_NOT_bypass_r1():
    # R2 escape only — R1 and R3 still enforced.
    atom = {"id": "a1", "content": "tiny", "source_ref": "pr:1228", "single_concept_override": True}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R1.min" for v in out.violations)


def test_single_concept_override_does_NOT_bypass_r3():
    atom = {"id": "a1", "content": "X" * 100, "single_concept_override": True}
    out = validate_atom(atom)
    assert not out.ok
    assert any(v.rule_id == "R4" for v in out.violations)


def test_granularity_exempt_logged_at_warning_level(caplog):
    import logging

    atom = {"id": "audit-bypass", "content": "x", "granularity_exempt": True}
    with caplog.at_level(logging.WARNING):
        validate_atom(atom)
    assert any("granularity_exempt=true" in r.message for r in caplog.records)


# ============== Validator-level negatives ==============


def test_validate_atom_rejects_non_dict_input():
    with pytest.raises(ValueError, match="atom must be dict"):
        validate_atom("not a dict")  # type: ignore[arg-type]


def test_validate_atom_handles_missing_content():
    out = validate_atom({"id": "a1", "source_ref": "pr:1228"})
    assert not out.ok
    assert any(v.rule_id == "R0" for v in out.violations)


def test_validate_atom_returns_outcome_dataclass():
    out = validate_atom(_atom("X" * 100))
    assert isinstance(out, ValidationOutcome)
    assert out.schema_version == "1.0"


# ============== Batch validator ==============


def test_validate_atoms_processes_each_row():
    outs = validate_atoms(
        [
            _atom("X" * 100),
            _atom("short"),  # R1.min violation
            _atom("X" * 100, source_ref="pr:1"),  # R3 violation
        ]
    )
    assert len(outs) == 3
    assert outs[0].ok
    assert not outs[1].ok
    assert not outs[2].ok


def test_validate_atoms_rejects_non_list_input():
    with pytest.raises(ValueError, match="atoms must be list"):
        validate_atoms({"id": "a1"})  # type: ignore[arg-type]
