---
name: slack-file-upload
description: Upload a file (e.g. .md audit doc) as a Slack file attachment to a named channel.
---

# Slack File Upload

Upload a file as a Slack attachment. Wraps `files_upload_v2` (3-step external upload API) via the slack_sdk WebClient.

## When to invoke

- Posting audit docs to #ceo (e.g. `docs/audits/*.md`)
- Sharing pipeline reports or exports to #execution or #completed_directives
- Any time a file attachment is preferable to an inline paste

## Required env vars

| Var | Source | Notes |
|-----|--------|-------|
| `SLACK_BOT_TOKEN` | `/home/elliotbot/.config/agency-os/.env` | `xoxb-...` bot token |
| `CALLSIGN` | env or `IDENTITY.md` | Prefix tag; defaults to `elliot` |

## Required bot scope

`files:write` — must be added to the Agency OS Slack App before this skill can upload. Without it the API returns `missing_scope`.

> **Status (2026-05-12):** scope not yet granted. Tests are 100% mocked. Grant scope via api.slack.com → Your Apps → Agency OS → OAuth & Permissions → Bot Token Scopes → Add `files:write` → reinstall app.

## Channel name → ID map

| Name | ID |
|------|----|
| `ceo` | `C0B2PM3TV0B` |
| `execution` | `C0B3QB0K1GQ` |
| `alerts` | `C0B2EJU53EK` |
| `completed_directives` | `C0B2U15PSEA` |
| `ops` | `C0B2UCNRJ86` |

Pass either the friendly name or the raw `C...` ID — the script resolves both.

## Invocation

```bash
python /home/elliotbot/clawd/skills/slack-file-upload/upload.py <channel> <file_path> [--title=<title>] [--comment=<comment>]
```

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `channel` | yes | Channel name (e.g. `ceo`) or ID (e.g. `C0B2PM3TV0B`) |
| `file_path` | yes | Absolute or relative path to file to upload |
| `--title=` | no | Display title shown in Slack (defaults to filename) |
| `--comment=` | no | `initial_comment` posted alongside the file |

The `[CALLSIGN_UPPER]` prefix is auto-prepended to `--comment` if not already present (mirrors `slack_relay.py` behaviour).

## Examples

```bash
# Upload audit doc to #ceo
python /home/elliotbot/clawd/skills/slack-file-upload/upload.py ceo \
    docs/audits/memory_audit_2026-05-12.md \
    --title="Memory Audit Synthesis" \
    --comment="[ELLIOT] Phase 1 complete"

# Upload to channel ID directly, no title
python /home/elliotbot/clawd/skills/slack-file-upload/upload.py C0B3QB0K1GQ \
    /tmp/report.md \
    --comment="Pipeline run summary"
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success — file uploaded and shared |
| `1` | Network or Slack API error (check stderr) |
| `2` | Missing `SLACK_BOT_TOKEN`, missing scope, or disallowed channel |
| `3` | File not found, or invalid / missing CLI arguments |

## Flow (what upload.py does internally)

`files_upload_v2` orchestrates three Slack API calls automatically:
1. `files.getUploadURLExternal` — obtains a pre-signed S3 upload URL
2. HTTP PUT to the S3 URL — streams file bytes directly
3. `files.completeUploadExternal` — associates the upload with the channel and posts `initial_comment`

The SDK hides this complexity behind a single method call.
