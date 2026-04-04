---
# Cost Estimation Addendum — Decomposer Skill
# Extends SKILL.md Step 1 (DECOMPOSE) with API cost estimates

## Per-Task Cost Block
When decomposing, add to each task:
```json
{
  "estimated_cost": {
    "api_calls": {
      "dfs": 0,
      "anthropic": 1,
      "brightdata": 0,
      "external_http": 0
    },
    "estimated_usd_aud": 0.00,
    "external_calls_allowed": true
  }
}
```

## Estimation Rates (AUD — LAW II)
| Provider | Per Call | Notes |
|----------|----------|-------|
| DFS | $0.016 | ~$0.01 USD × 1.6 |
| Anthropic Haiku | $0.005 | research-1, test-4, devops-6 |
| Anthropic Sonnet | $0.037 | build-2, build-3, review-5, main |
| Anthropic Opus | $0.24 | architect-0 only |
| Bright Data | $0.0012 | per record |
| External HTTP | $0.00 | scraping, public APIs |

## Plan Summary Table (show before Dave approves)
| Provider | Est. Calls | Est. Cost (AUD) |
|----------|-----------|----------------|
| DFS      | 0         | $0.00           |
| Anthropic| 0         | $0.00           |
| Bright Data | 0      | $0.00           |
| HTTP     | 0         | $0.00           |
| **TOTAL**| | **$0.00** |

## Guardrail Rule
If actual calls exceed estimate by >20% on any provider → consumer pauses and requests Dave authorisation via evo_auth_requests table.
GO → raise ceiling 50%, resume. STOP → task fails.

## Minimum Estimate Rules
- Every sub-agent invocation = minimum 1 Anthropic call
- research-1, test-4, devops-6 = Haiku rate
- build-2, build-3, review-5 = Sonnet rate
- architect-0 = Opus rate (flag high complexity explicitly)
---
