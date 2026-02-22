"""
ABN Client — Australian Business Number API Integration

Provides async interface to the ABN Web Services API for business lookups.
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()


class ABNClient:
    """
    Client for interacting with the ABN Web Services API.
    
    Provides methods for:
    - Searching businesses by name with advanced filters
    - Looking up business details by ABN
    - Entity type and status filtering
    """
    
    def __init__(self, auth_guid: str, base_url: str = "https://abr.business.gov.au/abrxmlsearch/AbrXmlSearch.asmx"):
        """
        Initialize ABN client.
        
        Args:
            auth_guid: Authentication GUID from ABN Web Services
            base_url: ABN Web Services base URL
        """
        self.auth_guid = auth_guid
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def search_by_name(
        self,
        name: str,
        state: str = None,
        postcode: str = None,
        active_only: bool = True,
        entity_type_code: List[str] = None
    ) -> List[Dict]:
        """
        Search ABN by name using SearchByNameAdvanced2017.
        
        Args:
            name: Business name to search
            state: State code (NSW, VIC, QLD, etc.)
            postcode: Postcode filter
            active_only: Only return active ABNs
            entity_type_code: Filter by entity type:
                - PRV: Private company
                - PUB: Public company
                - IND: Individual/Sole trader
                - TRT: Trust (usually excluded)
                - SUP: Super fund (usually excluded)
                - OTH: Other
        
        Returns:
            List of business records from ABN API
        """
        await self._ensure_session()
        
        params = {
            'name': name,
            'authenticationGuid': self.auth_guid,
            'searchWidth': 'typical',  # typical, narrow, wide
            'minimumScore': '12',  # Minimum match score (0-100)
            'maxSearchResults': '200'  # Max results per query
        }
        
        if state:
            params['stateCode'] = state
        
        if postcode:
            params['postcode'] = postcode
        
        if active_only:
            params['activeABNsOnly'] = 'Y'
        
        if entity_type_code:
            # ABN API accepts comma-separated entity type codes
            params['entityTypeCode'] = ','.join(entity_type_code)
        
        try:
            url = f"{self.base_url}/SearchByNameAdvanced2017"
            
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                
                # Parse XML response
                xml_text = await response.text()
                results = self._parse_search_results(xml_text)
                
                logger.info(
                    "abn_search_completed",
                    name=name,
                    state=state,
                    results_count=len(results)
                )
                
                return results
                
        except Exception as e:
            logger.error("abn_search_failed", name=name, error=str(e))
            raise
    
    async def lookup_by_abn(self, abn: str) -> Optional[Dict]:
        """
        Lookup business details by ABN.
        
        Args:
            abn: Australian Business Number (11 digits)
        
        Returns:
            Business record or None if not found
        """
        await self._ensure_session()
        
        params = {
            'searchString': abn,
            'authenticationGuid': self.auth_guid,
            'includeHistoricalDetails': 'N'
        }
        
        try:
            url = f"{self.base_url}/AbrXmlSearch"
            
            async with self.session.get(url, params=params) as response:
                response.raise_for_status()
                
                xml_text = await response.text()
                result = self._parse_lookup_result(xml_text)
                
                logger.info("abn_lookup_completed", abn=abn, found=bool(result))
                
                return result
                
        except Exception as e:
            logger.error("abn_lookup_failed", abn=abn, error=str(e))
            return None
    
    def _parse_search_results(self, xml_text: str) -> List[Dict]:
        """
        Parse XML search results into list of dictionaries.
        
        This is a simplified parser - in production you'd want proper XML parsing
        with error handling for malformed responses.
        """
        import xml.etree.ElementTree as ET
        
        results = []
        
        try:
            root = ET.fromstring(xml_text)
            
            # Find all business entity records
            for entity in root.findall('.//businessEntity2017'):
                record = {}
                
                # Basic details
                abn_elem = entity.find('.//identifierValue')
                if abn_elem is not None:
                    record['abn'] = abn_elem.text
                
                # Entity status
                status_elem = entity.find('.//entityStatus/entityStatusCode')
                if status_elem is not None:
                    record['status'] = status_elem.text
                
                # Entity type
                type_elem = entity.find('.//entityType/entityTypeCode')
                if type_elem is not None:
                    record['entity_type'] = type_elem.text
                
                type_name_elem = entity.find('.//entityType/entityDescription')
                if type_name_elem is not None:
                    record['entity_type_name'] = type_name_elem.text
                
                # Main business name
                main_name_elem = entity.find('.//mainName/organisationName')
                if main_name_elem is not None:
                    record['entity_name'] = main_name_elem.text
                
                # Main trading name
                main_trading_elem = entity.find('.//mainTradingName/organisationName')
                if main_trading_elem is not None:
                    record['trading_name'] = main_trading_elem.text
                
                # GST status
                gst_elem = entity.find('.//goodsAndServicesTax/effectiveFrom')
                if gst_elem is not None:
                    record['gst_effective_from'] = gst_elem.text
                
                gst_status_elem = entity.find('.//goodsAndServicesTax')
                if gst_status_elem is not None:
                    record['gst_status'] = 'registered'
                else:
                    record['gst_status'] = 'not_registered'
                
                # Business names (ASIC)
                business_names = []
                for name_elem in entity.findall('.//otherTradingName/organisationName'):
                    if name_elem.text:
                        business_names.append(name_elem.text)
                
                if business_names:
                    record['business_names'] = business_names
                    record['asic_names'] = business_names  # Alias for compatibility
                
                # Address (main business location)
                address_parts = []
                address_elem = entity.find('.//mainBusinessPhysicalAddress')
                if address_elem is not None:
                    for field in ['addressLine1', 'addressLine2', 'locality', 'stateCode', 'postcode']:
                        elem = address_elem.find(f'.//{field}')
                        if elem is not None and elem.text:
                            address_parts.append(elem.text)
                    
                    if address_parts:
                        record['address'] = ', '.join(address_parts)
                        record['state'] = address_elem.find('.//stateCode')
                        if record['state'] is not None:
                            record['state'] = record['state'].text
                
                if record.get('abn'):  # Only include records with valid ABN
                    results.append(record)
            
        except ET.ParseError as e:
            logger.error("xml_parse_error", error=str(e))
        except Exception as e:
            logger.error("search_result_parse_error", error=str(e))
        
        return results
    
    def _parse_lookup_result(self, xml_text: str) -> Optional[Dict]:
        """Parse XML lookup result into dictionary."""
        # Similar to _parse_search_results but for single record lookup
        results = self._parse_search_results(xml_text)
        return results[0] if results else None
    
    async def close(self):
        """Close the client session."""
        if self.session:
            await self.session.close()
            self.session = None