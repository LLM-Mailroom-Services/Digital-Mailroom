# Insurance Claims — 2× L4 · C16 · n=50

**Run:** `sand42-50-insurance-claims-specialist-awq-2l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-insurance-claims-specialist-awq-2l4-c16` |
| GPUs / replicas | 2 |
| Concurrency | 16 (8 per replica) |
| Documents | 50 |
| Spec hash | 1f035de4… |
| **Time** |  |
| Wall (busy) | 89.49 s |
| GPU seconds | 88.58 s |
| Cold boot | 0.31 s |
| **Cost** |  |
| Busy-window GPU $ | $0.039773 |
| Billed GPU $ | $0.039368 |
| Billed seconds | 88.58 s |
| Idle $ | $0.016674 (37.52 s) |
| Cost per document | $0.000787 |
| Cost per ok document | $0.000787 |
| Cost per 1M tokens | $0.2119 |
| **Tokens** |  |
| Prompt tokens | 165,315 |
| Completion tokens | 20,434 (11.0%) |
| Total tokens | 185,749 |
| Tokens per document | 3,715 |
| Per document: instructions + template | 2,710 (72.9%) |
| Per document: document text | 597 (16.1%) |
| Per document: output | 409 (11.0%) |
| Instruction tokens per model call | 2,710 over 50 calls |
| Token split basis | fit across documents, 4.47 chars/token |
| Completion p95 / max (ok docs) | 577 / 1,360 |
| **Throughput** |  |
| Tokens / second | 2,075.6 |
| Tokens / second per L4 | 1,037.8 |
| Documents / minute | 33.52 |
| **Latency (per document, ok rows)** |  |
| Mean | 16.63 s |
| p50 | 16.15 s |
| p95 | 23.57 s |
| Max | 39.50 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 9.29× of 16 |
| Slot occupancy | 58.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 18 / 32 |
| Mean TTFT per replica | 0.487 s / 2.112 s |
| Prefix-cache hit per replica | 55.8% / 58.0% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 26 samples · serving-replica nvidia-smi |
| GPU utilization | 67.4 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 61.1 W (min 30.0 / max 73.2) of 72 W cap |
| GPU memory bandwidth | 61.8 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,579 MHz (min 975 / max 2,040) |
| GPU temperature | 71.0 C (min 56.0 / max 79.0) |
| GPU memory used | 20,996 MiB (min 20,996 / max 20,997) |
| **Quality** |  |
| Overall extraction score | 0.6697 (sd 0.065) |
| Score min / max | 0.5663 / 0.8133 |
| Scoring method | `suite` |
| Schema-valid rate | 0.30 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Insurance Claims run dashboard](sand42-50-insurance-claims-specialist-awq-2l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-ef79520b2f50217b` | yes | 0.6892 | 11.2 | 3138 | 390 | — |
| 2 | `DOC-2a33a6c34834e769` | yes | 0.6338 | 17.5 | 2953 | 329 | — |
| 3 | `DOC-997823d9605a4a59` | yes | 0.6398 | 17.7 | 2973 | 336 | — |
| 4 | `DOC-9ba0a3d4c680b976` | yes | 0.6398 | 17.8 | 2982 | 334 | — |
| 5 | `DOC-2a55a2b5324659f8` | yes | 0.8098 | 18.0 | 2865 | 345 | — |
| 6 | `DOC-2aea7f6dc44b37e1` | yes | 0.7741 | 19.0 | 2835 | 353 | — |
| 7 | `DOC-629fb5789dfd10ca` | yes | 0.7979 | 19.0 | 2836 | 349 | — |
| 8 | `DOC-9a6f58879fcb3367` | yes | 0.6487 | 19.2 | 2946 | 360 | — |
| 9 | `DOC-e7c196f508907c6f` | yes | 0.7830 | 19.3 | 2834 | 367 | — |
| 10 | `DOC-158c0b74df673b81` | yes | 0.6442 | 19.7 | 2939 | 362 | — |
| 11 | `DOC-e2a58ed4c02470c0` | yes | 0.7946 | 20.0 | 2835 | 368 | — |
| 12 | `DOC-968c9605eab0a87d` | yes | 0.6442 | 20.1 | 2942 | 367 | — |
| 13 | `DOC-991cb72cb83c7a6c` | yes | 0.6442 | 20.2 | 2941 | 374 | — |
| 14 | `DOC-5c4e70db54374e72` | yes | 0.6874 | 21.6 | 3151 | 399 | — |
| 15 | `DOC-2435c398b95844bc` | yes | 0.6879 | 22.8 | 3080 | 444 | — |
| 16 | `DOC-9051d4cf8d7ab452` | yes | 0.7100 | 13.4 | 3115 | 352 | — |
| 17 | `DOC-5b1e8e2aed95c089` | yes | 0.6825 | 26.0 | 3123 | 549 | — |
| 18 | `DOC-5060222215c75aa6` | yes | 0.6745 | 9.0 | 2801 | 245 | — |
| 19 | `DOC-00d28a1df0e3f6ba` | yes | 0.6971 | 10.2 | 2812 | 259 | — |
| 20 | `DOC-728d06b610b25244` | yes | 0.7043 | 9.2 | 2804 | 273 | — |
| 21 | `DOC-6f6fc9762418a70f` | yes | 0.7048 | 9.3 | 2811 | 289 | — |
| 22 | `DOC-f5e6c0de5f1d8593` | yes | 0.6450 | 10.2 | 2812 | 309 | — |
| 23 | `DOC-00ccdcb0154a8629` | yes | 0.6228 | 11.3 | 2812 | 281 | — |
| 24 | `DOC-c34baab0b5fe378a` | yes | 0.6899 | 11.0 | 2807 | 280 | — |
| 25 | `DOC-cbfcdb6f42cf2ae6` | yes | 0.6872 | 10.8 | 2806 | 285 | — |
| 26 | `DOC-e4b1466ee8d1ff19` | yes | 0.7037 | 15.0 | 3113 | 392 | — |
| 27 | `DOC-2d7cc160b78a69c5` | yes | 0.6442 | 12.4 | 2979 | 378 | — |
| 28 | `DOC-29e384939c31d44a` | yes | 0.6220 | 14.5 | 3010 | 382 | — |
| 29 | `DOC-87c0c53132830a6c` | yes | 0.6265 | 14.4 | 2993 | 401 | — |
| 30 | `DOC-d8df43ed4d8faf89` | yes | 0.6888 | 19.8 | 3107 | 529 | — |
| 31 | `DOC-0cdb706a0cdbe3b6` | yes | 0.6265 | 14.6 | 2981 | 366 | — |
| 32 | `DOC-3ae2dc5d624e2120` | yes | 0.5999 | 13.8 | 2871 | 341 | — |
| 33 | `DOC-27b23fd94cc70d9d` | yes | 0.6052 | 14.4 | 2890 | 353 | — |
| 34 | `DOC-4e21681f375a247d` | yes | 0.6426 | 16.4 | 2985 | 400 | — |
| 35 | `DOC-93c8d133c296d536` | yes | 0.5663 | 13.3 | 2879 | 325 | — |
| 36 | `DOC-364435343e0a2250` | yes | 0.6474 | 15.9 | 3020 | 393 | — |
| 37 | `DOC-7bd9dbc1b39ad41d` | yes | 0.6081 | 23.6 | 3171 | 601 | — |
| 38 | `DOC-91da307f80433ae3` | yes | 0.5796 | 15.8 | 2894 | 358 | — |
| 39 | `DOC-44bcd388c4710b71` | yes | 0.5663 | 15.2 | 2884 | 343 | — |
| 40 | `DOC-90338506fc792f32` | yes | 0.5903 | 15.2 | 2882 | 371 | — |
| 41 | `DOC-164aa748f84cef54` | yes | 0.5899 | 16.7 | 2911 | 403 | — |
| 42 | `DOC-7f1f866b022cee63` | yes | 0.7873 | 18.6 | 4985 | 508 | — |
| 43 | `DOC-85314478b81710d9` | yes | 0.6287 | 14.2 | 5285 | 426 | — |
| 44 | `DOC-73d64bbeb296bd95` | yes | 0.6198 | 20.9 | 4524 | 544 | — |
| 45 | `DOC-384665a051d0fcd6` | yes | 0.6802 | 17.1 | 5208 | 498 | — |
| 46 | `DOC-ab18f15b7a51f1ab` | yes | 0.7446 | 17.8 | 5538 | 523 | — |
| 47 | `DOC-1076ac5b4b0df386` | yes | 0.5722 | 15.8 | 4482 | 502 | — |
| 48 | `DOC-6dcc0b9ba494c25b` | yes | 0.8133 | 15.9 | 5114 | 561 | — |
| 49 | `DOC-5b97ae3f8558703c` | yes | 0.6912 | 17.2 | 4565 | 577 | — |
| 50 | `DOC-02f77aa77391a8c2` | yes | 0.7059 | 39.5 | 5091 | 1360 | — |

_Generated 2026-10-13T04:33:03+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-insurance-claims-specialist-awq-2l4-c16.card.json`._
