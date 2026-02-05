#!/usr/bin/env python3
"""
Browser-Based Image Enhancer
============================
Uses Playwright + proxy rotation to enhance images via web services.
No API keys needed. Just stealth browser automation.

Usage:
    python tools/browser_image_enhancer.py <image_path> [--output <path>] [--scale 2|4]
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from tools.proxy_manager import get_proxy_list
import random

CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def get_stealth_context(playwright, proxy_url=None):
    """Create a stealth browser context with proxy."""
    
    # Random viewport
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
    ]
    viewport = random.choice(viewports)
    
    # Random user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ]
    user_agent = random.choice(user_agents)
    
    launch_args = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
        ]
    }
    
    if proxy_url:
        launch_args["proxy"] = {"server": proxy_url}
    
    browser = await playwright.chromium.launch(**launch_args)
    
    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
        timezone_id="America/New_York",
    )
    
    # Anti-detection scripts
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        window.chrome = { runtime: {} };
    """)
    
    return browser, context


async def enhance_via_bigjpg(image_path: str, scale: int = 2, proxy_url: str = None) -> dict:
    """
    Enhance image using bigjpg.com (free AI upscaler).
    
    Args:
        image_path: Path to input image
        scale: 2x or 4x upscale
        proxy_url: Optional proxy
    
    Returns:
        dict with success, output_path, etc.
    """
    image_path = Path(image_path).resolve()
    if not image_path.exists():
        return {"success": False, "error": f"Image not found: {image_path}"}
    
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p, proxy_url)
        page = await context.new_page()
        
        try:
            print(f"[bigjpg] Loading page...")
            await page.goto("https://bigjpg.com/", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)
            
            # Upload image
            print(f"[bigjpg] Uploading {image_path.name}...")
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                # Try to find by other means
                file_input = await page.query_selector('#fileupload')
            
            if not file_input:
                await page.screenshot(path=str(CACHE_DIR / "bigjpg_debug.png"))
                return {"success": False, "error": "Could not find file upload input", "screenshot": str(CACHE_DIR / "bigjpg_debug.png")}
            
            await file_input.set_input_files(str(image_path))
            await asyncio.sleep(3)
            
            # Wait for upload to complete and find the enhance button
            print(f"[bigjpg] Waiting for upload...")
            await page.wait_for_selector('.img-list-item, .file-item', timeout=30000)
            
            # Click enlarge/enhance button
            print(f"[bigjpg] Starting enhancement ({scale}x)...")
            
            # Select scale if option available
            scale_selector = f'input[value="{scale}x"], button:has-text("{scale}x")'
            scale_btn = await page.query_selector(scale_selector)
            if scale_btn:
                await scale_btn.click()
                await asyncio.sleep(1)
            
            # Click the start/enlarge button
            start_btn = await page.query_selector('button:has-text("Start"), button:has-text("Enlarge"), .start-btn, #start-btn')
            if start_btn:
                await start_btn.click()
            else:
                # Try clicking the item itself which might trigger processing
                item = await page.query_selector('.img-list-item, .file-item')
                if item:
                    await item.click()
            
            await asyncio.sleep(5)
            
            # Wait for processing (can take 30-120 seconds)
            print(f"[bigjpg] Processing (this may take 1-2 minutes)...")
            
            # Poll for download link
            for i in range(60):  # Up to 5 minutes
                download_link = await page.query_selector('a[download], a:has-text("Download"), .download-btn')
                if download_link:
                    break
                
                # Check for error
                error_el = await page.query_selector('.error-msg, .alert-danger')
                if error_el:
                    error_text = await error_el.inner_text()
                    return {"success": False, "error": f"Enhancement failed: {error_text}"}
                
                await asyncio.sleep(5)
                if i % 6 == 0:
                    print(f"[bigjpg] Still processing... ({i*5}s)")
            
            if not download_link:
                await page.screenshot(path=str(CACHE_DIR / "bigjpg_timeout.png"))
                return {"success": False, "error": "Timed out waiting for enhancement", "screenshot": str(CACHE_DIR / "bigjpg_timeout.png")}
            
            # Download the result
            print(f"[bigjpg] Downloading result...")
            
            # Get the download URL
            href = await download_link.get_attribute("href")
            
            # Use Playwright's download handling
            async with page.expect_download() as download_info:
                await download_link.click()
            download = await download_info.value
            
            # Save to cache
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CACHE_DIR / f"enhanced_{timestamp}_{image_path.stem}.jpg"
            await download.save_as(str(output_path))
            
            print(f"[bigjpg] ✓ Saved to {output_path}")
            
            return {
                "success": True,
                "output_path": str(output_path),
                "scale": scale,
                "service": "bigjpg.com",
            }
            
        except Exception as e:
            await page.screenshot(path=str(CACHE_DIR / "bigjpg_error.png"))
            return {
                "success": False,
                "error": str(e),
                "screenshot": str(CACHE_DIR / "bigjpg_error.png"),
            }
        finally:
            await browser.close()


async def enhance_via_imglarger(image_path: str, scale: int = 2, proxy_url: str = None) -> dict:
    """
    Enhance image using imglarger.com (free AI upscaler).
    Simpler interface, often faster.
    """
    image_path = Path(image_path).resolve()
    if not image_path.exists():
        return {"success": False, "error": f"Image not found: {image_path}"}
    
    async with async_playwright() as p:
        browser, context = await get_stealth_context(p, proxy_url)
        page = await context.new_page()
        
        try:
            print(f"[imglarger] Loading page...")
            await page.goto("https://imglarger.com/", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            
            # Find and use file upload
            print(f"[imglarger] Uploading {image_path.name}...")
            
            # Handle cookie consent if present
            cookie_btn = await page.query_selector('button:has-text("Accept"), button:has-text("OK"), .cookie-accept')
            if cookie_btn:
                await cookie_btn.click()
                await asyncio.sleep(1)
            
            file_input = await page.query_selector('input[type="file"]')
            if not file_input:
                await page.screenshot(path=str(CACHE_DIR / "imglarger_debug.png"))
                return {"success": False, "error": "Could not find file upload", "screenshot": str(CACHE_DIR / "imglarger_debug.png")}
            
            await file_input.set_input_files(str(image_path))
            await asyncio.sleep(5)
            
            # Wait for processing to complete
            print(f"[imglarger] Processing...")
            
            # Look for result/download
            for i in range(60):
                download_link = await page.query_selector('a[download], a:has-text("Download"), .download-btn, button:has-text("Download")')
                if download_link:
                    break
                await asyncio.sleep(5)
                if i % 6 == 0:
                    print(f"[imglarger] Still processing... ({i*5}s)")
            
            if not download_link:
                await page.screenshot(path=str(CACHE_DIR / "imglarger_timeout.png"))
                return {"success": False, "error": "Timed out", "screenshot": str(CACHE_DIR / "imglarger_timeout.png")}
            
            # Download
            print(f"[imglarger] Downloading result...")
            async with page.expect_download() as download_info:
                await download_link.click()
            download = await download_info.value
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = CACHE_DIR / f"enhanced_{timestamp}_{image_path.stem}.jpg"
            await download.save_as(str(output_path))
            
            print(f"[imglarger] ✓ Saved to {output_path}")
            
            return {
                "success": True,
                "output_path": str(output_path),
                "scale": scale,
                "service": "imglarger.com",
            }
            
        except Exception as e:
            await page.screenshot(path=str(CACHE_DIR / "imglarger_error.png"))
            return {
                "success": False,
                "error": str(e),
                "screenshot": str(CACHE_DIR / "imglarger_error.png"),
            }
        finally:
            await browser.close()


async def enhance_image(image_path: str, scale: int = 2, service: str = "auto", use_proxy: bool = True) -> dict:
    """
    Main entry point - tries multiple services with proxy rotation.
    
    Args:
        image_path: Path to input image
        scale: Upscale factor (2 or 4)
        service: "bigjpg", "imglarger", or "auto" (tries both)
        use_proxy: Whether to use proxy rotation
    
    Returns:
        dict with success, output_path, etc.
    """
    # Get a random proxy if enabled
    proxy_url = None
    if use_proxy:
        proxies = get_proxy_list()
        if proxies:
            proxy_url = random.choice(proxies)
            print(f"[enhancer] Using proxy: {proxy_url.split('@')[1] if '@' in proxy_url else proxy_url}")
    
    services = {
        "bigjpg": enhance_via_bigjpg,
        "imglarger": enhance_via_imglarger,
    }
    
    if service != "auto":
        if service not in services:
            return {"success": False, "error": f"Unknown service: {service}"}
        return await services[service](image_path, scale, proxy_url)
    
    # Auto mode: try services in order
    errors = []
    for name, func in services.items():
        print(f"\n[enhancer] Trying {name}...")
        result = await func(image_path, scale, proxy_url)
        if result["success"]:
            return result
        errors.append(f"{name}: {result.get('error', 'Unknown error')}")
        
        # Rotate proxy for next attempt
        if use_proxy and proxies:
            proxy_url = random.choice(proxies)
    
    return {
        "success": False,
        "error": "All services failed",
        "details": errors,
    }


def enhance_image_sync(image_path: str, **kwargs) -> dict:
    """Synchronous wrapper for enhance_image."""
    return asyncio.run(enhance_image(image_path, **kwargs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhance images via web services")
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("--output", "-o", help="Output path (default: auto)")
    parser.add_argument("--scale", type=int, default=2, choices=[2, 4], help="Upscale factor")
    parser.add_argument("--service", default="auto", choices=["auto", "bigjpg", "imglarger"])
    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy rotation")
    
    args = parser.parse_args()
    
    result = asyncio.run(enhance_image(
        args.image,
        scale=args.scale,
        service=args.service,
        use_proxy=not args.no_proxy,
    ))
    
    if result["success"]:
        print(f"\n✓ Success! Enhanced image saved to: {result['output_path']}")
        if args.output:
            import shutil
            shutil.move(result["output_path"], args.output)
            print(f"  Moved to: {args.output}")
    else:
        print(f"\n✗ Failed: {result.get('error')}")
        if result.get("details"):
            for d in result["details"]:
                print(f"  - {d}")
        sys.exit(1)
