"""
SERP-first identity parser for S2.

Parses DFS SERP results for a bare domain query to extract:
  - business_name (from title, GMB panel, or knowledge graph)
  - primary_location (from GMB address or local_pack)
  - footer_abn (11-digit ABN from abr.business.gov.au snippet)
  - phone (from GMB panel)
  - gmb_rating + gmb_review_count + gmb_category

SERP-first principle: Google indexes AU businesses with clean
structured data. One SERP query resolves identity that HTML
scraping fails to extract.

Ratified: 2026-04-13.
"""

from __future__ import annotations

import re
from typing import Any

ABN_RE = re.compile(r"\b(\d{2}\s?\d{3}\s?\d{3}\s?\d{3})\b")
PHONE_RE = re.compile(r"(?:\+61|0)\d[\d\s\-\.]{7,12}")


def parse_serp_identity(items: list[dict], domain: str) -> dict[str, Any]:
    """
    Parse DFS SERP items for identity fields.

    Args:
        items: list of SERP result items from DFS
        domain: the domain we queried

    Returns:
        dict with: business_name, primary_location, footer_abn, phone,
        gmb_rating, gmb_review_count, gmb_category, source_details
    """
    result: dict[str, Any] = {
        "business_name": None,
        "primary_location": None,
        "footer_abn": None,
        "phone": None,
        "gmb_rating": None,
        "gmb_review_count": None,
        "gmb_category": None,
        "source_details": [],
    }

    clean_domain = domain.replace("www.", "").lower()

    for item in items:
        item_type = item.get("type", "organic")
        item_domain = (item.get("domain") or "").replace("www.", "").lower()
        title = item.get("title") or ""
        desc = item.get("description") or ""
        url = item.get("url") or ""

        # --- GMB / Knowledge Graph / Local Pack ---
        if item_type in ("knowledge_graph", "local_pack", "maps"):
            _extract_gmb(item, result)
            continue

        # --- ABR snippet (abr.business.gov.au) ---
        if "abr.business.gov.au" in url:
            _extract_abr(item, result)
            continue

        # --- Same-domain organic result (business name from title) ---
        if item_type == "organic" and clean_domain in item_domain:
            if not result["business_name"] and title:
                # Clean title: strip common suffixes
                name = re.sub(
                    r"\s*[\|\-–—]\s*(Home|Welcome|Official|Website|Main|Australia).*$",
                    "",
                    title,
                    flags=re.I,
                ).strip()
                if len(name) > 2:
                    result["business_name"] = name
                    result["source_details"].append(f"name:organic_title:{url[:60]}")

        # --- Phone from any snippet mentioning the domain ---
        if clean_domain in item_domain and not result["phone"]:
            phones = PHONE_RE.findall(f"{title} {desc}")
            if phones:
                result["phone"] = re.sub(r"[\s\-\.]", "", phones[0])
                result["source_details"].append(f"phone:organic:{url[:60]}")

    return result


def _extract_gmb(item: dict, result: dict) -> None:
    """Extract GMB/knowledge graph fields."""
    title = item.get("title") or ""
    if title and not result["business_name"]:
        result["business_name"] = title
        result["source_details"].append("name:gmb_panel")

    # Rating
    rating = item.get("rating")
    if rating and not result["gmb_rating"]:
        if isinstance(rating, dict):
            result["gmb_rating"] = rating.get("value") or rating.get("rating_value")
            result["gmb_review_count"] = rating.get("votes_count") or rating.get("reviews_count")
        else:
            result["gmb_rating"] = rating

    # Address / location
    address = item.get("address") or ""
    if not address:
        # Try description for location pattern
        desc = item.get("description") or ""
        # Match "Category in Location" pattern
        loc_match = re.search(
            r"(?:in|located in|serving)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s*[A-Z]{2,3})?)", desc
        )
        if loc_match:
            address = loc_match.group(1)

    if address and not result["primary_location"]:
        result["primary_location"] = address
        result["source_details"].append("location:gmb_panel")

    # Category
    category = item.get("category") or ""
    if not category:
        desc = item.get("description") or ""
        cat_match = re.match(r"^([A-Z][a-z]+(?:\s+[a-z]+)*)\s+in\s+", desc)
        if cat_match:
            category = cat_match.group(1)
    if category and not result["gmb_category"]:
        result["gmb_category"] = category

    # Phone
    phone = item.get("phone")
    if phone and not result["phone"]:
        result["phone"] = re.sub(r"[\s\-\.]", "", str(phone))
        result["source_details"].append("phone:gmb_panel")


def _extract_abr(item: dict, result: dict) -> None:
    """Extract ABN and entity name from ABR snippet."""
    url = item.get("url") or ""
    title = item.get("title") or ""
    desc = item.get("description") or ""
    text = f"{title} {desc}"

    # ABN from URL
    url_match = re.search(r"ABN/View[/?].*?(\d{11})", url)
    if url_match and not result["footer_abn"]:
        result["footer_abn"] = url_match.group(1)
        result["source_details"].append(f"abn:abr_url:{result['footer_abn']}")

    # ABN from text
    if not result["footer_abn"]:
        for m in ABN_RE.findall(text):
            clean = m.replace(" ", "")
            if len(clean) == 11:
                result["footer_abn"] = clean
                result["source_details"].append(f"abn:abr_text:{clean}")
                break

    # Entity name from ABR title: "Current details for ABN XX XXX XXX XXX"
    # Or from description: "Entity name: MADDOCKS"
    entity_match = re.search(r"Entity name:\s*([A-Z][A-Z\s&\',\.\-]+)", desc)
    if entity_match and not result["business_name"]:
        result["business_name"] = entity_match.group(1).strip().title()
        result["source_details"].append("name:abr_entity")
