#!/usr/bin/env python3
"""
Proxy Manager (Auto-Sync)
=========================
Fetches, parses, and rotates proxies from Webshare API.
Auto-refreshes weekly to handle dead proxies.

Usage:
    python tools/proxy_manager.py sync       # Fetch fresh proxy list
    python tools/proxy_manager.py list       # Show loaded proxies
    python tools/proxy_manager.py test       # Test random proxy
    python tools/proxy_manager.py verify     # Verify IP is hidden
"""

import os
import sys
import json
import random
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict

# ============================================
# Configuration
# ============================================

CONFIG_DIR = Path(__file__).parent.parent / ".config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

PROXY_CONFIG_FILE = CONFIG_DIR / "proxy_config.json"
PROXY_CACHE_FILE = CONFIG_DIR / "proxy_list.json"

# Default Webshare API URL
DEFAULT_PROXY_SOURCE = os.getenv(
    "WEBSHARE_PROXY_URL",
    "https://proxy.webshare.io/api/v2/proxy/list/download/qtlittgilrciykacamwewxkgpmaxnfamwqvjvvkx/-/any/username/backbone/-/?plan_id=12711897"
)

# Auto-refresh interval
REFRESH_INTERVAL_DAYS = 7


# ============================================
# Data Structures
# ============================================

@dataclass
class Proxy:
    """A single proxy configuration."""
    host: str
    port: int
    username: str
    password: str
    protocol: str = "http"
    
    @property
    def url(self) -> str:
        """Get proxy URL for Playwright."""
        return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
    
    @property
    def url_masked(self) -> str:
        """Get proxy URL with masked password."""
        return f"{self.protocol}://{self.username}:****@{self.host}:{self.port}"
    
    def __str__(self):
        return self.url_masked


@dataclass
class ProxyConfig:
    """Proxy manager configuration."""
    source_url: str
    last_sync: Optional[str] = None
    proxy_count: int = 0
    refresh_days: int = REFRESH_INTERVAL_DAYS


# ============================================
# Proxy Manager
# ============================================

class ProxyManager:
    """
    Manages proxy list with auto-sync from Webshare API.
    """
    
    def __init__(self):
        self.config: Optional[ProxyConfig] = None
        self.proxies: List[Proxy] = []
        self._load_config()
        self._load_proxies()
    
    def _load_config(self) -> None:
        """Load configuration from disk."""
        if PROXY_CONFIG_FILE.exists():
            try:
                data = json.loads(PROXY_CONFIG_FILE.read_text())
                self.config = ProxyConfig(**data)
            except Exception:
                pass
        
        if not self.config:
            self.config = ProxyConfig(source_url=DEFAULT_PROXY_SOURCE)
    
    def _save_config(self) -> None:
        """Save configuration to disk."""
        PROXY_CONFIG_FILE.write_text(json.dumps(asdict(self.config), indent=2))
    
    def _load_proxies(self) -> None:
        """Load cached proxy list."""
        if PROXY_CACHE_FILE.exists():
            try:
                data = json.loads(PROXY_CACHE_FILE.read_text())
                self.proxies = [Proxy(**p) for p in data.get("proxies", [])]
            except Exception:
                pass
    
    def _save_proxies(self) -> None:
        """Save proxy list to cache."""
        data = {
            "synced_at": datetime.now(timezone.utc).isoformat(),
            "count": len(self.proxies),
            "proxies": [asdict(p) for p in self.proxies],
        }
        PROXY_CACHE_FILE.write_text(json.dumps(data, indent=2))
    
    def needs_refresh(self) -> bool:
        """Check if proxy list needs refresh."""
        if not self.config.last_sync:
            return True
        
        try:
            last_sync = datetime.fromisoformat(self.config.last_sync)
            age = datetime.now(timezone.utc) - last_sync
            return age.days >= self.config.refresh_days
        except Exception:
            return True
    
    def sync(self, force: bool = False) -> dict:
        """
        Fetch fresh proxy list from source.
        
        Returns:
            dict with sync results
        """
        if not force and not self.needs_refresh():
            return {
                "success": True,
                "action": "skipped",
                "reason": "List is fresh",
                "count": len(self.proxies),
                "last_sync": self.config.last_sync,
            }
        
        try:
            response = requests.get(self.config.source_url, timeout=30)
            response.raise_for_status()
            
            # Parse proxy list (format: host:port:user:pass)
            lines = response.text.strip().split("\n")
            new_proxies = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split(":")
                if len(parts) >= 4:
                    proxy = Proxy(
                        host=parts[0],
                        port=int(parts[1]),
                        username=parts[2],
                        password=parts[3],
                    )
                    new_proxies.append(proxy)
            
            if not new_proxies:
                return {
                    "success": False,
                    "error": "No proxies found in response",
                }
            
            # Update state
            self.proxies = new_proxies
            self.config.last_sync = datetime.now(timezone.utc).isoformat()
            self.config.proxy_count = len(new_proxies)
            
            # Persist
            self._save_config()
            self._save_proxies()
            
            # Update environment for autonomous_browser
            self._export_to_env()
            
            return {
                "success": True,
                "action": "synced",
                "count": len(new_proxies),
                "last_sync": self.config.last_sync,
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
    
    def _export_to_env(self) -> None:
        """Export proxy list to environment variable."""
        if self.proxies:
            urls = [p.url for p in self.proxies]
            os.environ["PROXY_LIST"] = ",".join(urls)
    
    def get_random(self) -> Optional[Proxy]:
        """Get a random proxy."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)
    
    def get_all_urls(self) -> List[str]:
        """Get all proxy URLs."""
        return [p.url for p in self.proxies]
    
    def test_proxy(self, proxy: Optional[Proxy] = None) -> dict:
        """
        Test a proxy connection.
        
        Returns:
            dict with test results including external IP
        """
        proxy = proxy or self.get_random()
        if not proxy:
            return {"success": False, "error": "No proxies available"}
        
        try:
            # Test with ipinfo.io
            response = requests.get(
                "https://ipinfo.io/json",
                proxies={
                    "http": proxy.url,
                    "https": proxy.url,
                },
                timeout=15,
            )
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "success": True,
                "proxy": proxy.url_masked,
                "external_ip": data.get("ip"),
                "location": f"{data.get('city', '?')}, {data.get('region', '?')}, {data.get('country', '?')}",
                "org": data.get("org", "Unknown"),
            }
            
        except Exception as e:
            return {
                "success": False,
                "proxy": proxy.url_masked,
                "error": str(e),
            }
    
    def verify_hidden(self) -> dict:
        """
        Verify that our real IP is hidden.
        
        Compares direct IP vs proxied IP.
        """
        # Get direct IP
        try:
            direct_response = requests.get("https://ipinfo.io/json", timeout=10)
            direct_ip = direct_response.json().get("ip", "unknown")
        except Exception as e:
            return {"success": False, "error": f"Failed to get direct IP: {e}"}
        
        # Get proxied IP
        proxy = self.get_random()
        if not proxy:
            return {"success": False, "error": "No proxies configured"}
        
        proxy_result = self.test_proxy(proxy)
        
        if not proxy_result.get("success"):
            return {
                "success": False,
                "error": f"Proxy test failed: {proxy_result.get('error')}",
                "direct_ip": direct_ip,
            }
        
        proxied_ip = proxy_result.get("external_ip")
        is_hidden = direct_ip != proxied_ip
        
        return {
            "success": True,
            "hidden": is_hidden,
            "direct_ip": direct_ip,
            "proxied_ip": proxied_ip,
            "proxy_location": proxy_result.get("location"),
            "proxy_org": proxy_result.get("org"),
            "proxy_used": proxy.url_masked,
        }


# ============================================
# Global Manager Instance
# ============================================

_manager: Optional[ProxyManager] = None


def get_manager() -> ProxyManager:
    """Get or create the global proxy manager."""
    global _manager
    if _manager is None:
        _manager = ProxyManager()
    return _manager


def auto_sync() -> dict:
    """Auto-sync if needed (call at startup)."""
    manager = get_manager()
    return manager.sync()


def get_proxy_list() -> List[str]:
    """Get list of proxy URLs for autonomous_browser."""
    manager = get_manager()
    
    # Auto-sync if needed
    if manager.needs_refresh() or not manager.proxies:
        manager.sync()
    
    return manager.get_all_urls()


# ============================================
# CLI Interface
# ============================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Proxy Manager (Auto-Sync)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Fetch fresh proxy list")
    sync_parser.add_argument("--force", action="store_true", help="Force refresh")
    
    # List command
    list_parser = subparsers.add_parser("list", help="Show loaded proxies")
    list_parser.add_argument("--full", action="store_true", help="Show full URLs")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test random proxy")
    test_parser.add_argument("--count", type=int, default=1, help="Number of proxies to test")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify IP is hidden")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show configuration")
    
    args = parser.parse_args()
    manager = get_manager()
    
    if args.command == "sync":
        print("🔄 Syncing proxy list...")
        result = manager.sync(force=args.force)
        
        if result.get("success"):
            print(f"✅ {result.get('action', 'done').upper()}")
            print(f"   Proxies: {result.get('count')}")
            print(f"   Last sync: {result.get('last_sync', 'N/A')[:19]}")
        else:
            print(f"❌ FAILED: {result.get('error')}")
    
    elif args.command == "list":
        if not manager.proxies:
            print("No proxies loaded. Run 'sync' first.")
            return
        
        print(f"📋 Loaded Proxies ({len(manager.proxies)}):\n")
        for i, proxy in enumerate(manager.proxies[:20], 1):
            if args.full:
                print(f"  {i:2}. {proxy.url}")
            else:
                print(f"  {i:2}. {proxy}")
        
        if len(manager.proxies) > 20:
            print(f"  ... and {len(manager.proxies) - 20} more")
    
    elif args.command == "test":
        print(f"🧪 Testing {args.count} proxy(ies)...\n")
        
        for i in range(args.count):
            proxy = manager.get_random()
            result = manager.test_proxy(proxy)
            
            if result.get("success"):
                print(f"  ✅ Proxy {i+1}: {result.get('proxy')}")
                print(f"     External IP: {result.get('external_ip')}")
                print(f"     Location: {result.get('location')}")
                print(f"     Org: {result.get('org')}")
            else:
                print(f"  ❌ Proxy {i+1}: {result.get('proxy')}")
                print(f"     Error: {result.get('error')}")
            print()
    
    elif args.command == "verify":
        print("🕵️ Verifying stealth mode...\n")
        result = manager.verify_hidden()
        
        if result.get("success"):
            if result.get("hidden"):
                print("✅ STEALTH MODE ACTIVE")
                print(f"\n   Your real IP:    {result.get('direct_ip')}")
                print(f"   Proxied IP:      {result.get('proxied_ip')}")
                print(f"   Proxy location:  {result.get('proxy_location')}")
                print(f"   Proxy provider:  {result.get('proxy_org')}")
                print(f"\n   ✓ IPs are different - you are hidden!")
            else:
                print("⚠️ WARNING: IP NOT HIDDEN")
                print(f"   Both IPs: {result.get('direct_ip')}")
                print("   Proxy may not be working correctly.")
        else:
            print(f"❌ Verification failed: {result.get('error')}")
    
    elif args.command == "status":
        print("📊 PROXY MANAGER STATUS")
        print("=" * 50)
        
        print(f"\nConfiguration:")
        print(f"  Source URL: {manager.config.source_url[:50]}...")
        print(f"  Refresh interval: {manager.config.refresh_days} days")
        print(f"  Last sync: {manager.config.last_sync or 'Never'}")
        
        print(f"\nProxy Pool:")
        print(f"  Loaded: {len(manager.proxies)} proxies")
        print(f"  Needs refresh: {'Yes' if manager.needs_refresh() else 'No'}")
        
        print(f"\nFiles:")
        print(f"  Config: {PROXY_CONFIG_FILE}")
        print(f"  Cache: {PROXY_CACHE_FILE}")


if __name__ == "__main__":
    main()
