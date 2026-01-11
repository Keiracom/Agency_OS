"""
FILE: scripts/check_env.py
PURPOSE: Validate all required environment variables for Agency OS
USAGE: python scripts/check_env.py
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Literal

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env file
from dotenv import load_dotenv

# Try multiple .env locations
env_paths = [
    Path("config/.env"),
    Path(".env"),
    Path("../.env"),
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"📁 Loaded: {env_path.absolute()}\n")
        break
else:
    print("⚠️  No .env file found. Checking system environment only.\n")


@dataclass
class EnvVar:
    name: str
    purpose: str
    priority: Literal["critical", "required", "optional"]
    category: str
    url: str = ""


# === ENVIRONMENT VARIABLE DEFINITIONS ===
ENV_VARS = [
    # CORE INFRASTRUCTURE
    EnvVar("SUPABASE_URL", "Database connection", "critical", "Infrastructure", "https://supabase.com/dashboard"),
    EnvVar("SUPABASE_ANON_KEY", "Public API access", "critical", "Infrastructure", ""),
    EnvVar("SUPABASE_SERVICE_KEY", "Admin API access", "critical", "Infrastructure", ""),
    EnvVar("DATABASE_URL", "PostgreSQL connection (port 6543)", "critical", "Infrastructure", ""),
    EnvVar("REDIS_URL", "Caching layer", "critical", "Infrastructure", "https://upstash.com"),
    EnvVar("PREFECT_API_URL", "Workflow orchestration (self-hosted)", "critical", "Infrastructure", "https://prefect-server-production-f9b1.up.railway.app"),
    
    # AI
    EnvVar("ANTHROPIC_API_KEY", "Claude AI for ICP/messaging", "critical", "AI", "https://console.anthropic.com"),
    
    # LEAD ENRICHMENT
    EnvVar("APOLLO_API_KEY", "Lead sourcing + enrichment", "required", "Enrichment", "https://developer.apollo.io"),
    EnvVar("APIFY_API_KEY", "Website scraping for ICP", "required", "Enrichment", "https://console.apify.com/account/integrations"),
    EnvVar("CLAY_API_KEY", "Fallback enrichment", "optional", "Enrichment", "https://app.clay.com/settings/api"),
    
    # EMAIL CHANNEL
    EnvVar("RESEND_API_KEY", "Send outreach emails", "required", "Email", "https://resend.com/api-keys"),
    EnvVar("POSTMARK_SERVER_TOKEN", "Inbound reply detection", "required", "Email", "https://account.postmarkapp.com/servers"),
    
    # SMS CHANNEL
    EnvVar("TWILIO_ACCOUNT_SID", "SMS outreach", "required", "SMS", "https://console.twilio.com"),
    EnvVar("TWILIO_AUTH_TOKEN", "SMS auth", "required", "SMS", ""),
    EnvVar("TWILIO_PHONE_NUMBER", "Sending number (+61...)", "required", "SMS", ""),
    
    # LINKEDIN CHANNEL
    EnvVar("HEYREACH_API_KEY", "LinkedIn automation", "required", "LinkedIn", "https://heyreach.io"),
    
    # VOICE CHANNEL
    EnvVar("VAPI_API_KEY", "Voice AI orchestration", "required", "Voice", "https://vapi.ai"),
    EnvVar("VAPI_PHONE_NUMBER_ID", "Linked Twilio number in Vapi", "required", "Voice", ""),
    EnvVar("ELEVENLABS_API_KEY", "Voice synthesis (TTS)", "required", "Voice", "https://elevenlabs.io"),
    
    # DIRECT MAIL
    EnvVar("LOB_API_KEY", "Physical mail campaigns", "optional", "Direct Mail", "https://dashboard.lob.com"),
    
    # PAYMENTS
    EnvVar("STRIPE_API_KEY", "Billing (secret key)", "required", "Payments", "https://dashboard.stripe.com/apikeys"),
    EnvVar("STRIPE_PUBLISHABLE_KEY", "Frontend Stripe.js", "required", "Payments", ""),
    EnvVar("STRIPE_WEBHOOK_SECRET", "Webhook verification", "required", "Payments", ""),
    EnvVar("STRIPE_PRICE_IGNITION", "$2,500/mo tier Price ID", "required", "Payments", ""),
    EnvVar("STRIPE_PRICE_VELOCITY", "$5,000/mo tier Price ID (or $2,500 founding)", "required", "Payments", ""),
    EnvVar("STRIPE_PRICE_DOMINANCE", "$7,500/mo tier Price ID", "required", "Payments", ""),
    
    # CALENDAR
    EnvVar("CALCOM_API_KEY", "Meeting booking", "optional", "Calendar", "https://app.cal.com/settings/developer/api-keys"),
    EnvVar("CALENDLY_API_KEY", "Alt meeting booking", "optional", "Calendar", "https://calendly.com/integrations/api_webhooks"),
    
    # SEARCH
    EnvVar("SERPER_API_KEY", "Web search for ICP research", "optional", "Search", "https://serper.dev"),
    
    # MONITORING
    EnvVar("SENTRY_DSN", "Error tracking", "optional", "Monitoring", "https://sentry.io"),
    
    # SECURITY
    EnvVar("WEBHOOK_HMAC_SECRET", "Outbound webhook signing", "optional", "Security", ""),
    EnvVar("JWT_SECRET", "JWT token signing", "optional", "Security", ""),
    
    # DEPLOYMENT
    EnvVar("VERCEL_TOKEN", "Frontend deployment", "required", "Deployment", "https://vercel.com/account/tokens"),
    EnvVar("GITHUB_TOKEN", "CI/CD access", "optional", "Deployment", "https://github.com/settings/tokens"),
    
    # GOOGLE OAUTH
    EnvVar("GOOGLE_CLIENT_ID", "Google OAuth login", "required", "Auth", "https://console.cloud.google.com/apis/credentials"),
    EnvVar("GOOGLE_CLIENT_SECRET", "Google OAuth secret", "required", "Auth", ""),
]


def check_env_var(var: EnvVar) -> tuple[bool, str]:
    """Check if an environment variable is set and valid."""
    value = os.getenv(var.name, "")
    
    if not value:
        return False, "NOT SET"
    
    # Check for placeholder values
    placeholders = ["your_", "sk-...", "pk_...", "re_...", "whsec_...", "price_...", "[", "PASSWORD"]
    for placeholder in placeholders:
        if placeholder in value:
            return False, "PLACEHOLDER"
    
    # Mask the value for display
    if len(value) > 10:
        masked = value[:4] + "..." + value[-4:]
    else:
        masked = value[:2] + "..." 
    
    return True, masked


def main():
    print("=" * 60)
    print("🔍 AGENCY OS ENVIRONMENT CHECK")
    print("=" * 60)
    print()
    
    results = {
        "critical": {"pass": 0, "fail": 0, "vars": []},
        "required": {"pass": 0, "fail": 0, "vars": []},
        "optional": {"pass": 0, "fail": 0, "vars": []},
    }
    
    current_category = ""
    
    for var in ENV_VARS:
        # Print category header
        if var.category != current_category:
            current_category = var.category
            print(f"\n{'─' * 40}")
            print(f"📦 {current_category.upper()}")
            print(f"{'─' * 40}")
        
        is_set, value = check_env_var(var)
        
        # Emoji based on status and priority
        if is_set:
            emoji = "✅"
            results[var.priority]["pass"] += 1
        else:
            if var.priority == "critical":
                emoji = "🚨"
            elif var.priority == "required":
                emoji = "❌"
            else:
                emoji = "⚪"
            results[var.priority]["fail"] += 1
            results[var.priority]["vars"].append(var)
        
        # Priority indicator
        priority_badge = {
            "critical": "[CRITICAL]",
            "required": "[REQUIRED]",
            "optional": "[optional]",
        }[var.priority]
        
        print(f"{emoji} {var.name:<30} {priority_badge:<12} {value}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    total_pass = sum(r["pass"] for r in results.values())
    total_fail = sum(r["fail"] for r in results.values())
    
    print(f"\n🚨 Critical:  {results['critical']['pass']}/{results['critical']['pass'] + results['critical']['fail']} configured")
    print(f"❌ Required:  {results['required']['pass']}/{results['required']['pass'] + results['required']['fail']} configured")
    print(f"⚪ Optional:  {results['optional']['pass']}/{results['optional']['pass'] + results['optional']['fail']} configured")
    print(f"\n📈 Total:     {total_pass}/{total_pass + total_fail} ({100 * total_pass // (total_pass + total_fail)}%)")
    
    # Action items
    if results["critical"]["fail"] > 0:
        print("\n" + "=" * 60)
        print("🚨 CRITICAL - MUST FIX BEFORE LAUNCH:")
        print("=" * 60)
        for var in results["critical"]["vars"]:
            url_hint = f" → {var.url}" if var.url else ""
            print(f"  • {var.name}: {var.purpose}{url_hint}")
    
    if results["required"]["fail"] > 0:
        print("\n" + "=" * 60)
        print("❌ REQUIRED - CHANNELS WON'T WORK WITHOUT:")
        print("=" * 60)
        for var in results["required"]["vars"]:
            url_hint = f" → {var.url}" if var.url else ""
            print(f"  • {var.name}: {var.purpose}{url_hint}")
    
    # Exit code
    if results["critical"]["fail"] > 0:
        print("\n⛔ BLOCKING: Critical variables missing. Cannot launch.")
        sys.exit(1)
    elif results["required"]["fail"] > 0:
        print("\n⚠️  WARNING: Some channels will not function.")
        sys.exit(0)
    else:
        print("\n🚀 READY: All critical and required variables configured!")
        sys.exit(0)


if __name__ == "__main__":
    main()
