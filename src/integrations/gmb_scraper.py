# DEPRECATED — Replaced by Bright Data Google Maps SERP (CEO Directive #031, Feb 2026)
# See skills/enrichment/brightdata-gmb/

"""
DIY Google My Business Scraper (DEPRECATED)

This module is deprecated as of CEO Directive #031.
Use skills/enrichment/brightdata-gmb/ instead.

Cost comparison:
- DIY scraper: $0.006/lead
- Bright Data: $0.0015/request (75% cost reduction)

The tools/ directory (autonomous_browser.py, proxy_manager.py) is no longer needed.
"""

import warnings

warnings.warn(
    "gmb_scraper.py is deprecated. Use skills/enrichment/brightdata-gmb/ instead. "
    "See CEO Directive #031 for details.",
    DeprecationWarning,
    stacklevel=2
)


def search_google_maps(*args, **kwargs):
    """
    Deprecated GMB search function.
    
    Use skills/enrichment/brightdata-gmb/run.py:gmb_search() instead.
    """
    raise DeprecationWarning(
        "gmb_scraper.search_google_maps() is deprecated. "
        "Use skills/enrichment/brightdata-gmb/run.py:gmb_search() instead."
    )


class GMBScraper:
    """
    Deprecated GMB scraper class.
    
    Use skills/enrichment/brightdata-gmb/ instead.
    """
    
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "GMBScraper class is deprecated. Use Bright Data GMB skill instead.",
            DeprecationWarning,
            stacklevel=2
        )
    
    def search(self, *args, **kwargs):
        raise DeprecationWarning(
            "GMBScraper.search() is deprecated. "
            "Use skills/enrichment/brightdata-gmb/ instead."
        )