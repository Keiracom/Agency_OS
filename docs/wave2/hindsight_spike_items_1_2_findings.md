# Hindsight Verification Spike — Items 1 + 2

**Agent:** scout
**Dispatched by:** elliot (PHASE 2.1 Hindsight Verification Spike)
**Date:** 2026-05-24
**Items covered:** (1) REPO HEALTH, (2) BENCHMARK VALIDITY
**Items NOT covered (handed back per dispatch):** 3 multi-tenancy, 4 fastembed, 5 BYOK routing, 6 domain mapping — engineer-tier validation, route to Atlas/Orion.
**Mandate:** LAW XIV raw-output, verbatim citations, no summary-only.

---

## SECTION A — REPO HEALTH (item 1)

### A.1 Repo identity + license — VERIFIED MIT

`GET /repos/vectorize-io/hindsight` returned the following verbatim fields:

```
"name":"hindsight"
"full_name":"vectorize-io/hindsight"
"description":"Hindsight: Agent Memory That  Learns"
"created_at":"2025-10-30T11:49:48Z"
"updated_at":"2026-05-24T13:28:31Z"
"pushed_at":"2026-05-22T22:38:28Z"
"homepage":"https://hindsight.vectorize.io/"
"stargazers_count":14377
"forks_count":820
"watchers_count":14377
"subscribers_count":41
"open_issues_count":141
"language":"Python"
"has_issues":true
"has_discussions":true
"archived":false
"disabled":false
"default_branch":"main"
"topics":["agentic-ai","agents","ai-memory","memory"]
"license":{"key":"mit","name":"MIT License","spdx_id":"MIT","url":"https://api.github.com/licenses/mit"}
```

**MIT license confirmed** (`"spdx_id":"MIT"`).
**Repo age:** created 2025-10-30 — ~7 months old at probe time.
**Stars:** 14,377 (high — material community interest).
**Forks:** 820. **Subscribers (watchers):** 41.

### A.2 Contributor base — heavy Vectorize-employee core + meaningful community tail

Top contributors from `GET /repos/vectorize-io/hindsight/contributors` (verbatim `login,contributions`):

```
nicoloboschi      907   (Vectorize employee — Nicoló Boschi, co-author of paper)
benfrank241       125   (Ben Frank)
cdbartholomew      69   (Chris Bartholomew, Vectorize employee — paper co-author)
r266-tech          31
DK09876            31
dcbouius           24
slayoffer          21
chrislatimer       18   (Chris Latimer, Vectorize CEO — paper first author)
dependabot[bot]    18
mrkhachaturov       9
xmh1011             8
octo-patch          6
kagura-agent        5
youchi1             4
voarsh2             4
aliu-ronin          4
akhater             4
Rutimka             4
franchb             4
GodsBoy             4
Aldoustheorchestrator 4
bjornslib           3
fabioscarsi         3
vanvuongngo         3
grimmjoww           3
harryplusplus       3
abix5               2
csfet9              2
ooa-andera          2
beordie             2
```

**Read-out:**
- 4 of top 8 contributors are Vectorize-affiliated (nicoloboschi, cdbartholomew, chrislatimer, benfrank241 — `ben.bartholomew@vectorize.io` appears in commit emails) — confirms **vendor-driven project**, not community-led.
- 25+ distinct community contributors with ≥2 contributions — non-trivial community participation for a 7-month-old repo.
- Dependabot active — automated security/dep updates wired in.

### A.3 Commit cadence (last 90 days, 2026-02-23 → 2026-05-24) — VERY HIGH

`GET /repos/vectorize-io/hindsight/commits?since=2026-02-23` paginated:

```
TOTAL_COMMITS_LAST_90D: 901
```

**Read-out:** 901 commits in 90 days = ~10 commits/day average. This is **emphatically not a zombie project** — it is one of the more actively developed memory-system repos on GitHub at this scale.

Note: the per-author breakdown returned only the most-recent paginated page (30 commits, all distinct authors) — the high diversity in that single page corroborates broad-base activity, not a single-author push.

### A.4 Issue volume + responsiveness (last 90 days) — STRONG

`GET /repos/vectorize-io/hindsight/issues?state=all&since=2026-02-23` paginated:

```
TOTAL_ISSUES_LAST_90D: 323
  open:    78
  closed: 245
  closed time-to-close median: 1.6d
  closed time-to-close p90:   10.6d
```

10 most-recent OPEN issues (verbatim):

```
#1719  2026-05-24  Zombie worker tasks permanently block consolidation after container re
#1717  2026-05-24  FlashRank ONNX reranker: glibc allocator retains ~50MB/recall, RSS gro
#1715  2026-05-23  Add per-bank consolidation slot allocation (`HINDSIGHT_API_WORKER_CONS
#1707  2026-05-22  VectorChord recall may over-expand semantic/BM25 candidates and degrad
#1706  2026-05-21  feat: add mode override parameter to mental model refresh endpoint
#1681  2026-05-21  Windows: npx command not found when starting Control Plane UI
#1680  2026-05-21  Discussion: Narrator line ties first-person attribution to banks.name
#1679  2026-05-21  Bug: delta-mode initial refresh skips all pre-existing facts when ment
#1677  2026-05-20  control-plane: SDK close errors logged as 'Value is not JSON serial
#1671  2026-05-20  Async operations need poison quarantine / degraded queue health
```

10 most-recently-closed issues (verbatim) showing time-to-close:

```
#1708  open->closed=  0.2d  HINDSIGHT_API_HEALTH_URL default ignores HINDSIGHT_API_PORT
#1658  open->closed=  2.0d  API Pod and Worker Pod Fail to Start
#1647  open->closed=  1.4d  Can't use opencode-go as LLM provider
#1646  open->closed=  1.7d  feat(config): per-operation LLM provider/model endpoints
#1644  open->closed=  2.3d  Gemma 4 <thought> tags cause JSON parse error in openai_compatible_llm
#1641  open->closed=  3.2d  [Bug] hindsight-embed local_embedded fails to start: TypeError: FastMCP()
#1637  open->closed=  4.3d  openai-codex provider should refresh OAuth access tokens automatically
#1619  open->closed=  8.9d  Consolidation fails if observation config is set to "Server Default"
#1616  open->closed=  6.2d  Add HINDSIGHT_API_WORKER_ID tip to api quickstart
#1597  open->closed=  0.9d  --daemon mode ignores --port flag, hardcodes DEFAULT_DAEMON_PORT=8889
```

**Read-out:** median issue close in 1.6 days. Issue numbers in #1700s show ~1,719 lifetime issues in ~7 months → very high churn. Recent OPEN issues are technical/operational (worker quarantine, ONNX memory leak, VectorChord recall) — the kind of detail you only see in a project under heavy real production load.

### A.5 Releases + version cadence — VERY HIGH

`GET /repos/vectorize-io/hindsight/tags` (latest 30 tags):

```
v0.6.2  (sha 8b10231b)  -- 2026-05-14 release
v0.6.1  (sha 0f7c5e89)
v0.6.0  (sha b967e1c8)
v0.5.6  (sha e9b18733)
v0.5.5  (sha c308e473)
v0.5.4  (sha 76a1bfa5)
v0.5.3  (sha 6ae6663c)
v0.5.2  (sha 712a8628)
v0.5.1  (sha aeb0c8b5)
v0.5.0  (sha c5091d29)
v0.4.22 (sha d7f6723546…)
... down to v0.4.3 in the first page
```

Latest release `v0.6.2` published `2026-05-14T20:27:52Z` by `github-actions[bot]` — automated release pipeline. Going from `v0.4.3` (lowest visible) to `v0.6.2` inside this paginated window suggests **dozens of versioned releases inside the 7-month repo lifetime**. Release cadence is **multiple per week**.

### A.6 Active vs zombie verdict — ACTIVELY MAINTAINED (high confidence)

Empirical evidence:
- 901 commits last 90 days
- 1.6-day median issue close time, 245 issues closed in 90 days
- Latest release 10 days before probe (v0.6.2 2026-05-14)
- Most-recent commit 2 days before probe (`pushed_at 2026-05-22`)
- Vendor-employee core (4 of top 8 contributors) + meaningful community tail
- Dependabot wired in, GitHub Actions auto-releases

**This is the opposite of a zombie project.** Risk is *not* abandonment. Risks worth flagging are: (a) vendor-driven roadmap (Vectorize commercial product), (b) breaking changes between weekly minor releases — likely high churn in API.

---

## SECTION B — BENCHMARK VALIDITY (item 2)

### B.1 Is LongMemEval a published benchmark? — YES (ICLR 2025)

From `arxiv.org/abs/2410.10813`:

> **Title:** "LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory"
> **Authors:** Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, Dong Yu
> **Conference:** ICLR 2025
> **Test set:** "500 meticulously curated questions embedded within freely scalable user-assistant chat histories"

Verbatim 5 core abilities tested:
> "information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention"

A successor benchmark `LongMemEval-V2` exists at `arxiv.org/html/2605.12493v1` ("Evaluating Long-Term Agent Memory Toward Experienced Colleagues" — 25M/115M token tiers). Not yet adopted as the dominant leaderboard.

### B.2 CRITICAL CAVEAT — LongMemEval is CONVERSATIONAL, not agentic-SE memory

Verbatim from the paper: the benchmark format is *"freely scalable user-assistant chat histories"* — multi-turn conversational dialogue between a user and a chat assistant.

The 5 abilities (info extraction, multi-session reasoning, temporal reasoning, knowledge updates, abstention) are all assessed against **chat-dialogue input**.

**No mention of agentic software-engineering tasks, code editing, file I/O, repo state, or multi-step tool-use traces** in the benchmark.

**Implication for Agency OS:** Hindsight's 91.4% score validates LongMemEval-style conversational recall. It does **NOT** directly validate agentic-SE memory (agent task graphs, KEI dispatch history, PR review chains, build/test/deploy traces). The Memory Abstraction Layer V1 use case is agentic-SE — closer to LongMemEval-V2's "experienced colleagues" framing than LongMemEval-V1. This is a methodological gap worth raising in the deliberation, not a disqualification.

### B.3 Where is Hindsight's submission documented? — Two sources, slightly different numbers

**Source 1 — Arxiv paper:** `arxiv.org/abs/2512.12818`

> **Title:** "Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects"
> **Authors:** Chris Latimer, Nicoló Boschi, Andrew Neeser, Chris Bartholomew, Gaurav Srivastava, Xuan Wang, Naren Ramakrishnan
> **Submitted:** December 14, 2025
> **Headline score:** "91.4%" (with scaled backbone model)
> **OSS-20B score:** 83.6%
> **Claim vs full-context GPT-4o:** "outperforming full context GPT-4o" and "consistently outperforming existing memory architectures on multi-session and open-domain questions"

The 4 of the 7 authors are Vectorize employees (Latimer = CEO, Boschi, Bartholomew). The remaining 3 (Neeser, Srivastava, Wang, Ramakrishnan) — Virginia Tech / Washington Post per the Vectorize press release. This is an academic-vendor co-authored paper, not third-party validation.

**Source 2 — `vectorize-io/hindsight-benchmarks` repo:**

Verbatim per-model breakdown from `results/longmemeval.json.gz` (extracted):

```
Hindsight (Gemini-3):  91.4%  overall accuracy
Hindsight (OSS-120B):  89.0%  overall accuracy
Hindsight (OSS-20B):   83.6%  overall accuracy
```

LoComo benchmark (separate, also tracked):

```
Hindsight (Gemini-3):  89.61%  overall accuracy
Hindsight (OSS-120B):  85.67%  overall accuracy
Hindsight (OSS-20B):   83.18%  overall accuracy
```

### B.4 Vendor's own benchmark site shows DIFFERENT numbers — flag for deliberation

From `benchmarks.hindsight.vectorize.io`:

```
LongMemEvalS:   94.6%
LoComo10:       92%
PersonaMem32K:  86.6%
BEAM100K:       75%
BEAM1M:         73.9%
LifeBenchEN:    71.5%
BEAM500K:       71.1%
BEAM10M:        64.1%
```

**Internal inconsistency:** Vectorize claims 91.4% in the Dec-2025 press release + arxiv paper, but their own benchmark dashboard now claims 94.6% on the same benchmark. Either:
- The dashboard is updated with newer results post-paper, or
- The benchmark methodology differs (different split, different model).

Either way: the "91.4%" claim Viktor cited is the paper figure. The dashboard figure is unverified-by-paper.

### B.5 Competitor leaderboard positioning — CONTESTED

From the WebSearch results:

**ByteRover competitor benchmark page (`byterover.dev/blog/benchmark_ai_agent_memory_real_production_byterover_top_market_accuracy_longmemeval`):**

> "ByteRover scores 92.2% overall accuracy, ahead of Hindsight (89.6%), Memobase (75.8%), Zep (75.1%), Mem0 (66.9%), and OpenAI Memory (52.9%)"

ByteRover ranks Hindsight at **89.6%** in their re-evaluation — 1.8pp below Hindsight's own paper claim. Possible explanations: ByteRover used the OSS-120B config (which Hindsight's own results show as 89.0%), not the Gemini-3 config. Worth noting either way: **the 91.4% is a best-case figure that depends on Gemini 3 Pro Preview (proprietary, not OSS) at the backbone.**

**OMEGA leaderboard (`omegamax.co/benchmarks`):**

> "OMEGA scores 95.4% (466/500) at 50ms retrieval"

OMEGA claims a higher score than Hindsight. No idea if it's overfitted, but the leaderboard is *not* a clean "Hindsight is #1" picture even at the headline number.

**Memoria (MatrixOrigin blog Apr 2026):**

> "Memoria retrieval supported up to 88.78% overall accuracy on LongMemEval_s"

Memoria sits ~3pp behind Hindsight (Gemini-3) but ahead of Hindsight (OSS-20B).

### B.6 Methodology disclosure — partial

From `github.com/vectorize-io/hindsight-benchmarks`:

- Result JSON files exist: `results/longmemeval.json.gz`, `results/locomo.json.gz`
- `benchmark-runner/benchmark_models.json` lists model configs
- `benchmark-runner/quality_benchmark/locomo_quality.json` exists
- **But eval scripts + prompts + traces** are not on the public surface of this repo per the fetch — the GitHub fetch says these live "in the main Hindsight repository" (`vectorize-io/hindsight`). I did not deeply audit those.

**Footnote — benchmarks repo lacks LICENSE (Max catch, 2026-05-24):** `GET /repos/vectorize-io/hindsight-benchmarks` returns `"license": null` (verified independently 2026-05-24 by scout; repo `created_at: 2025-12-01T10:05:36Z`). The main `vectorize-io/hindsight` runtime repo is MIT (Section A.1) but the **benchmarks repo we rely on for source verification of the 91.4% claim is unlicensed**. Downstream redistribution rights for the result JSON files (`results/longmemeval.json.gz`, `results/locomo.json.gz`) + inclusion in derivative benchmarks are ambiguous in the absence of an explicit licence grant. Worth raising with Vectorize before any third-party comparative-benchmark publication that re-uses these files. License-parity gap relative to the runtime repo.

**Verdict on validity:** The 91.4% LongMemEval claim is:
- ✅ Sourced from a real ICLR-2025-published benchmark
- ✅ Documented in an arxiv paper (Dec 2025) with named academic co-authors
- ✅ Reproducible-in-principle via the published `hindsight-benchmarks` repo
- ⚠️ Best-case config (Gemini 3 Pro Preview backbone — proprietary, costly)
- ⚠️ Vendor-published, not independently peer-reviewed yet (arxiv, not journal)
- ⚠️ Competitor leaderboards show Hindsight ranked behind OMEGA (95.4%) and behind ByteRover (92.2%) on the same benchmark
- ⚠️ Hindsight's own dashboard shows a different higher number (94.6%) than the paper (91.4%) — internal inconsistency
- ⚠️ **Benchmarks repo unlicensed** — redistribution rights for the result JSON files unclear (license-parity gap vs the MIT runtime repo — see footnote above)
- ❌ **NOT directly applicable to agentic-SE memory** — LongMemEval tests chat-assistant conversational recall, not the workflow our MAL V1 is being designed for

---

## SECTION C — DELIBERATOR HAND-OFF

**Items 3-6** (multi-tenancy schema-per-tenant, fastembed local-embed, BYOK LLM routing, Hindsight↔Agency-OS domain mapping) are engineer-tier validation per the dispatch — handing back to elliot for Atlas/Orion routing.

**Surprising findings worth surfacing to the deliberators:**

1. **LongMemEval is conversational, not agentic-SE memory** (Section B.2). The most-cited validation of Hindsight does not directly map to MAL V1's actual use case. LongMemEval-V2 (2605.12493) is closer to the right benchmark but Hindsight has no published submission there.
2. **91.4% requires Gemini 3 Pro Preview backbone** (Section B.3). OSS-only deployment gives 89.0% (120B) / 83.6% (20B). If our BYOK routing constraint forces OSS-only, expect ~5-8pp drop.
3. **Vendor leaderboard has internal inconsistency** (B.4) — paper says 91.4%, dashboard says 94.6%. Worth asking Vectorize for clarification before treating either as load-bearing.
4. **OMEGA (95.4%) and ByteRover (92.2%) outrank Hindsight on LongMemEval** in their own reports — "Hindsight is #1" is a contested marketing claim, not a closed leaderboard finding.
5. **Repo health is genuinely strong** (Section A.6) — 901 commits/90d, 1.6d median issue close. Adoption risk is *not* abandonment; it's API churn (weekly releases) and vendor-driven roadmap.

**Recommendation lane (scout's own — not authoritative):** the verification *does not disqualify* Hindsight, but the headline "91.4% on LongMemEval" should be re-framed in deliberation as "best-case conversational-recall score with proprietary backbone — agentic-SE-memory fitness still unproven."

---

## SOURCES (verbatim URLs)

- https://github.com/vectorize-io/hindsight (repo + license + commit/issue/release data via gh api)
- https://github.com/vectorize-io/hindsight-benchmarks (results JSON files)
- https://arxiv.org/abs/2410.10813 (LongMemEval paper, ICLR 2025)
- https://arxiv.org/abs/2512.12818 (Hindsight paper, "Hindsight is 20/20", Dec 2025)
- https://arxiv.org/html/2605.12493v1 (LongMemEval-V2)
- https://benchmarks.hindsight.vectorize.io/ (vendor dashboard)
- https://www.byterover.dev/blog/benchmark_ai_agent_memory_real_production_byterover_top_market_accuracy_longmemeval (competitor leaderboard)
- https://omegamax.co/benchmarks (OMEGA leaderboard)
- https://venturebeat.com/data/with-91-accuracy-open-source-hindsight-agentic-memory-provides-20-20-vision (VentureBeat coverage — fetch 429'd, not used as primary source)
- https://www.morningstar.com/news/pr-newswire/20251216ph48348/vectorize-breaks-90-on-longmemeval-with-open-source-ai-agent-memory-system (Dec 2025 Vectorize press release — title corroborated)
- https://medium.com/@matrixorigin-database/benchmarking-memoria-on-longmemeval-strong-memory-retrieval-clear-reader-separation-ee6c89c75d76 (Memoria comparison)
