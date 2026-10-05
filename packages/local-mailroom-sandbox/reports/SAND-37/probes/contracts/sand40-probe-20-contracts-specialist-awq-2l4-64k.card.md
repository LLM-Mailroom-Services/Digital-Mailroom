# Contracts — 2× L4 · C32 · n=20

**Run:** `sand40-probe-20-contracts-specialist-awq-2l4-64k` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | contracts_specialist |
| Prompt | contracts_specialist_v33_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 6,144 |
| Input cap (max_input_chars) | 128,000 |
| Optimized long-document settings | yes |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 1.0 |
| Length re-samples | 1 |
| Chunk window (chars) | 120000 |
| Chunk overlap (chars) | 8000 |
| hf_overrides | `{"rope_parameters": {"factor": 2.0, "original_max_position_embeddings": 32768, "rope_theta": 1000000, "rope_type": "yarn"}}` |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 20 docs (fingerprint 704bac6c015d) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 65536 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-probe-20-contracts-specialist-awq-2l4-64k` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 20 |
| Spec hash | 664d0316… |
| **Time** |  |
| Wall (busy) | 105.57 s |
| GPU seconds | 105.73 s |
| Cold boot | 0.16 s |
| **Cost** |  |
| Busy-window GPU $ | $0.046920 |
| Billed GPU $ (incl. boot) | $0.046990 |
| Idle $ | $0.021446 (48.25 s) |
| Cost per document | $0.002346 |
| Cost per ok document | $0.002346 |
| Cost per 1M tokens | $0.2658 |
| **Tokens** |  |
| Prompt tokens | 142,889 |
| Completion tokens | 33,650 (19.1%) |
| Total tokens | 176,539 |
| Tokens per document | 8,827 |
| Completion p95 / max (ok docs) | 2,585 / 2,902 |
| **Throughput** |  |
| Tokens / second | 1,672.3 |
| Tokens / second per L4 | 836.1 |
| Documents / minute | 11.37 |
| **Latency (per document, ok rows)** |  |
| Mean | 91.70 s |
| p50 | 94.93 s |
| p95 | 128.94 s |
| Max | 135.37 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 17.37× of 32 |
| Slot occupancy | 54.3% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 10 / 10 |
| Mean TTFT per replica | 10.467 s / 18.330 s |
| Prefix-cache hit per replica | 34.1% / 23.3% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.6703 (sd 0.126) |
| Score min / max | 0.4138 / 0.8571 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 20 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 17 |
| Micro precision / recall / F1 | 0.667 / 0.652 / 0.659 |
| Metadata value checks | 36 / 47 |
| Suite field score (mean) | not captured |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-98ff556893f1a98f` | yes | 0.8571 | 29.8 | 2506 | 361 | — |
| 2 | `DOC-440a54573c24b918` | yes | 0.8000 | 39.8 | 2799 | 608 | — |
| 3 | `DOC-ade03c57c5f78e21` | yes | 0.4286 | 67.6 | 3399 | 1379 | — |
| 4 | `DOC-d1c45d175a8abeb5` | yes | 0.7143 | 75.1 | 6157 | 911 | — |
| 5 | `DOC-9e063c6e3baf1233` | yes | 0.6207 | 76.6 | 6792 | 1606 | — |
| 6 | `DOC-9696c5996f24d85d` | yes | — | 83.4 | 3683 | 1078 | — |
| 7 | `DOC-adad5ef793c0e409` | yes | 0.5806 | 83.7 | 8759 | 1819 | — |
| 8 | `DOC-06229aa6571f9d46` | yes | 0.7826 | 90.3 | 5460 | 2021 | — |
| 9 | `DOC-dfa5c8eb1e7b837c` | yes | 0.7500 | 90.6 | 5361 | 2029 | — |
| 10 | `DOC-ba6d7a0ea5100bbb` | yes | 0.7778 | 94.9 | 7587 | 1334 | — |
| 11 | `DOC-c68a4dd90660c113` | yes | 0.7059 | 95.0 | 12194 | 2183 | — |
| 12 | `DOC-5892b6dc609c8d0f` | yes | — | 96.4 | 6912 | 1384 | — |
| 13 | `DOC-a2ce7adbf6f5cb8d` | yes | 0.8148 | 98.3 | 6035 | 2300 | — |
| 14 | `DOC-55df050fcb737129` | yes | 0.4138 | 99.8 | 4767 | 1469 | — |
| 15 | `DOC-2ca7b08d2d439f1e` | yes | — | 109.9 | 8413 | 1729 | — |
| 16 | `DOC-6712aa595cfe3e2c` | yes | 0.6316 | 111.5 | 9648 | 1769 | — |
| 17 | `DOC-99ca00712a84f039` | yes | 0.6154 | 112.4 | 4643 | 2902 | — |
| 18 | `DOC-f9b36fee351217c2` | yes | 0.5263 | 114.5 | 7237 | 1853 | — |
| 19 | `DOC-c30c293d38a2cd8b` | yes | 0.7097 | 128.9 | 25772 | 2330 | — |
| 20 | `DOC-fca31a55b1d526ea` | yes | 0.6667 | 135.4 | 4765 | 2585 | — |

_Generated 2026-10-01T04:18:04+00:00 by `sandbox run card`. Machine-readable twin: `sand40-probe-20-contracts-specialist-awq-2l4-64k.card.json`._
