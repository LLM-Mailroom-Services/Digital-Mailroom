# Insurance Claims — 1× L4 · C8 · n=50

**Run:** `sand42-50-insurance-claims-specialist-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-insurance-claims-specialist-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 8f77e131… |
| **Time** |  |
| Wall (busy) | 147.74 s |
| GPU seconds | 120.65 s |
| Cold boot | 0.14 s |
| **Cost** |  |
| Busy-window GPU $ | $0.032830 |
| Billed GPU $ | $0.026812 |
| Billed seconds | 120.65 s |
| Idle $ | $0.012098 (54.44 s) |
| Cost per document | $0.000536 |
| Cost per ok document | $0.000536 |
| Cost per 1M tokens | $0.1442 |
| **Tokens** |  |
| Prompt tokens | 165,315 |
| Completion tokens | 20,586 (11.1%) |
| Total tokens | 185,901 |
| Tokens per document | 3,718 |
| Per document: instructions + template | 2,710 (72.9%) |
| Per document: document text | 597 (16.0%) |
| Per document: output | 412 (11.1%) |
| Instruction tokens per model call | 2,710 over 50 calls |
| Token split basis | fit across documents, 4.47 chars/token |
| Completion p95 / max (ok docs) | 568 / 1,371 |
| **Throughput** |  |
| Tokens / second | 1,258.3 |
| Tokens / second per L4 | 1,258.3 |
| Documents / minute | 20.31 |
| **Latency (per document, ok rows)** |  |
| Mean | 14.93 s |
| p50 | 13.40 s |
| p95 | 22.28 s |
| Max | 43.52 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.05× of 8 |
| Slot occupancy | 63.2% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 0.767 s |
| Prefix-cache hit per replica | 58.4% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 18 samples · serving-replica nvidia-smi |
| GPU utilization | 93.2 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 99.2 % |
| GPU power draw | 70.2 W (min 37.7 / max 73.8) of 72 W cap |
| GPU memory bandwidth | 82.6 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,474 MHz (min 1,155 / max 2,040) |
| GPU temperature | 63.8 C (min 55.0 / max 68.0) |
| GPU memory used | 21,028 MiB (min 21,028 / max 21,028) |
| **Quality** |  |
| Overall extraction score | 0.6709 (sd 0.062) |
| Score min / max | 0.5663 / 0.8133 |
| Scoring method | `suite` |
| Schema-valid rate | 0.32 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Insurance Claims run dashboard](sand42-50-insurance-claims-specialist-awq-1l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-2a33a6c34834e769` | yes | 0.6298 | 12.8 | 2953 | 337 | — |
| 2 | `DOC-2a55a2b5324659f8` | yes | 0.8098 | 12.8 | 2865 | 346 | — |
| 3 | `DOC-629fb5789dfd10ca` | yes | 0.7944 | 12.8 | 2836 | 345 | — |
| 4 | `DOC-158c0b74df673b81` | yes | 0.6442 | 12.8 | 2939 | 350 | — |
| 5 | `DOC-e7c196f508907c6f` | yes | 0.7830 | 14.0 | 2834 | 363 | — |
| 6 | `DOC-e2a58ed4c02470c0` | yes | 0.7857 | 14.4 | 2835 | 366 | — |
| 7 | `DOC-991cb72cb83c7a6c` | yes | 0.6442 | 15.4 | 2941 | 374 | — |
| 8 | `DOC-2aea7f6dc44b37e1` | yes | 0.7741 | 16.1 | 2835 | 387 | — |
| 9 | `DOC-9ba0a3d4c680b976` | yes | 0.6398 | 12.0 | 2982 | 334 | — |
| 10 | `DOC-997823d9605a4a59` | yes | 0.6398 | 12.9 | 2973 | 355 | — |
| 11 | `DOC-968c9605eab0a87d` | yes | 0.6442 | 13.1 | 2942 | 367 | — |
| 12 | `DOC-9a6f58879fcb3367` | yes | 0.6442 | 14.0 | 2946 | 374 | — |
| 13 | `DOC-ef79520b2f50217b` | yes | 0.6892 | 12.1 | 3138 | 382 | — |
| 14 | `DOC-2435c398b95844bc` | yes | 0.6879 | 15.1 | 3080 | 469 | — |
| 15 | `DOC-5b1e8e2aed95c089` | yes | 0.6876 | 18.0 | 3123 | 534 | — |
| 16 | `DOC-5c4e70db54374e72` | yes | 0.6763 | 17.7 | 3151 | 535 | — |
| 17 | `DOC-00d28a1df0e3f6ba` | yes | 0.6971 | 8.5 | 2812 | 259 | — |
| 18 | `DOC-9051d4cf8d7ab452` | yes | 0.7100 | 12.3 | 3115 | 352 | — |
| 19 | `DOC-5060222215c75aa6` | yes | 0.6745 | 9.7 | 2801 | 297 | — |
| 20 | `DOC-e4b1466ee8d1ff19` | yes | 0.7037 | 13.8 | 3113 | 401 | — |
| 21 | `DOC-728d06b610b25244` | yes | 0.7043 | 9.0 | 2804 | 273 | — |
| 22 | `DOC-00ccdcb0154a8629` | yes | 0.6228 | 9.6 | 2812 | 281 | — |
| 23 | `DOC-f5e6c0de5f1d8593` | yes | 0.7169 | 10.7 | 2812 | 307 | — |
| 24 | `DOC-d8df43ed4d8faf89` | yes | 0.6888 | 18.4 | 3107 | 529 | — |
| 25 | `DOC-c34baab0b5fe378a` | yes | 0.6899 | 10.6 | 2807 | 299 | — |
| 26 | `DOC-cbfcdb6f42cf2ae6` | yes | 0.6872 | 10.0 | 2806 | 275 | — |
| 27 | `DOC-6f6fc9762418a70f` | yes | 0.7048 | 10.4 | 2811 | 289 | — |
| 28 | `DOC-29e384939c31d44a` | yes | 0.6131 | 10.9 | 3010 | 306 | — |
| 29 | `DOC-2d7cc160b78a69c5` | yes | 0.6442 | 13.6 | 2979 | 396 | — |
| 30 | `DOC-0cdb706a0cdbe3b6` | yes | 0.6131 | 10.3 | 2981 | 312 | — |
| 31 | `DOC-87c0c53132830a6c` | yes | 0.6265 | 13.2 | 2993 | 397 | — |
| 32 | `DOC-4e21681f375a247d` | yes | 0.6426 | 13.0 | 2985 | 400 | — |
| 33 | `DOC-27b23fd94cc70d9d` | yes | 0.6052 | 11.4 | 2890 | 353 | — |
| 34 | `DOC-364435343e0a2250` | yes | 0.6474 | 12.7 | 3020 | 393 | — |
| 35 | `DOC-3ae2dc5d624e2120` | yes | 0.5999 | 11.6 | 2871 | 333 | — |
| 36 | `DOC-7bd9dbc1b39ad41d` | yes | 0.6031 | 22.3 | 3171 | 625 | — |
| 37 | `DOC-93c8d133c296d536` | yes | 0.5663 | 13.1 | 2879 | 325 | — |
| 38 | `DOC-91da307f80433ae3` | yes | 0.5796 | 14.8 | 2894 | 358 | — |
| 39 | `DOC-44bcd388c4710b71` | yes | 0.5837 | 16.2 | 2884 | 374 | — |
| 40 | `DOC-90338506fc792f32` | yes | 0.5823 | 17.1 | 2882 | 372 | — |
| 41 | `DOC-164aa748f84cef54` | yes | 0.5899 | 18.6 | 2911 | 403 | — |
| 42 | `DOC-73d64bbeb296bd95` | yes | 0.6198 | 24.2 | 4524 | 544 | — |
| 43 | `DOC-7f1f866b022cee63` | yes | 0.7261 | 22.1 | 4985 | 510 | — |
| 44 | `DOC-384665a051d0fcd6` | yes | 0.6798 | 21.1 | 5208 | 501 | — |
| 45 | `DOC-85314478b81710d9` | yes | 0.6332 | 17.2 | 5285 | 441 | — |
| 46 | `DOC-ab18f15b7a51f1ab` | yes | 0.7459 | 21.0 | 5538 | 533 | — |
| 47 | `DOC-1076ac5b4b0df386` | yes | 0.6569 | 15.6 | 4482 | 429 | — |
| 48 | `DOC-6dcc0b9ba494c25b` | yes | 0.8133 | 17.8 | 5114 | 562 | — |
| 49 | `DOC-5b97ae3f8558703c` | yes | 0.6912 | 16.0 | 4565 | 568 | — |
| 50 | `DOC-02f77aa77391a8c2` | yes | 0.7059 | 43.5 | 5091 | 1371 | — |

_Generated 2026-10-13T04:32:44+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-insurance-claims-specialist-awq-1l4-c8.card.json`._
