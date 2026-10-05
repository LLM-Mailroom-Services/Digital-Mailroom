# Qwen3-8B-AWQ specialist grid: aligned spec and run plan (SAND-037)

The specialist grid crosses three factors, 20 cells in all:

| Factor | Levels |
| --- | --- |
| Document class | correspondence, insurance claims, corporate records, contracts, merger agreements |
| Sample size | n = 20, n = 50 |
| Fleet shape | 1×L4 · C8 (one replica) and 2×L4 · C32 (two replicas, 16 per replica) |

Every cell now shares one spec, so a difference between two cells of the same class can only come
from n or the fleet shape. All 20 cells are run by two catalog runbooks:

```bash
sandbox runbook show grid-1l4   # the ten 1×L4 cells, one warm L4
sandbox runbook show grid-2l4   # the ten 2×L4 cells, one warm two-replica fleet
```

## The aligned spec

| Variable | Every cell | Source it matches |
| --- | --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, `max_model_len` 32768, `gpu_memory_utilization` 0.90 | SAND-032 |
| Engine | `awq_marlin`, fp8 KV cache, CUDA graphs [1, 2, 4, 8, 16], prefix caching, `max_num_seqs` 16 per replica, thinking off, `max_inputs` 32 | SAND-032 frozen L5 (`QWEN3-L4-LADDER-SUMMARY.md`); S2a, S2b, S3, S10 |
| Data | `mailroom-dataset` `ground_truth` @ `ed7576b6`, `split: all`, seed 42, one class bucket, so the n = 20 draw nests inside the n = 50 draw | SAND-032 S2/S3 ("nested 20 ⊂ 50 ⊂ 100") |
| Prompts | eval-environment frozen v1 stems: `*_simplified`, contracts `contracts_specialist_v33_simplified` | run-30 suite, SAND-032 S3 (except S3 correspondence) |
| Output cap | `max_tokens` 8192 for every class | grid posture |
| Temperature | 0.7 for contracts and merger; 0.1 (the vendored call-site value) for the other three | see below |
| Retries | `job.max_retries` 2 | grid posture |
| Modal app | `sandbox-vllm`, `min_containers` = `max_containers` = replicas | grid posture |

Only these vary: n (20 / 50), replicas (1 / 2) and client concurrency (8 / 32). Cost caps and wall limits
scale with n and class. `tests/test_specialist_posture.py` fails if any cell drifts from this spec, and
`sandbox runbook check` fails if any config's deploy env differs from its runbook's export block.

## The length errors: runaway decoding, not a short cap

Every LengthFinishReasonError on record is a contracts or merger document that used its entire
completion budget. Successful outputs from the same runs are far shorter:

| Run | Successful outputs: p95 / max (tokens) | Failed outputs (tokens) |
| --- | --- | --- |
| `grid-20-merger-specialist-awq-1l4` | 1,241 / 1,335 | 4,096 (cap) |
| `grid-20-merger-specialist-awq-1l4-retry` | 1,377 / 1,427 | 16,384 × 3 (cap) |
| `sand032-s3-merger50` | 1,217 / 1,695 | 6 at cap |
| `sand032-s5-merger50-maud` (MAUD prompt) | 2,209 / 3,423 | 4 at cap |
| `run-20-contracts-awq-c8` | 2,837 / 3,029 | 3 at the 8,192 cap |
| `grid-50-contracts-specialist-awq-2l4` | 2,463 / 3,559 | 8,192 × 2 (cap) |
| `sand032-s9-contracts50-bal` | 3,045 / 4,055 | 6 at cap |

Three observations point to looping generation rather than documents that need more room:

1. Raising the cap from 4,096 to 8,192 to 16,384 never cleared the failures; the 16,384 leg failed three
   documents instead of one.
2. The failing documents change from run to run. `DOC-158ec6b697211e14` failed at 4,096 on the first merger
   cell and finished normally on the retry leg, which failed three other documents.
3. Only contracts and merger fail. They are the two specialists that decode under the JSON-schema grammar
   (`langchain_agents`, `with_structured_output(method="json_schema")`). Correspondence, insurance and
   corporate records go through `agents.base` with `response_format: json_object` and have never hit a cap.

Every specialist passes `temperature=0.1` as a literal at its call site. Near-greedy decoding under a
grammar that allows unbounded arrays and strings (the merger schema's `reasoning.entries`, `parties`,
`maud_clauses`) can repeat indefinitely, and each job retry at 0.1 replays the same loop. Qwen3's model card
says not to use greedy decoding in non-thinking mode because it causes endless repetitions, and recommends
temperature 0.7.

**Fix.** Contracts and merger cells run at temperature 0.7. The vendored call sites cannot be edited (drift
guard), so `mailroom_sandbox.sampling` wraps both base `_call_structured` implementations and applies a
run-scoped `temperature` knob from the grid posture row; agents without one keep their call-site value. The
other three classes stay at 0.1, which keeps them comparable with every SAND-032 run.

**Cap.** `max_tokens` stays at 8,192 for every class: about twice the longest successful output on record
(4,055). Do not raise it. A document that still ends at 8,192 is a loop; record the count as a finding.

## Cell status

All 20 cells run. Two cells already executed under the old spec; they get `-rerun` run ids so their
committed reports stay intact.

| Class | n = 20 · 1×L4 | n = 20 · 2×L4 | n = 50 · 1×L4 | n = 50 · 2×L4 |
| --- | --- | --- | --- | --- |
| Correspondence | `grid-20-correspondence-specialist-awq-1l4` | `grid-20-correspondence-specialist-awq-2l4` | `grid-50-correspondence-specialist-awq-1l4` | `grid-50-correspondence-specialist-awq-2l4` |
| Insurance claims | `grid-20-insurance-claims-specialist-awq-1l4` | `grid-20-insurance-claims-specialist-awq-2l4` | `grid-50-insurance-claims-specialist-awq-1l4` | `grid-50-insurance-claims-specialist-awq-2l4` |
| Corporate records | `grid-20-corporate-records-specialist-awq-1l4` | `grid-20-corporate-records-specialist-awq-2l4` | `grid-50-corporate-records-specialist-awq-1l4` | `grid-50-corporate-records-specialist-awq-2l4` |
| Contracts | `grid-20-contracts-specialist-awq-1l4` | `grid-20-contracts-specialist-awq-2l4` | `grid-50-contracts-specialist-awq-1l4` | `grid-50-contracts-specialist-awq-2l4-rerun` |
| Merger agreements | `grid-20-merger-specialist-awq-1l4-rerun` | `grid-20-merger-specialist-awq-2l4` | `grid-50-merger-specialist-awq-1l4` | `grid-50-merger-specialist-awq-2l4` |

### Records the aligned grid supersedes

| Existing record | Cell | What differs from the aligned spec |
| --- | --- | --- |
| `run-20-correspondence-awq-c8` | correspondence · 20 · 1×L4 | Pinned prompt not sent (pre-`6dbf457`); rev `46a4d3c2`; plain `awq`, eager, `max_num_seqs` 256; decode 2048 |
| `run-20-contracts-awq-c8` | contracts · 20 · 1×L4 | Same prompt and data issues; plain `awq`, eager, `max_num_seqs` 256; temperature 0.1 |
| `run-20-insurance-claims-specialist-awq` | insurance · 20 · 1×L4 | Rev `46a4d3c2`, stratified `split: test`; `max_num_seqs` 6; decode 3072 |
| `run-20-corporate-records-specialist-awq` | corporate · 20 · 1×L4 | Rev `46a4d3c2`, stratified `split: test`; decode 4096; no serving export |
| `grid-20-merger-specialist-awq-1l4` and `-retry` | merger · 20 · 1×L4 | Stratified `split: train`; plain `awq`, eager, `max_num_seqs` 8; decode 4096 / 16384 at temperature 0.1 |
| `run-20-correspondence-specialist-awq` | correspondence · 20 · 2×L4 | C8, `max_num_seqs` 6, `_production` prompt |
| `grid-50-contracts-specialist-awq-1l4` (attempt) | contracts · 50 · 1×L4 | Deployed with `MAX_INPUTS=0`, served one request at a time; no result |
| `grid-50-contracts-specialist-awq-2l4` | contracts · 50 · 2×L4 | Plain `awq`; temperature 0.1 (2 LengthFinish) |
| `sand032-s3-*50` (four classes) | n = 50 · 2×L4 | Decode 2048–4096; `sandbox-vllm-sand032` app; correspondence on the `_production` prompt |

The superseded records remain the evidence for their own experiments. They are not grid cells.

## Reading the results

- The 1×L4 vs 2×L4 contrast now isolates the fleet: same engine, same draw, same prompt and decode. Client
  concurrency still differs by design (8 on one replica, 16 per replica on two), so per-replica load
  doubles along with the GPU count. SAND-032 S2a vs S2b (8 per replica on both) is the matched-load test.
- Contracts and merger ground truth is CUAD / MAUD labels, not the extraction schema, so their
  `overall_extraction_score` is near zero by construction. Score them with the CUAD clause F1 and MAUD
  accuracy scorers the SAND-032 reports use.
- Contracts and merger scores are not directly comparable with older runs at temperature 0.1.

## Reports

Every grid run exports a score & cost card, and each runbook ends with its fleet's finalized suite card,
all under `reports/SAND-37/` (layout and field list: `reports/SAND-37/README.md`):

| Artifact | Path |
| --- | --- |
| Per-run card | `reports/SAND-37/<1L4 or 2L4>/<specialist>/<run_id>.card.md` + `.card.json` |
| 1× L4 suite card | `reports/SAND-37/1L4/L4x1-SCORE-COST-CARD.md` + `.json` |
| 2× L4 suite card | `reports/SAND-37/2L4/L4x2-SCORE-COST-CARD.md` + `.json` |

Each run in the runbooks is `preflight → scrape-metrics before → start → scrape-metrics after → run card`,
so every card carries its own per-replica vLLM telemetry.

## Spend

Estimates only; the per-cell cost caps are the abort guards.

| Runbook | Warm GPU time (likely) | GPU $ (likely) | Sum of cost caps |
| --- | --- | ---: | ---: |
| `grid-1l4` | ≈ 1 h on one L4 (S3 per-L4 throughput on the same engine × 0.7 for C8, as S2a measured) | ≈ $0.80 | $5.70 |
| `grid-2l4` | ≈ 18 min on two L4s (S3 walls; one cold boot per replica) | ≈ $0.55 | $8.20 |

Neither runbook authorizes spend; approve before `modal deploy`.
