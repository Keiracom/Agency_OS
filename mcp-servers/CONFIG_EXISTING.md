# MCP Server Configuration - Existing Servers

> Generated: 2025-02-03
> Source: `~/.config/agency-os/.env`

---

## 1. Supabase MCP

**Status:** ✅ CONFIGURED

**Package:** `@supabase/mcp-server-supabase`

**Installation:**
```bash
npx -y @supabase/mcp-server-supabase --help
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `SUPABASE_URL` | ✅ Found: `https://jatzvazlbusedwsnqxzr.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ Found (as `SUPABASE_SERVICE_KEY`) |

**Config JSON:**
```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase", "--access-token", "${SUPABASE_ACCESS_TOKEN}"],
      "env": {
        "SUPABASE_URL": "https://jatzvazlbusedwsnqxzr.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "${SUPABASE_SERVICE_KEY}"
      }
    }
  }
}
```

---

## 2. GitHub MCP

**Status:** ✅ CONFIGURED

**Package:** `@modelcontextprotocol/server-github`

**Installation:**
```bash
npx -y @modelcontextprotocol/server-github
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `GITHUB_TOKEN` | ✅ Found |

**Config JSON:**
```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

---

## 3. Redis MCP (Upstash)

**Status:** ✅ CONFIGURED

**Package:** `@modelcontextprotocol/server-redis` or `@upstash/mcp-server`

**Installation:**
```bash
npx -y @upstash/mcp-server
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `REDIS_URL` | ✅ Found: `rediss://...@clever-stag-35095.upstash.io:6379` |
| `UPSTASH_REDIS_REST_URL` | ✅ Found |
| `UPSTASH_REDIS_REST_TOKEN` | ✅ Found |

**Config JSON (Upstash REST API):**
```json
{
  "mcpServers": {
    "redis": {
      "command": "npx",
      "args": ["-y", "@upstash/mcp-server"],
      "env": {
        "UPSTASH_REDIS_REST_URL": "https://clever-stag-35095.upstash.io",
        "UPSTASH_REDIS_REST_TOKEN": "${UPSTASH_REDIS_REST_TOKEN}"
      }
    }
  }
}
```

**Alternative (Standard Redis Protocol):**
```json
{
  "mcpServers": {
    "redis": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-redis"],
      "env": {
        "REDIS_URL": "${REDIS_URL}"
      }
    }
  }
}
```

---

## 4. Brave Search MCP

**Status:** ✅ CONFIGURED

**Package:** `@anthropic/mcp-server-brave-search` (official) or `@anthropics/mcp-server-brave-search`

**Installation:**
```bash
npx -y @anthropic/mcp-server-brave-search
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `BRAVE_API_KEY` | ✅ Found |

**Config JSON:**
```json
{
  "mcpServers": {
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```

---

## 5. Slack MCP

**Status:** ❌ MISSING_CREDS

**Package:** `@anthropic/mcp-server-slack` or community alternatives

**Installation:**
```bash
npx -y @anthropic/mcp-server-slack
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `SLACK_BOT_TOKEN` | ❌ Not found |
| `SLACK_TEAM_ID` | ❌ Not found |

**Config JSON (template):**
```json
{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-slack"],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-...",
        "SLACK_TEAM_ID": "T..."
      }
    }
  }
}
```

**Setup Required:**
1. Create Slack App at https://api.slack.com/apps
2. Add Bot Token Scopes: `channels:read`, `chat:write`, `users:read`
3. Install to workspace
4. Copy Bot User OAuth Token

---

## 6. Notion MCP

**Status:** ❌ MISSING_CREDS

**Package:** `@anthropic/mcp-server-notion` or `@notionhq/mcp-server`

**Installation:**
```bash
npx -y @anthropic/mcp-server-notion
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `NOTION_API_KEY` | ❌ Not found |

**Config JSON (template):**
```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-notion"],
      "env": {
        "NOTION_API_KEY": "secret_..."
      }
    }
  }
}
```

**Setup Required:**
1. Go to https://www.notion.so/my-integrations
2. Create new integration
3. Copy Internal Integration Token
4. Share relevant pages/databases with the integration

---

## 7. Google Calendar MCP

**Status:** ⚠️ PARTIAL (OAuth creds exist, needs token flow)

**Package:** `@anthropic/mcp-server-google-calendar` or `@anthropic/mcp-server-google-drive`

**Installation:**
```bash
npx -y @anthropic/mcp-server-google-calendar
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `GOOGLE_CLIENT_ID` | ✅ Found |
| `GOOGLE_CLIENT_SECRET` | ✅ Found |
| `GOOGLE_REFRESH_TOKEN` | ❌ Needs OAuth flow |

**Config JSON (template):**
```json
{
  "mcpServers": {
    "google-calendar": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-google-calendar"],
      "env": {
        "GOOGLE_CLIENT_ID": "${GOOGLE_CLIENT_ID}",
        "GOOGLE_CLIENT_SECRET": "${GOOGLE_CLIENT_SECRET}",
        "GOOGLE_REFRESH_TOKEN": "..."
      }
    }
  }
}
```

**Setup Required:**
1. OAuth credentials exist for Web App
2. Need to complete OAuth flow to get refresh token
3. Enable Calendar API in Google Cloud Console

---

## 8. Linear MCP

**Status:** ❌ MISSING_CREDS

**Package:** Community server (e.g., `linear-mcp-server`)

**Installation:**
```bash
npx -y linear-mcp-server
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `LINEAR_API_KEY` | ❌ Not found |

**Config JSON (template):**
```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "linear-mcp-server"],
      "env": {
        "LINEAR_API_KEY": "lin_api_..."
      }
    }
  }
}
```

**Setup Required:**
1. Go to https://linear.app/settings/api
2. Create Personal API Key
3. Add to .env

---

## 9. ClickHouse MCP

**Status:** ❌ MISSING_CREDS

**Package:** `@clickhouse/mcp-server` or `ClickHouse/mcp-clickhouse`

**Installation:**
```bash
npx -y @clickhouse/mcp-server
```

**Required Env Vars:**
| Variable | Status |
|----------|--------|
| `CLICKHOUSE_HOST` | ❌ Not found |
| `CLICKHOUSE_USER` | ❌ Not found |
| `CLICKHOUSE_PASSWORD` | ❌ Not found |

**Config JSON (template):**
```json
{
  "mcpServers": {
    "clickhouse": {
      "command": "npx",
      "args": ["-y", "@clickhouse/mcp-server"],
      "env": {
        "CLICKHOUSE_HOST": "https://...",
        "CLICKHOUSE_USER": "default",
        "CLICKHOUSE_PASSWORD": "..."
      }
    }
  }
}
```

**Note:** ClickHouse not currently in stack. Skip unless analytics warehouse needed.

---

## Summary

| MCP | Status | Ready |
|-----|--------|-------|
| Supabase | ✅ CONFIGURED | Yes |
| GitHub | ✅ CONFIGURED | Yes |
| Redis (Upstash) | ✅ CONFIGURED | Yes |
| Brave Search | ✅ CONFIGURED | Yes |
| Slack | ❌ MISSING_CREDS | No |
| Notion | ❌ MISSING_CREDS | No |
| Google Calendar | ⚠️ PARTIAL | Needs OAuth flow |
| Linear | ❌ MISSING_CREDS | No |
| ClickHouse | ❌ MISSING_CREDS | No (not in stack) |

---

## Combined Config (Ready MCPs Only)

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["-y", "@supabase/mcp-server-supabase", "--access-token", "${SUPABASE_ACCESS_TOKEN}"],
      "env": {
        "SUPABASE_URL": "https://jatzvazlbusedwsnqxzr.supabase.co"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "redis": {
      "command": "npx",
      "args": ["-y", "@upstash/mcp-server"],
      "env": {
        "UPSTASH_REDIS_REST_URL": "https://clever-stag-35095.upstash.io",
        "UPSTASH_REDIS_REST_TOKEN": "${UPSTASH_REDIS_REST_TOKEN}"
      }
    },
    "brave-search": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "${BRAVE_API_KEY}"
      }
    }
  }
}
```
