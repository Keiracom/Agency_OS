# Telegram MCP Server for AgencyOS_CEO Bot

This MCP (Model Context Protocol) server provides Claude Desktop integration with the Telegram Bot API for the AgencyOS_CEO bot.

## Setup Instructions

### 1. Install Dependencies

```bash
cd /home/elliotbot/clawd/mcp-servers/telegram
pip install -r requirements.txt
```

### 2. Configure Claude Desktop

Add the following configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["/home/elliotbot/clawd/mcp-servers/telegram/server.py"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "8207453089:AAFG99Dt6gWuhI88YMkcrtheWOivjRmzOfo"
      }
    }
  }
}
```

### 3. Restart Claude Desktop

After adding the configuration, restart Claude Desktop for the changes to take effect.

## Available Tools

### 1. `send_message`
Send a message to a Telegram chat.

**Parameters:**
- `text` (string, required): The message text to send
- `chat_id` (integer/string, required): The chat ID to send the message to

**Example:**
```
Please send "Hello from Claude!" to the AgencyOS group
```

### 2. `get_messages`
Get recent messages from a Telegram chat.

**Parameters:**
- `chat_id` (integer/string, required): The chat ID to get messages from
- `limit` (integer, optional): Number of recent messages to retrieve (default: 10, max: 100)

**Example:**
```
Get the last 5 messages from the AgencyOS group
```

### 3. `get_chat_id`
Get the default configured chat ID (-5151519377 for AgencyOS group).

**Parameters:** None

**Example:**
```
What's the default chat ID?
```

## Bot Details

- **Token:** 8207453089:AAFG99Dt6gWuhI88YMkcrtheWOivjRmzOfo
- **Default Group ID:** -5151519377 (AgencyOS group)
- **Base URL:** https://api.telegram.org/bot{token}

## Testing

To test the server installation:

1. Verify Python syntax:
   ```bash
   python -m py_compile server.py
   ```

2. Test MCP server response:
   ```bash
   python server.py
   ```
   (The server will start and wait for MCP protocol messages via stdin/stdout)

## Troubleshooting

- Make sure the bot token is correctly set in the environment variable
- Ensure the bot has permissions to read/write in the target chats
- Check that all dependencies are installed: `pip list | grep -E "(mcp|httpx)"`
- Verify Claude Desktop configuration syntax is valid JSON

## API Reference

This server uses the Telegram Bot API directly via HTTP requests:
- `sendMessage` - For sending messages
- `getUpdates` - For retrieving recent messages

No webhook setup required - uses polling method for message retrieval.