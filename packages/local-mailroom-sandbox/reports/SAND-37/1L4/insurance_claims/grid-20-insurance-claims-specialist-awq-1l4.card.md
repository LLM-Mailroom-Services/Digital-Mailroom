# Insurance Claims — 1× L4 · C8 · n=20

**Run:** `grid-20-insurance-claims-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | insurance_claims_specialist |
| Prompt | insurance_claims_specialist_simplified |
| Temperature | 0.1 (vendored call site) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 13,500 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 20 docs (fingerprint 6c72fe4bf896) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-20-insurance-claims-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 20 |
| Spec hash | b52b9ad6… |
| **Time** |  |
| Wall (busy) | 37.79 s |
| GPU seconds | 38.08 s |
| Cold boot | 0.28 s |
| **Cost** |  |
| Busy-window GPU $ | $0.008398 |
| Billed GPU $ (incl. boot) | $0.008462 |
| Idle $ | $0.000930 (4.18 s) |
| Cost per document | $0.000420 |
| Cost per ok document | $0.000420 |
| Cost per 1M tokens | $0.1225 |
| **Tokens** |  |
| Prompt tokens | 60,771 |
| Completion tokens | 7,765 (11.3%) |
| Total tokens | 68,536 |
| Tokens per document | 3,427 |
| Per document: instructions + template | 2,695 (78.6%) |
| Per document: document text | 344 (10.0%) |
| Per document: output | 388 (11.3%) |
| Instruction tokens per model call | 2,695 over 20 calls |
| Token split basis | fit across documents, 4.24 chars/token |
| Completion p95 / max (ok docs) | 496 / 968 |
| **Throughput** |  |
| Tokens / second | 1,813.5 |
| Tokens / second per L4 | 1,813.5 |
| Documents / minute | 31.75 |
| **Latency (per document, ok rows)** |  |
| Mean | 13.44 s |
| p50 | 13.18 s |
| p95 | 18.97 s |
| Max | 24.81 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 7.11× of 8 |
| Slot occupancy | 88.9% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 20 |
| Mean TTFT per replica | 1.063 s |
| Prefix-cache hit per replica | 61.5% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.6836 (sd 0.054) |
| Score min / max | 0.5993 / 0.8056 |
| Scoring method | `suite` |
| Schema-valid rate | 0.30 |
| Parse errors | 0 |
| Errors | 0 / 20 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-edc5811634a19b7a` | yes | 0.8056 | 11.9 | 2835 | 292 | — |
| 2 | `DOC-dcb4333f78bfe249` | yes | 0.6363 | 13.2 | 2934 | 345 | — |
| 3 | `DOC-c0e145a5a0a0d4bd` | yes | 0.7930 | 13.2 | 2833 | 347 | — |
| 4 | `DOC-4fd4cf5db3cfdb47` | yes | 0.6839 | 13.4 | 2940 | 354 | — |
| 5 | `DOC-d5e1b8ed3350fb36` | yes | 0.6290 | 14.6 | 2969 | 370 | — |
| 6 | `DOC-4dda6e74e78edd70` | yes | 0.6428 | 14.9 | 2949 | 375 | — |
| 7 | `DOC-a1a2afde18ded42d` | yes | 0.6885 | 16.1 | 3086 | 396 | — |
| 8 | `DOC-576c9233159914e3` | yes | 0.6825 | 19.0 | 3080 | 496 | — |
| 9 | `DOC-b3be1f4b2b6142ed` | yes | 0.6955 | 10.1 | 2815 | 289 | — |
| 10 | `DOC-596b1f881ecf4a8a` | yes | 0.7163 | 9.7 | 2806 | 305 | — |
| 11 | `DOC-c0d9bf1e6be4ad51` | yes | 0.7015 | 10.2 | 2808 | 314 | — |
| 12 | `DOC-85e24caa52979f50` | yes | 0.7114 | 13.0 | 3121 | 368 | — |
| 13 | `DOC-df5ebe3e7263b6c6` | yes | 0.6385 | 9.3 | 2815 | 288 | — |
| 14 | `DOC-a0be2aba09a3f580` | yes | 0.6913 | 14.1 | 3095 | 367 | — |
| 15 | `DOC-17abdc452037b6eb` | yes | 0.7041 | 15.8 | 3129 | 433 | — |
| 16 | `DOC-4348717727f6d6b4` | yes | 0.6456 | 13.2 | 3004 | 408 | — |
| 17 | `DOC-01f1577c446c646d` | yes | 0.5993 | 10.0 | 2868 | 332 | — |
| 18 | `DOC-4e21681f375a247d` | yes | 0.6411 | 10.8 | 2985 | 347 | — |
| 19 | `DOC-ab3b194998a42322` | yes | 0.6131 | 11.7 | 3016 | 371 | — |
| 20 | `DOC-0966e6d5a9e7bd71` | yes | 0.7532 | 24.8 | 4683 | 968 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-20-insurance-claims-specialist-awq-1l4.card.json`._
