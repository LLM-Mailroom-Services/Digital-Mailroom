# Merger Agreements — 2× L4 · C32 · n=5

**Run:** `sand40-check-5-merger-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_maud_v1 |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 6,144 |
| Input cap (max_input_chars) | 54,000 |
| Optimized long-document settings | yes |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 1.0 |
| Length re-samples | 1 |
| Chunk window (chars) | 47000 |
| Chunk overlap (chars) | 6500 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 5 docs (fingerprint d411e98fb6b8) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-check-5-merger-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 5 |
| Spec hash | 596b9a2c… |
| **Time** |  |
| Wall (busy) | 284.49 s |
| GPU seconds | 284.85 s |
| Cold boot | 0.36 s |
| **Cost** |  |
| Busy-window GPU $ | $0.126441 |
| Billed GPU $ (incl. boot) | $0.126601 |
| Idle $ | $0.103923 (233.83 s) |
| Cost per document | $0.025288 |
| Cost per ok document | $0.025288 |
| Cost per 1M tokens | $0.2175 |
| **Tokens** |  |
| Prompt tokens | 556,273 |
| Completion tokens | 24,996 (4.3%) |
| Total tokens | 581,269 |
| Tokens per document | 116,254 |
| Per document: instructions + template | 20,248 (17.4%) |
| Per document: document text | 91,007 (78.3%) |
| Per document: output | 4,999 (4.3%) |
| Instruction tokens per model call | 2,469 over 41 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 5,814 / 5,814 |
| **Throughput** |  |
| Tokens / second | 2,043.2 |
| Tokens / second per L4 | 1,021.6 |
| Documents / minute | 1.05 |
| **Latency (per document, ok rows)** |  |
| Mean | 324.27 s |
| p50 | 268.80 s |
| p95 | 465.66 s |
| Max | 465.66 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.70× of 32 |
| Slot occupancy | 17.8% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 21 / 22 |
| Mean TTFT per replica | 4.828 s / 4.202 s |
| Prefix-cache hit per replica | 21.7% / 24.6% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 2 |
| **Quality** |  |
| Overall extraction score | 0.1362 (sd 0.079) |
| Score min / max | 0.0000 / 0.2353 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 5 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 56 / 79 (70.9%) |
| Micro accuracy | 13.9% |
| Precision on answered | 19.6% |
| Clean subset | 5 / 34 |
| Suite field score (mean) | not captured |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-f4e726a7f2c25494` | yes | 0.1333 | 181.2 | 80639 | 3891 | — |
| 2 | `DOC-1e016055aa435e71` | yes | 0.1250 | 247.7 | 124347 | 4470 | — |
| 3 | `DOC-52f9a5be69429299` | yes | 0.2353 | 268.8 | 119128 | 5814 | — |
| 4 | `DOC-d554890e66786170` | yes | 0.1875 | 458.0 | 109746 | 5154 | — |
| 5 | `DOC-5fa0ba13cf68b593` | yes | 0.0000 | 465.7 | 122413 | 5667 | — |

_Generated 2026-10-01T06:44:51+00:00 by `sandbox run card`. Machine-readable twin: `sand40-check-5-merger-specialist-awq-2l4.card.json`._
