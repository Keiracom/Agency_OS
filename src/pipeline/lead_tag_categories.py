"""
FILE: src/pipeline/lead_tag_categories.py
PURPOSE: Single source of truth for lead_tags stage and category enumerations.
         Shared between tag_handler and any future query/reporting code.
"""

STAGE_CHOICES = [
    "stage1_discovery",
    "stage2_abn",
    "stage3_comprehension",
    "stage4_affordability",
    "stage5_scoring",
    "stage6_seo",
    "stage7_contact",
    "stage8_email",
    "stage9_social",
    "stage10_dm",
    "stage11_card",
    "manual",  # Dave catching it outside the pipeline
]

REASON_CATEGORIES = [
    "enterprise",
    "chain",
    "franchise",
    "wrong_industry",
    "sole_trader",
    "government",
    "not_au_based",
    "duplicate",
    "bad_data",
    "not_a_business",
    "already_customer",
    "not_reachable",
    "other",
]


def is_valid_stage(s: str) -> bool:
    """Return True if s is a recognised pipeline stage."""
    return s in STAGE_CHOICES


def is_valid_category(c: str) -> bool:
    """Return True if c is a recognised reason category."""
    return c in REASON_CATEGORIES
