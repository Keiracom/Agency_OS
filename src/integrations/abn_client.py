"""
FILE: src/integrations/abn_client.py
PURPOSE: ABN Lookup API client for Australian business data (Tier 1 Siege Waterfall)
PHASE: SIEGE (System Overhaul)
TASK: SIEGE-002
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
  - httpx
  - xmltodict
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 4: Validation threshold 0.70
  - LAW II: All costs in $AUD ($0.00 - FREE)

SIEGE CONTEXT:
  Tier 1 of the Siege Waterfall enrichment system.
  ABN Lookup provides FREE access to Australian Business Register data.
  
  Source: https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx
  Cost: $0.00 AUD (FREE with GUID registration)
  Rate Limits: Reasonable use policy, no hard limits published
  
  Data Available:
    - ABN (Australian Business Number)
    - ACN (Australian Company Number) for companies
    - Business/Entity Name
    - Trading Names (deprecated post-2012)
    - Business Names (ASIC registered)
    - State/Territory
    - Postcode
    - GST registration status
    - Entity type (Company, Sole Trader, Trust, etc.)
    - ABN status (Active/Cancelled)
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any

import httpx
import sentry_sdk
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

try:
    import xmltodict
except ImportError:
    xmltodict = None  # Will raise error on use

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ValidationError

logger = logging.getLogger(__name__)


# ============================================
# CONSTANTS
# ============================================

ABN_LOOKUP_BASE_URL = "https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx"

# Cost per lookup in $AUD (LAW II compliance)
COST_PER_LOOKUP_AUD = 0.00  # FREE

# State code mapping for name search
STATE_CODES = {
    "nsw": "NSW",
    "new south wales": "NSW",
    "vic": "VIC",
    "victoria": "VIC",
    "qld": "QLD",
    "queensland": "QLD",
    "wa": "WA",
    "western australia": "WA",
    "sa": "SA",
    "south australia": "SA",
    "tas": "TAS",
    "tasmania": "TAS",
    "act": "ACT",
    "australian capital territory": "ACT",
    "nt": "NT",
    "northern territory": "NT",
}

# Entity type mapping from ABR codes
ENTITY_TYPE_MAP = {
    "IND": "Individual/Sole Trader",
    "PRV": "Australian Private Company",
    "PUB": "Australian Public Company",
    "TRT": "Trust",
    "PTR": "Partnership",
    "SGE": "State Government Entity",
    "CGE": "Commonwealth Government Entity",
    "LGE": "Local Government Entity",
    "COP": "Co-operative",
    "SUP": "Superannuation Fund",
    "OIE": "Other Incorporated Entity",
    "DES": "Deceased Estate",
    "FXT": "Fixed Trust",
    "DUT": "Discretionary Trust",
    "HYT": "Hybrid Trust",
    "UNT": "Unit Trust",
    "CMT": "Cash Management Trust",
    "PST": "Pooled Superannuation Trust",
    "FPT": "Family Partnership",
    "LPT": "Limited Partnership",
}


# ============================================
# CUSTOM EXCEPTIONS
# ============================================


class ABNLookupError(IntegrationError):
    """ABN Lookup API error."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        details = details or {}
        if code:
            details["abr_error_code"] = code
        super().__init__(service="abn_lookup", message=message, details=details)


class ABNNotFoundError(ABNLookupError):
    """ABN/ACN not found in register."""

    def __init__(self, identifier: str, identifier_type: str = "ABN"):
        super().__init__(
            message=f"{identifier_type} not found: {identifier}",
            details={"identifier": identifier, "identifier_type": identifier_type},
        )


class ABNValidationError(ValidationError):
    """ABN/ACN format validation error."""

    def __init__(self, identifier: str, reason: str):
        super().__init__(
            message=f"Invalid ABN/ACN format: {reason}",
            field="abn" if len(identifier.replace(" ", "")) == 11 else "acn",
            details={"identifier": identifier, "reason": reason},
        )


# ============================================
# ABN/ACN VALIDATION HELPERS
# ============================================


def validate_abn(abn: str) -> str:
    """
    Validate and normalize an ABN.
    
    ABN is 11 digits with a specific checksum algorithm.
    
    Args:
        abn: ABN string (may contain spaces)
        
    Returns:
        Normalized ABN (digits only)
        
    Raises:
        ABNValidationError: If ABN format is invalid
    """
    # Remove spaces and non-digits
    cleaned = re.sub(r"\D", "", abn)
    
    if len(cleaned) != 11:
        raise ABNValidationError(abn, "ABN must be 11 digits")
    
    # ABN checksum validation
    # Weights: 10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    
    # Subtract 1 from first digit for checksum
    digits = [int(d) for d in cleaned]
    digits[0] -= 1
    
    checksum = sum(d * w for d, w in zip(digits, weights))
    
    if checksum % 89 != 0:
        raise ABNValidationError(abn, "ABN checksum validation failed")
    
    return cleaned


def validate_acn(acn: str) -> str:
    """
    Validate and normalize an ACN.
    
    ACN is 9 digits with a specific checksum algorithm.
    
    Args:
        acn: ACN string (may contain spaces)
        
    Returns:
        Normalized ACN (digits only)
        
    Raises:
        ABNValidationError: If ACN format is invalid
    """
    # Remove spaces and non-digits
    cleaned = re.sub(r"\D", "", acn)
    
    if len(cleaned) != 9:
        raise ABNValidationError(acn, "ACN must be 9 digits")
    
    # ACN checksum validation
    # Weights: 8, 7, 6, 5, 4, 3, 2, 1 (for first 8 digits)
    weights = [8, 7, 6, 5, 4, 3, 2, 1]
    
    digits = [int(d) for d in cleaned]
    checksum = sum(d * w for d, w in zip(digits[:8], weights))
    
    remainder = checksum % 10
    check_digit = (10 - remainder) % 10
    
    if check_digit != digits[8]:
        raise ABNValidationError(acn, "ACN checksum validation failed")
    
    return cleaned


def format_abn(abn: str) -> str:
    """Format ABN with standard spacing: XX XXX XXX XXX."""
    cleaned = re.sub(r"\D", "", abn)
    if len(cleaned) == 11:
        return f"{cleaned[:2]} {cleaned[2:5]} {cleaned[5:8]} {cleaned[8:11]}"
    return cleaned


def format_acn(acn: str) -> str:
    """Format ACN with standard spacing: XXX XXX XXX."""
    cleaned = re.sub(r"\D", "", acn)
    if len(cleaned) == 9:
        return f"{cleaned[:3]} {cleaned[3:6]} {cleaned[6:9]}"
    return cleaned


# ============================================
# MAIN CLASS: ABN CLIENT
# ============================================


class ABNClient:
    """
    ABN Lookup API client for Australian business data.
    
    Tier 1 of Siege Waterfall - FREE ($0.00 AUD per lookup).
    
    Provides access to the Australian Business Register via
    the ABN Lookup XML web services.
    
    Usage:
        client = ABNClient()
        
        # Search by ABN
        result = await client.search_by_abn("51 835 430 479")
        
        # Search by name
        results = await client.search_by_name("Woolworths", state="NSW")
        
        # Search by ACN
        result = await client.search_by_acn("080 036 693")
        
        # Bulk search by postcode
        results = await client.bulk_search({"postcode": "2000"})
    
    Attributes:
        guid: Authentication GUID for API access
        _client: Async HTTP client
        _request_count: Number of requests made (for stats)
    
    Note:
        A GUID is required for API access. Register for free at:
        https://abr.business.gov.au/Tools/WebServices
        
        Set ABN_LOOKUP_GUID environment variable or pass to constructor.
    """

    def __init__(self, guid: str | None = None):
        """
        Initialize ABN Lookup client.
        
        Args:
            guid: Authentication GUID (uses settings if not provided)
        """
        self.guid = guid or getattr(settings, "abn_lookup_guid", None) or ""
        
        if not self.guid:
            logger.warning(
                "[ABN] No GUID configured. API calls may fail. "
                "Register for free at: https://abr.business.gov.au/Tools/WebServices"
            )
        
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        
        # Check xmltodict is available
        if xmltodict is None:
            raise IntegrationError(
                service="abn_lookup",
                message="xmltodict package required. Install with: pip install xmltodict",
            )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Accept": "text/xml",
                    "User-Agent": "AgencyOS/1.0 (ABN Lookup Integration)",
                },
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "ABNClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    )
    async def _request(
        self,
        method: str,
        params: dict[str, str],
    ) -> dict[str, Any]:
        """
        Make API request and parse XML response.
        
        Args:
            method: API method name (e.g., "SearchByABNv202001")
            params: Request parameters
            
        Returns:
            Parsed response as dict
            
        Raises:
            ABNLookupError: If API returns an error
            APIError: If HTTP request fails
        """
        client = await self._get_client()
        
        # Add auth GUID to params
        params["authenticationGuid"] = self.guid
        
        url = f"{ABN_LOOKUP_BASE_URL}/{method}"
        
        try:
            self._request_count += 1
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            # Parse XML response
            data = xmltodict.parse(response.text)
            
            # Extract payload
            payload = data.get("ABRPayloadSearchResults", {})
            resp = payload.get("response", {})
            
            # Check for exceptions
            if "exception" in resp:
                exc = resp["exception"]
                code = exc.get("exceptionCode", "UNKNOWN")
                desc = exc.get("exceptionDescription", "Unknown error")
                
                # Log but don't capture expected errors in Sentry
                if code == "SEARCH":
                    logger.debug(f"[ABN] Search returned no results: {desc}")
                else:
                    logger.warning(f"[ABN] API error ({code}): {desc}")
                
                raise ABNLookupError(message=desc, code=code)
            
            return payload
            
        except httpx.HTTPStatusError as e:
            sentry_sdk.set_context(
                "abn_request",
                {
                    "method": method,
                    "params": {k: v for k, v in params.items() if k != "authenticationGuid"},
                    "status_code": e.response.status_code,
                },
            )
            sentry_sdk.capture_exception(e)
            raise APIError(
                service="abn_lookup",
                status_code=e.response.status_code,
                response=e.response.text[:500],
                message=f"ABN Lookup API error: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            sentry_sdk.capture_exception(e)
            raise IntegrationError(
                service="abn_lookup",
                message=f"ABN Lookup request failed: {str(e)}",
            )

    # ============================================
    # PUBLIC METHODS
    # ============================================

    async def search_by_abn(self, abn: str) -> dict[str, Any]:
        """
        Lookup business by ABN number.
        
        Args:
            abn: Australian Business Number (11 digits, spaces allowed)
            
        Returns:
            Business data dict with keys:
                - found: bool
                - abn: Formatted ABN
                - acn: ACN if company (optional)
                - business_name: Main/Legal name
                - trading_name: Trading as name (if any)
                - business_names: ASIC-registered business names
                - state: State/Territory code
                - postcode: Business postcode
                - status: "Active" or "Cancelled"
                - entity_type: Human-readable entity type
                - entity_type_code: Raw ABR entity type code
                - gst_registered: bool
                - gst_from: GST registration date (if registered)
                - source: "abn_lookup"
                - cost_aud: 0.00
                
        Raises:
            ABNValidationError: If ABN format is invalid
            ABNLookupError: If ABN not found
        """
        # Validate and clean ABN
        cleaned_abn = validate_abn(abn)
        
        try:
            payload = await self._request(
                "SearchByABNv202001",
                {
                    "searchString": cleaned_abn,
                    "includeHistoricalDetails": "N",
                },
            )
            
            response = payload.get("response", {})
            record = response.get("businessEntity202001") or response.get("businessEntity201408") or response.get("businessEntity")
            
            if not record:
                raise ABNNotFoundError(cleaned_abn, "ABN")
            
            return self._transform_business_entity(record)
            
        except ABNLookupError as e:
            if "Search" in str(e.details.get("abr_error_code", "")):
                raise ABNNotFoundError(cleaned_abn, "ABN")
            raise

    async def search_by_name(
        self,
        name: str,
        state: str | None = None,
        postcode: str | None = None,
        legal_name: bool = True,
        trading_name: bool = True,
        business_name: bool = True,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search businesses by name, optionally filter by state.
        
        Uses ABRSearchByNameAdvancedSimpleProtocol2017 for maximum flexibility.
        
        Args:
            name: Business name to search for
            state: State/Territory code or name (optional)
            postcode: Filter by postcode (optional)
            legal_name: Include legal/entity names in search
            trading_name: Include trading names in search
            business_name: Include ASIC business names in search
            limit: Maximum results to return (default 20, max 200)
            
        Returns:
            List of matching business summaries with keys:
                - abn: ABN
                - business_name: Matched name
                - name_type: Type of name matched
                - state: State code
                - postcode: Postcode
                - status: ABN status
                - score: Search relevance score
                - source: "abn_lookup"
                
        Raises:
            ValidationError: If name is too short
        """
        if len(name.strip()) < 3:
            raise ValidationError(
                message="Search name must be at least 3 characters",
                field="name",
            )
        
        # Build state filter params
        state_params = {s: "N" for s in ["NSW", "SA", "ACT", "VIC", "WA", "NT", "QLD", "TAS"]}
        
        if state:
            # Normalize state code
            state_normalized = STATE_CODES.get(state.lower(), state.upper())
            if state_normalized in state_params:
                state_params[state_normalized] = "Y"
            else:
                logger.warning(f"[ABN] Unknown state code: {state}")
        else:
            # If no state filter, search all states
            state_params = {s: "Y" for s in state_params}
        
        params = {
            "name": name,
            "postcode": postcode or "",
            "legalName": "Y" if legal_name else "N",
            "tradingName": "Y" if trading_name else "N",
            "businessName": "Y" if business_name else "N",
            "activeABNsOnly": "Y",
            "searchWidth": "typical",
            "minimumScore": "0",
            "maxSearchResults": str(min(limit, 200)),
            **state_params,
        }
        
        try:
            payload = await self._request(
                "ABRSearchByNameAdvancedSimpleProtocol2017",
                params,
            )
            
            response = payload.get("response", {})
            search_results = response.get("searchResultsList", {})
            
            if not search_results:
                return []
            
            # Handle single result vs list
            results = search_results.get("searchResultsRecord", [])
            if isinstance(results, dict):
                results = [results]
            
            return [self._transform_search_result(r) for r in results[:limit]]
            
        except ABNLookupError as e:
            # No results is not an error
            if "Search" in str(e.details.get("abr_error_code", "")):
                return []
            raise

    async def search_by_acn(self, acn: str) -> dict[str, Any]:
        """
        Lookup business by ACN (Australian Company Number).
        
        ACN is the 9-digit company number issued by ASIC.
        
        Args:
            acn: Australian Company Number (9 digits, spaces allowed)
            
        Returns:
            Business data dict (same format as search_by_abn)
            
        Raises:
            ABNValidationError: If ACN format is invalid
            ABNLookupError: If ACN not found
        """
        # Validate and clean ACN
        cleaned_acn = validate_acn(acn)
        
        try:
            payload = await self._request(
                "SearchByASICv201408",
                {
                    "searchString": cleaned_acn,
                    "includeHistoricalDetails": "N",
                },
            )
            
            response = payload.get("response", {})
            record = response.get("businessEntity201408") or response.get("businessEntity")
            
            if not record:
                raise ABNNotFoundError(cleaned_acn, "ACN")
            
            return self._transform_business_entity(record)
            
        except ABNLookupError as e:
            if "Search" in str(e.details.get("abr_error_code", "")):
                raise ABNNotFoundError(cleaned_acn, "ACN")
            raise

    async def bulk_search(
        self,
        criteria: dict[str, Any],
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Bulk search for seeding lead pool.
        
        Supports various search criteria for finding businesses:
        - postcode: Search by postcode (returns ABN list)
        - name + state: Search by name with state filter
        
        Args:
            criteria: Search criteria dict:
                - postcode: Australian postcode
                - name: Business name
                - state: State filter
            limit: Maximum results per query
            
        Returns:
            List of business records (enriched where possible)
            
        Example:
            # Find all active businesses in Sydney CBD
            results = await client.bulk_search({"postcode": "2000"}, limit=50)
            
            # Search for marketing agencies in Victoria
            results = await client.bulk_search({
                "name": "marketing agency",
                "state": "VIC"
            })
        """
        results = []
        
        # Postcode search
        if criteria.get("postcode"):
            postcode = str(criteria["postcode"])
            if not re.match(r"^\d{4}$", postcode):
                raise ValidationError(
                    message="Postcode must be 4 digits",
                    field="postcode",
                )
            
            try:
                payload = await self._request(
                    "SearchByPostcode",
                    {"postcode": postcode},
                )
                
                response = payload.get("response", {})
                abn_list = response.get("abnList", {})
                
                if abn_list:
                    abns = abn_list.get("abn", [])
                    if isinstance(abns, str):
                        abns = [abns]
                    
                    # Enrich first N ABNs with full details
                    enriched = []
                    for abn in abns[:limit]:
                        try:
                            # Rate limit: 5 requests per second
                            await asyncio.sleep(0.2)
                            detail = await self.search_by_abn(abn)
                            enriched.append(detail)
                        except (ABNNotFoundError, ABNLookupError) as e:
                            logger.debug(f"[ABN] Skipping {abn}: {e}")
                            continue
                    
                    results.extend(enriched)
                    
            except ABNLookupError:
                pass  # No results for postcode
        
        # Name search
        elif criteria.get("name"):
            name_results = await self.search_by_name(
                name=criteria["name"],
                state=criteria.get("state"),
                postcode=criteria.get("postcode"),
                limit=limit,
            )
            results.extend(name_results)
        
        else:
            raise ValidationError(
                message="Bulk search requires 'postcode' or 'name' in criteria",
            )
        
        return results

    async def enrich_from_abn(self, abn: str) -> dict[str, Any]:
        """
        Enrich lead data from ABN lookup.
        
        This method is designed for Siege Waterfall Tier 1 integration.
        Returns data in a format compatible with the waterfall enrichment.
        
        Args:
            abn: Australian Business Number
            
        Returns:
            Enrichment data dict with:
                - found: bool
                - source: "abn_lookup"
                - cost_aud: 0.00
                - (all business data fields)
        """
        try:
            result = await self.search_by_abn(abn)
            result["found"] = True
            return result
        except (ABNNotFoundError, ABNValidationError):
            return {
                "found": False,
                "source": "abn_lookup",
                "cost_aud": COST_PER_LOOKUP_AUD,
            }

    # ============================================
    # TRANSFORM METHODS
    # ============================================

    def _transform_business_entity(self, record: dict) -> dict[str, Any]:
        """
        Transform ABR business entity to standard format.
        
        Handles the complex nested structure of ABR XML responses.
        """
        # Extract ABN
        abn_info = record.get("ABN", {})
        if isinstance(abn_info, list):
            # Multiple ABNs (historical) - get current
            current = next((a for a in abn_info if a.get("isCurrentIndicator") == "Y"), abn_info[0])
            abn_info = current
        
        abn = abn_info.get("identifierValue", "")
        abn_status = abn_info.get("identifierStatus", "Unknown")
        
        # Extract entity type
        entity_type_info = record.get("entityType", {})
        entity_type_code = entity_type_info.get("entityTypeCode", "")
        entity_type = ENTITY_TYPE_MAP.get(
            entity_type_code,
            entity_type_info.get("entityDescription", entity_type_code),
        )
        
        # Extract GST status
        gst_info = record.get("goodsAndServicesTax", {})
        if isinstance(gst_info, list):
            gst_info = next((g for g in gst_info if g.get("effectiveTo") is None), gst_info[0] if gst_info else {})
        
        gst_registered = gst_info.get("effectiveFrom") is not None
        gst_from = gst_info.get("effectiveFrom")
        
        # Extract names
        business_name = ""
        trading_name = ""
        business_names = []
        
        # Main name (for non-individuals)
        main_name = record.get("mainName", {})
        if isinstance(main_name, list):
            main_name = next((n for n in main_name if n.get("isCurrentIndicator") == "Y"), main_name[0] if main_name else {})
        if main_name:
            business_name = main_name.get("organisationName", "")
        
        # Legal name (for individuals)
        legal_name = record.get("legalName", {})
        if isinstance(legal_name, list):
            legal_name = next((n for n in legal_name if n.get("isCurrentIndicator") == "Y"), legal_name[0] if legal_name else {})
        if legal_name and not business_name:
            given_name = legal_name.get("givenName", "")
            family_name = legal_name.get("familyName", "")
            business_name = f"{given_name} {family_name}".strip()
        
        # Main trading name
        main_trading = record.get("mainTradingName", {})
        if isinstance(main_trading, list):
            main_trading = next((n for n in main_trading if n.get("isCurrentIndicator") == "Y"), main_trading[0] if main_trading else {})
        if main_trading:
            trading_name = main_trading.get("organisationName", "")
        
        # Business names (ASIC registered since 2012)
        bn_list = record.get("businessName", [])
        if isinstance(bn_list, dict):
            bn_list = [bn_list]
        for bn in bn_list:
            if bn.get("isCurrentIndicator") == "Y":
                bn_name = bn.get("organisationName", "")
                if bn_name:
                    business_names.append(bn_name)
        
        # Extract address
        address_info = record.get("mainBusinessPhysicalAddress", {})
        if isinstance(address_info, list):
            address_info = next((a for a in address_info if a.get("isCurrentIndicator") == "Y"), address_info[0] if address_info else {})
        
        state = address_info.get("stateCode", "")
        postcode = address_info.get("postcode", "")
        
        # Extract ACN (for companies)
        acn = ""
        asic_number = record.get("ASICNumber", "")
        if asic_number:
            acn = asic_number
        
        return {
            "found": True,
            "source": "abn_lookup",
            "cost_aud": COST_PER_LOOKUP_AUD,
            # Identifiers
            "abn": format_abn(abn),
            "abn_raw": abn,
            "acn": format_acn(acn) if acn else None,
            "acn_raw": acn if acn else None,
            # Names
            "business_name": business_name,
            "trading_name": trading_name if trading_name != business_name else None,
            "business_names": business_names if business_names else None,
            # Location
            "state": state,
            "postcode": postcode,
            # Status
            "status": "Active" if abn_status == "Active" else "Cancelled",
            "abn_status_raw": abn_status,
            # Entity
            "entity_type": entity_type,
            "entity_type_code": entity_type_code,
            # GST
            "gst_registered": gst_registered,
            "gst_from": gst_from,
            # Metadata
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    def _transform_search_result(self, record: dict) -> dict[str, Any]:
        """Transform ABR search result to standard format."""
        abn = record.get("ABN", {}).get("identifierValue", "")
        abn_status = record.get("ABN", {}).get("identifierStatus", "")
        
        # Get matched name
        name_info = record.get("mainName", {})
        name = name_info.get("organisationName", "")
        name_type = "main"
        
        if not name:
            name_info = record.get("legalName", {})
            if name_info:
                given = name_info.get("givenName", "")
                family = name_info.get("familyName", "")
                name = f"{given} {family}".strip()
                name_type = "legal"
        
        if not name:
            name_info = record.get("businessName", {})
            name = name_info.get("organisationName", "")
            name_type = "business"
        
        if not name:
            name_info = record.get("mainTradingName", {})
            name = name_info.get("organisationName", "")
            name_type = "trading"
        
        # Address
        state = record.get("mainBusinessPhysicalAddress", {}).get("stateCode", "")
        postcode = record.get("mainBusinessPhysicalAddress", {}).get("postcode", "")
        
        # Score
        score = int(record.get("score", 0))
        
        return {
            "abn": format_abn(abn),
            "abn_raw": abn,
            "business_name": name,
            "name_type": name_type,
            "state": state,
            "postcode": postcode,
            "status": "Active" if abn_status == "Active" else "Cancelled",
            "score": score,
            "source": "abn_lookup",
            "cost_aud": COST_PER_LOOKUP_AUD,
        }

    # ============================================
    # UTILITY METHODS
    # ============================================

    def get_stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            "service": "abn_lookup",
            "requests_made": self._request_count,
            "cost_aud": 0.00,  # Always free
            "guid_configured": bool(self.guid),
        }


# ============================================
# SINGLETON ACCESSOR
# ============================================

_abn_client: ABNClient | None = None


def get_abn_client() -> ABNClient:
    """Get or create ABNClient singleton instance."""
    global _abn_client
    if _abn_client is None:
        _abn_client = ABNClient()
    return _abn_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials (uses settings.abn_lookup_guid)
# [x] Retry logic with tenacity
# [x] Type hints on all methods
# [x] Docstrings on all methods
# [x] Custom exceptions (ABNLookupError, ABNNotFoundError, ABNValidationError)
# [x] Cost tracking in $AUD (LAW II compliance) - $0.00 FREE
# [x] ABN/ACN validation with checksum
# [x] search_by_abn method
# [x] search_by_name method with state filter
# [x] search_by_acn method
# [x] bulk_search method for lead pool seeding
# [x] enrich_from_abn for Siege Waterfall integration
# [x] Graceful degradation (no GUID = warning, not error)
# [x] Rate limiting in bulk operations (0.2s delay)
# [x] Sentry error capture
# [x] Singleton accessor pattern
# [x] Async context manager support
