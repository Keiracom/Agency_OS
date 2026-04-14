"""F4 — Verification gap fills for Gemini nulls.

Fills missing fields from F3 payload using DFS endpoints and phone classifier.
Each fill attempt is independent — partial success is OK.

Ratified: 2026-04-14. Pipeline F architecture.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.common.phone_classifier import classify_au_phone

if TYPE_CHECKING:
    from src.clients.dfs_labs_client import DFSLabsClient

logger = logging.getLogger(__name__)


class VerifyFills:
    """F4 stage: fill null fields from F3 payload."""

    async def fill(
        self,
        domain: str,
        f3_payload: dict,
        dfs_client: "DFSLabsClient",
    ) -> dict:
        """
        Fill null fields from F3 Gemini payload.

        Returns dict of filled fields + source provenance.
        Each fill key mirrors the F3 payload path it fixes.

        Args:
            domain: bare prospect domain
            f3_payload: raw F3 Gemini output dict
            dfs_client: DFSLabsClient instance (already initialised)

        Returns:
            {
              "gmb_fill": dict | None,        — filled GMB rating/reviews
              "linkedin_url_fill": str | None,— filled DM LinkedIn URL
              "phone_classifications": dict,  — phone type for all phones found
              "dm_mismatch": bool | None,     — DM name vs any found LinkedIn name
              "fills_applied": list[str],     — which fills fired
            }
        """
        fills: dict = {
            "gmb_fill": None,
            "linkedin_url_fill": None,
            "phone_classifications": {},
            "dm_mismatch": None,
            "fills_applied": [],
        }

        identity = f3_payload.get("s2_identity", {}) or {}
        dm = (f3_payload.get("s6_dm_identification", {}) or {}).get("primary_dm", {}) or {}
        business_name = identity.get("canonical_business_name") or domain

        # --- Fill 1: Missing GMB rating/reviews → DFS Maps query ---
        if not identity.get("gmb_rating"):
            try:
                gmb = await dfs_client.maps_search_gmb(business_name)
                if gmb and gmb.get("gmb_rating"):
                    fills["gmb_fill"] = gmb
                    fills["fills_applied"].append("gmb_fill")
                    logger.info("F4 gmb_fill: found rating %.1f for %s", gmb["gmb_rating"], domain)
            except Exception as exc:
                logger.warning("F4 gmb_fill failed for %s: %s", domain, exc)

        # --- Fill 2: Missing DM LinkedIn URL → DFS SERP site:linkedin.com/in ---
        dm_name = dm.get("name")
        if dm_name and not dm.get("linkedin_url"):
            try:
                results = await dfs_client.search_linkedin_people(
                    company_name=business_name,
                )
                # Find the best match: DM name appears in result name
                dm_first = dm_name.split()[0].lower() if dm_name else ""
                dm_last = dm_name.split()[-1].lower() if dm_name and len(dm_name.split()) > 1 else ""
                for r in results:
                    candidate_name = (r.get("name") or "").lower()
                    if dm_first and dm_last and dm_first in candidate_name and dm_last in candidate_name:
                        fills["linkedin_url_fill"] = r.get("linkedin_url")
                        fills["fills_applied"].append("linkedin_url_fill")
                        logger.info("F4 linkedin_url_fill: matched %s for %s", r.get("name"), dm_name)
                        break
                    elif dm_first and dm_first in candidate_name:
                        # Weaker match — store only if no better found
                        if not fills["linkedin_url_fill"]:
                            fills["linkedin_url_fill"] = r.get("linkedin_url")
                if fills["linkedin_url_fill"] and "linkedin_url_fill" not in fills["fills_applied"]:
                    fills["fills_applied"].append("linkedin_url_fill")
            except Exception as exc:
                logger.warning("F4 linkedin_url_fill failed for %s: %s", domain, exc)

        # --- Fill 3: Phone classification on all phones found in F3 ---
        phones_to_classify: dict[str, str] = {}
        if identity.get("primary_phone"):
            phones_to_classify["identity_primary"] = identity["primary_phone"]
        if dm.get("direct_phone"):
            phones_to_classify["dm_direct"] = dm["direct_phone"]
        # GMB phone if filled
        if fills["gmb_fill"] and fills["gmb_fill"].get("gmb_phone"):
            phones_to_classify["gmb_phone"] = fills["gmb_fill"]["gmb_phone"]

        for key, raw_phone in phones_to_classify.items():
            try:
                classified = classify_au_phone(raw_phone)
                fills["phone_classifications"][key] = classified
            except Exception as exc:
                logger.warning("F4 phone_classify failed for %s (%s): %s", key, raw_phone, exc)

        if fills["phone_classifications"]:
            fills["fills_applied"].append("phone_classifications")

        # --- Fill 4: dm_mismatch flag ---
        # Compare F3 DM name vs any LinkedIn results we found
        if dm_name and fills.get("linkedin_url_fill"):
            # We found a LinkedIn URL — assume name matched (checked above)
            fills["dm_mismatch"] = False
        elif dm_name and not fills.get("linkedin_url_fill"):
            # No match found — either unresolvable or mismatch
            fills["dm_mismatch"] = None  # indeterminate

        return fills
