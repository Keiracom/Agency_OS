# DEPLOYMENT CHECKLIST — Admin Dashboard Test

**Date:** December 21, 2025  
**Status:** Admin Dashboard complete, ready to deploy

---

## Pre-Deployment Checklist

### 1. Accounts Ready?

| Service | Have Account? | Have CLI? |
|---------|---------------|-----------|
| Railway | ☐ Yes | `npm install -g @railway/cli` |
| Vercel | ☐ Yes | `npm install -g vercel` |
| Supabase | ✅ Yes (already running) | — |
| Upstash | ✅ Yes (already running) | — |

### 2. Credentials in .env?

You already have these in `config/.env`:
- ✅ SUPABASE_URL
- ✅ SUPABASE_ANON_KEY
- ✅ SUPABASE_SERVICE_KEY
- ✅ ANTHROPIC_API_KEY
- ✅ REDIS_URL
- ✅ PREFECT_API_URL (self-hosted on Railway)
- ✅ VERCEL_TOKEN
- ✅ GITHUB_TOKEN

---

## Step-by-Step Deployment

### Step 1: Apply Database Migration

The Admin Dashboard needs the new `is_platform_admin` column.

**In Supabase Dashboard:**
1. Go to SQL Editor
2. Run the migration from `supabase/migrations/010_platform_admin.sql`
3. Then set yourself as admin:

```sql
UPDATE users 
SET is_platform_admin = TRUE 
WHERE email = 'your-email@example.com';
```

---

### Step 2: Deploy Backend to Railway

**Option A: Via Railway Dashboard (Easier)**

1. Go to [railway.app](https://railway.app)
2. Create new project → Deploy from GitHub repo
3. Select your Agency_OS repo
4. Add environment variables (copy from your `.env`):

```
SUPABASE_URL=https://jatzvazlbusedwsnqxzr.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_KEY=eyJ...
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=rediss://...
PREFECT_API_URL=https://prefect-server-production-f9b1.up.railway.app/api
```

5. Deploy and get your Railway URL (e.g., `https://agency-os-api.up.railway.app`)

**Option B: Via CLI**

```bash
cd C:\AI\Agency_OS
railway login
railway init
railway up
```

---

### Step 3: Deploy Frontend to Vercel

**Option A: Via Vercel Dashboard (Easier)**

1. Go to [vercel.com](https://vercel.com)
2. Import project from GitHub
3. Set Root Directory: `frontend`
4. Add environment variables:

```
NEXT_PUBLIC_SUPABASE_URL=https://jatzvazlbusedwsnqxzr.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app
```

5. Deploy and get your Vercel URL (e.g., `https://agency-os.vercel.app`)

**Option B: Via CLI**

```bash
cd C:\AI\Agency_OS\frontend
vercel login
vercel --prod
```

---

### Step 4: Access Admin Dashboard

1. Go to your Vercel URL: `https://your-app.vercel.app/login`
2. Sign in with the email you set as platform admin
3. You'll be redirected to `/admin` (Command Center)

---

## Quick Test Checklist

After deployment, verify:

| Page | URL | Check |
|------|-----|-------|
| Login | `/login` | ☐ Can sign in |
| Command Center | `/admin` | ☐ Shows KPIs |
| Clients | `/admin/clients` | ☐ Lists clients |
| System Status | `/admin/system` | ☐ Shows service health |
| AI Spend | `/admin/costs/ai` | ☐ Shows spend data |

---

## Troubleshooting

### "Not authorized" on /admin
- Check `is_platform_admin = TRUE` for your user in Supabase

### API errors
- Check Railway logs for backend errors
- Verify environment variables are set

### Database errors
- Ensure migration 010 was applied
- Check Supabase connection string uses port 6543

---

## URLs After Deployment

| Service | URL |
|---------|-----|
| Frontend | `https://_______.vercel.app` |
| Backend API | `https://_______.up.railway.app` |
| Supabase | `https://jatzvazlbusedwsnqxzr.supabase.co` |
| Admin Dashboard | `https://_______.vercel.app/admin` |

---

## Next Steps After Testing

1. ☐ Configure custom domain (optional)
2. ☐ Add remaining API keys (Apollo, Resend, etc.)
3. ☐ Set up Sentry for error tracking
4. ☐ Enable Prefect flows

---
