"""tests/pipeline/test_abn_match.py — unit tests for the F2.2 shared ABN helpers.

Covers canonicalize_abn (digit normalisation + checksum), is_valid_abn
(ABR checksum algorithm), and clean_entity_name (suffix/prefix stripping
for fuzzy comparison).

All tests are pure-function — no DB, no network. Fast CI.
"""

from __future__ import annotations

import pytest

from src.pipeline.abn_match import (
    ABN_CANONICAL_FORMAT,
    canonicalize_abn,
    clean_entity_name,
    is_valid_abn,
)

# A real ABN that passes the ABR checksum (Telstra, public record).
_VALID_ABN_DIGITS = "33051775556"
_VALID_ABN_CANONICAL = "33 051 775 556"


# ── canonicalize_abn ──────────────────────────────────────────────────────────


def test_canonicalize_abn_passthrough_canonical():
    assert canonicalize_abn(_VALID_ABN_CANONICAL) == _VALID_ABN_CANONICAL


def test_canonicalize_abn_strips_separators():
    assert canonicalize_abn("33-051-775-556") == _VALID_ABN_CANONICAL
    assert canonicalize_abn("33.051.775.556") == _VALID_ABN_CANONICAL
    assert canonicalize_abn("  33051775556  ") == _VALID_ABN_CANONICAL


def test_canonicalize_abn_no_separators():
    assert canonicalize_abn(_VALID_ABN_DIGITS) == _VALID_ABN_CANONICAL


def test_canonicalize_abn_none_or_empty():
    assert canonicalize_abn(None) is None
    assert canonicalize_abn("") is None
    assert canonicalize_abn("   ") is None


def test_canonicalize_abn_wrong_length():
    assert canonicalize_abn("123") is None
    assert canonicalize_abn("123456789012") is None  # 12 digits


def test_canonicalize_abn_non_digit_after_strip():
    """Non-digit chars are stripped first; if remainder is wrong length OR
    fails checksum, result is None either way."""
    assert canonicalize_abn("not-an-abn-here") is None
    # "ABN12345678901" → strip → "12345678901" (11 digits) → fails ABR checksum → None
    assert canonicalize_abn("ABN12345678901") is None


def test_canonicalize_abn_invalid_checksum():
    """11 digits but failing the ABR checksum."""
    # Trivial wrong: all zeros
    assert canonicalize_abn("00000000000") is None
    # Off-by-one of valid (last digit changed)
    bad = _VALID_ABN_DIGITS[:-1] + "0"
    if bad != _VALID_ABN_DIGITS:
        assert canonicalize_abn(bad) is None


def test_canonicalize_abn_canonical_format_constant():
    """Sanity: the documented format constant matches the regex shape we produce."""
    result = canonicalize_abn(_VALID_ABN_DIGITS)
    assert result is not None
    assert len(result) == len(ABN_CANONICAL_FORMAT)
    assert result.count(" ") == ABN_CANONICAL_FORMAT.count(" ")


# ── is_valid_abn ──────────────────────────────────────────────────────────────


def test_is_valid_abn_passes_real_abn():
    assert is_valid_abn(_VALID_ABN_DIGITS) is True


def test_is_valid_abn_rejects_zero_padding():
    assert is_valid_abn("00000000000") is False


def test_is_valid_abn_rejects_short():
    assert is_valid_abn("123") is False


def test_is_valid_abn_rejects_non_digit():
    assert is_valid_abn("abc12345678") is False
    assert is_valid_abn("12 345 678 901") is False  # spaces not allowed in raw digits


def test_is_valid_abn_empty_or_none():
    assert is_valid_abn("") is False
    # type: ignore[arg-type] — testing the None guard
    assert is_valid_abn(None) is False  # type: ignore[arg-type]


# ── clean_entity_name ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Acme Pty Ltd", "ACME"),
        ("Acme PTY. LIMITED", "ACME"),
        ("Acme Proprietary Limited", "ACME"),
        ("Acme Limited", "ACME"),
        ("Acme Ltd", "ACME"),
        ("ACME LLC", "ACME"),
        ("ACME, Inc.", "ACME,"),  # comma stays — not part of suffix pattern
        ("Acme Incorporated", "ACME"),
        ("Acme Co.", "ACME"),
        ("Acme Company", "ACME"),
    ],
)
def test_clean_entity_name_strips_suffixes(raw: str, expected: str):
    assert clean_entity_name(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("THE TRUSTEE FOR ACME TRUST", "ACME"),
        ("THE TRUSTEE OF ACME TRUST", "ACME"),
        ("AS TRUSTEE FOR ACME TRUST", "ACME"),
        ("ATF ACME TRUST", "ACME"),
        ("THE Acme", "ACME"),
        ("Mr Smith", "SMITH"),
        ("Dr. Pymble Dental Pty Ltd", "PYMBLE DENTAL"),
        ("ESTATE OF JOHN SMITH", "JOHN SMITH"),
    ],
)
def test_clean_entity_name_strips_prefixes(raw: str, expected: str):
    assert clean_entity_name(raw) == expected


def test_clean_entity_name_combined_prefix_and_suffix():
    """Strip both prefix and suffix in one call."""
    assert clean_entity_name("THE TRUSTEE FOR PYMBLE DENTAL PTY LTD") == "PYMBLE DENTAL"


def test_clean_entity_name_none_or_empty():
    assert clean_entity_name(None) == ""
    assert clean_entity_name("") == ""
    assert clean_entity_name("   ") == ""


def test_clean_entity_name_no_changes():
    """A plain entity name with no recognised prefix/suffix is returned upper-cased."""
    assert clean_entity_name("Pymble Dental") == "PYMBLE DENTAL"
    assert clean_entity_name("acme") == "ACME"


def test_clean_entity_name_handles_repeated_application():
    """Repeated application is idempotent."""
    once = clean_entity_name("Acme Pty Ltd")
    twice = clean_entity_name(once)
    assert once == twice
