# Insurance Claims — 2× L4 · C32 · n=50

**Run:** `sand42-50-insurance-claims-specialist-awq-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 50 docs (fingerprint f4fdcee45e7f) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-50-insurance-claims-specialist-awq-2l4-c32` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 676fd83f… |
| **Time** |  |
| Wall (busy) | 75.89 s |
| GPU seconds | 76.08 s |
| Cold boot | 0.35 s |
| **Cost** |  |
| Busy-window GPU $ | $0.033728 |
| Billed GPU $ | $0.033814 |
| Billed seconds | 76.08 s |
| Idle $ | $0.015968 (35.93 s) |
| Cost per document | $0.000676 |
| Cost per ok document | $0.000676 |
| Cost per 1M tokens | $0.1819 |
| **Tokens** |  |
| Prompt tokens | 165,315 |
| Completion tokens | 20,600 (11.1%) |
| Total tokens | 185,915 |
| Tokens per document | 3,718 |
| Per document: instructions + template | 2,710 (72.9%) |
| Per document: document text | 597 (16.0%) |
| Per document: output | 412 (11.1%) |
| Instruction tokens per model call | 2,710 over 50 calls |
| Token split basis | fit across documents, 4.47 chars/token |
| Completion p95 / max (ok docs) | 568 / 1,418 |
| **Throughput** |  |
| Tokens / second | 2,449.9 |
| Tokens / second per L4 | 1,224.9 |
| Documents / minute | 39.53 |
| **Latency (per document, ok rows)** |  |
| Mean | 25.57 s |
| p50 | 23.96 s |
| p95 | 40.08 s |
| Max | 46.45 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 16.85× of 32 |
| Slot occupancy | 52.7% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 14 / 36 |
| Mean TTFT per replica | 1.277 s / 8.031 s |
| Prefix-cache hit per replica | 53.6% / 59.2% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 21 samples · serving-replica nvidia-smi |
| GPU utilization | 74.8 % mean (p95 99.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 81.8 % — **below the 90% gate (issue #128)** |
| GPU power draw | 62.8 W (min 29.6 / max 73.4) of 72 W cap |
| GPU memory bandwidth | 71.1 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,560 MHz (min 1,020 / max 2,040) |
| GPU temperature | 68.1 C (min 49.0 / max 81.0) |
| GPU memory used | 21,022 MiB (min 21,022 / max 21,022) |
| **Quality** |  |
| Overall extraction score | 0.6662 (sd 0.062) |
| Score min / max | 0.5663 / 0.8098 |
| Scoring method | `suite` |
| Schema-valid rate | 0.30 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Insurance Claims run dashboard](sand42-50-insurance-claims-specialist-awq-2l4-c32.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-158c0b74df673b81` | yes | 0.6353 | 12.0 | 2939 | 343 | — |
| 2 | `DOC-e7c196f508907c6f` | yes | 0.7830 | 12.0 | 2834 | 362 | — |
| 3 | `DOC-997823d9605a4a59` | yes | 0.6442 | 12.4 | 2973 | 382 | — |
| 4 | `DOC-ef79520b2f50217b` | yes | 0.6892 | 12.9 | 3138 | 395 | — |
| 5 | `DOC-87c0c53132830a6c` | yes | 0.6265 | 12.9 | 2993 | 397 | — |
| 6 | `DOC-00ccdcb0154a8629` | yes | 0.6228 | 16.4 | 2812 | 285 | — |
| 7 | `DOC-5060222215c75aa6` | yes | 0.6745 | 16.5 | 2801 | 287 | — |
| 8 | `DOC-728d06b610b25244` | yes | 0.7218 | 16.5 | 2804 | 289 | — |
| 9 | `DOC-c34baab0b5fe378a` | yes | 0.6232 | 18.4 | 2807 | 308 | — |
| 10 | `DOC-2a33a6c34834e769` | yes | 0.6298 | 19.6 | 2953 | 337 | — |
| 11 | `DOC-9ba0a3d4c680b976` | yes | 0.6398 | 20.0 | 2982 | 334 | — |
| 12 | `DOC-629fb5789dfd10ca` | yes | 0.7979 | 20.7 | 2836 | 349 | — |
| 13 | `DOC-9051d4cf8d7ab452` | yes | 0.7100 | 21.1 | 3115 | 352 | — |
| 14 | `DOC-9a6f58879fcb3367` | yes | 0.6442 | 21.9 | 2946 | 357 | — |
| 15 | `DOC-968c9605eab0a87d` | yes | 0.6442 | 22.5 | 2942 | 367 | — |
| 16 | `DOC-0cdb706a0cdbe3b6` | yes | 0.6176 | 22.6 | 2981 | 366 | — |
| 17 | `DOC-2aea7f6dc44b37e1` | yes | 0.7741 | 23.7 | 2835 | 387 | — |
| 18 | `DOC-e4b1466ee8d1ff19` | yes | 0.7037 | 24.2 | 3113 | 400 | — |
| 19 | `DOC-2435c398b95844bc` | yes | 0.6795 | 27.3 | 3080 | 485 | — |
| 20 | `DOC-3ae2dc5d624e2120` | yes | 0.5999 | 14.7 | 2871 | 347 | — |
| 21 | `DOC-4e21681f375a247d` | yes | 0.6426 | 16.3 | 2985 | 400 | — |
| 22 | `DOC-d8df43ed4d8faf89` | yes | 0.6888 | 29.1 | 3107 | 529 | — |
| 23 | `DOC-5b1e8e2aed95c089` | yes | 0.6825 | 30.5 | 3123 | 551 | — |
| 24 | `DOC-00d28a1df0e3f6ba` | yes | 0.6971 | 31.3 | 2812 | 260 | — |
| 25 | `DOC-91da307f80433ae3` | yes | 0.5796 | 15.3 | 2894 | 358 | — |
| 26 | `DOC-90338506fc792f32` | yes | 0.5823 | 16.0 | 2882 | 385 | — |
| 27 | `DOC-f5e6c0de5f1d8593` | yes | 0.7169 | 34.7 | 2812 | 307 | — |
| 28 | `DOC-cbfcdb6f42cf2ae6` | yes | 0.6205 | 36.5 | 2806 | 290 | — |
| 29 | `DOC-991cb72cb83c7a6c` | yes | 0.6442 | 36.7 | 2941 | 372 | — |
| 30 | `DOC-6f6fc9762418a70f` | yes | 0.7048 | 36.6 | 2811 | 294 | — |
| 31 | `DOC-1076ac5b4b0df386` | yes | 0.6569 | 14.4 | 4482 | 428 | — |
| 32 | `DOC-ab18f15b7a51f1ab` | yes | 0.7414 | 17.0 | 5538 | 494 | — |
| 33 | `DOC-2a55a2b5324659f8` | yes | 0.8098 | 39.6 | 2865 | 345 | — |
| 34 | `DOC-29e384939c31d44a` | yes | 0.6131 | 39.6 | 3010 | 323 | — |
| 35 | `DOC-5c4e70db54374e72` | yes | 0.6874 | 39.8 | 3151 | 399 | — |
| 36 | `DOC-e2a58ed4c02470c0` | yes | 0.8036 | 40.1 | 2835 | 346 | — |
| 37 | `DOC-73d64bbeb296bd95` | yes | 0.6023 | 20.6 | 4524 | 568 | — |
| 38 | `DOC-5b97ae3f8558703c` | yes | 0.6864 | 16.8 | 4565 | 566 | — |
| 39 | `DOC-2d7cc160b78a69c5` | yes | 0.6442 | 41.1 | 2979 | 378 | — |
| 40 | `DOC-27b23fd94cc70d9d` | yes | 0.6052 | 29.5 | 2890 | 353 | — |
| 41 | `DOC-364435343e0a2250` | yes | 0.6474 | 30.8 | 3020 | 393 | — |
| 42 | `DOC-93c8d133c296d536` | yes | 0.5663 | 30.4 | 2879 | 320 | — |
| 43 | `DOC-44bcd388c4710b71` | yes | 0.5663 | 28.8 | 2884 | 343 | — |
| 44 | `DOC-7bd9dbc1b39ad41d` | yes | 0.6036 | 46.5 | 3171 | 625 | — |
| 45 | `DOC-164aa748f84cef54` | yes | 0.5899 | 29.4 | 2911 | 410 | — |
| 46 | `DOC-7f1f866b022cee63` | yes | 0.7261 | 31.2 | 4985 | 510 | — |
| 47 | `DOC-85314478b81710d9` | yes | 0.6189 | 29.4 | 5285 | 443 | — |
| 48 | `DOC-384665a051d0fcd6` | yes | 0.6798 | 31.6 | 5208 | 506 | — |
| 49 | `DOC-6dcc0b9ba494c25b` | yes | 0.7569 | 30.9 | 5114 | 557 | — |
| 50 | `DOC-02f77aa77391a8c2` | yes | 0.6864 | 39.6 | 5091 | 1418 | — |

_Generated 2026-10-13T04:33:10+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-insurance-claims-specialist-awq-2l4-c32.card.json`._
