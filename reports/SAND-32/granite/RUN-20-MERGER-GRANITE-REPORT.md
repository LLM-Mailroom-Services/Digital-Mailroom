# Run report — `run-20-merger-granite` (PARTIAL: cost-cap abort at 16/20)

Modal × vLLM specialist extract: **merger_agreement_specialist on MERGER_AGREEMENT
docs** (quotas 7/7/3/2/1 from run-30-merger-specialist, train split — test has
only ~17 mergers), on **ibm-granite/granite-4.2-8b-fp8** at **concurrency 3** on
**1×L4** (MIN=MAX=1 pinned), DMR-074 `merger_agreement_specialist_simplified`
pin, 16k run-scoped decode (probe-validated fix for the 4096 LengthFinish).

| | |
| --- | --- |
| run_id | `run-20-merger-granite` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_simplified` (local DMR-074 pin) |
| engine | `ibm-granite/granite-4.2-8b-fp8`, vLLM `v0.29.0`, 1× L4, `compressed-tensors`, 32768 |
| engine flags | gpu_util=0.90, max_num_seqs=6, prefix_caching=on, enforce_eager=on, reasoning-parser=`granite` (native; `granite_thinking_parser` crash-loops 0.29.0), no tool parser |
| deploy | same R2 warm app as probes (cold boot 153 s noted once in probe report; preflight warm 1.08 s here) |
| dataset | mailroom-dataset `ground_truth`, split=train, rev `46a4d3c2`, seed 42, draw `624e026fc985` |
| git | `dde5616` (post c=8-requirement commit; run dispatched at c=3 under prior HALT revision — spec locked) |

## Headline results (PARTIAL — guard abort, no scores)

| metric | value |
| --- | --- |
| docs attempted / ok / failed / unattempted | **16 / 11 / 5 / 4** |
| abort cause | `cost_cap_usd=1.20 exceeded (est_gpu_usd=1.2866 at wall=5789.9s)` — guard worked as designed |
| wall (run) | 5789.9 s (04:05:19 → ~05:53, ~96.5 min) |
| concurrency (dispatched) | 3 (spec-locked; c=8 mandate arrived mid-run — see concurrency note) |
| est. GPU cost (guard accounting) | **$1.2866** |
| $/doc attempted / per ok | $0.0804 / $0.1170 |
| LengthFinish errors | **0** (16k decode held) |
| overall_extraction_score | **unknown** (abort pre-empted scoring; isolated path persists no items — honest gap) |

## Concurrency note (c=3 kept vs c=8 mandate)

Measured evidence for c=3 on Granite, presented per the mandate's exception
clause: (a) halt-run at c=8 serialized to **1.0×** (8 simultaneous dispatches,
completions strictly ~195 s apart; Qwen AWQ c=8 measured 5–7×); (b) boot-measured
KV pool 68,128 tokens ÷ ~20k per full-length request ≈ 3 concurrent; (c) live
engine logs during this block: **Running: 1 req, never >1, despite c=8
dispatched** — vLLM 0.29 serializes guided-JSON + Granite thinking server-side.
Killing 11-ok progress to restart at c=8 against this evidence would re-burn
~$1.30 for an identical serialization. Qwen legs stay c=8 (separate regime,
clean 5–7× precedent, zero 408s).

## Error mechanism (all 5 failures)

Thinking-leakage parse errors, e.g. `structured_output_parse_error: Invalid
json output: Okay, let's tackle this merger agreement extraction...` — the
native `granite` parser does not split thinking spans, so thinking chatter
reaches LangChain's JSON parser. Distinct from the LengthFinish solved by 16k.

## Incident: proxy 408 (1×)

`GET /v1/chat/completions -> 408 Request Timeout (duration ~82 s, execution
~5 s)` in Modal app logs — the `@web_server` proxy times out requests queued
behind multi-minute generations on the single container. 408 is NOT in the
retryable set (`{429,500,502,503,504}` + timeouts/connection) in either
`llm/retry.py` or `base_agent._is_retryable_error`, so it fails the attempt
instantly with no log — this is also the halt-run fast-fail mechanism.
Spend impact: ≤1 doc attempt (~5 s execution), negligible. Fix applied to the
next instance (correspondence-50 c=4 tune-down, later superseded — see its report).

## Concurrency proof

Serial-dominated: 16 docs × ~500 s est. serial ≈ 8000 s vs 5790 s wall ≈
**~1.4×** (far from 3× — engine single-streams guided Granite decode).

## Spend accounting (this instance)

- Billed window (guard): wall 5789.9 s × L4 $0.80/hr → **$1.2866** (over the
  $1.20 cap by triggering it — expected abort behavior, not overrun).
- Pre-flight c=3 estimate was $0.67 likely — actual 1.9× over: Granite decode
  (~19 tok/s, ~12k completions) doubles per-doc busy vs assumption. Future
  Granite legs must estimate from probe-measured rates, not Qwen tables.
