# File Structure — Agency OS

**Last Updated:** January 5, 2026

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
│   ├── architecture/             # System design docs
│   │   ├── DECISIONS.md          # Technology choices (LOCKED)
│   │   ├── FILE_STRUCTURE.md     # This file
│   │   ├── IMPORT_HIERARCHY.md   # Layer rules (ENFORCED)
│   │   └── RULES.md              # Claude Code rules
│   ├── phases/                   # Phase specifications (22 files)
│   │   ├── PHASE_INDEX.md        # Master index
│   │   └── PHASE_01 through PHASE_21
│   ├── specs/                    # Component specifications
│   │   ├── database/             # Schema definitions (7 files)
│   │   ├── engines/              # Engine specs (12 files)
│   │   ├── integrations/         # API wrapper specs (18 files)
│   │   ├── phase16/              # Conversion Intelligence
│   │   └── phase17/              # Launch Prerequisites
│   ├── audits/                   # QA audits
│   ├── finance/                  # P&L projections
│   ├── marketing/                # Landing pages, campaigns
│   ├── manuals/                  # User/admin manuals
│   ├── progress/                 # Build tracking
│   ├── research/                 # Competitive analysis
│   └── screenshots/              # UI screenshots
├── reference/
│   ├── MCP_REQUIREMENTS.md
│   ├── API_CREDENTIALS_CHECKLIST.md
│   └── *_old.md                  # Archived specs
├── scripts/
│   ├── dev_tunnel.sh
│   ├── update_webhook_urls.py
│   └── v0-generate.ts            # v0.dev helper
├── prompts/
│   └── PHASE_21_KICKOFF.md       # Claude Code prompts
├── skills/
│   ├── SKILL_INDEX.md
│   ├── agents/                   # Agent skills
│   ├── campaign/                 # Campaign skills
│   ├── conversion/               # Conversion skills
│   ├── frontend/                 # UI/Frontend skills
│   └── testing/                  # Testing skills
├── src/                          # Backend source
├── frontend/                     # Next.js frontend
├── supabase/                     # Database migrations
├── tests/                        # Test suite
├── .claude/                      # Claude agent configs
│
├── PROJECT_BLUEPRINT.md          # SLIM: Core decisions only
├── PROJECT_BLUEPRINT_FULL_ARCHIVE.md  # Original full blueprint
├── PROGRESS.md                   # Task tracking
├── CLAUDE.md                     # Claude instructions
├── README.md
├── requirements.txt
├── Dockerfile
├── Dockerfile.prefect
├── docker-compose.yml
├── railway.toml
├── vercel.json
└── prefect.yaml
```

---

## Source Structure (`src/`)

```
src/
├── __init__.py
├── exceptions.py                 # Custom exceptions
├── api/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app
│   ├── dependencies.py           # Auth, DB deps
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       ├── campaigns.py
│       ├── leads.py
│       ├── webhooks.py
│       ├── webhooks_outbound.py
│       ├── reports.py
│       ├── onboarding.py
│       └── patterns.py
├── config/
│   ├── __init__.py
│   └── settings.py               # Pydantic settings
├── models/                       # LAYER 1 (Bottom)
│   ├── __init__.py
│   ├── base.py                   # SoftDeleteMixin, UUIDv7
│   ├── client.py
│   ├── user.py
│   ├── membership.py
│   ├── campaign.py
│   ├── lead.py
│   ├── activity.py
│   └── conversion_patterns.py
├── integrations/                 # LAYER 2
│   ├── __init__.py
│   ├── supabase.py
│   ├── redis.py
│   ├── apollo.py
│   ├── apify.py
│   ├── clay.py
│   ├── resend.py
│   ├── postmark.py
│   ├── twilio.py
│   ├── heyreach.py
│   ├── vapi.py
│   ├── elevenlabs.py
│   ├── clicksend.py
│   ├── dataforseo.py
│   ├── infraforge.py
│   ├── smartlead.py
│   └── anthropic.py
├── engines/                      # LAYER 3
│   ├── __init__.py
│   ├── base.py
│   ├── scout.py
│   ├── scorer.py
│   ├── allocator.py
│   ├── email.py
│   ├── sms.py
│   ├── linkedin.py
│   ├── voice.py
│   ├── mail.py
│   ├── closer.py
│   ├── content.py
│   ├── reporter.py
│   ├── icp_scraper.py
│   ├── email_infrastructure.py
│   └── content_utils.py
├── algorithms/                   # Statistical learning
│   ├── __init__.py
│   ├── who_detector.py
│   ├── what_detector.py
│   ├── when_detector.py
│   └── how_detector.py
├── intelligence/                 # Platform learning
│   ├── __init__.py
│   ├── platform_priors.py
│   ├── platform_aggregator.py
│   └── platform_weight_optimizer.py
├── orchestration/                # LAYER 4 (Top)
│   ├── __init__.py
│   ├── worker.py
│   ├── flows/
│   │   ├── __init__.py
│   │   ├── campaign_flow.py
│   │   ├── enrichment_flow.py
│   │   ├── outreach_flow.py
│   │   ├── reply_recovery_flow.py
│   │   ├── onboarding_flow.py
│   │   ├── pattern_learning_flow.py
│   │   ├── pattern_health_flow.py
│   │   ├── pattern_backfill_flow.py
│   │   ├── email_provisioning_flow.py
│   │   └── platform_learning_flow.py
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── enrichment_tasks.py
│   │   ├── scoring_tasks.py
│   │   ├── outreach_tasks.py
│   │   └── reply_tasks.py
│   └── schedules/
│       ├── __init__.py
│       └── scheduled_jobs.py
└── agents/
    ├── __init__.py
    ├── base_agent.py
    ├── cmo_agent.py
    ├── content_agent.py
    ├── reply_agent.py
    ├── icp_discovery_agent.py
    └── skills/
        ├── __init__.py
        ├── base_skill.py
        ├── website_parser.py
        ├── service_extractor.py
        ├── value_prop_extractor.py
        ├── portfolio_extractor.py
        ├── industry_classifier.py
        ├── company_size_estimator.py
        ├── icp_deriver.py
        ├── als_weight_suggester.py
        ├── messaging_generator.py
        └── sequence_builder.py
```

---

## Frontend Structure (`frontend/`)

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── signup/
│   ├── dashboard/
│   │   ├── page.tsx
│   │   ├── campaigns/
│   │   ├── leads/
│   │   ├── reports/
│   │   └── settings/
│   ├── admin/
│   │   ├── page.tsx
│   │   ├── clients/
│   │   ├── revenue/
│   │   ├── system/
│   │   └── email-health/
│   ├── onboarding/
│   └── page.tsx                  # Landing page
├── components/
│   ├── ui/                       # Shadcn components
│   ├── layout/
│   ├── landing/                  # Landing page components
│   ├── dashboard/                # Dashboard components
│   ├── admin/                    # Admin components
│   └── campaigns/
├── lib/
│   ├── supabase.ts
│   └── utils.ts
├── hooks/
├── styles/
├── public/
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

---

## Database Migrations (`supabase/migrations/`)

```
supabase/migrations/
├── 001_foundation.sql
├── 002_clients_users_memberships.sql
├── 003_campaigns.sql
├── 004_leads_suppression.sql
├── 005_activities.sql
├── 006_permission_modes.sql
├── 007_webhook_configs.sql
├── 008_audit_logs.sql
├── 009_rls_policies.sql
├── 010_platform_admin.sql
├── 011_email_template.sql
├── 012_client_icp_profile.sql
├── 013_replies_meetings.sql
├── 014_conversion_intelligence.sql
├── 015_dataforseo_cache.sql
├── 016_credits_usage.sql
├── 017_email_infrastructure.sql
└── 018_platform_intelligence.sql
```
