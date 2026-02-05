#!/usr/bin/env python3
"""
Autonomous Browser Tool (Stealth Edition)
==========================================
Uses Playwright for intelligent web navigation and extraction.
No more API quotas. No more JavaScript failures. No more IP bans.

STEALTH FEATURES:
- Proxy rotation (PROXY_URL or PROXY_LIST env vars)
- User-Agent randomization (fake-useragent)
- Fingerprint spoofing (viewport, timezone, locale)
- Burner Protocol: auto-retry with new identity on 403/429

Usage:
    python tools/autonomous_browser.py fetch <url> [--proxy <url>]
    python tools/autonomous_browser.py fetch <url> --stealth
    python tools/autonomous_browser.py test-stealth
"""

import os
import sys
import json
import asyncio
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False


# ============================================
# Configuration
# ============================================

CACHE_DIR = Path(__file__).parent.parent / ".cache" / "browser"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Proxy configuration
PROXY_URL = os.getenv("PROXY_URL", "")  # Single proxy
PROXY_LIST = os.getenv("PROXY_LIST", "")  # Comma-separated list

# Auto-load from proxy_manager if available
def _auto_load_proxies():
    global PROXY_LIST
    if not PROXY_LIST:
        try:
            from tools.proxy_manager import get_proxy_list
            proxies = get_proxy_list()
            if proxies:
                # Load a rotating subset (100 proxies max for performance)
                import random
                subset = random.sample(proxies, min(100, len(proxies)))
                PROXY_LIST = ",".join(subset)
        except ImportError:
            pass

_auto_load_proxies()

DEFAULT_TIMEOUT = 30000  # 30 seconds
MAX_RETRIES = 3
BURNER_RETRY_CODES = [403, 429, 503]  # Status codes that trigger identity rotation


# ============================================
# Stealth Identity System
# ============================================

@dataclass
class StealthIdentity:
    """A complete browser identity for stealth mode."""
    user_agent: str
    viewport: dict
    locale: str
    timezone: str
    proxy: Optional[str]
    platform: str
    
    def __str__(self):
        return f"[{self.platform}] {self.user_agent[:50]}... via {self.proxy or 'direct'}"


class IdentityRotator:
    """
    Manages rotating browser identities for stealth operations.
    Each identity = User-Agent + Viewport + Locale + Timezone + Proxy
    """
    
    # Common viewport sizes (realistic distributions)
    VIEWPORTS = [
        {"width": 1920, "height": 1080},  # Full HD (most common)
        {"width": 1366, "height": 768},   # Laptop
        {"width": 1536, "height": 864},   # Scaled laptop
        {"width": 1440, "height": 900},   # MacBook
        {"width": 2560, "height": 1440},  # QHD
        {"width": 1280, "height": 720},   # HD
    ]
    
    # Timezone/locale pairs (realistic combinations)
    LOCALES = [
        ("en-US", "America/New_York"),
        ("en-US", "America/Los_Angeles"),
        ("en-US", "America/Chicago"),
        ("en-GB", "Europe/London"),
        ("en-AU", "Australia/Sydney"),
        ("de-DE", "Europe/Berlin"),
        ("fr-FR", "Europe/Paris"),
    ]
    
    # Fallback user agents if fake-useragent fails
    FALLBACK_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self):
        self._ua_generator = None
        self._proxies: List[str] = []
        self._used_proxies: set = set()
        self._load_proxies()
    
    def _load_proxies(self):
        """Load proxy list from environment."""
        if PROXY_LIST:
            self._proxies = [p.strip() for p in PROXY_LIST.split(",") if p.strip()]
        elif PROXY_URL:
            self._proxies = [PROXY_URL]
    
    def _get_user_agent(self) -> Tuple[str, str]:
        """Get a random user agent and platform."""
        if HAS_FAKE_UA:
            try:
                if self._ua_generator is None:
                    self._ua_generator = UserAgent(browsers=['chrome', 'firefox', 'safari', 'edge'])
                
                # Get random browser type
                browser_type = random.choice(['chrome', 'firefox', 'safari', 'edge'])
                ua = getattr(self._ua_generator, browser_type)
                
                # Determine platform from UA
                if 'Windows' in ua:
                    platform = 'Windows'
                elif 'Macintosh' in ua:
                    platform = 'macOS'
                elif 'Linux' in ua:
                    platform = 'Linux'
                else:
                    platform = 'Unknown'
                
                return ua, platform
            except Exception:
                pass
        
        # Fallback
        ua = random.choice(self.FALLBACK_UAS)
        platform = 'Windows' if 'Windows' in ua else 'macOS' if 'Mac' in ua else 'Linux'
        return ua, platform
    
    def _get_proxy(self, exclude: set = None) -> Optional[str]:
        """Get a proxy, optionally excluding already-tried ones."""
        if not self._proxies:
            return None
        
        available = [p for p in self._proxies if p not in (exclude or set())]
        if not available:
            # All proxies exhausted, reset
            available = self._proxies
        
        return random.choice(available) if available else None
    
    def generate(self, exclude_proxies: set = None) -> StealthIdentity:
        """Generate a fresh stealth identity."""
        ua, platform = self._get_user_agent()
        viewport = random.choice(self.VIEWPORTS)
        locale, tz = random.choice(self.LOCALES)
        proxy = self._get_proxy(exclude_proxies)
        
        return StealthIdentity(
            user_agent=ua,
            viewport=viewport,
            locale=locale,
            timezone=tz,
            proxy=proxy,
            platform=platform,
        )
    
    @property
    def proxy_count(self) -> int:
        return len(self._proxies)


# Global identity rotator
_rotator = IdentityRotator()


# ============================================
# Cache Layer
# ============================================

def get_cache_key(url: str, task: str = "") -> str:
    """Generate cache key for URL + task."""
    content = f"{url}:{task}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def get_cached(url: str, task: str = "", max_age_hours: int = 24) -> Optional[dict]:
    """Get cached result if fresh enough."""
    key = get_cache_key(url, task)
    cache_file = CACHE_DIR / f"{key}.json"
    
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            cached_at = datetime.fromisoformat(data.get("cached_at", "2000-01-01"))
            age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
            
            if age_hours < max_age_hours:
                return data
        except Exception:
            pass
    return None


def set_cached(url: str, task: str, result: dict) -> None:
    """Cache a result."""
    key = get_cache_key(url, task)
    cache_file = CACHE_DIR / f"{key}.json"
    
    result["cached_at"] = datetime.now(timezone.utc).isoformat()
    result["url"] = url
    result["task"] = task
    
    cache_file.write_text(json.dumps(result, indent=2))


# ============================================
# Stealth Browser Context
# ============================================

async def create_stealth_context(
    playwright,
    identity: StealthIdentity,
) -> Tuple["Browser", "BrowserContext"]:
    """
    Create a browser context with full stealth configuration.
    """
    # Launch options
    launch_opts = {
        "headless": True,
    }
    
    # Add proxy if configured
    if identity.proxy:
        # Parse proxy URL (supports http://user:pass@host:port)
        from urllib.parse import urlparse
        parsed = urlparse(identity.proxy)
        proxy_config = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            proxy_config["username"] = parsed.username
        if parsed.password:
            proxy_config["password"] = parsed.password
        launch_opts["proxy"] = proxy_config
    
    browser = await playwright.chromium.launch(**launch_opts)
    
    # Context options for fingerprint spoofing
    context_opts = {
        "viewport": identity.viewport,
        "user_agent": identity.user_agent,
        "locale": identity.locale,
        "timezone_id": identity.timezone,
        # Additional stealth options
        "java_script_enabled": True,
        "bypass_csp": True,
        "ignore_https_errors": True,
        # Realistic permissions
        "permissions": ["geolocation"],
        "geolocation": {"latitude": 37.7749, "longitude": -122.4194},  # SF
    }
    
    context = await browser.new_context(**context_opts)
    
    # Inject stealth scripts to avoid detection
    await context.add_init_script("""
        // Overwrite navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
        
        // Overwrite chrome runtime
        window.chrome = {
            runtime: {}
        };
        
        // Overwrite permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Add plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5]
        });
        
        // Add languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
    """)
    
    return browser, context


# ============================================
# Burner Protocol (Auto-Retry with New Identity)
# ============================================

async def fetch_with_burner_protocol(
    url: str,
    extract_selector: Optional[str] = None,
    scroll: bool = True,
    screenshot: bool = False,
    stealth: bool = True,
    max_retries: int = MAX_RETRIES,
) -> dict:
    """
    Fetch a URL with automatic identity rotation on blocks.
    
    BURNER PROTOCOL:
    1. Try with current identity
    2. On 403/429/503: close browser, get new identity, retry
    3. Log all identity rotations
    """
    tried_proxies = set()
    last_error = None
    
    for attempt in range(max_retries):
        identity = _rotator.generate(exclude_proxies=tried_proxies)
        
        if identity.proxy:
            tried_proxies.add(identity.proxy)
        
        print(f"[STEALTH] Attempt {attempt + 1}/{max_retries}: {identity}")
        
        result = await _fetch_single_attempt(
            url=url,
            identity=identity,
            extract_selector=extract_selector,
            scroll=scroll,
            screenshot=screenshot,
            stealth=stealth,
        )
        
        if result.get("success"):
            result["identity_rotations"] = attempt
            result["final_identity"] = str(identity)
            return result
        
        # Check if we should rotate identity
        status_code = result.get("status_code", 0)
        error = result.get("error", "")
        
        if status_code in BURNER_RETRY_CODES:
            print(f"[BURNER] Got {status_code}, rotating identity...")
            last_error = f"HTTP {status_code}"
            continue
        elif "blocked" in error.lower() or "captcha" in error.lower():
            print(f"[BURNER] Detected block: {error[:50]}, rotating identity...")
            last_error = error
            continue
        else:
            # Non-retryable error
            return result
    
    return {
        "success": False,
        "url": url,
        "error": f"All {max_retries} identities exhausted. Last error: {last_error}",
        "identity_rotations": max_retries - 1,
    }


async def _fetch_single_attempt(
    url: str,
    identity: StealthIdentity,
    extract_selector: Optional[str] = None,
    scroll: bool = True,
    screenshot: bool = False,
    stealth: bool = True,
) -> dict:
    """Single fetch attempt with given identity."""
    async with async_playwright() as p:
        try:
            if stealth:
                browser, context = await create_stealth_context(p, identity)
            else:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport=identity.viewport,
                    user_agent=identity.user_agent,
                )
            
            page = await context.new_page()
            
            # Navigate with response tracking
            response = await page.goto(url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT)
            
            status_code = response.status if response else 0
            
            # Check for block indicators
            if status_code in BURNER_RETRY_CODES:
                await browser.close()
                return {
                    "success": False,
                    "url": url,
                    "status_code": status_code,
                    "error": f"Received HTTP {status_code}",
                }
            
            # Check page content for block indicators
            page_text = await page.inner_text("body")
            block_indicators = [
                "access denied", "blocked", "captcha", "please verify",
                "rate limit", "too many requests", "forbidden"
            ]
            
            for indicator in block_indicators:
                if indicator in page_text.lower()[:2000]:
                    await browser.close()
                    return {
                        "success": False,
                        "url": url,
                        "status_code": status_code,
                        "error": f"Block indicator detected: '{indicator}'",
                    }
            
            # Scroll to load lazy content
            if scroll:
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await asyncio.sleep(0.3)
                await page.evaluate("window.scrollTo(0, 0)")
                await asyncio.sleep(0.5)
            
            # Extract content
            if extract_selector:
                elements = await page.query_selector_all(extract_selector)
                content = []
                for el in elements:
                    text = await el.inner_text()
                    if text.strip():
                        content.append(text.strip())
                extracted = "\n\n".join(content)
            else:
                extracted = await page.inner_text("body")
            
            # Optional screenshot
            screenshot_path = None
            if screenshot:
                screenshot_path = str(CACHE_DIR / f"screenshot_{get_cache_key(url, '')}.png")
                await page.screenshot(path=screenshot_path, full_page=True)
            
            result = {
                "success": True,
                "url": url,
                "status_code": status_code,
                "title": await page.title(),
                "content": extracted[:50000],
                "content_length": len(extracted),
                "screenshot": screenshot_path,
            }
            
            await browser.close()
            return result
            
        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
            }


# ============================================
# Public API
# ============================================

async def autonomous_fetch(
    url: str,
    task: Optional[str] = None,
    extract_selector: Optional[str] = None,
    use_cache: bool = True,
    cache_hours: int = 24,
    scroll: bool = True,
    screenshot: bool = False,
    stealth: bool = True,
    proxy: Optional[str] = None,
) -> dict:
    """
    Autonomously fetch and extract content from any URL.
    
    Args:
        url: Target URL
        task: Natural language task (for future agent mode)
        extract_selector: CSS selector for extraction
        use_cache: Whether to use cached results
        cache_hours: Cache TTL in hours
        scroll: Whether to scroll for lazy content
        screenshot: Whether to capture screenshot
        stealth: Enable stealth mode (fingerprint spoofing)
        proxy: Override proxy URL
    
    Returns:
        dict with success, content, and metadata
    """
    if not HAS_PLAYWRIGHT:
        return {"success": False, "error": "Playwright not installed"}
    
    # Check cache
    if use_cache:
        cached = get_cached(url, task or "", cache_hours)
        if cached:
            cached["from_cache"] = True
            return cached
    
    # Override proxy if specified
    if proxy:
        global PROXY_URL
        old_proxy = PROXY_URL
        PROXY_URL = proxy
        _rotator._load_proxies()
    
    # Fetch with burner protocol
    result = await fetch_with_burner_protocol(
        url=url,
        extract_selector=extract_selector,
        scroll=scroll,
        screenshot=screenshot,
        stealth=stealth,
    )
    
    # Restore proxy
    if proxy:
        PROXY_URL = old_proxy
        _rotator._load_proxies()
    
    # Cache successful results
    if result.get("success") and use_cache:
        set_cached(url, task or "", result)
    
    result["from_cache"] = False
    return result


def fetch_sync(url: str, **kwargs) -> dict:
    """Synchronous wrapper for autonomous_fetch."""
    return asyncio.run(autonomous_fetch(url, **kwargs))


# ============================================
# CLI Interface
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Browser Tool (Stealth Edition)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch a URL")
    fetch_parser.add_argument("url", help="URL to fetch")
    fetch_parser.add_argument("--extract", help="CSS selector for extraction")
    fetch_parser.add_argument("--no-cache", action="store_true", help="Skip cache")
    fetch_parser.add_argument("--screenshot", action="store_true", help="Capture screenshot")
    fetch_parser.add_argument("--no-stealth", action="store_true", help="Disable stealth mode")
    fetch_parser.add_argument("--proxy", help="Override proxy URL")
    
    # Test stealth command
    test_parser = subparsers.add_parser("test-stealth", help="Test stealth capabilities")
    
    # Identity command
    identity_parser = subparsers.add_parser("identity", help="Generate random identity")
    identity_parser.add_argument("--count", type=int, default=3, help="Number of identities")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show stealth configuration")
    
    args = parser.parse_args()
    
    if args.command == "fetch":
        result = fetch_sync(
            args.url,
            extract_selector=args.extract,
            use_cache=not args.no_cache,
            screenshot=args.screenshot,
            stealth=not args.no_stealth,
            proxy=args.proxy,
        )
        print(json.dumps(result, indent=2, default=str))
        
    elif args.command == "test-stealth":
        print("🕵️ STEALTH MODE TEST")
        print("=" * 50)
        
        # Show configuration
        print(f"\n📋 Configuration:")
        print(f"   Proxies configured: {_rotator.proxy_count}")
        print(f"   fake-useragent: {'✅' if HAS_FAKE_UA else '❌'}")
        print(f"   Playwright: {'✅' if HAS_PLAYWRIGHT else '❌'}")
        
        # Generate identities
        print(f"\n🎭 Sample Identities:")
        for i in range(3):
            identity = _rotator.generate()
            print(f"   {i+1}. {identity}")
        
        # Test fetch
        print(f"\n🌐 Testing fetch with stealth...")
        result = fetch_sync(
            "https://httpbin.org/headers",
            stealth=True,
            use_cache=False,
        )
        
        if result.get("success"):
            print(f"   ✅ SUCCESS")
            print(f"   Status: {result.get('status_code')}")
            print(f"   Identity rotations: {result.get('identity_rotations', 0)}")
            
            # Parse headers from response
            content = result.get("content", "")
            if "User-Agent" in content:
                # Extract user agent from httpbin response
                import re
                ua_match = re.search(r'"User-Agent":\s*"([^"]+)"', content)
                if ua_match:
                    print(f"   Sent UA: {ua_match.group(1)[:60]}...")
        else:
            print(f"   ❌ FAILED: {result.get('error')}")
        
        # Test block detection
        print(f"\n🛡️ Burner Protocol: Active")
        print(f"   Auto-retry on: {BURNER_RETRY_CODES}")
        print(f"   Max retries: {MAX_RETRIES}")
        
    elif args.command == "identity":
        print(f"🎭 Generated Identities:\n")
        for i in range(args.count):
            identity = _rotator.generate()
            print(f"{i+1}. Platform: {identity.platform}")
            print(f"   UA: {identity.user_agent[:70]}...")
            print(f"   Viewport: {identity.viewport['width']}x{identity.viewport['height']}")
            print(f"   Locale: {identity.locale} | TZ: {identity.timezone}")
            print(f"   Proxy: {identity.proxy or 'direct'}")
            print()
    
    elif args.command == "status":
        print("🕵️ STEALTH BROWSER STATUS")
        print("=" * 50)
        print(f"\nDependencies:")
        print(f"  Playwright: {'✅ Installed' if HAS_PLAYWRIGHT else '❌ Missing'}")
        print(f"  fake-useragent: {'✅ Installed' if HAS_FAKE_UA else '❌ Missing'}")
        
        print(f"\nProxy Configuration:")
        print(f"  PROXY_URL: {'✅ Set' if PROXY_URL else '❌ Not set'}")
        print(f"  PROXY_LIST: {_rotator.proxy_count} proxies loaded")
        
        print(f"\nBurner Protocol:")
        print(f"  Retry on status codes: {BURNER_RETRY_CODES}")
        print(f"  Max identity rotations: {MAX_RETRIES}")
        
        print(f"\nCache:")
        print(f"  Directory: {CACHE_DIR}")
        cache_files = list(CACHE_DIR.glob("*.json"))
        print(f"  Cached pages: {len(cache_files)}")


if __name__ == "__main__":
    main()
