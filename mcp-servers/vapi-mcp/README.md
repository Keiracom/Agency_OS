# Vapi MCP Server

MCP server for Vapi voice AI assistant management and outbound calling.

## Installation

```bash
cd vapi-mcp
pip install -e .
```

## Environment Variables

```bash
VAPI_API_KEY=your_key_here
VAPI_API_URL=https://api.vapi.ai  # optional, defaults to this
```

## Tools

| Tool | Description |
|------|-------------|
| `list_assistants()` | List all voice assistants |
| `create_assistant(config)` | Create new assistant |
| `update_assistant(id, config)` | Update assistant config |
| `get_assistant(id)` | Get assistant details |
| `delete_assistant(id)` | Delete assistant |
| `start_call(assistant_id, phone_number)` | Initiate outbound call |
| `get_call(call_id)` | Get call status |
| `list_calls(filters)` | Call history |
| `get_transcript(call_id)` | Get call transcript |
| `list_phone_numbers()` | List Vapi phone numbers |

## Usage with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vapi": {
      "command": "vapi-mcp",
      "env": {
        "VAPI_API_KEY": "your_key"
      }
    }
  }
}
```
