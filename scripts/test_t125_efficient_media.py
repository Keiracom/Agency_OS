#!/usr/bin/env python3
"""
CEO Directive #039 — T1.25 Validation Test
Purpose: Confirm fuzzy match now clears 70% threshold for Efficient Media case

Test case from #038 mini validation:
- ABN: 77603054815 | EFFICIENT MEDIA PTY LTD | NSW  
- GMB: Efficient Media | Digital Marketing Agency
- Previous score: 55% (FAIL)
- Expected after T1.25: >70% (PASS)
"""

import asyncio
import sys
from fuzzywuzzy import fuzz

# Test data from #038 failure
ABN_LEGAL_NAME = "EFFICIENT MEDIA PTY LTD"
GMB_NAME = "Efficient Media"
THRESHOLD = 70

def clean_company_name(name: str) -> str:
    """Clean company name for better fuzzy matching (from T1.25)."""
    import re
    if not name:
        return ""
    suffixes_pattern = r'\s+(PTY\.?\s*LTD\.?|LIMITED|LTD\.?|PROPRIETARY|INC\.?|INCORPORATED|HOLDINGS?|GROUP|AUSTRALIA|AUST\.?|AU)\s*$'
    cleaned = re.sub(suffixes_pattern, '', name.upper(), flags=re.IGNORECASE)
    return cleaned.strip().title()


def test_match():
    """Test fuzzy matching with and without T1.25 cleaning."""
    
    print("=" * 60)
    print("CEO Directive #039 — T1.25 Validation Test")
    print("=" * 60)
    print()
    
    # Test 1: Original (no T1.25)
    score_original = fuzz.ratio(ABN_LEGAL_NAME.lower(), GMB_NAME.lower())
    token_original = fuzz.token_set_ratio(ABN_LEGAL_NAME.lower(), GMB_NAME.lower())
    best_original = max(score_original, token_original)
    
    print(f"[T1 only] ABN legal_name: '{ABN_LEGAL_NAME}'")
    print(f"[T1 only] GMB name:       '{GMB_NAME}'")
    print(f"[T1 only] fuzz.ratio:      {score_original}%")
    print(f"[T1 only] token_set_ratio: {token_original}%")
    print(f"[T1 only] Best score:      {best_original}%")
    print(f"[T1 only] Threshold:       {THRESHOLD}%")
    print(f"[T1 only] Result:          {'✓ PASS' if best_original >= THRESHOLD else '✗ FAIL'}")
    print()
    
    # Test 2: With T1.25 cleaning (simulates ASIC registered_name)
    cleaned_name = clean_company_name(ABN_LEGAL_NAME)
    
    score_cleaned = fuzz.ratio(cleaned_name.lower(), GMB_NAME.lower())
    token_cleaned = fuzz.token_set_ratio(cleaned_name.lower(), GMB_NAME.lower())
    best_cleaned = max(score_cleaned, token_cleaned)
    
    print(f"[T1.25]   ASIC cleaned:    '{cleaned_name}'")
    print(f"[T1.25]   GMB name:        '{GMB_NAME}'")
    print(f"[T1.25]   fuzz.ratio:      {score_cleaned}%")
    print(f"[T1.25]   token_set_ratio: {token_cleaned}%")
    print(f"[T1.25]   Best score:      {best_cleaned}%")
    print(f"[T1.25]   Threshold:       {THRESHOLD}%")
    print(f"[T1.25]   Result:          {'✓ PASS' if best_cleaned >= THRESHOLD else '✗ FAIL'}")
    print()
    
    # Summary
    print("=" * 60)
    improvement = best_cleaned - best_original
    print(f"Improvement: +{improvement}% ({best_original}% → {best_cleaned}%)")
    
    if best_cleaned >= THRESHOLD and best_original < THRESHOLD:
        print("✓ T1.25 FIXES the fuzzy match failure")
        return 0
    elif best_cleaned >= THRESHOLD:
        print("✓ Match passes with T1.25")
        return 0
    else:
        print("✗ T1.25 does NOT fix the failure — investigate further")
        return 1


if __name__ == "__main__":
    sys.exit(test_match())
