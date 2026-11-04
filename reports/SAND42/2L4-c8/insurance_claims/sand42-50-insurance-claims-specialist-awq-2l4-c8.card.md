# Insurance Claims — 2× L4 · C8 · n=50

**Run:** `sand42-50-insurance-claims-specialist-awq-2l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-insurance-claims-specialist-awq-2l4-c8` |
| GPUs / replicas | 2 |
| Concurrency | 8 (4 per replica) |
| Documents | 50 |
| Spec hash | 9c87cb29… |
| **Time** |  |
| Wall (busy) | 119.72 s |
| GPU seconds | 109.41 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.053211 |
| Billed GPU $ | $0.048624 |
| Billed seconds | 109.41 s |
| Idle $ | $0.017816 (40.09 s) |
| Cost per document | $0.000972 |
| Cost per ok document | $0.000972 |
| Cost per 1M tokens | $0.2612 |
| **Tokens** |  |
| Prompt tokens | 165,315 |
| Completion tokens | 20,857 (11.2%) |
| Total tokens | 186,172 |
| Tokens per document | 3,723 |
| Per document: instructions + template | 2,710 (72.8%) |
| Per document: document text | 597 (16.0%) |
| Per document: output | 417 (11.2%) |
| Instruction tokens per model call | 2,710 over 50 calls |
| Token split basis | fit across documents, 4.47 chars/token |
| Completion p95 / max (ok docs) | 626 / 1,406 |
| **Throughput** |  |
| Tokens / second | 1,555.0 |
| Tokens / second per L4 | 777.5 |
| Documents / minute | 25.06 |
| **Latency (per document, ok rows)** |  |
| Mean | 12.74 s |
| p50 | 11.59 s |
| p95 | 18.71 s |
| Max | 38.33 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.32× of 8 |
| Slot occupancy | 66.5% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 27 / 23 |
| Mean TTFT per replica | 0.703 s / 0.538 s |
| Prefix-cache hit per replica | 58.8% / 55.3% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 32 samples · serving-replica nvidia-smi |
| GPU utilization | 85.6 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 94.7 % |
| GPU power draw | 67.0 W (min 30.9 / max 73.2) of 72 W cap |
| GPU memory bandwidth | 83.0 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,558 MHz (min 1,080 / max 2,040) |
| GPU temperature | 69.6 C (min 55.0 / max 82.0) |
| GPU memory used | 21,023 MiB (min 21,022 / max 21,024) |
| **Quality** |  |
| Overall extraction score | 0.6654 (sd 0.064) |
| Score min / max | 0.5663 / 0.8133 |
| Scoring method | `suite` |
| Schema-valid rate | 0.28 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Insurance Claims run dashboard](sand42-50-insurance-claims-specialist-awq-2l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-2aea7f6dc44b37e1` | yes | 0.7741 | 10.6 | 2835 | 353 | — |
| 2 | `DOC-991cb72cb83c7a6c` | yes | 0.6442 | 10.6 | 2941 | 374 | — |
| 3 | `DOC-2a33a6c34834e769` | yes | 0.6298 | 12.1 | 2953 | 337 | — |
| 4 | `DOC-2a55a2b5324659f8` | yes | 0.8098 | 12.2 | 2865 | 346 | — |
| 5 | `DOC-629fb5789dfd10ca` | yes | 0.7944 | 12.8 | 2836 | 353 | — |
| 6 | `DOC-e7c196f508907c6f` | yes | 0.7830 | 12.9 | 2834 | 361 | — |
| 7 | `DOC-158c0b74df673b81` | yes | 0.6442 | 13.1 | 2939 | 366 | — |
| 8 | `DOC-e2a58ed4c02470c0` | yes | 0.7805 | 13.1 | 2835 | 370 | — |
| 9 | `DOC-997823d9605a4a59` | yes | 0.6398 | 10.5 | 2973 | 355 | — |
| 10 | `DOC-968c9605eab0a87d` | yes | 0.6442 | 10.5 | 2942 | 367 | — |
| 11 | `DOC-9ba0a3d4c680b976` | yes | 0.6398 | 9.9 | 2982 | 334 | — |
| 12 | `DOC-9a6f58879fcb3367` | yes | 0.6442 | 11.2 | 2946 | 374 | — |
| 13 | `DOC-ef79520b2f50217b` | yes | 0.6892 | 11.3 | 3138 | 382 | — |
| 14 | `DOC-5c4e70db54374e72` | yes | 0.6915 | 12.0 | 3151 | 404 | — |
| 15 | `DOC-2435c398b95844bc` | yes | 0.6879 | 12.5 | 3080 | 453 | — |
| 16 | `DOC-5b1e8e2aed95c089` | yes | 0.6896 | 15.2 | 3123 | 543 | — |
| 17 | `DOC-9051d4cf8d7ab452` | yes | 0.7248 | 9.5 | 3115 | 307 | — |
| 18 | `DOC-00d28a1df0e3f6ba` | yes | 0.6971 | 7.7 | 2812 | 259 | — |
| 19 | `DOC-5060222215c75aa6` | yes | 0.6745 | 7.1 | 2801 | 245 | — |
| 20 | `DOC-728d06b610b25244` | yes | 0.7043 | 7.9 | 2804 | 273 | — |
| 21 | `DOC-e4b1466ee8d1ff19` | yes | 0.7037 | 11.8 | 3113 | 415 | — |
| 22 | `DOC-00ccdcb0154a8629` | yes | 0.6228 | 8.4 | 2812 | 281 | — |
| 23 | `DOC-f5e6c0de5f1d8593` | yes | 0.6955 | 9.0 | 2812 | 300 | — |
| 24 | `DOC-d8df43ed4d8faf89` | yes | 0.6888 | 15.5 | 3107 | 529 | — |
| 25 | `DOC-c34baab0b5fe378a` | yes | 0.6899 | 8.8 | 2807 | 299 | — |
| 26 | `DOC-6f6fc9762418a70f` | yes | 0.7048 | 8.1 | 2811 | 285 | — |
| 27 | `DOC-cbfcdb6f42cf2ae6` | yes | 0.6205 | 8.8 | 2806 | 290 | — |
| 28 | `DOC-29e384939c31d44a` | yes | 0.6131 | 9.5 | 3010 | 306 | — |
| 29 | `DOC-2d7cc160b78a69c5` | yes | 0.6442 | 11.1 | 2979 | 396 | — |
| 30 | `DOC-0cdb706a0cdbe3b6` | yes | 0.6131 | 9.3 | 2981 | 312 | — |
| 31 | `DOC-87c0c53132830a6c` | yes | 0.6265 | 11.2 | 2993 | 397 | — |
| 32 | `DOC-27b23fd94cc70d9d` | yes | 0.6052 | 9.9 | 2890 | 353 | — |
| 33 | `DOC-4e21681f375a247d` | yes | 0.6426 | 10.6 | 2985 | 382 | — |
| 34 | `DOC-364435343e0a2250` | yes | 0.6474 | 11.4 | 3020 | 393 | — |
| 35 | `DOC-7bd9dbc1b39ad41d` | yes | 0.6031 | 17.5 | 3171 | 626 | — |
| 36 | `DOC-3ae2dc5d624e2120` | yes | 0.5999 | 10.7 | 2871 | 338 | — |
| 37 | `DOC-93c8d133c296d536` | yes | 0.5663 | 10.8 | 2879 | 325 | — |
| 38 | `DOC-91da307f80433ae3` | yes | 0.5796 | 12.2 | 2894 | 358 | — |
| 39 | `DOC-44bcd388c4710b71` | yes | 0.5663 | 12.0 | 2884 | 346 | — |
| 40 | `DOC-90338506fc792f32` | yes | 0.5823 | 12.9 | 2882 | 372 | — |
| 41 | `DOC-164aa748f84cef54` | yes | 0.5810 | 14.7 | 2911 | 394 | — |
| 42 | `DOC-73d64bbeb296bd95` | yes | 0.6023 | 18.1 | 4524 | 580 | — |
| 43 | `DOC-7f1f866b022cee63` | yes | 0.7309 | 18.7 | 4985 | 508 | — |
| 44 | `DOC-384665a051d0fcd6` | yes | 0.6802 | 18.5 | 5208 | 529 | — |
| 45 | `DOC-ab18f15b7a51f1ab` | yes | 0.7414 | 15.0 | 5538 | 494 | — |
| 46 | `DOC-85314478b81710d9` | yes | 0.6287 | 14.7 | 5285 | 426 | — |
| 47 | `DOC-1076ac5b4b0df386` | yes | 0.5722 | 15.5 | 4482 | 508 | — |
| 48 | `DOC-6dcc0b9ba494c25b` | yes | 0.8133 | 15.7 | 5114 | 557 | — |
| 49 | `DOC-02f77aa77391a8c2` | yes | 0.6912 | 38.3 | 5091 | 1406 | — |
| 50 | `DOC-5b97ae3f8558703c` | yes | 0.6245 | 25.6 | 4565 | 996 | — |

_Generated 2026-10-13T04:32:57+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-insurance-claims-specialist-awq-2l4-c8.card.json`._
