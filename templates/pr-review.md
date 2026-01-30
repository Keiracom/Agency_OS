# PR Review Template

## Purpose
Systematic checklist for reviewing Pull Requests with focus on security, quality, and maintainability.

## Input Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `PR_URL` | ✅ | GitHub PR URL (e.g., `https://github.com/org/repo/pull/123`) |
| `REPO_NAME` | ✅ | Repository name |
| `PR_NUMBER` | ✅ | PR number |
| `REVIEW_DEPTH` | ❌ | quick/standard/thorough (default: standard) |

## Instructions

### Step 1: Gather PR Context
```bash
# Fetch PR details
gh pr view PR_NUMBER --repo REPO_NAME --json title,body,files,additions,deletions,author

# Get the diff
gh pr diff PR_NUMBER --repo REPO_NAME
```

### Step 2: Run Through Checklist

#### 🔒 Security Review
- [ ] No secrets/credentials committed (API keys, passwords, tokens)
- [ ] No SQL injection vulnerabilities
- [ ] Input validation on user-provided data
- [ ] Auth/authz changes reviewed carefully
- [ ] Dependencies updated are from trusted sources
- [ ] No sensitive data logged

#### 🧪 Testing
- [ ] Tests added for new functionality
- [ ] Existing tests pass
- [ ] Edge cases covered
- [ ] Test coverage maintained or improved
- [ ] Integration tests if needed

#### 📚 Documentation
- [ ] README updated if needed
- [ ] API docs updated for endpoint changes
- [ ] Code comments for complex logic
- [ ] CHANGELOG entry if applicable
- [ ] Migration guide for breaking changes

#### 💥 Breaking Changes
- [ ] API contracts preserved (or versioned)
- [ ] Database migrations are reversible
- [ ] Feature flags for risky changes
- [ ] Deprecation warnings added before removal
- [ ] Client impact assessed

#### 🏗️ Code Quality
- [ ] Follows project conventions
- [ ] No dead code or console.logs
- [ ] Error handling is appropriate
- [ ] No obvious performance issues
- [ ] DRY principles applied

#### 🚀 Deployment
- [ ] Environment variables documented
- [ ] Database migrations included
- [ ] Rollback plan considered
- [ ] Monitoring/alerts updated if needed

### Step 3: Summarize Findings

## Expected Output Format

```markdown
# PR Review: [PR Title]

**PR:** REPO_NAME#PR_NUMBER
**Author:** @author
**Reviewer:** @elliot
**Date:** YYYY-MM-DD

## 📊 Summary
| Aspect | Status | Notes |
|--------|--------|-------|
| Security | ✅/⚠️/❌ | |
| Tests | ✅/⚠️/❌ | |
| Docs | ✅/⚠️/❌ | |
| Breaking | ✅/⚠️/❌ | |
| Quality | ✅/⚠️/❌ | |

## 🔍 Detailed Findings

### Critical Issues (Must Fix)
- [ ] Issue 1

### Suggestions (Nice to Have)
- [ ] Suggestion 1

### Questions
- Question 1?

## 💬 Review Comments
[Specific line-by-line feedback]

## 🎯 Verdict
- [ ] ✅ **Approve** — Ready to merge
- [ ] 🔄 **Request Changes** — Needs work
- [ ] 💬 **Comment** — Questions/discussion needed
```

## Example Usage
```
@elliot Review PR https://github.com/Keiracom/agency-os/pull/42 using pr-review template
```

## Notes
- For security-sensitive repos, always use `thorough` depth
- Flag any changes to auth, payments, or PII handling
- Check if CI/CD pipeline passed before reviewing
