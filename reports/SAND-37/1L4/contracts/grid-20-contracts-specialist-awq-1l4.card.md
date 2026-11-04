# Contracts — 1× L4 · C8 · n=20

**Run:** `grid-20-contracts-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | contracts_specialist |
| Prompt | contracts_specialist_v33_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 24,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 20 docs (fingerprint 704bac6c015d) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-20-contracts-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 20 |
| Spec hash | bab88512… |
| **Time** |  |
| Wall (busy) | 299.30 s |
| GPU seconds | 299.72 s |
| Cold boot | 0.42 s |
| **Cost** |  |
| Busy-window GPU $ | $0.066510 |
| Billed GPU $ (incl. boot) | $0.066604 |
| Idle $ | $0.030657 (137.96 s) |
| Cost per document | $0.003326 |
| Cost per ok document | $0.003501 |
| Cost per 1M tokens | $0.4289 |
| **Tokens** |  |
| Prompt tokens | 123,139 |
| Completion tokens | 31,915 (20.6%) |
| Total tokens | 155,054 |
| Tokens per document | 8,161 |
| Per document: instructions + template | 2,867 (35.1%) |
| Per document: document text | 3,614 (44.3%) |
| Per document: output | 1,680 (20.6%) |
| Instruction tokens per model call | 2,867 over 19 calls |
| Token split basis | fit across documents, 4.57 chars/token |
| Completion p95 / max (ok docs) | 2,442 / 4,860 |
| **Throughput** |  |
| Tokens / second | 518.1 |
| Tokens / second per L4 | 518.1 |
| Documents / minute | 4.01 |
| **Latency (per document, ok rows)** |  |
| Mean | 67.93 s |
| p50 | 65.78 s |
| p95 | 104.92 s |
| Max | 187.84 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.07× of 8 |
| Slot occupancy | 63.4% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 20 |
| Mean TTFT per replica | 3.137 s |
| Prefix-cache hit per replica | 42.5% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 1 |
| **Quality** |  |
| Overall extraction score | 0.6307 (sd 0.143) |
| Score min / max | 0.4615 / 1.0000 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 1 / 20 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 16 |
| Micro precision / recall / F1 | 0.657 / 0.548 / 0.597 |
| Metadata value checks | 32 / 44 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 1 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-98ff556893f1a98f` | yes | 0.7500 | 33.7 | 3200 | 654 | — |
| 2 | `DOC-9696c5996f24d85d` | yes | — | 64.1 | 4377 | 1422 | — |
| 3 | `DOC-c30c293d38a2cd8b` | yes | 0.5455 | 37.3 | 9794 | 911 | — |
| 4 | `DOC-6712aa595cfe3e2c` | yes | 0.4706 | 74.5 | 7666 | 1680 | — |
| 5 | `DOC-adad5ef793c0e409` | yes | 0.4615 | 76.2 | 8247 | 1701 | — |
| 6 | `DOC-5892b6dc609c8d0f` | yes | — | 79.7 | 7606 | 1790 | — |
| 7 | `DOC-ba6d7a0ea5100bbb` | yes | 0.6316 | 80.3 | 7887 | 1807 | — |
| 8 | `DOC-440a54573c24b918` | yes | 1.0000 | 26.5 | 3493 | 627 | — |
| 9 | `DOC-9e063c6e3baf1233` | yes | 0.5455 | 104.9 | 7486 | 2442 | — |
| 10 | `DOC-ade03c57c5f78e21` | yes | 0.7059 | 49.9 | 4093 | 1278 | — |
| 11 | `DOC-c68a4dd90660c113` | yes | 0.6154 | 49.8 | 7851 | 1302 | — |
| 12 | `DOC-55df050fcb737129` | yes | 0.5000 | 63.4 | 5461 | 1639 | — |
| 13 | `DOC-99ca00712a84f039` | yes | 0.6667 | 78.7 | 5337 | 2002 | — |
| 14 | `DOC-fca31a55b1d526ea` | yes | 0.8333 | 80.1 | 5459 | 2068 | — |
| 15 | `DOC-f9b36fee351217c2` | yes | 0.5000 | 65.8 | 7931 | 1719 | — |
| 16 | `DOC-a2ce7adbf6f5cb8d` | yes | 0.5556 | 39.2 | 6729 | 1080 | — |
| 17 | `DOC-d1c45d175a8abeb5` | yes | 0.5600 | 27.1 | 6851 | 775 | — |
| 18 | `DOC-2ca7b08d2d439f1e` | yes | — | 187.8 | 7616 | 4860 | — |
| 19 | `DOC-dfa5c8eb1e7b837c` | yes | 0.7500 | 71.8 | 6055 | 2158 | — |
| 20 | `DOC-06229aa6571f9d46` | no | — | 228.1 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=6154, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-20-contracts-specialist-awq-1l4.card.json`._
