"""
Contract: src/config/category_registry.py
Purpose: Maps agency services to DFS category codes for service-first discovery.
         Every business in Australia that needs SEO is a prospect — categories
         segment the DFS API call, they do not limit the prospect pool.
Directive: #298

KEY INSIGHT (ratified 2026-03-30):
  Campaign = service the agency sells
  Industry + geography are optional filters, not campaign definitions
  Discovery sweeps nationally for signals matching the service

DFS domain_metrics_by_categories accepts multiple category codes per call.
One call returned 22,592 AU dental domains (~$0.10). API handles bulk efficiently.
Max safe batch: 20 category codes per API call (conservative limit).

Category codes sourced from DFS /v3/dataforseo_labs/categories (3,182 total categories).
"""
from __future__ import annotations

# ── Maximum category codes per DFS API call ──────────────────────────────────
MAX_CATEGORIES_PER_CALL = 20

# ── Human-readable labels (for dashboard display) ────────────────────────────
CATEGORY_LABELS: dict[int, str] = {
    # Dental
    10514: "Dentists & Dental Services",

    # Construction & Trades
    10282: "Building Construction & Maintenance",
    11138: "Building Painting Services",
    13462: "Plumbing",
    11295: "Electrical Wiring",
    11284: "HVAC & Climate Control",
    11147: "HVAC Service & Repair",

    # Legal
    10163: "Legal",
    13686: "Attorneys & Law Firms",

    # Automotive
    13309: "Automotive GPS Systems",
    10040: "Auto Parts & Accessories",
    11284: "HVAC & Climate Control",

    # Real Estate
    10531: "Real Estate Investments",
    10830: "Real Estate Rental & Leasing",

    # Accounting & Finance
    11093: "Accounting & Auditing",
    12391: "Bookkeeping",

    # Medical
    10520: "Hospitals & Health Clinics",
    10509: "Laboratory & Diagnostic Services",

    # Hospitality
    10020: "Dining & Nightlife",
    12975: "Restaurant Reviews & Listings",

    # Fitness
    10123: "Fitness",
    12049: "Fitness Instruction & Training",

    # Hair & Beauty
    10333: "Hair Salons & Styling Services",

    # Veterinary
    11979: "Veterinary",

    # Marketing
    11088: "Advertising & Marketing",
    12376: "Internet Marketing",

    # Home Services
    10418: "Home Heating & Cooling",
}

# ── Service → category code mapping ──────────────────────────────────────────
# Key insight: ALL categories work for ALL services.
# The mapping below reflects SIGNAL RELEVANCE — categories where the
# target signals (ads without tracking, no analytics, etc.) are most
# commonly observed for each service.
#
# For a complete service-first sweep, use ALL_DISCOVERY_CATEGORIES.

SERVICE_CATEGORY_MAP: dict[str, list[int]] = {
    "seo": [
        # High-organic-traffic verticals where SEO signal is strongest
        10514,  # Dentists & Dental Services
        13462,  # Plumbing
        11295,  # Electrical Wiring
        11147,  # HVAC Service & Repair
        11284,  # HVAC & Climate Control
        10163,  # Legal
        13686,  # Attorneys & Law Firms
        10520,  # Hospitals & Health Clinics
        10282,  # Building Construction & Maintenance
        11138,  # Building Painting Services
        10531,  # Real Estate Investments
        11093,  # Accounting & Auditing
        12391,  # Bookkeeping
        10123,  # Fitness
        12049,  # Fitness Instruction & Training
        10333,  # Hair Salons & Styling Services
        11979,  # Veterinary
        10020,  # Dining & Nightlife
        12975,  # Restaurant Reviews & Listings
        10418,  # Home Heating & Cooling
    ],
    "google_ads": [
        # Verticals with highest ad spend and conversion tracking gaps
        10514,  # Dentists & Dental Services
        13462,  # Plumbing
        11295,  # Electrical Wiring
        11147,  # HVAC Service & Repair
        10163,  # Legal
        13686,  # Attorneys & Law Firms
        10520,  # Hospitals & Health Clinics
        10282,  # Building Construction & Maintenance
        10531,  # Real Estate Investments
        11093,  # Accounting & Auditing
        10123,  # Fitness
        10333,  # Hair Salons & Styling Services
        11979,  # Veterinary
        12049,  # Fitness Instruction & Training
        11138,  # Building Painting Services
        11284,  # HVAC & Climate Control
        12391,  # Bookkeeping
        10020,  # Dining & Nightlife
        11979,  # Veterinary
        10418,  # Home Heating & Cooling
    ],
    "social_media": [
        # Verticals where social proof and engagement signals are strong
        10514,  # Dentists & Dental Services
        10333,  # Hair Salons & Styling Services
        10123,  # Fitness
        12049,  # Fitness Instruction & Training
        10020,  # Dining & Nightlife
        12975,  # Restaurant Reviews & Listings
        11979,  # Veterinary
        13462,  # Plumbing
        11295,  # Electrical Wiring
        10282,  # Building Construction & Maintenance
        11138,  # Building Painting Services
        10531,  # Real Estate Investments
        10163,  # Legal
        13686,  # Attorneys & Law Firms
        10520,  # Hospitals & Health Clinics
        11093,  # Accounting & Auditing
        11147,  # HVAC Service & Repair
        12391,  # Bookkeeping
        11284,  # HVAC & Climate Control
        10418,  # Home Heating & Cooling
    ],
    "web_design": [
        # Verticals where website quality gap signal is strongest
        10514,  # Dentists & Dental Services
        13462,  # Plumbing
        11295,  # Electrical Wiring
        10163,  # Legal
        13686,  # Attorneys & Law Firms
        10520,  # Hospitals & Health Clinics
        10282,  # Building Construction & Maintenance
        11138,  # Building Painting Services
        10531,  # Real Estate Investments
        11093,  # Accounting & Auditing
        12391,  # Bookkeeping
        10123,  # Fitness
        10333,  # Hair Salons & Styling Services
        11979,  # Veterinary
        12049,  # Fitness Instruction & Training
        11147,  # HVAC Service & Repair
        11284,  # HVAC & Climate Control
        10020,  # Dining & Nightlife
        12975,  # Restaurant Reviews & Listings
        10418,  # Home Heating & Cooling
    ],
}

# ── All discovery categories (for unrestricted service-first sweep) ───────────
ALL_DISCOVERY_CATEGORIES: list[int] = sorted(set(
    code
    for codes in SERVICE_CATEGORY_MAP.values()
    for code in codes
))

# ── Industry vertical groupings (for preferred_industries soft-weighting) ─────
INDUSTRY_VERTICALS: dict[str, list[int]] = {
    "dental":       [10514],
    "trades":       [13462, 11295, 11147, 11284, 10418, 11138],
    "legal":        [10163, 13686],
    "construction": [10282, 11138],
    "hospitality":  [10020, 12975],
    "automotive":   [13309, 10040],
    "real_estate":  [10531, 10830],
    "accounting":   [11093, 12391],
    "medical":      [10520, 10509],
    "fitness":      [10123, 12049],
    "hair_beauty":  [10333],
    "veterinary":   [11979],
    "hvac":         [11284, 11147, 10418],
    "marketing":    [11088, 12376],
}


def get_discovery_categories(
    services: list[str],
    preferred_industries: list[str] | None = None,
) -> list[int]:
    """
    Return the union of DFS category codes for the given services.

    If preferred_industries is provided, codes matching those industries
    are sorted first (soft weighting — they appear earlier in the list
    so workers process them first in round-robin).

    Args:
        services: List of service slugs the agency sells.
                  e.g. ["seo", "google_ads"]
        preferred_industries: Optional list of industry slugs to prioritise.
                  e.g. ["dental", "trades"]

    Returns:
        Deduplicated list of category code ints.
        Preferred industry codes appear first if specified.
    """
    # Collect all codes for requested services
    all_codes: set[int] = set()
    for svc in services:
        all_codes.update(SERVICE_CATEGORY_MAP.get(svc, []))

    if not all_codes:
        # Fallback: return all discovery categories
        all_codes = set(ALL_DISCOVERY_CATEGORIES)

    if preferred_industries:
        preferred_codes: list[int] = []
        for ind in preferred_industries:
            for code in INDUSTRY_VERTICALS.get(ind, []):
                if code in all_codes and code not in preferred_codes:
                    preferred_codes.append(code)
        remaining = [c for c in ALL_DISCOVERY_CATEGORIES if c in all_codes and c not in preferred_codes]
        return preferred_codes + remaining

    # Default order: stable sort by code for reproducibility
    return sorted(all_codes)
