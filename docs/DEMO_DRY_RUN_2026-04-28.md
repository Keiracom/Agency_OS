# Demo dry-run runbook — Dashboard rebuild PR4 (2026-04-28)

Operator runbook for verifying the Dashboard rebuild end-to-end after PRs
#441 (palette/sidebar), #442 (core components), #443 (pipeline view), and
#444 (this PR — mock unwiring + demo polish).

**Operator note:** the dry-run touches `clients`, `campaigns`, and
`campaign_leads` rows. Clone Atlas does not have direct DB credentials in
the Claude Code runtime; this script must be invoked from the operator's
shell where `DATABASE_URL` / `SUPABASE_DB_URL` and the Supabase service
key are loaded.

## 1. Seed the demo tenant

```bash
cd /home/elliotbot/clawd/Agency_OS

# Confirm dry-run output looks sane first.
python3 scripts/seed_demo_tenant.py
# Expected:
#   demo client exists / created — id=…
#   ensuring demo Supabase auth user (email=demo@keiracom.com)…
#   selecting top 7 BU prospects (stage >= 6, propensity > 60, real email)…
#   selected: 7 prospects   (or shortfall error if pool < 7)

# Apply writes.
python3 scripts/seed_demo_tenant.py --execute
# Expected tail:
#   demo campaign exists / created — id=…
#   linked: 7 new campaign_leads rows
#   demo_client_id: …
#   demo_campaign_id: …
```

If `--execute` exits with `ERROR — only N of 7 target prospects passed all
filters`, the BU pool is short of the curated tier. Triggers:

- Run more enrichment to grow the candidate pool (Stage 9/10 funnel).
- Or temporarily lower `MIN_PROPENSITY` in `scripts/seed_demo_tenant.py`
  for a non-production demo (revert after capture).

## 2. Confirm the auth path

```bash
# Auth user creation is idempotent. Re-running --execute is safe.
# Verify the user exists via the Supabase admin API:
curl -s "$SUPABASE_URL/auth/v1/admin/users?email=demo@keiracom.com" \
  -H "apikey: $SUPABASE_SERVICE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" | jq '.users[0].id'
```

Sign in at the dashboard route with:

- email: `demo@keiracom.com`
- password: `${DEMO_PASSWORD:-demo-investor-2026}`

## 3. Pipeline View verification (PR3 + PR4)

After signing in, open `/dashboard/pipeline`:

- [ ] **Header** uses Playfair Display ("Pipeline, _ranked_") with amber
      italic accent (PR1 palette)
- [ ] **State tabs** render Review / Outreach / Complete; default mode is
      Outreach showing live counts pulled from `usePipelineData`
- [ ] **Filter chips**: All / Top 10 / Top 50 / Struggling / Trying /
      Dabbling — counts add up to total
- [ ] **List view** shows the 7 demo prospects ranked by score, each with
      a left intent bar (red=struggling / amber=trying / tan=dabbling)
- [ ] Active filter chip is amber-filled with on-amber text
- [ ] Click any row → ProspectDrawer slides in (existing behaviour
      preserved)
- [ ] Toggle to `kanban` and `table` views — both still render

## 4. Prospect Detail card (PR3)

If the demo data has at least one prospect with grades, click that row to
open the drawer. The new `ProspectDetailCard` component is available for
embedding in any page; verify the grade strip + signal timeline render
correctly when sample data is supplied:

```tsx
import { ProspectDetailCard } from "@/components/dashboard/ProspectDetailCard";

<ProspectDetailCard prospect={{
  id: "demo-1",
  name: "Dr Sample",
  company: "Demo Dental Clinic",
  vulnerability: "No paid acquisition; weak SEO; reviews stale.",
  grades: { website: "C", seo: "D", reviews: "F", ads: "F", social: "C", content: "B" },
  signals: [
    { id: "s1", kind: "email_sent", at: new Date().toISOString(), headline: "Email · Sent — opening hook" },
    { id: "s2", kind: "email_replied", at: new Date(Date.now() - 3600_000).toISOString(),
      headline: "Email · Replied", quote: "Very interested. We've been struggling with our online presence." },
  ],
  meeting: { scheduledAt: new Date(Date.now() + 2 * 86400_000).toISOString(), withName: "Dr Sample", durationMin: 30 },
}} />
```

- [ ] A-F grade strip renders 6 colour-coded chips
- [ ] Signal timeline shows mono date stamps + amber-bordered Playfair
      italic quote blocks
- [ ] Meeting block shows a green-bordered countdown ("in 2d Xh")

## 5. Demo Mode banner (PR4)

Set `IS_DEMO_MODE=true` (or seed the demo cookie) and reload `/dashboard`:

- [ ] Banner sits at top with deep-ink background + amber `Demo Mode`
      label + amber `Start Free Trial →` button
- [ ] Dismiss button (×) clears the banner for the session
- [ ] Banner palette matches the rest of the dashboard (no orange-gradient
      legacy)

## 6. Mock unwiring (PR4)

On `/dashboard`:

- [ ] Channel Orchestration slot shows a `TODO · MOCK` panel naming
      `GET /api/v1/dashboard/touches?breakdown=channel`
- [ ] Smart Calling slot shows a `TODO · MOCK` panel naming the voice
      stats + recent calls endpoints
- [ ] What's Working pane has the real `insight.detail` (when present)
      and a `TODO · MOCK` sub-panel for the segment analytics endpoints
- [ ] No fabricated numbers render in any of these slots

## 7. agencyxos.ai/demo (Vercel marketing project)

The static demo at `/demo` served from `frontend/landing/` is now the v10
prototype `dashboard-master-agency-desk.html`. After the next Vercel
deploy of the `frontend/landing/` project:

- [ ] `https://agencyxos.ai/demo` serves the cream/amber Agency Desk
      prototype (md5 matches `dashboard-master-agency-desk.html`)
- [ ] Brand mark renders Playfair Display with amber italic `OS`
- [ ] Sidebar is 232px dark with amber active borders

## Sign-off

When every checkbox is ticked, paste the Vercel deploy URL + a
screenshot of `/dashboard` + `/dashboard/pipeline` into the dashboard
rebuild thread.
