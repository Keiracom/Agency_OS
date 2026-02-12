#!/usr/bin/env python3
"""
Test suite for siege_waterfall.py
CEO Directive #014 - ABN→GMB Waterfall Name Resolution
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from siege_waterfall import (
    ABNRecord, GMBSearchResult, WaterfallAttempt,
    GenericNameFilter, NameProcessor, Tier2GMBEnricher, SiegeWaterfall
)


class TestGenericNameFilter:
    """Test the generic name filtering logic"""
    
    def test_generic_filter_with_asic_names_should_not_filter(self):
        """If ASIC business names exist, should not filter even with generic legal name"""
        business_names = ["Actual Business Services", "Real Company"]
        legal_name = "Generic Holdings Pty Ltd"
        
        result = GenericNameFilter.is_generic(business_names, legal_name)
        assert result is False
    
    def test_generic_filter_without_asic_names_should_filter(self):
        """If no ASIC names and generic legal name, should filter"""
        business_names = []
        legal_name = "Investment Holdings Pty Ltd"
        
        result = GenericNameFilter.is_generic(business_names, legal_name)
        assert result is True
    
    def test_generic_filter_patterns(self):
        """Test all generic patterns"""
        business_names = []
        
        generic_names = [
            "ABC Holdings Pty Ltd",
            "XYZ Enterprises Ltd", 
            "Investment Group Pty Ltd",
            "Property Trust Limited",
            "Management Services Pty Ltd",
            "Consulting Properties Ltd"
        ]
        
        for name in generic_names:
            result = GenericNameFilter.is_generic(business_names, name)
            assert result is True, f"Should filter generic name: {name}"
    
    def test_non_generic_names_should_not_filter(self):
        """Non-generic names should not be filtered"""
        business_names = []
        
        non_generic_names = [
            "Smith Construction Pty Ltd",
            "Melbourne Coffee Co",
            "Tech Solutions Australia",
            "Green Energy Systems"
        ]
        
        for name in non_generic_names:
            result = GenericNameFilter.is_generic(business_names, name)
            assert result is False, f"Should not filter non-generic name: {name}"


class TestNameProcessor:
    """Test name processing utilities"""
    
    def test_strip_legal_suffixes(self):
        """Test legal suffix stripping"""
        test_cases = [
            ("Example Business Pty Ltd", "Example Business"),
            ("Test Company Ltd", "Test Company"),
            ("Service Corp Pty", "Service Corp"),
            ("Holdings Limited", "Holdings"),
            ("ABC Company Pty. Ltd.", "ABC Company"),
            ("No Suffix Company", "No Suffix Company"),
            ("", ""),
            (None, None)
        ]
        
        for input_name, expected in test_cases:
            if input_name is None:
                result = NameProcessor.strip_legal_suffixes(input_name)
                assert result is None
            else:
                result = NameProcessor.strip_legal_suffixes(input_name)
                assert result == expected, f"Input: {input_name}, Expected: {expected}, Got: {result}"
    
    def test_create_location_search(self):
        """Test location-pinned search creation"""
        name = "Test Business"
        postcode = "2000"
        state = "NSW"
        
        result = NameProcessor.create_location_search(name, postcode, state)
        assert result == "Test Business 2000 NSW Australia"
    
    def test_create_location_search_missing_data(self):
        """Test location search with missing data"""
        name = "Test Business"
        
        # Missing postcode
        result = NameProcessor.create_location_search(name, None, "NSW")
        assert result == name
        
        # Missing state
        result = NameProcessor.create_location_search(name, "2000", None)
        assert result == name
        
        # Missing both
        result = NameProcessor.create_location_search(name, None, None)
        assert result == name


class TestTier2GMBEnricher:
    """Test the main GMB enrichment logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_supabase = Mock()
        self.mock_gmb = Mock()
        self.enricher = Tier2GMBEnricher(
            supabase_client=self.mock_supabase,
            gmb_client=self.mock_gmb
        )
    
    def test_build_search_waterfall_full_data(self):
        """Test waterfall building with complete ABN data"""
        abn_record = ABNRecord(
            abn="12345678901",
            business_name="Example Business Pty Ltd",
            business_names=["Example Services", "Example Corp"],
            trading_name="ExampleTrade",
            postcode="2000",
            state="NSW"
        )
        
        waterfall = self.enricher._build_search_waterfall(abn_record)
        
        # Should have: 2 ASIC names, trading name, stripped legal name, location search
        assert len(waterfall) == 5
        
        steps, names = zip(*waterfall)
        
        # Check step identifiers
        assert "a1" in steps  # First ASIC name
        assert "a2" in steps  # Second ASIC name
        assert "b" in steps   # Trading name
        assert "c" in steps   # Stripped legal name
        assert "d" in steps   # Location search
        
        # Check names
        assert "Example Services" in names
        assert "Example Corp" in names
        assert "ExampleTrade" in names
        assert "Example Business" in names
        assert "Example Business 2000 NSW Australia" in names
    
    def test_build_search_waterfall_minimal_data(self):
        """Test waterfall building with minimal ABN data"""
        abn_record = ABNRecord(
            abn="12345678901",
            business_name="Simple Business Pty Ltd",
            business_names=[],
            trading_name=None,
            postcode=None,
            state=None
        )
        
        waterfall = self.enricher._build_search_waterfall(abn_record)
        
        # Should only have stripped legal name
        assert len(waterfall) == 1
        assert waterfall[0] == ("c", "Simple Business")
    
    def test_process_abn_record_generic_filter(self):
        """Test that generic names are filtered out"""
        abn_record = ABNRecord(
            abn="12345678901",
            business_name="Generic Holdings Pty Ltd",
            business_names=[],  # No ASIC names
            trading_name=None,
            postcode="2000",
            state="NSW"
        )
        
        success, result, status = self.enricher.process_abn_record(abn_record)
        
        assert success is False
        assert result is None
        assert status == "tier2_skipped_generic_name"
    
    def test_calculate_match_score(self):
        """Test match score calculation"""
        test_cases = [
            ("Example Business", "Example Business Services", 1.0),  # Perfect subset match
            ("Tech Corp", "Tech Corporation Limited", 0.5),           # Partial match
            ("ABC Company", "XYZ Services", 0.0),                    # No match
            ("", "Something", 0.0),                                  # Empty search
            ("Something", "", 0.0)                                   # Empty found
        ]
        
        for search_name, found_name, expected_score in test_cases:
            score = self.enricher._calculate_match_score(search_name, found_name)
            assert score == expected_score, f"Search: {search_name}, Found: {found_name}, Expected: {expected_score}, Got: {score}"


class TestSiegeWaterfall:
    """Test the main orchestrator"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.waterfall = SiegeWaterfall()  # No Supabase for testing
    
    def test_process_lead_structure(self):
        """Test that lead processing returns expected structure"""
        lead_data = {
            'abn': '12345678901',
            'business_name': 'Test Business Pty Ltd',
            'business_names': ['Test Services'],
            'trading_name': 'TestCorp',
            'postcode': '2000',
            'state': 'NSW'
        }
        
        result = self.waterfall.process_lead(lead_data)
        
        # Should contain original data plus tier2 results
        assert 'tier2_status' in result
        assert 'tier2_success' in result
        assert result['abn'] == lead_data['abn']
        assert result['business_name'] == lead_data['business_name']
    
    def test_process_lead_generic_filter(self):
        """Test lead processing with generic name"""
        lead_data = {
            'abn': '12345678901',
            'business_name': 'Investment Holdings Pty Ltd',
            'business_names': [],  # No ASIC names
            'trading_name': None,
            'postcode': '2000',
            'state': 'NSW'
        }
        
        result = self.waterfall.process_lead(lead_data)
        
        assert result['tier2_status'] == 'tier2_skipped_generic_name'
        assert result['tier2_success'] is False


# Integration test data
TEST_LEADS = [
    {
        'name': 'Full Data Lead',
        'data': {
            'abn': '11234567890',
            'business_name': 'Melbourne Coffee Roasters Pty Ltd',
            'business_names': ['Melbourne Coffee Co', 'Coffee Roasters Melbourne'],
            'trading_name': 'MelbCoffee',
            'postcode': '3000',
            'state': 'VIC'
        },
        'expected_steps': 5  # 2 ASIC + trading + stripped + location
    },
    {
        'name': 'Generic Holdings Lead',
        'data': {
            'abn': '22345678901',
            'business_name': 'ABC Holdings Pty Ltd',
            'business_names': [],
            'trading_name': None,
            'postcode': '2000',
            'state': 'NSW'
        },
        'expected_status': 'tier2_skipped_generic_name'
    },
    {
        'name': 'Minimal Data Lead',
        'data': {
            'abn': '33456789012',
            'business_name': 'Simple Trading Pty Ltd',
            'business_names': [],
            'trading_name': None,
            'postcode': None,
            'state': None
        },
        'expected_steps': 1  # Only stripped legal name
    }
]


@pytest.mark.parametrize("test_lead", TEST_LEADS, ids=[lead['name'] for lead in TEST_LEADS])
def test_integration_scenarios(test_lead):
    """Integration tests for various lead scenarios"""
    waterfall = SiegeWaterfall()
    result = waterfall.process_lead(test_lead['data'])
    
    if 'expected_status' in test_lead:
        assert result['tier2_status'] == test_lead['expected_status']
    
    if 'expected_steps' in test_lead:
        # This would require mocking the enricher to count actual steps
        # For now, just ensure processing completed
        assert 'tier2_status' in result
        assert 'tier2_success' in result


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])