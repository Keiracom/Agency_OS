Got it — Unipile to replace HeyReach for Agency OS.
A few quick questions before I update the documentation:

Have you already signed up for Unipile? (Need to know if we're collecting API credentials or still evaluating)
Which Unipile features are you planning to use? The main ones relevant to Agency OS would be:

LinkedIn messaging/sequences
Connection request automation
Inbox sync (unified inbox)
Profile data retrieval


Does this affect the Phase 18 email infrastructure work, or is this a separate LinkedIn channel concern?
Should I search for Unipile's current pricing/API docs to update the cost modeling?
Yes look up pricing and benefits of unipile over heyreach for startup.15:26Unipile pricing plans 202510 resultsUnipile Pricing 2025g2.comAPI Pricing - Unipileunipile.comOne API for Multi-Channel Messaging in your app - Unipileunipile.comUnipile - Features & Pricing (December 2025)saasworthy.comLinkedIn API: Advancing Sales & Recruiting - Unipileunipile.comUnipile Pricing: Cost and Pricing planssaasworthy.comLinkedIn API for Developers: Full Integration Guideunipile.comHow LinkedIn API Pricing Works - Unipileunipile.comUnipile Reviews 2025: Details, Pricing, & Features | G2g2.comWhatsApp API Pricing: Understand Costs and Find a Scalable Alternative - Unipileunipile.comHeyReach pricing 2025 per seat monthly cost10 resultsHeyReach Pricing - Scale LinkedIn Outreach Like Never Before. Try It Free!heyreach.ioIn-depth Heyreach Review: Based on 100+ Paid Users Experiencesalesforge.aiHeyReach Overview (2025) – Features, Pros, Cons & Pricingsalesforge.aiHeyReach Review 2025: Is It Worth the Price? Better Alternatives Insidebearconnect.ioHeyReach Review 2025: Why It’s the #1 LinkedIn Automation Platformheyreach.ioHeyReach Pricing 2025: Compare Plans and Coststrustradius.comHeyReach Pricing 2026g2.comHeyReach for Sales Teams: Unlimited LinkedIn Senders, One Fixed Costheyreach.ioLa Growth Machine Review 2025: Features, Pros & Cons, Alternativesheyreach.ioHeyReach Review 2025: Features, Pros, Cons, Pricing and Alternativeszumvu.comHere's the Unipile vs HeyReach comparison for a startup like Agency OS:

Pricing Comparison
ScaleHeyReachUnipile1-3 LinkedIn accounts$79/month for one LinkedIn seat Heyreach ($79-$237/mo)For up to 10 linked accounts, the base price is 49€/$55 per month Unipile10 accounts$590-$790/mo (at $59-$79 each)$55/mo (included in base)50 accountsUnlimited LinkedIn seats for a fixed cost, starting at $799/month HeyreachFor 11 to 50 linked accounts, the cost is 5.00€/$5.50 per account per month Unipile = ~$275/mo100 accounts$999-$1,999/moFor 51 to 200 linked accounts, the price decreases to 4.50€/$5.00 per account per month Unipile = ~$500/mo

Key Benefits of Unipile for Agency OS
1. API-First Architecture

Unipile provides 500+ endpoints to integrate messaging, email, calendar, and user management across multiple providers like LinkedIn, WhatsApp, Gmail, and Outlook. Unipile
Rapid deployment: Get started in hours, not months Unipile

2. Multi-Channel in One API

Unipile supports integration with various platforms for messaging, including WhatsApp, LinkedIn, Instagram, Messenger, Telegram, and X (Twitter). Additionally, Unipile supports email providers such as Gmail, Outlook, and IMAP. Unipile

3. No Per-Message Fees

Unipile does not enforce any limits on your usage, you can send and receive as many messages or events as you need. Unipile

4. Full LinkedIn Feature Access

Unipile's API seamlessly integrates with all LinkedIn platforms, including LinkedIn Classic, Premium, Recruiter, and Sales Navigator. Unipile

5. Programmatic Control

You can programmatically send invitations, detect accepted connections, and trigger follow-up actions like messages. Python Central

6. Compliance & Security

Unipile's infrastructure and internal processes are aligned with SOC 2 requirements... official compliance confirmation effective October 19, 2025. Unipile


Startup Cost Savings (Agency OS Scenario)
For your 3 pricing tiers requiring multiple customer LinkedIn accounts:
TierEst. AccountsHeyReach CostUnipile CostIgnition (few)~5~$395/mo$55/moVelocity (medium)~15~$799/mo~$82/moDominance (scale)~30~$799/mo~$165/mo
Potential savings: 70-85% on LinkedIn automation costs

Trade-offs to Consider
HeyReach AdvantageUnipile Trade-offTurnkey UI/UX for campaignsYou build the UI (more dev work)Built-in unified inboxYou implement inbox in Agency OSPre-built campaign sequencesYou code the sequence logicAccount safety/warmup built-inYou manage LinkedIn limits yourself

Bottom line: Unipile makes sense if you want full programmatic control and significant cost savings, but it means building the LinkedIn campaign management features yourself rather than using HeyReach's GUI.
Want me to search for Unipile's API documentation to assess integration complexity?It means also that when we sign up a user we can link them up easier without getting their credentials for linkedin or getting them to sign up to heyreach.15:29Exactly right. That's a huge UX and onboarding win.
With HeyReach: User signs up to Agency OS → redirected to HeyReach → creates separate account → connects LinkedIn there → you manage two systems
With Unipile: User signs up to Agency OS → OAuth-style LinkedIn connection flow embedded in YOUR app → doneUnipile LinkedIn OAuth connect account flow embed app10 resultsConnection methodsunipile.comLinkedIn API for Developers: Full Integration Guideunipile.comLinkedIn API: Advancing Sales & Recruiting - Unipileunipile.comGitHub - unipile/unipile-node-sdk: A Node.js wrapper for Unipile’s API to manage LinkedIn API, WhatsApp API, Email API...github.comHosted auth wizardunipile.comLinkedIn Guideunipile.comLinkedIn API Python: The Complete Developer's Guide - Unipileunipile.comHow to Get LinkedIn ID Using an API - Unipileunipile.comUnified Inbox and Cross-Platform Communication - Unipileunipile.comLinkedIn API Documentation: Integration with Unipile - Unipileunipile.comThis confirms the onboarding advantage is significant. Here's the Unipile connection flow for Agency OS:

Hosted Auth Flow (Recommended)
The Hosted Auth Wizard is a pre-built, optimised authentication interface that simplifies the process of connecting user accounts securely. With its built-in features, you can significantly reduce your development time and provide a streamlined authentication experience. Unipile
Your onboarding flow becomes:
1. User signs up to Agency OS
2. Click "Connect LinkedIn" button
3. Agency OS backend calls Unipile to generate auth link
4. User redirected to Unipile's hosted wizard
5. User logs into LinkedIn (handles 2FA, captcha automatically)
6. Webhook fires back to Agency OS with account_id
7. Done - user is connected
Backend code (Node.js):
javascriptawait client.account.createHostedAuthLink({
  type: "create",
  api_url: "https://{YOUR_DSN}",
  expiresOn: "2024-12-22T12:00:00.701Z",
  providers: ["LINKEDIN"],
  success_redirect_url: "https://agencyos.com/onboarding/success",
  failure_redirect_url: "https://agencyos.com/onboarding/failed", 
  notify_url: "https://api.agencyos.com/webhooks/unipile",
  name: "user_12345"  // your internal user ID
});
When your user successfully connects an account, you can receive a callback on a URL of your choice with the account_id and your internal ID to store the matching and make your future requests. Unipile
Webhook response you receive:
json{
  "status": "CREATION_SUCCESS",
  "account_id": "e54m8LR22bA7G5qsAc8w",
  "name": "user_12345"
}

Key Benefits for Agency OS Onboarding
HeyReach PainUnipile SolutionUser needs separate HeyReach accountSingle Agency OS accountUser manages LinkedIn in two placesAll in Agency OSYou don't control the UXFully white-labeled experienceCredential handoff awkwardAuthenticates users through secure OAuth-like flow UnipileCan't programmatically check statusCreate a database to store your users' connected accounts with status (OK, CREDENTIALS, etc.) Unipile

Reconnection Handling
When the LinkedIn account is disconnected and you receive a webhook notification, your backend can use the custom authentication 'reconnect' function with the last recorded cookie and the account_id retrieved during the initial connection. Unipile
This means you can handle session expiry gracefully without user intervention in many cases.

Rate Limits to Build Into Agency OS
Connection Requests (Invitations): For paid and active LinkedIn accounts, it's recommended to send between 80 and 100 invitations per day. Message Sending: Limit message sending to between 100 and 150 per account per day to stay within safe usage parameters. Unipile

Bottom line: This eliminates the "go sign up for HeyReach" friction entirely. Your customers connect LinkedIn inside Agency OS and never know Unipile exists.
Want me to draft a migration plan from HeyReach to Unipile for the PROJECT_BLUEPRINT?We know the limits with linkedin. We set the connections from our end. Lets say agency os makes 17 connections a day through unipile and we have that guardrail on the limit of connections. How do we randomise the timing? Do we require another tool or do we program that in?15:33You program that in yourself. Unipile is just the API — it executes when you call it. The timing/randomisation logic lives in your orchestration layer.
Options for Agency OS:

Prefect (already in your stack) — Schedule flows with random delays between tasks
Custom Python with asyncio or time.sleep — Simple random intervals
Celery with jitter — If you need distributed task queue


Simple approach with Prefect:
pythonimport random
import asyncio
from prefect import flow, task

@task
def send_connection_request(account_id: str, profile_urn: str):
    # Call Unipile API
    client.messaging.send_invitation(
        account_id=account_id,
        recipient_id=profile_urn,
        message="Hi, I'd love to connect..."
    )

@flow
async def daily_linkedin_outreach(account_id: str, prospects: list):
    daily_limit = 17
    
    for prospect in prospects[:daily_limit]:
        send_connection_request(account_id, prospect["urn"])
        
        # Random delay: 8-45 minutes between requests
        delay = random.uniform(8 * 60, 45 * 60)
        await asyncio.sleep(delay)

Key randomisation factors to mimic human behaviour:
FactorImplementationTime between requestsrandom.uniform(min_seconds, max_seconds)Daily start timeRandomise first request between 8am-10amAvoid overnightOnly run during "business hours" for that user's timezoneBatch variationSome days 15, some days 19 (within safe range)Weekday weightingReduce volume on weekends

Do you want me to draft a full LinkedInOrchestrationEngine module that handles:

Per-account daily limits
Randomised timing with jitter
Timezone-aware scheduling
Queue management for multiple Agency OS customers?
Yes15:35Check if there's a relevant skill for creating documentation or code filesThis is for docx files. Since this is a Python module for the backend, I'll create it directly.3 stepsCopy all LinkedIn orchestration files to outputsbashcp /home/claude/linkedin_orchestration_engine.py /home/claude/linkedin_orchestration_schema.sql /home/claude/linkedin_orchestration_routes.py /mnt/user-data/outputs/Outputexit code 0Presented 3 filesHere's the complete LinkedIn Orchestration Engine for Agency OS:

What's Included
1. linkedin_orchestration_engine.py — Core orchestration logic

TimingEngine — Humanised random delays (beta distribution, 5-45 min between actions)
QueueManager — Action queue with priority, retry logic, dead letter handling
UnipileClient — Async wrapper for Unipile API
Prefect flows for daily outreach with concurrency control
Timezone-aware business hours (8am-6pm, skip/reduce weekends)
Per-hour burst prevention (max 8 actions/hour)

2. linkedin_orchestration_schema.sql — Supabase persistence

linkedin_action_queue — Pending actions with status tracking
linkedin_account_daily_state — Daily counts and randomised limits
linkedin_connected_accounts — Linked accounts via Unipile
PostgreSQL functions for atomic queue operations
Row Level Security policies

3. linkedin_orchestration_routes.py — FastAPI integration

/connect — Initiate Unipile hosted auth flow
/accounts/{id}/queue — Add actions to queue
/accounts/{id}/queue/bulk — Bulk import (up to 500)
/accounts/{id}/stats/today — Daily progress
Webhook endpoints for Unipile callbacks


Key Timing Randomisation
python# Beta distribution for natural clustering
delay = random.betavariate(2, 5)  # Right-skewed, most delays in lower-middle range

# Daily limit randomisation
connections_today = random.randint(15, 20)  # Not always 17

# Start time jitter
start_time = 8am + random.randint(0, 120) minutes

Next Steps

Get Unipile API credentials — Sign up at unipile.com
Run the SQL schema in Supabase
Add environment variables: UNIPILE_DSN, UNIPILE_API_KEY
Deploy Prefect flow on a schedule (every 30 min during business hours)

Want me to update the PROJECT_BLUEPRINT to reflect the HeyReach → Unipile migration?Linkedin orchestration enginePY Open in Visual Studio CodeLinkedin orchestration schemaCode · SQL Open in Visual Studio CodeLinkedin orchestration routesPY Open in Visual Studio CodeDownload allSomething to keep in mind. All we need is connections. We already have the lead and all their linkedin scraped through apify. So once this process is done. We just make a connection via unipile via the user's account.15:39That simplifies things significantly. Let me clarify the flow:
Current State:

Lead data already enriched (Apify scrape → Clay waterfall → stored in Supabase)
Lead has LinkedIn profile URL/URN ready to go

What Unipile does:

User connects their LinkedIn via hosted auth (once, during onboarding)
Agency OS queues connection requests
Orchestration engine sends them with randomised timing


So the engine I built is overkill for your immediate needs. You really just need:
python# Simplified flow
async def send_daily_connections(account_id: str, leads: list[str]):
    """
    account_id: Unipile account ID (user's LinkedIn)
    leads: List of LinkedIn profile URNs to connect with
    """
    daily_limit = random.randint(15, 20)
    
    for urn in leads[:daily_limit]:
        await unipile.send_connection_request(
            account_id=account_id,
            recipient_urn=urn,
            message=personalised_message  # From your AI content engine
        )
        
        # Random delay: 8-45 minutes
        await asyncio.sleep(random.uniform(480, 2700))

Questions to confirm the stripped-down scope:

Connection message — Is this generated per-lead by your AI Content Engine, or a template with variable substitution?
After connection accepted — Does Agency OS need to handle follow-up messages, or is that a future phase?
Tracking — Do you need to track connection request → accepted/rejected status via Unipile webhooks?

Want me to slim down the module to just the connection-sending logic with timing randomisation?Im not sure. We need to see how extracting posts and other data on a lead will determine an icebreaker. What are your thoughts on this?15:40Good question. There are a few approaches to generating personalised icebreakers from LinkedIn data:

Option 1: Pre-scrape via Apify (Current Flow)
You're already scraping leads. Apify can pull:

Recent posts (content, engagement)
Activity (comments, shares, reactions)
Profile details (headline, about, experience, skills)
Featured content
Recommendations

Icebreaker generated at enrichment time, stored with lead data. Connection request uses pre-written message.
Pros: No extra API calls at send time, faster queue processing
Cons: Data could be stale by send time (days/weeks later)

Option 2: Just-in-Time via Unipile
Before sending connection, fetch fresh data:
python# Unipile can retrieve profile + posts
profile = await unipile.get_profile(account_id, profile_urn, linkedin_sections="*")
posts = await unipile.get_user_posts(account_id, profile_urn)

# Generate icebreaker with fresh context
icebreaker = await ai_engine.generate_icebreaker(profile, posts)

# Send connection
await unipile.send_connection_request(account_id, profile_urn, message=icebreaker)
Pros: Fresh data, more relevant icebreaker
Cons: Extra API calls, slower processing, potential rate limits on profile views

Option 3: Hybrid (Recommended)

Apify scrape at enrichment — Get baseline profile data
Score leads — ALS determines priority
Just-in-time post fetch — Only for high-priority leads, right before sending
Fallback — Use pre-generated icebreaker if fresh fetch fails


What Makes a Good Icebreaker?
SignalExampleIcebreaker AngleRecent post topicPosted about AI in marketing"Saw your take on AI personalisation — we're seeing similar results with..."EngagementCommented on industry newsReference the specific discussionJob changeStarted new role 2 months ago"Congrats on the move to [Company]..."Shared connectionMutual contact"Noticed we both know [Name]..."Content creatorRegular poster"Been following your posts on [topic]..."Event/webinarAttended or spoke at eventReference the event

My Recommendation
For MVP/launch: Pre-generate icebreakers during enrichment (Apify data → Claude → stored message). Keeps the connection-sending logic simple.
Post-launch iteration: Add just-in-time freshness check for top-tier leads where conversion matters most.

What's your gut feel? Do you want the icebreaker locked in at enrichment, or does the "stale data" concern warrant the extra complexity?look into agency os files and tell me how hard it will be to replace heyreach with unipile?21:28Searched Google Drive0 resultsSearching Google Drivelook into agency os files and tell me how hard it will be to replace heyreach with unipile? you are claude desktop - you have mcp access to get into my local folders21:29look into agency os files and tell me how hard it will be to replace heyreach with unipile? you are claude desktop - you have mcp access to get into my local folders C:\AI\Agency_OS read blueprint and progress21:295 stepsFread_text_fileRequest{
  `path`: `C:\\AI\\Agency_OS\\src\\integrations\\heyreach.py`
}Response"""
FILE: src/integrations/heyreach.py
PURPOSE: HeyReach integration for LinkedIn automation with proxy
PHASE: 3 (Integrations)
TASK: INT-009
DEPENDENCIES:
  - src/config/settings.py
  - src/exceptions.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 17: Resource-level rate limits (17/day/seat)
"""

from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config.settings import settings
from src.exceptions import APIError, IntegrationError, ResourceRateLimitError


class HeyReachClient:
    """
    HeyReach client for LinkedIn automation.

    Manages LinkedIn outreach via HeyReach API with
    per-seat rate limiting (17/day per seat).
    """

    BASE_URL = "https://api.heyreach.io/v1"
    DAILY_LIMIT_PER_SEAT = 17  # Rule 17

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.heyreach_api_key
        if not self.api_key:
            raise IntegrationError(
                service="heyreach",
                message="HeyReach API key is required",
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
    ) -> dict:
        """Make API request with retry logic."""
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise APIError(
                service="heyreach",
                status_code=e.response.status_code,
                response=e.response.text,
            )
        except httpx.RequestError as e:
            raise IntegrationError(
                service="heyreach",
                message=f"HeyReach request failed: {str(e)}",
            )

    async def get_seats(self) -> list[dict[str, Any]]:
        """
        Get available LinkedIn seats.

        Returns:
            List of seats with usage info
        """
        result = await self._request("GET", "/seats")
        return result.get("seats", [])

    async def send_connection_request(
        self,
        seat_id: str,
        linkedin_url: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        """
        Send LinkedIn connection request.

        Args:
            seat_id: HeyReach seat ID to use
            linkedin_url: Target LinkedIn profile URL
            message: Optional connection message

        Returns:
            Connection request result
        """
        data = {
            "seat_id": seat_id,
            "profile_url": linkedin_url,
        }
        if message:
            data["message"] = message[:300]  # LinkedIn limit

        result = await self._request("POST", "/connections/request", data)

        return {
            "success": True,
            "request_id": result.get("id"),
            "status": result.get("status"),
            "provider": "heyreach",
        }

    async def send_message(
        self,
        seat_id: str,
        linkedin_url: str,
        message: str,
    ) -> dict[str, Any]:
        """
        Send LinkedIn direct message.

        Args:
            seat_id: HeyReach seat ID
            linkedin_url: Target LinkedIn profile URL
            message: Message content

        Returns:
            Message send result
        """
        data = {
            "seat_id": seat_id,
            "profile_url": linkedin_url,
            "message": message,
        }

        result = await self._request("POST", "/messages/send", data)

        return {
            "success": True,
            "message_id": result.get("id"),
            "status": result.get("status"),
            "provider": "heyreach",
        }

    async def get_conversations(
        self,
        seat_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get LinkedIn conversations for a seat.

        Args:
            seat_id: HeyReach seat ID
            limit: Maximum conversations to return

        Returns:
            List of conversations
        """
        result = await self._request(
            "GET",
            f"/conversations?seat_id={seat_id}&limit={limit}",
        )

        return [
            {
                "conversation_id": c.get("id"),
                "profile_url": c.get("profile_url"),
                "name": c.get("name"),
                "last_message": c.get("last_message"),
                "last_message_at": c.get("last_message_at"),
                "unread": c.get("unread", False),
            }
            for c in result.get("conversations", [])
        ]

    async def get_new_replies(self, seat_id: str) -> list[dict[str, Any]]:
        """
        Get new replies (unread messages) for a seat.

        Args:
            seat_id: HeyReach seat ID

        Returns:
            List of new replies
        """
        result = await self._request(
            "GET",
            f"/messages/unread?seat_id={seat_id}",
        )

        return [
            {
                "message_id": m.get("id"),
                "profile_url": m.get("profile_url"),
                "name": m.get("sender_name"),
                "message": m.get("content"),
                "received_at": m.get("received_at"),
            }
            for m in result.get("messages", [])
        ]

    async def get_profile(self, linkedin_url: str) -> dict[str, Any]:
        """
        Get LinkedIn profile data.

        Args:
            linkedin_url: LinkedIn profile URL

        Returns:
            Profile data
        """
        result = await self._request(
            "POST",
            "/profiles/lookup",
            {"profile_url": linkedin_url},
        )

        profile = result.get("profile", {})
        return {
            "found": bool(profile),
            "linkedin_url": linkedin_url,
            "first_name": profile.get("first_name"),
            "last_name": profile.get("last_name"),
            "headline": profile.get("headline"),
            "company": profile.get("current_company"),
            "location": profile.get("location"),
            "connections": profile.get("connections_count"),
        }

    async def check_seat_limit(self, seat_id: str) -> dict[str, Any]:
        """
        Check if seat has available daily capacity.

        Args:
            seat_id: HeyReach seat ID

        Returns:
            Limit info with remaining capacity
        """
        result = await self._request("GET", f"/seats/{seat_id}/usage")

        daily_used = result.get("daily_actions", 0)
        remaining = max(0, self.DAILY_LIMIT_PER_SEAT - daily_used)

        return {
            "seat_id": seat_id,
            "daily_limit": self.DAILY_LIMIT_PER_SEAT,
            "daily_used": daily_used,
            "remaining": remaining,
            "can_send": remaining > 0,
        }

    # ==========================================
    # LinkedIn Account Management (Phase 24H)
    # ==========================================

    async def add_linkedin_account(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """
        Add a LinkedIn account to HeyReach.

        NOTE: Check HeyReach API documentation for actual endpoint.
        This is based on common patterns for LinkedIn automation platforms.

        Args:
            email: LinkedIn account email
            password: LinkedIn account password

        Returns:
            Dict with:
            - success: bool
            - requires_2fa: bool (if 2FA needed)
            - 2fa_method: str ('sms', 'email', 'authenticator')
            - sender_id: str (HeyReach sender ID)
            - account_id: str (HeyReach account ID)
            - profile_url: str
            - profile_name: str
            - headline: str
            - connection_count: int
            - error: str (if failed)
        """
        try:
            result = await self._request(
                "POST",
                "/senders/linkedin",
                data={
                    "email": email,
                    "password": password,
                },
            )

            # Check if 2FA is required
            if result.get("requires_verification") or result.get("requires_2fa"):
                return {
                    "success": False,
                    "requires_2fa": True,
                    "2fa_method": result.get("verification_method", "unknown"),
                }

            # Check for errors
            if result.get("error") or not result.get("sender_id"):
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": result.get("error", "Failed to connect LinkedIn account"),
                }

            # Success
            return {
                "success": True,
                "requires_2fa": False,
                "sender_id": result.get("sender_id") or result.get("id"),
                "account_id": result.get("account_id"),
                "profile_url": result.get("profile_url") or result.get("linkedin_url"),
                "profile_name": result.get("name") or result.get("profile_name"),
                "headline": result.get("headline"),
                "connection_count": result.get("connections") or result.get("connection_count"),
            }

        except APIError as e:
            # Handle specific API errors
            if e.status_code == 401:
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": "Invalid LinkedIn credentials",
                }
            elif e.status_code == 429:
                return {
                    "success": False,
                    "requires_2fa": False,
                    "error": "Too many attempts. Please try again later.",
                }
            raise

    async def verify_2fa(
        self,
        email: str,
        password: str,
        code: str,
    ) -> dict[str, Any]:
        """
        Submit 2FA code to complete LinkedIn connection.

        Args:
            email: LinkedIn account email
            password: LinkedIn account password
            code: 2FA verification code

        Returns:
            Same structure as add_linkedin_account
        """
        try:
            result = await self._request(
                "POST",
                "/senders/linkedin/verify",
                data={
                    "email": email,
                    "password": password,
                    "code": code,
                },
            )

            if result.get("error") or not result.get("sender_id"):
                return {
                    "success": False,
                    "error": result.get("error", "Invalid verification code"),
                }

            return {
                "success": True,
                "sender_id": result.get("sender_id") or result.get("id"),
                "account_id": result.get("account_id"),
                "profile_url": result.get("profile_url") or result.get("linkedin_url"),
                "profile_name": result.get("name") or result.get("profile_name"),
                "headline": result.get("headline"),
                "connection_count": result.get("connections") or result.get("connection_count"),
            }

        except APIError as e:
            if e.status_code == 400:
                return {
                    "success": False,
                    "error": "Invalid verification code",
                }
            raise

    async def remove_sender(self, sender_id: str) -> dict[str, Any]:
        """
        Remove a LinkedIn sender from HeyReach.

        Args:
            sender_id: HeyReach sender ID

        Returns:
            Dict with success status
        """
        result = await self._request("DELETE", f"/senders/{sender_id}")
        return {
            "success": True,
            "sender_id": sender_id,
        }

    async def get_sender(self, sender_id: str) -> dict[str, Any]:
        """
        Get sender details from HeyReach.

        Args:
            sender_id: HeyReach sender ID

        Returns:
            Sender details
        """
        result = await self._request("GET", f"/senders/{sender_id}")
        return {
            "sender_id": result.get("id"),
            "email": result.get("email"),
            "profile_url": result.get("profile_url"),
            "profile_name": result.get("name"),
            "headline": result.get("headline"),
            "connection_count": result.get("connections"),
            "status": result.get("status"),
        }


# Singleton instance
_heyreach_client: HeyReachClient | None = None


def get_heyreach_client() -> HeyReachClient:
    """Get or create HeyReach client instance."""
    global _heyreach_client
    if _heyreach_client is None:
        _heyreach_client = HeyReachClient()
    return _heyreach_client


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Seat management
# [x] Connection requests
# [x] Direct messaging
# [x] Conversation retrieval
# [x] New replies (unread messages)
# [x] Profile lookup
# [x] Daily limit tracking (17/seat)
# [x] Error handling with custom exceptions
# [x] All functions have type hints
# [x] All functions have docstrings
Fread_text_fileRequest{
  `path`: `C:\\AI\\Agency_OS\\src\\engines\\linkedin.py`
}Response"""
FILE: src/engines/linkedin.py
PURPOSE: LinkedIn engine using HeyReach integration
PHASE: 4 (Engines), modified Phase 16/24B for Conversion Intelligence
TASK: ENG-007, 16E-003, CONTENT-004
DEPENDENCIES:
  - src/engines/base.py
  - src/engines/content_utils.py (Phase 16)
  - src/integrations/heyreach.py
  - src/integrations/redis.py
  - src/models/lead.py
  - src/models/activity.py
RULES APPLIED:
  - Rule 1: Follow blueprint exactly
  - Rule 11: Session passed as argument
  - Rule 12: No imports from other engines (content_utils is utilities, not engine)
  - Rule 14: Soft deletes only
  - Rule 17: Resource-level rate limits (17/day/seat)
PHASE 16 CHANGES:
  - Added content_snapshot capture for WHAT Detector learning
  - Tracks touch_number, sequence context, and message_type
PHASE 24B CHANGES:
  - Store full_message_body for complete content analysis
  - Link to template_id for template tracking
  - Track ab_test_id and ab_variant for A/B testing
  - Store links_included and personalization_fields_used
  - Track ai_model_used and prompt_version
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.engines.base import EngineResult, OutreachEngine

logger = logging.getLogger(__name__)
from src.engines.content_utils import build_linkedin_snapshot
from src.exceptions import ResourceRateLimitError, ValidationError
from src.integrations.heyreach import HeyReachClient, get_heyreach_client
from src.integrations.redis import rate_limiter
from src.models.activity import Activity
from src.models.base import ChannelType
from src.models.lead import Lead


# Rate limit (Rule 17)
LINKEDIN_DAILY_LIMIT_PER_SEAT = 17


class LinkedInEngine(OutreachEngine):
    """
    LinkedIn engine for sending connection requests and messages via HeyReach.

    Features:
    - Connection request sending
    - Direct message sending
    - Resource-level rate limiting (17/day/seat - Rule 17)
    - Activity logging
    - Conversation tracking
    """

    def __init__(self, heyreach_client: HeyReachClient | None = None):
        """
        Initialize LinkedIn engine.

        Args:
            heyreach_client: Optional HeyReach client (uses singleton if not provided)
        """
        self._heyreach = heyreach_client

    @property
    def name(self) -> str:
        return "linkedin"

    @property
    def channel(self) -> ChannelType:
        return ChannelType.LINKEDIN

    @property
    def heyreach(self) -> HeyReachClient:
        if self._heyreach is None:
            self._heyreach = get_heyreach_client()
        return self._heyreach

    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        content: str,
        **kwargs: Any,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn message or connection request.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            content: Message content
            **kwargs: Additional options:
                - seat_id: HeyReach seat ID (required)
                - action: 'connection' or 'message' (default: 'message')
                - template_id: UUID of template used (Phase 24B)
                - ab_test_id: UUID of A/B test (Phase 24B)
                - ab_variant: A/B variant 'A', 'B', or 'control' (Phase 24B)
                - ai_model_used: AI model used for generation (Phase 24B)
                - prompt_version: Version of prompt used (Phase 24B)
                - personalization_fields_used: List of personalization fields (Phase 24B)

        Returns:
            EngineResult with send result
        """
        # Validate required fields
        seat_id = kwargs.get("seat_id")
        if not seat_id:
            return EngineResult.fail(
                error="HeyReach seat_id is required",
                metadata={"lead_id": str(lead_id)},
            )

        action = kwargs.get("action", "message")
        if action not in ("connection", "message"):
            return EngineResult.fail(
                error="Invalid action. Must be 'connection' or 'message'",
                metadata={"action": action},
            )

        # Get lead
        lead = await self.get_lead_by_id(db, lead_id)
        campaign = await self.get_campaign_by_id(db, campaign_id)

        # Validate LinkedIn URL
        if not lead.linkedin_url:
            return EngineResult.fail(
                error="Lead has no LinkedIn URL",
                metadata={"lead_id": str(lead_id)},
            )

        # TEST_MODE: Redirect LinkedIn to test recipient
        original_linkedin = lead.linkedin_url
        if settings.TEST_MODE:
            lead.linkedin_url = settings.TEST_LINKEDIN_RECIPIENT
            logger.info(f"TEST_MODE: Redirecting LinkedIn {original_linkedin} → {lead.linkedin_url}")

        # Check rate limit (Rule 17)
        try:
            allowed, current_count = await rate_limiter.check_and_increment(
                resource_type="linkedin",
                resource_id=seat_id,
                limit=LINKEDIN_DAILY_LIMIT_PER_SEAT,
            )
        except ResourceRateLimitError as e:
            return EngineResult.fail(
                error=str(e),
                metadata={
                    "seat_id": seat_id,
                    "limit": LINKEDIN_DAILY_LIMIT_PER_SEAT,
                },
            )

        try:
            # Send connection request or message
            if action == "connection":
                result = await self.heyreach.send_connection_request(
                    seat_id=seat_id,
                    linkedin_url=lead.linkedin_url,
                    message=content if content else None,
                )
                activity_action = "connection_sent"
            else:
                result = await self.heyreach.send_message(
                    seat_id=seat_id,
                    linkedin_url=lead.linkedin_url,
                    message=content,
                )
                activity_action = "message_sent"

            # Get message/request ID
            provider_id = result.get("message_id") or result.get("request_id")

            # Log activity with content snapshot (Phase 16) and template tracking (Phase 24B)
            await self._log_activity(
                db=db,
                lead=lead,
                campaign_id=campaign_id,
                action=activity_action,
                provider_message_id=provider_id,
                content_preview=content[:200] if len(content) > 200 else content,
                message_content=content,  # Phase 16: Pass full content for snapshot
                message_type="connection" if action == "connection" else "message",
                connection_note=content if action == "connection" else None,
                sequence_step=kwargs.get("sequence_step"),
                sequence_id=kwargs.get("sequence_id"),
                provider_response=result,
                seat_id=seat_id,
                # Phase 24B: Content tracking fields
                template_id=kwargs.get("template_id"),
                ab_test_id=kwargs.get("ab_test_id"),
                ab_variant=kwargs.get("ab_variant"),
                ai_model_used=kwargs.get("ai_model_used"),
                prompt_version=kwargs.get("prompt_version"),
                personalization_fields_used=kwargs.get("personalization_fields_used"),
            )

            return EngineResult.ok(
                data={
                    "provider_id": provider_id,
                    "linkedin_url": lead.linkedin_url,
                    "seat_id": seat_id,
                    "action": action,
                    "status": result.get("status"),
                    "remaining_quota": LINKEDIN_DAILY_LIMIT_PER_SEAT - current_count,
                },
                metadata={
                    "engine": self.name,
                    "channel": self.channel.value,
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"LinkedIn {action} failed: {str(e)}",
                metadata={
                    "lead_id": str(lead_id),
                    "campaign_id": str(campaign_id),
                    "seat_id": seat_id,
                    "action": action,
                },
            )

    async def send_connection_request(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str | None = None,
        seat_id: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn connection request.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Optional connection message
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message or "",
            seat_id=seat_id,
            action="connection",
        )

    async def send_message(
        self,
        db: AsyncSession,
        lead_id: UUID,
        campaign_id: UUID,
        message: str,
        seat_id: str | None = None,
    ) -> EngineResult[dict[str, Any]]:
        """
        Send a LinkedIn direct message.

        Args:
            db: Database session (passed by caller)
            lead_id: Target lead UUID
            campaign_id: Campaign UUID
            message: Message content
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with send result
        """
        return await self.validate_and_send(
            db=db,
            lead_id=lead_id,
            campaign_id=campaign_id,
            content=message,
            seat_id=seat_id,
            action="message",
        )

    async def send_batch(
        self,
        db: AsyncSession,
        actions: list[dict[str, Any]],
    ) -> EngineResult[dict[str, Any]]:
        """
        Send multiple LinkedIn actions (connections or messages).

        Args:
            db: Database session (passed by caller)
            actions: List of action configs with lead_id, campaign_id, content, etc.

        Returns:
            EngineResult with batch send summary
        """
        results = {
            "total": len(actions),
            "sent": 0,
            "failed": 0,
            "rate_limited": 0,
            "actions": [],
        }

        for action_config in actions:
            lead_id = action_config.get("lead_id")
            campaign_id = action_config.get("campaign_id")
            content = action_config.get("content", "")

            if not all([lead_id, campaign_id]):
                results["failed"] += 1
                results["actions"].append({
                    "lead_id": str(lead_id) if lead_id else None,
                    "status": "failed",
                    "reason": "Missing required fields",
                })
                continue

            result = await self.validate_and_send(
                db=db,
                lead_id=lead_id,
                campaign_id=campaign_id,
                content=content,
                **action_config,
            )

            if result.success:
                results["sent"] += 1
                results["actions"].append({
                    "lead_id": str(lead_id),
                    "status": "sent",
                    "provider_id": result.data.get("provider_id"),
                    "action": result.data.get("action"),
                })
            else:
                # Check if rate limited
                if "rate limit" in result.error.lower():
                    results["rate_limited"] += 1
                else:
                    results["failed"] += 1

                results["actions"].append({
                    "lead_id": str(lead_id),
                    "status": "failed",
                    "reason": result.error,
                })

        return EngineResult.ok(
            data=results,
            metadata={
                "success_rate": results["sent"] / results["total"] if results["total"] > 0 else 0,
            },
        )

    async def get_seat_status(
        self,
        seat_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get status of a LinkedIn seat (quota, availability).

        Args:
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with seat status
        """
        try:
            # Get current usage from rate limiter
            usage = await rate_limiter.get_usage(
                resource_type="linkedin",
                resource_id=seat_id,
            )

            remaining = max(0, LINKEDIN_DAILY_LIMIT_PER_SEAT - usage)

            return EngineResult.ok(
                data={
                    "seat_id": seat_id,
                    "daily_limit": LINKEDIN_DAILY_LIMIT_PER_SEAT,
                    "daily_used": usage,
                    "remaining": remaining,
                    "can_send": remaining > 0,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get seat status: {str(e)}",
                metadata={"seat_id": seat_id},
            )

    async def get_new_replies(
        self,
        db: AsyncSession,
        seat_id: str,
    ) -> EngineResult[dict[str, Any]]:
        """
        Get new LinkedIn replies for a seat.

        Args:
            db: Database session (passed by caller)
            seat_id: HeyReach seat ID

        Returns:
            EngineResult with new replies
        """
        try:
            replies = await self.heyreach.get_new_replies(seat_id)

            return EngineResult.ok(
                data={
                    "seat_id": seat_id,
                    "reply_count": len(replies),
                    "replies": replies,
                },
            )

        except Exception as e:
            return EngineResult.fail(
                error=f"Failed to get replies: {str(e)}",
                metadata={"seat_id": seat_id},
            )

    async def _log_activity(
        self,
        db: AsyncSession,
        lead: Lead,
        campaign_id: UUID,
        action: str,
        provider_message_id: str | None = None,
        content_preview: str | None = None,
        message_content: str | None = None,
        message_type: str = "message",
        connection_note: str | None = None,
        sequence_step: int | None = None,
        sequence_id: str | None = None,
        provider_response: dict | None = None,
        seat_id: str | None = None,
        # Phase 24B: Content tracking fields
        template_id: UUID | None = None,
        ab_test_id: UUID | None = None,
        ab_variant: str | None = None,
        ai_model_used: str | None = None,
        prompt_version: str | None = None,
        personalization_fields_used: list[str] | None = None,
    ) -> None:
        """
        Log LinkedIn activity to database.

        Phase 16: Now captures content_snapshot for WHAT Detector learning.
        Phase 24B: Now stores template_id, A/B test info, and full message body.
        """
        metadata = {}
        if seat_id:
            metadata["seat_id"] = seat_id

        # Build content snapshot for Conversion Intelligence (Phase 16)
        snapshot = None
        full_body = message_content or connection_note
        if full_body:
            snapshot = build_linkedin_snapshot(
                message=message_content or "",
                lead=lead,
                message_type=message_type,
                connection_note=connection_note,
                touch_number=sequence_step or 1,
                sequence_id=sequence_id,
            )
            # Phase 24B: Enhance snapshot with additional tracking data
            if snapshot:
                snapshot["ai_model"] = ai_model_used
                snapshot["prompt_version"] = prompt_version
                snapshot["personalization_available"] = personalization_fields_used or []
                if ab_variant:
                    snapshot["ab_variant"] = ab_variant
                if ab_test_id:
                    snapshot["ab_test_id"] = str(ab_test_id)

        # Phase 24B: Extract links from LinkedIn content
        links_included = None
        if full_body:
            import re
            # Extract URLs from LinkedIn message content
            url_pattern = r'https?://[^\s]+'
            links_included = list(set(re.findall(url_pattern, full_body)))

        activity = Activity(
            client_id=lead.client_id,
            campaign_id=campaign_id,
            lead_id=lead.id,
            channel=ChannelType.LINKEDIN,
            action=action,
            provider_message_id=provider_message_id,
            sequence_step=sequence_step,
            content_preview=content_preview,
            content_snapshot=snapshot,  # Phase 16: Store content snapshot
            # Phase 24B: Content tracking fields
            template_id=template_id,
            ab_test_id=ab_test_id,
            ab_variant=ab_variant,
            full_message_body=full_body,  # Store complete content
            links_included=links_included,
            personalization_fields_used=personalization_fields_used,
            ai_model_used=ai_model_used,
            prompt_version=prompt_version,
            provider="heyreach",
            provider_status=action,
            provider_response=provider_response,
            extra_data=metadata,
            created_at=datetime.utcnow(),
        )

        db.add(activity)
        await db.commit()


# Singleton instance
_linkedin_engine: LinkedInEngine | None = None


def get_linkedin_engine() -> LinkedInEngine:
    """Get or create LinkedIn engine instance."""
    global _linkedin_engine
    if _linkedin_engine is None:
        _linkedin_engine = LinkedInEngine()
    return _linkedin_engine


# ============================================
# VERIFICATION CHECKLIST
# ============================================
# [x] Contract comment at top
# [x] No hardcoded credentials
# [x] Session passed as argument (Rule 11)
# [x] No imports from other engines (Rule 12)
# [x] Soft delete check inherited from BaseEngine
# [x] Resource-level rate limits (17/day/seat - Rule 17)
# [x] Connection request support
# [x] Direct message support
# [x] Activity logging after send
# [x] Batch sending support
# [x] Seat status checking
# [x] New replies retrieval
# [x] Extends OutreachEngine from base.py
# [x] EngineResult wrapper for responses
# [x] All functions have type hints
# [x] All functions have docstrings
# [x] Phase 16: content_snapshot captured for WHAT Detector
# [x] Phase 16: touch_number, sequence_id, and message_type tracked
# [x] Phase 24B: template_id stored for template tracking
# [x] Phase 24B: ab_test_id and ab_variant for A/B testing
# [x] Phase 24B: full_message_body stored for complete content analysis
# [x] Phase 24B: links_included extracted from LinkedIn
# [x] Phase 24B: personalization_fields_used tracked
# [x] Phase 24B: ai_model_used and prompt_version stored
I've already started looking at the files. Let me continue searching for all HeyReach references to give you a complete picture.9 stepsFread_text_fileRequest{
  `head`: 150,
  `path`: `C:\\AI\\Agency_OS\\src\\config\\settings.py`,
  `tail`: 100
}ResponseCannot specify both head and tail parameters simultaneouslyread_fileRequest{
  `path`: `C:\\AI\\Agency_OS\\src\\config\\settings.py`,
  `length`: 50,
  `offset`: 100
}Response[Reading 50 lines from line 100 (total: 313 lines, 163 remaining)]

    # NOT used for SMS. ClickSend is the SMS provider for Australia.
    twilio_account_sid: str = Field(default="", description="Twilio account SID (voice only)")
    twilio_auth_token: str = Field(default="", description="Twilio auth token (voice only)")
    twilio_phone_number: str = Field(default="", description="Twilio phone number (voice only)")

    heyreach_api_key: str = Field(default="", description="HeyReach API key")
    
    # === ClickSend (Australian SMS + Direct Mail) ===
    # Primary SMS provider for Australian market. Twilio is used for voice calls ONLY.
    clicksend_username: str = Field(default="", description="ClickSend username/email")
    clicksend_api_key: str = Field(default="", description="ClickSend API key")

    # === DataForSEO (SEO Metrics Enrichment) ===
    dataforseo_login: str = Field(default="", description="DataForSEO login email")
    dataforseo_password: str = Field(default="", description="DataForSEO API password")

    # === Voice AI Stack (Vapi + ElevenLabs) ===
    vapi_api_key: str = Field(default="", description="Vapi API key")
    vapi_phone_number_id: str = Field(default="", description="Twilio number linked in Vapi")
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key")

    # === Stripe ===
    stripe_api_key: str = Field(default="", description="Stripe secret key")
    stripe_publishable_key: str = Field(default="", description="Stripe publishable key")
    stripe_webhook_secret: str = Field(default="", description="Stripe webhook signing secret")
    stripe_price_ignition: str = Field(default="", description="Stripe Price ID for Ignition tier")
    stripe_price_velocity: str = Field(default="", description="Stripe Price ID for Velocity tier")
    stripe_price_dominance: str = Field(default="", description="Stripe Price ID for Dominance tier")

    # === Calendar/Meetings ===
    calcom_api_key: str = Field(default="", description="Cal.com API key")
    calendly_api_key: str = Field(default="", description="Calendly API key")

    # === Australian DNCR (Do Not Call Register) ===
    dncr_api_key: str = Field(default="", description="ACMA DNCR API key")
    dncr_api_url: str = Field(
        default="https://api.dncr.gov.au/v1",
        description="DNCR API URL"
    )
    dncr_account_id: str = Field(default="", description="DNCR Account ID")
    dncr_cache_ttl_hours: int = Field(default=24, description="Hours to cache DNCR results")

    # === Web Search (Phase 12B) ===
    serper_api_key: str = Field(default="", description="Serper.dev Google Search API key")

    # === Sentry (Error Tracking) ===
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")
    sentry_auth_token: str = Field(default="", description="Sentry auth token for API access")

    # === Development ===Now let me check the database migrations and the flows that use LinkedIn:6 stepsstart_searchRequest{
  `path`: `C:\\AI\\Agency_OS\\src`,
  `pattern`: `linkedin_engine`,
  `searchType`: `content`
}ResponseStarted content search session: search_6_1768214056107
Pattern: "linkedin_engine"
Path: C:\AI\Agency_OS\src
Status: RUNNING
Runtime: 46ms
Total results: 0


🔄 Search in progress. Use get_more_search_results to get more results.get_more_search_resultsRequest{
  `sessionId`: `search_6_1768214056107`
}ResponseSearch session: search_6_1768214056107
Status: COMPLETED
Runtime: 29s
Total results found: 64 (11 matches)
Showing results 0-63

Results:
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:385 - raise
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:386 - 
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:387 - # === SEND LINKEDIN MESSAGE ===
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:388 - logger.info(f"Sending LinkedIn {message_type} to lead {lead_id} (campaign {campaign.id})")
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:389 - 
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:390 - linkedin_engine
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:391 - linkedin_engine
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:392 - db=db,
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:393 - lead_id=lead_id,
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:394 - campaign_id=campaign.id,
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:395 - content=content,
📄 C:\AI\Agency_OS\src\orchestration\tasks\outreach_tasks.py:396 - seat_id=seat_id,
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:35 - from sqlalchemy.ext.asyncio import AsyncSession
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:36 - 
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:37 - from src.engines.allocator import get_allocator_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:38 - from src.engines.content import get_content_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:39 - from src.engines.email import get_email_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:40 - linkedin_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:41 - from src.engines.mail import get_mail_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:42 - from src.engines.sms import get_sms_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:43 - from src.engines.voice import get_voice_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:44 - from src.integrations.supabase import get_db_session
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:45 - from src.models.activity import Activity
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:371 - Returns:
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:372 - Dict with send result
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:373 - """
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:374 - async with get_db_session() as db:
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:375 - content_engine = get_content_engine()
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:376 - linkedin_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:377 - allocator_engine = get_allocator_engine()
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:378 - 
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:379 - lead_uuid = UUID(lead_id)
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:380 - campaign_uuid = UUID(campaign_id)
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:381 - 
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:408 - "success": False,
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:409 - "error": f"Content generation failed: {content_result.error}",
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:410 - }
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:411 - 
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:412 - # Send connection request
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:413 - linkedin_engine
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:414 - db=db,
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:415 - lead_id=lead_uuid,
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:416 - message=content_result.data["message"],
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:417 - seat_id=resource,
📄 C:\AI\Agency_OS\src\orchestration\flows\outreach_flow.py:418 - )
📄 C:\AI\Agency_OS\src\engines\linkedin.py:530 - db.add(activity)
📄 C:\AI\Agency_OS\src\engines\linkedin.py:531 - await db.commit()
📄 C:\AI\Agency_OS\src\engines\linkedin.py:532 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:533 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:534 - # Singleton instance
📄 C:\AI\Agency_OS\src\engines\linkedin.py:535 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:536 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:537 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:538 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:539 - """Get or create LinkedIn engine instance."""
📄 C:\AI\Agency_OS\src\engines\linkedin.py:540 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:541 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:542 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:543 - linkedin_engine
📄 C:\AI\Agency_OS\src\engines\linkedin.py:544 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:545 - 
📄 C:\AI\Agency_OS\src\engines\linkedin.py:546 - # ============================================
📄 C:\AI\Agency_OS\src\engines\linkedin.py:547 - # VERIFICATION CHECKLIST
📄 C:\AI\Agency_OS\src\engines\linkedin.py:548 - # ============================================

✅ Search completed.Now I have a complete picture. Let me summarize the assessment:

HeyReach → Unipile Migration Complexity Assessment
Overall Difficulty: MEDIUM (3-4 days of focused work)
The good news: HeyReach integration is well-isolated with clean boundaries. The bad news: it touches several critical files.

Files That Need Changes
FileComplexityChanges Requiredsrc/integrations/heyreach.pyReplace entirelyCreate new unipile.py (~200 lines)src/engines/linkedin.pyMediumSwap client import, update method callssrc/services/linkedin_connection_service.pyMediumChange auth flow to hosted auth (simpler!)src/api/routes/linkedin.pyLowAdjust endpoints for hosted auth redirectsrc/models/linkedin_credential.pyLowRename heyreach_* → unipile_* columnssupabase/migrations/031_linkedin_credentials.sqlLowCreate new migration to rename columnssrc/config/settings.pyTrivialheyreach_api_key → unipile_api_key + unipile_dsnsrc/orchestration/flows/outreach_flow.pyLowNo changes needed (uses engine abstraction)src/orchestration/tasks/outreach_tasks.pyLowNo changes needed (uses engine abstraction)tests/conftest.pyMediumUpdate mock fixturestests/test_engines/test_linkedin.pyMediumUpdate mock client

What Makes This EASIER Than Expected

Engine abstraction pattern - The LinkedInEngine wraps HeyReach, so orchestration flows don't need changes
Hosted auth is SIMPLER - Unipile's OAuth-style flow eliminates the 2FA dance
No credentials stored - With hosted auth, you don't store LinkedIn email/password at all!
Same operations - Both support: connection requests, messages, profile data


What Makes This Harder

Database migration - Need to rename columns (heyreach_sender_id → unipile_account_id)
Auth flow change - Current flow stores encrypted credentials; Unipile uses hosted auth redirect
Test mocks - ~4 test files reference HeyReach mocks


Recommended Migration Steps
Phase 1: Foundation (Day 1)

Create src/integrations/unipile.py with new client
Add UNIPILE_API_KEY and UNIPILE_DSN to settings
Create database migration 032 to add unipile_account_id column

Phase 2: Engine Update (Day 2)

Update src/engines/linkedin.py to use UnipileClient
Update src/services/linkedin_connection_service.py for hosted auth
Simplify credential model (can remove encrypted password fields!)

Phase 3: API Routes (Day 3)

Change /linkedin/connect to return hosted auth URL
Add /linkedin/callback webhook endpoint
Remove /linkedin/verify-2fa (no longer needed!)

Phase 4: Testing & Cleanup (Day 4)

Update test fixtures
Run E2E tests
Remove old HeyReach code
Create migration to drop deprecated columns


Key Code Differences
Current HeyReach Flow:
User enters LinkedIn email/password → Store encrypted → Call HeyReach API → Handle 2FA → Store sender_id
New Unipile Flow:
User clicks "Connect LinkedIn" → Redirect to Unipile hosted auth → Webhook callback → Store account_id
This is actually simpler - no credential encryption, no 2FA handling!