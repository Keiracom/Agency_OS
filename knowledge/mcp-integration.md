# MCP Integration for Clawdbot

## Summary

Clawdbot **does support MCP** (Model Context Protocol) servers through the bundled **mcporter** skill. This provides a CLI-based approach to calling MCP servers, making any MCP tool available to the agent.

---

## How MCP Works in Clawdbot

### The mcporter Skill

Clawdbot ships with a bundled skill at `skills/mcporter/SKILL.md` that teaches the agent how to use the `mcporter` CLI tool.

**What mcporter does:**
- Acts as a universal MCP client
- Supports both HTTP and stdio transports
- Handles OAuth authentication automatically
- Auto-discovers MCP servers from Cursor/Claude/Codex configs
- Maintains a daemon for stateful connections

### Installation

```bash
# Install mcporter globally
npm install -g mcporter

# Verify installation
mcporter --version
```

The mcporter skill will automatically become available once the binary is on PATH.

### Configuration

mcporter uses a JSON config file. Default locations:
- Project: `./config/mcporter.json`
- Home: `~/.mcporter/mcporter.json`

Example configuration:

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "YOUR_API_KEY"
      }
    },
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

---

## Usage Examples

### Basic Commands

```bash
# List all configured MCP servers
mcporter list

# List tools from a specific server with schema details
mcporter list context7 --schema

# Call a tool
mcporter call context7.resolve-library-id libraryName=react

# Call with function syntax
mcporter call 'linear.create_comment(issueId: "ENG-123", body: "Hello world")'
```

### Within Clawdbot

The agent can use mcporter through the exec tool:

```bash
# The agent can run:
mcporter call context7.get-library-docs context7CompatibleLibraryID=/supabase/supabase topic=auth
```

---

## Recommended MCP Servers

### 1. Context7 (Library Documentation)

**Purpose:** Provides up-to-date code documentation for any library directly to the LLM.

**Installation:**

```bash
# Option A: Remote HTTP (recommended - no local install)
# Just add to mcporter config

# Option B: Local stdio
npm install -g @upstash/context7-mcp
```

**Configuration:**

```json
{
  "mcpServers": {
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

**Get API Key:** https://context7.com/dashboard (free tier available)

**Tools Available:**
- `resolve-library-id` - Convert library name to Context7 ID
- `query-docs` - Get documentation for a specific library

**Example Usage:**
```bash
mcporter call context7.resolve-library-id libraryName=nextjs
mcporter call context7.query-docs libraryId=/vercel/next.js query="app router middleware"
```

---

### 2. Playwright MCP (Browser Automation)

**Purpose:** Browser automation via Playwright's accessibility tree - no screenshots needed.

**Installation:**

```bash
# No global install needed - uses npx
# Just add to mcporter config
```

**Configuration:**

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

**Key Options:**
- `--headless` - Run without visible browser
- `--browser chrome|firefox|webkit` - Choose browser
- `--caps vision` - Enable screenshot capabilities

**Tools Available:**
- `browser_navigate` - Navigate to URL
- `browser_click` - Click elements
- `browser_type` - Type text
- `browser_snapshot` - Get accessibility tree
- `browser_screenshot` - Capture screenshot (with `--caps vision`)

**Note:** Clawdbot already has extensive browser tooling built-in. Playwright MCP may be redundant unless you need specific Playwright features.

---

### 3. GitHub MCP Server (GitHub API)

**Purpose:** Full GitHub API access - repos, issues, PRs, code search, security scanning.

**Installation:**

```bash
# Option A: Docker (recommended)
docker pull ghcr.io/github/github-mcp-server

# Option B: Build from source
go build -o github-mcp-server ./cmd/github-mcp-server
```

**Configuration (Docker):**

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

**Get Token:** https://github.com/settings/personal-access-tokens/new

**Toolsets Available:**
- `repos` - File operations, branches, commits
- `issues` - Create, read, update, comment on issues
- `pull_requests` - PR operations, reviews, merging
- `users` - User info
- `code_security` - Code scanning alerts

**Example Usage:**
```bash
mcporter call github.list_issues owner=anthropics repo=claude-code state=open
mcporter call github.create_issue owner=myorg repo=myrepo title="Bug report" body="Details here"
```

---

## Setup Checklist

1. **Install mcporter:**
   ```bash
   npm install -g mcporter
   ```

2. **Create config file:**
   ```bash
   mkdir -p ~/.mcporter
   cat > ~/.mcporter/mcporter.json << 'EOF'
   {
     "mcpServers": {
       "context7": {
         "url": "https://mcp.context7.com/mcp"
       }
     }
   }
   EOF
   ```

3. **Verify the skill is available:**
   ```bash
   clawdbot skills list | grep mcporter
   ```

4. **Test MCP connection:**
   ```bash
   mcporter list
   ```

5. **Restart Clawdbot gateway** to pick up the new skill:
   ```bash
   clawdbot gateway restart
   ```

---

## Alternatives to mcporter

If mcporter doesn't fit your needs:

### 1. Direct API Calls

For HTTP-based MCPs like Context7, you can call them directly via curl/fetch without mcporter:

```bash
curl -X POST https://mcp.context7.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "resolve-library-id", "arguments": {"libraryName": "react"}}}'
```

### 2. Custom Skills

Write a custom skill that wraps specific MCP functionality:

```markdown
---
name: context7-docs
description: Get library documentation via Context7
metadata: {"clawdbot":{"requires":{"env":["CONTEXT7_API_KEY"]}}}
---

Use this skill to fetch up-to-date documentation for any library.

## Usage
1. Run: `curl -X POST https://mcp.context7.com/mcp ...`
2. Parse the response
3. Return relevant documentation
```

### 3. Clawdbot Plugins

For deeper integration, create a Clawdbot plugin that registers MCP tools directly. See `/home/elliotbot/.npm-global/lib/node_modules/clawdbot/docs/plugin.md`.

---

## Limitations

1. **No native MCP protocol in Clawdbot** - MCP is accessed via the mcporter CLI skill, not built into the core.

2. **Extra latency** - Each MCP call spawns a subprocess (mcporter), adding overhead vs native tools.

3. **Token cost** - MCP tool schemas can be large; mcporter mitigates this by not loading schemas into context unless explicitly requested.

4. **Daemon management** - Stateful MCPs (like chrome-devtools) require the mcporter daemon running.

---

## Further Reading

- **mcporter docs:** https://mcporter.dev / https://github.com/steipete/mcporter
- **Context7 docs:** https://context7.com/docs
- **Playwright MCP:** https://github.com/microsoft/playwright-mcp
- **GitHub MCP Server:** https://github.com/anthropics/github-mcp-server
- **Clawdbot Skills:** https://docs.clawd.bot/tools/skills
- **MCP Specification:** https://modelcontextprotocol.io

---

*Last updated: 2026-01-29*
