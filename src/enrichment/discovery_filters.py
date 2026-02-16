"""
Discovery Filters — Hard and Soft Filtering Logic

Implements the filter rules from session research:
- Hard discard: trusts, super funds, deceased estates, government, cancelled ABNs, no GST
- Soft flag: holdings/investments with zero ASIC names (unless has trading name)
"""
from typing import Tuple, Optional, Dict, Any
import structlog

logger = structlog.get_logger()


class DiscoveryFilters:
    """
    Applies filtering rules to discovery results.
    
    Returns (passed: bool, reason: Optional[str])
    """
    
    # Entity types to hard discard
    DISCARD_ENTITY_TYPES = {
        'trust',
        'super fund',
        'superannuation fund',
        'deceased estate',
        'government entity',
        'government',
        'partnership',  # Usually not B2B targets
    }
    
    # Keywords indicating non-B2B entities
    DISCARD_NAME_KEYWORDS = {
        'trust',
        'super fund',
        'superannuation',
        'deceased estate',
        'government',
        'council',
        'department of',
        'commonwealth of',
        'state of',
    }
    
    # Soft flag patterns (not discarded, but flagged for review)
    SOFT_FLAG_PATTERNS = {
        'holdings',
        'investments',
        'investment',
        'holding',
        'pty ltd atf',  # "As Trustee For"
    }
    
    def apply(self, record: Dict[str, Any], source: str) -> Tuple[bool, Optional[str]]:
        """
        Apply all filter rules to a record.
        
        Returns:
            (True, None) if passed
            (False, reason) if hard discarded
            (True, "soft_flag: reason") if soft flagged but passed
        """
        if source == 'abn_api':
            return self._filter_abn_record(record)
        else:
            # Maps results pass through (filtered later with ABN verification)
            return (True, None)
    
    def _filter_abn_record(self, record: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Filter ABN API results."""
        
        # 1. Check ABN status
        status = (record.get('status') or record.get('abn_status') or '').lower()
        if 'cancelled' in status or 'inactive' in status:
            return (False, "cancelled_abn")
        
        # 2. Check entity type
        entity_type = (record.get('entity_type') or record.get('entity_type_name') or '').lower()
        for discard_type in self.DISCARD_ENTITY_TYPES:
            if discard_type in entity_type:
                return (False, f"entity_type:{discard_type}")
        
        # 3. Check GST registration
        gst_status = record.get('gst_status') or record.get('gst') or ''
        gst_from = record.get('gst_from') or record.get('gst_effective_from')
        
        # If GST status explicitly says not registered
        if isinstance(gst_status, str) and 'not registered' in gst_status.lower():
            return (False, "no_gst_registration")
        
        # If no GST date and no positive status indicator
        if not gst_from and not gst_status:
            # This might be a data gap - soft flag instead of hard discard
            pass
        
        # 4. Check entity name for discard keywords
        entity_name = (record.get('entity_name') or record.get('name') or '').lower()
        for keyword in self.DISCARD_NAME_KEYWORDS:
            if keyword in entity_name:
                return (False, f"name_keyword:{keyword}")
        
        # 5. Soft flag: holdings/investments with no business names
        for pattern in self.SOFT_FLAG_PATTERNS:
            if pattern in entity_name:
                asic_names = record.get('asic_names') or record.get('business_names') or []
                trading_name = record.get('trading_name') or ''
                
                if not asic_names and not trading_name:
                    # Soft flag but pass
                    return (True, "soft_flag:holding_no_business_name")
        
        return (True, None)
    
    def is_holding_with_business_name(self, record: Dict[str, Any]) -> bool:
        """
        Check if record is a holding company WITH business names.
        These should pass as they may be legitimate businesses.
        
        Example: "KJR Holdings" with ASIC name "Bloom Marketing"
        """
        entity_name = (record.get('entity_name') or record.get('name') or '').lower()
        
        is_holding = any(p in entity_name for p in self.SOFT_FLAG_PATTERNS)
        
        if not is_holding:
            return False
        
        asic_names = record.get('asic_names') or record.get('business_names') or []
        trading_name = record.get('trading_name') or ''
        
        return bool(asic_names or trading_name)