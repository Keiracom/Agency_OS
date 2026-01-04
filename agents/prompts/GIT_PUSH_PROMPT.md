# GIT PUSH PROMPT — Agency OS

> **Copy this into Claude Code to push all changes to GitHub.**

---

## IDENTITY

You are pushing the Agency OS codebase to GitHub so it can be deployed to Vercel and Railway.

---

## WORKING DIRECTORY

```
C:\AI\Agency_OS\
```

---

## TASK

Push all current code to GitHub. This includes:
- All backend code (src/)
- All frontend code (frontend/)
- All migrations (supabase/)
- All configuration files
- The new Admin Dashboard

---

## STEPS

### 1. Check Git Status

```bash
git status
```

See what files are new/modified.

---

### 2. Add All Files

```bash
git add .
```

---

### 3. Check What's Staged

```bash
git status
```

Confirm all files are staged.

---

### 4. Commit

```bash
git commit -m "feat: Complete Admin Dashboard with 20 pages

- Added database migration 010_platform_admin.sql
- Added admin API routes (13 endpoints)
- Added admin frontend layout with auth protection
- Added 7 admin components (KPICard, AlertBanner, etc.)
- Added 20 admin pages:
  - Command Center, Revenue, Clients, Client Detail
  - Campaigns, Leads, Activity, Replies
  - Costs Overview, AI Spend, Channel Costs
  - System Status, Errors, Queues, Rate Limits
  - Compliance, Suppression, Bounces
  - Settings, Users
- All pages protected by is_platform_admin check
- QA verified: 0 issues"
```

---

### 5. Push to GitHub

```bash
git push origin main
```

If the branch is `master` instead of `main`:
```bash
git push origin master
```

---

### 6. Verify

Go to GitHub and confirm the push:
```
https://github.com/[your-username]/Agency_OS
```

---

## IF ERRORS

### "Not a git repository"

```bash
git init
git remote add origin https://github.com/[your-username]/Agency_OS.git
git branch -M main
git add .
git commit -m "Initial commit: Agency OS v3.0"
git push -u origin main
```

### "Authentication failed"

Use GitHub CLI:
```bash
gh auth login
```

Or use a Personal Access Token:
```bash
git remote set-url origin https://[TOKEN]@github.com/[your-username]/Agency_OS.git
```

### "Updates were rejected"

Pull first, then push:
```bash
git pull origin main --rebase
git push origin main
```

---

## AFTER PUSH

Confirm with:
1. ✅ GitHub shows latest commit
2. ✅ All files visible in repo
3. ✅ `frontend/app/admin/` folder exists with all pages

Then deploy:
- Vercel will auto-deploy if connected
- Railway will auto-deploy if connected

---

**END OF PROMPT**
