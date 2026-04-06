---
name: pr-tool
description: Create GitHub PRs with one command (LAW VIII compliance)
---
# PR Tool

Creates a branch, commits files, pushes, and opens a PR.

## Usage
```bash
./create-pr.sh <branch-name> "<commit-message>" [file1 file2 ...]
```

If no files specified, stages all changes in the commit.

## Example
```bash
cd ~/clawd/skills/pr-tool
./create-pr.sh feature/new-hook "feat: Add session hook" hooks/session-supabase/handler.ts
```

## Returns
PR URL on success, error message on failure.
