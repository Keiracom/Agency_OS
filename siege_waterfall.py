#!/usr/bin/env python3
"""
Siege Waterfall - ABN→GMB Name Resolution Pipeline
Implements CEO Directive #014

This module contains waterfall name resolution utilities for GMB matching.

NOTE: T2 GMB enrichment has been deprecated (CEO Directive T0/T2 Merge).
T0 discovery via Bright Data GMB already returns all GMB fields (rating, phone,
address, website, review_count, category). T2 enrichment was redundant.

The waterfall name utilities (NameProcessor, GenericNameFilter) remain available
for T0 discovery query building.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import json

# Supabase imports (assumed to be available)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# GMB API imports (assumed to be available)
try:
    from gmb_client import GMBClient
    GMB_AVAILABLE = True
except ImportError:
    GMB_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ABNRecord:
    """ABN record structure from bulk extract"""
    abn: str
    business_name: str  # Legal name
    business_names: List[str]  # ASIC-registered business names (since 2012)
    trading_name: Optional[str]  # Legacy pre-2012 trading names
    postcode: Optional[str]
    state: Optional[str]


@dataclass
class GMBSearchResult:
    """GMB search result structure"""
    found: bool
    place_id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    match_score: Optional[float] = None


@dataclass
class WaterfallAttempt:
    """Single waterfall search attempt tracking"""
    abn: str
    abn_name: str  # Original business name
    search_name_used: str
    waterfall_step: str  # a/b/c/d
    gmb_result: str  # found/not_found
    match_score: Optional[float]
    pass_fail: str
    timestamp: datetime


class GenericNameFilter:
    """Filter for generic business names that should skip GMB enrichment"""
    
    GENERIC_PATTERNS = [
        'holdings',
        'enterprises', 
        'investments',
        'trust',
        'group',
        'services',
        'management',
        'properties',
        'consulting'
    ]
    
    @classmethod
    def is_generic(cls, business_names: List[str], legal_name: str) -> bool:
        """
        Check if business should skip Tier 2 GMB enrichment
        
        Args:
            business_names: ASIC business names array
            legal_name: Legal business name
            
        Returns:
            True if should skip GMB enrichment
        """
        # Only apply filter if no ASIC business names exist
        if business_names:
            return False
            
        # Check legal name against generic patterns
        legal_lower = legal_name.lower()
        return any(pattern in legal_lower for pattern in cls.GENERIC_PATTERNS)


class NameProcessor:
    """Process business names for GMB search"""
    
    # Legal entity suffixes to strip
    LEGAL_SUFFIXES = [
        'pty ltd',
        'pty. ltd.',
        'pty limited',
        'proprietary limited',
        'ltd',
        'limited',
        'pty',
        'proprietary'
    ]
    
    @classmethod
    def strip_legal_suffixes(cls, name: str) -> str:
        """Strip legal entity suffixes from business name"""
        if not name:
            return name
            
        name_lower = name.lower().strip()
        
        for suffix in cls.LEGAL_SUFFIXES:
            if name_lower.endswith(suffix):
                # Remove suffix and clean up
                stripped = name[:-(len(suffix))].strip()
                # Remove trailing comma or period
                stripped = re.sub(r'[,.]$', '', stripped).strip()
                return stripped
                
        return name.strip()
    
    @classmethod
    def create_location_search(cls, name: str, postcode: str, state: str) -> str:
        """Create location-pinned search string"""
        if not all([name, postcode, state]):
            return name
            
        return f"{name} {postcode} {state} Australia"


class Tier2GMBEnricher:
    """Tier 2 GMB enrichment with waterfall name resolution"""
    
    def __init__(self, supabase_client: Optional[Client] = None, gmb_client: Optional[Any] = None):
        self.supabase = supabase_client
        self.gmb = gmb_client
        self.attempts: List[WaterfallAttempt] = []
        
    def process_abn_record(self, abn_record: ABNRecord) -> Tuple[bool, Optional[GMBSearchResult], str]:
        """
        Process ABN record through Tier 2 GMB waterfall
        
        Args:
            abn_record: ABN record to process
            
        Returns:
            Tuple of (success, gmb_result, status_message)
        """
        # Check generic name filter first
        if GenericNameFilter.is_generic(abn_record.business_names, abn_record.business_name):
            logger.info(f"Skipping ABN {abn_record.abn} - generic name pattern")
            return False, None, "tier2_skipped_generic_name"
        
        # Execute waterfall search
        success, gmb_result = self._execute_waterfall_search(abn_record)
        
        # Log all attempts to database
        self._log_attempts()
        
        if success:
            return True, gmb_result, "tier2_gmb_found"
        else:
            return False, None, "tier2_gmb_not_found"
    
    def _execute_waterfall_search(self, abn_record: ABNRecord) -> Tuple[bool, Optional[GMBSearchResult]]:
        """Execute the waterfall name resolution search"""
        search_names = self._build_search_waterfall(abn_record)
        
        for step, search_name in search_names:
            logger.info(f"Waterfall step {step}: searching for '{search_name}'")
            
            gmb_result = self._search_gmb(search_name)
            
            # Log this attempt
            attempt = WaterfallAttempt(
                abn=abn_record.abn,
                abn_name=abn_record.business_name,
                search_name_used=search_name,
                waterfall_step=step,
                gmb_result="found" if gmb_result.found else "not_found",
                match_score=gmb_result.match_score,
                pass_fail="pass" if gmb_result.found else "fail",
                timestamp=datetime.now(timezone.utc)
            )
            self.attempts.append(attempt)
            
            if gmb_result.found:
                logger.info(f"GMB match found at step {step} for ABN {abn_record.abn}")
                return True, gmb_result
        
        logger.info(f"No GMB match found for ABN {abn_record.abn} after all waterfall steps")
        return False, None
    
    def _build_search_waterfall(self, abn_record: ABNRecord) -> List[Tuple[str, str]]:
        """
        Build waterfall search terms according to CEO Directive #014
        
        Returns:
            List of (step_id, search_name) tuples
        """
        search_terms = []
        
        # Step A: ASIC business names from business_names[] array (try each)
        if abn_record.business_names:
            for i, business_name in enumerate(abn_record.business_names):
                if business_name and business_name.strip():
                    step_id = f"a{i+1}" if len(abn_record.business_names) > 1 else "a"
                    search_terms.append((step_id, business_name.strip()))
        
        # Step B: ABN trading_name (pre-2012 legacy)
        if abn_record.trading_name and abn_record.trading_name.strip():
            search_terms.append(("b", abn_record.trading_name.strip()))
        
        # Step C: Legal name stripped of legal suffixes
        if abn_record.business_name:
            stripped_name = NameProcessor.strip_legal_suffixes(abn_record.business_name)
            if stripped_name and stripped_name != abn_record.business_name:
                search_terms.append(("c", stripped_name))
        
        # Step D: Location-pinned search
        if abn_record.business_name and abn_record.postcode and abn_record.state:
            base_name = NameProcessor.strip_legal_suffixes(abn_record.business_name) or abn_record.business_name
            location_search = NameProcessor.create_location_search(
                base_name, abn_record.postcode, abn_record.state
            )
            if location_search != base_name:  # Only add if location context was added
                search_terms.append(("d", location_search))
        
        return search_terms
    
    def _search_gmb(self, search_name: str) -> GMBSearchResult:
        """
        Search GMB for business name
        
        Args:
            search_name: Name to search for
            
        Returns:
            GMBSearchResult object
        """
        if not self.gmb or not GMB_AVAILABLE:
            # Mock result for testing/development
            logger.warning("GMB client not available, using mock result")
            return GMBSearchResult(
                found=False,
                match_score=0.0
            )
        
        try:
            # Actual GMB search would go here
            result = self.gmb.search(search_name)
            
            # Convert to our result format
            if result and result.get('places'):
                place = result['places'][0]  # Take first result
                return GMBSearchResult(
                    found=True,
                    place_id=place.get('place_id'),
                    name=place.get('name'),
                    address=place.get('formatted_address'),
                    phone=place.get('formatted_phone_number'),
                    website=place.get('website'),
                    rating=place.get('rating'),
                    review_count=place.get('user_ratings_total'),
                    match_score=self._calculate_match_score(search_name, place.get('name', ''))
                )
            else:
                return GMBSearchResult(found=False, match_score=0.0)
                
        except Exception as e:
            logger.error(f"GMB search failed for '{search_name}': {e}")
            return GMBSearchResult(found=False, match_score=0.0)
    
    def _calculate_match_score(self, search_name: str, found_name: str) -> float:
        """
        Calculate match score between search name and found name
        
        Args:
            search_name: Name searched for
            found_name: Name found in results
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not search_name or not found_name:
            return 0.0
            
        # Simple token-based similarity
        search_tokens = set(search_name.lower().split())
        found_tokens = set(found_name.lower().split())
        
        if not search_tokens:
            return 0.0
            
        intersection = search_tokens.intersection(found_tokens)
        return len(intersection) / len(search_tokens)
    
    def _log_attempts(self):
        """Log all waterfall attempts to Supabase"""
        if not self.attempts or not self.supabase or not SUPABASE_AVAILABLE:
            if self.attempts:
                logger.warning("Supabase not available, logging attempts locally")
                for attempt in self.attempts:
                    logger.info(f"GMB Attempt: {attempt}")
            return
        
        try:
            # Prepare data for Supabase insertion
            log_data = []
            for attempt in self.attempts:
                log_data.append({
                    'abn': attempt.abn,
                    'abn_name': attempt.abn_name,
                    'search_name_used': attempt.search_name_used,
                    'waterfall_step': attempt.waterfall_step,
                    'gmb_result': attempt.gmb_result,
                    'match_score': attempt.match_score,
                    'pass_fail': attempt.pass_fail,
                    'timestamp': attempt.timestamp.isoformat()
                })
            
            # Insert to tier2_gmb_match_log table
            result = self.supabase.table('tier2_gmb_match_log').insert(log_data).execute()
            logger.info(f"Logged {len(log_data)} waterfall attempts to Supabase")
            
        except Exception as e:
            logger.error(f"Failed to log attempts to Supabase: {e}")
            # Fall back to local logging
            for attempt in self.attempts:
                logger.info(f"GMB Attempt (fallback): {attempt}")
        
        # Clear attempts after logging
        self.attempts.clear()


class SiegeWaterfall:
    """Main siege waterfall orchestrator"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """
        Initialize Siege Waterfall
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key
        """
        self.supabase_client = None
        if SUPABASE_AVAILABLE and supabase_url and supabase_key:
            self.supabase_client = create_client(supabase_url, supabase_key)
        
        self.tier2_enricher = Tier2GMBEnricher(
            supabase_client=self.supabase_client,
            gmb_client=None  # Will be injected when available
        )
    
    def process_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single lead through the siege waterfall
        
        Args:
            lead_data: Lead data containing ABN information and T0 GMB data
            
        Returns:
            Processed lead data (GMB fields preserved from T0 discovery)
            
        NOTE: T2 GMB enrichment has been removed (CEO Directive T0/T2 Merge).
        T0 discovery via Bright Data GMB already provides all GMB fields:
        rating, phone, address, website, review_count, category.
        This method now passes through leads without redundant GMB API calls.
        """
        result_data = lead_data.copy()
        
        # T2 GMB enrichment removed — T0 discovery already provides GMB fields
        # Check if T0 already populated GMB data
        has_gmb_from_t0 = any([
            lead_data.get('rating'),
            lead_data.get('phone'),
            lead_data.get('address'),
            lead_data.get('website'),
            lead_data.get('review_count'),
            lead_data.get('category'),
            lead_data.get('gmb_data')  # Alternative: nested GMB object
        ])
        
        if has_gmb_from_t0:
            result_data['tier2_status'] = 'tier2_skipped_t0_has_gmb'
            result_data['tier2_success'] = True  # T0 already succeeded
            logger.info(f"Skipping T2 GMB enrichment for {lead_data.get('abn', 'unknown')} - T0 already has GMB data")
        else:
            # No GMB data from T0 — mark as not enriched
            # This shouldn't happen if T0 ran correctly, but handle gracefully
            result_data['tier2_status'] = 'tier2_skipped_no_t0_gmb'
            result_data['tier2_success'] = False
            logger.warning(f"Lead {lead_data.get('abn', 'unknown')} has no GMB data from T0 discovery")
        
        return result_data


def main():
    """Main function for testing"""
    import os
    
    # Initialize with environment variables
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    waterfall = SiegeWaterfall(supabase_url, supabase_key)
    
    # Test data
    test_lead = {
        'abn': '12345678901',
        'business_name': 'Test Business Pty Ltd',
        'business_names': ['Test Business Services', 'Test Co'],
        'trading_name': 'TestCorp',
        'postcode': '2000',
        'state': 'NSW'
    }
    
    result = waterfall.process_lead(test_lead)
    print(f"Processing result: {json.dumps(result, indent=2)}")


if __name__ == '__main__':
    main()