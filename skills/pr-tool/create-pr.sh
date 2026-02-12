#!/bin/bash
set -e

BRANCH="$1"
MESSAGE="$2"
shift 2 2>/dev/null || true
FILES="$@"

if [ -z "$BRANCH" ] || [ -z "$MESSAGE" ]; then
  echo "Usage: create-pr.sh <branch-name> \"<commit-message>\" [files...]"
  exit 1
fi

cd /home/elliotbot/clawd

# Ensure we're on main and up to date
git fetch origin
git checkout main 2>/dev/null || git checkout master
git pull origin main 2>/dev/null || git pull origin master

# Create branch
git checkout -b "$BRANCH"

# Stage files
if [ -n "$FILES" ]; then
  git add $FILES
else
  git add -A
fi

# Commit and push
git commit -m "$MESSAGE"
git push -u origin "$BRANCH"

# Create PR
PR_URL=$(gh pr create --title "$MESSAGE" --body "Created via pr-tool skill (LAW VIII compliance)." --base main 2>&1 | grep -o 'https://github.com[^ ]*' || echo "")

if [ -n "$PR_URL" ]; then
  echo "✅ PR created: $PR_URL"
else
  echo "✅ Branch pushed: $BRANCH (PR may need manual creation)"
fi
