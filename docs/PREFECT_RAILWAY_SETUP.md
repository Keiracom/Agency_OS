# Prefect on Railway - Setup Guide

**Created:** 2026-01-07
**Purpose:** Deploy self-hosted Prefect server and worker on Railway

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY PROJECT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │   api (existing) │     │  prefect-server  │                  │
│  │   ─────────────  │     │  ───────────────  │                  │
│  │   FastAPI app    │     │  Prefect UI/API  │                  │
│  │   Port: $PORT    │────▶│  Port: $PORT     │                  │
│  │   Dockerfile     │     │  Dockerfile.     │                  │
│  │                  │     │     prefect      │                  │
│  └──────────────────┘     └────────┬─────────┘                  │
│                                    │                             │
│                                    ▼                             │
│                           ┌──────────────────┐                  │
│                           │  prefect-worker  │                  │
│                           │  ───────────────  │                  │
│                           │  Executes flows  │                  │
│                           │  Dockerfile.     │                  │
│                           │     worker       │                  │
│                           └──────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Step 1: Create Prefect Server Service

### In Railway Dashboard:

1. **Go to your Railway project**

2. **Click "New Service" → "Empty Service"**

3. **Configure the service:**
   - Name: `prefect-server`
   - Root Directory: `/` (project root)
   - Dockerfile Path: `Dockerfile.prefect`

4. **Set Environment Variables:**
   ```
   PREFECT_SERVER_API_HOST=0.0.0.0
   PREFECT_UI_ENABLED=true
   ```

5. **Optional: Use PostgreSQL for Prefect metadata**
   ```
   PREFECT_API_DATABASE_CONNECTION_URL=postgresql://postgres:[PASSWORD]@[HOST]:5432/prefect
   ```
   (You can create a new database in Supabase or use a separate Railway PostgreSQL)

6. **Deploy the service**

7. **Get the public URL** (e.g., `https://prefect-server-production-xxxx.up.railway.app`)

---

## Step 2: Create Prefect Worker Service

### In Railway Dashboard:

1. **Click "New Service" → "Empty Service"**

2. **Configure the service:**
   - Name: `prefect-worker`
   - Root Directory: `/` (project root)
   - Dockerfile Path: `Dockerfile.worker`

3. **Set Environment Variables:**

   **Required - Prefect Connection:**
   ```
   PREFECT_API_URL=https://prefect-server-production-xxxx.up.railway.app/api
   ```
   (Use the URL from Step 1)

   **Required - Copy ALL env vars from your api service:**
   ```
   DATABASE_URL=...
   REDIS_URL=...
   SUPABASE_URL=...
   SUPABASE_KEY=...
   SUPABASE_SERVICE_KEY=...
   ANTHROPIC_API_KEY=...
   APOLLO_API_KEY=...
   APIFY_API_KEY=...
   CLAY_API_KEY=...
   RESEND_API_KEY=...
   (... all other API keys)
   ```

4. **Deploy the service**

---

## Step 3: Update API Service

### In Railway Dashboard:

1. **Go to your `api` service**

2. **Add/Update Environment Variable:**
   ```
   PREFECT_API_URL=https://prefect-server-production-xxxx.up.railway.app/api
   ```

3. **Redeploy the service**

---

## Step 4: Verify Setup

### Option A: Use Prefect UI

1. Open: `https://prefect-server-production-xxxx.up.railway.app`
2. You should see the Prefect dashboard
3. Check **Work Pools** - should show `agency-os-pool`
4. Check **Deployments** - should show your flows

### Option B: Use CLI (from local machine)

```bash
# Set the API URL
export PREFECT_API_URL=https://prefect-server-production-xxxx.up.railway.app/api

# Check work pools
python -m prefect work-pool ls

# Check deployments
python -m prefect deployment ls

# Check flow runs
python -m prefect flow-run ls --limit 10
```

---

## Step 5: Test a Flow

### Trigger a test flow run:

```bash
# From local machine with PREFECT_API_URL set
python -m prefect deployment run "pool_population/pool-population"
```

### Or via API call:

```bash
curl -X POST "https://your-api.railway.app/api/v1/pool/populate" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

---

## Scheduled Flows

Once deployed, these flows run automatically:

| Flow | Schedule | Purpose |
|------|----------|---------|
| `enrichment-flow` | Daily 2 AM AEST | Enrich new leads |
| `outreach-flow` | Hourly 8AM-6PM Mon-Fri | Send outreach |
| `reply-recovery-flow` | Every 6 hours | Catch missed replies |
| `metrics-flow` | Daily midnight | Generate reports |
| `pattern-learning-flow` | Weekly Sunday 3 AM | AI optimization |
| `pattern-backfill-flow` | Daily 4 AM | Backfill patterns |

---

## Troubleshooting

### Worker not connecting

```bash
# Check worker logs in Railway dashboard
# Look for: "Connected to Prefect server"
```

### Flows not deploying

```bash
# SSH into worker container or run locally:
export PREFECT_API_URL=https://...
python -m prefect deploy --all
```

### Work pool not created

```bash
# Create manually:
python -m prefect work-pool create agency-os-pool --type process
```

---

## Cost Estimate

| Service | Memory | CPU | Est. Monthly |
|---------|--------|-----|--------------|
| prefect-server | 512MB | Shared | ~$5 |
| prefect-worker | 1GB | Shared | ~$7-10 |
| **Total** | | | **~$12-15/month** |

---

## Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile.prefect` | Prefect server container |
| `Dockerfile.worker` | Prefect worker container |
| `railway.prefect.toml` | Railway config for server |
| `railway.worker.toml` | Railway config for worker |
| `scripts/start-prefect-server.sh` | Server startup script |
| `scripts/start-prefect-worker.sh` | Worker startup script |
| `scripts/setup-prefect.sh` | Manual setup script |
| `prefect.yaml` | Flow deployment definitions |

---

## Quick Reference Commands

```bash
# Set API URL (do this first)
export PREFECT_API_URL=https://prefect-server-production-xxxx.up.railway.app/api

# List work pools
python -m prefect work-pool ls

# List deployments
python -m prefect deployment ls

# Deploy all flows
python -m prefect deploy --all

# Run a deployment manually
python -m prefect deployment run "pool_population/pool-population"

# Check recent flow runs
python -m prefect flow-run ls --limit 10

# Start local worker (for testing)
python -m prefect worker start --pool agency-os-pool
```
