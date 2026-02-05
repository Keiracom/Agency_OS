# Resend MCP Server

MCP server for Resend transactional email delivery.

## Installation

```bash
cd resend-mcp
pip install -e .
```

## Environment Variables

```bash
RESEND_API_KEY=re_xxxxx
RESEND_API_URL=https://api.resend.com  # optional
```

## Tools

| Tool | Description |
|------|-------------|
| `send_email(from, to, subject, html)` | Send email |
| `send_batch(emails[])` | Send multiple emails |
| `list_emails()` | List sent emails |
| `get_email(email_id)` | Email status/details |
| `list_domains()` | Configured domains |
| `get_domain(domain_id)` | Domain details |
| `add_domain(name)` | Add sending domain |
| `verify_domain(domain_id)` | Trigger DNS verification |
| `delete_domain(domain_id)` | Remove domain |
| `list_api_keys()` | Account API keys |

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "resend": {
      "command": "resend-mcp",
      "env": {
        "RESEND_API_KEY": "re_xxxxx"
      }
    }
  }
}
```

## Notes

- From address must use a verified domain
- Supports HTML and plain text content
- Batch sending available for bulk operations
