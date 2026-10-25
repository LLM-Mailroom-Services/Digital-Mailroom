# Contracts — 2× L4 · C32 · n=50

**Run:** `sand42-50-contracts-specialist-awq-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-contracts-specialist-awq-2l4-c32` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | f11ad4ea… |
| **Time** |  |
| Wall (busy) | 1,026.39 s |
| GPU seconds | 784.24 s |
| Cold boot | 0.41 s |
| **Cost** |  |
| Busy-window GPU $ | $0.456174 |
| Billed GPU $ | $0.348551 |
| Billed seconds | 784.24 s |
| Idle $ | $0.291339 (655.51 s) |
| Cost per document | $0.006971 |
| Cost per ok document | $0.006971 |
| Cost per 1M tokens | $0.3763 |
| **Tokens** |  |
| Prompt tokens | 792,747 |
| Completion tokens | 133,634 (14.4%) |
| Total tokens | 926,381 |
| Tokens per document | 18,528 |
| Per document: instructions + template | 3,200 (17.3%) |
| Per document: document text | 12,655 (68.3%) |
| Per document: output | 2,673 (14.4%) |
| Instruction tokens per model call | 1,798 over 89 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 6,594 / 17,083 |
| **Throughput** |  |
| Tokens / second | 902.6 |
| Tokens / second per L4 | 451.3 |
| Documents / minute | 2.92 |
| **Latency (per document, ok rows)** |  |
| Mean | 237.36 s |
| p50 | 171.43 s |
| p95 | 592.64 s |
| Max | 768.14 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 11.56× of 32 |
| Slot occupancy | 36.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 43 / 46 |
| Mean TTFT per replica | 4.470 s / 10.897 s |
| Prefix-cache hit per replica | 34.2% / 39.5% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 2 / 3 |
| **GPU hardware (nvidia-smi)** | 235 samples · serving-replica nvidia-smi |
| GPU utilization | 86.8 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 96.9 % |
| GPU power draw | 67.5 W (min 32.9 / max 73.4) of 72 W cap |
| GPU memory bandwidth | 80.6 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,427 MHz (min 990 / max 2,040) |
| GPU temperature | 75.3 C (min 65.0 / max 85.0) |
| GPU memory used | 21,026 MiB (min 21,022 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.6221 (sd 0.133) |
| Score min / max | 0.3077 / 0.8696 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 50 |
| Micro precision / recall / F1 | 0.657 / 0.617 / 0.636 |
| Metadata value checks | 85 / 141 |
| Suite field score (mean) | not captured |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Contracts run dashboard](sand42-50-contracts-specialist-awq-2l4-c32.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-f8b0d4bcbac60ca2` | yes | 0.7500 | 64.7 | 3824 | 574 | — |
| 2 | `DOC-2c3a9c3168cd0e3a` | yes | 0.6000 | 83.4 | 3385 | 877 | — |
| 3 | `DOC-27b649fe2f6fae8e` | yes | 0.7500 | 90.0 | 5464 | 979 | — |
| 4 | `DOC-f5a54932794ef16e` | yes | 0.6667 | 95.8 | 5302 | 1069 | — |
| 5 | `DOC-eaa14fe106140524` | yes | 0.6250 | 103.2 | 7001 | 1079 | — |
| 6 | `DOC-268df6c8fabb385a` | yes | 0.6667 | 108.9 | 5201 | 1186 | — |
| 7 | `DOC-1843cfdaf5db1840` | yes | 0.6000 | 117.2 | 7407 | 1323 | — |
| 8 | `DOC-9a36838df2878b37` | yes | 0.5217 | 124.9 | 8142 | 1374 | — |
| 9 | `DOC-e4272758b561f8cd` | yes | 0.7500 | 134.8 | 6987 | 1494 | — |
| 10 | `DOC-593f2c6de770b84c` | yes | 0.7273 | 138.6 | 9228 | 1570 | — |
| 11 | `DOC-70f90b46b2c4f1a6` | yes | 0.7500 | 60.7 | 3154 | 507 | — |
| 12 | `DOC-3c07c9ccd9a01d6e` | yes | 0.7059 | 151.8 | 7428 | 1663 | — |
| 13 | `DOC-b83763aeff114369` | yes | 0.6897 | 157.0 | 7446 | 1846 | — |
| 14 | `DOC-385a86c69f8e562c` | yes | 0.6667 | 160.8 | 6560 | 1759 | — |
| 15 | `DOC-1ddc9333769d27e4` | yes | 0.5714 | 76.0 | 4450 | 932 | — |
| 16 | `DOC-a7ea445212692b88` | yes | 0.6667 | 171.4 | 9369 | 2031 | — |
| 17 | `DOC-035731e655e67aab` | yes | 0.5000 | 171.5 | 5207 | 2055 | — |
| 18 | `DOC-81c4ce12d907380c` | yes | 0.5714 | 188.9 | 7047 | 2134 | — |
| 19 | `DOC-cbc1f0d62edbb23e` | yes | 0.5000 | 200.6 | 4155 | 2258 | — |
| 20 | `DOC-c9d4c4f8ff433527` | yes | 0.5882 | 69.2 | 7730 | 970 | — |
| 21 | `DOC-e998c563b82122b9` | yes | 0.5263 | 207.7 | 10006 | 1731 | — |
| 22 | `DOC-dfb4e69a3ab10dc9` | yes | 0.4138 | 118.9 | 7378 | 1541 | — |
| 23 | `DOC-e235bc9735f96335` | yes | 0.5714 | 232.3 | 10699 | 2887 | — |
| 24 | `DOC-d6b6b418dd211b76` | yes | 0.5455 | 126.0 | 7293 | 1826 | — |
| 25 | `DOC-e0d31c39359cb803` | yes | 0.6316 | 111.2 | 6879 | 1684 | — |
| 26 | `DOC-1e22a2d4068b8650` | yes | 0.7143 | 255.7 | 7587 | 3320 | — |
| 27 | `DOC-62b300182901e850` | yes | 0.6250 | 192.2 | 33346 | 2152 | — |
| 28 | `DOC-8993ad1085e08bd0` | yes | 0.8421 | 258.2 | 22402 | 3204 | — |
| 29 | `DOC-fe06800cc62e5e19` | yes | 0.6897 | 153.2 | 8619 | 1595 | — |
| 30 | `DOC-472f423cdf0819ef` | yes | 0.7500 | 167.2 | 4656 | 1850 | — |
| 31 | `DOC-812192e392d8d410` | yes | 0.6000 | 289.9 | 5551 | 3333 | — |
| 32 | `DOC-dbe52fd78e44b0ef` | yes | 0.8696 | 129.3 | 18750 | 2320 | — |
| 33 | `DOC-4b57f485708ab60b` | yes | 0.5333 | 153.6 | 6639 | 1543 | — |
| 34 | `DOC-9cee2e10b449a71c` | yes | 0.7879 | 325.6 | 21752 | 3518 | — |
| 35 | `DOC-01849fa3020a5ac1` | yes | 0.5000 | 142.8 | 4173 | 1563 | — |
| 36 | `DOC-0752e0811f5f5eb7` | yes | 0.4444 | 332.4 | 41619 | 4048 | — |
| 37 | `DOC-e218d39bb2f3c5ef` | yes | 0.3333 | 188.1 | 19923 | 2839 | — |
| 38 | `DOC-3f4003eb02433292` | yes | 0.3077 | 197.4 | 4421 | 2365 | — |
| 39 | `DOC-1266801f2faad19f` | yes | 0.6818 | 362.3 | 33383 | 4725 | — |
| 40 | `DOC-712c3f92a0a56b77` | yes | 0.4737 | 376.6 | 56227 | 4260 | — |
| 41 | `DOC-73055dbb1e9f5f2f` | yes | 0.4138 | 385.6 | 49409 | 4564 | — |
| 42 | `DOC-4fb6419e37bff201` | yes | 0.7586 | 430.4 | 22234 | 6594 | — |
| 43 | `DOC-6b67382dcf833c5b` | yes | 0.8000 | 260.0 | 24554 | 3711 | — |
| 44 | `DOC-aca7df716d7eef00` | yes | 0.8214 | 353.1 | 36448 | 5855 | — |
| 45 | `DOC-2b510409d3b9a4a6` | yes | 0.3333 | 550.7 | 9632 | 1525 | — |
| 46 | `DOC-a6f559e4010fc8d1` | yes | 0.6429 | 592.6 | 31544 | 2859 | — |
| 47 | `DOC-8f737e9fec8f24f0` | yes | 0.5714 | 520.9 | 23191 | 1822 | — |
| 48 | `DOC-dfd20f94bb76b6e4` | yes | 0.5926 | 481.5 | 11041 | 1892 | — |
| 49 | `DOC-e29140d2e8e989be` | yes | 0.6667 | 735.1 | 33913 | 7745 | — |
| 50 | `DOC-53e364f030a30b5c` | yes | 0.7941 | 768.1 | 94991 | 17083 | — |

_Generated 2026-10-13T04:33:07+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-contracts-specialist-awq-2l4-c32.card.json`._
