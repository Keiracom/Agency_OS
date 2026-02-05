# Telnyx MCP Server

MCP server for Telnyx SMS and voice communications.

## Installation

```bash
cd telnyx-mcp
pip install -e .
```

## Environment Variables

```bash
TELNYX_API_KEY=your_key_here
TELNYX_API_URL=https://api.telnyx.com/v2  # optional
```

## Tools

| Tool | Description |
|------|-------------|
| `send_sms(from, to, text)` | Send SMS message |
| `list_phone_numbers()` | List owned DIDs |
| `search_available_numbers(country, area_code)` | Find numbers to buy |
| `buy_number(phone_number)` | Purchase a number |
| `make_call(from, to, connection_id)` | Initiate voice call |
| `list_calls()` | Call history |
| `get_call(call_control_id)` | Call details |
| `get_usage()` | Account usage stats |
| `get_message(message_id)` | Message details |

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "telnyx": {
      "command": "telnyx-mcp",
      "env": {
        "TELNYX_API_KEY": "your_key"
      }
    }
  }
}
```
