# MARKETING LAUNCH PLAN: The Fully Automated "Build in Public" Machine

**Document Type:** Marketing Strategy  
**Owner:** CMO  
**Approved By:** CEO  
**Brand Philosophy:** "Automation expert uses automation to sell automation."

---

## Executive Summary

We will build a fully automated content machine that:
1. Generates AI video updates with scripted narration
2. Auto-posts to LinkedIn, Twitter, YouTube
3. Pulls real metrics from Agency OS dashboard
4. Creates content variations for each platform
5. Runs 24/7 with minimal human intervention

**The Meta-Story:** The campaign itself proves the product philosophy.

---

# PART 1: THE AUTOMATION ARCHITECTURE

## 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTOMATED BUILD IN PUBLIC MACHINE                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   DATA LAYER    │      │  CONTENT GEN    │      │  DISTRIBUTION   │
│                 │      │                 │      │                 │
│ • Agency OS API │      │ • Script Gen    │      │ • LinkedIn API  │
│ • Metrics DB    │      │ • Video Gen     │      │ • Twitter API   │
│ • Milestones    │      │ • Post Gen      │      │ • YouTube API   │
│                 │      │ • Image Gen     │      │ • Email (Resend)│
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                      ┌─────────────────────┐
                      │   ORCHESTRATION     │
                      │                     │
                      │ • Prefect Flows     │
                      │ • Scheduling        │
                      │ • Approval Queue    │
                      │   (if Co-Pilot)     │
                      └─────────────────────┘
```

## 1.2 The Tech Stack

```yaml
automation_stack:
  data_sources:
    agency_os_metrics:
      source: "supabase_api"
      metrics:
        - leads_enriched
        - emails_sent
        - open_rate
        - reply_rate
        - meetings_booked
        - pipeline_value
      refresh: "real_time"
      
    milestones:
      source: "manual_or_triggered"
      events:
        - first_email_sent
        - first_reply
        - first_meeting
        - first_customer
        - 5_customers
        - 10_customers
        - 20_customers_sold_out
        
  content_generation:
    scripts:
      provider: "claude_api"
      model: "claude-sonnet-4-20250514"
      templates: "see_section_2"
      
    video:
      provider: "heygen"  # or Synthesia, D-ID
      avatar: "custom_or_stock"
      voice: "cloned_or_stock"
      resolution: "1080p"
      format: "mp4"
      cost: "$0.10-0.50 per minute"
      
    images:
      provider: "midjourney_or_dalle"
      use_cases:
        - thumbnail_generation
        - chart_screenshots
        - branded_graphics
        
    post_copy:
      provider: "claude_api"
      platforms:
        - linkedin_long_form
        - twitter_thread
        - twitter_single
        - youtube_description
        - email_newsletter
        
  distribution:
    linkedin:
      method: "linkedin_api_or_phantombuster"
      post_types: ["text", "video", "image", "document"]
      scheduling: "buffer_or_native"
      
    twitter:
      method: "twitter_api_v2"
      post_types: ["tweet", "thread", "video"]
      scheduling: "native"
      
    youtube:
      method: "youtube_data_api"
      post_types: ["shorts", "long_form"]
      scheduling: "native"
      
    email:
      method: "resend_api"
      list: "waitlist_subscribers"
      frequency: "weekly"
      
  orchestration:
    provider: "prefect"
    flows:
      - daily_metrics_pull
      - daily_content_generation
      - daily_video_generation
      - scheduled_posting
      - milestone_triggered_content
      
  approval_mode:
    autopilot:
      description: "Full automation, posts without review"
      risk: "medium"
      recommended_for: "after_week_2"
      
    co_pilot:
      description: "Generates content, queues for approval"
      risk: "low"
      recommended_for: "week_1"
      
    manual:
      description: "Generates content, you post manually"
      risk: "lowest"
      recommended_for: "testing"
```

---

# PART 2: CONTENT TEMPLATES & SCRIPTS

## 2.1 Video Script Templates

### Template A: Daily Metrics Update (60-90 seconds)

```yaml
video_template_daily:
  name: "Daily Dashboard Update"
  duration: "60-90 seconds"
  frequency: "daily"
  best_time: "8:00 AM AEST"
  
  script_structure:
    hook: |
      "Day {day_number} of using Agency OS to sell Agency OS.
      Here's what happened in the last 24 hours."
      
    metrics: |
      "We sent {emails_sent_today} emails.
      {opens_today} people opened them — that's a {open_rate}% open rate.
      We got {replies_today} replies, {positive_replies} of them positive.
      {meetings_booked_today} meetings booked.
      Total pipeline is now ${pipeline_value}."
      
    insight: |
      "{insight_of_the_day}"
      # Examples:
      # "Interesting pattern: Tuesday emails are outperforming Monday."
      # "Our subject line 'Quick question' is getting 40% opens."
      # "Dentists are responding 2x better than physios."
      
    cta: |
      "We're filling 20 founding spots at 50% off for life.
      {spots_remaining} spots left.
      Link in bio if you want in."
      
  visual_structure:
    - scene_1: "Avatar talking to camera (hook)"
    - scene_2: "Dashboard screenshot with metrics highlighted"
    - scene_3: "Avatar explaining insight"
    - scene_4: "CTA with waitlist link overlay"
    
  variables_from_api:
    - day_number
    - emails_sent_today
    - opens_today
    - open_rate
    - replies_today
    - positive_replies
    - meetings_booked_today
    - pipeline_value
    - spots_remaining
    - insight_of_the_day  # AI-generated based on data trends
```

### Template B: Weekly Deep Dive (3-5 minutes)

```yaml
video_template_weekly:
  name: "Weekly Deep Dive"
  duration: "3-5 minutes"
  frequency: "weekly (Friday)"
  platform: "youtube_long_form"
  
  script_structure:
    intro: |
      "Week {week_number} of building Agency OS in public.
      This week we {headline_achievement}.
      Let me break down what happened."
      
    section_1_numbers: |
      "First, the numbers.
      This week we reached out to {total_leads_week} potential customers.
      {total_emails_week} emails sent across {active_campaigns} campaigns.
      Our overall open rate was {avg_open_rate}%.
      Reply rate: {reply_rate}%.
      We booked {meetings_week} meetings worth an estimated ${pipeline_added} in pipeline."
      
    section_2_whats_working: |
      "What's working:
      {working_insight_1}
      {working_insight_2}
      {working_insight_3}"
      # AI analyzes data and generates insights
      
    section_3_whats_not: |
      "What's not working:
      {not_working_insight_1}
      We're going to {fix_action} next week."
      
    section_4_next_week: |
      "Next week's plan:
      {next_week_focus}
      I'll report back on how it goes."
      
    cta: |
      "If you're an agency doing outbound manually, this is what we're automating.
      {spots_remaining} founding spots left at 50% off.
      Link in description."
      
  visual_structure:
    - scene_1: "Avatar intro (talking head)"
    - scene_2: "Animated chart showing week-over-week growth"
    - scene_3: "Dashboard walkthrough (screen recording)"
    - scene_4: "Avatar explaining insights"
    - scene_5: "Before/after comparison graphic"
    - scene_6: "CTA with urgency meter (spots remaining)"
```

### Template C: Milestone Celebration (30-60 seconds)

```yaml
video_template_milestone:
  name: "Milestone Announcement"
  duration: "30-60 seconds"
  frequency: "triggered_by_event"
  tone: "excited_but_authentic"
  
  triggers:
    - first_reply
    - first_meeting
    - first_customer
    - 5_customers
    - 10_customers
    - 15_customers
    - sold_out
    
  script_template:
    first_reply: |
      "We got our first reply!
      Day {day_number}. {emails_sent_total} emails sent.
      And someone actually wrote back.
      
      They said: '{reply_snippet}'
      
      This is what we're building. Automated outreach that actually works.
      {spots_remaining} founding spots left."
      
    first_meeting: |
      "First meeting booked! 📅
      
      {days_to_first_meeting} days from first email to first meeting.
      {emails_to_first_meeting} emails sent.
      {lead_name} from {lead_company} wants to chat.
      
      The system works. {spots_remaining} spots left."
      
    first_customer: |
      "We just closed our first customer! 🎉
      
      {customer_name} from {customer_company} is founding customer #1.
      They came in through our own outbound.
      
      The product sells itself — literally.
      
      19 spots remaining."
      
    sold_out: |
      "SOLD OUT. 🔒
      
      20 founding customers in {days_to_sold_out} days.
      All from automated outbound.
      Zero paid ads.
      
      We're now opening the early access waitlist.
      25% off first year for everyone who signed up.
      
      Thank you to everyone who believed early.
      Let's build."
```

### Template D: Educational Content (2-3 minutes)

```yaml
video_template_educational:
  name: "How We Do X"
  duration: "2-3 minutes"
  frequency: "2x per week"
  purpose: "value_first_selling"
  
  topics:
    - "How we get 35%+ email open rates"
    - "The ALS: How we prioritize leads"
    - "Why we don't use polymorphic messaging"
    - "Our email warmup process explained"
    - "How we handle LinkedIn without getting banned"
    - "The 5-minute reply rule"
    - "Why we built multi-channel (not just email)"
    
  script_structure:
    hook: |
      "Most agencies get 10-15% email open rates.
      We're getting {our_open_rate}%.
      Here's exactly how."
      
    problem: |
      "The problem with most cold email:
      {problem_description}"
      
    solution: |
      "What we do differently:
      {solution_step_1}
      {solution_step_2}
      {solution_step_3}"
      
    proof: |
      "Here's our actual data:
      {screenshot_or_metric}"
      
    cta: |
      "This is built into Agency OS.
      You don't have to figure this out yourself.
      {spots_remaining} founding spots left."
```

---

## 2.2 LinkedIn Post Templates

### Daily Post (Auto-Generated)

```yaml
linkedin_daily:
  format: "text_with_metrics"
  length: "150-300 words"
  
  template_variations:
    variation_a: |
      Day {day_number} of using Agency OS to sell Agency OS.
      
      Yesterday's numbers:
      → {emails_sent} emails sent
      → {open_rate}% open rate
      → {replies} replies ({positive_replies} positive)
      → {meetings_booked} meetings booked
      
      Total pipeline: ${pipeline_value}
      
      {insight_of_the_day}
      
      {spots_remaining} founding spots left at 50% off for life.
      
      Comment "INFO" if you want the details.
      
    variation_b: |
      Quick update from the Agency OS experiment:
      
      📧 {emails_sent} emails
      👀 {open_rate}% opens
      💬 {replies} replies
      📅 {meetings_booked} meetings
      
      What's working: {whats_working}
      
      What's not: {whats_not}
      
      Still {spots_remaining} spots at 50% off.
      
      Building in public means sharing the ugly too.
      
    variation_c: |
      The automation is working.
      
      In {day_number} days:
      • {total_emails} emails sent (automated)
      • {total_meetings} meetings booked (automated)
      • {total_customers} customers closed (from our own outbound)
      
      This post? Also automated.
      
      I set up an AI content system that:
      1. Pulls metrics from Agency OS
      2. Generates scripts
      3. Creates videos
      4. Posts everywhere
      
      I haven't manually written a post in {days_since_manual} days.
      
      That's the product philosophy.
      
      {spots_remaining} spots left.
```

### Milestone Post (Triggered)

```yaml
linkedin_milestone:
  format: "celebration_with_proof"
  
  templates:
    first_customer: |
      🎉 First customer signed!
      
      {customer_first_name} from {customer_company} just became founding customer #1.
      
      How they found us:
      → Received our automated cold email
      → Opened it 3 times
      → Replied "tell me more"
      → Booked a demo
      → Signed up
      
      Time from first email to close: {days_to_close} days
      
      The product literally sold itself.
      
      19 founding spots remaining at 50% off for life.
      
      Who's next?
      
    ten_customers: |
      10 founding customers. 🔥
      
      All from automated outbound.
      $0 spent on ads.
      
      Here's the breakdown:
      → {total_emails_sent} emails sent
      → {total_replies} replies
      → {total_meetings} meetings
      → 10 customers
      
      Conversion rate from email to customer: {conversion_rate}%
      
      10 spots left.
      
      This is what Agency OS does.
      Except for your agency, not mine.
      
    sold_out: |
      SOLD OUT 🔒
      
      20 founding customers in {days_to_sold_out} days.
      
      The experiment worked:
      → Built an outbound automation tool
      → Used it to sell itself
      → Closed 20 customers without a single ad
      
      What's next:
      → Early access waitlist is open
      → 25% off first year for waitlist
      → Velocity + Dominance tiers coming Q2
      
      Thank you to everyone who took a chance on us.
      
      Now let's build something great together.
```

---

## 2.3 Twitter Thread Templates

```yaml
twitter_threads:
  weekly_recap:
    format: "numbered_thread"
    length: "8-12 tweets"
    
    structure:
      tweet_1: |
        Week {week_number} of building Agency OS in public.
        
        Here's everything that happened 🧵
        
      tweet_2: |
        THE NUMBERS:
        
        Emails sent: {emails_week}
        Open rate: {open_rate}%
        Replies: {replies_week}
        Meetings: {meetings_week}
        Pipeline: ${pipeline_week}
        
      tweet_3: |
        WHAT WORKED:
        
        {working_insight_1}
        
      tweet_4: |
        {working_insight_2}
        
      tweet_5: |
        WHAT DIDN'T WORK:
        
        {not_working_insight}
        
      tweet_6: |
        THE FIX:
        
        {what_were_changing}
        
      tweet_7: |
        CUSTOMER UPDATE:
        
        {customer_count}/20 founding spots filled
        {spots_remaining} remaining
        
      tweet_8: |
        NEXT WEEK'S FOCUS:
        
        {next_week_plan}
        
      tweet_9: |
        If you're an agency doing outbound manually, this is what we're automating.
        
        50% off for life for founding customers.
        
        Link in bio.
        
      tweet_10: |
        Follow along for daily updates.
        
        RT tweet 1 if you want to see more builds in public like this.
```

---

# PART 3: VIDEO GENERATION PIPELINE

## 3.1 AI Video Tools Comparison

```yaml
video_generation_tools:
  heygen:
    description: "AI avatars with lip-sync"
    pricing: "$24/mo (Creator) - 15 min/mo"
    quality: "high"
    avatar_options: "stock or custom clone"
    voice_options: "stock or voice clone"
    api: "yes"
    best_for: "daily updates, professional feel"
    
  synthesia:
    description: "AI avatars, enterprise focused"
    pricing: "$29/mo (Starter) - 10 min/mo"
    quality: "very high"
    avatar_options: "stock or custom"
    api: "yes (higher tiers)"
    best_for: "polished weekly videos"
    
  d_id:
    description: "Talking photos/avatars"
    pricing: "$5.99/mo (Lite) - 5 min/mo"
    quality: "medium-high"
    api: "yes"
    best_for: "quick social clips"
    
  runway:
    description: "AI video generation"
    pricing: "$15/mo - 125 credits"
    quality: "creative/stylized"
    best_for: "b-roll, effects"
    
  recommended_stack:
    daily_updates: "heygen"
    weekly_deep_dives: "heygen + screen_recording"
    milestone_celebrations: "heygen"
    educational: "heygen + canva_for_graphics"
    
  cost_estimate:
    heygen_creator: "$24/mo"
    estimated_usage: "20-30 min/mo"
    overage: "$6/additional minute"
    total: "~$50-80/mo"
```

## 3.2 Video Generation Flow

```yaml
video_generation_flow:
  trigger: "daily_at_7am_aest"
  
  step_1_data_pull:
    source: "supabase_api"
    query: "get_yesterdays_metrics"
    output:
      - emails_sent_today
      - open_rate
      - replies
      - positive_replies
      - meetings_booked
      - pipeline_value
      - spots_remaining
      
  step_2_insight_generation:
    provider: "claude_api"
    prompt: |
      Based on these metrics from yesterday:
      {metrics_json}
      
      And the trend from the past 7 days:
      {weekly_trend_json}
      
      Generate ONE interesting insight for today's video update.
      Keep it under 30 words.
      Make it specific and data-driven.
      
    output: "insight_of_the_day"
    
  step_3_script_generation:
    provider: "claude_api"
    template: "daily_metrics_update"
    variables:
      - day_number
      - all_metrics
      - insight_of_the_day
      - spots_remaining
    output: "full_script"
    
  step_4_video_generation:
    provider: "heygen_api"
    inputs:
      script: "{full_script}"
      avatar_id: "your_avatar_id"
      voice_id: "your_voice_id"
      background: "office_or_branded"
    output: "video_url"
    
  step_5_thumbnail_generation:
    provider: "canva_api_or_dalle"
    template: "daily_update_thumbnail"
    variables:
      - day_number
      - key_metric: "{meetings_booked} meetings"
    output: "thumbnail_url"
    
  step_6_post_generation:
    provider: "claude_api"
    generate:
      - linkedin_post
      - twitter_thread
      - youtube_description
    output: "all_post_copy"
    
  step_7_distribution:
    linkedin:
      content: "{linkedin_post}"
      video: "{video_url}"
      schedule: "8:00 AM AEST"
      
    twitter:
      content: "{twitter_hook}"
      video: "{video_url}"
      schedule: "8:15 AM AEST"
      
    youtube:
      title: "Day {day_number}: {headline_metric}"
      description: "{youtube_description}"
      video: "{video_url}"
      thumbnail: "{thumbnail_url}"
      schedule: "8:30 AM AEST"
      
  step_8_logging:
    store:
      - content_generated
      - platforms_posted
      - post_urls
      - engagement_metrics_24h_later
```

## 3.3 HeyGen API Implementation

```python
# content_automation/video_generator.py

import httpx
from typing import Optional

class HeyGenVideoGenerator:
    """Generate AI videos using HeyGen API."""
    
    BASE_URL = "https://api.heygen.com/v2"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json"
        }
        
    async def generate_video(
        self,
        script: str,
        avatar_id: str,
        voice_id: str,
        background_url: Optional[str] = None
    ) -> dict:
        """
        Generate a video from script.
        Returns video_id for status polling.
        """
        payload = {
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id
                },
                "background": {
                    "type": "color",
                    "value": "#1a1a2e"  # Dark branded background
                } if not background_url else {
                    "type": "image",
                    "url": background_url
                }
            }],
            "dimension": {
                "width": 1920,
                "height": 1080
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/video/generate",
                json=payload,
                headers=self.headers
            )
            return response.json()
    
    async def get_video_status(self, video_id: str) -> dict:
        """Poll for video generation status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/video_status.get",
                params={"video_id": video_id},
                headers=self.headers
            )
            return response.json()
    
    async def wait_for_video(self, video_id: str, timeout: int = 600) -> str:
        """Wait for video to complete and return URL."""
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            status = await self.get_video_status(video_id)
            
            if status["data"]["status"] == "completed":
                return status["data"]["video_url"]
            
            if status["data"]["status"] == "failed":
                raise Exception(f"Video generation failed: {status}")
            
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Video generation timed out")
            
            await asyncio.sleep(10)  # Poll every 10 seconds
```

---

# PART 4: DISTRIBUTION AUTOMATION

## 4.1 LinkedIn Automation

```yaml
linkedin_automation:
  method: "linkedin_api_via_oauth"
  
  # Note: LinkedIn API is restrictive. Alternatives:
  alternative_methods:
    buffer:
      description: "Schedule posts via Buffer API"
      cost: "$6/mo"
      video_support: "yes"
      
    zapier:
      description: "Trigger posts via Zapier"
      cost: "$20/mo"
      video_support: "limited"
      
    phantombuster:
      description: "Automation via browser extension"
      cost: "$59/mo"
      risk: "medium (ToS)"
      
  recommended: "buffer_api"
  
  implementation:
    schedule_post:
      time: "8:00 AM AEST"
      days: ["monday", "tuesday", "wednesday", "thursday", "friday"]
      
    post_types:
      daily: "video + caption"
      milestone: "video + caption + hashtags"
      educational: "video + carousel"
```

## 4.2 Twitter Automation

```python
# content_automation/twitter_poster.py

import tweepy
from typing import List

class TwitterAutomation:
    """Post content to Twitter/X automatically."""
    
    def __init__(self, credentials: dict):
        self.client = tweepy.Client(
            consumer_key=credentials["api_key"],
            consumer_secret=credentials["api_secret"],
            access_token=credentials["access_token"],
            access_token_secret=credentials["access_token_secret"]
        )
        
    async def post_tweet(self, content: str, video_path: str = None) -> dict:
        """Post a single tweet, optionally with video."""
        
        media_id = None
        if video_path:
            # Upload video first
            media = self.client.media_upload(video_path)
            media_id = media.media_id
            
        response = self.client.create_tweet(
            text=content,
            media_ids=[media_id] if media_id else None
        )
        
        return {"tweet_id": response.data["id"]}
    
    async def post_thread(self, tweets: List[str]) -> List[dict]:
        """Post a thread of tweets."""
        
        results = []
        previous_tweet_id = None
        
        for tweet in tweets:
            response = self.client.create_tweet(
                text=tweet,
                in_reply_to_tweet_id=previous_tweet_id
            )
            previous_tweet_id = response.data["id"]
            results.append({"tweet_id": previous_tweet_id})
            
        return results
```

## 4.3 YouTube Automation

```python
# content_automation/youtube_poster.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class YouTubeAutomation:
    """Upload videos to YouTube automatically."""
    
    def __init__(self, credentials: Credentials):
        self.youtube = build("youtube", "v3", credentials=credentials)
        
    async def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        thumbnail_path: str = None,
        privacy: str = "public"
    ) -> dict:
        """Upload video to YouTube."""
        
        request_body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        response = self.youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media
        ).execute()
        
        video_id = response["id"]
        
        # Upload thumbnail if provided
        if thumbnail_path:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            
        return {"video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}
```

---

# PART 5: ORCHESTRATION (PREFECT FLOWS)

## 5.1 Daily Content Flow

```python
# flows/content_automation.py

from prefect import flow, task
from datetime import datetime

@task
async def pull_metrics():
    """Pull yesterday's metrics from Agency OS."""
    from integrations.supabase import get_daily_metrics
    return await get_daily_metrics(date=datetime.now().date() - timedelta(days=1))

@task
async def generate_insight(metrics: dict):
    """Generate AI insight from metrics."""
    from integrations.claude import generate_content
    
    prompt = f"""
    Based on these metrics: {metrics}
    Generate ONE interesting insight under 30 words.
    Make it specific and data-driven.
    """
    
    return await generate_content(prompt)

@task
async def generate_script(metrics: dict, insight: str, day_number: int):
    """Generate video script."""
    from integrations.claude import generate_content
    from templates.video_scripts import DAILY_UPDATE_TEMPLATE
    
    return DAILY_UPDATE_TEMPLATE.format(
        day_number=day_number,
        emails_sent=metrics["emails_sent"],
        open_rate=metrics["open_rate"],
        replies=metrics["replies"],
        positive_replies=metrics["positive_replies"],
        meetings_booked=metrics["meetings_booked"],
        pipeline_value=metrics["pipeline_value"],
        spots_remaining=metrics["spots_remaining"],
        insight=insight
    )

@task
async def generate_video(script: str):
    """Generate video using HeyGen."""
    from integrations.heygen import HeyGenVideoGenerator
    
    generator = HeyGenVideoGenerator(api_key=HEYGEN_API_KEY)
    video_id = await generator.generate_video(
        script=script,
        avatar_id=AVATAR_ID,
        voice_id=VOICE_ID
    )
    
    return await generator.wait_for_video(video_id)

@task
async def generate_posts(metrics: dict, insight: str, video_url: str):
    """Generate social media posts."""
    from integrations.claude import generate_content
    
    linkedin = await generate_content(
        template="linkedin_daily",
        variables={**metrics, "insight": insight}
    )
    
    twitter = await generate_content(
        template="twitter_daily",
        variables={**metrics, "insight": insight}
    )
    
    return {"linkedin": linkedin, "twitter": twitter}

@task
async def distribute_content(video_url: str, posts: dict):
    """Post to all platforms."""
    from integrations.linkedin import post_to_linkedin
    from integrations.twitter import post_to_twitter
    from integrations.youtube import upload_to_youtube
    
    results = {}
    
    results["linkedin"] = await post_to_linkedin(
        content=posts["linkedin"],
        video_url=video_url
    )
    
    results["twitter"] = await post_to_twitter(
        content=posts["twitter"],
        video_url=video_url
    )
    
    results["youtube"] = await upload_to_youtube(
        video_url=video_url,
        title=f"Day {DAY_NUMBER}: Agency OS Update",
        description=posts["linkedin"]
    )
    
    return results

@flow(name="daily-content-automation")
async def daily_content_flow():
    """
    Full daily content automation flow.
    Runs at 7 AM AEST.
    """
    
    # Pull data
    metrics = await pull_metrics()
    
    # Generate content
    insight = await generate_insight(metrics)
    script = await generate_script(metrics, insight, get_day_number())
    video_url = await generate_video(script)
    posts = await generate_posts(metrics, insight, video_url)
    
    # Distribute
    results = await distribute_content(video_url, posts)
    
    # Log results
    await log_content_run(metrics, posts, results)
    
    return results
```

## 5.2 Milestone Trigger Flow

```python
@flow(name="milestone-content-trigger")
async def milestone_content_flow(milestone_type: str, milestone_data: dict):
    """
    Triggered when a milestone is hit.
    E.g., first customer, 10 customers, sold out.
    """
    
    # Generate milestone-specific script
    script = await generate_milestone_script(milestone_type, milestone_data)
    
    # Generate video
    video_url = await generate_video(script)
    
    # Generate celebratory posts
    posts = await generate_milestone_posts(milestone_type, milestone_data, video_url)
    
    # Distribute IMMEDIATELY (milestones are time-sensitive)
    results = await distribute_content(video_url, posts)
    
    # Send notification to founder
    await send_notification(
        title=f"🎉 Milestone content posted: {milestone_type}",
        body=f"Video: {video_url}"
    )
    
    return results
```

---

# PART 6: COST ANALYSIS

## 6.1 Monthly Automation Costs

```yaml
automation_costs:
  content_generation:
    claude_api:
      usage: "~100,000 tokens/month"
      cost: "$3-5"
      
    heygen:
      plan: "Creator ($24/mo)"
      overage: "~$20-30"
      total: "$45-55"
      
  distribution:
    buffer:
      plan: "Essentials ($6/mo)"
      total: "$6"
      
    twitter_api:
      plan: "Basic ($100/mo)"  # Or free tier if <1500 tweets
      total: "$0-100"
      
  infrastructure:
    prefect_cloud:
      plan: "Free tier"
      total: "$0"
      
  total_monthly:
    low_estimate: "$55"
    high_estimate: "$165"
    
  comparison:
    manual_content_creation: "20+ hours/month"
    hourly_value: "$100/hr"
    manual_cost: "$2,000+"
    automation_savings: "90%+"
```

## 6.2 ROI Analysis

```yaml
roi_analysis:
  investment:
    setup_time: "20 hours"
    monthly_cost: "$100"
    monthly_maintenance: "2 hours"
    
  returns:
    content_pieces_per_month: 60+
    reach_multiplier: "3x platforms"
    consistency: "100% (never miss a day)"
    brand_building: "automation expert positioning"
    
  meta_benefit: |
    "The automation itself IS the marketing.
    Every post proves the philosophy.
    The medium is the message."
```

---

# PART 7: APPROVAL MODES

## 7.1 Mode Configuration

```yaml
content_approval_modes:
  autopilot:
    description: "Full automation, posts without human review"
    flow:
      - generate_content
      - post_immediately
      - notify_after_posting
    recommended_after: "week_2 (once templates are dialed in)"
    
  co_pilot:
    description: "Generates content, queues for approval"
    flow:
      - generate_content
      - add_to_approval_queue
      - notify_for_review
      - wait_for_approval_or_timeout
      - post_if_approved
    timeout: "2 hours (then auto-post)"
    recommended_for: "week_1, milestone content"
    
  manual:
    description: "Generates content, you post manually"
    flow:
      - generate_content
      - send_to_dashboard
      - wait_for_manual_action
    recommended_for: "initial testing only"
```

## 7.2 Approval Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  📝 Content Approval Queue                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ⏳ PENDING APPROVAL (Auto-posts in 1h 47m)                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Daily Update - Day 14                                       ││
│  │ Video: [Preview] Script: [View]                             ││
│  │                                                             ││
│  │ LinkedIn Post:                                              ││
│  │ "Day 14 of using Agency OS to sell Agency OS..."           ││
│  │                                                             ││
│  │ [✓ Approve All]  [Edit]  [Skip Today]                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ✅ POSTED TODAY                                                │
│  └── Twitter thread (8:15 AM) — 12 likes, 3 retweets           │
│                                                                 │
│  📊 CONTENT MODE: Co-Pilot                                      │
│  [Switch to Autopilot]                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

# PART 8: THE META-NARRATIVE

## 8.1 The Story We're Telling

```yaml
brand_narrative:
  chapter_1_the_problem:
    week: "1-2"
    story: |
      "I'm an automation expert who was doing outbound manually.
      The irony wasn't lost on me.
      So I built something to fix it."
      
  chapter_2_the_experiment:
    week: "3-4"
    story: |
      "I'm using my outbound tool to sell my outbound tool.
      Every email you get from me? Automated.
      Every follow-up? Automated.
      Let me show you the numbers."
      
  chapter_3_the_proof:
    week: "5-6"
    story: |
      "First customer came through automated outbound.
      Then the second. Then the third.
      The product is selling itself."
      
  chapter_4_the_meta:
    week: "7-8"
    story: |
      "Now I've automated the content too.
      This video? AI-generated.
      This post? AI-written.
      I haven't manually created content in weeks.
      That's the philosophy: automate everything."
      
  chapter_5_the_close:
    week: "9-10"
    story: |
      "20 founding customers in 60 days.
      Zero paid ads.
      100% automated.
      If you're an agency, this is what I'll do for you."
```

## 8.2 The Proof Stack

```yaml
proof_elements:
  show_dont_tell:
    - dashboard_screenshots: "real metrics, daily"
    - video_of_system: "show the automation running"
    - customer_testimonials: "as they come in"
    - email_examples: "actual messages sent"
    
  transparency:
    - share_failures: "what's not working"
    - share_costs: "what we're spending"
    - share_learnings: "what we'd do differently"
    
  meta_proof:
    - announce_when_content_is_automated: "this post was AI-generated"
    - show_the_content_pipeline: "here's how this video was made"
    - timestamp_automation: "generated at 6:47 AM while I slept"
```

---

# SIGN-OFF

## Additions to Previous Approvals

| # | Addition | Decision |
|---|----------|----------|
| 22 | AI Video Generation (HeyGen) | [ ] YES  [ ] NO  [ ] MODIFY |
| 23 | Automated Daily Content Pipeline | [ ] YES  [ ] NO  [ ] MODIFY |
| 24 | Three Content Modes (Autopilot/Co-Pilot/Manual) | [ ] YES  [ ] NO  [ ] MODIFY |
| 25 | Updated Waitlist (50% × lifetime × 20 spots) | [ ] YES  [ ] NO  [ ] MODIFY |
| 26 | Dogfooding + Meta-Narrative Strategy | [ ] YES  [ ] NO  [ ] MODIFY |
| 27 | Content Distribution Stack (Buffer + Twitter API + YouTube) | [ ] YES  [ ] NO  [ ] MODIFY |
| 28 | $55-165/mo Content Automation Budget | [ ] YES  [ ] NO  [ ] MODIFY |

---

**CEO Signature:** _________________________

**Date:** _________________________

---

**END OF MARKETING LAUNCH PLAN**
