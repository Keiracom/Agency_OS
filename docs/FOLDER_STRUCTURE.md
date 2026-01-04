# Agency OS - Folder Structure

> Quick reference for navigating the codebase

---

## Root Directory

```
C:\AI\Agency_OS\
│
├── CLAUDE.md              # Claude Code instructions
├── PROJECT_BLUEPRINT.md   # Master architecture document
├── PROGRESS.md            # Build progress tracker
├── README.md              # GitHub landing page
├── DEPLOYMENT.md          # Deployment guide
├── DEPLOYMENT_ISSUES.md   # Troubleshooting guide
│
├── Dockerfile             # API service container
├── Dockerfile.prefect     # Worker/Prefect container
├── docker-compose.yml     # Local development
├── prefect.yaml           # Prefect configuration
├── railway.toml           # Railway deployment
├── vercel.json            # Vercel deployment
├── requirements.txt       # Python dependencies
├── package.json           # Root Node dependencies
│
├── .env                   # Local environment (gitignored)
├── .gitignore
└── .railwayignore
```

---

## Source Code (`src/`)

```
src/
├── __init__.py
├── exceptions.py          # Custom exceptions
│
├── config/                # App configuration
│   └── settings.py        # Pydantic settings
│
├── models/                # LAYER 1 - Data models
│   ├── base.py            # Base model, enums
│   ├── client.py          # Client/tenant
│   ├── user.py            # User profile
│   ├── membership.py      # User-Client link
│   ├── campaign.py        # Campaigns
│   ├── lead.py            # Leads + ALS
│   ├── activity.py        # Activity log
│   └── conversion_patterns.py  # Phase 16
│
├── integrations/          # LAYER 2 - External APIs
│   ├── supabase.py        # Database
│   ├── redis.py           # Cache + rate limits
│   ├── anthropic.py       # Claude AI
│   ├── apollo.py          # Lead enrichment
│   ├── apify.py           # Web scraping
│   ├── clay.py            # Premium enrichment
│   ├── resend.py          # Email sending
│   ├── postmark.py        # Inbound email
│   ├── twilio.py          # SMS
│   ├── heyreach.py        # LinkedIn
│   ├── synthflow.py       # Voice AI
│   ├── lob.py             # Direct mail
│   └── serper.py          # Web search
│
├── engines/               # LAYER 3 - Business logic
│   ├── base.py            # Base engine class
│   ├── scout.py           # Data enrichment
│   ├── scorer.py          # ALS scoring
│   ├── allocator.py       # Channel allocation
│   ├── email.py           # Email engine
│   ├── sms.py             # SMS engine
│   ├── linkedin.py        # LinkedIn engine
│   ├── voice.py           # Voice AI engine
│   ├── mail.py            # Direct mail engine
│   ├── closer.py          # Reply handling
│   ├── content.py         # AI content gen
│   ├── reporter.py        # Metrics
│   ├── icp_scraper.py     # ICP discovery
│   └── content_utils.py   # Content helpers
│
├── detectors/             # LAYER 3.5 - Conversion Intelligence
│   ├── base.py            # Base detector
│   ├── who_detector.py    # Lead pattern analysis
│   ├── what_detector.py   # Message pattern analysis
│   ├── when_detector.py   # Timing analysis
│   ├── how_detector.py    # Channel analysis
│   └── weight_optimizer.py # ALS weight learning
│
├── orchestration/         # LAYER 4 - Workflow coordination
│   ├── worker.py          # Prefect agent
│   ├── flows/
│   │   ├── campaign_flow.py
│   │   ├── enrichment_flow.py
│   │   ├── outreach_flow.py
│   │   ├── reply_recovery_flow.py
│   │   ├── onboarding_flow.py
│   │   ├── pattern_learning_flow.py
│   │   └── pattern_backfill_flow.py
│   ├── tasks/
│   │   ├── enrichment_tasks.py
│   │   ├── scoring_tasks.py
│   │   ├── outreach_tasks.py
│   │   └── reply_tasks.py
│   └── schedules/
│       └── scheduled_jobs.py
│
├── agents/                # AI Agents
│   ├── base_agent.py
│   ├── cmo_agent.py       # Orchestration decisions
│   ├── content_agent.py   # Copy generation
│   ├── reply_agent.py     # Intent classification
│   ├── icp_discovery_agent.py
│   ├── campaign_generation_agent.py
│   └── skills/            # Agent skills
│       ├── base_skill.py
│       ├── website_parser.py
│       ├── service_extractor.py
│       ├── value_prop_extractor.py
│       ├── portfolio_extractor.py
│       ├── industry_classifier.py
│       ├── company_size_estimator.py
│       ├── icp_deriver.py
│       ├── als_weight_suggester.py
│       ├── messaging_generator.py
│       ├── sequence_builder.py
│       ├── campaign_splitter.py
│       └── industry_researcher.py
│
└── api/                   # FastAPI routes
    ├── main.py            # App entrypoint
    ├── dependencies.py    # Auth, DB deps
    └── routes/
        ├── health.py
        ├── campaigns.py
        ├── campaign_generation.py
        ├── leads.py
        ├── webhooks.py
        ├── webhooks_outbound.py
        ├── reports.py
        ├── admin.py
        ├── onboarding.py
        ├── patterns.py
        ├── meetings.py
        └── replies.py
```

---

## Frontend (`frontend/`)

```
frontend/
├── app/
│   ├── layout.tsx         # Root layout
│   ├── globals.css
│   ├── providers.tsx
│   ├── (auth)/            # Auth pages
│   ├── auth/              # Auth callbacks
│   ├── admin/             # Admin dashboard
│   ├── dashboard/         # User dashboard
│   └── onboarding/        # Onboarding flow
│
├── components/
│   ├── ui/                # shadcn components
│   ├── layout/            # Layout components
│   ├── admin/             # Admin components
│   ├── dashboard/         # Dashboard components
│   └── campaigns/         # Campaign components
│
├── hooks/                 # Custom React hooks
├── lib/                   # Utilities
│   ├── api/               # API client
│   ├── supabase.ts
│   └── utils.ts
│
├── types/                 # TypeScript types
└── [config files]
```

---

## Agents (`agents/`)

```
agents/
├── builder/               # Builder Agent
│   ├── BUILDER_AGENT_PROMPT.md
│   ├── BUILDER_CONSTITUTION.md
│   └── tasks/             # Pending tasks
│
├── fixer/                 # Fixer Agent
│   ├── FIXER_AGENT_PROMPT.md
│   ├── FIXER_CONSTITUTION.md
│   └── reports/           # Fix logs
│
├── qa/                    # QA Agent
│   ├── QA_AGENT_PROMPT.md
│   ├── QA_CONSTITUTION.md
│   ├── FULL_CODEBASE_QA_PROMPT.md
│   └── reports/           # QA reports
│
└── prompts/               # Standalone prompts
    ├── ADMIN_DASHBOARD_BUILD_PROMPT.md
    ├── ADMIN_REMAINING_PAGES_PROMPT.md
    ├── DEPLOYMENT_CHECKLIST.md
    ├── GIT_PUSH_PROMPT.md
    └── QUICKSTART.md
```

---

## Documentation (`docs/`)

```
docs/
├── manuals/               # User documentation
│   ├── ADMIN_DASHBOARD_MANUAL.md
│   ├── ADMIN_DASHBOARD_MANUAL.pdf
│   ├── USER_DASHBOARD_MANUAL.pdf
│   ├── admin-manual.html
│   ├── user-manual.html
│   └── manual.html
│
├── specs/                 # Technical specifications
│   ├── phase16/           # Conversion Intelligence specs
│   ├── BOMBORA_INTEGRATION_SPEC.md
│   ├── CAMPAIGN_SKILLS_SPEC.md
│   ├── CC_PROMPT_PHASE11_ICP_SKILLS.md
│   └── FULL_SYSTEM_ARCHITECTURE.md
│
├── progress/              # Build tracking
│   └── COMPLETED_PHASES.md
│
├── marketing/             # Marketing materials
│   └── MARKETING_LAUNCH_PLAN.md
│
└── screenshots/           # UI screenshots
```

---

## Skills (`skills/`)

```
skills/
├── SKILL_INDEX.md         # Skill directory
├── agents/                # Agent-related skills
├── campaign/              # Campaign skills
├── conversion/            # Conversion intelligence
├── frontend/              # Frontend skills
└── testing/               # Testing skills
```

---

## Scripts (`scripts/`)

```
scripts/
├── dev_tunnel.sh          # ngrok for webhooks
├── update_webhook_urls.py # Update webhook URLs
├── capture-screenshots.js # Screenshot capture
├── capture-screenshots.mjs
├── generate-manual.js     # Generate HTML manuals
└── generate-manuals.js
```

---

## Tests (`tests/`)

```
tests/
├── conftest.py            # Pytest fixtures
├── fixtures/              # Mock data
├── integration/           # Integration tests
├── live/                  # Live API tests
├── test_api/              # API route tests
├── test_detectors/        # Detector tests
├── test_e2e/              # End-to-end tests
├── test_engines/          # Engine tests
├── test_flows/            # Prefect flow tests
└── test_skills/           # Skill tests
```

---

## Database (`supabase/`)

```
supabase/
└── migrations/
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
    ├── 011_fix_user_insert_policy.sql
    ├── 012_client_icp_profile.sql
    ├── 013_campaign_templates.sql
    └── 014_conversion_intelligence.sql
```

---

## Quick Navigation

| What you need | Where to look |
|---------------|---------------|
| Architecture decisions | `PROJECT_BLUEPRINT.md` |
| Build progress | `PROGRESS.md` |
| Claude Code instructions | `CLAUDE.md` |
| Run QA check | `agents/qa/FULL_CODEBASE_QA_PROMPT.md` |
| API routes | `src/api/routes/` |
| Database schema | `supabase/migrations/` |
| Frontend pages | `frontend/app/` |
| Deploy instructions | `DEPLOYMENT.md` |
