# Elliot Dashboard 🤖

Mobile-first dashboard for monitoring Elliot's memory, decisions, and activity.

## Features

- **📊 Dashboard** — Quick stats, session health, recent activity
- **🧠 Memory Browser** — Search and explore memory, learnings, patterns, rules
- **⚖️ Decision Log** — Track decisions with context, rationale, and outcomes
- **📈 Activity Feed** — Real-time activity with token/cost tracking

## Tech Stack

- **Next.js 14** — React framework with App Router
- **Supabase** — PostgreSQL database
- **Tailwind CSS** — Mobile-first styling
- **TypeScript** — Type safety

## Setup

### 1. Database Setup

Run the schema in your Supabase SQL Editor:

```bash
# Copy and run in Supabase Dashboard → SQL Editor
cat supabase-schema.sql
```

### 2. Environment Variables

Create `.env.local`:

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# API Auth (optional - for sync script)
ELLIOT_API_TOKEN=your-secret-token
```

Or source from your existing config:

```bash
source ~/.config/agency-os/.env
```

### 3. Install & Run

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000/elliot](http://localhost:3000/elliot)

### 4. Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Add environment variables in Vercel dashboard
```

## Syncing Memory Files

The sync script parses your markdown memory files and pushes to Supabase:

```bash
# One-time sync
npm run sync

# Watch for changes (requires `watch` package)
npm run sync:watch
```

### Sync Script Environment

```bash
# Direct Supabase connection (preferred)
SUPABASE_URL=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Or via API
ELLIOT_API_URL=https://your-dashboard.vercel.app/api/elliot
ELLIOT_API_TOKEN=your-token

# Workspace path
ELLIOT_WORKSPACE=/home/elliotbot/clawd
```

## API Endpoints

### GET /api/elliot/stats

Get dashboard statistics and optional data.

```bash
# Basic stats
curl /api/elliot/stats

# Include specific data
curl "/api/elliot/stats?include=memory,learnings,decisions"
```

### POST /api/elliot/sync

Push memory updates.

```bash
curl -X POST /api/elliot/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "memory", "data": {"key": "test", "value": "hello"}}'
```

Types: `memory`, `decision`, `learning`, `pattern`, `rule`, `session`, `bulk`

### POST /api/elliot/log

Log activity.

```bash
curl -X POST /api/elliot/log \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Completed task X",
    "action_type": "task",
    "status": "completed",
    "tokens_used": 1500,
    "cost_usd": 0.003
  }'
```

## File Structure

```
dashboard/
├── app/
│   ├── elliot/
│   │   ├── page.tsx        # Main dashboard
│   │   ├── layout.tsx      # Dashboard layout
│   │   ├── memory/         # Memory browser
│   │   ├── decisions/      # Decision log
│   │   └── activity/       # Activity feed
│   ├── api/elliot/
│   │   ├── stats/          # GET stats
│   │   ├── sync/           # POST sync
│   │   └── log/            # POST/PATCH activity
│   ├── layout.tsx          # Root layout
│   └── globals.css         # Global styles
├── components/
│   ├── Card.tsx            # Card components
│   ├── Navigation.tsx      # Nav components
│   ├── Search.tsx          # Search & filters
│   └── Loading.tsx         # Loading states
├── lib/
│   ├── supabase.ts         # Supabase client & types
│   ├── utils.ts            # Utility functions
│   └── auth.ts             # API auth helpers
├── scripts/
│   └── sync-to-supabase.ts # Memory sync script
├── public/
│   └── manifest.json       # PWA manifest
└── supabase-schema.sql     # Database schema
```

## Mobile PWA

Add to home screen on iOS/Android for app-like experience:

1. Open dashboard in Safari/Chrome
2. Tap share button
3. "Add to Home Screen"

## Development

```bash
# Dev server with hot reload
npm run dev

# Type checking
npx tsc --noEmit

# Build for production
npm run build
npm run start
```

## License

MIT - Built for Elliot 🤖
