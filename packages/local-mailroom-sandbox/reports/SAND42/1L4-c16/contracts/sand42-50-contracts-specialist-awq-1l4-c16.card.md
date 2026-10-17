# Contracts — 1× L4 · C16 · n=50

**Run:** `sand42-50-contracts-specialist-awq-1l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | contracts_specialist |
| Prompt | contracts_specialist_v33_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 49,000 |
| Chunk window (chars) | 43000 |
| Chunk overlap (chars) | 6000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint 5344b28a3033) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-50-contracts-specialist-awq-1l4-c16` |
| GPUs / replicas | 1 |
| Concurrency | 16 (16 per replica) |
| Documents | 50 |
| Spec hash | 630a7ebd… |
| **Time** |  |
| Wall (busy) | 1,124.43 s |
| GPU seconds | 1,012.66 s |
| Cold boot | 0.37 s |
| **Cost** |  |
| Busy-window GPU $ | $0.249873 |
| Billed GPU $ | $0.225035 |
| Billed seconds | 1,012.66 s |
| Idle $ | $0.073626 (331.32 s) |
| Cost per document | $0.004501 |
| Cost per ok document | $0.004501 |
| Cost per 1M tokens | $0.2333 |
| **Tokens** |  |
| Prompt tokens | 831,734 |
| Completion tokens | 132,891 (13.8%) |
| Total tokens | 964,625 |
| Tokens per document | 19,292 |
| Per document: instructions + template | 3,980 (20.6%) |
| Per document: document text | 12,655 (65.6%) |
| Per document: output | 2,658 (13.8%) |
| Instruction tokens per model call | 2,236 over 89 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 8,257 / 10,739 |
| **Throughput** |  |
| Tokens / second | 857.9 |
| Tokens / second per L4 | 857.9 |
| Documents / minute | 2.67 |
| **Latency (per document, ok rows)** |  |
| Mean | 253.79 s |
| p50 | 167.86 s |
| p95 | 791.91 s |
| Max | 906.10 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 11.29× of 16 |
| Slot occupancy | 70.5% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 89 |
| Mean TTFT per replica | 3.705 s |
| Prefix-cache hit per replica | 37.7% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 2 |
| **GPU hardware (nvidia-smi)** | 166 samples · serving-replica nvidia-smi |
| GPU utilization | 97.8 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 71.6 W (min 35.0 / max 75.3) of 72 W cap |
| GPU memory bandwidth | 86.4 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,294 MHz (min 1,035 / max 2,040) |
| GPU temperature | 76.6 C (min 73.0 / max 81.0) |
| GPU memory used | 21,026 MiB (min 21,026 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.6037 (sd 0.134) |
| Score min / max | 0.2727 / 0.8571 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 50 |
| Micro precision / recall / F1 | 0.625 / 0.603 / 0.614 |
| Metadata value checks | 83 / 142 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Contracts run dashboard](sand42-50-contracts-specialist-awq-1l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-268df6c8fabb385a` | yes | 0.6667 | 106.9 | 5201 | 965 | — |
| 2 | `DOC-f5a54932794ef16e` | yes | 0.6667 | 122.4 | 5302 | 1154 | — |
| 3 | `DOC-eaa14fe106140524` | yes | 0.6667 | 133.9 | 7001 | 1293 | — |
| 4 | `DOC-385a86c69f8e562c` | yes | 0.7273 | 140.8 | 6560 | 1406 | — |
| 5 | `DOC-593f2c6de770b84c` | yes | 0.7368 | 150.6 | 9228 | 1544 | — |
| 6 | `DOC-a7ea445212692b88` | yes | 0.6897 | 161.7 | 9369 | 1665 | — |
| 7 | `DOC-3c07c9ccd9a01d6e` | yes | 0.8182 | 169.8 | 7428 | 1733 | — |
| 8 | `DOC-1843cfdaf5db1840` | yes | 0.2727 | 49.5 | 7407 | 632 | — |
| 9 | `DOC-cbc1f0d62edbb23e` | yes | 0.5455 | 89.8 | 4155 | 1065 | — |
| 10 | `DOC-2c3a9c3168cd0e3a` | yes | 0.6667 | 72.7 | 3385 | 858 | — |
| 11 | `DOC-e235bc9735f96335` | yes | 0.6429 | 207.7 | 10699 | 2170 | — |
| 12 | `DOC-81c4ce12d907380c` | yes | 0.5714 | 90.9 | 7047 | 972 | — |
| 13 | `DOC-e4272758b561f8cd` | yes | 0.5556 | 247.6 | 6987 | 2571 | — |
| 14 | `DOC-f8b0d4bcbac60ca2` | yes | 0.4286 | 116.6 | 3824 | 1269 | — |
| 15 | `DOC-0752e0811f5f5eb7` | yes | 0.4000 | 297.8 | 41619 | 3141 | — |
| 16 | `DOC-b83763aeff114369` | yes | 0.6667 | 139.6 | 7446 | 1541 | — |
| 17 | `DOC-4fb6419e37bff201` | yes | 0.7857 | 387.1 | 22234 | 4079 | — |
| 18 | `DOC-e998c563b82122b9` | yes | 0.5263 | 145.6 | 10006 | 1519 | — |
| 19 | `DOC-035731e655e67aab` | yes | 0.6000 | 166.0 | 5207 | 1814 | — |
| 20 | `DOC-9cee2e10b449a71c` | yes | 0.7500 | 266.2 | 21752 | 2865 | — |
| 21 | `DOC-70f90b46b2c4f1a6` | yes | 0.8571 | 35.0 | 3154 | 443 | — |
| 22 | `DOC-812192e392d8d410` | yes | 0.6000 | 268.6 | 5551 | 2885 | — |
| 23 | `DOC-1e22a2d4068b8650` | yes | 0.7143 | 207.1 | 7587 | 2192 | — |
| 24 | `DOC-27b649fe2f6fae8e` | yes | 0.7368 | 169.7 | 5464 | 1701 | — |
| 25 | `DOC-1ddc9333769d27e4` | yes | 0.5333 | 109.9 | 4450 | 1160 | — |
| 26 | `DOC-9a36838df2878b37` | yes | 0.3810 | 330.6 | 8142 | 3560 | — |
| 27 | `DOC-fe06800cc62e5e19` | yes | 0.6316 | 92.0 | 8619 | 957 | — |
| 28 | `DOC-d6b6b418dd211b76` | yes | 0.5000 | 78.7 | 7293 | 921 | — |
| 29 | `DOC-73055dbb1e9f5f2f` | yes | 0.5854 | 548.1 | 49409 | 5809 | — |
| 30 | `DOC-62b300182901e850` | yes | 0.6667 | 163.6 | 33346 | 1754 | — |
| 31 | `DOC-1266801f2faad19f` | yes | 0.6842 | 351.6 | 33383 | 3754 | — |
| 32 | `DOC-472f423cdf0819ef` | yes | 0.5714 | 117.3 | 4656 | 1362 | — |
| 33 | `DOC-e0d31c39359cb803` | yes | 0.5000 | 110.1 | 6879 | 1239 | — |
| 34 | `DOC-c9d4c4f8ff433527` | yes | 0.4444 | 124.7 | 7730 | 1372 | — |
| 35 | `DOC-3f4003eb02433292` | yes | 0.3478 | 111.3 | 4421 | 1212 | — |
| 36 | `DOC-4b57f485708ab60b` | yes | 0.6000 | 116.8 | 6639 | 1257 | — |
| 37 | `DOC-dfb4e69a3ab10dc9` | yes | 0.5000 | 268.7 | 7378 | 2933 | — |
| 38 | `DOC-8993ad1085e08bd0` | yes | 0.7234 | 401.5 | 22402 | 4364 | — |
| 39 | `DOC-dfd20f94bb76b6e4` | yes | 0.6364 | 183.5 | 21000 | 2163 | — |
| 40 | `DOC-01849fa3020a5ac1` | yes | 0.4444 | 92.9 | 4173 | 1149 | — |
| 41 | `DOC-e218d39bb2f3c5ef` | yes | 0.4211 | 198.0 | 19923 | 2309 | — |
| 42 | `DOC-53e364f030a30b5c` | yes | 0.7586 | 751.8 | 94991 | 8149 | — |
| 43 | `DOC-e29140d2e8e989be` | yes | 0.6800 | 791.9 | 45485 | 8921 | — |
| 44 | `DOC-aca7df716d7eef00` | yes | 0.6977 | 318.5 | 36448 | 4318 | — |
| 45 | `DOC-8f737e9fec8f24f0` | yes | 0.5455 | 409.4 | 35815 | 5275 | — |
| 46 | `DOC-712c3f92a0a56b77` | yes | 0.3846 | 651.4 | 56227 | 8257 | — |
| 47 | `DOC-6b67382dcf833c5b` | yes | 0.4783 | 228.6 | 24554 | 3772 | — |
| 48 | `DOC-2b510409d3b9a4a6` | yes | 0.7317 | 872.4 | 21668 | 10739 | — |
| 49 | `DOC-a6f559e4010fc8d1` | yes | 0.5882 | 906.1 | 31544 | 3691 | — |
| 50 | `DOC-dbe52fd78e44b0ef` | yes | 0.8571 | 416.7 | 11546 | 1017 | — |

_Generated 2026-10-13T04:32:48+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-contracts-specialist-awq-1l4-c16.card.json`._
