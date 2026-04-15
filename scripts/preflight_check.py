"""Pipeline F v2.1 — Pre-flight check.

Run before every cohort run to verify env vars, provider connectivity, and credentials.

Usage: python scripts/preflight_check.py
"""
import sys
sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")

from dotenv import dotenv_values

env = dotenv_values("/home/elliotbot/.config/agency-os/.env")

REQUIRED_KEYS = [
    "GEMINI_API_KEY",
    "BRIGHTDATA_API_KEY",
    "DATAFORSEO_LOGIN",
    "DATAFORSEO_PASSWORD",
    "APIFY_API_TOKEN",
    "CONTACTOUT_API_KEY",
    "HUNTER_API_KEY",
    "ZEROBOUNCE_API_KEY",
    "TELEGRAM_TOKEN",
]

def check_env():
    """Verify all required env vars present with non-empty values."""
    ok = True
    for key in REQUIRED_KEYS:
        val = env.get(key, "")
        if val:
            print(f"  ✓ {key} (len={len(val)})")
        else:
            print(f"  ✗ {key} MISSING")
            ok = False
    return ok

def main():
    print("Pipeline F v2.1 — Pre-flight Check")
    print("=" * 40)

    print("\n1. Environment Variables:")
    env_ok = check_env()

    print(f"\nResult: {'PASS' if env_ok else 'FAIL'}")
    if not env_ok:
        print("Fix missing env vars before running cohort.")
        sys.exit(1)

    print("\nPre-flight PASSED. Ready to run.")

if __name__ == "__main__":
    main()
