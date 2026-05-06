"""src/pipeline/abn_match.py — shared ABN utilities for F2.2 discovery integrations.

Lightweight helpers used by AusTender, ASIC New Companies, and Seek connectors
to canonicalise ABNs, clean entity names, and validate ABN checksums BEFORE
writing to business_universe.

Existing ABN-match logic in src/pipeline/free_enrichment.py
(FreeEnrichmentService._abn_*) remains untouched — that module is tightly
coupled to the cohort_runner enrichment flow and out of F2.2 scope. This
module is for NEW connectors that need to validate + normalise an ABN
inline before INSERT.

Per LAW XII: F2.2 connectors (AusTender, ASIC, Seek) MUST go through these
helpers — direct ABN handling outside this module is forbidden.
"""

from __future__ import annotations

import re

# Public — F2.2 connectors import from here.
__all__ = [
    "canonicalize_abn",
    "is_valid_abn",
    "clean_entity_name",
    "ABN_CANONICAL_FORMAT",
]

# Canonical "XX XXX XXX XXX" — 11 digits in 2-3-3-3 grouping with single-space
# separators. ABR (Australian Business Register) presents ABNs in this shape;
# we normalise to it for consistent BU storage and dedup.
ABN_CANONICAL_FORMAT = "XX XXX XXX XXX"

# ABR's documented ABN checksum weights (algorithm published at
# https://abr.business.gov.au/Help/AbnFormat).
_ABN_CHECKSUM_WEIGHTS = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)

# Suffix/prefix patterns that ABR (and ASIC) attach to entity names. Stripped
# before similarity comparison to reduce false negatives ("ACME PTY LTD" vs
# "ACME" should match).
_RE_ENTITY_SUFFIXES = re.compile(
    r"\s+(PTY\s+LTD|PTY\.?\s+LIMITED|PROPRIETARY\s+LIMITED|PROPRIETARY\s+LTD|"
    r"LIMITED|LTD\.?|LLC|INC\.?|INCORPORATED|GMBH|TRUST|"
    r"PARTNERSHIP|PARTNERS|CO\.?|COMPANY)\b\.?$",
    re.IGNORECASE,
)

_RE_ENTITY_PREFIXES = re.compile(
    r"^(THE\s+TRUSTEE\s+FOR\s+|THE\s+TRUSTEE\s+OF\s+|TRUSTEE\s+FOR\s+|"
    r"AS\s+TRUSTEE\s+FOR\s+|ATF\s+|TRUSTEES?\s+OF\s+|"
    r"THE\s+(LATE\s+)?ESTATE\s+OF\s+|ESTATE\s+OF\s+|"
    r"THE\s+|MR\.?\s+|MRS\.?\s+|MS\.?\s+|MISS\s+|DR\.?\s+|PROF\.?\s+)",
    re.IGNORECASE,
)


def canonicalize_abn(raw: str | None) -> str | None:
    """Normalise an ABN to canonical "XX XXX XXX XXX" format.

    Strips all non-digit characters, validates length (11 digits) and
    ABN checksum per ABR spec. Returns None on any validation failure.

    Args:
        raw: ABN string in any format ("12345678901", "12 345 678 901",
             "12-345-678-901", " 12.345.678.901 " etc.).

    Returns:
        Canonical "XX XXX XXX XXX" string on valid input. None otherwise.

    Examples:
        >>> canonicalize_abn("51 824 753 556")
        '51 824 753 556'
        >>> canonicalize_abn("51824753556")
        '51 824 753 556'
        >>> canonicalize_abn("not-an-abn")  # missing digits
        >>> canonicalize_abn("12345678901")  # checksum fails
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) != 11:
        return None
    if not is_valid_abn(digits):
        return None
    # 2-3-3-3 grouping
    return f"{digits[0:2]} {digits[2:5]} {digits[5:8]} {digits[8:11]}"


def is_valid_abn(digits: str) -> bool:
    """Validate an 11-digit ABN against the ABR checksum algorithm.

    Per ABR: subtract 1 from the leading digit, multiply each of the 11
    digits by the documented weights, sum the products, and verify the
    sum modulo 89 is zero.

    Args:
        digits: 11-character digit-only string.

    Returns:
        True iff the ABN passes the ABR checksum.
    """
    if not digits or not digits.isdigit() or len(digits) != 11:
        return False
    int_digits = [int(d) for d in digits]
    int_digits[0] -= 1  # ABR-spec adjustment to leading digit
    weighted_sum = sum(d * w for d, w in zip(int_digits, _ABN_CHECKSUM_WEIGHTS, strict=True))
    return weighted_sum % 89 == 0


def clean_entity_name(name: str | None) -> str:
    """Strip ABR/ASIC entity suffixes and trustee prefixes for comparison.

    Used before fuzzy name-matching against ABR or BU `display_name` —
    "DENTISTS @ PYMBLE PTY LIMITED" and "DENTISTS @ PYMBLE" should match
    even though the legal-form suffix differs.

    Args:
        name: Raw entity name. None / empty returns "".

    Returns:
        Cleaned upper-cased name with surrounding whitespace stripped.

    Examples:
        >>> clean_entity_name("Dentists @ Pymble Pty Limited")
        'DENTISTS @ PYMBLE'
        >>> clean_entity_name("THE TRUSTEE FOR ACME TRUST")
        'ACME'
        >>> clean_entity_name("Acme Pty Ltd")
        'ACME'
        >>> clean_entity_name(None)
        ''
    """
    if not name:
        return ""
    s = str(name).strip().upper()
    # Strip prefixes first (greedy chain — "THE TRUSTEE FOR ..." may also
    # have a "THE" prefix it strips at the front).
    prev = None
    while prev != s:
        prev = s
        s = _RE_ENTITY_PREFIXES.sub("", s).strip()
    # Strip suffixes (also greedy — "X PTY LTD COMPANY" → "X").
    prev = None
    while prev != s:
        prev = s
        s = _RE_ENTITY_SUFFIXES.sub("", s).strip()
        # Strip the trailing trust-suffix that some entities carry as the
        # final word AFTER PTY LTD has been removed.
        s = re.sub(r"\s+TRUST$", "", s).strip()
    return s
