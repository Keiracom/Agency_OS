# Elliot Dashboard

A simple, standalone dashboard to see what Elliot knows and does.

## Quick Start

### Option 1: Local Server (Recommended)
```bash
cd /home/elliotbot/clawd
./scripts/generate-dashboard-data.sh
python3 -m http.server 8080
```
Then open: `http://localhost:8080/dashboard.html`

### Option 2: Direct File Access
Some browsers block local file access to JSON. If Chrome/Firefox complains:
```bash
# Firefox with CORS disabled
firefox --allow-file-access-from-files dashboard.html

# Chrome (create shortcut with flag)
google-chrome --allow-file-access-from-files dashboard.html
```

### Option 3: VS Code Live Server
If you have VS Code with Live Server extension, just right-click `dashboard.html` → Open with Live Server.

---

## Files

| File | Purpose |
|------|---------|
| `dashboard.html` | The dashboard UI (single HTML file, no build) |
| `dashboard-data.json` | Generated data from memory files |
| `scripts/generate-dashboard-data.sh` | Regenerates the JSON data |

---

## Updating Data

The dashboard auto-refreshes every 30 seconds, but it only reads `dashboard-data.json`. To see new changes:

```bash
./scripts/generate-dashboard-data.sh
```

### Add to Elliot's Heartbeat
To keep data fresh, add to `HEARTBEAT.md`:
```markdown
- [ ] Run `./scripts/generate-dashboard-data.sh` to update dashboard
```

Or create a cron job:
```bash
# Every 15 minutes
*/15 * * * * /home/elliotbot/clawd/scripts/generate-dashboard-data.sh
```

---

## What It Shows

### Metrics (Top Row)
- **Rules**: Count of operating constraints (from `knowledge/RULES.md`)
- **Learnings**: Permanent lessons (from `knowledge/LEARNINGS.md`)
- **Decisions**: Logged decisions (from `knowledge/DECISIONS.md`)
- **Patterns**: Recurring observations (from `memory/PATTERNS.md`)
- **TODO/Blocked/Running**: Task status (from `tasks/*.md`)

### Tabs
1. **🧠 Core Memory** — Elliot's internalized understanding (`MEMORY.md`)
2. **📋 Rules** — Non-negotiable operating constraints
3. **💡 Learnings** — Lessons extracted from experience
4. **⚖️ Decisions** — Decision log with rationale
5. **🔄 Patterns** — Observed recurring themes
6. **📝 Tasks** — Active work and backlog
7. **📅 Daily Log** — Today's and yesterday's activity

---

## Hosting Options

### 1. Local Only
Run `python3 -m http.server 8080` when you want to view it.

### 2. Always-On (This Server)
```bash
# Run in background with nohup
nohup python3 -m http.server 8080 --directory /home/elliotbot/clawd &

# Or use screen/tmux for easier management
screen -S dashboard
python3 -m http.server 8080 --directory /home/elliotbot/clawd
# Ctrl+A, D to detach
```

### 3. Vercel/Netlify (Public)
Just push `dashboard.html` and `dashboard-data.json` to a repo and deploy. Update JSON via CI/CD.

### 4. Cloudflare Tunnel (Secure Remote Access)
If you have cloudflared:
```bash
cloudflared tunnel --url http://localhost:8080
```

---

## Customization

The dashboard is a single HTML file using:
- **Tailwind CSS** (via CDN)
- **Marked.js** (for Markdown rendering)
- **Inter font** (via Google Fonts)

Edit `dashboard.html` directly to customize colors, layout, or add new tabs.

---

## Troubleshooting

**"Failed to load dashboard data"**
→ Run `./scripts/generate-dashboard-data.sh` first

**JSON loads but shows wrong data**
→ Check if `dashboard-data.json` was updated: `ls -la dashboard-data.json`

**Can't access from another device**
→ Make sure to bind to all interfaces: `python3 -m http.server 8080 --bind 0.0.0.0`

**Markdown tables look weird**
→ The markdown renderer handles tables, but complex ones may need tweaking
