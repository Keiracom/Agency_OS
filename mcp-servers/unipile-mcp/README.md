# Unipile MCP Server

MCP server for LinkedIn automation via Unipile.

## Installation

```bash
cd unipile-mcp
pip install -e .
```

## Environment Variables

```bash
UNIPILE_API_KEY=your_key_here
UNIPILE_API_URL=https://api22.unipile.com:15268  # your DSN endpoint
```

## Tools

| Tool | Description |
|------|-------------|
| `search_profiles(query)` | Search LinkedIn profiles |
| `get_profile(profile_id)` | Get profile details |
| `send_connection(profile_id, message)` | Send connection request |
| `send_message(profile_id, message)` | Send DM to connection |
| `list_connections()` | List your connections |
| `get_account_status()` | Account health check |
| `list_conversations()` | Message threads |
| `get_conversation(id)` | Conversation messages |
| `withdraw_invitation(id)` | Cancel pending invite |
| `list_pending_invitations()` | Pending requests |

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "unipile": {
      "command": "unipile-mcp",
      "env": {
        "UNIPILE_API_KEY": "your_key",
        "UNIPILE_API_URL": "https://api22.unipile.com:15268"
      }
    }
  }
}
```
