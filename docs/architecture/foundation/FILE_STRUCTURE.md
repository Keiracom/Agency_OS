# File Structure — Agency OS

**Last Updated:** January 22, 2026

---

## Root Directory

```
C:\AI\Agency_OS\
├── config/
│   ├── .env                      # Master secrets (all credentials)
│   ├── .env.example              # Template for new setups
│   ├── RAILWAY_ENV_VARS.txt
│   └── VERCEL_ENV_VARS.txt
├── docs/
│   ├── architecture/             # System design docs (7 subfolders)
│   │   ├── ARCHITECTURE_INDEX.md # Master navigation
│   │   ├── TODO.md               # Gaps & priorities (SINGLE SOURCE)
│   │   ├── foundation/           # Core rules (LOCKED)
│   │   ├── business/             # Tiers, scoring, campaigns
│   │   ├── distribution/         # Channel specs
│   │   ├── flows/                # Data pipelines
│   │   ├── content/              # SDK, Smart Prompts
│   │   ├── process/              # Dev workflow
│   │   └── frontend/             # UI architecture
│   ├── phases/                   # Phase specifications
│   │   └── PHASE_INDEX.md        # Master index
│   ├── specs/                    # Component specifications
│   │   ├── database/             # Schema definitions
│   │   ├── engines/              # Engine specs
│   │   └── integrations/         # API wrapper specs
│   └── e2e/                      # E2E testing system
├── scripts/
│   ├── dev_tunnel.sh
│   └── update_webhook_urls.py
├── skills/
│   ├── SKILL_INDEX.md
│   └── [category folders]
├── src/                          # Backend source (176+ files)
├── frontend/                     # Next.js frontend
├── supabase/                     # Database migrations
├── tests/                        # Test suite
│
├── PROJECT_BLUEPRINT.md          # Slim overview
├── PROGRESS.md                   # Task tracking
├── CLAUDE.md                     # Claude instructions
├── requirements.txt
├── Dockerfile
├── Dockerfile.prefect
├── railway.toml
└── prefect.yaml
```

---

## Source Structure (`src/`)

### Layer 1: Models (20 files)

```
src/models/
├── __init__.py
├── base.py                   # SoftDeleteMixin, UUIDv7, enums
├── user.py                   # User accounts
├── client.py                 # Client organizations
├── membership.py             # User-client relationships
├── campaign.py               # Campaigns, sequences, templates
├── lead.py                   # Leads with SDK fields
├── lead_pool.py              # Platform lead repository
├── activity.py               # Outreach activities
├── conversion_patterns.py    # CIS pattern storage
├── client_intelligence.py    # Proof points, testimonials
├── client_persona.py         # Client personas
├── resource_pool.py          # Shared resources
├── linkedin_credential.py    # LinkedIn auth
├── linkedin_seat.py          # LinkedIn seats
├── linkedin_connection.py    # Connection tracking
├── social_profile.py         # Social profiles
├── lead_social_post.py       # Social posts
├── url_validation.py         # URL validation results
└── sdk_usage_log.py          # SDK cost tracking
```

### Layer 2: Integrations (22 files)

```
src/integrations/
├── __init__.py
├── supabase.py               # Database connection
├── redis.py                  # Cache (not task queues)
├── anthropic.py              # Claude API
├── sdk_brain.py              # SDK orchestration
│
├── # Enrichment
├── apollo.py                 # Apollo People API
├── apify.py                  # Web scraping
├── clay.py                   # Data enrichment
├── serper.py                 # Google search
├── dataforseo.py             # SEO data
│
├── # Email
├── salesforge.py             # Primary email (multi-mailbox)
├── resend.py                 # Transactional email
├── postmark.py               # Backup email
│
├── # SMS & Voice
├── clicksend.py              # SMS (Australia)
├── twilio.py                 # Voice (via Vapi)
├── vapi.py                   # Voice AI orchestration
├── elevenlabs.py             # Text-to-speech
├── dncr.py                   # Do Not Call Register
│
├── # LinkedIn
├── unipile.py                # LinkedIn API (current)
├── heyreach.py               # LinkedIn (deprecated)
│
├── # Scraping
├── camoufox_scraper.py       # Anti-detection browser
│
└── sentry_utils.py           # Error tracking
```

### Layer 3: Engines (20 files)

```
src/engines/
├── __init__.py
├── base.py                   # EngineResult, OutreachEngine base
│
├── # Enrichment & Scoring
├── scout.py                  # Lead enrichment waterfall
├── scorer.py                 # ALS scoring
├── allocator.py              # Channel allocation
│
├── # Outreach Channels
├── email.py                  # Email via Salesforge
├── sms.py                    # SMS via ClickSend
├── voice.py                  # Voice via Vapi
├── linkedin.py               # LinkedIn via Unipile
├── mail.py                   # Direct mail (spec only)
│
├── # Content Generation
├── content.py                # Email/SMS/LinkedIn content
├── smart_prompts.py          # Context builders, templates
├── content_utils.py          # Content snapshots
│
├── # Reply & Intelligence
├── closer.py                 # Reply handling
├── client_intelligence.py    # Proof point extraction
├── campaign_suggester.py     # AI campaign suggestions
│
├── # Utilities
├── icp_scraper.py            # Website scraping for ICP
├── url_validator.py          # URL validation waterfall
├── timing.py                 # Humanized timing
└── reporter.py               # Metrics & analytics
```

### Layer 3: Detectors (8 files)

```
src/detectors/
├── __init__.py
├── base.py                   # AbstractDetector base
├── who_detector.py           # Lead attributes that convert
├── what_detector.py          # Content patterns that convert
├── when_detector.py          # Timing patterns that convert
├── how_detector.py           # Channel effectiveness
├── funnel_detector.py        # Downstream outcomes
└── weight_optimizer.py       # ALS weight optimization
```

### Layer 3: Services (22 files)

```
src/services/
├── __init__.py
│
├── # Lead Pool
├── lead_pool_service.py      # Pool CRUD operations
├── lead_allocator_service.py # Lead allocation to campaigns
│
├── # Validation
├── jit_validator.py          # Just-in-time validation
├── suppression_service.py    # Suppression list checks
│
├── # Email
├── domain_health_service.py  # Domain reputation
├── domain_capacity_service.py # Send capacity
├── email_events_service.py   # Open/click tracking
├── thread_service.py         # Email threading
│
├── # Reply & Conversation
├── reply_analyzer.py         # Sentiment analysis
├── conversation_analytics_service.py
│
├── # CRM & Meetings
├── crm_push_service.py       # CRM sync
├── meeting_service.py        # Meeting capture
├── deal_service.py           # Deal pipeline
├── customer_import_service.py # Customer data import
├── buyer_signal_service.py   # Buyer signals
│
├── # LinkedIn
├── linkedin_connection_service.py
│
├── # Resources
├── resource_assignment_service.py
├── sequence_generator_service.py
├── timezone_service.py
│
├── # Cost Control
├── send_limiter.py           # AI spend limiter
└── sdk_usage_service.py      # SDK cost tracking
```

### Layer 4: Orchestration (19 files)

```
src/orchestration/
├── __init__.py
├── worker.py                 # Prefect worker entry
│
├── flows/                    # Prefect flows (15 files)
│   ├── __init__.py
│   ├── onboarding_flow.py    # ICP extraction
│   ├── post_onboarding_flow.py # Resource assignment
│   ├── pool_population_flow.py # Lead sourcing
│   ├── pool_assignment_flow.py # Lead allocation
│   ├── enrichment_flow.py    # Campaign enrichment
│   ├── lead_enrichment_flow.py # Pool lead enrichment
│   ├── stale_lead_refresh_flow.py # Data freshness
│   ├── outreach_flow.py      # Multi-channel execution
│   ├── reply_recovery_flow.py # Reply polling
│   ├── campaign_flow.py      # Campaign activation
│   ├── pattern_learning_flow.py # CIS learning
│   ├── pattern_backfill_flow.py # Historical patterns
│   ├── intelligence_flow.py  # Hot lead research
│   └── credit_reset_flow.py  # Monthly credit reset
│
├── tasks/                    # Reusable tasks (5 files)
│   ├── __init__.py
│   ├── enrichment_tasks.py
│   ├── scoring_tasks.py
│   ├── outreach_tasks.py
│   └── reply_tasks.py
│
└── schedules/
    ├── __init__.py
    └── scheduled_jobs.py     # Cron schedules
```

### SDK Agents (7 files)

```
src/agents/sdk_agents/
├── __init__.py               # Public exports
├── sdk_eligibility.py        # Gate functions
├── sdk_tools.py              # Web search/fetch tools
├── enrichment_agent.py       # Deep research agent
├── email_agent.py            # Personalized email agent
├── voice_kb_agent.py         # Voice knowledge base
└── icp_agent.py              # ICP extraction agent
```

### API Routes (17 files)

```
src/api/
├── __init__.py
├── main.py                   # FastAPI app
├── dependencies.py           # Auth, DB deps
│
└── routes/
    ├── __init__.py
    ├── health.py             # Health checks
    ├── admin.py              # Platform admin (23+ endpoints)
    ├── onboarding.py         # ICP extraction
    ├── campaigns.py          # Campaign CRUD
    ├── leads.py              # Lead CRUD
    ├── pool.py               # Lead pool operations
    ├── linkedin.py           # LinkedIn operations
    ├── reports.py            # Analytics
    ├── patterns.py           # CIS patterns
    ├── replies.py            # Reply inbox
    ├── meetings.py           # Meeting management
    ├── crm.py                # CRM integration
    ├── customers.py          # Customer data
    ├── webhooks.py           # Inbound webhooks
    ├── webhooks_outbound.py  # Outbound webhook config
    └── campaign_generation.py # AI campaign generation
```

### Config (2 files)

```
src/config/
├── __init__.py
├── settings.py               # Pydantic settings
└── tiers.py                  # Tier definitions
```

---

## Frontend Structure (`frontend/`)

```
frontend/
├── app/
│   ├── (auth)/               # Auth pages
│   │   ├── login/
│   │   └── signup/
│   ├── (marketing)/          # Public pages
│   │   ├── pricing/
│   │   └── features/
│   ├── dashboard/            # Client workspace (11 pages)
│   │   ├── page.tsx          # Main dashboard
│   │   ├── campaigns/
│   │   ├── leads/
│   │   ├── reports/
│   │   ├── replies/
│   │   ├── meetings/
│   │   └── settings/
│   ├── admin/                # Platform admin (21 pages)
│   │   ├── page.tsx          # Command center
│   │   ├── clients/
│   │   ├── costs/
│   │   ├── email-health/
│   │   ├── prefect/
│   │   ├── linkedin/
│   │   └── patterns/
│   ├── onboarding/           # Onboarding wizard (4 steps)
│   └── page.tsx              # Landing page
│
├── components/
│   ├── ui/                   # Shadcn components (20+)
│   ├── layout/               # Shell, sidebar, nav
│   ├── dashboard/            # Dashboard components
│   ├── admin/                # Admin components
│   └── campaigns/            # Campaign components
│
├── hooks/                    # React Query hooks (11 files)
├── lib/
│   ├── api/                  # API client modules (9 files)
│   ├── supabase.ts
│   └── utils.ts
│
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

---

## Database Migrations (`supabase/migrations/`)

41 migration files:

```
001_foundation.sql            # UUID, timestamps
002_clients_users_memberships.sql
003_campaigns.sql
004_leads_suppression.sql
005_activities.sql
006_permission_modes.sql
007_webhook_configs.sql
008_audit_logs.sql
009_rls_policies.sql
010_platform_admin.sql
011_fix_user_insert_policy.sql
012_client_icp_profile.sql
013_campaign_templates.sql
014_conversion_intelligence.sql
015_founding_spots.sql
016_auto_provision_client.sql
017_fix_trigger_schema.sql
018_sdk_usage_log.sql
021_deep_research.sql
024_lead_pool.sql
025_content_tracking.sql
026_email_engagement.sql
027_conversation_threads.sql
028_downstream_outcomes.sql
029_crm_push.sql
030_customer_import.sql
031_linkedin_credentials.sql
032_lead_enrichment_fields.sql
033_unipile_migration.sql
034_linkedin_timing.sql
035_sdk_enrichment_fields.sql
036_client_intelligence.sql
037_lead_pool_client_ownership.sql
038_campaign_allocation.sql
039_drop_orphaned_suppression_tables.sql
040_drop_ab_testing.sql
041_resource_pool.sql
042_client_personas.sql
043_linkedin_seats.sql
044_domain_health.sql
045_auto_sequences.sql
```

**Note:** Migrations 018-020, 022-023 were added out of sequence.

---

## File Count Summary

| Area | Files |
|------|-------|
| Models | 20 |
| Integrations | 22 |
| Engines | 20 |
| Detectors | 8 |
| Services | 22 |
| Orchestration | 19 |
| SDK Agents | 7 |
| API Routes | 17 |
| **Total src/** | **135+** |
| Frontend pages | 42 |
| Frontend components | 61 |
| Migrations | 41 |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
