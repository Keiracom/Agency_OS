#!/usr/bin/env python3
"""
YouTube OAuth Token Manager

Handles OAuth 2.0 authentication for YouTube Data API v3.
Uses Desktop app flow with localhost redirect.

Usage:
    # First-time setup (interactive)
    python youtube_oauth.py --setup
    
    # Check token status
    python youtube_oauth.py --status
    
    # Get access token (auto-refreshes if needed)
    python youtube_oauth.py --token
"""

import argparse
import http.server
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

# Configuration
ENV_FILE = Path.home() / ".config" / "agency-os" / ".env"
TOKEN_FILE = Path.home() / ".config" / "agency-os" / "youtube_tokens.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
REDIRECT_PORT = 8085
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"

# OAuth endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def load_env() -> dict[str, str]:
    """Load environment variables from .env file."""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Remove quotes if present
                    value = value.strip().strip('"').strip("'")
                    env[key.strip()] = value
    return env


def get_credentials() -> tuple[str, str]:
    """Get OAuth client credentials from environment."""
    env = load_env()
    client_id = env.get("YOUTUBE_CLIENT_ID")
    client_secret = env.get("YOUTUBE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("ERROR: Missing YOUTUBE_CLIENT_ID or YOUTUBE_CLIENT_SECRET in ~/.config/agency-os/.env")
        sys.exit(1)
    
    return client_id, client_secret


def load_tokens() -> Optional[dict]:
    """Load stored tokens from file."""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def save_tokens(tokens: dict) -> None:
    """Save tokens to file."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    # Secure the file
    os.chmod(TOKEN_FILE, 0o600)


def is_token_expired(tokens: dict) -> bool:
    """Check if access token is expired (with 5 min buffer)."""
    if "expires_at" not in tokens:
        return True
    expires_at = datetime.fromisoformat(tokens["expires_at"])
    # Add 5 minute buffer
    buffer_seconds = 300
    return datetime.now(timezone.utc).timestamp() >= (expires_at.timestamp() - buffer_seconds)


def refresh_access_token(tokens: dict) -> dict:
    """Refresh the access token using refresh token."""
    client_id, client_secret = get_credentials()
    
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": tokens["refresh_token"],
        "grant_type": "refresh_token"
    }).encode()
    
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"ERROR: Failed to refresh token: {e.code} - {error_body}")
        sys.exit(1)
    
    # Update tokens
    tokens["access_token"] = result["access_token"]
    if "refresh_token" in result:
        tokens["refresh_token"] = result["refresh_token"]
    
    # Calculate expiry
    expires_in = result.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc).timestamp() + expires_in
    tokens["expires_at"] = datetime.fromtimestamp(expires_at, timezone.utc).isoformat()
    tokens["refreshed_at"] = datetime.now(timezone.utc).isoformat()
    
    save_tokens(tokens)
    return tokens


def get_valid_access_token() -> str:
    """Get a valid access token, refreshing if necessary."""
    tokens = load_tokens()
    
    if not tokens:
        print("ERROR: No tokens found. Run 'python youtube_oauth.py --setup' first.")
        sys.exit(1)
    
    if is_token_expired(tokens):
        tokens = refresh_access_token(tokens)
    
    return tokens["access_token"]


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for tokens."""
    client_id, client_secret = get_credentials()
    
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }).encode()
    
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"ERROR: Token exchange failed: {e.code} - {error_body}")
        sys.exit(1)
    
    # Calculate expiry
    expires_in = result.get("expires_in", 3600)
    expires_at = datetime.now(timezone.utc).timestamp() + expires_in
    
    tokens = {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "token_type": result.get("token_type", "Bearer"),
        "expires_at": datetime.fromtimestamp(expires_at, timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scopes": SCOPES
    }
    
    return tokens


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""
    
    auth_code: Optional[str] = None
    error: Optional[str] = None
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def do_GET(self):
        """Handle OAuth callback."""
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            """)
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", params["error"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Authorization Failed</h1>
                <p>{OAuthCallbackHandler.error}</p>
                </body></html>
            """.encode())
        else:
            self.send_response(404)
            self.end_headers()


def run_oauth_flow(headless: bool = False) -> dict:
    """Run the full OAuth flow.
    
    Args:
        headless: If True, use manual code entry instead of local server.
    """
    client_id, _ = get_credentials()
    
    # Build authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent"  # Force consent to get refresh token
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    print("\n=== YouTube OAuth Setup ===\n")
    
    if headless:
        # Manual/headless flow
        print("HEADLESS MODE - Manual authorization required\n")
        print("1. Open this URL in any browser:\n")
        print(f"   {auth_url}\n")
        print("2. Authorize the application")
        print("3. You'll be redirected to localhost (it will fail - that's OK!)")
        print("4. Copy the FULL redirect URL from your browser address bar")
        print("   It looks like: http://localhost:8085?code=4/0XXXXX...&scope=...")
        print()
        
        redirect_url = input("Paste the redirect URL here: ").strip()
        
        # Extract code from URL
        parsed = urllib.parse.urlparse(redirect_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        
        if "error" in query_params:
            error = query_params.get("error_description", query_params["error"])[0]
            print(f"\nERROR: Authorization failed: {error}")
            sys.exit(1)
        
        if "code" not in query_params:
            print("\nERROR: No authorization code found in URL")
            print("Make sure you copied the complete URL including ?code=...")
            sys.exit(1)
        
        code = query_params["code"][0]
    else:
        # Interactive flow with local server
        print("Opening browser for authorization...")
        print(f"\nIf browser doesn't open, visit this URL:\n{auth_url}\n")
        
        # Start local server
        server = http.server.HTTPServer(("localhost", REDIRECT_PORT), OAuthCallbackHandler)
        server.timeout = 120  # 2 minute timeout
        
        # Try to open browser
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass  # URL already printed
        
        print("Waiting for authorization (timeout: 2 minutes)...")
        
        # Handle single request
        OAuthCallbackHandler.auth_code = None
        OAuthCallbackHandler.error = None
        
        while not OAuthCallbackHandler.auth_code and not OAuthCallbackHandler.error:
            server.handle_request()
        
        server.server_close()
        
        if OAuthCallbackHandler.error:
            print(f"\nERROR: Authorization failed: {OAuthCallbackHandler.error}")
            sys.exit(1)
        
        code = OAuthCallbackHandler.auth_code
    
    print("Authorization received, exchanging for tokens...")
    
    tokens = exchange_code_for_tokens(code)
    save_tokens(tokens)
    
    print("\n✓ Tokens saved successfully!")
    print(f"  Location: {TOKEN_FILE}")
    print(f"  Expires: {tokens['expires_at']}")
    
    return tokens


def show_status() -> None:
    """Show current token status."""
    tokens = load_tokens()
    
    print("\n=== YouTube OAuth Status ===\n")
    
    if not tokens:
        print("Status: NOT CONFIGURED")
        print("\nRun 'python youtube_oauth.py --setup' to authenticate.")
        return
    
    print(f"Token file: {TOKEN_FILE}")
    print(f"Created: {tokens.get('created_at', 'Unknown')}")
    print(f"Last refreshed: {tokens.get('refreshed_at', 'Never')}")
    print(f"Expires at: {tokens.get('expires_at', 'Unknown')}")
    
    if is_token_expired(tokens):
        print("Status: EXPIRED (will auto-refresh on next use)")
    else:
        print("Status: VALID ✓")
    
    print(f"Scopes: {', '.join(tokens.get('scopes', []))}")


def main():
    parser = argparse.ArgumentParser(description="YouTube OAuth Token Manager")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--setup", action="store_true", help="Run OAuth setup flow")
    group.add_argument("--status", action="store_true", help="Show token status")
    group.add_argument("--token", action="store_true", help="Print valid access token")
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Use manual code entry (for servers without browser)"
    )
    
    args = parser.parse_args()
    
    if args.setup:
        run_oauth_flow(headless=args.headless)
    elif args.status:
        show_status()
    elif args.token:
        token = get_valid_access_token()
        print(token)


if __name__ == "__main__":
    main()
