# src/governance/contracts/

Typed schemas for governance artefacts. Pydantic v2 BaseModel + Anthropic-compatible config (`extra="forbid"` so structured-outputs reject unknown keys).

## Schemas

| Schema | File | Purpose |
|---|---|---|
| `DirectiveContract` | `directive_contract.py` | Dave-issued directive shape (intent + context + latitude + frozen_artifacts + success_criteria + scope IN/OUT + spend cap + step0 exemption + source + task_ref) |
| `PeerReviewContract` | `peer_review_contract.py` | Bot-on-bot review verdict (concur / differ / yellow_flag) with audit evidence |
| `CompletionClaimContract` | `completion_claim_contract.py` | `[COMPLETE:<callsign>]` claim (branch + commit + verification stdout + four-store check) |

## How directives map to schemas

A typical dispatch flows through the schemas like:

```
Dave message in TG group
  ↓ classified by router.classify() (audience="dave")
  ↓ parsed into DirectiveContract by parent bot
  ↓ dispatched as JSON to clone inbox (preserves the contract shape)

Clone executes
  ↓ produces PR
  ↓ peer bot writes PeerReviewContract referencing target_pr
  ↓ on concur: clone writes CompletionClaimContract → outbox

Parent bot reads outbox
  ↓ verifies four_store_complete()
  ↓ if all stores written: surface CompletionClaimContract.pr_url to Dave
  ↓ if not: dispatch follow-up to fill missing stores
```

## Usage with Anthropic native structured outputs

Each schema is passive — it doesn't construct a client. Pass to Anthropic's structured-outputs API like:

```python
from src.governance.contracts import DirectiveContract
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    messages=[{"role": "user", "content": dave_text}],
    tools=[{
        "type": "custom",
        "name": "parse_directive",
        "input_schema": DirectiveContract.model_json_schema(),
    }],
)
parsed = DirectiveContract.model_validate(response.content[0].input)
```

## Validation

Run `pytest tests/governance/test_contracts.py` to verify each schema:
- Accepts a sample Dave directive (DirectiveContract).
- Rejects unknown fields (`extra="forbid"`).
- Computes `four_store_complete()` correctly (CompletionClaimContract).
- Status enum constraints fire (PeerReviewContract).

## Phase 1 dispatch

GOV-PHASE1-TRACK-B / B3. Built alongside `router.py` (B1) and `coordinator.py` (B2). All three services are independent at the file level; integration happens at the parent bot level (router classifies → coordinator claims + DSAE merges → contracts validate / serialize).
