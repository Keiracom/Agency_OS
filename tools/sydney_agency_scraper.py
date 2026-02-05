#!/usr/bin/env python3
"""
Sydney Digital Marketing Agency Scraper - v2 (CSS Selector + Curated Data)
===========================================================================
Scrapes digital marketing and SEO agencies in Sydney from multiple sources.

APPROACH:
1. Primary: Curated seed data from accessible list sites (no Cloudflare)
2. Fallback: Web search enrichment for contact details
3. Validation: Strict data integrity checks

Sources (Cloudflare-Free):
- OneLittleWeb rankings (web_fetch accessible)
- Prosperity Media lists (web_fetch accessible)
- Web search enrichment (Brave API)

NOTE: Direct scraping of Clutch/YellowPages/GoodFirms blocked by Cloudflare.
      This scraper uses curated data extraction instead.

Usage:
    python tools/sydney_agency_scraper.py scrape --source curated
    python tools/sydney_agency_scraper.py scrape --source curated --output agencies.csv
    python tools/sydney_agency_scraper.py scrape --source curated --max-pages 1
"""

import os
import sys
import json
import csv
import asyncio
import re
import random
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, quote_plus, urlparse
import hashlib

# Force unbuffered output
import functools
print = functools.partial(print, flush=True)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================
# Configuration
# ============================================

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "scraped_agencies"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting configuration
MIN_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 2.0

# Max results
MAX_RESULTS_PER_SOURCE = 100

# Junk patterns to filter out (UI elements, not agency names)
JUNK_PATTERNS = [
    r'^articles?$',
    r'^write a review$',
    r'^list business$',
    r'^more info$',
    r'^less info$',
    r'^sponsored$',
    r'^advertisement$',
    r'^\d+\s*-\s*\d+$',  # Employee counts like "2 - 9"
    r'^\d+\s*reviews?$',
    r'^top .+ agencies$',
    r'^filter',
    r'^sort',
    r'^page \d+',
    r'^showing',
    r'^results',
    r'^search',
    r'^login',
    r'^sign in',
    r'^contact us$',
    r'^get quote$',
    r'^view website$',
]


# ============================================
# Data Models
# ============================================

@dataclass
class Agency:
    """Represents a single agency record."""
    name: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    services: List[str] = field(default_factory=list)
    google_rating: Optional[float] = None
    google_reviews_count: Optional[int] = None
    source: str = ""
    source_url: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary with services as comma-separated string."""
        d = asdict(self)
        d['services'] = ', '.join(self.services) if self.services else ''
        return d
    
    @property
    def unique_id(self) -> str:
        """Generate unique ID based on name and website."""
        content = f"{self.name.lower().strip()}:{(self.website or '').lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def is_valid(self) -> bool:
        """Check if this is a valid agency (not junk data)."""
        if not self.name or len(self.name) < 3:
            return False
        
        name_lower = self.name.lower().strip()
        
        # Check against junk patterns
        for pattern in JUNK_PATTERNS:
            if re.match(pattern, name_lower, re.IGNORECASE):
                return False
        
        # Must have either website or phone
        if not self.website and not self.phone:
            return False
        
        # Validate website if present
        if self.website:
            parsed = urlparse(self.website)
            if not parsed.netloc:
                return False
        
        return True


# ============================================
# Helper Functions
# ============================================

def clean_text(text: Optional[str]) -> Optional[str]:
    """Clean and normalize text."""
    if not text:
        return None
    text = re.sub(r'\s+', ' ', text.strip())
    return text if text else None


def extract_phone(text: str) -> Optional[str]:
    """Extract Australian phone number from text."""
    patterns = [
        r'(?:\+61|0)[2-478](?:[ -]?\d){8}',
        r'(?:\+61|0)4\d{2}[ -]?\d{3}[ -]?\d{3}',
        r'\(0[2-9]\)[ -]?\d{4}[ -]?\d{4}',
        r'1[38]00[ -]?\d{3}[ -]?\d{3}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def normalize_website(url: str) -> str:
    """Normalize website URL."""
    if not url:
        return url
    url = url.strip()
    if not url.startswith('http'):
        url = 'https://' + url
    return url


# ============================================
# Curated Data Scraper (Cloudflare-Free Sources)
# ============================================

class CuratedDataScraper:
    """
    Scrapes agency data from accessible curated list sites.
    These sites don't have Cloudflare protection.
    """
    
    source_name = "curated"
    
    # Curated sources that are Cloudflare-free
    CURATED_SOURCES = [
        {
            "url": "https://onelittleweb.com/top-agencies/seo-agencies-in-sydney/",
            "name": "OneLittleWeb",
        },
        {
            "url": "https://prosperitymedia.com.au/the-6-best-seo-agencies-in-sydney-2025/",
            "name": "ProsperityMedia",
        },
    ]
    
    def __init__(self):
        self.agencies: List[Agency] = []
        self.bytes_transferred = 0
    
    async def scrape(self, max_pages: int = 2) -> List[Agency]:
        """Scrape agencies from curated sources."""
        print(f"\n{'='*60}")
        print(f"📋 CURATED DATA SCRAPER (Cloudflare-Free)")
        print(f"{'='*60}")
        
        sources_to_scrape = self.CURATED_SOURCES[:max_pages]
        
        for source in sources_to_scrape:
            await self._scrape_source(source)
            await asyncio.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))
        
        # Deduplicate
        self._deduplicate()
        
        # Filter invalid entries
        valid_agencies = [a for a in self.agencies if a.is_valid()]
        
        print(f"\n✅ Curated Data: Found {len(valid_agencies)} valid agencies")
        print(f"   (Filtered out {len(self.agencies) - len(valid_agencies)} invalid entries)")
        
        self.agencies = valid_agencies
        return self.agencies
    
    async def _scrape_source(self, source: dict):
        """Scrape a single curated source."""
        url = source["url"]
        name = source["name"]
        
        print(f"\n  📥 Fetching: {name}")
        print(f"     URL: {url[:60]}...")
        
        # Use subprocess to call web_fetch equivalent (or direct HTTP)
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.bytes_transferred += len(content.encode('utf-8'))
                        
                        if "onelittleweb" in url.lower():
                            self._parse_onelittleweb(content, url)
                        elif "prosperitymedia" in url.lower():
                            self._parse_prosperitymedia(content, url)
                        else:
                            self._parse_generic(content, url)
                    else:
                        print(f"     ⚠️ HTTP {response.status}")
        except Exception as e:
            print(f"     ❌ Error: {str(e)[:50]}")
    
    def _parse_onelittleweb(self, content: str, source_url: str):
        """
        Parse OneLittleWeb ranking table (HTML format).
        Structure: <td>rank</td><td>name</td><td><a href="url">domain</a></td>
        """
        print("     Parsing OneLittleWeb format (HTML)...")
        
        # Pattern for HTML table rows with agency data
        pattern = r'<td[^>]*>(\d+)</td>\s*<td[^>]*>([^<]+)</td>\s*<td[^>]*><a[^>]+href="([^"]+)"'
        
        matches = re.findall(pattern, content, re.DOTALL)
        print(f"     Found {len(matches)} agency entries in table")
        
        for rank, name, website in matches:
            name = clean_text(name)
            website = normalize_website(website)
            
            if name and website and len(name) > 2:
                agency = Agency(
                    name=name,
                    website=website,
                    address="Sydney, NSW, Australia",
                    services=["SEO"],
                    source="onelittleweb",
                    source_url=source_url,
                )
                self.agencies.append(agency)
    
    def _parse_prosperitymedia(self, content: str, source_url: str):
        """
        Parse Prosperity Media article (HTML format).
        Structure: <a href="external_url">Agency Name</a>
        """
        print("     Parsing ProsperityMedia format (HTML)...")
        
        # Pattern for external links (not prosperitymedia.com.au)
        pattern = r'<a[^>]+href="(https?://(?!prosperitymedia)[^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, content)
        
        skip_words = ['read', 'click', 'learn', 'contact', 'download', 'subscribe', 
                      'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
                      'share', 'comment', 'reply']
        
        agencies_found = 0
        seen_urls = set()
        
        for url, name in matches:
            # Clean URL (remove tracking params)
            url = url.split('?')[0].rstrip('/')
            
            if url in seen_urls:
                continue
            seen_urls.add(url)
            
            name = clean_text(name)
            
            # Skip non-agency links
            if any(skip in name.lower() for skip in skip_words):
                continue
            
            website = normalize_website(url)
            
            if name and website and len(name) > 3 and len(name) < 50:
                agency = Agency(
                    name=name,
                    website=website,
                    address="Sydney, NSW, Australia",
                    services=["SEO"],
                    source="prosperitymedia",
                    source_url=source_url,
                )
                self.agencies.append(agency)
                agencies_found += 1
        
        print(f"     Found {agencies_found} agencies")
    
    def _parse_generic(self, content: str, source_url: str):
        """Generic parser for unknown formats."""
        print("     Parsing generic format...")
        
        # Look for agency-like patterns
        pattern = r'\[([A-Za-z][A-Za-z0-9\s&\'\.\-]+?)\]\((https?://[^)]+)\)'
        matches = re.findall(pattern, content)
        
        for name, url in matches:
            name = clean_text(name)
            website = normalize_website(url)
            
            if name and website and len(name) > 3:
                agency = Agency(
                    name=name,
                    website=website,
                    source="curated",
                    source_url=source_url,
                )
                self.agencies.append(agency)
    
    def _deduplicate(self):
        """Remove duplicate agencies."""
        seen = {}
        unique = []
        
        for agency in self.agencies:
            uid = agency.unique_id
            if uid not in seen:
                seen[uid] = agency
                unique.append(agency)
            else:
                # Merge data
                existing = seen[uid]
                if not existing.phone and agency.phone:
                    existing.phone = agency.phone
                if not existing.email and agency.email:
                    existing.email = agency.email
                if agency.services:
                    existing.services = list(set(existing.services + agency.services))
        
        self.agencies = unique


# ============================================
# Legacy Scrapers (Cloudflare-Blocked - Deprecated)
# ============================================

class YellowPagesScraper:
    """DEPRECATED: Yellow Pages is now Cloudflare-protected."""
    source_name = "yellowpages"
    
    async def scrape(self, max_pages: int = 1) -> List[Agency]:
        print(f"\n⚠️  YELLOWPAGES SCRAPER: Cloudflare-blocked")
        print(f"   Use 'curated' source instead")
        return []


class ClutchScraper:
    """DEPRECATED: Clutch.co is now Cloudflare-protected."""
    source_name = "clutch"
    
    async def scrape(self, max_pages: int = 1) -> List[Agency]:
        print(f"\n⚠️  CLUTCH SCRAPER: Cloudflare-blocked")
        print(f"   Use 'curated' source instead")
        return []


class GoodFirmsScraper:
    """DEPRECATED: GoodFirms is now Cloudflare-protected."""
    source_name = "goodfirms"
    
    async def scrape(self, max_pages: int = 1) -> List[Agency]:
        print(f"\n⚠️  GOODFIRMS SCRAPER: Cloudflare-blocked")
        print(f"   Use 'curated' source instead")
        return []


# ============================================
# Main Orchestrator
# ============================================

class SydneyAgencyScraper:
    """
    Main orchestrator for scraping Sydney digital agencies.
    """
    
    SCRAPERS = {
        "curated": CuratedDataScraper,
        "yellowpages": YellowPagesScraper,
        "clutch": ClutchScraper,
        "goodfirms": GoodFirmsScraper,
    }
    
    def __init__(self):
        self.all_agencies: List[Agency] = []
        self.total_bytes = 0
    
    async def scrape(
        self,
        sources: List[str] = None,
        max_pages: int = 2,
    ) -> List[Agency]:
        """
        Scrape agencies from specified sources.
        """
        if sources is None or "all" in sources:
            sources = ["curated"]  # Default to curated (only working source)
        
        print(f"\n{'='*60}")
        print(f"🚀 SYDNEY AGENCY SCRAPER v2.0")
        print(f"   Sources: {', '.join(sources)}")
        print(f"   Max pages per source: {max_pages}")
        print(f"{'='*60}")
        
        for source in sources:
            if source not in self.SCRAPERS:
                print(f"⚠️ Unknown source: {source}")
                continue
            
            scraper_class = self.SCRAPERS[source]
            scraper = scraper_class()
            
            try:
                agencies = await scraper.scrape(max_pages=max_pages)
                self.all_agencies.extend(agencies)
                
                # Track bytes if available
                if hasattr(scraper, 'bytes_transferred'):
                    self.total_bytes += scraper.bytes_transferred
                    
            except Exception as e:
                print(f"❌ Error scraping {source}: {e}")
        
        # Final deduplication
        self._deduplicate()
        
        # Final validation
        valid = [a for a in self.all_agencies if a.is_valid()]
        
        print(f"\n{'='*60}")
        print(f"✅ SCRAPING COMPLETE")
        print(f"   Total valid agencies: {len(valid)}")
        print(f"   Data transferred: {self.total_bytes / 1024:.1f} KB")
        print(f"{'='*60}")
        
        self.all_agencies = valid
        return self.all_agencies
    
    def _deduplicate(self):
        """Remove duplicate agencies across sources."""
        seen = {}
        unique = []
        
        for agency in self.all_agencies:
            uid = agency.unique_id
            if uid not in seen:
                seen[uid] = agency
                unique.append(agency)
        
        self.all_agencies = unique
    
    def save_csv(self, filepath: str = None) -> str:
        """Save results to CSV file."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = OUTPUT_DIR / f"sydney_agencies_{timestamp}.csv"
        else:
            filepath = Path(filepath)
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        fieldnames = ['name', 'website', 'phone', 'email', 'address', 'services', 
                      'google_rating', 'google_reviews_count', 'source', 'source_url', 'scraped_at']
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for agency in self.all_agencies:
                writer.writerow(agency.to_dict())
        
        print(f"📄 CSV saved: {filepath}")
        return str(filepath)
    
    def save_json(self, filepath: str = None) -> str:
        """Save results to JSON file."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = OUTPUT_DIR / f"sydney_agencies_{timestamp}.json"
        else:
            filepath = Path(filepath)
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "total_agencies": len(self.all_agencies),
            "sources": list(set(a.source for a in self.all_agencies)),
            "data_quality": {
                "total_records": len(self.all_agencies),
                "with_website": sum(1 for a in self.all_agencies if a.website),
                "with_phone": sum(1 for a in self.all_agencies if a.phone),
                "with_email": sum(1 for a in self.all_agencies if a.email),
            },
            "agencies": [asdict(a) for a in self.all_agencies],
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"📄 JSON saved: {filepath}")
        return str(filepath)
    
    def print_data_quality_report(self):
        """Print a data quality report."""
        total = len(self.all_agencies)
        if total == 0:
            print("\n⚠️  No agencies scraped")
            return
        
        with_website = sum(1 for a in self.all_agencies if a.website)
        with_phone = sum(1 for a in self.all_agencies if a.phone)
        with_email = sum(1 for a in self.all_agencies if a.email)
        
        print(f"\n📊 DATA QUALITY REPORT")
        print(f"   Total Records: {total}")
        print(f"   With Website:  {with_website} ({100*with_website/total:.0f}%)")
        print(f"   With Phone:    {with_phone} ({100*with_phone/total:.0f}%)")
        print(f"   With Email:    {with_email} ({100*with_email/total:.0f}%)")
        
        # Sample records
        print(f"\n   Sample Records (first 5):")
        for agency in self.all_agencies[:5]:
            print(f"   • {agency.name}")
            print(f"     Website: {agency.website or 'N/A'}")
            print(f"     Phone: {agency.phone or 'N/A'}")


# ============================================
# CLI Interface
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sydney Digital Marketing Agency Scraper v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Scrape curated sources (recommended - Cloudflare-free)
    python tools/sydney_agency_scraper.py scrape --source curated
    
    # Scrape with custom output
    python tools/sydney_agency_scraper.py scrape --source curated --output my_agencies.csv
    
    # List available sources
    python tools/sydney_agency_scraper.py sources
    
NOTE: Direct scraping of Clutch/YellowPages/GoodFirms is blocked by Cloudflare.
      Use --source curated for reliable data extraction.
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape agencies from sources")
    scrape_parser.add_argument(
        "--source", "-s",
        action="append",
        dest="sources",
        help="Source to scrape (curated recommended; yellowpages/clutch/goodfirms are Cloudflare-blocked)"
    )
    scrape_parser.add_argument(
        "--max-pages", "-p",
        type=int,
        default=2,
        help="Maximum pages/sources to scrape (default: 2)"
    )
    scrape_parser.add_argument(
        "--output", "-o",
        help="Output file path (auto-detects CSV/JSON from extension)"
    )
    scrape_parser.add_argument(
        "--json-only",
        action="store_true",
        help="Output JSON only"
    )
    scrape_parser.add_argument(
        "--csv-only",
        action="store_true",
        help="Output CSV only"
    )
    
    # Sources command
    sources_parser = subparsers.add_parser("sources", help="List available sources")
    
    args = parser.parse_args()
    
    if args.command == "scrape":
        scraper = SydneyAgencyScraper()
        
        # Handle sources
        sources = args.sources or ["curated"]
        
        # Run async scraper
        agencies = asyncio.run(scraper.scrape(sources=sources, max_pages=args.max_pages))
        
        # Print quality report
        scraper.print_data_quality_report()
        
        if not agencies:
            print("\n⚠️ No agencies found.")
            return
        
        # Save outputs
        if args.output:
            if args.output.endswith('.json'):
                scraper.save_json(args.output)
            elif args.output.endswith('.csv'):
                scraper.save_csv(args.output)
            else:
                scraper.save_csv(args.output + '.csv')
                scraper.save_json(args.output + '.json')
        else:
            if not args.json_only:
                scraper.save_csv()
            if not args.csv_only:
                scraper.save_json()
    
    elif args.command == "sources":
        print("\n📋 Available Sources:")
        print("=" * 60)
        print(f"  ✅ curated        - Cloudflare-free curated lists (RECOMMENDED)")
        print(f"  ⚠️  yellowpages    - Cloudflare-blocked (deprecated)")
        print(f"  ⚠️  clutch         - Cloudflare-blocked (deprecated)")
        print(f"  ⚠️  goodfirms      - Cloudflare-blocked (deprecated)")
        print("\nUse '--source curated' for reliable data extraction.")


if __name__ == "__main__":
    main()
