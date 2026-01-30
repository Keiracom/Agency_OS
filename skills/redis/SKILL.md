---
name: redis
description: Use when working with Redis cache or key-value store. Get/set keys, manage lists/sets/hashes, pub/sub messaging, caching. Triggers on "redis", "cache", "upstash", "key-value", "rate limiting", session storage.
metadata: {"clawdbot":{"emoji":"🔴","always":true,"requires":{"bins":["curl","jq"]}}}
---

# Redis 🔴

Redis in-memory database management.

## Setup

```bash
export REDIS_URL="redis://localhost:6379"
```

## Features

- Key-value operations
- Data structures (lists, sets, hashes)
- Pub/Sub messaging
- Cache management
- TTL management

## Usage Examples

```
"Get key user:123"
"Set cache for 1 hour"
"Show all keys matching user:*"
"Flush cache"
```

## Commands

```bash
redis-cli GET key
redis-cli SET key value EX 3600
redis-cli KEYS "pattern*"
```
