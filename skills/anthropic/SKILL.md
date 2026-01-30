---
name: anthropic
description: Anthropic Claude API. Text generation, vision, tool use, and structured output via Messages API.
metadata: {"clawdbot":{"emoji":"🧠","always":true,"requires":{"env":["ANTHROPIC_API_KEY"],"bins":["curl","jq"]}}}
---

# Anthropic Claude API 🧠

Interact with Anthropic's Claude models via REST API.

## Authentication

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

All requests require:
- Header: `x-api-key: $ANTHROPIC_API_KEY`
- Header: `anthropic-version: 2023-06-01`
- Base URL: `https://api.anthropic.com`

## Models & Pricing

| Model | ID | Input $/MTok | Output $/MTok | Context | Use Case |
|-------|-----|--------------|---------------|---------|----------|
| **Opus 4.5** | `claude-opus-4-5-20250220` | $15 | $75 | 200K | Flagship, deep reasoning |
| **Opus 4.1** | `claude-opus-4-1-20250219` | $15 | $75 | 200K | Advanced coding, agentic |
| **Opus 4** | `claude-opus-4-20250514` | $15 | $75 | 200K | Complex analysis |
| **Sonnet 4.5** | `claude-sonnet-4-5-20250514` | $3 | $15 | 200K | Best value for complex tasks |
| **Sonnet 4** | `claude-sonnet-4-20250514` | $3 | $15 | 200K | Balanced performance |
| **Haiku 4.5** | `claude-haiku-4-5-20250514` | $1 | $5 | 200K | Fast, low-cost production |
| **Haiku 3.5** | `claude-3-5-haiku-20241022` | $0.80 | $4 | 200K | Ultra-cheap, still capable |
| **Haiku 3** | `claude-3-haiku-20240307` | $0.25 | $1.25 | 200K | Cheapest classification/scoring |

**MTok = Million tokens (~750K words)**

### Model Selection Guide

```
Classification/Scoring → Haiku 3 ($0.25/MTok) 
High-volume automation → Haiku 4.5 ($1/MTok)
General tasks/coding   → Sonnet 4.5 ($3/MTok)
Critical decisions     → Opus 4.5 ($15/MTok)
```

## Messages API

### Basic Request

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Explain quantum computing in 3 sentences."}
    ]
  }'
```

### With System Prompt

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "system": "You are a concise technical writer. Respond in bullet points.",
    "messages": [
      {"role": "user", "content": "What are the benefits of microservices?"}
    ]
  }'
```

### Multi-turn Conversation

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "What is Python?"},
      {"role": "assistant", "content": "Python is a high-level programming language known for readability."},
      {"role": "user", "content": "Show me a hello world example."}
    ]
  }'
```

## Structured Output (JSON Mode)

Force JSON output by specifying in system prompt and using `prefill`:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "system": "Extract entities as JSON. Schema: {\"people\": [], \"places\": [], \"orgs\": []}",
    "messages": [
      {"role": "user", "content": "Tim Cook announced Apple will open a store in Tokyo."},
      {"role": "assistant", "content": "{"}
    ]
  }'
```

The assistant prefill `{` forces JSON output continuation.

## Vision (Image Analysis)

```bash
# Base64 image
IMAGE_B64=$(base64 -w0 image.png)

curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d "{
    \"model\": \"claude-sonnet-4-5-20250514\",
    \"max_tokens\": 1024,
    \"messages\": [{
      \"role\": \"user\",
      \"content\": [
        {\"type\": \"image\", \"source\": {\"type\": \"base64\", \"media_type\": \"image/png\", \"data\": \"$IMAGE_B64\"}},
        {\"type\": \"text\", \"text\": \"Describe this image.\"}
      ]
    }]
  }"

# URL image
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "messages": [{
      "role": "user",
      "content": [
        {"type": "image", "source": {"type": "url", "url": "https://example.com/image.jpg"}},
        {"type": "text", "text": "What is in this image?"}
      ]
    }]
  }'
```

## Tool Use (Function Calling)

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "City name"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
          },
          "required": ["location"]
        }
      }
    ],
    "messages": [
      {"role": "user", "content": "What is the weather in Sydney?"}
    ]
  }'
```

Response contains `tool_use` block:
```json
{
  "content": [{
    "type": "tool_use",
    "id": "toolu_01ABC...",
    "name": "get_weather",
    "input": {"location": "Sydney", "unit": "celsius"}
  }]
}
```

Feed result back:
```json
{
  "messages": [
    {"role": "user", "content": "What is the weather in Sydney?"},
    {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_01ABC...", "name": "get_weather", "input": {"location": "Sydney"}}]},
    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_01ABC...", "content": "22°C, partly cloudy"}]}
  ]
}
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | string | required | Model ID |
| `max_tokens` | int | required | Max output tokens (1-4096) |
| `messages` | array | required | Conversation messages |
| `system` | string | optional | System prompt |
| `temperature` | float | 1.0 | 0.0=deterministic, 1.0=creative |
| `top_p` | float | optional | Nucleus sampling (alt to temp) |
| `top_k` | int | optional | Top-k sampling |
| `stop_sequences` | array | optional | Stop generation at these strings |
| `stream` | bool | false | Enable SSE streaming |
| `tools` | array | optional | Available tools/functions |
| `tool_choice` | object | optional | Force tool use |

### Temperature Guidelines

```
0.0 → Deterministic (code, math, extraction)
0.3 → Focused creative (rewriting, summaries)
0.7 → Balanced (general tasks)
1.0 → High creativity (brainstorming)
```

## Streaming

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "stream": true,
    "messages": [{"role": "user", "content": "Write a short poem."}]
  }'
```

Returns Server-Sent Events (SSE):
```
event: content_block_delta
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"The"}}
```

## Extended Thinking

For complex reasoning, enable extended thinking:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 16000,
    "thinking": {
      "type": "enabled",
      "budget_tokens": 10000
    },
    "messages": [{"role": "user", "content": "Solve this complex math problem..."}]
  }'
```

## Batch API (50% Discount)

For non-urgent requests, use batch API at half price:

```bash
# Create batch
curl https://api.anthropic.com/v1/messages/batches \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "requests": [
      {
        "custom_id": "req-1",
        "params": {
          "model": "claude-sonnet-4-5-20250514",
          "max_tokens": 1024,
          "messages": [{"role": "user", "content": "Hello"}]
        }
      }
    ]
  }'

# Check status
curl https://api.anthropic.com/v1/messages/batches/{batch_id} \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

## Prompt Caching

Cache large prompts to reduce repeated input costs:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: prompt-caching-2024-07-31" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250514",
    "max_tokens": 1024,
    "system": [
      {
        "type": "text",
        "text": "<very long document content here...>",
        "cache_control": {"type": "ephemeral"}
      }
    ],
    "messages": [{"role": "user", "content": "Summarize the document."}]
  }'
```

Cache pricing:
- Write: 1.25x base input price (one-time)
- Read: 0.1x base input price (90% savings!)
- TTL: 5 minutes (refreshed on use)

## Rate Limits

Limits vary by tier. Typical defaults:

| Tier | Requests/min | Tokens/min | Tokens/day |
|------|--------------|------------|------------|
| Free | 5 | 20,000 | 300,000 |
| Tier 1 | 50 | 40,000 | 1,000,000 |
| Tier 2 | 1,000 | 80,000 | 2,500,000 |
| Tier 3 | 2,000 | 160,000 | 5,000,000 |
| Tier 4 | 4,000 | 400,000 | 10,000,000 |

Rate limit headers in response:
- `anthropic-ratelimit-requests-limit`
- `anthropic-ratelimit-requests-remaining`
- `anthropic-ratelimit-tokens-limit`
- `anthropic-ratelimit-tokens-remaining`

## Error Handling

| Status | Error | Action |
|--------|-------|--------|
| 400 | `invalid_request_error` | Fix request format |
| 401 | `authentication_error` | Check API key |
| 403 | `permission_error` | Check access/quota |
| 429 | `rate_limit_error` | Exponential backoff |
| 500 | `api_error` | Retry with backoff |
| 529 | `overloaded_error` | Retry after delay |

### Retry Pattern

```bash
#!/bin/bash
max_retries=3
retry_delay=1

for i in $(seq 1 $max_retries); do
  response=$(curl -s -w "\n%{http_code}" ...)
  status=$(echo "$response" | tail -1)
  
  if [[ "$status" == "200" ]]; then
    echo "$response" | head -n -1
    exit 0
  elif [[ "$status" == "429" || "$status" == "529" ]]; then
    sleep $((retry_delay * i))
  else
    echo "Error: $status" >&2
    exit 1
  fi
done
```

## Cost Optimization Tips

1. **Use Haiku for simple tasks** - Classification, extraction, routing at $0.25-1/MTok
2. **Reserve Opus for critical work** - 15x more expensive than Sonnet
3. **Enable caching** - 90% savings on repeated context
4. **Use batch API** - 50% off for async workloads
5. **Minimize context** - Don't send full history every request
6. **Set appropriate max_tokens** - Lower = cheaper, prevents runaway
7. **Stream for UX** - Same cost, better perceived performance

## Commands

### Quick test
```bash
skills/anthropic/scripts/anthropic-chat.sh "Hello, Claude!"
```

### With model selection
```bash
skills/anthropic/scripts/anthropic-chat.sh "Classify this sentiment: Great product!" "claude-3-haiku-20240307"
```

## Response Format

```json
{
  "id": "msg_01ABC...",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Hello! How can I help?"}
  ],
  "model": "claude-sonnet-4-5-20250514",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 12,
    "output_tokens": 8
  }
}
```

## Notes

- All models support 200K token context window
- Vision available on all current models
- Tool use requires proper JSON schema definitions
- Extended thinking uses additional tokens (budget counted toward output)
- Batch results available within 24 hours
