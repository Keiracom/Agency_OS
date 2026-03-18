"""
Contract: src/services/icp_filter_service.py
Purpose: ICP (Ideal Customer Profile) filtering for Agency OS
Layer: 3 - services
Imports: None (standalone)
Consumers: lead_pool_service, waterfall_verification_worker, pool_population_flow

FILE: src/services/icp_filter_service.py
PURPOSE: Strict ICP filtering for Australian marketing/digital agencies
PHASE: Directive #044 (ICP Filter Critical Fix), updated Directive #046
TASK: ICP-001
DEPENDENCIES: None
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - No non-ICP leads enter pipeline

CEO DIRECTIVE #044: Non-ICP leads are a critical defect.
CEO DIRECTIVE #046: Added underscore-format industry values, normalized matching,
  fixed blacklist to only check category fields (not company name).
Agency OS targets Australian marketing/digital agencies EXCLUSIVELY.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# ============================================
# ICP WHITELIST — Agency Categories
# ============================================

ICP_CATEGORY_WHITELIST = {
    # Core agency types
    "marketing agency",
    "digital marketing agency",
    "advertising agency",
    "seo agency",
    "social media agency",
    "creative agency",
    "media agency",
    "pr agency",
    "public relations agency",
    "web design agency",
    "branding agency",
    "content agency",
    "content marketing agency",
    "performance marketing agency",
    "growth agency",
    "digital agency",
    "full service agency",
    "integrated agency",
    "communications agency",
    "brand agency",
    "media buying agency",
    "ppc agency",
    "sem agency",
    "email marketing agency",
    "inbound marketing agency",
    "marketing consultancy",
    "digital consultancy",
    "advertising services",
    "marketing services",
}

# Industry strings that indicate agency (from LinkedIn/enrichment data)
# Includes both space-separated and underscore-separated formats (Directive #046)
ICP_INDUSTRY_WHITELIST = {
    # Space-separated formats (LinkedIn standard)
    "marketing and advertising",
    "marketing & advertising",
    "advertising services",
    "marketing services",
    "digital media",
    "online media",
    "internet",  # Often used for digital agencies
    "public relations and communications",
    "public relations",
    "media production",
    # Underscore-separated formats (Directive #046 fix)
    "digital_marketing",
    "marketing_and_advertising",
    "advertising_and_marketing",
    "seo",
    "social_media",
    "public_relations",
    "web_design",
    "creative_services",
    "media",
    "branding",
}


# ============================================
# HARD EXCLUDE LIST — Never ICP
# ============================================

ICP_CATEGORY_BLACKLIST = {
    # Trades
    "trades",
    "plumbing",
    "plumber",
    "construction",
    "electrical",
    "electrician",
    "carpentry",
    "carpenter",
    "roofing",
    "roofer",
    "landscaping",
    "landscaper",
    "cleaning",
    "cleaner",
    "hvac",
    "air conditioning",
    "pest control",
    "locksmith",
    "fencing",
    "concreting",
    "tiling",
    "painting",
    "glazing",
    "flooring",
    "demolition",
    "excavation",
    "scaffolding",
    "crane",
    "rigging",
    "welding",
    "fabrication",
    "steel",
    "steelwork",
    "structural",
    "fitout",
    "fitouts",
    # Hospitality
    "hospitality",
    "restaurant",
    "cafe",
    "bar",
    "pub",
    "hotel",
    "motel",
    "catering",
    "food service",
    "food & beverage",
    # Retail
    "retail",
    "shop",
    "store",
    "supermarket",
    "convenience",
    # Medical
    "medical",
    "dental",
    "dentist",
    "doctor",
    "clinic",
    "hospital",
    "pharmacy",
    "physiotherapy",
    "chiropractic",
    "optometry",
    "pathology",
    "radiology",
    "aged care",
    "healthcare",
    "health care",
    # Professional services (non-agency)
    "legal",
    "lawyer",
    "solicitor",
    "accounting",
    "accountant",
    "bookkeeping",
    "financial planning",
    "real estate",
    "property",
    "insurance",
    # Other
    "automotive",
    "mechanic",
    "smash repair",
    "furniture",
    "manufacturing",
    "mining",
    "agriculture",
    "farming",
    "transport",
    "logistics",
    "trucking",
    "staffing",
    "recruiting",
    "recruitment",
    "labour hire",
    "labor hire",
    "workforce",
}

# Industry strings that are never ICP (from LinkedIn/enrichment data)
ICP_INDUSTRY_BLACKLIST = {
    "construction",
    "staffing & recruiting",
    "staffing and recruiting",
    "automotive",
    "furniture",
    "hospitals and health care",
    "medical practice",
    "legal services",
    "accounting",
    "real estate",
    "retail",
    "hospitality",
    "food & beverages",
    "food and beverages",
    "transportation",
    "manufacturing",
    "mining & metals",
    "agriculture",
    "wholesale",
    "consumer goods",
    "facilities services",
    "mechanical or industrial engineering",
    "civil engineering",
    "building materials",
}


# ============================================
# ICP FILTER SERVICE
# ============================================


class ICPFilterService:
    """
    Service for filtering leads against Agency OS ICP criteria.

    Agency OS targets Australian marketing/digital agencies EXCLUSIVELY.
    This service provides:
    - Layer 1: GMB Category Whitelist check
    - Layer 2: Hard Exclude List check
    - Layer 3: Industry validation for ALS gating
    """

    @staticmethod
    def normalize_text(text: str | None) -> str:
        """Normalize text for matching."""
        if not text:
            return ""
        return text.lower().strip()

    @staticmethod
    def normalize_for_industry_match(text: str | None) -> str:
        """
        Normalize text for industry matching (Directive #046).

        Converts both underscore and space formats to underscore format
        so 'digital_marketing' matches 'digital marketing' and vice versa.
        """
        if not text:
            return ""
        # Lowercase, strip, replace spaces with underscores
        normalized = text.lower().strip().replace(" ", "_").replace("&", "and")
        return normalized

    @classmethod
    def check_category_whitelist(
        cls,
        categories: list[str] | None,
        gmb_category: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Layer 1: Check if ANY category matches ICP whitelist.

        Args:
            categories: List of GMB all_categories or similar
            gmb_category: Primary GMB category

        Returns:
            Tuple of (passes_whitelist, matched_category)
        """
        all_cats = []

        if gmb_category:
            all_cats.append(cls.normalize_text(gmb_category))

        if categories:
            all_cats.extend([cls.normalize_text(c) for c in categories])

        for cat in all_cats:
            for whitelist_term in ICP_CATEGORY_WHITELIST:
                if whitelist_term in cat:
                    return True, cat

        return False, None

    @classmethod
    def check_category_blacklist(
        cls,
        categories: list[str] | None,
        gmb_category: str | None = None,
        company_name: str | None = None,  # Kept for signature compat, NOT used (Directive #046)
    ) -> tuple[bool, str | None]:
        """
        Layer 2: Check if ANY category matches HARD EXCLUDE list.

        DIRECTIVE #046 FIX: Only checks GMB category and all_categories fields.
        Company name is NOT checked — "Property Marketing Agency" is valid ICP
        because the GMB category will be marketing agency, not real estate.

        Args:
            categories: List of GMB all_categories or similar
            gmb_category: Primary GMB category
            company_name: IGNORED (kept for signature compatibility)

        Returns:
            Tuple of (is_blacklisted, matched_term)
        """
        all_text = []

        if gmb_category:
            all_text.append(cls.normalize_text(gmb_category))

        if categories:
            all_text.extend([cls.normalize_text(c) for c in categories])

        # NOTE: company_name deliberately NOT included (Directive #046)
        # Property Marketing Agency should pass — their GMB category is "marketing agency"

        if not all_text:
            # No categories to check = not blacklisted
            return False, None

        combined = " ".join(all_text)

        for blacklist_term in ICP_CATEGORY_BLACKLIST:
            # Use word boundary matching to avoid false positives
            pattern = r"\b" + re.escape(blacklist_term) + r"\b"
            if re.search(pattern, combined):
                return True, blacklist_term

        return False, None

    @classmethod
    def check_industry_whitelist(
        cls,
        industry: str | None,
        sub_industry: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if industry matches ICP whitelist.

        Uses dual normalization (Directive #046):
        - Standard lowercase/strip for exact matches
        - Underscore normalization for format-agnostic matching

        Args:
            industry: Industry field from enrichment data
            sub_industry: Sub-industry if available

        Returns:
            Tuple of (passes_whitelist, matched_industry)
        """
        industries = []

        if industry:
            industries.append(cls.normalize_text(industry))
        if sub_industry:
            industries.append(cls.normalize_text(sub_industry))

        # Build normalized whitelist for underscore matching
        normalized_whitelist = {cls.normalize_for_industry_match(t) for t in ICP_INDUSTRY_WHITELIST}

        for ind in industries:
            # Direct match against whitelist
            if ind in ICP_INDUSTRY_WHITELIST:
                return True, ind

            # Normalized match (underscore format) — Directive #046
            normalized_ind = cls.normalize_for_industry_match(ind)
            if normalized_ind in normalized_whitelist:
                return True, ind

            # Partial match for flexibility
            for whitelist_term in ICP_INDUSTRY_WHITELIST:
                if whitelist_term in ind or ind in whitelist_term:
                    return True, ind
                # Also check normalized partial match
                norm_term = cls.normalize_for_industry_match(whitelist_term)
                if norm_term in normalized_ind or normalized_ind in norm_term:
                    return True, ind

        return False, None

    @classmethod
    def check_industry_blacklist(
        cls,
        industry: str | None,
        sub_industry: str | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if industry is on HARD EXCLUDE list.

        Args:
            industry: Industry field from enrichment data
            sub_industry: Sub-industry if available

        Returns:
            Tuple of (is_blacklisted, matched_industry)
        """
        industries = []

        if industry:
            industries.append(cls.normalize_text(industry))
        if sub_industry:
            industries.append(cls.normalize_text(sub_industry))

        for ind in industries:
            if ind in ICP_INDUSTRY_BLACKLIST:
                return True, ind

        return False, None

    @classmethod
    def is_icp_qualified(
        cls,
        lead_data: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        """
        Full ICP qualification check.

        Applies all three layers:
        - Layer 1: GMB Category Whitelist
        - Layer 2: Hard Exclude List
        - Layer 3: Industry validation

        Args:
            lead_data: Lead data dict with company_industry, categories, etc.

        Returns:
            Tuple of (is_qualified, details_dict)
        """
        details = {
            "qualified": False,
            "reason": None,
            "layer_failed": None,
            "matched_term": None,
        }

        # Extract fields
        company_name = lead_data.get("company_name")
        industry = lead_data.get("company_industry")
        sub_industry = lead_data.get("company_sub_industry")

        # GMB categories from enrichment_data or direct field
        enrichment = lead_data.get("enrichment_data") or {}
        if isinstance(enrichment, str):
            import json

            try:
                enrichment = json.loads(enrichment)
            except Exception:
                enrichment = {}

        categories = (
            lead_data.get("categories")
            or lead_data.get("all_categories")
            or enrichment.get("gmb_categories")
            or enrichment.get("categories")
            or []
        )
        gmb_category = lead_data.get("gmb_category") or enrichment.get("gmb_category")

        # ========== Layer 2: Hard Exclude (check first) ==========
        # If blacklisted, reject immediately
        is_blacklisted, blacklist_term = cls.check_category_blacklist(
            categories, gmb_category, company_name
        )
        if is_blacklisted:
            details["reason"] = f"Blacklisted category/name: {blacklist_term}"
            details["layer_failed"] = "layer_2_category_blacklist"
            details["matched_term"] = blacklist_term
            logger.info(f"ICP REJECT (Layer 2): {company_name} — {blacklist_term}")
            return False, details

        is_industry_blacklisted, blacklist_industry = cls.check_industry_blacklist(
            industry, sub_industry
        )
        if is_industry_blacklisted:
            details["reason"] = f"Blacklisted industry: {blacklist_industry}"
            details["layer_failed"] = "layer_2_industry_blacklist"
            details["matched_term"] = blacklist_industry
            logger.info(f"ICP REJECT (Layer 2): {company_name} — industry: {blacklist_industry}")
            return False, details

        # ========== Layer 1: Category Whitelist ==========
        passes_cat_whitelist, matched_cat = cls.check_category_whitelist(categories, gmb_category)
        if passes_cat_whitelist:
            details["qualified"] = True
            details["reason"] = f"Matched category: {matched_cat}"
            details["matched_term"] = matched_cat
            logger.info(f"ICP PASS (Layer 1): {company_name} — {matched_cat}")
            return True, details

        # ========== Layer 3: Industry Whitelist ==========
        passes_ind_whitelist, matched_ind = cls.check_industry_whitelist(industry, sub_industry)
        if passes_ind_whitelist:
            details["qualified"] = True
            details["reason"] = f"Matched industry: {matched_ind}"
            details["matched_term"] = matched_ind
            logger.info(f"ICP PASS (Layer 3): {company_name} — industry: {matched_ind}")
            return True, details

        # ========== No match ==========
        details["reason"] = "No ICP match found"
        details["layer_failed"] = "no_whitelist_match"
        logger.info(f"ICP REJECT (no match): {company_name} — industry: {industry}")
        return False, details

    @classmethod
    def calculate_industry_als_penalty(
        cls,
        lead_data: dict[str, Any],
    ) -> int:
        """
        Layer 3: Calculate ALS penalty for non-agency industries.

        Returns penalty to subtract from ALS score.
        Non-agency industry should result in ALS < 50.

        Args:
            lead_data: Lead data dict

        Returns:
            Penalty points (0 = no penalty, 50+ = effectively disqualified)
        """
        industry = lead_data.get("company_industry")

        # Blacklisted industry = max penalty
        is_blacklisted, _ = cls.check_industry_blacklist(industry)
        if is_blacklisted:
            return 60  # Ensures ALS < 50 even with perfect other scores

        # Whitelisted industry = no penalty
        passes_whitelist, _ = cls.check_industry_whitelist(industry)
        if passes_whitelist:
            return 0

        # Unknown industry = moderate penalty
        return 30


# Singleton instance
_icp_filter_service = ICPFilterService()


def get_icp_filter_service() -> ICPFilterService:
    """Get the ICP filter service instance."""
    return _icp_filter_service
